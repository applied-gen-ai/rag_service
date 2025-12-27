#################################
# ECS Roles
#################################

# ECS Task Execution Role
resource "aws_iam_role" "ecs_task_execution" {
  name = "${var.project_name}-ecsTaskExecutionRole"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        },
        Action = "sts:AssumeRole"
      }
    ]
  })
}

# This is the missing resource referenced in outputs.tf
resource "aws_iam_role" "task_execution_role" {
  name = "${var.project_name}-${var.environment}-task-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        },
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_execution_policy" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy_attachment" "task_execution_policy" {
  role       = aws_iam_role.task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# ECS Task Role (for app inside container)
resource "aws_iam_role" "ecs_task_role" {
  name = "${var.project_name}-ecsTaskRole"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        },
        Action = "sts:AssumeRole"
      }
    ]
  })
}

# ECS CloudWatch policies
resource "aws_iam_role_policy" "cloudwatch_metrics_policy" {
  name = "${var.project_name}-cloudwatch-metrics"
  role = aws_iam_role.ecs_task_role.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = ["cloudwatch:PutMetricData"],
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy" "cloudwatch_logs_policy" {
  name = "${var.project_name}-cloudwatch-logs"
  role = aws_iam_role.ecs_task_role.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = [
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams",
          "logs:GetLogEvents",
          "logs:StartQuery",
          "logs:GetQueryResults"
        ],
        Resource = "*"
      }
    ]
  })
}

#################################
# CodePipeline Role
#################################
resource "aws_iam_role" "codepipeline_role" {
  name = "${var.project_name}-pipeline-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          Service = "codepipeline.amazonaws.com"
        },
        Action = "sts:AssumeRole"
      }
    ]
  })
}

# FIXED: Use variable instead of direct resource reference
resource "aws_iam_role_policy" "codepipeline_policy" {
  name = "${var.project_name}-pipeline-policy"
  role = aws_iam_role.codepipeline_role.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "s3:GetObject",
          "s3:GetObjectVersion",
          "s3:PutObject",
          "s3:GetBucketVersioning"
        ],
        Resource = [
          var.artifact_bucket_arn,
          "${var.artifact_bucket_arn}/*"
        ]
      },
      {
        Effect   = "Allow",
        Action   = ["codestar-connections:UseConnection"],
        Resource = var.github_connection_arn
      },
      {
        Effect   = "Allow",
        Action   = [
          "codebuild:StartBuild",
          "codebuild:BatchGetBuilds"
        ],
        Resource = var.codebuild_project_arn
      },
      {
        Effect = "Allow",
        Action = [
          "codedeploy:GetApplication",
          "codedeploy:GetApplicationRevision",
          "codedeploy:RegisterApplicationRevision",
          "codedeploy:GetDeployment",
          "codedeploy:CreateDeployment",
          "codedeploy:GetDeploymentConfig"
        ],
        Resource = "*"
      },
      #  Add ECS permissions here
      {
        Effect = "Allow",
        Action = [
          "ecs:RegisterTaskDefinition",
          "ecs:DescribeTaskDefinition"
        ],
        Resource = "*"
      },
      
            {
        Effect = "Allow",
        Action = "iam:PassRole",
        Resource = [
          aws_iam_role.ecs_task_execution.arn,
          aws_iam_role.task_execution_role.arn
        ],
        Condition = {
          StringEquals = {
            "iam:PassedToService" = "ecs-tasks.amazonaws.com"
          }
        }
      }
    ]
  })
}



#################################
# CodeBuild Role
#################################
resource "aws_iam_role" "codebuild_role" {
  name = "${var.project_name}-codebuild-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          Service = "codebuild.amazonaws.com"
        },
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_policy" "codebuild_ecr_policy" {
  name = "${var.project_name}-codebuild-ecr"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      # ECR permissions - UPDATED with missing permissions
      {
        Effect   = "Allow",
        Action   = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:CompleteLayerUpload",
          "ecr:GetDownloadUrlForLayer",
          "ecr:InitiateLayerUpload",
          "ecr:PutImage",
          "ecr:UploadLayerPart",
          "ecr:BatchGetImage",
          # NEW: Add these missing permissions
          "ecr:DescribeRepositories",
          "ecr:CreateRepository",
          "ecr:DescribeImages",
          "ecr:ListImages"
        ],
        Resource = "*"
      },
      # CloudWatch Logs permissions
      {
        Effect   = "Allow",
        Action   = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        Resource = "*"
      },
      # S3 artifacts permissions
      {
        Effect = "Allow",
        Action = [
          "s3:GetObject",
          "s3:GetObjectVersion",
          "s3:PutObject"
        ],
        Resource = [
          var.artifact_bucket_arn,
          "${var.artifact_bucket_arn}/*"
        ]
      },
      # NEW: Add STS permissions for debugging
      {
        Effect = "Allow",
        Action = [
          "sts:GetCallerIdentity"
        ],
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "codebuild_ecr" {
  role       = aws_iam_role.codebuild_role.name
  policy_arn = aws_iam_policy.codebuild_ecr_policy.arn
}

#################################
# CodeDeploy Role
#################################
resource "aws_iam_role" "codedeploy_role" {
  name = "${var.project_name}-codedeploy-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          Service = "codedeploy.amazonaws.com"
        },
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "codedeploy_policy" {
  role       = aws_iam_role.codedeploy_role.name
  policy_arn = "arn:aws:iam::aws:policy/AWSCodeDeployRoleForECS"
}