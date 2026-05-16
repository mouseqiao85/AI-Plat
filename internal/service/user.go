package service

import (
	"fmt"

	"github.com/agent-platform/internal/model"
	"github.com/agent-platform/internal/store"
	"github.com/agent-platform/pkg/auth"
	"golang.org/x/crypto/bcrypt"
)

var (
	ErrUserNotFound    = fmt.Errorf("用户不存在")
	ErrWrongPassword   = fmt.Errorf("原密码错误")
	ErrCannotDeleteSelf = fmt.Errorf("不能删除自己的账号")
)

type UserService struct {
	store *store.Store
}

func NewUserService(s *store.Store) *UserService {
	return &UserService{store: s}
}

func (s *UserService) Register(username, password string) (*model.User, error) {
	existing, _ := s.store.GetUserByUsername(username)
	if existing != nil {
		return nil, fmt.Errorf("用户名已存在")
	}

	hash, err := bcrypt.GenerateFromPassword([]byte(password), bcrypt.DefaultCost)
	if err != nil {
		return nil, fmt.Errorf("密码加密失败: %w", err)
	}

	return s.store.CreateUser(username, string(hash))
}

func (s *UserService) Login(username, password string) (*model.AuthResponse, error) {
	user, err := s.store.GetUserByUsername(username)
	if err != nil {
		return nil, fmt.Errorf("查询用户失败: %w", err)
	}
	if user == nil {
		return nil, fmt.Errorf("用户名或密码错误")
	}

	if err := bcrypt.CompareHashAndPassword([]byte(user.PasswordHash), []byte(password)); err != nil {
		return nil, fmt.Errorf("用户名或密码错误")
	}

	token, err := auth.CreateToken(user.ID, user.Username, user.Role, user.Tier)
	if err != nil {
		return nil, fmt.Errorf("生成令牌失败: %w", err)
	}

	return &model.AuthResponse{
		Token:    token,
		UserID:   user.ID,
		Username: user.Username,
		Role:     user.Role,
	}, nil
}

func (s *UserService) GetProfile(userID int64) (*model.User, error) {
	return s.store.GetUserByID(userID)
}

func (s *UserService) ChangePassword(userID int64, oldPassword, newPassword string) error {
	user, err := s.store.GetUserByID(userID)
	if err != nil {
		return ErrUserNotFound
	}
	if user == nil {
		return ErrUserNotFound
	}
	if err := bcrypt.CompareHashAndPassword([]byte(user.PasswordHash), []byte(oldPassword)); err != nil {
		return ErrWrongPassword
	}
	hash, err := bcrypt.GenerateFromPassword([]byte(newPassword), bcrypt.DefaultCost)
	if err != nil {
		return fmt.Errorf("密码加密失败: %w", err)
	}
	return s.store.UpdatePassword(userID, string(hash))
}

func (s *UserService) UpdateProfile(userID int64, nickname string) error {
	return s.store.UpdateUserProfile(userID, nickname)
}

func (s *UserService) ListUsers() ([]*model.User, error) {
	return s.store.ListUsers()
}

func (s *UserService) UpdateUserRole(targetUserID int64, role string) error {
	user, err := s.store.GetUserByID(targetUserID)
	if err != nil {
		return ErrUserNotFound
	}
	if user == nil {
		return ErrUserNotFound
	}
	return s.store.UpdateUserRole(targetUserID, role)
}

func (s *UserService) DeleteUser(targetUserID int64) error {
	return s.store.DeleteUser(targetUserID)
}

func (s *UserService) AdminResetPassword(targetUserID int64, newPassword string) error {
	user, err := s.store.GetUserByID(targetUserID)
	if err != nil {
		return ErrUserNotFound
	}
	if user == nil {
		return ErrUserNotFound
	}
	hash, err := bcrypt.GenerateFromPassword([]byte(newPassword), bcrypt.DefaultCost)
	if err != nil {
		return fmt.Errorf("密码加密失败: %w", err)
	}
	return s.store.UpdatePassword(targetUserID, string(hash))
}
