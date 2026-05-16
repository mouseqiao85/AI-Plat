package tool

import (
	"encoding/json"
	"fmt"
	"sync"

	"github.com/agent-platform/internal/model"
)

type Tool interface {
	Name() string
	Description() string
	InputSchema() map[string]interface{}
	Execute(args map[string]interface{}) (interface{}, error)
}

type Registry struct {
	mu    sync.RWMutex
	tools map[string]Tool
}

func NewRegistry() *Registry {
	return &Registry{tools: make(map[string]Tool)}
}

func (r *Registry) Register(t Tool) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.tools[t.Name()] = t
}

func (r *Registry) Get(name string) (Tool, bool) {
	r.mu.RLock()
	defer r.mu.RUnlock()
	t, ok := r.tools[name]
	return t, ok
}

func (r *Registry) List() []model.ToolDefinition {
	r.mu.RLock()
	defer r.mu.RUnlock()

	defs := make([]model.ToolDefinition, 0, len(r.tools))
	for _, t := range r.tools {
		schema, _ := json.Marshal(t.InputSchema())
		defs = append(defs, model.ToolDefinition{
			Name:        t.Name(),
			Description: t.Description(),
			InputSchema: schema,
		})
	}
	return defs
}

func (r *Registry) Execute(name string, args map[string]interface{}) (interface{}, error) {
	t, ok := r.Get(name)
	if !ok {
		return nil, fmt.Errorf("tool not found: %s", name)
	}
	return t.Execute(args)
}

func (r *Registry) GetOpenAITools() []map[string]interface{} {
	r.mu.RLock()
	defer r.mu.RUnlock()

	tools := make([]map[string]interface{}, 0, len(r.tools))
	for _, t := range r.tools {
		tools = append(tools, map[string]interface{}{
			"type": "function",
			"function": map[string]interface{}{
				"name":        t.Name(),
				"description": t.Description(),
				"parameters":  t.InputSchema(),
			},
		})
	}
	return tools
}
