#!/usr/bin/env bash
set -euo pipefail

AWS_REGION="${AWS_REGION:-ap-southeast-1}"
BUCKET_NAME="rag-platform-terraform-state"
TABLE_NAME="rag-platform-terraform-lock"

echo "=== Setup Terraform State Backend ==="
echo "Region: $AWS_REGION"
echo ""

# Create S3 bucket for state
echo "[1/2] Creating S3 bucket for Terraform state..."
if aws s3api head-bucket --bucket "$BUCKET_NAME" 2>/dev/null; then
  echo "  Bucket already exists"
else
  aws s3api create-bucket \
    --bucket "$BUCKET_NAME" \
    --region "$AWS_REGION" \
    --create-bucket-configuration LocationConstraint="$AWS_REGION"

  aws s3api put-bucket-versioning \
    --bucket "$BUCKET_NAME" \
    --versioning-configuration Status=Enabled

  aws s3api put-bucket-encryption \
    --bucket "$BUCKET_NAME" \
    --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'

  aws s3api put-public-access-block \
    --bucket "$BUCKET_NAME" \
    --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

  echo "  Created: $BUCKET_NAME"
fi

# Create DynamoDB table for state locking
echo "[2/2] Creating DynamoDB table for state locking..."
if aws dynamodb describe-table --table-name "$TABLE_NAME" --region "$AWS_REGION" > /dev/null 2>&1; then
  echo "  Table already exists"
else
  aws dynamodb create-table \
    --table-name "$TABLE_NAME" \
    --attribute-definitions AttributeName=LockID,AttributeType=S \
    --key-schema AttributeName=LockID,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region "$AWS_REGION"

  echo "  Created: $TABLE_NAME"
fi

echo ""
echo "=== State Backend Ready ==="
echo "You can now run: cd infra && terraform init"
