variable "ecs_cluster_name" { type = string }
variable "ecs_service_name" { type = string }
variable "alb_arn_suffix" { type = string }            # e.g. aws_lb.app_lb.arn_suffix
variable "alb_target_group_arn_suffix" { type = string }
variable "log_group_name" { type = string }           # aws_cloudwatch_log_group.ecs_logs.name
variable "region" {
  type    = string
  default = "us-east-1"
}


# thresholds
variable "cpu_threshold" { 
type = number
default = 60
}

variable "memory_threshold" { 
type = number
default = 60
 }
variable "response_time_threshold" { 
type = number
default = 1.5
} # seconds
