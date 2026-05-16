package handler

import (
	"encoding/json"
	"io"
	"net/http"
	"strings"

	"github.com/gin-gonic/gin"

	"github.com/agent-platform/internal/model"
)

// AdminHandler proxies admin requests to the Python agent service
type AdminHandler struct {
	agentURL string
}

func NewAdminHandler(agentURL string) *AdminHandler {
	return &AdminHandler{agentURL: agentURL}
}

func (h *AdminHandler) ListProviders(c *gin.Context) {
	url := strings.TrimRight(h.agentURL, "/") + "/api/v1/admin/providers"
	req, _ := http.NewRequestWithContext(c.Request.Context(), "GET", url, nil)
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		c.JSON(http.StatusBadGateway, gin.H{"error": err.Error()})
		return
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(resp.Body)

	var providers []model.LlmProvider
	json.Unmarshal(body, &providers)
	if providers == nil {
		providers = []model.LlmProvider{}
	}

	// Separate static (built-in) vs dynamic providers
	staticCount := 0
	for _, p := range providers {
		if p.IsStatic {
			staticCount++
		}
	}

	c.JSON(http.StatusOK, gin.H{
		"providers":    providers,
		"static_count": staticCount,
		"dynamic_count": len(providers) - staticCount,
	})
}

func (h *AdminHandler) AddProvider(c *gin.Context) {
	h.proxyToAgent(c, "POST", "/providers")
}

func (h *AdminHandler) UpdateProvider(c *gin.Context) {
	id := c.Param("id")
	h.proxyToAgent(c, "PUT", "/providers/"+id)
}

func (h *AdminHandler) DeleteProvider(c *gin.Context) {
	id := c.Param("id")
	h.proxyToAgent(c, "DELETE", "/providers/"+id)
}

func (h *AdminHandler) proxyToAgent(c *gin.Context, method, path string) {
	url := strings.TrimRight(h.agentURL, "/") + "/api/v1/admin" + path
	req, err := http.NewRequestWithContext(c.Request.Context(), method, url, c.Request.Body)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	req.Header.Set("Content-Type", "application/json")
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		c.JSON(http.StatusBadGateway, gin.H{"error": err.Error()})
		return
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(resp.Body)
	c.Data(resp.StatusCode, "application/json", body)
}
