# General
variable "name" {
  description = "Name of the ECS service"
  type        = string
}

variable "cluster_id" {
  description = "ECS cluster ID where the service will run"
  type        = string
}

variable "cluster_name" {
  description = "Name of the ECS cluster (for autoscaling resource ID)"
  type        = string
}

variable "task_definition_arn" {
  description = "ARN of the ECS task definition to run"
  type        = string
}

variable "desired_count" {
  description = "Desired number of ECS tasks"
  type        = number
  default     = 1
}

# Networking
variable "subnet_ids" {
  description = "List of subnet IDs for ECS tasks"
  type        = list(string)
}

variable "security_group_id" {
  description = "Security group ID for the ECS service and ALB"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID used by target group"
  type        = string
}

# Container
variable "container_name" {
  description = "Name of the container defined in the task"
  type        = string
}

variable "container_port" {
  description = "Port the container listens on"
  type        = number
  default     = 8501
}

# Autoscaling
variable "target_value" {
  description = "Target value for ALBRequestCountPerTarget in autoscaling"
  type        = number
  default     = 100.0
}

# Logging
variable "log_group" {
  description = "CloudWatch Logs group name"
  type        = string
}

variable "region" {
  description = "AWS region"
  type        = string
}

# IAM roles (used in task_definition module, if you're combining logic)
variable "execution_role_arn" {
  description = "IAM role ARN that ECS uses to pull images and write logs"
  type        = string
}

variable "task_role_arn" {
  description = "IAM role ARN that the container assumes"
  type        = string
}