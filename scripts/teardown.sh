#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
INFRA_DIR="$ROOT_DIR/infra"

echo "=== RAG Platform Teardown ==="
echo ""
echo "WARNING: This will destroy ALL AWS infrastructure."
echo "  - ECS services (api, worker, web)"
echo "  - RDS PostgreSQL database (all data)"
echo "  - ElastiCache Redis"
echo "  - S3 bucket (all documents)"
echo "  - VPC, ALB, NAT Gateway"
echo "  - ECR repositories (all images)"
echo ""

read -p "Are you sure? Type 'destroy' to confirm: " CONFIRM
if [ "$CONFIRM" != "destroy" ]; then
  echo "Aborted."
  exit 0
fi

echo ""
echo "Destroying infrastructure..."
cd "$INFRA_DIR"
terraform init -input=false
terraform destroy -auto-approve

echo ""
echo "=== Teardown Complete ==="
echo "All resources have been destroyed."
