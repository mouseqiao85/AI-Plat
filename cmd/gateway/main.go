package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"strconv"
	"syscall"
	"time"

	"github.com/agent-platform/internal/api"
	"github.com/agent-platform/internal/store"
	"github.com/agent-platform/pkg/config"
	"github.com/joho/godotenv"
	"golang.org/x/crypto/bcrypt"
)

func main() {
	// Load .env from CWD before anything reads os.Getenv. Missing file is non-fatal.
	if err := godotenv.Load(); err != nil && !os.IsNotExist(err) {
		log.Printf("godotenv.Load: %v", err)
	}

	configPath := "configs/config.yaml"
	if _, err := os.Stat(configPath); os.IsNotExist(err) {
		configPath = "../../configs/config.yaml"
	}
	cfg, err := config.Load(configPath)
	if err != nil {
		log.Fatalf("Failed to load config: %v", err)
	}

	db, err := store.NewStore(cfg.Database.DSN)
	if err != nil {
		log.Fatalf("Failed to initialize database: %v", err)
	}
	defer db.Close()

	seedAdminUser(db)

	router := api.SetupRouter(db, cfg)

	srv := &http.Server{
		Addr:         getEnvDefault("GATEWAY_HOST", "0.0.0.0") + ":" + strconv.Itoa(cfg.Port),
		Handler:      router,
		ReadTimeout:  30 * time.Second,
		WriteTimeout: getEnvDurationDefault("GATEWAY_WRITE_TIMEOUT_SECONDS", 2*time.Hour),
		IdleTimeout:  120 * time.Second,
	}

	go func() {
		log.Printf("Gateway starting on %s (debug=%v)", srv.Addr, cfg.Debug)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("Server failed: %v", err)
		}
	}()

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	log.Println("Shutting down server...")
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	if err := srv.Shutdown(ctx); err != nil {
		log.Fatalf("Server forced to shutdown: %v", err)
	}
	log.Println("Server stopped")
}

func seedAdminUser(db *store.Store) {
	hash, err := bcrypt.GenerateFromPassword([]byte("admin"), bcrypt.DefaultCost)
	if err != nil {
		return
	}
	_ = db.SeedAdminUser(string(hash))
}

func getEnvDefault(key, def string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return def
}

func getEnvDurationDefault(key string, def time.Duration) time.Duration {
	if v := os.Getenv(key); v != "" {
		seconds, err := strconv.Atoi(v)
		if err == nil && seconds > 0 {
			return time.Duration(seconds) * time.Second
		}
	}
	return def
}
