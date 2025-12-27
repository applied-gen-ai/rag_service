resource "aws_cloudwatch_dashboard" "ecs_dashboard" {
  dashboard_name = "${var.ecs_service_name}-dashboard"

  dashboard_body = jsonencode({
    widgets = [

      # ===============================
      # CPU Utilization
      # ===============================
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6

        properties = {
          metrics = [
            [
              "AWS/ECS",
              "CPUUtilization",
              "ClusterName",
              var.ecs_cluster_name,
              "ServiceName",
              var.ecs_service_name
            ]
          ]
          period = 60
          stat   = "Average"
          region = var.region
          title  = "ECS CPU Utilization (%)"
        }
      },

      # ===============================
      # Memory Utilization
      # ===============================
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6

        properties = {
          metrics = [
            [
              "AWS/ECS",
              "MemoryUtilization",
              "ClusterName",
              var.ecs_cluster_name,
              "ServiceName",
              var.ecs_service_name
            ]
          ]
          period = 60
          stat   = "Average"
          region = var.region
          title  = "ECS Memory Utilization (%)"
        }
      },

      # ===============================
      # ALB Request Count
      # ===============================
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6

        properties = {
          metrics = [
            [
              "AWS/ApplicationELB",
              "RequestCount",
              "LoadBalancer",
              var.alb_arn_suffix
            ]
          ]
          period = 60
          stat   = "Sum"
          region = var.region
          title  = "ALB Request Count"
        }
      },

      # ===============================
      # ALB Target Response Time
      # ===============================
      {
        type   = "metric"
        x      = 12
        y      = 6
        width  = 12
        height = 6

        properties = {
          metrics = [
            [
              "AWS/ApplicationELB",
              "TargetResponseTime",
              "LoadBalancer",
              var.alb_arn_suffix
            ]
          ]
          period = 60
          stat   = "Average"
          region = var.region
          title  = "ALB Target Response Time (sec)"
        }
      },

      # ===============================
      # Running Task Count
      # ===============================
      {
        type   = "metric"
        x      = 0
        y      = 12
        width  = 12
        height = 6

        properties = {
          metrics = [
            [
              "AWS/ECS",
              "RunningTaskCount",
              "ClusterName",
              var.ecs_cluster_name,
              "ServiceName",
              var.ecs_service_name
            ]
          ]
          period = 60
          stat   = "Average"
          region = var.region
          title  = "Running ECS Tasks"
        }
      },

      # ===============================
      # Desired Task Count
      # ===============================
      {
        type   = "metric"
        x      = 12
        y      = 12
        width  = 12
        height = 6

        properties = {
          metrics = [
            [
              "AWS/ECS",
              "DesiredTaskCount",
              "ClusterName",
              var.ecs_cluster_name,
              "ServiceName",
              var.ecs_service_name
            ]
          ]
          period = 60
          stat   = "Average"
          region = var.region
          title  = "Desired ECS Tasks"
        }
      }
    ]

    start = "-PT30M"
    periodOverride = "inherit"
  })
}