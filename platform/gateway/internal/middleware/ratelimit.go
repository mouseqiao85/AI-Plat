package middleware

import (
	"sync"
	"time"

	"github.com/ai-plat/gateway/pkg/response"
	"github.com/gin-gonic/gin"
	"golang.org/x/time/rate"
)

type RateLimiter struct {
	limiters sync.Map
	rps      int
	burst    int
}

type IPRateLimiter struct {
	limiters sync.Map
	rps      int
	burst    int
}

func NewRateLimiter(rps, burst int) *RateLimiter {
	return &RateLimiter{
		rps:   rps,
		burst: burst,
	}
}

func NewIPRateLimiter(rps, burst int) *IPRateLimiter {
	return &IPRateLimiter{
		rps:   rps,
		burst: burst,
	}
}

func (rl *RateLimiter) getLimiter(key string) *rate.Limiter {
	if limiter, ok := rl.limiters.Load(key); ok {
		return limiter.(*rate.Limiter)
	}

	limiter := rate.NewLimiter(rate.Limit(rl.rps), rl.burst)
	rl.limiters.Store(key, limiter)
	return limiter
}

func (rl *IPRateLimiter) getLimiter(ip string) *rate.Limiter {
	if limiter, ok := rl.limiters.Load(ip); ok {
		return limiter.(*rate.Limiter)
	}

	limiter := rate.NewLimiter(rate.Limit(rl.rps), rl.burst)
	rl.limiters.Store(ip, limiter)
	return limiter
}

func (rl *RateLimiter) Allow(key string) bool {
	return rl.getLimiter(key).Allow()
}

func (rl *IPRateLimiter) Allow(ip string) bool {
	return rl.getLimiter(ip).Allow()
}

func RateLimit(rps, burst int) gin.HandlerFunc {
	limiter := NewRateLimiter(rps, burst)

	return func(c *gin.Context) {
		key := c.ClientIP()
		if !limiter.Allow(key) {
			response.TooManyRequests(c, "rate limit exceeded")
			c.Abort()
			return
		}
		c.Next()
	}
}

func IPRateLimit(rps, burst int) gin.HandlerFunc {
	limiter := NewIPRateLimiter(rps, burst)

	return func(c *gin.Context) {
		ip := c.ClientIP()
		if !limiter.Allow(ip) {
			response.TooManyRequests(c, "rate limit exceeded for your IP")
			c.Abort()
			return
		}
		c.Next()
	}
}

func UserRateLimit(rps, burst int) gin.HandlerFunc {
	limiters := make(map[string]*rate.Limiter)
	mu := sync.RWMutex{}

	cleanupTicker := time.NewTicker(time.Minute)
	go func() {
		for range cleanupTicker.C {
			mu.Lock()
			limiters = make(map[string]*rate.Limiter)
			mu.Unlock()
		}
	}()

	return func(c *gin.Context) {
		userID, exists := c.Get("user_id")
		if !exists {
			c.Next()
			return
		}

		key := userID.(string)

		mu.RLock()
		limiter, exists := limiters[key]
		mu.RUnlock()

		if !exists {
			mu.Lock()
			limiter = rate.NewLimiter(rate.Limit(rps), burst)
			limiters[key] = limiter
			mu.Unlock()
		}

		if !limiter.Allow() {
			response.TooManyRequests(c, "rate limit exceeded")
			c.Abort()
			return
		}

		c.Next()
	}
}

func SlidingWindowRateLimit(windowSize time.Duration, maxRequests int) gin.HandlerFunc {
	type window struct {
		timestamps []time.Time
		mu         sync.Mutex
	}

	windows := make(map[string]*window)
	mu := sync.RWMutex{}

	cleanupTicker := time.NewTicker(time.Minute)
	go func() {
		for now := range cleanupTicker.C {
			mu.Lock()
			for key, w := range windows {
				w.mu.Lock()
				validIdx := 0
				for _, t := range w.timestamps {
					if now.Sub(t) <= windowSize {
						w.timestamps[validIdx] = t
						validIdx++
					}
				}
				w.timestamps = w.timestamps[:validIdx]
				if len(w.timestamps) == 0 {
					delete(windows, key)
				}
				w.mu.Unlock()
			}
			mu.Unlock()
		}
	}()

	return func(c *gin.Context) {
		key := c.ClientIP()
		now := time.Now()

		mu.RLock()
		w, exists := windows[key]
		mu.RUnlock()

		if !exists {
			mu.Lock()
			w = &window{timestamps: []time.Time{}}
			windows[key] = w
			mu.Unlock()
		}

		w.mu.Lock()
		validIdx := 0
		for _, t := range w.timestamps {
			if now.Sub(t) <= windowSize {
				w.timestamps[validIdx] = t
				validIdx++
			}
		}
		w.timestamps = w.timestamps[:validIdx]

		if len(w.timestamps) >= maxRequests {
			w.mu.Unlock()
			response.TooManyRequests(c, "rate limit exceeded")
			c.Abort()
			return
		}

		w.timestamps = append(w.timestamps, now)
		w.mu.Unlock()

		c.Next()
	}
}
