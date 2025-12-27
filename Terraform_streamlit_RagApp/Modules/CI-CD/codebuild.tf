resource "aws_codebuild_project" "Ragapp_build" {
  name          = "${var.project_name}-build"
  service_role = var.codebuild_role_arn


  build_timeout = 20

  artifacts {
    type = "CODEPIPELINE"
  }

  environment {
    compute_type    = "BUILD_GENERAL1_SMALL"
    image           = "aws/codebuild/standard:5.0"
    type            = "LINUX_CONTAINER"
    privileged_mode = true

    environment_variable {
      name  = "AWS_REGION"
      value = "us-east-1"
    }

    environment_variable {
      name  = "ACCOUNT_ID"
      value = "826695974453"
    }

    environment_variable {
      name  = "ECR_REPO_NAME"
      value = "streamlit-app-1"
    }

    environment_variable {
      name  = "ECS_CONTAINER_NAME"
      value = "my-container"
    }
  }

  source {
  type      = "CODEPIPELINE"
  buildspec       = "buildspec.yml"
}
}
