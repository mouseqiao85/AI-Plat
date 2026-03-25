package proxy

import (
	"sync"
	"time"

	"github.com/ai-plat/gateway/internal/loadbalancer"
	"go.uber.org/zap"
)

type CircuitBreaker struct {
	maxRequests      uint32
	interval         time.Duration
	timeout          time.Duration
	failureThreshold uint32
	successThreshold uint32

	state map[string]*CircuitState
	mu    sync.RWMutex
}

type CircuitState struct {
	failures    uint32
	successes   uint32
	lastFailure time.Time
	state       string // "closed", "open", "half-open"
}

func NewCircuitBreaker(
	maxRequests uint32,
	interval time.Duration,
	timeout time.Duration,
	failureThreshold uint32,
	successThreshold uint32,
) *CircuitBreaker {
	return &CircuitBreaker{
		maxRequests:      maxRequests,
		interval:         interval,
		timeout:          timeout,
		failureThreshold: failureThreshold,
		successThreshold: successThreshold,
		state:            make(map[string]*CircuitState),
	}
}

func (cb *CircuitBreaker) AllowRequest(backendURL string) bool {
	cb.mu.Lock()
	defer cb.mu.Unlock()

	state, exists := cb.state[backendURL]
	if !exists {
		state = &CircuitState{state: "closed"}
		cb.state[backendURL] = state
	}

	switch state.state {
	case "closed":
		return true
	case "open":
		if time.Since(state.lastFailure) > cb.timeout {
			state.state = "half-open"
			state.failures = 0
			state.successes = 0
			return true
		}
		return false
	case "half-open":
		return true
	}
	return false
}

func (cb *CircuitBreaker) RecordSuccess(backendURL string) {
	cb.mu.Lock()
	defer cb.mu.Unlock()

	state, exists := cb.state[backendURL]
	if !exists {
		return
	}

	state.successes++

	if state.state == "half-open" && state.successes >= cb.successThreshold {
		state.state = "closed"
		state.failures = 0
		state.successes = 0
	}
}

func (cb *CircuitBreaker) RecordFailure(backendURL string) {
	cb.mu.Lock()
	defer cb.mu.Unlock()

	state, exists := cb.state[backendURL]
	if !exists {
		state = &CircuitState{state: "closed"}
		cb.state[backendURL] = state
	}

	state.failures++
	state.lastFailure = time.Now()

	if state.state == "half-open" {
		state.state = "open"
		return
	}

	if state.failures >= cb.failureThreshold {
		state.state = "open"
	}
}

func (cb *CircuitBreaker) GetState(backendURL string) string {
	cb.mu.RLock()
	defer cb.mu.RUnlock()

	if state, exists := cb.state[backendURL]; exists {
		return state.state
	}
	return "closed"
}

type HealthChecker struct {
	backends []*loadbalancer.Backend
	interval time.Duration
	timeout  time.Duration
	logger   *zap.Logger
	stopChan chan struct{}
}

func NewHealthChecker(
	backends []*loadbalancer.Backend,
	interval time.Duration,
	timeout time.Duration,
	logger *zap.Logger,
) *HealthChecker {
	return &HealthChecker{
		backends: backends,
		interval: interval,
		timeout:  timeout,
		logger:   logger,
		stopChan: make(chan struct{}),
	}
}

func (hc *HealthChecker) Start() {
	ticker := time.NewTicker(hc.interval)
	defer ticker.Stop()

	for {
		select {
		case <-hc.stopChan:
			return
		case <-ticker.C:
			hc.checkAll()
		}
	}
}

func (hc *HealthChecker) Stop() {
	close(hc.stopChan)
}

func (hc *HealthChecker) checkAll() {
	for _, backend := range hc.backends {
		go hc.checkBackend(backend)
	}
}

func (hc *HealthChecker) checkBackend(backend *loadbalancer.Backend) {
	client := http.Client{Timeout: hc.timeout}

	start := time.Now()
	resp, err := client.Get(backend.URL + "/health")
	duration := time.Since(start)

	if err != nil {
		backend.SetAlive(false)
		hc.logger.Warn("health check failed",
			zap.String("backend", backend.URL),
			zap.Error(err),
		)
		return
	}
	defer resp.Body.Close()

	backend.ResponseTime = duration
	backend.LastChecked = time.Now()
	backend.SetAlive(resp.StatusCode >= 200 && resp.StatusCode < 300)

	if backend.IsAlive() {
		hc.logger.Debug("health check passed",
			zap.String("backend", backend.URL),
			zap.Duration("response_time", duration),
		)
	}
}
