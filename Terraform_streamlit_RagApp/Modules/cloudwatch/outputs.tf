output "dashboard_name" {
  value = aws_cloudwatch_dashboard.ecs_dashboard.dashboard_name
}

output "dashboard_url" {
  value = "https://console.aws.amazon.com/cloudwatch/home#dashboards:name=${aws_cloudwatch_dashboard.ecs_dashboard.dashboard_name}"
}

output "cpu_alarm_arn" { value = aws_cloudwatch_metric_alarm.cpu_high.arn }
output "memory_alarm_arn" { value = aws_cloudwatch_metric_alarm.memory_high.arn }
output "response_alarm_arn" { value = aws_cloudwatch_metric_alarm.response_time_high.arn }
