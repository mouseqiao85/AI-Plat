package tool

import (
	"testing"
)

type mockTool struct{}

func (m *mockTool) Name() string                         { return "mock_tool" }
func (m *mockTool) Description() string                  { return "A mock tool for testing" }
func (m *mockTool) InputSchema() map[string]interface{}   {
	return map[string]interface{}{
		"type": "object",
		"properties": map[string]interface{}{
			"arg": map[string]interface{}{"type": "string"},
		},
	}
}
func (m *mockTool) Execute(args map[string]interface{}) (interface{}, error) {
	return map[string]interface{}{"result": "ok"}, nil
}

func TestRegistryRegisterAndGet(t *testing.T) {
	r := NewRegistry()
	r.Register(&mockTool{})

	tool, ok := r.Get("mock_tool")
	if !ok {
		t.Fatal("tool not found")
	}
	if tool.Name() != "mock_tool" {
		t.Errorf("expected name=mock_tool, got %s", tool.Name())
	}
}

func TestRegistryList(t *testing.T) {
	r := NewRegistry()
	r.Register(&mockTool{})

	defs := r.List()
	if len(defs) != 1 {
		t.Fatalf("expected 1 tool, got %d", len(defs))
	}
	if defs[0].Name != "mock_tool" {
		t.Errorf("expected name=mock_tool, got %s", defs[0].Name)
	}
}

func TestRegistryExecute(t *testing.T) {
	r := NewRegistry()
	r.Register(&mockTool{})

	result, err := r.Execute("mock_tool", map[string]interface{}{"arg": "test"})
	if err != nil {
		t.Fatalf("Execute failed: %v", err)
	}
	resultMap, ok := result.(map[string]interface{})
	if !ok {
		t.Fatal("result is not a map")
	}
	if resultMap["result"] != "ok" {
		t.Errorf("expected result=ok, got %v", resultMap["result"])
	}
}

func TestRegistryGetNotFound(t *testing.T) {
	r := NewRegistry()
	_, ok := r.Get("nonexistent")
	if ok {
		t.Fatal("expected tool not found")
	}
}

func TestRegistryExecuteNotFound(t *testing.T) {
	r := NewRegistry()
	_, err := r.Execute("nonexistent", nil)
	if err == nil {
		t.Fatal("expected error for nonexistent tool")
	}
}
