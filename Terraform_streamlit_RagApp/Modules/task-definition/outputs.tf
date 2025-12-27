output "log_group_name" {
  description = "Name of the CloudWatch Log Group"
  value       = aws_cloudwatch_log_group.ecs_logs.name
}

output "task_definition_arn" {
  description = "ARN of the ECS task definition"
  value       = aws_ecs_task_definition.app.arn
}

output "container_name" {
  description = "Name of the ECS container"
  value       = "my-container"
}

output "security_group_id" {
  description = "Security Group ID for ALB and ECS tasks"
  value       = aws_security_group.alb_sg.id
}
