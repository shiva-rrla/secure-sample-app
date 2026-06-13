# Secure Sample Application – DevSecOps Reference Architecture

A production-grade, cloud-native microservice blueprint demonstrating end-to-end **DevSecOps** practices across code, pipeline, infrastructure, and runtime.

## Architecture Overview

```


┌─────────────────────────────────────────────────────────────┐
│                          Developer                           │
│                      (shift-left security)                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  CI/CD Pipeline  (.github/workflows/devsecops.yml)           │
│  ├── Pre-commit: Secret scan (TruffleHog)                    │
│  ├── Build: Dependency scan (Trivy FS) + Unit tests          │
│  ├── SAST: Semgrep / CodeQL                                  │
│  ├── Image: Build → Container scan (Trivy) → Sign (Cosign)   │
│  └── Deploy: GitOps commit to Kustomize overlay              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Infrastructure as Code  (terraform/)                        │
│  ├── VPC: Private subnets, NAT, Flow Logs, KMS               │
│  └── EKS: Envelope encryption, IRSA (OIDC), Private API      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Kubernetes Runtime  (k8s/)                                  │
│  ├── Namespace: Pod Security Standards (restricted)          │
│  ├── Deployment: Non-root, read-only FS, seccomp, limits     │
│  ├── NetworkPolicy: Zero-trust ingress/egress                │
│  └── OPA/Gatekeeper: Policy enforcement (non-root)           │
└─────────────────────────────────────────────────────────────┘
```



## Repository Structure

```
secure-sample-app/
├── app/                          # Python FastAPI application
│   ├── main.py                   # Application entrypoint (non-root, structured logs)
│   ├── requirements.txt          # Pinned dependencies with lockfile
│   ├── Dockerfile                # Multi-stage, distroless-hardened image
│   └── tests/                    # Unit tests (pytest)
├── .github/workflows/
│   └── devsecops.yml             # Full CI/CD pipeline with security gates
├── infra/
│   ├── terraform/                # Hardened AWS infrastructure (EKS + VPC)
│   └── k8s/                      # Kubernetes manifests (Kustomize + Policies)
│       ├── base/
│       │   ├── namespace.yaml
│       │   ├── serviceaccount.yaml
│       │   ├── deployment.yaml
│       │   ├── service.yaml
│       │   ├── network-policy.yaml
│       │   └── ...
│       └── overlays/production/
│           └── kustomization.yaml
└── policies/
    └── k8s/
        └── gatekeeper-require-non-root.yaml
```



## Technology Stack

| Layer | Technology |
|-------|------------|
| **Language** | Python 3.12 + FastAPI |
| **Container** | Multi-stage Docker build (non-root, minimal attack surface) |
| **CI/CD** | GitHub Actions |
| **Infrastructure** | Terraform + AWS (EKS, VPC, KMS) |
| **Orchestration** | Kubernetes (Kustomize + GitOps) |
| **Security Scanning** | TruffleHog, Semgrep, Trivy, Checkov, Cosign |
| **Policy Enforcement** | OPA Gatekeeper / Kyverno |
| **Observability** | Prometheus annotations (metrics), structured JSON logging |

## Quick Start

### 1. Local Development

```bash
cd app
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest tests/ -v
python main.py
# Open http://localhost:8080/healthz
```

### 2. Build & Scan Container Locally

```bash
cd app
docker build -t secure-sample-app:local .

# Scan the image for vulnerabilities
trivy image secure-sample-app:local
```

### 3. Deploy Infrastructure (AWS)

```bash
cd terraform
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

> ⚠️ **Prerequisites:** AWS credentials, valid SSL certificate for OIDC (usually handled automatically).

### 4. Deploy Application to EKS

```bash
aws eks update-kubeconfig --region us-east-1 --name secure-sample-app

# Deploy base + production overlay
kubectl apply -k k8s/overlays/production/

# Verify
kubectl get pods -n secure-sample-app
kubectl get svc -n secure-sample-app
```

## Security Checklist

### Code (Shift-Left)
- [x] Dependencies pinned in `requirements.txt` with lockfile
- [x] No secrets or credentials in source code
- [x] Structured JSON logging (no PII)
- [x] Graceful `SIGTERM` handling
- [x] Health (`/healthz`) and readiness (`/readyz`) probes

### Build & CI/CD
- [x] **Secret Scanning:** TruffleHog scans every commit
- [x] **SAST:** Semgrep runs against OWASP rules on every PR
- [x] **SCA:** Trivy scans filesystem dependencies for CVEs
- [x] **Container Scan:** Trivy scans the final image before push
- [x] **Image Signing:** Cosign keyless signing of artifacts
- [x] **IaC Scan:** Checkov validates Terraform configurations
- [x] GitOps deployment (no kubeconfig in CI runners)

### Infrastructure
- [x] **Network:** Private subnets for workloads; NAT Gateways for egress
- [x] **Encryption:** KMS envelope encryption for EKS secrets + VPC Flow Logs
- [x] **Access:** IAM Roles via OIDC (IRSA) – no long-lived AWS keys
- [x] **Logging:** VPC Flow Logs enabled for forensic analysis
- [x] **Hardening:** No SSH to nodes; minimal security groups

### Runtime (Kubernetes)
- [x] **Pod Security:** `runAsNonRoot`, `readOnlyRootFilesystem`, `seccomp`
- [x] **Network Policy:** Default-deny all ingress/egress; explicit allow rules only
- [x] **RBAC:** Dedicated ServiceAccount; `automountServiceAccountToken: false`
- [x] **Policy Enforcement:** Gatekeeper constraint requires non-root containers
- [x] **Resource Limits:** CPU/memory requests and limits defined
- [x] **Topology:** Pods spread across availability zones

## Key Design Decisions

1. **Distroless vs. Slim:**
   We use `python:3.12-slim-bookworm` with a manually created non-root user – easier to debug than pure distroless while still minimizing the attack surface. Build-stage dependencies are discarded.

2. **Private EKS API Endpoint:**
   The cluster API is accessible via private endpoint (`endpoint_private_access = true`). Public access is enabled for demo convenience; restrict `public_access_cidrs` to your corporate IP range in production.

3. **No `hpa.yaml` in Overlay:**
   Kustomize overlays are intentionally kept minimal. Horizontal Pod Autoscaling should be added via a separate patch or Helm values when load patterns are understood.

4. **OIDC / IRSA Over Node IAM:**
   The node IAM role only has ECR read, EKS worker, and CNI policies. Application-level AWS permissions (e.g., S3, DynamoDB) should be granted via IRSA roles attached to the ServiceAccount.

## License

MIT – Free to use as a reference scaffold for your own projects.
