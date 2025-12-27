resource "aws_codedeploy_app" "ecs_app" {
  compute_platform = "ECS"
  name             = "${var.project_name}-ecs-app"
}

resource "aws_codedeploy_deployment_group" "ecs_blue_green" {
  app_name              = aws_codedeploy_app.ecs_app.name
  deployment_group_name = "${var.project_name}-ecs-deployment"
  service_role_arn      = var.codedeploy_role_arn

  deployment_style {
    deployment_type   = "BLUE_GREEN"
    deployment_option = "WITH_TRAFFIC_CONTROL"
  }

  deployment_config_name = "CodeDeployDefault.ECSAllAtOnce"

  ecs_service {
    cluster_name = var.ecs_cluster_name
    service_name = var.ecs_service_name
  }

  load_balancer_info {
  target_group_pair_info {
    prod_traffic_route {
      listener_arns = [var.alb_listener_arn]
    }
    test_traffic_route {
      listener_arns = [var.alb_test_listener_arn]
    }
    target_group {
        name = var.blue_tg_name   # must be name
      }
      target_group {
        name = var.green_tg_name  # must be name
      }
    }
  }

  blue_green_deployment_config {
    deployment_ready_option {
      action_on_timeout    = "CONTINUE_DEPLOYMENT"
      wait_time_in_minutes = 0
    }
    terminate_blue_instances_on_deployment_success {
      action                          = "TERMINATE"
      termination_wait_time_in_minutes = 5
    }
  }

  auto_rollback_configuration {
    enabled = true
    events  = ["DEPLOYMENT_FAILURE"]
  }
}

