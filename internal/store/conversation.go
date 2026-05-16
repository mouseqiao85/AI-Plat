package store

import (
	"strings"
	"time"

	"github.com/agent-platform/internal/model"
)

// parseTime parses a SQLite timestamp that may include Go's monotonic clock suffix.
func parseTime(s string) (time.Time, error) {
	// Strip Go monotonic clock suffix: " m=+..."
	if idx := strings.Index(s, " m="); idx != -1 {
		s = s[:idx]
	}
	// Try formats from most to least specific
	formats := []string{
		"2006-01-02 15:04:05.9999999 -0700 MST",
		"2006-01-02 15:04:05.9999999 -0700",
		"2006-01-02 15:04:05",
		time.RFC3339Nano,
		time.RFC3339,
	}
	for _, f := range formats {
		if t, err := time.Parse(f, s); err == nil {
			return t, nil
		}
	}
	return time.Time{}, nil
}

func (s *Store) CreateConversation(userID int64, title string) (*model.Conversation, error) {
	if title == "" {
		title = "新对话"
	}
	now := time.Now()
	result, err := s.DB.Exec(
		`INSERT INTO conversations (user_id, title, created_at, updated_at) VALUES (?, ?, ?, ?)`,
		userID, title, now, now,
	)
	if err != nil {
		return nil, err
	}
	id, _ := result.LastInsertId()
	return &model.Conversation{ID: id, UserID: userID, Title: title, CreatedAt: now, UpdatedAt: now}, nil
}

func (s *Store) GetConversation(id int64) (*model.Conversation, error) {
	conv := &model.Conversation{}
	var createdAt, updatedAt string
	err := s.DB.QueryRow(
		`SELECT id, user_id, title, created_at, updated_at FROM conversations WHERE id = ?`, id,
	).Scan(&conv.ID, &conv.UserID, &conv.Title, &createdAt, &updatedAt)
	if err != nil {
		return nil, err
	}
	conv.CreatedAt, _ = parseTime(createdAt)
	conv.UpdatedAt, _ = parseTime(updatedAt)
	return conv, nil
}

func (s *Store) ListConversations(userID int64, limit int) ([]*model.Conversation, error) {
	if limit <= 0 {
		limit = 50
	}
	rows, err := s.DB.Query(
		`SELECT id, user_id, title, created_at, updated_at FROM conversations
		 WHERE user_id = ? ORDER BY updated_at DESC LIMIT ?`, userID, limit,
	)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var convs []*model.Conversation
	for rows.Next() {
		conv := &model.Conversation{}
		var createdAt, updatedAt string
		if err := rows.Scan(&conv.ID, &conv.UserID, &conv.Title, &createdAt, &updatedAt); err != nil {
			return nil, err
		}
		conv.CreatedAt, _ = parseTime(createdAt)
		conv.UpdatedAt, _ = parseTime(updatedAt)
		convs = append(convs, conv)
	}
	return convs, nil
}

func (s *Store) UpdateConversationTitle(id int64, title string) error {
	_, err := s.DB.Exec(
		`UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?`,
		title, time.Now(), id,
	)
	return err
}

func (s *Store) DeleteConversation(id int64) error {
	_, err := s.DB.Exec(`DELETE FROM messages WHERE conversation_id = ?`, id)
	if err != nil {
		return err
	}
	_, err = s.DB.Exec(`DELETE FROM conversations WHERE id = ?`, id)
	return err
}

func (s *Store) DeleteAllConversations(userID int64) (int64, error) {
	// Delete all messages for this user's conversations
	_, err := s.DB.Exec(
		`DELETE FROM messages WHERE conversation_id IN (SELECT id FROM conversations WHERE user_id = ?)`,
		userID,
	)
	if err != nil {
		return 0, err
	}
	// Delete all conversations
	result, err := s.DB.Exec(`DELETE FROM conversations WHERE user_id = ?`, userID)
	if err != nil {
		return 0, err
	}
	return result.RowsAffected()
}
