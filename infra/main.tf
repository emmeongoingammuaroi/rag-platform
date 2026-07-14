terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "rag-platform-terraform-state"
    key            = "terraform.tfstate"
    region         = "ap-southeast-1"
    dynamodb_table = "rag-platform-terraform-lock"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "rag-platform"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}
