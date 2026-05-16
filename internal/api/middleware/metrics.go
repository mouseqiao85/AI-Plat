package middleware

import (
	"strconv"
	"time"

	"github.com/gin-gonic/gin"
)

var (
	RequestsTotal    = make(map[string]int64)
	ErrorsTotal      = make(map[string]int64)
	requestDurations = make(map[string][]float64)
)

func MetricsMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		start := time.Now()
		path := c.FullPath()
		if path == "" {
			path = c.Request.URL.Path
		}

		c.Next()

		duration := time.Since(start).Seconds()
		RequestsTotal[path]++
		if c.Writer.Status() >= 400 {
			ErrorsTotal[path]++
		}
		requestDurations[path] = append(requestDurations[path], duration)
		c.Header("X-Response-Time", strconv.FormatFloat(duration*1000, 'f', 2, 64)+"ms")
	}
}
