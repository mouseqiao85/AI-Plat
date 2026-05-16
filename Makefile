.PHONY: run-go run-python build test clean

run-go:
	cd cmd/gateway && go run main.go

run-python:
	cd agent && python -m uvicorn main:app --reload --port 8001

build:
	cd cmd/gateway && go build -o ../../bin/gateway .

test-go:
	go test ./...

test-python:
	cd agent && python -m pytest tests/ -v

test: test-go test-python

bench-go:
	go test ./... -bench=. -benchmem -run=^$

bench-python:
	cd agent && python -m pytest tests/test_performance.py -v -s

perf-python:
	cd agent && python -m pytest tests/test_performance.py tests/test_concurrency.py -v -s

clean:
	rm -rf data/
	rm -rf bin/
	rm -rf agent/data/

deps:
	go mod tidy
	cd agent && pip install -e ".[dev]"
