resource "aws_cloudwatch_log_group" "ecs_logs" {
  name              = "/ecs/my-app"
  retention_in_days = 7
}

# 5. ECS Task Definition
resource "aws_ecs_task_definition" "app" {
  family                   = "my-app"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "2048"
  memory                   = "4096"
  execution_role_arn = var.execution_role_arn
  task_role_arn      = var.task_role_arn


  container_definitions = jsonencode([{
  name  = "my-container"
  image = var.ecr_image_url

  portMappings = [{
    containerPort = 8000
    protocol      = "tcp"
  }]

  environment = [
    {
      name  = "LLM_TARGET"
      value = var.llm_target
    }
  ]

  logConfiguration = {
    logDriver = "awslogs"
    options = {
      awslogs-group         = aws_cloudwatch_log_group.ecs_logs.name
      awslogs-region        = "us-east-1"
      awslogs-stream-prefix = "ecs"
    }
  }
}])
}

# 7. Security Group for ALB & ECS
resource "aws_security_group" "alb_sg" {
  name        = "alb-sg"
  description = "Allow HTTP/HTTPS for ALB"
  vpc_id      = var.vpc_id

  # Allow browser traffic on port 80
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Keep this only if you want to reach 8501 directly (not required if all goes through port 80)
  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
