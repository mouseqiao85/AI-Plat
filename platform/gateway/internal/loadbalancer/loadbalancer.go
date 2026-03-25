package loadbalancer

import (
	"sync"
	"sync/atomic"
	"time"
)

type Backend struct {
	URL          string
	Alive        bool
	mu           sync.RWMutex
	Failures     uint32
	LastChecked  time.Time
	ResponseTime time.Duration
}

type LoadBalancer interface {
	Select(backends []*Backend) *Backend
}

type RoundRobin struct {
	current uint64
}

func NewRoundRobin() *RoundRobin {
	return &RoundRobin{current: 0}
}

func (rr *RoundRobin) Select(backends []*Backend) *Backend {
	if len(backends) == 0 {
		return nil
	}

	healthyBackends := make([]*Backend, 0)
	for _, b := range backends {
		if b.IsAlive() {
			healthyBackends = append(healthyBackends, b)
		}
	}

	if len(healthyBackends) == 0 {
		return nil
	}

	idx := atomic.AddUint64(&rr.current, 1) - 1
	return healthyBackends[idx%uint64(len(healthyBackends))]
}

type WeightedRoundRobin struct {
	current   uint64
	weights   map[string]int
	remaining map[string]int
	mu        sync.Mutex
}

func NewWeightedRoundRobin(weights map[string]int) *WeightedRoundRobin {
	remaining := make(map[string]int)
	for k, v := range weights {
		remaining[k] = v
	}
	return &WeightedRoundRobin{
		current:   0,
		weights:   weights,
		remaining: remaining,
	}
}

func (wrr *WeightedRoundRobin) Select(backends []*Backend) *Backend {
	if len(backends) == 0 {
		return nil
	}

	wrr.mu.Lock()
	defer wrr.mu.Unlock()

	healthyBackends := make([]*Backend, 0)
	for _, b := range backends {
		if b.IsAlive() {
			healthyBackends = append(healthyBackends, b)
		}
	}

	if len(healthyBackends) == 0 {
		return nil
	}

	for {
		for _, b := range healthyBackends {
			if wrr.remaining[b.URL] > 0 {
				wrr.remaining[b.URL]--
				return b
			}
		}

		for k := range wrr.remaining {
			wrr.remaining[k] = wrr.weights[k]
		}
	}
}

type LeastConnections struct {
	connections map[string]*int64
	mu          sync.Mutex
}

func NewLeastConnections() *LeastConnections {
	return &LeastConnections{
		connections: make(map[string]*int64),
	}
}

func (lc *LeastConnections) Select(backends []*Backend) *Backend {
	if len(backends) == 0 {
		return nil
	}

	healthyBackends := make([]*Backend, 0)
	for _, b := range backends {
		if b.IsAlive() {
			healthyBackends = append(healthyBackends, b)
		}
	}

	if len(healthyBackends) == 0 {
		return nil
	}

	lc.mu.Lock()
	defer lc.mu.Unlock()

	var selected *Backend
	minConns := int64(^uint64(0) >> 1)

	for _, b := range healthyBackends {
		if _, exists := lc.connections[b.URL]; !exists {
			var conns int64 = 0
			lc.connections[b.URL] = &conns
		}

		conns := atomic.LoadInt64(lc.connections[b.URL])
		if conns < minConns {
			minConns = conns
			selected = b
		}
	}

	if selected != nil {
		atomic.AddInt64(lc.connections[selected.URL], 1)
	}

	return selected
}

func (lc *LeastConnections) Release(url string) {
	lc.mu.Lock()
	if conns, exists := lc.connections[url]; exists {
		atomic.AddInt64(conns, -1)
	}
	lc.mu.Unlock()
}

func (b *Backend) IsAlive() bool {
	b.mu.RLock()
	defer b.mu.RUnlock()
	return b.Alive
}

func (b *Backend) SetAlive(alive bool) {
	b.mu.Lock()
	defer b.mu.Unlock()
	b.Alive = alive
}

func (b *Backend) IncrementFailures() {
	atomic.AddUint32(&b.Failures, 1)
}

func (b *Backend) ResetFailures() {
	atomic.StoreUint32(&b.Failures, 0)
}

func (b *Backend) GetFailures() uint32 {
	return atomic.LoadUint32(&b.Failures)
}
