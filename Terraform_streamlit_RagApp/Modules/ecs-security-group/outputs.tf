output "security_group_id" {
  description = "Security group ID used by ECS tasks and ALB"
  value       = aws_security_group.ecs_sg.id
}

