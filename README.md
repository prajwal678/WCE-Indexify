# **Web Content Extraction API**

## **Prerequisites**
- Docker and Docker Compose
- Kubernetes cluster (e.g., Minikube for local development)
- Python 3.9+
- `kubectl` CLI tool
- `minikube` CLI tool

## **Local Setup**
   ```bash
   git clone <your-repository>
   cd <your-repository>

   python -m venv venv
   source venv/bin/activate

   pip install -r requirements.txt
   ```
## **Running a Local Kubernetes Cluster with Minikube**
   ```bash
   minikube start
   minikube addons enable metrics-server
   minikube addons enable ingress

   kubectl cluster-info
   ```
## **Building Docker Images**
   ```bash
   eval $(minikube docker-env)

   docker build -t web-content-extractor-api:latest ./api
   docker build -t tensorlake/indexify:latest .
   ```

## **Deploying Containers to Kubernetes**
   ```bash
   kubectl create configmap extractors-config --from-file=extractors/

   kubectl apply -f kubernetes/deployment.yaml

   kubectl get pods
   kubectl get services
   ```

## **Running Tests**
1. Unit tests:
   ```bash
   pytest tests/test_api.py
   ```

2. Load tests:
   ```bash
   python -m tests.test_load
   ```

3. Kubernetes tests:
   ```bash
   python -m tests.test_kubernetes
   ```

## **Monitoring**

- Metrics: [http://localhost:8000/metrics](http://localhost:8000/metrics)
- Health Check: [http://localhost:8000/health](http://localhost:8000/health)

can use curl to make direct url requests also to check when buidign locally
single-
```bash
curl -X POST http://localhost:8000/extract \
  -H "Content-Type: application/json" \
  -d '{
    "url": "http://example.com",
    "schema": {
      "type": "object",
      "properties": {
        "title": {"type": "string"},
        "content": {"type": "array", "items": {"type": "string"}}
      },
      "required": ["title"]
    }
  }'
```

batch/multiple - 
```bash
curl -X POST http://localhost:8000/extract/batch \
  -H "Content-Type: application/json" \
  -d '{
    "urls": ["http://example.com", "http://example.org"],
    "schema": {
      "type": "object",
      "properties": {
        "title": {"type": "string"},
        "content": {"type": "array", "items": {"type": "string"}}
      },
      "required": ["title"]
    }
  }'
```