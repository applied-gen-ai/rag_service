# General settings
variable "ecr_image_url" {
  description = "ECR image URL for the container"
  type        = string
}

variable "log_group_name" {
  description = "Name of the CloudWatch Log Group"
  type        = string
  default     = "/ecs/my-app"
}

variable "log_retention_in_days" {
  description = "Retention period for CloudWatch logs"
  type        = number
  default     = 7
}

# Task sizing
variable "cpu" {
  description = "CPU units for ECS Fargate task"
  type        = string
  default     = "1024"
}

variable "memory" {
  description = "Memory for ECS Fargate task"
  type        = string
  default     = "2048"
}

# IAM roles
variable "execution_role_arn" {
  description = "Execution role ARN for ECS task"
  type        = string
}

variable "task_role_arn" {
  description = "Task role ARN assumed by the container"
  type        = string
}

# Networking
variable "vpc_id" {
  description = "VPC ID for security group"
  type        = string
}

variable "llm_target" {
  description = "gRPC endpoint of LLM running in EKS"
  type        = string
}

