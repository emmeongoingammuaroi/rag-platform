output "alb_dns_name" {
  description = "ALB DNS name (application URL)"
  value       = aws_lb.main.dns_name
}

output "alb_url" {
  description = "Full application URL"
  value       = "http://${aws_lb.main.dns_name}"
}

output "ecr_api_repository_url" {
  description = "ECR repository URL for API image"
  value       = aws_ecr_repository.api.repository_url
}

output "ecr_web_repository_url" {
  description = "ECR repository URL for web image"
  value       = aws_ecr_repository.web.repository_url
}

output "rds_endpoint" {
  description = "RDS instance endpoint"
  value       = aws_db_instance.main.endpoint
}

output "redis_endpoint" {
  description = "ElastiCache Redis endpoint"
  value       = aws_elasticache_cluster.main.cache_nodes[0].address
}

output "s3_bucket_name" {
  description = "S3 bucket for document storage"
  value       = aws_s3_bucket.documents.id
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.main.name
}

output "api_log_group" {
  description = "CloudWatch log group for API"
  value       = aws_cloudwatch_log_group.api.name
}
