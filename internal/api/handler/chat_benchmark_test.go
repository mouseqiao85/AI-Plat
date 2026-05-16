package handler

import (
	"testing"

	"github.com/agent-platform/internal/model"
	"github.com/agent-platform/pkg/config"
)

func BenchmarkStreamEventMarshal(b *testing.B) {
	evt := model.StreamEvent{
		Type:        "tool_progress",
		ToolName:    "web_search",
		CurrentStep: 2,
		TotalSteps:  5,
		Status:      "running",
	}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_ = evt
	}
}

func BenchmarkStreamEventTypes(b *testing.B) {
	events := []model.StreamEvent{
		{Type: "text", Content: "Hello world"},
		{Type: "tool_call", ToolName: "web_search"},
		{Type: "tool_result", ToolName: "web_search", Result: []byte(`{"ok":true}`)},
		{Type: "tool_progress", ToolName: "calculator", CurrentStep: 1, TotalSteps: 3, Status: "running"},
		{Type: "done", Done: true},
	}

	cfg := &config.Config{Debug: true}
	_ = cfg

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		for _, e := range events {
			_ = e.Type
			_ = e.ToolName
		}
	}
}
