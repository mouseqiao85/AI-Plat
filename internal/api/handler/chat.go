package handler

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strconv"
	"time"

	"github.com/gin-gonic/gin"

	"github.com/agent-platform/internal/api/middleware"
	"github.com/agent-platform/internal/model"
	"github.com/agent-platform/internal/service/agent"
	"github.com/agent-platform/internal/service/tool"
	"github.com/agent-platform/internal/store"
	"github.com/agent-platform/pkg/config"
)

type ChatHandler struct {
	store    *store.Store
	agentCli *agent.Client
	registry *tool.Registry
	cfg      *config.Config
}

func NewChatHandler(db *store.Store, registry *tool.Registry, cfg *config.Config) *ChatHandler {
	return &ChatHandler{
		store:    db,
		agentCli: agent.NewClient(cfg),
		registry: registry,
		cfg:      cfg,
	}
}

func (h *ChatHandler) Chat(c *gin.Context) {
	var req model.ChatRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "请求参数无效"})
		return
	}

	if req.Message == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "消息不能为空"})
		return
	}

	userID := middleware.GetUserID(c)

	convID := req.ConversationID
	if convID == 0 {
		title := req.Message
		if len([]rune(title)) > 50 {
			title = string([]rune(title)[:50]) + "..."
		}
		conv, err := h.store.CreateConversation(userID, title)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "创建会话失败"})
			return
		}
		convID = conv.ID
		// Send conversation_id to frontend
		c.Writer.Header().Set("Content-Type", "text/event-stream")
		c.Writer.Header().Set("Cache-Control", "no-cache")
		c.Writer.Header().Set("Connection", "keep-alive")
		c.Writer.Header().Set("X-Accel-Buffering", "no")
		flusher, ok := c.Writer.(http.Flusher)
		if !ok {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "不支持流式输出"})
			return
		}
		fmt.Fprintf(c.Writer, "event: conversation_id\ndata: {\"conversation_id\":%d}\n\n", convID)
		flusher.Flush()
	} else {
		if _, err := h.store.GetConversation(convID); err != nil {
			c.JSON(http.StatusNotFound, gin.H{"error": "会话不存在"})
			return
		}
	}

	messages, err := h.store.ListMessages(convID, 50)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "加载消息失败"})
		return
	}

	var history []agent.AgentMsg
	for _, msg := range messages {
		history = append(history, agent.AgentMsg{
			Role:    msg.Role,
			Content: msg.Content,
		})
	}

	// Set headers only if not already set (for new conversations)
	if req.ConversationID != 0 {
		c.Writer.Header().Set("Content-Type", "text/event-stream")
		c.Writer.Header().Set("Cache-Control", "no-cache")
		c.Writer.Header().Set("Connection", "keep-alive")
		c.Writer.Header().Set("X-Accel-Buffering", "no")
	}

	type sseWriter interface {
		Write([]byte) (int, error)
		Flush()
	}
	flusher, ok := c.Writer.(http.Flusher)
	if !ok {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "不支持流式输出"})
		return
	}

	_, _ = h.store.CreateMessage(convID, "user", req.Message, nil, 0)

	done := make(chan struct{})
	heartbeat := time.NewTicker(15 * time.Second)
	defer heartbeat.Stop()

	go func() {
		for {
			select {
			case <-heartbeat.C:
				fmt.Fprintf(c.Writer, "event: ping\ndata: {}\n\n")
				flusher.Flush()
			case <-done:
				return
			}
		}
	}()

	// Include skill_name in the request to Python agent
	if req.SkillName != "" {
		_ = req.SkillName // passed through to agent via req object
	}

	tools := h.registry.GetOpenAITools()
	eventCh, errCh := h.agentCli.StreamChat(c.Request.Context(), &req, userID, convID, history, tools)

	convTitleSet := false
	isStreamDone := false
	var fullResponse string
	hasError := false

	for {
		select {
		case event, ok := <-eventCh:
			if !ok {
				close(done)
				// Channel closed without a terminal event — save and send done
				if !hasError && !isStreamDone {
					if fullResponse != "" {
						_, _ = h.store.CreateMessage(convID, "assistant", fullResponse, nil, 0)
					}
					fmt.Fprintf(c.Writer, "event: done\ndata: {\"conversation_id\":%d,\"done\":true}\n\n", convID)
					flusher.Flush()
				}
				return
			}

			// Transform Python agent SSE events to frontend-compatible format
			h.writeSSEEvent(c.Writer, flusher, event, convID, &fullResponse, &convTitleSet, &isStreamDone)

		case err, ok := <-errCh:
			if ok && err != nil {
				hasError = true
				errData, _ := json.Marshal(map[string]string{"message": err.Error()})
				fmt.Fprintf(c.Writer, "event: error\ndata: %s\n\n", string(errData))
				flusher.Flush()
			}
			close(done)
			return

		case <-c.Request.Context().Done():
			close(done)
			return
		}
	}
}

// writeSSEEvent transforms a StreamEvent from the Python agent and writes it as SSE
func (h *ChatHandler) writeSSEEvent(w http.ResponseWriter, flusher http.Flusher, event model.StreamEvent, convID int64, fullResponse *string, titleSet *bool, streamDone *bool) {
	switch event.Type {
	case "text":
		*fullResponse += event.Content
		if !*titleSet && len([]rune(*fullResponse)) > 10 {
			title := string([]rune(*fullResponse)[:30])
			_ = h.store.UpdateConversationTitle(convID, title)
			*titleSet = true
		}
		data, _ := json.Marshal(map[string]string{"text": event.Content})
		fmt.Fprintf(w, "event: text\ndata: %s\n\n", string(data))

	case "thinking":
		fmt.Fprintf(w, "event: thinking\ndata: {}\n\n")

	case "tool_progress":
		// Map to tool_call event
		data, _ := json.Marshal(map[string]interface{}{
			"name":   event.ToolName,
			"status": "running",
		})
		fmt.Fprintf(w, "event: tool_call\ndata: %s\n\n", string(data))

	case "tool_call":
		status := "running"
		if event.Status != "" {
			status = event.Status
		}
		data, _ := json.Marshal(map[string]interface{}{
			"name":      event.ToolName,
			"tool_args": event.ToolArgs,
			"status":    status,
		})
		fmt.Fprintf(w, "event: tool_call\ndata: %s\n\n", string(data))

	case "tool_result":
		success := event.Success
		data, _ := json.Marshal(map[string]interface{}{
			"result":  event.Result,
			"success": success,
		})
		fmt.Fprintf(w, "event: tool_result\ndata: %s\n\n", string(data))

	case "notice":
		raw, _ := json.Marshal(event)
		fmt.Fprintf(w, "event: notice\ndata: %s\n\n", string(raw))

	case "card":
		raw, _ := json.Marshal(event)
		fmt.Fprintf(w, "event: card\ndata: %s\n\n", string(raw))

	case "plan_created":
		raw, _ := json.Marshal(event)
		fmt.Fprintf(w, "event: plan_created\ndata: %s\n\n", string(raw))

	case "plan_step_update":
		raw, _ := json.Marshal(event)
		fmt.Fprintf(w, "event: plan_step_update\ndata: %s\n\n", string(raw))

	case "worker_started":
		raw, _ := json.Marshal(event)
		fmt.Fprintf(w, "event: worker_started\ndata: %s\n\n", string(raw))

	case "worker_progress":
		raw, _ := json.Marshal(event)
		fmt.Fprintf(w, "event: worker_progress\ndata: %s\n\n", string(raw))

	case "worker_done":
		raw, _ := json.Marshal(event)
		fmt.Fprintf(w, "event: worker_done\ndata: %s\n\n", string(raw))

	case "file_download":
		raw, _ := json.Marshal(event)
		fmt.Fprintf(w, "event: file_download\ndata: %s\n\n", string(raw))

	case "compact_start", "compact_done":
		// Suppress compact events from reaching the client
		return

	case "error":
		errData, _ := json.Marshal(map[string]string{"message": event.Error})
		fmt.Fprintf(w, "event: error\ndata: %s\n\n", string(errData))

	case "done":
		*streamDone = true
		if *fullResponse != "" {
			_, _ = h.store.CreateMessage(convID, "assistant", *fullResponse, nil, 0)
		}
		fmt.Fprintf(w, "event: done\ndata: {\"conversation_id\":%d,\"done\":true}\n\n", convID)

	default:
		// Pass through unknown events
		raw, _ := json.Marshal(event)
		fmt.Fprintf(w, "event: %s\ndata: %s\n\n", event.Type, string(raw))
	}
	flusher.Flush()
}

/* ── Conversations ── */

func (h *ChatHandler) Conversations(c *gin.Context) {
	userID := middleware.GetUserID(c)
	convs, err := h.store.ListConversations(userID, 50)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "获取会话列表失败"})
		return
	}
	if convs == nil {
		convs = []*model.Conversation{}
	}
	c.JSON(http.StatusOK, convs)
}

func (h *ChatHandler) GetMessages(c *gin.Context) {
	idStr := c.Param("id")
	convID, err := strconv.ParseInt(idStr, 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "无效的会话ID"})
		return
	}

	if _, err := h.store.GetConversation(convID); err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "会话不存在"})
		return
	}

	msgs, err := h.store.ListMessages(convID, 100)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "获取消息失败"})
		return
	}
	if msgs == nil {
		msgs = []*model.Message{}
	}
	c.JSON(http.StatusOK, msgs)
}

func (h *ChatHandler) RenameConversation(c *gin.Context) {
	idStr := c.Param("id")
	convID, err := strconv.ParseInt(idStr, 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "无效的会话ID"})
		return
	}

	var req struct {
		Title string `json:"title"`
	}
	if err := c.ShouldBindJSON(&req); err != nil || req.Title == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "请提供标题"})
		return
	}

	if err := h.store.UpdateConversationTitle(convID, req.Title); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "重命名失败"})
		return
	}

	conv, _ := h.store.GetConversation(convID)
	c.JSON(http.StatusOK, conv)
}

func (h *ChatHandler) DeleteConversation(c *gin.Context) {
	idStr := c.Param("id")
	convID, err := strconv.ParseInt(idStr, 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "无效的会话ID"})
		return
	}

	if err := h.store.DeleteConversation(convID); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "删除失败"})
		return
	}

	c.Status(http.StatusNoContent)
}

func (h *ChatHandler) ClearConversationMessages(c *gin.Context) {
	idStr := c.Param("id")
	convID, err := strconv.ParseInt(idStr, 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "无效的会话ID"})
		return
	}

	if err := h.store.ClearMessages(convID); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "清除失败"})
		return
	}

	c.Status(http.StatusNoContent)
}

func (h *ChatHandler) GetUserProfile(c *gin.Context) {
	userID := middleware.GetUserID(c)

	// Get local user info
	user, err := h.store.GetUserByID(userID)
	if err != nil || user == nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "用户不存在"})
		return
	}

	profile := gin.H{
		"id":       user.ID,
		"username": user.Username,
		"nickname": user.Nickname,
		"tier":     user.Tier,
		"role":     user.Role,
	}

	// Try to get extended profile from Python agent memory
	url := h.cfg.Agent.ServiceURL + "/api/v1/memory/profile/" + strconv.FormatInt(userID, 10)
	req, _ := http.NewRequestWithContext(c.Request.Context(), "GET", url, nil)
	if resp, err := http.DefaultClient.Do(req); err == nil {
		defer resp.Body.Close()
		var memProfile map[string]interface{}
		if json.NewDecoder(resp.Body).Decode(&memProfile) == nil {
			profile["memory"] = memProfile
		}
	}

	c.JSON(http.StatusOK, gin.H{"profile": profile})
}

func (h *ChatHandler) ClearUserProfile(c *gin.Context) {
	userID := middleware.GetUserID(c)

	// Clear from Python agent memory
	url := h.cfg.Agent.ServiceURL + "/api/v1/memory/profile/" + strconv.FormatInt(userID, 10)
	req, _ := http.NewRequestWithContext(c.Request.Context(), "DELETE", url, nil)
	resp, err := http.DefaultClient.Do(req)
	if err == nil {
		resp.Body.Close()
	}

	c.JSON(http.StatusOK, gin.H{"status": "cleared"})
}

func (h *ChatHandler) DeleteAllConversations(c *gin.Context) {
	userID := middleware.GetUserID(c)
	count, err := h.store.DeleteAllConversations(userID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "清空失败"})
		return
	}
	c.JSON(http.StatusOK, gin.H{"deleted": count})
}

func (h *ChatHandler) Providers(c *gin.Context) {
	url := h.cfg.Agent.ServiceURL + "/api/v1/admin/providers"
	req, err := http.NewRequestWithContext(c.Request.Context(), "GET", url, nil)
	if err != nil {
		c.JSON(http.StatusOK, gin.H{"providers": []gin.H{}})
		return
	}
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		c.JSON(http.StatusOK, gin.H{"providers": []gin.H{}})
		return
	}
	defer resp.Body.Close()

	var providers []map[string]interface{}
	json.NewDecoder(resp.Body).Decode(&providers)
	if providers == nil {
		providers = []map[string]interface{}{}
	}

	c.JSON(http.StatusOK, gin.H{"providers": providers})
}
