data "aws_cloudwatch_log_group" "ecs_logs" {
  name = var.log_group_name
}

# ECS + ALB Security Group
resource "aws_security_group" "ecs_sg" {
  name        = "ecs-alb-sg"
  description = "Allow ALB to ECS traffic"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 80
    to_port     = 80
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
