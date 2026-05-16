package store

import (
	"encoding/json"
	"time"

	"github.com/agent-platform/internal/model"
)

func (s *Store) CreateMessage(conversationID int64, role, content string, toolCalls json.RawMessage, tokenCount int) (*model.Message, error) {
	now := time.Now()
	tcJSON := string(toolCalls)
	if tcJSON == "" {
		tcJSON = "null"
	}

	result, err := s.DB.Exec(
		`INSERT INTO messages (conversation_id, role, content, tool_calls, token_count, created_at)
		 VALUES (?, ?, ?, ?, ?, ?)`,
		conversationID, role, content, tcJSON, tokenCount, now,
	)
	if err != nil {
		return nil, err
	}
	id, _ := result.LastInsertId()

	_, _ = s.DB.Exec(`UPDATE conversations SET updated_at = ? WHERE id = ?`, now, conversationID)

	return &model.Message{
		ID: id, ConversationID: conversationID, Role: role, Content: content,
		ToolCalls: toolCalls, TokenCount: tokenCount, CreatedAt: now,
	}, nil
}

func (s *Store) ListMessages(conversationID int64, limit int) ([]*model.Message, error) {
	if limit <= 0 {
		limit = 100
	}
	rows, err := s.DB.Query(
		`SELECT id, conversation_id, role, content, tool_calls, token_count, created_at
		 FROM messages WHERE conversation_id = ? ORDER BY created_at ASC LIMIT ?`,
		conversationID, limit,
	)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var msgs []*model.Message
	for rows.Next() {
		msg := &model.Message{}
		var createdAt string
		var toolCallsStr string
		if err := rows.Scan(&msg.ID, &msg.ConversationID, &msg.Role, &msg.Content,
			&toolCallsStr, &msg.TokenCount, &createdAt); err != nil {
			return nil, err
		}
		msg.CreatedAt, _ = parseTime(createdAt)
		if toolCallsStr != "" && toolCallsStr != "null" {
			msg.ToolCalls = json.RawMessage(toolCallsStr)
		}
		msgs = append(msgs, msg)
	}
	return msgs, nil
}

func (s *Store) ClearMessages(conversationID int64) error {
	_, err := s.DB.Exec(`DELETE FROM messages WHERE conversation_id = ?`, conversationID)
	return err
}

func (s *Store) CountMessages(conversationID int64) (int, error) {
	var count int
	err := s.DB.QueryRow(
		`SELECT COUNT(*) FROM messages WHERE conversation_id = ?`, conversationID,
	).Scan(&count)
	return count, err
}
