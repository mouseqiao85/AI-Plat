package config

import (
	"time"

	"github.com/spf13/viper"
)

type Config struct {
	Server         ServerConfig         `mapstructure:"server"`
	Redis          RedisConfig          `mapstructure:"redis"`
	JWT            JWTConfig            `mapstructure:"jwt"`
	RateLimit      RateLimitConfig      `mapstructure:"rate_limit"`
	CircuitBreaker CircuitBreakerConfig `mapstructure:"circuit_breaker"`
	Upstreams      []UpstreamConfig     `mapstructure:"upstreams"`
	Routes         []RouteConfig        `mapstructure:"routes"`
	Logging        LoggingConfig        `mapstructure:"logging"`
	CORS           CORSConfig           `mapstructure:"cors"`
}

type ServerConfig struct {
	Port           int           `mapstructure:"port"`
	Mode           string        `mapstructure:"mode"`
	ReadTimeout    time.Duration `mapstructure:"read_timeout"`
	WriteTimeout   time.Duration `mapstructure:"write_timeout"`
	MaxHeaderBytes int           `mapstructure:"max_header_bytes"`
}

type RedisConfig struct {
	Addr     string `mapstructure:"addr"`
	Password string `mapstructure:"password"`
	DB       int    `mapstructure:"db"`
	PoolSize int    `mapstructure:"pool_size"`
}

type JWTConfig struct {
	Secret string        `mapstructure:"secret"`
	Expire time.Duration `mapstructure:"expire"`
	Issuer string        `mapstructure:"issuer"`
}

type RateLimitConfig struct {
	Enabled             bool `mapstructure:"enabled"`
	RequestsPerSecond   int  `mapstructure:"requests_per_second"`
	Burst               int  `mapstructure:"burst"`
	IPRequestsPerSecond int  `mapstructure:"ip_requests_per_second"`
}

type CircuitBreakerConfig struct {
	Enabled          bool          `mapstructure:"enabled"`
	MaxRequests      uint32        `mapstructure:"max_requests"`
	Interval         time.Duration `mapstructure:"interval"`
	Timeout          time.Duration `mapstructure:"timeout"`
	FailureThreshold uint32        `mapstructure:"failure_threshold"`
	SuccessThreshold uint32        `mapstructure:"success_threshold"`
}

type UpstreamConfig struct {
	Name        string             `mapstructure:"name"`
	Path        string             `mapstructure:"path"`
	Targets     []string           `mapstructure:"targets"`
	LoadBalance string             `mapstructure:"load_balance"`
	HealthCheck *HealthCheckConfig `mapstructure:"health_check"`
}

type HealthCheckConfig struct {
	Enabled  bool          `mapstructure:"enabled"`
	Interval time.Duration `mapstructure:"interval"`
	Timeout  time.Duration `mapstructure:"timeout"`
}

type RouteConfig struct {
	Path         string `mapstructure:"path"`
	Upstream     string `mapstructure:"upstream"`
	AuthRequired bool   `mapstructure:"auth_required"`
	RateLimit    bool   `mapstructure:"rate_limit"`
}

type LoggingConfig struct {
	Level  string `mapstructure:"level"`
	Format string `mapstructure:"format"`
	Output string `mapstructure:"output"`
}

type CORSConfig struct {
	Enabled     bool     `mapstructure:"enabled"`
	Origins     []string `mapstructure:"origins"`
	Methods     []string `mapstructure:"methods"`
	Headers     []string `mapstructure:"headers"`
	Credentials bool     `mapstructure:"credentials"`
	MaxAge      int      `mapstructure:"max_age"`
}

var GlobalConfig *Config

func Load(configPath string) (*Config, error) {
	v := viper.New()

	v.SetConfigFile(configPath)
	v.SetConfigType("yaml")

	if err := v.ReadInConfig(); err != nil {
		return nil, err
	}

	var config Config
	if err := v.Unmarshal(&config); err != nil {
		return nil, err
	}

	GlobalConfig = &config
	return &config, nil
}

func LoadDefault() (*Config, error) {
	return Load("config/config.yaml")
}
