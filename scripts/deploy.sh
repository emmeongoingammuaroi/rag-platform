#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
INFRA_DIR="$ROOT_DIR/infra"

AWS_REGION="${AWS_REGION:-ap-southeast-1}"
ECS_CLUSTER="rag-platform"

echo "=== RAG Platform Deploy ==="
echo "Region: $AWS_REGION"
echo ""

# Step 1: Terraform apply
echo "[1/6] Applying Terraform infrastructure..."
cd "$INFRA_DIR"
terraform init -input=false
terraform apply -auto-approve

# Capture outputs
ECR_API_REPO=$(terraform output -raw ecr_api_repository_url)
ECR_WEB_REPO=$(terraform output -raw ecr_web_repository_url)
ALB_URL=$(terraform output -raw alb_url)

echo ""
echo "  ECR API: $ECR_API_REPO"
echo "  ECR Web: $ECR_WEB_REPO"
echo "  ALB URL: $ALB_URL"
echo ""

# Step 2: Docker login to ECR
echo "[2/6] Logging into ECR..."
aws ecr get-login-password --region "$AWS_REGION" | \
  docker login --username AWS --password-stdin "$(echo "$ECR_API_REPO" | cut -d/ -f1)"

# Step 3: Build and push images
echo "[3/6] Building and pushing Docker images..."

echo "  Building API image..."
docker build -t "$ECR_API_REPO:latest" "$ROOT_DIR/backend"
docker push "$ECR_API_REPO:latest"

echo "  Building Web image..."
docker build -t "$ECR_WEB_REPO:latest" --target prod \
  --build-arg "VITE_API_URL=$ALB_URL" \
  "$ROOT_DIR/web"
docker push "$ECR_WEB_REPO:latest"

# Step 4: Run database migration
echo "[4/6] Running database migration..."
PRIVATE_SUBNETS=$(terraform output -json | jq -r '.[] | select(.value | type == "string") | empty' 2>/dev/null || true)

TASK_ARN=$(aws ecs run-task \
  --cluster "$ECS_CLUSTER" \
  --task-definition "${ECS_CLUSTER}-migrate" \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$(aws ec2 describe-subnets --filters "Name=tag:Name,Values=rag-platform-private-*" --query 'Subnets[*].SubnetId' --output text | tr '\t' ',')],securityGroups=[$(aws ec2 describe-security-groups --filters "Name=tag:Name,Values=rag-platform-ecs-sg" --query 'SecurityGroups[0].GroupId' --output text)],assignPublicIp=DISABLED}" \
  --query 'tasks[0].taskArn' \
  --output text)

echo "  Migration task: $TASK_ARN"
aws ecs wait tasks-stopped --cluster "$ECS_CLUSTER" --tasks "$TASK_ARN"

EXIT_CODE=$(aws ecs describe-tasks --cluster "$ECS_CLUSTER" --tasks "$TASK_ARN" \
  --query 'tasks[0].containers[0].exitCode' --output text)
if [ "$EXIT_CODE" != "0" ]; then
  echo "  ERROR: Migration failed (exit code: $EXIT_CODE)"
  exit 1
fi
echo "  Migration completed successfully"

# Step 5: Deploy ECS services
echo "[5/6] Deploying ECS services..."
aws ecs update-service --cluster "$ECS_CLUSTER" --service "${ECS_CLUSTER}-api" --force-new-deployment --no-cli-pager > /dev/null
aws ecs update-service --cluster "$ECS_CLUSTER" --service "${ECS_CLUSTER}-worker" --force-new-deployment --no-cli-pager > /dev/null
aws ecs update-service --cluster "$ECS_CLUSTER" --service "${ECS_CLUSTER}-web" --force-new-deployment --no-cli-pager > /dev/null

echo "  Waiting for API service to stabilize..."
aws ecs wait services-stable --cluster "$ECS_CLUSTER" --services "${ECS_CLUSTER}-api"

# Step 6: Smoke test
echo "[6/6] Running smoke test..."
for i in {1..10}; do
  if curl -sf "${ALB_URL}/health" > /dev/null 2>&1; then
    echo "  Health check passed!"
    echo ""
    echo "=== Deploy Complete ==="
    echo "Application URL: $ALB_URL"
    echo ""
    exit 0
  fi
  echo "  Attempt $i/10 — waiting 15s..."
  sleep 15
done

echo "  WARNING: Smoke test failed, but services may still be starting"
echo "  Application URL: $ALB_URL"
exit 1
