package tool

import (
	"testing"
)

type benchMockTool struct{}

func (m *benchMockTool) Name() string                       { return "bench_mock" }
func (m *benchMockTool) Description() string                { return "benchmark tool" }
func (m *benchMockTool) InputSchema() map[string]interface{} { return map[string]interface{}{"arg": "string"} }
func (m *benchMockTool) Execute(args map[string]interface{}) (interface{}, error) {
	return map[string]interface{}{"result": "ok"}, nil
}

func BenchmarkToolExecution(b *testing.B) {
	registry := NewRegistry()
	registry.Register(&benchMockTool{})

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, err := registry.Execute("bench_mock", map[string]interface{}{"arg": "test"})
		if err != nil {
			b.Fatal(err)
		}
	}
}

func BenchmarkToolExecutionParallel(b *testing.B) {
	registry := NewRegistry()
	registry.Register(&benchMockTool{})

	b.RunParallel(func(pb *testing.PB) {
		for pb.Next() {
			_, err := registry.Execute("bench_mock", map[string]interface{}{"arg": "test"})
			if err != nil {
				b.Fatal(err)
			}
		}
	})
}

func BenchmarkRegistryList(b *testing.B) {
	registry := NewRegistry()
	registry.Register(&benchMockTool{})

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_ = registry.List()
	}
}
