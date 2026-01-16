output "task_definition_arn" {
  description = "ARN of the ECS task definition"
  value       = aws_ecs_task_definition.app.arn
}

output "security_group_id" {
  description = "Security group ID used by ECS tasks and ALB"
  value       = aws_security_group.ecs_sg.id
}

output "log_group_name" {
  description = "CloudWatch log group name"
  value       = data.aws_cloudwatch_log_group.ecs_logs.name
}
