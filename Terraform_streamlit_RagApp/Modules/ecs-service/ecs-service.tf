resource "aws_ecs_service" "rag-app-service" {
  name            = var.name
  cluster         = var.cluster_id
  task_definition = var.task_definition_arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  deployment_controller {
    type = "CODE_DEPLOY"
  }

    load_balancer {
    target_group_arn = aws_lb_target_group.blue.arn
    container_name   = "my-container"
    container_port   = 8000
  }

  deployment_minimum_healthy_percent = 100
  deployment_maximum_percent         = 200

  network_configuration {
    subnets          = var.subnet_ids
    security_groups  = [var.security_group_id]
    assign_public_ip = true
  }

  # IMPORTANT: For CodeDeploy blue/green, we don’t attach TG directly here.
  depends_on = [
    aws_lb_listener.production,
    aws_lb_listener.test
  ]
}

# Application Load Balancer
resource "aws_lb" "ecs_alb" {
  name               = "${var.name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [var.security_group_id]
  subnets            = var.subnet_ids
}

# Blue Target Group
resource "aws_lb_target_group" "blue" {
  name        = "rag-b"
  port        = var.container_port
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    path                = "/health"
    protocol            = "HTTP"
    matcher             = "200"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 2
}

}

# Green Target Group
resource "aws_lb_target_group" "green" {
  name        = "rag-g"
  port        = var.container_port
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    path                = "/health"
    protocol            = "HTTP"
    matcher             = "200"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 2
}

}

# Production Listener (live traffic)
resource "aws_lb_listener" "production" {
  load_balancer_arn = aws_lb.ecs_alb.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.blue.arn
  }
}

# Test Listener (validation traffic for green)
resource "aws_lb_listener" "test" {
  load_balancer_arn = aws_lb.ecs_alb.arn
  port              = 8080
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.green.arn
  }
}
