resource "aws_lb" "ecs_alb" {
  name               = "${var.name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [var.security_group_id]
  subnets            = var.subnet_ids
  idle_timeout = 300
}

resource "aws_lb_target_group" "blue" {
  name        = "rag-blue"
  port        = var.container_port
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    path                = "/"
    protocol            = "HTTP"
    matcher             = "200"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 2
  }
}

resource "aws_lb_target_group" "green" {
  name        = "rag-green"
  port        = var.container_port
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    path                = "/"
    protocol            = "HTTP"
    matcher             = "200"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 2
  }
}

resource "aws_lb_listener" "production" {
  load_balancer_arn = aws_lb.ecs_alb.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.blue.arn
  }
}

resource "aws_lb_listener" "test" {
  load_balancer_arn = aws_lb.ecs_alb.arn
  port              = 8080
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.green.arn
  }
}

resource "aws_ecs_task_definition" "bootstrap" {
  family                   = "${var.name}-bootstrap"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "1024"
  memory                   = "2048"

  execution_role_arn = var.execution_role_arn
  task_role_arn      = var.task_role_arn

  container_definitions = jsonencode([
    {
      name  = var.container_name
      image = "public.ecr.aws/docker/library/nginx:latest"

      portMappings = [
        {
          containerPort = var.container_port
          protocol      = "tcp"
        }
      ]

      essential = true
    }
  ])
}


resource "aws_ecs_service" "rag_app" {
  name    = var.name
  cluster = var.cluster_id

  desired_count = 1
  launch_type   = "FARGATE"

  task_definition = aws_ecs_task_definition.bootstrap.arn

  deployment_controller {
    type = "CODE_DEPLOY"
  }

  network_configuration {
    subnets          = var.subnet_ids
    security_groups  = [var.security_group_id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.blue.arn
    container_name   = "my-container"
    container_port   = 8000
  }

  lifecycle {
    ignore_changes = [
      task_definition,
      load_balancer
    ]
  }
}
