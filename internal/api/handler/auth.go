package handler

import (
	"fmt"
	"net/http"
	"os"

	"github.com/gin-gonic/gin"

	"github.com/agent-platform/internal/model"
	"github.com/agent-platform/internal/service"
	"github.com/agent-platform/internal/store"
	"github.com/agent-platform/pkg/auth"
	"golang.org/x/crypto/bcrypt"
)

type AuthHandler struct {
	userSvc *service.UserService
	store   *store.Store
	debug   bool
}

func NewAuthHandler(db *store.Store, userSvc *service.UserService, debug bool) *AuthHandler {
	return &AuthHandler{userSvc: userSvc, store: db, debug: debug}
}

func (h *AuthHandler) Register(c *gin.Context) {
	var req model.RegisterRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "请求参数无效"})
		return
	}

	user, err := h.userSvc.Register(req.Username, req.Password)
	if err != nil {
		c.JSON(http.StatusConflict, gin.H{"error": err.Error()})
		return
	}

	resp, _ := h.userSvc.Login(req.Username, req.Password)
	c.JSON(http.StatusCreated, model.LoginResponse{
		AccessToken: resp.Token,
		User: model.UserInfo{
			ID: user.ID, Nickname: user.Nickname,
			MembershipTier: user.Tier, Role: user.Role,
		},
	})
}

func (h *AuthHandler) Login(c *gin.Context) {
	var req model.LoginRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "请求参数无效"})
		return
	}

	resp, err := h.userSvc.Login(req.Username, req.Password)
	if err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{"error": err.Error()})
		return
	}

	user, _ := h.userSvc.GetProfile(resp.UserID)
	nickname := ""
	tier := "free"
	role := "user"
	if user != nil {
		nickname = user.Nickname
		tier = user.Tier
		role = user.Role
	}

	c.JSON(http.StatusOK, model.LoginResponse{
		AccessToken: resp.Token,
		User: model.UserInfo{
			ID: resp.UserID, Nickname: nickname,
			MembershipTier: tier, Role: role,
		},
	})
}

func (h *AuthHandler) DevLogin(c *gin.Context) {
	// Hard production gate: refuse regardless of debug flag if env marks production.
	if os.Getenv("ENVIRONMENT") == "production" || os.Getenv("APP_ENV") == "production" {
		c.JSON(http.StatusNotFound, gin.H{"error": "not found"})
		return
	}
	if !h.debug {
		c.JSON(http.StatusForbidden, gin.H{"error": "开发登录仅限调试模式"})
		return
	}

	adminUser, _ := h.store.GetUserByUsername("admin")
	if adminUser == nil {
		hash, _ := bcrypt.GenerateFromPassword([]byte("admin"), bcrypt.DefaultCost)
		adminUser, _ = h.store.CreateUser("admin", string(hash))
		adminUser.Role = "admin"
	}

	// Generate a real JWT token instead of returning a hardcoded dev token
	token, err := auth.CreateToken(adminUser.ID, adminUser.Username, adminUser.Role, adminUser.Tier)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "生成令牌失败"})
		return
	}

	c.JSON(http.StatusOK, model.LoginResponse{
		AccessToken: token,
		User: model.UserInfo{
			ID: adminUser.ID, Nickname: adminUser.Nickname,
			MembershipTier: adminUser.Tier, Role: adminUser.Role,
		},
	})
}

func (h *AuthHandler) Me(c *gin.Context) {
	userID := c.GetInt64("user_id")
	user, err := h.userSvc.GetProfile(userID)
	if err != nil || user == nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "用户不存在"})
		return
	}

	c.JSON(http.StatusOK, model.UserInfo{
		ID: user.ID, Username: user.Username, Nickname: user.Nickname,
		MembershipTier: user.Tier, Role: user.Role,
		CreatedAt: user.CreatedAt.Format("2006-01-02 15:04:05"),
	})
}

// ChangePassword handles password change for current user
func (h *AuthHandler) ChangePassword(c *gin.Context) {
	var req model.ChangePasswordRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "请求参数无效，新密码至少6位"})
		return
	}

	userID := c.GetInt64("user_id")
	if err := h.userSvc.ChangePassword(userID, req.OldPassword, req.NewPassword); err != nil {
		if err == service.ErrUserNotFound {
			c.JSON(http.StatusNotFound, gin.H{"error": err.Error()})
		} else if err == service.ErrWrongPassword {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		} else {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		}
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "密码修改成功"})
}

// UpdateProfile handles updating user profile (nickname)
func (h *AuthHandler) UpdateProfile(c *gin.Context) {
	var req model.UpdateProfileRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "请求参数无效"})
		return
	}

	userID := c.GetInt64("user_id")
	if err := h.userSvc.UpdateProfile(userID, req.Nickname); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "个人信息更新成功"})
}

// ── Admin endpoints ──

// ListUsers returns all users (admin only)
func (h *AuthHandler) ListUsers(c *gin.Context) {
	users, err := h.userSvc.ListUsers()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "查询用户列表失败"})
		return
	}

	result := make([]model.UserDetail, 0, len(users))
	for _, u := range users {
		result = append(result, model.UserDetail{
			ID:        u.ID,
			Username:  u.Username,
			Nickname:  u.Nickname,
			Role:      u.Role,
			Tier:      u.Tier,
			CreatedAt: u.CreatedAt.Format("2006-01-02 15:04:05"),
			UpdatedAt: u.UpdatedAt.Format("2006-01-02 15:04:05"),
		})
	}

	c.JSON(http.StatusOK, gin.H{"users": result, "total": len(result)})
}

// AdminUpdateUser updates a user's role, nickname, or password (admin only)
func (h *AuthHandler) AdminUpdateUser(c *gin.Context) {
	userIDStr := c.Param("id")
	var userID int64
	if _, err := fmt.Sscanf(userIDStr, "%d", &userID); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "无效的用户ID"})
		return
	}

	var req model.AdminUpdateUserRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "请求参数无效"})
		return
	}

	if req.Role != "" {
		validRoles := map[string]bool{"user": true, "admin": true}
		if !validRoles[req.Role] {
			c.JSON(http.StatusBadRequest, gin.H{"error": "无效的角色，仅支持 user/admin"})
			return
		}
		if err := h.userSvc.UpdateUserRole(userID, req.Role); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}
	}

	if req.Nickname != "" {
		if err := h.userSvc.UpdateProfile(userID, req.Nickname); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}
	}

	if req.Password != "" {
		if len(req.Password) < 6 {
			c.JSON(http.StatusBadRequest, gin.H{"error": "密码至少6位"})
			return
		}
		if err := h.userSvc.AdminResetPassword(userID, req.Password); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}
	}

	c.JSON(http.StatusOK, gin.H{"message": "用户更新成功"})
}

// AdminDeleteUser deletes a user (admin only)
func (h *AuthHandler) AdminDeleteUser(c *gin.Context) {
	userIDStr := c.Param("id")
	var userID int64
	if _, err := fmt.Sscanf(userIDStr, "%d", &userID); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "无效的用户ID"})
		return
	}

	// Prevent admin from deleting themselves
	adminID := c.GetInt64("user_id")
	if userID == adminID {
		c.JSON(http.StatusBadRequest, gin.H{"error": "不能删除自己的账号"})
		return
	}

	if err := h.userSvc.DeleteUser(userID); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "用户已删除"})
}
