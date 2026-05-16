package handler

import (
	"net/http"
	"strconv"
	"strings"

	"github.com/gin-gonic/gin"

	"github.com/agent-platform/internal/api/middleware"
	"github.com/agent-platform/internal/store"
)

type MetricsHandler struct {
	store *store.Store
}

func NewMetricsHandler(db *store.Store) *MetricsHandler {
	return &MetricsHandler{store: db}
}

func (h *MetricsHandler) Metrics(c *gin.Context) {
	var sb strings.Builder
	sb.WriteString("# HELP gateway_requests_total Total requests\n")
	sb.WriteString("# TYPE gateway_requests_total counter\n")
	for path, count := range middleware.RequestsTotal {
		sb.WriteString("gateway_requests_total{path=\"" + path + "\"} " + strconv.FormatInt(count, 10) + "\n")
	}

	sb.WriteString("# HELP gateway_errors_total Total errors\n")
	sb.WriteString("# TYPE gateway_errors_total counter\n")
	for path, count := range middleware.ErrorsTotal {
		sb.WriteString("gateway_errors_total{path=\"" + path + "\"} " + strconv.FormatInt(count, 10) + "\n")
	}

	c.Data(http.StatusOK, "text/plain", []byte(sb.String()))
}
