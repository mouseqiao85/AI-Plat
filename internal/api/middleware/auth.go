package middleware

import (
	"net/http"
	"strings"

	"github.com/gin-gonic/gin"

	"github.com/agent-platform/pkg/auth"
)

// AuthMiddleware returns a Gin middleware that validates JWT tokens.
// If devToken is non-empty and cfg.Debug is true, requests carrying that
// token bypass JWT validation (developer convenience).
func AuthMiddleware(debug bool, devToken string) gin.HandlerFunc {
	return func(c *gin.Context) {
		header := c.GetHeader("Authorization")
		if header == "" {
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "未提供认证令牌"})
			return
		}

		tokenStr := strings.TrimPrefix(header, "Bearer ")

		// Dev token bypass — only when explicitly configured AND debug mode is on
		if debug && devToken != "" && tokenStr == devToken {
			c.Set("user_id", int64(1))
			c.Set("username", "admin")
			c.Set("role", "admin")
			c.Set("tier", "enterprise")
			c.Next()
			return
		}

		claims, err := auth.ValidateToken(tokenStr)
		if err != nil {
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "令牌无效或已过期"})
			return
		}

		c.Set("user_id", claims.UserID)
		c.Set("username", claims.Username)
		c.Set("role", claims.Role)
		c.Set("tier", claims.Tier)
		c.Next()
	}
}

func GetUserID(c *gin.Context) int64 {
	id, _ := c.Get("user_id")
	return id.(int64)
}

func GetUsername(c *gin.Context) string {
	name, _ := c.Get("username")
	return name.(string)
}

func GetRole(c *gin.Context) string {
	role, _ := c.Get("role")
	return role.(string)
}

func GetTier(c *gin.Context) string {
	tier, _ := c.Get("tier")
	return tier.(string)
}

// AdminMiddleware ensures the user has admin role
func AdminMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		role := GetRole(c)
		if role != "admin" {
			c.AbortWithStatusJSON(http.StatusForbidden, gin.H{"error": "需要管理员权限"})
			return
		}
		c.Next()
	}
}
