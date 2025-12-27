# SNS topic for alerts
resource "aws_sns_topic" "alerts" {
  name = "app-alerts"
}

# First email
resource "aws_sns_topic_subscription" "email_alert_havish" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = "havish802@gmail.com"
}

# Second email
resource "aws_sns_topic_subscription" "email_alert_kanuri" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = "ssskanuri@gmail.com"
}