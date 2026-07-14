variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ap-southeast-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "rag-platform"
}

# Database
variable "db_username" {
  description = "RDS master username"
  type        = string
  default     = "postgres"
}

variable "db_password" {
  description = "RDS master password"
  type        = string
  sensitive   = true
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "ai_rag_db"
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

# ECS
variable "ecs_api_cpu" {
  description = "API task CPU units (1024 = 1 vCPU)"
  type        = number
  default     = 512
}

variable "ecs_api_memory" {
  description = "API task memory in MiB"
  type        = number
  default     = 1024
}

variable "ecs_worker_cpu" {
  description = "Celery worker task CPU units"
  type        = number
  default     = 512
}

variable "ecs_worker_memory" {
  description = "Celery worker task memory in MiB"
  type        = number
  default     = 1024
}

variable "api_desired_count" {
  description = "Number of API tasks"
  type        = number
  default     = 1
}

variable "worker_desired_count" {
  description = "Number of Celery worker tasks"
  type        = number
  default     = 1
}

# ElastiCache
variable "redis_node_type" {
  description = "ElastiCache Redis node type"
  type        = string
  default     = "cache.t3.micro"
}

# Application secrets
variable "secret_key" {
  description = "Application secret key for JWT"
  type        = string
  sensitive   = true
}

variable "openai_api_key" {
  description = "OpenAI API key"
  type        = string
  sensitive   = true
}

variable "qdrant_url" {
  description = "Qdrant Cloud URL"
  type        = string
}

variable "qdrant_api_key" {
  description = "Qdrant Cloud API key"
  type        = string
  sensitive   = true
  default     = ""
}

# VPC
variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "Availability zones"
  type        = list(string)
  default     = ["ap-southeast-1a", "ap-southeast-1b"]
}
