package proxy

import (
	"context"
	"fmt"
	"io"
	"net/http"
	"net/http/httputil"
	"net/url"
	"strings"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
	"go.uber.org/zap"

	"github.com/ai-plat/gateway/internal/config"
	"github.com/ai-plat/gateway/internal/loadbalancer"
)

type ReverseProxy struct {
	upstreams      map[string]*Upstream
	logger         *zap.Logger
	circuitBreaker *CircuitBreaker
	mu             sync.RWMutex
}

type Upstream struct {
	Name         string
	Path         string
	Backends     []*loadbalancer.Backend
	LoadBalancer loadbalancer.LoadBalancer
	HealthCheck  *HealthChecker
}

func NewReverseProxy(cfg *config.Config, logger *zap.Logger) *ReverseProxy {
	rp := &ReverseProxy{
		upstreams: make(map[string]*Upstream),
		logger:    logger,
	}

	if cfg.CircuitBreaker.Enabled {
		rp.circuitBreaker = NewCircuitBreaker(
			cfg.CircuitBreaker.MaxRequests,
			cfg.CircuitBreaker.Interval,
			cfg.CircuitBreaker.Timeout,
			cfg.CircuitBreaker.FailureThreshold,
			cfg.CircuitBreaker.SuccessThreshold,
		)
	}

	for _, upstreamCfg := range cfg.Upstreams {
		upstream := rp.createUpstream(&upstreamCfg)
		rp.upstreams[upstreamCfg.Name] = upstream
	}

	return rp
}

func (rp *ReverseProxy) createUpstream(cfg *config.UpstreamConfig) *Upstream {
	backends := make([]*loadbalancer.Backend, 0, len(cfg.Targets))
	for _, target := range cfg.Targets {
		backends = append(backends, &loadbalancer.Backend{
			URL:   target,
			Alive: true,
		})
	}

	var lb loadbalancer.LoadBalancer
	switch cfg.LoadBalance {
	case "least_connections":
		lb = loadbalancer.NewLeastConnections()
	case "weighted_round_robin":
		weights := make(map[string]int)
		for i, b := range backends {
			weights[b.URL] = len(backends) - i
		}
		lb = loadbalancer.NewWeightedRoundRobin(weights)
	default:
		lb = loadbalancer.NewRoundRobin()
	}

	upstream := &Upstream{
		Name:         cfg.Name,
		Path:         cfg.Path,
		Backends:     backends,
		LoadBalancer: lb,
	}

	if cfg.HealthCheck != nil && cfg.HealthCheck.Enabled {
		upstream.HealthCheck = NewHealthChecker(
			upstream.Backends,
			cfg.HealthCheck.Interval,
			cfg.HealthCheck.Timeout,
			rp.logger,
		)
		go upstream.HealthCheck.Start()
	}

	return upstream
}

func (rp *ReverseProxy) Handler(upstreamName string) gin.HandlerFunc {
	return func(c *gin.Context) {
		rp.mu.RLock()
		upstream, exists := rp.upstreams[upstreamName]
		rp.mu.RUnlock()

		if !exists {
			c.JSON(http.StatusBadGateway, gin.H{
				"code":    http.StatusBadGateway,
				"message": "upstream not found",
			})
			return
		}

		backend := upstream.LoadBalancer.Select(upstream.Backends)
		if backend == nil {
			c.JSON(http.StatusServiceUnavailable, gin.H{
				"code":    http.StatusServiceUnavailable,
				"message": "no healthy backends available",
			})
			return
		}

		if rp.circuitBreaker != nil {
			if !rp.circuitBreaker.AllowRequest(backend.URL) {
				c.JSON(http.StatusServiceUnavailable, gin.H{
					"code":    http.StatusServiceUnavailable,
					"message": "circuit breaker open",
				})
				return
			}
		}

		start := time.Now()
		err := rp.proxyRequest(c, backend, upstream)
		duration := time.Since(start)

		if err != nil {
			backend.IncrementFailures()
			if rp.circuitBreaker != nil {
				rp.circuitBreaker.RecordFailure(backend.URL)
			}
			rp.logger.Error("proxy request failed",
				zap.String("upstream", upstreamName),
				zap.String("backend", backend.URL),
				zap.Error(err),
				zap.Duration("duration", duration),
			)
			return
		}

		backend.ResetFailures()
		if rp.circuitBreaker != nil {
			rp.circuitBreaker.RecordSuccess(backend.URL)
		}

		if lc, ok := upstream.LoadBalancer.(*loadbalancer.LeastConnections); ok {
			lc.Release(backend.URL)
		}
	}
}

func (rp *ReverseProxy) proxyRequest(c *gin.Context, backend *loadbalancer.Backend, upstream *Upstream) error {
	targetURL, err := url.Parse(backend.URL)
	if err != nil {
		return fmt.Errorf("parse target URL: %w", err)
	}

	proxy := httputil.NewSingleHostReverseProxy(targetURL)

	proxy.Director = func(req *http.Request) {
		req.URL.Scheme = targetURL.Scheme
		req.URL.Host = targetURL.Host
		req.URL.Path = strings.TrimPrefix(req.URL.Path, upstream.Path)
		if req.URL.Path == "" {
			req.URL.Path = "/"
		}
		req.Host = targetURL.Host
		req.Header.Set("X-Forwarded-For", c.ClientIP())
		req.Header.Set("X-Forwarded-Proto", c.Request.URL.Scheme)
		req.Header.Set("X-Forwarded-Host", c.Request.Host)
		req.Header.Set("X-Real-IP", c.ClientIP())

		if userID, exists := c.Get("user_id"); exists {
			req.Header.Set("X-User-ID", userID.(string))
		}
		if username, exists := c.Get("username"); exists {
			req.Header.Set("X-Username", username.(string))
		}
		if role, exists := c.Get("role"); exists {
			req.Header.Set("X-User-Role", role.(string))
		}
	}

	proxy.ModifyResponse = func(resp *http.Response) error {
		resp.Header.Set("X-Upstream", backend.URL)
		return nil
	}

	proxy.ErrorHandler = func(w http.ResponseWriter, r *http.Request, err error) {
		rp.logger.Error("proxy error",
			zap.String("path", r.URL.Path),
			zap.String("backend", backend.URL),
			zap.Error(err),
		)
		w.WriteHeader(http.StatusBadGateway)
		io.WriteString(w, `{"code":502,"message":"bad gateway"}`)
	}

	proxy.ServeHTTP(c.Writer, c.Request)
	return nil
}

func (rp *ReverseProxy) HealthCheck(ctx context.Context) {
	ticker := time.NewTicker(10 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			rp.mu.RLock()
			for _, upstream := range rp.upstreams {
				for _, backend := range upstream.Backends {
					rp.checkBackend(backend)
				}
			}
			rp.mu.RUnlock()
		}
	}
}

func (rp *ReverseProxy) checkBackend(backend *loadbalancer.Backend) {
	client := http.Client{Timeout: 5 * time.Second}
	resp, err := client.Get(backend.URL + "/health")
	if err != nil {
		backend.SetAlive(false)
		rp.logger.Warn("backend health check failed",
			zap.String("backend", backend.URL),
			zap.Error(err),
		)
		return
	}
	defer resp.Body.Close()

	backend.SetAlive(resp.StatusCode == http.StatusOK)
	backend.LastChecked = time.Now()
}

func (rp *ReverseProxy) GetUpstream(name string) (*Upstream, bool) {
	rp.mu.RLock()
	defer rp.mu.RUnlock()
	upstream, exists := rp.upstreams[name]
	return upstream, exists
}

func (rp *ReverseProxy) ListUpstreams() []string {
	rp.mu.RLock()
	defer rp.mu.RUnlock()
	names := make([]string, 0, len(rp.upstreams))
	for name := range rp.upstreams {
		names = append(names, name)
	}
	return names
}

func (rp *ReverseProxy) GetBackends(upstreamName string) []*loadbalancer.Backend {
	rp.mu.RLock()
	defer rp.mu.RUnlock()
	if upstream, exists := rp.upstreams[upstreamName]; exists {
		return upstream.Backends
	}
	return nil
}
