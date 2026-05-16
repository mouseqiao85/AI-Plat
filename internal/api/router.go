package api

import (
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"

	"github.com/gin-gonic/gin"

	"github.com/agent-platform/internal/api/handler"
	"github.com/agent-platform/internal/api/middleware"
	mw "github.com/agent-platform/internal/middleware"
	"github.com/agent-platform/internal/service"
	"github.com/agent-platform/internal/service/tool"
	"github.com/agent-platform/internal/service/tool/builtin"
	"github.com/agent-platform/internal/store"
	"github.com/agent-platform/pkg/config"
)

func SetupRouter(db *store.Store, cfg *config.Config) *gin.Engine {
	if !cfg.Debug {
		gin.SetMode(gin.ReleaseMode)
	}

	r := gin.New()

	// ── Security middleware ──
	r.Use(mw.RecoveryMiddleware())
	r.Use(mw.RequestIDMiddleware())
	r.Use(mw.SecurityHeadersMiddleware())

	// CORS — use configurable middleware when origins are set, otherwise allow all
	r.Use(mw.CORSMiddleware(mw.DefaultCORSConfig()))

	// Rate limiting
	if cfg.RateLimit.PerMinute > 0 {
		r.Use(mw.RateLimitMiddleware(mw.RateLimiterConfig{
			RequestsPerSecond: 100,
			Burst:             200,
			Enabled:           true,
		}))
	}

	// ── Services ──
	registry := tool.NewRegistry()
	registry.Register(builtin.NewWebSearchTool())
	registry.Register(builtin.NewCalculatorTool())

	userSvc := service.NewUserService(db)

	// ── Handlers ──
	healthH := handler.NewHealthHandler()
	authH := handler.NewAuthHandler(db, userSvc, cfg.Debug)
	chatH := handler.NewChatHandler(db, registry, cfg)
	toolExecH := tool.NewExecutorHandler(registry, cfg.Agent.Timeout)
	skillH := handler.NewSkillHandler(cfg.Agent.ServiceURL)
	adminH := handler.NewAdminHandler(cfg.Agent.ServiceURL)
	hermesH := handler.NewHermesHandler(cfg.Hermes.ServiceURL, cfg.Hermes.Timeout)
	marketH := handler.NewMarketHandler(db)

	r.GET("/api/v1/health", healthH.Health)

	// Catch-all passthrough for multi-agent orchestrator endpoints (/api/v2/*).
	// Must be registered before NoRoute so the SPA fallback doesn't swallow it.
	r.Any("/api/v2/*path", hermesH.PassthroughV2)

	v1 := r.Group("/api/v1")
	{
		setupAuthRoutes(v1, authH, cfg)
		setupChatRoutes(v1, chatH, cfg)
		setupConversationRoutes(v1, chatH, cfg)
		setupToolRoutes(v1, toolExecH, cfg)
		setupSkillRoutes(v1, skillH, cfg)
		setupAdminRoutes(v1, adminH, cfg)
		setupMarketRoutes(v1, marketH, cfg)
		setupHermesRoutes(v1, hermesH, cfg)
	}

	// Serve frontend — production build from web/dist/
	// Custom asset handler: long-lived caching + precompressed .gz when available
	r.GET("/assets/*filepath", serveStaticAsset)
	r.HEAD("/assets/*filepath", serveStaticAsset)
	r.StaticFile("/favicon.svg", "./web/dist/favicon.svg")
	r.StaticFile("/icons.svg", "./web/dist/icons.svg")
	r.StaticFile("/", "./web/dist/index.html")
	r.NoRoute(func(c *gin.Context) {
		c.File("./web/dist/index.html")
	})

	// Serve generated files — proxy to agent or serve locally
	r.GET("/api/v1/files/*filepath", func(c *gin.Context) {
		filePath := c.Param("filepath")
		proxyFileDownload(c, cfg.Agent.ServiceURL, filePath)
	})

	return r
}

func setupAuthRoutes(v1 *gin.RouterGroup, h *handler.AuthHandler, cfg *config.Config) {
	authGroup := v1.Group("/auth")
	{
		authGroup.POST("/register", h.Register)
		authGroup.POST("/login", h.Login)
		authGroup.POST("/dev-login", h.DevLogin)
		authGroup.GET("/me", middleware.AuthMiddleware(cfg.Debug, cfg.DevToken), h.Me)
		authGroup.POST("/change-password", middleware.AuthMiddleware(cfg.Debug, cfg.DevToken), h.ChangePassword)
		authGroup.POST("/update-profile", middleware.AuthMiddleware(cfg.Debug, cfg.DevToken), h.UpdateProfile)
	}
	// Admin-only user management
	adminAuth := v1.Group("/admin/users")
	adminAuth.Use(middleware.AuthMiddleware(cfg.Debug, cfg.DevToken))
	adminAuth.Use(middleware.AdminMiddleware())
	{
		adminAuth.GET("", h.ListUsers)
		adminAuth.PUT("/:id", h.AdminUpdateUser)
		adminAuth.DELETE("/:id", h.AdminDeleteUser)
	}
}

func setupChatRoutes(v1 *gin.RouterGroup, h *handler.ChatHandler, cfg *config.Config) {
	chatGroup := v1.Group("/chat")
	chatGroup.Use(middleware.AuthMiddleware(cfg.Debug, cfg.DevToken))
	{
		chatGroup.POST("", h.Chat)
		chatGroup.GET("/providers", h.Providers)
	}
}

func setupConversationRoutes(v1 *gin.RouterGroup, h *handler.ChatHandler, cfg *config.Config) {
	convGroup := v1.Group("/conversations")
	convGroup.Use(middleware.AuthMiddleware(cfg.Debug, cfg.DevToken))
	{
		convGroup.GET("", h.Conversations)
		convGroup.POST("/delete-all", h.DeleteAllConversations)
		convGroup.GET("/:id/messages", h.GetMessages)
		convGroup.PATCH("/:id", h.RenameConversation)
		convGroup.DELETE("/:id", h.DeleteConversation)
		convGroup.DELETE("/:id/messages", h.ClearConversationMessages)
		convGroup.GET("/user-profile", h.GetUserProfile)
		convGroup.DELETE("/user-profile", h.ClearUserProfile)
	}
}

func setupToolRoutes(v1 *gin.RouterGroup, h *tool.ExecutorHandler, cfg *config.Config) {
	toolGroup := v1.Group("/tools")
	toolGroup.Use(middleware.AuthMiddleware(cfg.Debug, cfg.DevToken))
	{
		toolGroup.POST("/execute", h.Execute)
		toolGroup.GET("", h.List)
	}
}

func setupSkillRoutes(v1 *gin.RouterGroup, h *handler.SkillHandler, cfg *config.Config) {
	skillGroup := v1.Group("/skills")
	skillGroup.Use(middleware.AuthMiddleware(cfg.Debug, cfg.DevToken))
	{
		skillGroup.GET("/", h.List)
		skillGroup.POST("", h.Add)
		skillGroup.POST("/upload", h.Upload)
		skillGroup.GET("/:name", h.Get)
		skillGroup.PUT("/:name", h.Update)
		skillGroup.DELETE("/:name", h.Remove)
		skillGroup.POST("/:name/enable", h.Enable)
		skillGroup.POST("/:name/disable", h.Disable)
	}
}

func setupAdminRoutes(v1 *gin.RouterGroup, h *handler.AdminHandler, cfg *config.Config) {
	adminGroup := v1.Group("/admin")
	adminGroup.Use(middleware.AuthMiddleware(cfg.Debug, cfg.DevToken))
	{
		adminGroup.GET("/providers", h.ListProviders)
		adminGroup.POST("/providers", h.AddProvider)
		adminGroup.PUT("/providers/:id", h.UpdateProvider)
		adminGroup.DELETE("/providers/:id", h.DeleteProvider)
	}
}

func setupMarketRoutes(v1 *gin.RouterGroup, h *handler.MarketHandler, cfg *config.Config) {
	marketGroup := v1.Group("/marketplace")
	marketGroup.Use(middleware.AuthMiddleware(cfg.Debug, cfg.DevToken))
	{
		marketGroup.GET("/agents", h.ListAgents)
		marketGroup.GET("/agents/:id", h.GetAgent)
		marketGroup.POST("/agents", h.CreateAgent)
		marketGroup.PATCH("/agents/:id", h.UpdateAgent)
		marketGroup.DELETE("/agents/:id", h.DeleteAgent)
	}
}

func setupHermesRoutes(v1 *gin.RouterGroup, h *handler.HermesHandler, cfg *config.Config) {
	hermesGroup := v1.Group("/hermes")
	hermesGroup.Use(middleware.AuthMiddleware(cfg.Debug, cfg.DevToken))
	{
		hermesGroup.GET("/health", h.Health)
		hermesGroup.POST("/chat", h.Chat)
		hermesGroup.POST("/chat/stream", h.ChatStream)
		hermesGroup.GET("/skills", h.ListSkills)
		hermesGroup.GET("/skills/:name", h.GetSkill)
		hermesGroup.POST("/skills/:name/execute", h.ExecuteSkill)
		hermesGroup.GET("/agents", h.ListAgents)
		hermesGroup.POST("/agents/:name/run", h.RunAgent)
		hermesGroup.GET("/workspace", h.Workspace)
		hermesGroup.GET("/skills/hub", h.SearchHub)
		hermesGroup.POST("/skills/hub/install", h.InstallHub)
	}
}

// proxyFileDownload serves generated files by trying the agent service first,
// then falling back to the local filesystem.
func proxyFileDownload(c *gin.Context, agentURL, filePath string) {
	filePath = strings.TrimPrefix(filePath, "/")

	// Try local filesystem first
	localPath := filepath.Join("./agent/data/generated", filePath)
	if info, err := os.Stat(localPath); err == nil && !info.IsDir() {
		c.File(localPath)
		return
	}

	// Fallback: proxy to Python agent service
	url := strings.TrimRight(agentURL, "/") + "/api/v1/files/" + filePath
	req, err := http.NewRequestWithContext(c.Request.Context(), "GET", url, nil)
	if err != nil {
		c.Status(http.StatusNotFound)
		return
	}

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		c.Status(http.StatusNotFound)
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		c.Status(resp.StatusCode)
		return
	}

	for key, values := range resp.Header {
		for _, v := range values {
			c.Header(key, v)
		}
	}

	io.Copy(c.Writer, resp.Body)
}
