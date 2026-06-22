package handler

import (
	"encoding/json"
	"io"
	"mime/multipart"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/gin-gonic/gin"
)

func TestKnowledgeGraphHandlerProxiesGetWithQuery(t *testing.T) {
	gin.SetMode(gin.TestMode)
	var seenPath string
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		seenPath = r.URL.String()
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(map[string]any{"ok": true})
	}))
	defer server.Close()

	router := gin.New()
	h := NewKnowledgeGraphHandler(server.URL)
	router.GET("/api/v1/knowledge-graph/*path", h.Passthrough)

	req := httptest.NewRequest("GET", "/api/v1/knowledge-graph/nodes?q=CSM&limit=5", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("status = %d, body=%s", w.Code, w.Body.String())
	}
	if seenPath != "/api/v1/knowledge-graph/nodes?q=CSM&limit=5" {
		t.Fatalf("unexpected proxied path: %s", seenPath)
	}
}

func TestKnowledgeGraphHandlerProxiesMultipartUpload(t *testing.T) {
	gin.SetMode(gin.TestMode)
	var seenContentType string
	var bodyContainsFile bool
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		seenContentType = r.Header.Get("Content-Type")
		body, _ := io.ReadAll(r.Body)
		bodyContainsFile = strings.Contains(string(body), "vault.zip")
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusCreated)
		_, _ = w.Write([]byte(`{"status":"completed"}`))
	}))
	defer server.Close()

	var buf strings.Builder
	writer := multipart.NewWriter(&buf)
	part, err := writer.CreateFormFile("file", "vault.zip")
	if err != nil {
		t.Fatal(err)
	}
	_, _ = part.Write([]byte("zip-content"))
	_ = writer.WriteField("source_name", "Vault")
	if err := writer.Close(); err != nil {
		t.Fatal(err)
	}

	router := gin.New()
	h := NewKnowledgeGraphHandler(server.URL)
	router.POST("/api/v1/knowledge-graph/*path", h.Passthrough)

	req := httptest.NewRequest("POST", "/api/v1/knowledge-graph/import/obsidian", strings.NewReader(buf.String()))
	req.Header.Set("Content-Type", writer.FormDataContentType())
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusCreated {
		t.Fatalf("status = %d, body=%s", w.Code, w.Body.String())
	}
	if !strings.HasPrefix(seenContentType, "multipart/form-data") {
		t.Fatalf("content type not preserved: %s", seenContentType)
	}
	if !bodyContainsFile {
		t.Fatal("proxied multipart body did not include filename")
	}
}
