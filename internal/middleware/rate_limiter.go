package middleware

import (
	"net/http"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
	"golang.org/x/time/rate"
)

// RateLimiterConfig 限流配置
type RateLimiterConfig struct {
	RequestsPerSecond rate.Limit // 每秒请求数
	Burst             int        // 突发请求数
	Enabled           bool       // 是否启用
}

// IPRateLimiter 基于IP的限流器
type IPRateLimiter struct {
	ips map[string]*rate.Limiter
	mu  sync.RWMutex
	r   rate.Limit
	b   int
}

// NewIPRateLimiter 创建IP限流器
func NewIPRateLimiter(r rate.Limit, b int) *IPRateLimiter {
	return &IPRateLimiter{
		ips: make(map[string]*rate.Limiter),
		r:   r,
		b:   b,
	}
}

// GetLimiter 获取指定IP的限流器
func (i *IPRateLimiter) GetLimiter(ip string) *rate.Limiter {
	i.mu.Lock()
	defer i.mu.Unlock()

	limiter, exists := i.ips[ip]
	if !exists {
		limiter = rate.NewLimiter(i.r, i.b)
		i.ips[ip] = limiter
	}

	return limiter
}

// CleanupOldLimiters 清理旧的限流器（防止内存泄漏）
func (i *IPRateLimiter) CleanupOldLimiters() {
	ticker := time.NewTicker(5 * time.Minute)
	defer ticker.Stop()

	for range ticker.C {
		i.mu.Lock()
		for ip, limiter := range i.ips {
			// 如果限流器超过10分钟未使用，则删除
			if limiter.Allow() {
				delete(i.ips, ip)
			}
		}
		i.mu.Unlock()
	}
}

// RateLimitMiddleware 限流中间件
func RateLimitMiddleware(config RateLimiterConfig) gin.HandlerFunc {
	if !config.Enabled {
		return func(c *gin.Context) {
			c.Next()
		}
	}

	limiter := NewIPRateLimiter(config.RequestsPerSecond, config.Burst)
	go limiter.CleanupOldLimiters()

	return func(c *gin.Context) {
		ip := c.ClientIP()
		ipLimiter := limiter.GetLimiter(ip)

		if !ipLimiter.Allow() {
			c.JSON(http.StatusTooManyRequests, gin.H{
				"error":   "rate_limit_exceeded",
				"message": "Too many requests, please try again later",
				"retry_after": "60s",
			})
			c.Abort()
			return
		}

		c.Next()
	}
}

// RateLimitByUser 基于用户的限流
func RateLimitByUser(config RateLimiterConfig) gin.HandlerFunc {
	if !config.Enabled {
		return func(c *gin.Context) {
			c.Next()
		}
	}

	limiters := make(map[string]*rate.Limiter)
	var mu sync.RWMutex

	return func(c *gin.Context) {
		// 从上下文获取用户ID
		userID, exists := c.Get("user_id")
		if !exists {
			c.Next()
			return
		}

		userIDStr := userID.(string)

		mu.Lock()
		limiter, exists := limiters[userIDStr]
		if !exists {
			limiter = rate.NewLimiter(config.RequestsPerSecond, config.Burst)
			limiters[userIDStr] = limiter
		}
		mu.Unlock()

		if !limiter.Allow() {
			c.JSON(http.StatusTooManyRequests, gin.H{
				"error":   "rate_limit_exceeded",
				"message": "Too many requests for this user",
				"retry_after": "60s",
			})
			c.Abort()
			return
		}

		c.Next()
	}
}

// SlidingWindowRateLimiter 滑动窗口限流器
type SlidingWindowRateLimiter struct {
	requests map[string][]time.Time
	mu       sync.RWMutex
	window   time.Duration
	limit    int
}

// NewSlidingWindowRateLimiter 创建滑动窗口限流器
func NewSlidingWindowRateLimiter(window time.Duration, limit int) *SlidingWindowRateLimiter {
	return &SlidingWindowRateLimiter{
		requests: make(map[string][]time.Time),
		window:   window,
		limit:    limit,
	}
}

// Allow 检查是否允许请求
func (s *SlidingWindowRateLimiter) Allow(key string) bool {
	s.mu.Lock()
	defer s.mu.Unlock()

	now := time.Now()
	windowStart := now.Add(-s.window)

	// 获取该key的所有请求时间
	requests, exists := s.requests[key]
	if !exists {
		s.requests[key] = []time.Time{now}
		return true
	}

	// 过滤掉窗口外的请求
	validRequests := []time.Time{}
	for _, reqTime := range requests {
		if reqTime.After(windowStart) {
			validRequests = append(validRequests, reqTime)
		}
	}

	// 检查是否超过限制
	if len(validRequests) >= s.limit {
		s.requests[key] = validRequests
		return false
	}

	// 添加当前请求
	validRequests = append(validRequests, now)
	s.requests[key] = validRequests
	return true
}

// SlidingWindowMiddleware 滑动窗口限流中间件
func SlidingWindowMiddleware(window time.Duration, limit int) gin.HandlerFunc {
	limiter := NewSlidingWindowRateLimiter(window, limit)

	return func(c *gin.Context) {
		ip := c.ClientIP()

		if !limiter.Allow(ip) {
			c.JSON(http.StatusTooManyRequests, gin.H{
				"error":   "rate_limit_exceeded",
				"message": "Too many requests in the time window",
				"window":  window.String(),
				"limit":   limit,
			})
			c.Abort()
			return
		}

		c.Next()
	}
}
