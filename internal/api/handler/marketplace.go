package handler

import (
	"net/http"
	"strconv"

	"github.com/gin-gonic/gin"

	"github.com/agent-platform/internal/api/middleware"
	"github.com/agent-platform/internal/model"
	"github.com/agent-platform/internal/store"
)

type MarketHandler struct {
	store *store.Store
}

func NewMarketHandler(db *store.Store) *MarketHandler {
	return &MarketHandler{store: db}
}

// GET /marketplace/agents?category=&page=1&pageSize=50
func (h *MarketHandler) ListAgents(c *gin.Context) {
	category := c.Query("category")
	page, _ := strconv.Atoi(c.DefaultQuery("page", "1"))
	pageSize, _ := strconv.Atoi(c.DefaultQuery("pageSize", "50"))

	agents, total, err := h.store.ListMarketAgents(category, page, pageSize)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "获取列表失败"})
		return
	}
	if agents == nil {
		agents = []*model.MarketAgent{}
	}
	c.JSON(http.StatusOK, gin.H{
		"agents":   agents,
		"total":    total,
		"page":     page,
		"pageSize": pageSize,
	})
}

// GET /marketplace/agents/:id
func (h *MarketHandler) GetAgent(c *gin.Context) {
	id, err := strconv.ParseInt(c.Param("id"), 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "无效ID"})
		return
	}
	agent, err := h.store.GetMarketAgent(id)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "智能体不存在"})
		return
	}
	c.JSON(http.StatusOK, agent)
}

// POST /marketplace/agents
func (h *MarketHandler) CreateAgent(c *gin.Context) {
	var req model.MarketAgentCreate
	if err := c.ShouldBindJSON(&req); err != nil || req.Title == "" || req.Category == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "标题和分类为必填项"})
		return
	}
	userID := middleware.GetUserID(c)
	agent, err := h.store.CreateMarketAgent(userID, &req)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "创建失败"})
		return
	}
	c.JSON(http.StatusCreated, agent)
}

// PATCH /marketplace/agents/:id
func (h *MarketHandler) UpdateAgent(c *gin.Context) {
	id, err := strconv.ParseInt(c.Param("id"), 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "无效ID"})
		return
	}
	if _, err := h.store.GetMarketAgent(id); err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "智能体不存在"})
		return
	}
	var req model.MarketAgentUpdate
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "参数无效"})
		return
	}
	agent, err := h.store.UpdateMarketAgent(id, &req)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "更新失败"})
		return
	}
	c.JSON(http.StatusOK, agent)
}

// DELETE /marketplace/agents/:id
func (h *MarketHandler) DeleteAgent(c *gin.Context) {
	id, err := strconv.ParseInt(c.Param("id"), 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "无效ID"})
		return
	}
	if err := h.store.DeleteMarketAgent(id); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "删除失败"})
		return
	}
	c.Status(http.StatusNoContent)
}
