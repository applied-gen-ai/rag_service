# General settings


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




# Networking
variable "vpc_id" {
  description = "VPC ID for security group"
  type        = string
}

