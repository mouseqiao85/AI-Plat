package auth

import (
	"fmt"
	"time"

	"github.com/golang-jwt/jwt/v5"
)

// DefaultSecret is the JWT secret used when none is configured.
// Override by calling Init or setting the field before use.
var DefaultSecret = "change-me-in-production"

// DefaultExpireMinutes is the default token expiry in minutes.
var DefaultExpireMinutes = 10080

// Claims represents the JWT claims for the platform.
type Claims struct {
	UserID   int64  `json:"user_id"`
	Username string `json:"username"`
	Role     string `json:"role"`
	Tier     string `json:"tier"`
	jwt.RegisteredClaims
}

// Init sets the default JWT secret and expiry.
func Init(secret string, expireMinutes int) {
	DefaultSecret = secret
	if expireMinutes > 0 {
		DefaultExpireMinutes = expireMinutes
	}
}

// CreateToken generates a JWT using package-level defaults.
func CreateToken(userID int64, username, role, tier string) (string, error) {
	return GenerateToken(username, role, DefaultSecret, DefaultExpireMinutes, userID, tier)
}

// ValidateToken parses and validates a JWT using the package-level default secret.
func ValidateToken(tokenStr string) (*Claims, error) {
	return ValidateTokenWithSecret(tokenStr, DefaultSecret)
}

// GenerateToken creates a signed JWT with the given parameters.
func GenerateToken(username, role, secret string, expireMinutes int, userID int64, tier string) (string, error) {
	now := time.Now()
	claims := &Claims{
		UserID:   userID,
		Username: username,
		Role:     role,
		Tier:     tier,
		RegisteredClaims: jwt.RegisteredClaims{
			ExpiresAt: jwt.NewNumericDate(now.Add(time.Duration(expireMinutes) * time.Minute)),
			IssuedAt:  jwt.NewNumericDate(now),
			NotBefore: jwt.NewNumericDate(now),
			Issuer:    "agent-platform",
		},
	}

	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	tokenString, err := token.SignedString([]byte(secret))
	if err != nil {
		return "", fmt.Errorf("sign token: %w", err)
	}

	return tokenString, nil
}

// ValidateTokenWithSecret parses and validates a JWT with the given secret.
func ValidateTokenWithSecret(tokenStr, secret string) (*Claims, error) {
	token, err := jwt.ParseWithClaims(tokenStr, &Claims{}, func(token *jwt.Token) (interface{}, error) {
		if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
			return nil, fmt.Errorf("unexpected signing method: %v", token.Header["alg"])
		}
		return []byte(secret), nil
	})
	if err != nil {
		return nil, fmt.Errorf("parse token: %w", err)
	}

	claims, ok := token.Claims.(*Claims)
	if !ok || !token.Valid {
		return nil, fmt.Errorf("invalid token")
	}

	return claims, nil
}
