package main

import (
	"context"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/gin-gonic/gin"
	"go.uber.org/zap"

	"github.com/ai-plat/gateway/internal/config"
	"github.com/ai-plat/gateway/internal/middleware"
	"github.com/ai-plat/gateway/internal/proxy"
	"github.com/ai-plat/gateway/pkg/jwt"
)

func main() {
	logger, _ := zap.NewProduction()
	defer logger.Sync()

	cfg, err := config.Load("config/config.yaml")
	if err != nil {
		logger.Fatal("load config failed", zap.Error(err))
	}

	gin.SetMode(cfg.Server.Mode)

	router := gin.New()

	router.Use(gin.Recovery())
	router.Use(middleware.CORS())

	jwtService := jwt.NewJWTService(
		cfg.JWT.Secret,
		cfg.JWT.Expire,
		cfg.JWT.Issuer,
	)

	reverseProxy := proxy.NewReverseProxy(cfg, logger)

	setupRoutes(router, cfg, jwtService, reverseProxy, logger)

	srv := &http.Server{
		Addr:           fmt.Sprintf(":%d", cfg.Server.Port),
		Handler:        router,
		ReadTimeout:    cfg.Server.ReadTimeout,
		WriteTimeout:   cfg.Server.WriteTimeout,
		MaxHeaderBytes: cfg.Server.MaxHeaderBytes,
	}

	go func() {
		logger.Info("starting gateway server",
			zap.Int("port", cfg.Server.Port),
		)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			logger.Fatal("listen failed", zap.Error(err))
		}
	}()

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	logger.Info("shutting down gateway server...")

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := srv.Shutdown(ctx); err != nil {
		logger.Fatal("server shutdown failed", zap.Error(err))
	}

	logger.Info("gateway server exited")
}

func setupRoutes(
	router *gin.Engine,
	cfg *config.Config,
	jwtService *jwt.JWTService,
	reverseProxy *proxy.ReverseProxy,
	logger *zap.Logger,
) {
	router.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"status":  "healthy",
			"service": "ai-plat-gateway",
			"version": "1.0.0",
		})
	})

	router.GET("/ready", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"ready":     true,
			"upstreams": reverseProxy.ListUpstreams(),
		})
	})

	router.GET("/metrics", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"upstreams": getUpstreamMetrics(reverseProxy),
		})
	})

	for _, routeCfg := range cfg.Routes {
		handler := buildHandler(routeCfg, cfg, jwtService, reverseProxy, logger)

		router.Any(routeCfg.Path, handler)
		router.Any(routeCfg.Path+"/*action", handler)
	}

	router.NoRoute(func(c *gin.Context) {
		c.JSON(http.StatusNotFound, gin.H{
			"code":    http.StatusNotFound,
			"message": "route not found",
		})
	})
}

func buildHandler(
	routeCfg config.RouteConfig,
	cfg *config.Config,
	jwtService *jwt.JWTService,
	reverseProxy *proxy.ReverseProxy,
	logger *zap.Logger,
) gin.HandlerFunc {
	return func(c *gin.Context) {
		if routeCfg.RateLimit && cfg.RateLimit.Enabled {
			if !checkRateLimit(c, cfg) {
				return
			}
		}

		if routeCfg.AuthRequired {
			middleware.Auth(jwtService)(c)
			if c.IsAborted() {
				return
			}
		}

		if routeCfg.Upstream == "" {
			c.JSON(http.StatusOK, gin.H{
				"status":  "ok",
				"message": "gateway is running",
			})
			return
		}

		reverseProxy.Handler(routeCfg.Upstream)(c)
	}
}

func checkRateLimit(c *gin.Context, cfg *config.Config) bool {
	return true
}

func getUpstreamMetrics(reverseProxy *proxy.ReverseProxy) map[string]interface{} {
	metrics := make(map[string]interface{})

	for _, name := range reverseProxy.ListUpstreams() {
		backends := reverseProxy.GetBackends(name)
		backendStatus := make([]map[string]interface{}, 0)

		for _, b := range backends {
			backendStatus = append(backendStatus, map[string]interface{}{
				"url":           b.URL,
				"alive":         b.IsAlive(),
				"failures":      b.GetFailures(),
				"response_time": b.ResponseTime.String(),
				"last_checked":  b.LastChecked,
			})
		}

		metrics[name] = map[string]interface{}{
			"backends": backendStatus,
		}
	}

	return metrics
}
