Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "DIAGNOSTIC REPORT" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# 1. Get stopped task reason
Write-Host "1. Why did the last task stop?" -ForegroundColor Yellow
$STOPPED_TASK = aws ecs list-tasks --cluster $CLUSTER --service-name $SERVICE --desired-status STOPPED --query "taskArns[0]" --output text
if ($STOPPED_TASK) {
    aws ecs describe-tasks --cluster $CLUSTER --tasks $STOPPED_TASK --query "tasks[0].{StoppedReason:stoppedReason,StopCode:stopCode,ExitCode:containers[0].exitCode,ContainerReason:containers[0].reason}"
} else {
    Write-Host "No stopped tasks found" -ForegroundColor Red
}

Write-Host "`n2. Which task definition is the service using?" -ForegroundColor Yellow
aws ecs describe-services --cluster $CLUSTER --services $SERVICE --query "services[0].taskDefinition"

Write-Host "`n3. What are the health check settings in task definition?" -ForegroundColor Yellow
aws ecs describe-task-definition --task-definition rag-streaming-production:3 --query "taskDefinition.containerDefinitions[0].healthCheck"

Write-Host "`n4. What is the service health check grace period?" -ForegroundColor Yellow
aws ecs describe-services --cluster $CLUSTER --services $SERVICE --query "services[0].healthCheckGracePeriodSeconds"

Write-Host "`n========================================`n" -ForegroundColor Cyan