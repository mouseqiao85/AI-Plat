package api

import (
	"net/http"
	"os"
	"path/filepath"
	"strings"

	"github.com/gin-gonic/gin"
)

// serveStaticAsset serves files under ./web/dist/assets/ with long-lived caching
// and transparent gzip when a sibling .gz file exists. Filenames include a
// content hash so aggressive caching is safe.
func serveStaticAsset(c *gin.Context) {
	rel := strings.TrimPrefix(c.Param("filepath"), "/")
	// Reject path traversal.
	if strings.Contains(rel, "..") || strings.HasPrefix(rel, "/") {
		c.Status(http.StatusBadRequest)
		return
	}
	full := filepath.Join("./web/dist/assets", rel)

	// Every asset under /assets/* has a content-hashed filename -> immutable.
	c.Header("Cache-Control", "public, max-age=31536000, immutable")

	// Serve precompressed .gz when available and client accepts gzip.
	if strings.Contains(c.GetHeader("Accept-Encoding"), "gzip") {
		if _, err := os.Stat(full + ".gz"); err == nil {
			c.Header("Content-Encoding", "gzip")
			c.Header("Vary", "Accept-Encoding")
			switch filepath.Ext(rel) {
			case ".js":
				c.Header("Content-Type", "application/javascript; charset=utf-8")
			case ".css":
				c.Header("Content-Type", "text/css; charset=utf-8")
			case ".svg":
				c.Header("Content-Type", "image/svg+xml")
			}
			c.File(full + ".gz")
			return
		}
	}
	c.File(full)
}
