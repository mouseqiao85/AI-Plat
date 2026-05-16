package middleware

import (
	"net/http"
	"strconv"
	"strings"

	"github.com/gin-gonic/gin"
)

// CORSConfig CORS配置
type CORSConfig struct {
	AllowedOrigins   []string
	AllowedMethods   []string
	AllowedHeaders   []string
	ExposedHeaders   []string
	AllowCredentials bool
	MaxAge           int
}

// DefaultCORSConfig 默认CORS配置
func DefaultCORSConfig() CORSConfig {
	return CORSConfig{
		AllowedOrigins: []string{
			"http://localhost:3000",
			"http://localhost:5173",
			"http://localhost:8080",
		},
		AllowedMethods: []string{
			http.MethodGet,
			http.MethodPost,
			http.MethodPut,
			http.MethodDelete,
			http.MethodOptions,
			http.MethodPatch,
		},
		AllowedHeaders: []string{
			"Origin",
			"Content-Type",
			"Authorization",
			"X-Requested-With",
			"Accept",
			"X-API-Key",
		},
		ExposedHeaders: []string{
			"Content-Length",
			"Content-Type",
			"X-Request-ID",
		},
		AllowCredentials: true,
		MaxAge:           86400, // 24小时
	}
}

// CORSMiddleware CORS中间件
func CORSMiddleware(config CORSConfig) gin.HandlerFunc {
	return func(c *gin.Context) {
		origin := c.Request.Header.Get("Origin")

		// 检查origin是否在允许列表中
		allowed := false
		for _, allowedOrigin := range config.AllowedOrigins {
			if allowedOrigin == "*" {
				allowed = true
				break
			}
			if allowedOrigin == origin {
				allowed = true
				break
			}
			// 支持通配符
			if strings.HasPrefix(allowedOrigin, "*.") {
				domain := strings.TrimPrefix(allowedOrigin, "*.")
				if strings.HasSuffix(origin, domain) {
					allowed = true
					break
				}
			}
		}

		if allowed {
			c.Header("Access-Control-Allow-Origin", origin)
		}

		// 设置其他CORS头
		c.Header("Access-Control-Allow-Methods", strings.Join(config.AllowedMethods, ", "))
		c.Header("Access-Control-Allow-Headers", strings.Join(config.AllowedHeaders, ", "))
		c.Header("Access-Control-Expose-Headers", strings.Join(config.ExposedHeaders, ", "))

		if config.AllowCredentials {
			c.Header("Access-Control-Allow-Credentials", "true")
		}

		if config.MaxAge > 0 {
			c.Header("Access-Control-Max-Age", strconv.Itoa(config.MaxAge))
		}

		// 处理预检请求
		if c.Request.Method == http.MethodOptions {
			c.AbortWithStatus(http.StatusNoContent)
			return
		}

		c.Next()
	}
}

// SecurityHeadersMiddleware 安全头中间件
func SecurityHeadersMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		// 防止XSS攻击
		c.Header("X-Content-Type-Options", "nosniff")
		c.Header("X-Frame-Options", "DENY")
		c.Header("X-XSS-Protection", "1; mode=block")

		// 内容安全策略
		c.Header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data: https:; connect-src 'self' https://cdn.jsdelivr.net")

		// 引用策略
		c.Header("Referrer-Policy", "strict-origin-when-cross-origin")

		// 特性策略
		c.Header("Permissions-Policy", "geolocation=(), microphone=(), camera=()")

		// HSTS (仅在生产环境启用HTTPS)
		// c.Header("Strict-Transport-Security", "max-age=31536000; includeSubDomains")

		c.Next()
	}
}

// InputSanitizerMiddleware 输入清理中间件
func InputSanitizerMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		// 只处理JSON请求
		if c.Request.Method != "GET" && c.Request.Method != "DELETE" {
			contentType := c.GetHeader("Content-Type")
			if strings.Contains(contentType, "application/json") {
				// 这里可以添加输入清理逻辑
				// 例如：XSS过滤、SQL注入检测等
			}
		}

		c.Next()
	}
}

// APIKeyAuthMiddleware API密钥认证中间件
func APIKeyAuthMiddleware(validAPIKeys []string) gin.HandlerFunc {
	validKeys := make(map[string]bool)
	for _, key := range validAPIKeys {
		validKeys[key] = true
	}

	return func(c *gin.Context) {
		apiKey := c.GetHeader("X-API-Key")

		// 如果提供了API密钥，验证它
		if apiKey != "" {
			if !validKeys[apiKey] {
				c.JSON(http.StatusUnauthorized, gin.H{
					"error":   "invalid_api_key",
					"message": "Invalid API key",
				})
				c.Abort()
				return
			}

			// API密钥有效，设置上下文
			c.Set("auth_type", "api_key")
			c.Set("api_key", apiKey)
		}

		c.Next()
	}
}

// RequestIDMiddleware 请求ID中间件
func RequestIDMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		requestID := c.GetHeader("X-Request-ID")
		if requestID == "" {
			// 生成请求ID
			requestID = generateRequestID()
		}

		// 设置请求ID到上下文和响应头
		c.Set("request_id", requestID)
		c.Header("X-Request-ID", requestID)

		c.Next()
	}
}

// generateRequestID 生成请求ID
func generateRequestID() string {
	// 使用简单的UUID生成
	// 实际生产中可以使用更强大的UUID库
	return strings.ReplaceAll(
		strings.ReplaceAll(
			strings.ReplaceAll(
				strings.ReplaceAll(
					strings.ToUpper(randomString(32)),
					"-", "",
				),
				" ", "",
			),
			"\n", "",
		),
		"\r", "",
	)
}

// randomString 生成随机字符串
func randomString(length int) string {
	const charset = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
	b := make([]byte, length)
	for i := range b {
		b[i] = charset[i%len(charset)]
	}
	return string(b)
}

// RecoveryMiddleware 恢复中间件
func RecoveryMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		defer func() {
			if err := recover(); err != nil {
				// 记录panic
				c.JSON(http.StatusInternalServerError, gin.H{
					"error":   "internal_server_error",
					"message": "An unexpected error occurred",
				})
				c.Abort()
			}
		}()
		c.Next()
	}
}
