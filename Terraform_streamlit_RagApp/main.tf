module "iam" {
  source = "./Modules/iam"
  
  project_name          = var.project_name
  environment           = var.environment
  github_connection_arn = var.github_connection_arn
  codebuild_project_arn  = module.CI-CD.codebuild_project_arn

  artifact_bucket_name  = module.CI-CD.artifact_bucket_name
  artifact_bucket_arn   = module.CI-CD.artifact_bucket_arn
}

module "ecr" {
  source       = "./Modules/ecr"
}

module "ecs-security-group" {
  source = "./Modules/ecs-security-group"
  vpc_id = data.terraform_remote_state.eks.outputs.vpc_id
}


module "ecs-cluster" {
  source = "./Modules/ecs-cluster"
}

module "ecs-service" {
  source = "./Modules/ecs-service"

  name                = "rag-service"
  cluster_id          = module.ecs-cluster.cluster_id
  cluster_name        = module.ecs-cluster.cluster_name

  subnet_ids        = data.terraform_remote_state.eks.outputs.public_subnet_ids
  vpc_id            = data.terraform_remote_state.eks.outputs.vpc_id

  container_name = "my-container"
  container_port = 8000   # MUST match task definition
  desired_count  = 1

  log_group           = "/ecs/my-app"
  task_role_arn       = module.iam.task_execution_role_arn
  execution_role_arn  = module.iam.task_execution_role_arn
  region              = var.aws_region

  security_group_id = module.ecs-security-group.security_group_id
}

module "cloudwatch" {
  source = "./Modules/cloudwatch"

  ecs_cluster_name            = module.ecs-cluster.cluster_name
  ecs_service_name            = module.ecs-service.ecs_service_name
  alb_arn_suffix              = module.ecs-service.alb_arn_suffix
  alb_target_group_arn_suffix = module.ecs-service.blue_target_group_arn_suffix
  region                      = "us-east-1"
  log_group_name = "/ecs/my-app"

  cpu_threshold           = 60
  memory_threshold        = 60
  response_time_threshold = 1.5
}

module "CI-CD" {
  source = "./Modules/CI-CD"

  project_name = var.project_name
  environment  = var.environment

  github_connection_arn = var.github_connection_arn
  github_owner          = var.github_owner
  github_repo           = var.github_repo
  github_branch         = var.github_branch

  buildspec_file = "${path.root}/buildspec.yml"
  appspec_file   = "${path.root}/appspec.yml"

  ecs_cluster_name      = module.ecs-cluster.cluster_name
  ecs_service_name      = module.ecs-service.ecs_service_name
  alb_listener_arn      = module.ecs-service.alb_listener_arn
  alb_test_listener_arn = module.ecs-service.alb_test_listener_arn
  blue_tg_name  = module.ecs-service.blue_tg_name
  green_tg_name = module.ecs-service.green_tg_name


  codebuild_role_arn    = module.iam.codebuild_role_arn
  codedeploy_role_arn   = module.iam.codedeploy_role_arn
  codepipeline_role_arn = module.iam.codepipeline_role_arn
}
