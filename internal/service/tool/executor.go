package tool

import (
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
)

type ExecutorHandler struct {
	registry *Registry
	timeout  time.Duration
}

func NewExecutorHandler(registry *Registry, timeoutSec int) *ExecutorHandler {
	return &ExecutorHandler{
		registry: registry,
		timeout:  time.Duration(timeoutSec) * time.Second,
	}
}

type ExecuteRequest struct {
	ToolName  string                 `json:"tool_name" binding:"required"`
	Arguments map[string]interface{} `json:"arguments"`
	SessionID string                 `json:"session_id"`
}

func (h *ExecutorHandler) Execute(c *gin.Context) {
	var req ExecuteRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "参数无效", "success": false})
		return
	}

	resultCh := make(chan executeResult, 1)
	go func() {
		result, err := h.registry.Execute(req.ToolName, req.Arguments)
		resultCh <- executeResult{Result: result, Err: err}
	}()

	select {
	case res := <-resultCh:
		if res.Err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{
				"error":   res.Err.Error(),
				"success": false,
			})
			return
		}
		c.JSON(http.StatusOK, gin.H{
			"result":  res.Result,
			"success": true,
		})
	case <-time.After(h.timeout):
		c.JSON(http.StatusGatewayTimeout, gin.H{
			"error":   "工具执行超时",
			"success": false,
		})
	}
}

func (h *ExecutorHandler) List(c *gin.Context) {
	tools := h.registry.List()
	c.JSON(http.StatusOK, gin.H{"tools": tools})
}

type executeResult struct {
	Result interface{}
	Err    error
}
