package handler

import (
	"context"
	"io"
	"net/http"
	"net/url"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
)

// HermesHandler proxies requests to the Hermes Bridge service
type HermesHandler struct {
	hermesURL  string
	timeout    int
	httpClient *http.Client
}

// NewHermesHandler creates a new HermesHandler
func NewHermesHandler(hermesURL string, timeout int) *HermesHandler {
	if timeout <= 0 {
		timeout = 600
	}
	return &HermesHandler{
		hermesURL: hermesURL,
		timeout:   timeout,
		httpClient: &http.Client{
			Timeout: time.Duration(timeout) * time.Second,
			Transport: &http.Transport{
				ResponseHeaderTimeout: time.Duration(timeout) * time.Second,
				IdleConnTimeout:       90 * time.Second,
			},
		},
	}
}

// Health proxy
func (h *HermesHandler) Health(c *gin.Context) {
	url := strings.TrimRight(h.hermesURL, "/") + "/api/v2/health"
	req, _ := http.NewRequestWithContext(c.Request.Context(), "GET", url, nil)
	resp, err := h.httpClient.Do(req)
	if err != nil {
		c.JSON(http.StatusBadGateway, gin.H{"error": err.Error()})
		return
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(resp.Body)
	c.Data(resp.StatusCode, "application/json", body)
}

// Chat proxy (non-streaming)
func (h *HermesHandler) Chat(c *gin.Context) {
	url := strings.TrimRight(h.hermesURL, "/") + "/api/v2/chat"
	req, _ := http.NewRequestWithContext(c.Request.Context(), "POST", url, c.Request.Body)
	req.Header.Set("Content-Type", "application/json")
	resp, err := h.httpClient.Do(req)
	if err != nil {
		c.JSON(http.StatusBadGateway, gin.H{"error": err.Error()})
		return
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(resp.Body)
	c.Data(resp.StatusCode, "application/json", body)
}

// ChatStream proxy (SSE)
func (h *HermesHandler) ChatStream(c *gin.Context) {
	url := strings.TrimRight(h.hermesURL, "/") + "/api/v2/chat/stream"
	req, _ := http.NewRequestWithContext(c.Request.Context(), "POST", url, c.Request.Body)
	req.Header.Set("Content-Type", "application/json")
	resp, err := h.httpClient.Do(req)
	if err != nil {
		c.JSON(http.StatusBadGateway, gin.H{"error": err.Error()})
		return
	}
	defer resp.Body.Close()

	c.Writer.Header().Set("Content-Type", "text/event-stream")
	c.Writer.Header().Set("Cache-Control", "no-cache")
	c.Writer.Header().Set("Connection", "keep-alive")
	c.Writer.Header().Set("X-Accel-Buffering", "no")
	flusher, ok := c.Writer.(http.Flusher)
	if !ok {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "streaming not supported"})
		return
	}

	buf := make([]byte, 4096)
	for {
		n, err := resp.Body.Read(buf)
		if n > 0 {
			c.Writer.Write(buf[:n])
			flusher.Flush()
		}
		if err != nil {
			break
		}
	}
}

func (h *HermesHandler) proxyGet(c *gin.Context, path string) {
	url := strings.TrimRight(h.hermesURL, "/") + path
	req, _ := http.NewRequestWithContext(c.Request.Context(), "GET", url, nil)
	resp, err := h.httpClient.Do(req)
	if err != nil {
		c.JSON(http.StatusBadGateway, gin.H{"error": err.Error()})
		return
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(resp.Body)
	c.Data(resp.StatusCode, "application/json", body)
}

func (h *HermesHandler) proxyPost(c *gin.Context, path string) {
	url := strings.TrimRight(h.hermesURL, "/") + path
	req, _ := http.NewRequestWithContext(c.Request.Context(), "POST", url, c.Request.Body)
	req.Header.Set("Content-Type", "application/json")
	resp, err := h.httpClient.Do(req)
	if err != nil {
		c.JSON(http.StatusBadGateway, gin.H{"error": err.Error()})
		return
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(resp.Body)
	c.Data(resp.StatusCode, "application/json", body)
}

// ListSkills lists all hermes skills
func (h *HermesHandler) ListSkills(c *gin.Context) {
	h.proxyGet(c, "/api/v2/skills")
}

// GetSkill gets a specific hermes skill
func (h *HermesHandler) GetSkill(c *gin.Context) {
	h.proxyGet(c, "/api/v2/skills/"+c.Param("name"))
}

// ExecuteSkill executes a hermes skill
func (h *HermesHandler) ExecuteSkill(c *gin.Context) {
	h.proxyPost(c, "/api/v2/skills/"+c.Param("name")+"/execute")
}

// ListAgents lists available agent workflows
func (h *HermesHandler) ListAgents(c *gin.Context) {
	h.proxyGet(c, "/api/v2/agents")
}

// RunAgent runs a specific agent workflow
func (h *HermesHandler) RunAgent(c *gin.Context) {
	h.proxyPost(c, "/api/v2/agents/"+c.Param("name")+"/run")
}

// Workspace lists workspace projects
func (h *HermesHandler) Workspace(c *gin.Context) {
	h.proxyGet(c, "/api/v2/workspace")
}

// SearchHub searches/browses the Hermes skills hub
func (h *HermesHandler) SearchHub(c *gin.Context) {
	q := c.Query("q")
	path := "/api/v2/skills/hub"
	if q != "" {
		path = "/api/v2/skills/hub?q=" + url.QueryEscape(q)
	}
	h.proxyGet(c, path)
}

// InstallHub installs a skill from the Hermes hub
func (h *HermesHandler) InstallHub(c *gin.Context) {
	h.proxyPost(c, "/api/v2/skills/hub/install")
}

// PassthroughV2 proxies any /api/v2/* request to the hermes bridge.
// Supports streaming (SSE) responses by detecting text/event-stream content type.
func (h *HermesHandler) PassthroughV2(c *gin.Context) {
	path := c.Param("path")
	targetURL := strings.TrimRight(h.hermesURL, "/") + "/api/v2" + path
	if c.Request.URL.RawQuery != "" {
		targetURL += "?" + c.Request.URL.RawQuery
	}

	// Use a context with timeout for non-streaming requests
	ctx, cancel := context.WithTimeout(c.Request.Context(), time.Duration(h.timeout)*time.Second)
	defer cancel()

	req, err := http.NewRequestWithContext(ctx, c.Request.Method, targetURL, c.Request.Body)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := h.httpClient.Do(req)
	if err != nil {
		if ctx.Err() == context.DeadlineExceeded {
			c.JSON(http.StatusGatewayTimeout, gin.H{"error": "hermes bridge request timed out"})
			return
		}
		c.JSON(http.StatusBadGateway, gin.H{"error": err.Error()})
		return
	}
	defer resp.Body.Close()

	contentType := resp.Header.Get("Content-Type")
	if strings.Contains(contentType, "text/event-stream") {
		c.Writer.Header().Set("Content-Type", "text/event-stream")
		c.Writer.Header().Set("Cache-Control", "no-cache")
		c.Writer.Header().Set("Connection", "keep-alive")
		c.Writer.Header().Set("X-Accel-Buffering", "no")

		flusher, ok := c.Writer.(http.Flusher)
		if !ok {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "streaming not supported"})
			return
		}

		buf := make([]byte, 4096)
		for {
			n, readErr := resp.Body.Read(buf)
			if n > 0 {
				if _, writeErr := c.Writer.Write(buf[:n]); writeErr != nil {
					return
				}
				flusher.Flush()
			}
			if readErr != nil {
				break
			}
		}
	} else {
		for key, values := range resp.Header {
			for _, v := range values {
				c.Header(key, v)
			}
		}
		body, _ := io.ReadAll(resp.Body)
		c.Data(resp.StatusCode, contentType, body)
	}
}
