# URL Shortener Microservices — Kubernetes & CI/CD Deployment

Production-ready deployment of a multi-service URL shortener on AWS EKS with full CI/CD, auto-scaling, monitoring, and load testing.

---

## Architecture

```
Internet
    │
    ▼
[NGINX Ingress Controller]
    │
    ▼
[Python Service :5000]  ──── Orchestrator / Dashboard / Analytics
    │              │
    ▼              ▼
[Go Service :8000]   [Node Service :3000]
 URL Shortener        URL Metadata
    │                     │
    └──────────┬───────────┘
               ▼
          [Redis :6379]
        Pub/Sub + Cache
               │
    ┌──────────┴──────────┐
    ▼                     ▼
[Prometheus]          [Grafana]
 Metrics               Dashboards
```

**CI/CD Flow:**
```
GitHub Push → GitHub Actions → SonarCloud → Docker Build → DockerHub → Helm Deploy → EKS
```

---

## Services

| Service | Port | Role | Tech |
|---------|------|------|------|
| Python | 5000 | Dashboard, analytics, orchestrator | Flask |
| Go | 8000 | URL shortener, fast redirects | Gin |
| Node.js | 3000 | URL metadata enrichment | Express |
| Redis | 6379 | Pub/Sub messaging, caching | Redis 7 |

---

## Prerequisites

### Local (Minikube)
```bash
brew install minikube kubectl helm
```

### AWS EKS (Terraform)
```bash
brew install awscli terraform eksctl
aws configure --profile ostad-account-2
```

### CI/CD
- DockerHub account
- GitHub repository
- SonarCloud account (free at sonarcloud.io)

---

## Quick Start — Local (Minikube)

### 1. Start Minikube

```bash
minikube start --cpus=4 --memory=8192
minikube addons enable ingress
minikube addons enable metrics-server
```

### 2. Build & Load Images

```bash
# Build all service images
eval $(minikube docker-env)

docker build -t python-service:latest ./python-service
docker build -t go-service:latest ./go-service
docker build -t node-service:latest ./node-service
```

### 3. Deploy via Helm

```bash
helm install urlshortener ./helm/urlshortener \
  --namespace urlshortener \
  --create-namespace \
  --set global.imageRegistry="" \
  --set global.imageTag=latest \
  --set pythonService.image.pullPolicy=Never \
  --set goService.image.pullPolicy=Never \
  --set nodeService.image.pullPolicy=Never
```

### 4. Add Hosts Entry

```bash
echo "$(minikube ip)  urlshortener.local" | sudo tee -a /etc/hosts
```

### 5. Access Application

```
Dashboard:    http://urlshortener.local
Go API:       http://urlshortener.local/go/
Node API:     http://urlshortener.local/node/
```

### 6. Verify Deployment

```bash
kubectl get pods -n urlshortener
kubectl get svc -n urlshortener
kubectl get hpa -n urlshortener
kubectl get ingress -n urlshortener
```

---

## AWS EKS Deployment (Terraform + Helm)

### Step 1 — Provision Infrastructure

```bash
cd terraform

# Initialize Terraform
terraform init

# Preview changes
terraform plan -var-file="terraform.tfvars"

# Apply (creates VPC, EKS cluster, node groups)
terraform apply -var-file="terraform.tfvars"
```

> **Note:** Cluster creation takes ~15 minutes.

### Step 2 — Configure kubectl

```bash
aws eks update-kubeconfig \
  --region eu-north-1 \
  --name urlshortener-cluster \
  --profile ostad-account-2
```

### Step 3 — Install Cluster Add-ons

```bash
# NGINX Ingress Controller
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --set controller.service.type=LoadBalancer

# Wait for LoadBalancer IP
kubectl get svc -n ingress-nginx -w

# Prometheus + Grafana (monitoring)
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  -f monitoring/prometheus-values.yaml
```

### Step 4 — Set DockerHub Credentials

```bash
kubectl create secret docker-registry dockerhub-secret \
  --docker-username=<YOUR_DOCKERHUB_USERNAME> \
  --docker-password=<YOUR_DOCKERHUB_TOKEN> \
  --namespace urlshortener
```

### Step 5 — Deploy Application

```bash
# Get your DockerHub username
DOCKERHUB_USERNAME=<YOUR_DOCKERHUB_USERNAME>

helm install urlshortener ./helm/urlshortener \
  --namespace urlshortener \
  --create-namespace \
  --set global.imageRegistry="${DOCKERHUB_USERNAME}" \
  --set global.imageTag=latest \
  --set ingress.host=urlshortener.YOUR_DOMAIN.com
```

### Step 6 — Get External IP

```bash
kubectl get ingress -n urlshortener
# OR
kubectl get svc ingress-nginx-controller -n ingress-nginx
```

### Teardown

```bash
helm uninstall urlshortener -n urlshortener
helm uninstall monitoring -n monitoring
helm uninstall ingress-nginx -n ingress-nginx

cd terraform && terraform destroy -var-file="terraform.tfvars"
```

---

## CI/CD Pipeline (GitHub Actions)

The pipeline triggers on every push to `main`.

### Pipeline Stages

| Stage | Action |
|-------|--------|
| 1. Test | Run unit tests per service |
| 2. SonarCloud | Code quality gate analysis |
| 3. Build | Docker images built with commit SHA tag |
| 4. Push | Images pushed to DockerHub |
| 5. Deploy | Helm upgrade on EKS cluster |

### Required GitHub Secrets

Go to your GitHub repo → Settings → Secrets and variables → Actions. Add:

| Secret | Value |
|--------|-------|
| `DOCKERHUB_USERNAME` | Your DockerHub username |
| `DOCKERHUB_TOKEN` | DockerHub access token |
| `AWS_ACCESS_KEY_ID` | IAM user access key |
| `AWS_SECRET_ACCESS_KEY` | IAM user secret key |
| `SONAR_TOKEN` | Token from sonarcloud.io |

### Get AWS Credentials

```bash
# Create IAM user with EKS permissions
aws iam create-user --user-name github-actions --profile ostad-account-2

# Attach policies
aws iam attach-user-policy \
  --user-name github-actions \
  --policy-arn arn:aws:iam::aws:policy/AmazonEKSClusterPolicy \
  --profile ostad-account-2

# Create access keys
aws iam create-access-key --user-name github-actions --profile ostad-account-2
```

---

## Monitoring

### Access Grafana

```bash
# Get Grafana password
kubectl get secret monitoring-grafana \
  -n monitoring \
  -o jsonpath="{.data.admin-password}" | base64 -d

# Port-forward locally
kubectl port-forward svc/monitoring-grafana 3001:80 -n monitoring
# Open: http://localhost:3001  (admin / password from above)
```

### Import Dashboards

In Grafana → Dashboards → Import:

| Dashboard | ID |
|-----------|----|
| Kubernetes Cluster Overview | 6417 |
| HPA Auto-scaling | 10257 |
| Pod Resource Usage | 6336 |

### Access Prometheus

```bash
kubectl port-forward svc/monitoring-kube-prometheus-prometheus 9090:9090 -n monitoring
# Open: http://localhost:9090
```

---

## Load Testing (Locust)

### Install Locust

```bash
pip install locust
```

### Run Load Test

```bash
# Headless (CI mode) - simulates 12 PM traffic spike
locust -f load-testing/locustfile.py \
  --host http://urlshortener.local \
  --users 200 \
  --spawn-rate 20 \
  --run-time 5m \
  --headless \
  --html load-testing/report.html

# Interactive UI mode
locust -f load-testing/locustfile.py \
  --host http://urlshortener.local
# Open: http://localhost:8089
```

### Watch HPA Scale During Load Test

```bash
# In a separate terminal
kubectl get hpa -n urlshortener -w
kubectl top pods -n urlshortener
```

---

## SonarCloud Setup

1. Sign in at [sonarcloud.io](https://sonarcloud.io) with GitHub
2. Click **+** → **Analyze new project** → select this repo
3. Copy the `SONAR_TOKEN` → add to GitHub secrets
4. Update `sonar-project.properties`:
   - Replace `<YOUR_SONAR_ORG>` with your SonarCloud organization key
   - Replace `<YOUR_PROJECT_KEY>` with your project key
5. Push to `main` — pipeline runs automatically

Quality gate thresholds (configured in `sonar-project.properties`):
- Coverage: ≥ 80%
- Duplications: ≤ 3%
- Code smells: 0 blockers/criticals

---

## Project Structure

```
capstan-project/
├── go-service/              # Go URL shortener service
├── python-service/          # Python dashboard & analytics
├── node-service/            # Node.js metadata service
├── terraform/               # AWS EKS infrastructure as code
│   ├── main.tf              # Provider config
│   ├── vpc.tf               # VPC, subnets, NAT gateway
│   ├── eks.tf               # EKS cluster & node groups
│   ├── variables.tf         # Input variables
│   ├── outputs.tf           # Output values
│   └── terraform.tfvars     # Variable values (set your own)
├── helm/
│   └── urlshortener/        # Helm chart (all services)
│       ├── Chart.yaml
│       ├── values.yaml
│       └── templates/
├── k8s/                     # Raw Kubernetes manifests (reference)
│   ├── namespace.yaml
│   ├── redis/
│   ├── go-service/
│   ├── python-service/
│   ├── node-service/
│   └── ingress.yaml
├── monitoring/
│   ├── prometheus-values.yaml
│   └── grafana-values.yaml
├── load-testing/
│   └── locustfile.py        # Locust load test (Python)
├── .github/
│   └── workflows/
│       └── deploy.yml       # GitHub Actions CI/CD pipeline
├── sonar-project.properties # SonarCloud config
└── docker-compose.yml       # Local dev without Kubernetes
```

---

## Environment Variables Reference

| Variable | Service | Description |
|----------|---------|-------------|
| `GO_SERVICE_URL` | Python | Go service internal URL |
| `NODE_SERVICE_URL` | Python | Node service internal URL |
| `REDIS_HOST` | All | Redis host |
| `REDIS_PORT` | All | Redis port (default: 6379) |
| `PYTHON_SERVICE_URL` | Go | Python fallback event URL |

---

## Troubleshooting

**Pods not starting:**
```bash
kubectl describe pod <pod-name> -n urlshortener
kubectl logs <pod-name> -n urlshortener
```

**HPA not scaling:**
```bash
# Verify metrics-server is running
kubectl get apiservice v1beta1.metrics.k8s.io
kubectl top nodes
```

**Ingress not reachable (Minikube):**
```bash
minikube tunnel  # Run in separate terminal (requires sudo)
```

**Terraform state issues:**
```bash
terraform refresh -var-file="terraform.tfvars"
```
