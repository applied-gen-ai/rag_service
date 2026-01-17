variable "aws_region" {
  default = "us-east-1"
}

variable "vpc_cidr" {}
variable "public_subnet_cidrs" {
  type = list(string)
}
variable "private_subnet_cidrs" {
  type = list(string)
}
variable "availability_zones" {
  type = list(string)
}

variable "project_name" {
  description = "The name of the CICD project"
  type        = string
}

# GitHub repo details
variable "github_connection_arn" {
  description = "ARN of the AWS CodeStar connection to GitHub"
  type        = string
}

variable "github_owner" {
  description = "GitHub organization or username"
  type        = string
}

variable "github_repo" {
  description = "GitHub repository name"
  type        = string
}

variable "github_branch" {
  description = "Branch to trigger the pipeline from"
  type        = string
  default     = "main"
}

# ECS & deployment related
variable "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  type        = string
}

variable "ecs_service_name" {
  description = "Name of the ECS service"
  type        = string
}

# Environment (e.g. dev, staging, prod)
variable "environment" {
  description = "Deployment environment"
  type        = string
}

