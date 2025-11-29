# ============================================================================
# Terraform Outputs - Important Information After Deployment
# ============================================================================

output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer"
  value       = aws_lb.main.dns_name
}

output "websocket_url" {
  description = "WebSocket URL to connect to RAG service"
  value       = "ws://${aws_lb.main.dns_name}/ws/chat"
}

output "health_check_url" {
  description = "Health check endpoint URL"
  value       = "http://${aws_lb.main.dns_name}/health"
}

output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = aws_ecs_cluster.main.name
}

output "ecs_service_name" {
  description = "Name of the ECS service"
  value       = aws_ecs_service.rag_service.name
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group name"
  value       = aws_cloudwatch_log_group.rag_service.name
}

output "alb_security_group_id" {
  description = "Security group ID for ALB"
  value       = aws_security_group.alb.id
}

output "fargate_security_group_id" {
  description = "Security group ID for Fargate tasks"
  value       = aws_security_group.fargate_tasks.id
}

# ============================================================================
# Management Commands
# ============================================================================

output "management_commands" {
  description = "Useful AWS CLI commands for managing the deployment"
  value = <<-EOT
    
    # View logs
    aws logs tail ${aws_cloudwatch_log_group.rag_service.name} --follow
    
    # Check service status
    aws ecs describe-services --cluster ${aws_ecs_cluster.main.name} --services ${aws_ecs_service.rag_service.name}
    
    # List running tasks
    aws ecs list-tasks --cluster ${aws_ecs_cluster.main.name} --service-name ${aws_ecs_service.rag_service.name}
    
    # Scale service
    aws ecs update-service --cluster ${aws_ecs_cluster.main.name} --service ${aws_ecs_service.rag_service.name} --desired-count 4
    
    # Force new deployment
    aws ecs update-service --cluster ${aws_ecs_cluster.main.name} --service ${aws_ecs_service.rag_service.name} --force-new-deployment
  EOT
}
