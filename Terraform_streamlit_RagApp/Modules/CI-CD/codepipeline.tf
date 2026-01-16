# Use existing S3 bucket
data "aws_s3_bucket" "codepipeline_artifacts" {
  bucket = "${var.project_name}-artifacts-${var.environment}"
}

resource "aws_s3_bucket_public_access_block" "codepipeline_artifacts_block" {
  bucket = data.aws_s3_bucket.codepipeline_artifacts.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "codepipeline_artifacts_versioning" {
  bucket = data.aws_s3_bucket.codepipeline_artifacts.id

  versioning_configuration {
    status = "Enabled"
  }
}


# CodePipeline definition
resource "aws_codepipeline" "Ragapp_pipeline" {
  name     = "${var.project_name}-pipeline"
  role_arn = var.codepipeline_role_arn


artifact_store {
  location = data.aws_s3_bucket.codepipeline_artifacts.bucket
  type     = "S3"
}

  stage {
    name = "Source"

    action {
      name             = "Source"
      category         = "Source"
      owner            = "AWS"
      provider         = "CodeStarSourceConnection"
      version          = "1"
      output_artifacts = ["source_output"]

      configuration = {
        ConnectionArn    = var.github_connection_arn
        FullRepositoryId = "${var.github_owner}/${var.github_repo}" 
        BranchName       = var.github_branch
      }
    }
  }

  stage {
  name = "Build"

  action {
    name             = "Build"
    category         = "Build"
    owner            = "AWS"
    provider         = "CodeBuild"
    input_artifacts  = ["source_output"]
    output_artifacts = ["build_output"]
    version          = "1"

    configuration = {
  ProjectName = aws_codebuild_project.Ragapp_build.name
}
  }
}

stage {
  name = "Deploy"

  action {
    name            = "Deploy"
    category        = "Deploy"
    owner           = "AWS"
    provider        = "CodeDeployToECS"   # correct provider
    input_artifacts = ["build_output"]    # matches Build stage output
    version         = "1"

    configuration = {
      ApplicationName                = aws_codedeploy_app.ecs_app.name
      DeploymentGroupName            = aws_codedeploy_deployment_group.ecs_blue_green.deployment_group_name
      TaskDefinitionTemplateArtifact = "build_output"        # must match
      TaskDefinitionTemplatePath = "taskdef.json"  # or your json file
      # Optional: only if you package appspec in the artifact
      AppSpecTemplateArtifact        = "build_output"
      AppSpecTemplatePath            = "appspec.yml"
    }
  }
}
}
