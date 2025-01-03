#Web Content Extraction API

##Prerequisites

Docker and Docker Compose
Kubernetes cluster (Minikube for local development)
Python 3.9+
kubectl CLI tool
minikube CLI tool

###Local setup
'''bash
git clone <your-repository>
cd <your-repository>


python -m venv venv
source venv/bin/activate

pip install -r requirements.txt
'''

### local cluster using minikube
'''bash
minikube start

minikube addons enable metrics-server
minikube addons enable ingress

kubectl cluster-info
'''

### docker builds
'''bash
eval $(minikube docker-env)  # On Windows: minikube docker-env | Invoke-Expression

docker build -t web-content-extractor-api:latest ./api
docker build -t tensorlake/indexify:latest .
'''

### container push/deploy onto kubernetes
'''bash
kubectl create configmap extractors-config --from-file=extractors/
kubectl apply -f kubernetes/deployment.yaml

kubectl get pods
kubectl get services
'''

### tests
'''bash
#ubit tests
pytest tests/test_api.py

#load tests
python -m tests.test_load

# kubernetes tests
python -m tests.test_kubernetes
'''

### monitoring
http://localhost:8000/metrics
http://localhost:8000/health

Can also use curl as for making requests 
single -
'''bash
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
'''

batch - 
'''bash
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
'''