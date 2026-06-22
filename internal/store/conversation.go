package store

import (
	"strings"
	"time"
	"unicode"
	"unicode/utf8"

	"github.com/agent-platform/internal/model"
)

func cleanConversationTitle(title string) string {
	title = strings.TrimSpace(title)
	title = strings.TrimPrefix(title, "[智能搜索 / GraphRAG]")
	title = strings.TrimSpace(title)
	title = strings.ReplaceAll(title, "\r", " ")
	title = strings.ReplaceAll(title, "\n", " ")
	title = strings.Join(strings.FieldsFunc(title, unicode.IsControl), " ")
	title = strings.Join(strings.Fields(title), " ")
	if title == "" || !utf8.ValidString(title) || looksCorruptedTitle(title) {
		return "新对话"
	}
	runes := []rune(title)
	if len(runes) > 50 {
		return string(runes[:50]) + "..."
	}
	return title
}

func looksCorruptedTitle(title string) bool {
	runes := []rune(title)
	if len(runes) == 0 {
		return true
	}
	bad := 0
	for _, r := range runes {
		if r == '\uFFFD' || r == '?' {
			bad++
		}
	}
	return bad >= 3 && bad*2 >= len(runes)
}

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
	title = cleanConversationTitle(title)
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
	title = cleanConversationTitle(title)
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
