package agent

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"

	"github.com/agent-platform/internal/model"
	"github.com/agent-platform/pkg/config"
)

type Client struct {
	baseURL    string
	httpClient *http.Client
}

func NewClient(cfg *config.Config) *Client {
	return &Client{
		baseURL: cfg.Agent.ServiceURL,
		httpClient: &http.Client{
			Timeout: 0, // No total timeout for SSE streaming; uses context cancellation
			Transport: &http.Transport{
				ResponseHeaderTimeout: 30 * time.Second,
				IdleConnTimeout:       90 * time.Second,
			},
		},
	}
}

type agentChatRequest struct {
	Message        string     `json:"message"`
	SessionID      string     `json:"session_id"`
	UserID         int64      `json:"user_id"`
	ConversationID int64      `json:"conversation_id"`
	ProviderID     string     `json:"provider_id,omitempty"`
	Model          string     `json:"model,omitempty"`
	SkillName      string     `json:"skill_name,omitempty"`
	Messages       []AgentMsg `json:"messages,omitempty"`
	// Tools in OpenAI function-calling format
	Tools          interface{} `json:"tools,omitempty"`
}

type AgentMsg struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

func (c *Client) StreamChat(
	ctx context.Context,
	req *model.ChatRequest,
	userID int64,
	convID int64,
	history []AgentMsg,
	tools interface{},
) (<-chan model.StreamEvent, <-chan error) {
	eventCh := make(chan model.StreamEvent, 100)
	errCh := make(chan error, 1)

	go func() {
		defer close(eventCh)
		defer close(errCh)

		agentReq := agentChatRequest{
			Message:        req.Message,
			SessionID:      fmt.Sprintf("%d", convID),
			UserID:         userID,
			ConversationID: convID,
			ProviderID:     req.ProviderID,
			Model:          req.Model,
			SkillName:      req.SkillName,
			Messages:       history,
			Tools:          tools,
		}

		body, err := json.Marshal(agentReq)
		if err != nil {
			errCh <- fmt.Errorf("marshal request: %w", err)
			return
		}

		httpReq, err := http.NewRequestWithContext(ctx, "POST",
			fmt.Sprintf("%s/api/v1/agent/chat/stream", c.baseURL), bytes.NewReader(body))
		if err != nil {
			errCh <- fmt.Errorf("create request: %w", err)
			return
		}
		httpReq.Header.Set("Content-Type", "application/json")
		httpReq.Header.Set("Accept", "text/event-stream")

		resp, err := c.httpClient.Do(httpReq)
		if err != nil {
			errCh <- fmt.Errorf("agent call failed: %w", err)
			return
		}
		defer resp.Body.Close()

		if resp.StatusCode != http.StatusOK {
			respBody, _ := io.ReadAll(resp.Body)
			errCh <- fmt.Errorf("agent returned %d: %s", resp.StatusCode, string(respBody))
			return
		}

		reader := bufio.NewReader(resp.Body)
		for {
			line, err := reader.ReadString('\n')
			if err != nil {
				if err != io.EOF {
					errCh <- fmt.Errorf("read stream: %w", err)
				}
				return
			}

			line = strings.TrimSpace(line)
			if line == "" {
				continue
			}
			if !strings.HasPrefix(line, "data: ") {
				continue
			}

			data := strings.TrimPrefix(line, "data: ")
			if data == "[DONE]" {
				eventCh <- model.StreamEvent{Type: "done", Done: true}
				return
			}

			var event model.StreamEvent
			if err := json.Unmarshal([]byte(data), &event); err != nil {
				eventCh <- model.StreamEvent{
					Type:    "text",
					Content: data,
				}
				continue
			}
			eventCh <- event
		}
	}()

	return eventCh, errCh
}

func (c *Client) InvokeChat(
	ctx context.Context,
	req *model.ChatRequest,
	userID int64,
	convID int64,
	history []AgentMsg,
	tools interface{},
) (string, error) {
	agentReq := agentChatRequest{
		Message:        req.Message,
		SessionID:      fmt.Sprintf("%d", convID),
		UserID:         userID,
		ConversationID: convID,
		ProviderID:     req.ProviderID,
		Model:          req.Model,
		Messages:       history,
		Tools:          tools,
	}

	body, err := json.Marshal(agentReq)
	if err != nil {
		return "", err
	}

	httpReq, err := http.NewRequestWithContext(ctx, "POST",
		fmt.Sprintf("%s/api/v1/agent/chat", c.baseURL), bytes.NewReader(body))
	if err != nil {
		return "", err
	}
	httpReq.Header.Set("Content-Type", "application/json")

	resp, err := c.httpClient.Do(httpReq)
	if err != nil {
		return "", fmt.Errorf("agent call failed: %w", err)
	}
	defer resp.Body.Close()

	var result struct {
		Response string `json:"response"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return "", err
	}
	return result.Response, nil
}

func (c *Client) Health(ctx context.Context) error {
	resp, err := c.httpClient.Get(fmt.Sprintf("%s/health", c.baseURL))
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("agent unhealthy: %d", resp.StatusCode)
	}
	return nil
}
