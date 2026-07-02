# Infrastructure

Placeholder for Terraform/IaC configuration.

## Planned Structure

```
infra/
├── main.tf
├── variables.tf
├── outputs.tf
├── vpc.tf
├── ecs.tf
├── rds.tf
├── elasticache.tf
├── alb.tf
├── s3.tf
└── iam.tf
```

## AWS Services

- ECS Fargate — API + Celery worker
- RDS PostgreSQL — Database
- ElastiCache Redis — Celery broker + cache
- ALB — Load balancer + SSL termination
- S3 — Document storage
- Qdrant Cloud — Vector DB (free tier)
