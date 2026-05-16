package store

import (
	"os"
	"testing"
)

func TestNewStore(t *testing.T) {
	dbPath := "test_data/test_store.db"
	defer os.RemoveAll("test_data")

	s, err := NewStore(dbPath + "?_journal_mode=WAL")
	if err != nil {
		t.Fatalf("NewStore failed: %v", err)
	}
	defer s.Close()

	if s.DB == nil {
		t.Fatal("DB is nil")
	}
}

func TestCreateAndGetUser(t *testing.T) {
	dbPath := "test_data/test_user.db"
	defer os.RemoveAll("test_data")

	s, err := NewStore(dbPath + "?_journal_mode=WAL")
	if err != nil {
		t.Fatalf("NewStore failed: %v", err)
	}
	defer s.Close()

	user, err := s.CreateUser("testuser", "hashed_password")
	if err != nil {
		t.Fatalf("CreateUser failed: %v", err)
	}
	if user.ID == 0 {
		t.Fatal("user ID is 0")
	}
	if user.Username != "testuser" {
		t.Errorf("expected username=testuser, got %s", user.Username)
	}

	fetched, err := s.GetUserByUsername("testuser")
	if err != nil {
		t.Fatalf("GetUserByUsername failed: %v", err)
	}
	if fetched == nil {
		t.Fatal("user not found")
	}
	if fetched.ID != user.ID {
		t.Errorf("ID mismatch: %d vs %d", fetched.ID, user.ID)
	}
}

func TestCreateConversation(t *testing.T) {
	dbPath := "test_data/test_conv.db"
	defer os.RemoveAll("test_data")

	s, err := NewStore(dbPath + "?_journal_mode=WAL")
	if err != nil {
		t.Fatalf("NewStore failed: %v", err)
	}
	defer s.Close()

	user, _ := s.CreateUser("convuser", "hash")
	conv, err := s.CreateConversation(user.ID, "测试会话")
	if err != nil {
		t.Fatalf("CreateConversation failed: %v", err)
	}
	if conv.ID == 0 {
		t.Fatal("conversation ID is 0")
	}
	if conv.Title != "测试会话" {
		t.Errorf("expected title=测试会话, got %s", conv.Title)
	}

	convs, err := s.ListConversations(user.ID, 10)
	if err != nil {
		t.Fatalf("ListConversations failed: %v", err)
	}
	if len(convs) != 1 {
		t.Fatalf("expected 1 conversation, got %d", len(convs))
	}
}

func TestCreateMessage(t *testing.T) {
	dbPath := "test_data/test_msg.db"
	defer os.RemoveAll("test_data")

	s, err := NewStore(dbPath + "?_journal_mode=WAL")
	if err != nil {
		t.Fatalf("NewStore failed: %v", err)
	}
	defer s.Close()

	user, _ := s.CreateUser("msguser", "hash")
	conv, _ := s.CreateConversation(user.ID, "测试")

	msg, err := s.CreateMessage(conv.ID, "user", "Hello", nil, 0)
	if err != nil {
		t.Fatalf("CreateMessage failed: %v", err)
	}
	if msg.ID == 0 {
		t.Fatal("message ID is 0")
	}
	if msg.Role != "user" {
		t.Errorf("expected role=user, got %s", msg.Role)
	}

	msgs, err := s.ListMessages(conv.ID, 50)
	if err != nil {
		t.Fatalf("ListMessages failed: %v", err)
	}
	if len(msgs) != 1 {
		t.Fatalf("expected 1 message, got %d", len(msgs))
	}
}
