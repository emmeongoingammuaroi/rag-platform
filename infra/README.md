# Infrastructure — AWS Deployment (Terraform)

## Architecture

```text
Internet → ALB (public subnets)
             ├── /api/*, /health, /ready → ECS API (private subnets)
             └── /* → ECS Web (private subnets)

ECS API → RDS PostgreSQL (private)
        → ElastiCache Redis (private)
        → Qdrant Cloud (external, free tier)
        → S3 (document storage)

ECS Worker (Celery) → same backends as API
```

## AWS Services

| Service           | Spec                     | Purpose                 | Est. cost/hr |
| ----------------- | ------------------------ | ----------------------- | ------------ |
| ECS Fargate       | 0.5 vCPU, 1GB × 3 tasks | API + Worker + Web      | ~$0.06       |
| RDS PostgreSQL    | db.t3.micro              | Database                | ~$0.02       |
| ElastiCache Redis | cache.t3.micro           | Celery broker + cache   | ~$0.02       |
| ALB               | 1 LB                     | Load balancer           | ~$0.02       |
| NAT Gateway       | 1                        | Private subnet internet | ~$0.05       |
| S3                | Standard                 | Document storage        | ~$0          |
| ECR               | —                        | Docker image registry   | ~$0          |
| Qdrant Cloud      | Free tier (1GB)          | Vector DB               | $0           |

Estimated total: ~$0.17/hr.

## Prerequisites

1. AWS CLI configured (`aws configure`)
2. Terraform >= 1.5 installed
3. Docker installed
4. Qdrant Cloud account (free tier)

## Quick Start

```bash
# 1. Setup Terraform state backend (one-time)
./scripts/setup-state.sh

# 2. Create terraform.tfvars from example
cp infra/terraform.tfvars.example infra/terraform.tfvars
# Edit with your secrets (db_password, openai_api_key, etc.)

# 3. Deploy everything
./scripts/deploy.sh

# 4. Teardown when done
./scripts/teardown.sh
```

## GitHub Actions CI/CD

The `deploy.yml` workflow supports manual trigger with deploy/destroy actions.

### Required Secrets

| Secret                  | Description                      |
| ----------------------- | -------------------------------- |
| `AWS_ACCESS_KEY_ID`     | IAM user access key              |
| `AWS_SECRET_ACCESS_KEY` | IAM user secret key              |
| `DB_PASSWORD`           | RDS master password              |
| `SECRET_KEY`            | Application JWT secret           |
| `OPENAI_API_KEY`        | OpenAI API key                   |
| `QDRANT_URL`            | Qdrant Cloud cluster URL         |
| `QDRANT_API_KEY`        | Qdrant Cloud API key             |
| `API_URL`               | ALB URL (set after first deploy) |
| `PRIVATE_SUBNETS`       | Comma-separated subnet IDs       |
| `ECS_SECURITY_GROUP`    | ECS security group ID            |

## File Structure

```text
infra/
├── main.tf              — Provider, backend config
├── variables.tf         — Input variables
├── outputs.tf           — Output values (ALB URL, endpoints)
├── vpc.tf               — VPC, subnets, NAT, security groups
├── ecr.tf               — ECR repositories (api, web)
├── ecs.tf               — ECS cluster, task definitions, services
├── rds.tf               — RDS PostgreSQL
├── elasticache.tf       — ElastiCache Redis
├── alb.tf               — ALB, target groups, listeners
├── s3.tf                — S3 bucket for documents
├── iam.tf               — IAM roles (execution + task)
├── terraform.tfvars.example — Template for secrets
└── .gitignore           — Excludes tfvars, state, .terraform/
```
