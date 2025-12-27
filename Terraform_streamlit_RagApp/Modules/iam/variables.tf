variable "project_name" {
  description = "The name of the project"
  type        = string
}

variable "environment" {
  description = "Deployment environment"
  type        = string
}

variable "github_connection_arn" {
  description = "ARN of the GitHub connection"
  type        = string
}

variable "artifact_bucket_arn" {
  description = "ARN of the S3 bucket for CodePipeline artifacts"
  type        = string
}

variable "artifact_bucket_name" {
  description = "Name of the S3 bucket for CodePipeline artifacts"
  type        = string
}

variable "codebuild_project_arn" {
  description = "ARN of the CodeBuild project used by CodePipeline"
  type        = string
}
