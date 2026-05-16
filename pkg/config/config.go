package config

import (
	"os"
	"strconv"

	"gopkg.in/yaml.v3"
)

// Config holds all configuration for the application.
// Values are loaded from config.yaml, then overridden by environment variables.
type Config struct {
	Port     int    `yaml:"port"`
	Debug    bool   `yaml:"debug"`
	DevToken string `yaml:"-"` // from env DEV_TOKEN; never in yaml
	Database struct {
		Driver string `yaml:"driver"`
		DSN    string `yaml:"dsn"`
	} `yaml:"database"`
	Redis struct {
		Enabled bool   `yaml:"enabled"`
		Addr    string `yaml:"addr"`
	} `yaml:"redis"`
	JWT struct {
		Secret        string `yaml:"secret"`
		Algorithm     string `yaml:"algorithm"`
		ExpireMinutes int    `yaml:"expire_minutes"`
	} `yaml:"jwt"`
	Agent struct {
		ServiceURL string `yaml:"service_url"`
		Timeout    int    `yaml:"timeout"`
	} `yaml:"agent"`
	Hermes struct {
		ServiceURL string `yaml:"service_url"`
		Timeout    int    `yaml:"timeout"`
	} `yaml:"hermes"`
	LLM struct {
		Provider string `yaml:"provider"`
		Model    string `yaml:"model"`
		APIKey   string `yaml:"api_key"`
		BaseURL  string `yaml:"base_url"`
	} `yaml:"llm"`
	RateLimit struct {
		PerMinute     int `yaml:"per_minute"`
		AuthPerMinute int `yaml:"auth_per_minute"`
	} `yaml:"rate_limit"`
	Log struct {
		Level  string `yaml:"level"`
		Format string `yaml:"format"`
	} `yaml:"log"`
}

// Load reads a YAML config file and returns a Config.
func Load(path string) (*Config, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}

	var cfg Config
	if err := yaml.Unmarshal(data, &cfg); err != nil {
		return nil, err
	}

	// Apply defaults
	if cfg.Port == 0 {
		cfg.Port = 8080
	}
	if cfg.JWT.ExpireMinutes == 0 {
		cfg.JWT.ExpireMinutes = 10080
	}
	if cfg.JWT.Algorithm == "" {
		cfg.JWT.Algorithm = "HS256"
	}
	if cfg.Agent.Timeout == 0 {
		cfg.Agent.Timeout = 300
	}
	if cfg.Agent.ServiceURL == "" {
		cfg.Agent.ServiceURL = "http://localhost:8001"
	}
	if cfg.Hermes.ServiceURL == "" {
		cfg.Hermes.ServiceURL = "http://localhost:8002"
	}
	if cfg.Hermes.Timeout == 0 {
		cfg.Hermes.Timeout = 300
	}
	if cfg.Log.Level == "" {
		cfg.Log.Level = "info"
	}
	if cfg.Log.Format == "" {
		cfg.Log.Format = "console"
	}

	// ── Environment variable overrides for secrets ──
	// These MUST come from env, never from config.yaml committed to git.
	if v := os.Getenv("JWT_SECRET"); v != "" {
		cfg.JWT.Secret = v
	}
	if cfg.JWT.Secret == "" {
		cfg.JWT.Secret = os.Getenv("JWT_SECRET")
	}
	if cfg.DevToken == "" {
		cfg.DevToken = os.Getenv("DEV_TOKEN")
	}
	if v := os.Getenv("DATABASE_DSN"); v != "" {
		cfg.Database.DSN = v
	}
	if v := os.Getenv("LLM_API_KEY"); v != "" {
		cfg.LLM.APIKey = v
	}
	if v := os.Getenv("LLM_BASE_URL"); v != "" {
		cfg.LLM.BaseURL = v
	}
	if v := os.Getenv("LLM_MODEL"); v != "" {
		cfg.LLM.Model = v
	}
	if v := os.Getenv("LLM_PROVIDER"); v != "" {
		cfg.LLM.Provider = v
	}
	if v := os.Getenv("AGENT_SERVICE_URL"); v != "" {
		cfg.Agent.ServiceURL = v
	}
	if v := os.Getenv("HERMES_SERVICE_URL"); v != "" {
		cfg.Hermes.ServiceURL = v
	}
	if v := os.Getenv("PORT"); v != "" {
		if p, err := strconv.Atoi(v); err == nil {
			cfg.Port = p
		}
	}
	if v := os.Getenv("DEBUG"); v != "" {
		cfg.Debug = v == "true" || v == "1"
	}

	return &cfg, nil
}
