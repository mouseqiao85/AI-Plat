package model

import (
	"encoding/json"
	"time"
)

type User struct {
	ID           int64     `json:"id"`
	Username     string    `json:"username"`
	PasswordHash string    `json:"-"`
	Nickname     string    `json:"nickname"`
	Role         string    `json:"role"`
	Tier         string    `json:"tier"`
	CreatedAt    time.Time `json:"created_at"`
	UpdatedAt    time.Time `json:"updated_at"`
}

type Conversation struct {
	ID        int64     `json:"id"`
	UserID    int64     `json:"user_id"`
	Title     string    `json:"title"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

type Message struct {
	ID             int64           `json:"id"`
	ConversationID int64           `json:"conversation_id"`
	Role           string          `json:"role"`
	Content        string          `json:"content"`
	ToolCalls      json.RawMessage `json:"tool_calls,omitempty"`
	TokenCount     int             `json:"token_count"`
	CreatedAt      time.Time       `json:"created_at"`
}

type ChatRequest struct {
	Message        string `json:"message"`
	ConversationID int64  `json:"conversation_id,omitempty"`
	ProviderID     string `json:"provider_id,omitempty"`
	Model          string `json:"model,omitempty"`
	SkillName      string `json:"skill_name,omitempty"`
}

// UserInfo is the user object returned to frontend
type UserInfo struct {
	ID             int64  `json:"id"`
	Username       string `json:"username,omitempty"`
	Nickname       string `json:"nickname"`
	MembershipTier string `json:"membership_tier"`
	Role           string `json:"role,omitempty"`
	CreatedAt      string `json:"created_at,omitempty"`
}

// UserDetail is the detailed user info for admin management
type UserDetail struct {
	ID       int64  `json:"id"`
	Username string `json:"username"`
	Nickname string `json:"nickname"`
	Role     string `json:"role"`
	Tier     string `json:"tier"`
	CreatedAt string `json:"created_at"`
	UpdatedAt string `json:"updated_at"`
}

// ChangePasswordRequest is the request to change password
type ChangePasswordRequest struct {
	OldPassword string `json:"old_password" binding:"required"`
	NewPassword string `json:"new_password" binding:"required,min=6"`
}

// UpdateProfileRequest is the request to update user profile
type UpdateProfileRequest struct {
	Nickname string `json:"nickname" binding:"required"`
}

// AdminUpdateUserRequest is the admin request to update a user
type AdminUpdateUserRequest struct {
	Role       string `json:"role,omitempty"`
	Nickname   string `json:"nickname,omitempty"`
	Password   string `json:"password,omitempty"`
}

// LoginResponse is the auth response for frontend
type LoginResponse struct {
	AccessToken string   `json:"access_token"`
	User        UserInfo `json:"user"`
}

type ToolDefinition struct {
	Name        string          `json:"name"`
	Description string          `json:"description"`
	InputSchema json.RawMessage `json:"input_schema"`
}

type StreamEvent struct {
	Type        string          `json:"type"`
	Content     string          `json:"content,omitempty"`
	ToolName    string          `json:"tool_name,omitempty"`
	ToolArgs    json.RawMessage `json:"tool_args,omitempty"`
	ToolID      string          `json:"tool_id,omitempty"`
	Result      json.RawMessage `json:"result,omitempty"`
	Success     bool            `json:"success,omitempty"`
	Error       string          `json:"error,omitempty"`
	ConvID      int64           `json:"conversation_id,omitempty"`
	ConvTitle   string          `json:"conversation_title,omitempty"`
	Done        bool            `json:"done,omitempty"`
	CurrentStep int             `json:"current_step,omitempty"`
	TotalSteps  int             `json:"total_steps,omitempty"`
	Status      string          `json:"status,omitempty"`
}

type AuthResponse struct {
	Token    string `json:"token"`
	UserID   int64  `json:"user_id"`
	Username string `json:"username"`
	Role     string `json:"role"`
	ExpiresIn int   `json:"expires_in"`
}

type RegisterRequest struct {
	Username string `json:"username" binding:"required,min=3,max=32"`
	Password string `json:"password" binding:"required,min=6"`
}

type LoginRequest struct {
	Username string `json:"username" binding:"required"`
	Password string `json:"password" binding:"required"`
}

// ── Marketplace ──

type MarketAgent struct {
	ID           int64     `json:"id"`
	UserID       int64     `json:"user_id"`
	Title        string    `json:"title"`
	Function     string    `json:"function"`
	Description  string    `json:"description"`
	Icon         string    `json:"icon"`
	AccessURL    string    `json:"access_url"`
	KnowledgeURL string    `json:"knowledge_url"`
	Tags         string    `json:"tags"`
	Author       string    `json:"author"`
	UsageCount   int       `json:"usage_count"`
	Category     string    `json:"category"`
	Featured     bool      `json:"featured"`
	CreatedAt    time.Time `json:"created_at"`
	UpdatedAt    time.Time `json:"updated_at"`
}

type MarketAgentCreate struct {
	Title        string `json:"title"`
	Function     string `json:"function"`
	Description  string `json:"description"`
	Icon         string `json:"icon,omitempty"`
	AccessURL    string `json:"access_url,omitempty"`
	KnowledgeURL string `json:"knowledge_url,omitempty"`
	Tags         string `json:"tags"`
	Author       string `json:"author,omitempty"`
	Category     string `json:"category"`
	Featured     bool   `json:"featured"`
}

type MarketAgentUpdate struct {
	Title        *string `json:"title,omitempty"`
	Function     *string `json:"function,omitempty"`
	Description  *string `json:"description,omitempty"`
	AccessURL    *string `json:"access_url,omitempty"`
	KnowledgeURL *string `json:"knowledge_url,omitempty"`
	Tags         *string `json:"tags,omitempty"`
	Category     *string `json:"category,omitempty"`
	Featured     *bool   `json:"featured,omitempty"`
}

type LlmProvider struct {
	ID           string   `json:"id"`
	Name         string   `json:"name"`
	BaseURL      string   `json:"base_url"`
	APIKey       string   `json:"api_key"`
	CustomHeader string   `json:"custom_header,omitempty"`
	Models       []string `json:"models"`
	IsStatic     bool     `json:"-"`
}
