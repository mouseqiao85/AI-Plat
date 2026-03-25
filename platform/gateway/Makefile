.PHONY: build run test clean docker

APP_NAME=gateway
VERSION=$(shell git describe --tags --always --dirty 2>/dev/null || echo "dev")
BUILD_TIME=$(shell date -u '+%Y-%m-%d_%H:%M:%S')
LDFLAGS=-ldflags "-X main.Version=$(VERSION) -X main.BuildTime=$(BUILD_TIME)"

build:
	go build $(LDFLAGS) -o bin/$(APP_NAME) ./cmd/gateway

run:
	go run ./cmd/gateway

test:
	go test -v -race -coverprofile=coverage.out ./...

coverage: test
	go tool cover -html=coverage.out

lint:
	golangci-lint run

fmt:
	go fmt ./...

vet:
	go vet ./...

clean:
	rm -rf bin/
	rm -f coverage.out

deps:
	go mod download
	go mod tidy

docker:
	docker build -t ai-plat/gateway:$(VERSION) .

docker-run:
	docker run -p 8080:8080 ai-plat/gateway:$(VERSION)

docker-push:
	docker push ai-plat/gateway:$(VERSION)

install:
	go install ./cmd/gateway

dev:
	go run ./cmd/gateway -config config/config.yaml

benchmark:
	go test -bench=. -benchmem ./...

proto:
	protoc --go_out=. --go_opt=paths=source_relative \
		--go-grpc_out=. --go-grpc_opt=paths=source_relative \
		proto/*.proto

help:
	@echo "Available targets:"
	@echo "  build      - Build the binary"
	@echo "  run        - Run the application"
	@echo "  test       - Run tests"
	@echo "  coverage   - Generate test coverage report"
	@echo "  lint       - Run linter"
	@echo "  fmt        - Format code"
	@echo "  clean      - Clean build artifacts"
	@echo "  deps       - Download dependencies"
	@echo "  docker     - Build Docker image"
	@echo "  docker-run - Run Docker container"
	@echo "  benchmark  - Run benchmarks"
