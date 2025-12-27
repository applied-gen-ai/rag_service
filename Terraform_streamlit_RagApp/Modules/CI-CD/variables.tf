# From GitHub
variable "github_connection_arn" {}
variable "github_owner" {}
variable "github_repo" {}
variable "github_branch" {}

# ECS/ALB
variable "ecs_cluster_name" {}
variable "ecs_service_name" {}
variable "alb_listener_arn" {}
variable "alb_test_listener_arn" {}



variable "project_name" {}
variable "environment" {}

variable "codebuild_role_arn" {
  type        = string
  description = "IAM Role ARN for CodeBuild"
}

variable "codedeploy_role_arn" {
  type        = string
  description = "IAM Role ARN for CodeDeploy"
}

variable "codepipeline_role_arn" {
  type        = string
  description = "IAM Role ARN for CodePipeline"
}

variable "buildspec_file" {
  description = "Path to buildspec.yml"
  type        = string
}

variable "appspec_file" {
  description = "Path to appspec.yml"
  type        = string
}

variable "blue_tg_name" {
  description = "Name of the blue target group"
  type        = string
}

variable "green_tg_name" {
  description = "Name of the green target group"
  type        = string
}

