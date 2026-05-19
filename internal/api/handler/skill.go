package handler

import (
	"io"
	"net/http"
	"strings"

	"github.com/gin-gonic/gin"
)

// SkillHandler proxies skill requests to the Python agent service
type SkillHandler struct {
	agentURL string
	client   *http.Client
}

func NewSkillHandler(agentURL string) *SkillHandler {
	return &SkillHandler{
		agentURL: agentURL,
		client:   &http.Client{},
	}
}

func (h *SkillHandler) proxy(c *gin.Context, method, path string, body io.Reader) {
	url := strings.TrimRight(h.agentURL, "/") + "/api/v1/skills" + path
	req, err := http.NewRequestWithContext(c.Request.Context(), method, url, body)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := h.client.Do(req)
	if err != nil {
		c.JSON(http.StatusBadGateway, gin.H{"error": "技能服务不可用: " + err.Error()})
		return
	}
	defer resp.Body.Close()

	respBody, _ := io.ReadAll(resp.Body)
	c.Data(resp.StatusCode, "application/json", respBody)
}

func (h *SkillHandler) List(c *gin.Context) {
	h.proxy(c, "GET", "", nil)
}

func (h *SkillHandler) Get(c *gin.Context) {
	name := c.Param("name")
	h.proxy(c, "GET", "/"+name, nil)
}

func (h *SkillHandler) Add(c *gin.Context) {
	h.proxy(c, "POST", "", c.Request.Body)
}

func (h *SkillHandler) ImportGithub(c *gin.Context) {
	h.proxy(c, "POST", "/import/github", c.Request.Body)
}

func (h *SkillHandler) Remove(c *gin.Context) {
	name := c.Param("name")
	h.proxy(c, "DELETE", "/"+name, nil)
}

func (h *SkillHandler) Enable(c *gin.Context) {
	name := c.Param("name")
	h.proxy(c, "POST", "/"+name+"/enable", nil)
}

func (h *SkillHandler) Disable(c *gin.Context) {
	name := c.Param("name")
	h.proxy(c, "POST", "/"+name+"/disable", nil)
}

// Update skill metadata (PUT)
func (h *SkillHandler) Update(c *gin.Context) {
	name := c.Param("name")
	h.proxy(c, "PUT", "/"+name, c.Request.Body)
}

// Upload a zip skill package — passthrough multipart
func (h *SkillHandler) Upload(c *gin.Context) {
	url := strings.TrimRight(h.agentURL, "/") + "/api/v1/skills/upload"
	req, err := http.NewRequestWithContext(c.Request.Context(), "POST", url, c.Request.Body)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	req.Header.Set("Content-Type", c.GetHeader("Content-Type"))
	req.ContentLength = c.Request.ContentLength

	resp, err := h.client.Do(req)
	if err != nil {
		c.JSON(http.StatusBadGateway, gin.H{"error": "技能服务不可用: " + err.Error()})
		return
	}
	defer resp.Body.Close()

	respBody, _ := io.ReadAll(resp.Body)
	c.Data(resp.StatusCode, "application/json", respBody)
}
