resource "aws_ecs_cluster" "main" {
  name = var.project_name

  setting {
    name  = "containerInsights"
    value = "disabled"
  }
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "api" {
  name              = "/ecs/${var.project_name}/api"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_group" "worker" {
  name              = "/ecs/${var.project_name}/worker"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_group" "web" {
  name              = "/ecs/${var.project_name}/web"
  retention_in_days = 7
}

# API Task Definition
resource "aws_ecs_task_definition" "api" {
  family                   = "${var.project_name}-api"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.ecs_api_cpu
  memory                   = var.ecs_api_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name  = "api"
    image = "${aws_ecr_repository.api.repository_url}:latest"

    portMappings = [{
      containerPort = 8000
      protocol      = "tcp"
    }]

    environment = [
      { name = "DATABASE_URL", value = "postgresql+asyncpg://${var.db_username}:${var.db_password}@${aws_db_instance.main.endpoint}/${var.db_name}" },
      { name = "REDIS_URL", value = "redis://${aws_elasticache_cluster.main.cache_nodes[0].address}:6379/0" },
      { name = "QDRANT_URL", value = var.qdrant_url },
      { name = "QDRANT_API_KEY", value = var.qdrant_api_key },
      { name = "SECRET_KEY", value = var.secret_key },
      { name = "OPENAI_API_KEY", value = var.openai_api_key },
      { name = "S3_BUCKET_NAME", value = aws_s3_bucket.documents.id },
      { name = "S3_REGION", value = var.aws_region },
      { name = "S3_ENDPOINT_URL", value = "" },
      { name = "S3_ACCESS_KEY", value = "" },
      { name = "S3_SECRET_KEY", value = "" },
      { name = "ENVIRONMENT", value = "production" },
      { name = "DEBUG", value = "false" },
      { name = "LOG_FORMAT", value = "json" },
      { name = "RERANKER_ENABLED", value = "false" },
      { name = "HYDE_ENABLED", value = "false" },
      { name = "OCR_ENABLED", value = "false" },
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.api.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "api"
      }
    }

    healthCheck = {
      command     = ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()\""]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 10
    }
  }])
}

# Celery Worker Task Definition
resource "aws_ecs_task_definition" "worker" {
  family                   = "${var.project_name}-worker"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.ecs_worker_cpu
  memory                   = var.ecs_worker_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name  = "worker"
    image = "${aws_ecr_repository.api.repository_url}:latest"

    command = ["celery", "-A", "app.core.celery_app.celery_app", "worker", "--loglevel=INFO", "--without-heartbeat", "--without-mingle"]

    environment = [
      { name = "DATABASE_URL", value = "postgresql+asyncpg://${var.db_username}:${var.db_password}@${aws_db_instance.main.endpoint}/${var.db_name}" },
      { name = "REDIS_URL", value = "redis://${aws_elasticache_cluster.main.cache_nodes[0].address}:6379/0" },
      { name = "QDRANT_URL", value = var.qdrant_url },
      { name = "QDRANT_API_KEY", value = var.qdrant_api_key },
      { name = "SECRET_KEY", value = var.secret_key },
      { name = "OPENAI_API_KEY", value = var.openai_api_key },
      { name = "S3_BUCKET_NAME", value = aws_s3_bucket.documents.id },
      { name = "S3_REGION", value = var.aws_region },
      { name = "S3_ENDPOINT_URL", value = "" },
      { name = "S3_ACCESS_KEY", value = "" },
      { name = "S3_SECRET_KEY", value = "" },
      { name = "ENVIRONMENT", value = "production" },
      { name = "DEBUG", value = "false" },
      { name = "LOG_FORMAT", value = "json" },
      { name = "RERANKER_ENABLED", value = "false" },
      { name = "HYDE_ENABLED", value = "false" },
      { name = "OCR_ENABLED", value = "false" },
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.worker.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "worker"
      }
    }
  }])
}

# Web Task Definition
resource "aws_ecs_task_definition" "web" {
  family                   = "${var.project_name}-web"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name  = "web"
    image = "${aws_ecr_repository.web.repository_url}:latest"

    portMappings = [{
      containerPort = 3000
      protocol      = "tcp"
    }]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.web.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "web"
      }
    }

    healthCheck = {
      command     = ["CMD-SHELL", "curl -f http://localhost:3000/ || exit 1"]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 10
    }
  }])
}

# Migration Task Definition (one-off)
resource "aws_ecs_task_definition" "migrate" {
  family                   = "${var.project_name}-migrate"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name  = "migrate"
    image = "${aws_ecr_repository.api.repository_url}:latest"

    command = ["alembic", "upgrade", "head"]

    environment = [
      { name = "DATABASE_URL", value = "postgresql+asyncpg://${var.db_username}:${var.db_password}@${aws_db_instance.main.endpoint}/${var.db_name}" },
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.api.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "migrate"
      }
    }
  }])
}

# ECS Services

resource "aws_ecs_service" "api" {
  name            = "${var.project_name}-api"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.api_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = 8000
  }

  depends_on = [aws_lb_listener.http]
}

resource "aws_ecs_service" "worker" {
  name            = "${var.project_name}-worker"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.worker.arn
  desired_count   = var.worker_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = false
  }
}

resource "aws_ecs_service" "web" {
  name            = "${var.project_name}-web"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.web.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.web.arn
    container_name   = "web"
    container_port   = 3000
  }

  depends_on = [aws_lb_listener.http]
}
