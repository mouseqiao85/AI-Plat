package handler

import (
	"io"
	"net/http"
	"strings"

	"github.com/gin-gonic/gin"
)

// KnowledgeGraphHandler proxies knowledge graph requests to the Python agent service.
type KnowledgeGraphHandler struct {
	agentURL string
	client   *http.Client
}

func NewKnowledgeGraphHandler(agentURL string) *KnowledgeGraphHandler {
	return &KnowledgeGraphHandler{
		agentURL: agentURL,
		client:   &http.Client{},
	}
}

func (h *KnowledgeGraphHandler) proxy(c *gin.Context) {
	path := c.Param("path")
	url := strings.TrimRight(h.agentURL, "/") + "/api/v1/knowledge-graph" + path
	if c.Request.URL.RawQuery != "" {
		url += "?" + c.Request.URL.RawQuery
	}

	req, err := http.NewRequestWithContext(c.Request.Context(), c.Request.Method, url, c.Request.Body)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	contentType := c.GetHeader("Content-Type")
	if contentType != "" {
		req.Header.Set("Content-Type", contentType)
	} else {
		req.Header.Set("Content-Type", "application/json")
	}
	req.ContentLength = c.Request.ContentLength

	resp, err := h.client.Do(req)
	if err != nil {
		c.JSON(http.StatusBadGateway, gin.H{"error": "知识图谱服务不可用: " + err.Error()})
		return
	}
	defer resp.Body.Close()

	for key, values := range resp.Header {
		for _, value := range values {
			c.Header(key, value)
		}
	}
	respBody, _ := io.ReadAll(resp.Body)
	responseType := resp.Header.Get("Content-Type")
	if responseType == "" {
		responseType = "application/json"
	}
	c.Data(resp.StatusCode, responseType, respBody)
}

func (h *KnowledgeGraphHandler) Passthrough(c *gin.Context) {
	h.proxy(c)
}
