output "ecs_service_name" {
  description = "Name of the ECS service"
  value       = aws_ecs_service.rag-app-service.name
}

output "ecs_service_arn" {
  description = "ARN of the ECS service"
  value       = aws_ecs_service.rag-app-service.arn
}

output "ecs_cluster_name" {
  value = var.cluster_name
}

output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer"
  value       = aws_lb.ecs_alb.dns_name
}

# Blue/Green Outputs
output "alb_listener_arn" {
  description = "Production ALB Listener ARN"
  value       = aws_lb_listener.production.arn
}

output "alb_test_listener_arn" {
  description = "Test ALB Listener ARN"
  value       = aws_lb_listener.test.arn
}

output "blue_target_group" {
  description = "Blue Target Group ARN"
  value       = aws_lb_target_group.blue.arn
}

output "green_target_group" {
  description = "Green Target Group ARN"
  value       = aws_lb_target_group.green.arn
}

output "alb_arn_suffix" {
  description = "ARN suffix of the Application Load Balancer"
  value       = aws_lb.ecs_alb.arn_suffix
}

output "blue_target_group_arn_suffix" {
  description = "ARN suffix of the Blue Target Group"
  value       = aws_lb_target_group.blue.arn_suffix
}

output "green_target_group_arn_suffix" {
  description = "ARN suffix of the Green Target Group"
  value       = aws_lb_target_group.green.arn_suffix
}

output "blue_tg_name" {
  value = aws_lb_target_group.blue.name
}

output "green_tg_name" {
  value = aws_lb_target_group.green.name
}

output "prod_listener_arn" {
  value = aws_lb_listener.production.arn
}

output "test_listener_arn" {
  value = aws_lb_listener.test.arn
}
