#!/bin/bash
set -e

echo "=========================================="
echo "AI-Plat Platform Deployment Script"
echo "=========================================="

ENVIRONMENT=${1:-dev}
NAMESPACE="ai-plat"

echo "Environment: $ENVIRONMENT"
echo "Namespace: $NAMESPACE"

# Check kubectl
if ! command -v kubectl &> /dev/null; then
    echo "Error: kubectl is not installed"
    exit 1
fi

# Check cluster connection
echo "Checking cluster connection..."
if ! kubectl cluster-info &> /dev/null; then
    echo "Error: Cannot connect to Kubernetes cluster"
    exit 1
fi

echo "✓ Cluster connection OK"

# Create namespace if not exists
echo "Creating namespace..."
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

# Apply kustomize
echo "Applying Kubernetes manifests..."
kubectl apply -k deploy/kubernetes/overlays/$ENVIRONMENT

# Wait for deployments
echo "Waiting for deployments to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/api-service -n $NAMESPACE
kubectl wait --for=condition=available --timeout=300s deployment/gateway-service -n $NAMESPACE
kubectl wait --for=condition=available --timeout=300s deployment/web-service -n $NAMESPACE

echo ""
echo "=========================================="
echo "Deployment completed!"
echo "=========================================="
echo ""
echo "Pods:"
kubectl get pods -n $NAMESPACE
echo ""
echo "Services:"
kubectl get services -n $NAMESPACE
echo ""
echo "Access the platform:"
echo "  Web: http://ai-plat.example.com"
echo "  API: http://ai-plat.example.com/api"
echo "  Docs: http://ai-plat.example.com/docs"
