package middleware

import (
	"bytes"
	"encoding/json"
	"io"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/sirupsen/logrus"
)

// SensitiveField 敏感字段配置
type SensitiveField struct {
	Fields    []string
	MaskValue string
}

// LogConfig 日志配置
type LogConfig struct {
	Level           string
	Format          string
	Output          string
	MaskSensitive   bool
	SensitiveFields []string
}

// SensitiveDataMasker 敏感数据脱敏器
type SensitiveDataMasker struct {
	fields    map[string]bool
	maskValue string
}

// NewSensitiveDataMasker 创建敏感数据脱敏器
func NewSensitiveDataMasker(sensitiveFields []string, maskValue string) *SensitiveDataMasker {
	fields := make(map[string]bool)
	for _, field := range sensitiveFields {
		fields[strings.ToLower(field)] = true
	}

	return &SensitiveDataMasker{
		fields:    fields,
		maskValue: maskValue,
	}
}

// MaskMap 脱敏map数据
func (s *SensitiveDataMasker) MaskMap(data map[string]interface{}) map[string]interface{} {
	result := make(map[string]interface{})
	for key, value := range data {
		lowerKey := strings.ToLower(key)
		if s.fields[lowerKey] {
			result[key] = s.maskValue
		} else {
			switch v := value.(type) {
			case map[string]interface{}:
				result[key] = s.MaskMap(v)
			default:
				result[key] = value
			}
		}
	}
	return result
}

// MaskJSON 脱敏JSON数据
func (s *SensitiveDataMasker) MaskJSON(jsonData []byte) string {
	var data map[string]interface{}
	if err := json.Unmarshal(jsonData, &data); err != nil {
		return string(jsonData)
	}

	maskedData := s.MaskMap(data)
	result, err := json.Marshal(maskedData)
	if err != nil {
		return string(jsonData)
	}

	return string(result)
}

// StructuredLogger 结构化日志中间件
func StructuredLogger(masker *SensitiveDataMasker) gin.HandlerFunc {
	logger := logrus.New()
	logger.SetFormatter(&logrus.JSONFormatter{
		TimestampFormat: time.RFC3339,
	})

	return func(c *gin.Context) {
		start := time.Now()
		path := c.Request.URL.Path
		query := c.Request.URL.RawQuery

		// 读取请求体
		var requestBody []byte
		if c.Request.Body != nil {
			requestBody, _ = io.ReadAll(c.Request.Body)
			c.Request.Body = io.NopCloser(bytes.NewBuffer(requestBody))
		}

		// 创建响应写入器
		blw := &bodyLogWriter{body: bytes.NewBufferString(""), ResponseWriter: c.Writer}
		c.Writer = blw

		// 处理请求
		c.Next()

		// 计算延迟
		latency := time.Since(start)

		// 脱敏处理
		maskedRequestBody := requestBody
		maskedResponseBody := blw.body.Bytes()

		if masker != nil {
			maskedRequestBody = []byte(masker.MaskJSON(requestBody))
			maskedResponseBody = []byte(masker.MaskJSON(blw.body.Bytes()))
		}

		// 记录日志
		entry := logger.WithFields(logrus.Fields{
			"status":     c.Writer.Status(),
			"method":     c.Request.Method,
			"path":       path,
			"query":      query,
			"ip":         c.ClientIP(),
			"latency":    latency.String(),
			"user-agent": c.Request.UserAgent(),
			"request":    string(maskedRequestBody),
			"response":   string(maskedResponseBody),
		})

		// 根据状态码设置日志级别
		if c.Writer.Status() >= 500 {
			entry.Error("Server error")
		} else if c.Writer.Status() >= 400 {
			entry.Warn("Client error")
		} else {
			entry.Info("Request handled")
		}
	}
}

// bodyLogWriter 响应体日志写入器
type bodyLogWriter struct {
	gin.ResponseWriter
	body *bytes.Buffer
}

func (w bodyLogWriter) Write(b []byte) (int, error) {
	w.body.Write(b)
	return w.ResponseWriter.Write(b)
}

// AuditLogger 审计日志中间件
func AuditLogger(masker *SensitiveDataMasker) gin.HandlerFunc {
	logger := logrus.New()
	logger.SetFormatter(&logrus.JSONFormatter{
		TimestampFormat: time.RFC3339,
	})

	return func(c *gin.Context) {
		// 只记录关键操作
		method := c.Request.Method
		if method == "POST" || method == "PUT" || method == "DELETE" || method == "PATCH" {
			start := time.Now()
			path := c.Request.URL.Path

			// 读取请求体
			var requestBody []byte
			if c.Request.Body != nil {
				requestBody, _ = io.ReadAll(c.Request.Body)
				c.Request.Body = io.NopCloser(bytes.NewBuffer(requestBody))
			}

			// 脱敏
			maskedBody := string(requestBody)
			if masker != nil {
				maskedBody = masker.MaskJSON(requestBody)
			}

			c.Next()

			// 记录审计日志
			logger.WithFields(logrus.Fields{
				"timestamp": time.Now().Format(time.RFC3339),
				"method":    method,
				"path":      path,
				"status":    c.Writer.Status(),
				"ip":        c.ClientIP(),
				"user_id":   c.GetString("user_id"),
				"latency":   time.Since(start).String(),
				"request":   maskedBody,
			}).Info("Audit log")
		} else {
			c.Next()
		}
	}
}

// ErrorLogger 错误日志中间件
func ErrorLogger() gin.HandlerFunc {
	logger := logrus.New()
	logger.SetFormatter(&logrus.JSONFormatter{})

	return func(c *gin.Context) {
		c.Next()

		// 记录错误
		if len(c.Errors) > 0 {
			for _, err := range c.Errors {
				logger.WithFields(logrus.Fields{
					"path":  c.Request.URL.Path,
					"method": c.Request.Method,
					"ip":    c.ClientIP(),
					"error": err.Error(),
				}).Error("Request error")
			}
		}
	}
}

// RequestValidator 请求验证中间件
func RequestValidator() gin.HandlerFunc {
	return func(c *gin.Context) {
		// 检查Content-Type
		if c.Request.Method == "POST" || c.Request.Method == "PUT" || c.Request.Method == "PATCH" {
			contentType := c.GetHeader("Content-Type")
			if contentType != "" && !strings.Contains(contentType, "application/json") &&
				!strings.Contains(contentType, "multipart/form-data") {
				c.JSON(400, gin.H{
					"error":   "invalid_content_type",
					"message": "Content-Type must be application/json or multipart/form-data",
				})
				c.Abort()
				return
			}
		}

		// 检查请求体大小
		if c.Request.ContentLength > 10*1024*1024 { // 10MB
			c.JSON(413, gin.H{
				"error":   "request_too_large",
				"message": "Request body must be less than 10MB",
			})
			c.Abort()
			return
		}

		c.Next()
	}
}
