output "codebuild_project_name" {
  value = aws_codebuild_project.Ragapp_build.name
}

output "codedeploy_app_name" {
  value = aws_codedeploy_app.ecs_app.name
}

output "codedeploy_deployment_group" {
  value = aws_codedeploy_deployment_group.ecs_blue_green.deployment_group_name
}

output "pipeline_name" {
  value = aws_codepipeline.Ragapp_pipeline.name
}

output "artifact_bucket_name" {
  description = "Name of the S3 bucket for CodePipeline artifacts"
  value       = aws_s3_bucket.codepipeline_artifacts.bucket
}

output "artifact_bucket_arn" {
  description = "ARN of the S3 bucket for CodePipeline artifacts"
  value       = aws_s3_bucket.codepipeline_artifacts.arn
}

output "codepipeline_arn" {
  description = "ARN of the CodePipeline"
  value       = aws_codepipeline.Ragapp_pipeline.arn
}

output "codebuild_project_arn" {
  description = "ARN of the CodeBuild project"
  value       = aws_codebuild_project.Ragapp_build.arn
}
