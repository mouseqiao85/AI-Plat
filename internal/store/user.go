package store

import (
	"database/sql"
	"time"

	"github.com/agent-platform/internal/model"
)

func (s *Store) CreateUser(username, passwordHash string) (*model.User, error) {
	now := time.Now()
	result, err := s.DB.Exec(
		`INSERT INTO users (username, password_hash, nickname, role, tier, created_at, updated_at)
		 VALUES (?, ?, ?, 'user', 'free', ?, ?)`,
		username, passwordHash, username, now, now,
	)
	if err != nil {
		return nil, err
	}

	id, _ := result.LastInsertId()
	return &model.User{
		ID:           id,
		Username:     username,
		PasswordHash: passwordHash,
		Nickname:     username,
		Role:         "user",
		Tier:         "free",
		CreatedAt:    now,
		UpdatedAt:    now,
	}, nil
}

func (s *Store) GetUserByID(id int64) (*model.User, error) {
	user := &model.User{}
	var createdAt, updatedAt string
	err := s.DB.QueryRow(
		`SELECT id, username, password_hash, nickname, role, tier, created_at, updated_at
		 FROM users WHERE id = ?`, id,
	).Scan(&user.ID, &user.Username, &user.PasswordHash, &user.Nickname, &user.Role, &user.Tier, &createdAt, &updatedAt)
	if err == sql.ErrNoRows {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	user.CreatedAt, _ = parseTime(createdAt)
	user.UpdatedAt, _ = parseTime(updatedAt)
	return user, nil
}

func (s *Store) GetUserByUsername(username string) (*model.User, error) {
	user := &model.User{}
	var createdAt, updatedAt string
	err := s.DB.QueryRow(
		`SELECT id, username, password_hash, nickname, role, tier, created_at, updated_at
		 FROM users WHERE username = ?`, username,
	).Scan(&user.ID, &user.Username, &user.PasswordHash, &user.Nickname, &user.Role, &user.Tier, &createdAt, &updatedAt)
	if err == sql.ErrNoRows {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	user.CreatedAt, _ = parseTime(createdAt)
	user.UpdatedAt, _ = parseTime(updatedAt)
	return user, nil
}

func (s *Store) UpdatePassword(userID int64, newHash string) error {
	now := time.Now()
	_, err := s.DB.Exec(
		`UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?`,
		newHash, now, userID,
	)
	return err
}

func (s *Store) UpdateUserProfile(userID int64, nickname string) error {
	now := time.Now()
	_, err := s.DB.Exec(
		`UPDATE users SET nickname = ?, updated_at = ? WHERE id = ?`,
		nickname, now, userID,
	)
	return err
}

func (s *Store) ListUsers() ([]*model.User, error) {
	rows, err := s.DB.Query(
		`SELECT id, username, password_hash, nickname, role, tier, created_at, updated_at
		 FROM users ORDER BY id ASC`,
	)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var users []*model.User
	for rows.Next() {
		user := &model.User{}
		var createdAt, updatedAt string
		if err := rows.Scan(&user.ID, &user.Username, &user.PasswordHash, &user.Nickname, &user.Role, &user.Tier, &createdAt, &updatedAt); err != nil {
			return nil, err
		}
		user.CreatedAt, _ = parseTime(createdAt)
		user.UpdatedAt, _ = parseTime(updatedAt)
		users = append(users, user)
	}
	return users, rows.Err()
}

func (s *Store) UpdateUserRole(userID int64, role string) error {
	now := time.Now()
	_, err := s.DB.Exec(
		`UPDATE users SET role = ?, updated_at = ? WHERE id = ?`,
		role, now, userID,
	)
	return err
}

func (s *Store) DeleteUser(userID int64) error {
	_, err := s.DB.Exec(`DELETE FROM users WHERE id = ?`, userID)
	return err
}

func (s *Store) SeedAdminUser(passwordHash string) error {
	existing, _ := s.GetUserByUsername("admin")
	if existing != nil {
		return nil
	}
	now := time.Now()
	_, err := s.DB.Exec(
		`INSERT INTO users (username, password_hash, nickname, role, tier, created_at, updated_at)
		 VALUES (?, ?, 'Admin', 'admin', 'enterprise', ?, ?)`,
		"admin", passwordHash, now, now,
	)
	return err
}
