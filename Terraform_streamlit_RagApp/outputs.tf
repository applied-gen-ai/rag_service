output "alb_dns_name" {
  value = module.ecs-service.alb_dns_name
}

output "cluster_name" {
  value = module.ecs-cluster.cluster_name
}

output "task_definition_arn" {
  value = module.task-definition.task_definition_arn
}

output "pipeline_name" {
  value = module.CI-CD.pipeline_name
}

output "codebuild_project" {
  value = module.CI-CD.codebuild_project_name
}

output "repository_url" {
  value = module.ecr.ecr_repo_url
}

output "artifact_bucket_name" {
  value = module.CI-CD.artifact_bucket_name
}

output "artifact_bucket_arn" {
  value = module.CI-CD.artifact_bucket_arn
}