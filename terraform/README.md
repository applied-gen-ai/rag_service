# RAG Service Terraform Deployment

**deploy_rag** - AWS Fargate deployment for RAG Streaming Service

---

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Detailed Steps](#detailed-steps)
- [Configuration](#configuration)
- [Deployment](#deployment)
- [Post-Deployment](#post-deployment)
- [Troubleshooting](#troubleshooting)
- [Cost Estimation](#cost-estimation)

---

## Overview

This Terraform configuration deploys a production-ready RAG (Retrieval-Augmented Generation) streaming service on AWS Fargate with:

- **Serverless containers** (AWS Fargate - no EC2 management)
- **Auto-scaling** (1-10 tasks based on CPU/Memory)
- **Load balancing** (ALB with WebSocket support)
- **High availability** (Multi-AZ deployment)
- **Monitoring** (CloudWatch Logs + Container Insights)

**Architecture:**
```
Client → ALB (WebSocket) → Fargate Tasks → Qdrant + EKS LLM
```

---

## Prerequisites

### 1. **AWS CLI Configured**
```bash
aws --version
aws sts get-caller-identity
```

### 2. **Terraform Installed**
```bash
terraform --version
# Should be >= 1.0
```

### 3. **Docker Image in ECR**
```bash
# Build and push your image first
docker build -t rag-streaming:latest .
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account>.dkr.ecr.us-east-1.amazonaws.com
docker tag rag-streaming:latest <account>.dkr.ecr.us-east-1.amazonaws.com/rag-streaming:latest
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/rag-streaming:latest
```

### 4. **Existing Infrastructure**
- VPC with public and private subnets
- TheCode_ttft LLM service running on EKS
- Qdrant vector database accessible

### 5. **API Keys & Credentials**
- Qdrant URL and API key
- HuggingFace token
- AWS credentials with appropriate permissions

---

## Quick Start
```bash
# 1. Navigate to terraform directory
cd E:\RAG\TheCode_rag\terraform

# 2. Edit terraform.tfvars with your values
notepad terraform.tfvars

# 3. Initialize Terraform
terraform init

# 4. Review the plan
terraform plan

# 5. Deploy!
terraform apply

# 6. Get the WebSocket URL
terraform output websocket_url
```

---

## Detailed Steps

### **Step 1: Configure Variables**

Edit `terraform.tfvars` and fill in your values:
```hcl
# Required values
aws_account_id = "123456789012"
vpc_id = "vpc-xxxxx"
container_image = "123456789012.dkr.ecr.us-east-1.amazonaws.com/rag-streaming:latest"
llm_endpoint = "k8s-default-llmservi-xxxxx.elb.us-east-1.amazonaws.com:50051"
qdrant_url = "https://your-cluster.cloud.qdrant.io"
qdrant_api_key = "your-api-key"
hugging_face_token = "hf_xxxxx"
```

**How to find your values:**
```bash
# AWS Account ID
aws sts get-caller-identity --query Account --output text

# VPC ID
aws ec2 describe-vpcs --query "Vpcs[*].[VpcId,Tags[?Key=='Name'].Value|[0]]" --output table

# LLM Endpoint (from TheCode_ttft)
kubectl get svc llm-service -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'

# ECR Repository
aws ecr describe-repositories --repository-names rag-streaming --query "repositories[0].repositoryUri" --output text
```

### **Step 2: Initialize Terraform**
```bash
terraform init
```

This will:
- Download AWS provider plugins
- Initialize the backend
- Prepare modules

### **Step 3: Plan Deployment**
```bash
terraform plan -out=deployment.plan
```

Review the plan carefully. It will create:
- 1 ECS Cluster
- 1 ECS Service
- 1 Task Definition
- 1 Application Load Balancer
- 1 Target Group
- 2 Security Groups
- 1 CloudWatch Log Group
- 2 IAM Roles
- 2 Auto-scaling Policies

### **Step 4: Apply Configuration**
```bash
terraform apply deployment.plan
```

Or directly:
```bash
terraform apply
# Type 'yes' when prompted
```

**Deployment time:** ~5-10 minutes

### **Step 5: Verify Deployment**
```bash
# Get outputs
terraform output

# Check service status
aws ecs describe-services \
  --cluster $(terraform output -raw ecs_cluster_name) \
  --services $(terraform output -raw ecs_service_name)

# Test health endpoint
curl http://$(terraform output -raw alb_dns_name)/health
```

---

## Configuration

### **Resource Sizing**

| Environment | CPU | Memory | Tasks |
|-------------|-----|--------|-------|
| Development | 512 | 2048 MB | 1-3 |
| Staging | 1024 | 3072 MB | 1-5 |
| Production | 1024 | 3072 MB | 2-10 |

### **Auto-scaling Triggers**

- **CPU > 70%** → Scale out
- **Memory > 80%** → Scale out
- **CPU < 50%** for 5 minutes → Scale in

### **Cost Optimization**
```hcl
# Reduce for dev/testing
desired_count = 1
min_capacity = 1
max_capacity = 3
task_cpu = 512
task_memory = 2048
```

---

## Post-Deployment

### **1. Get Connection URL**
```bash
terraform output websocket_url
# ws://rag-streaming-alb-xxxxx.us-east-1.elb.amazonaws.com/ws/chat
```

### **2. Test the Service**
```bash
# Health check
curl http://$(terraform output -raw alb_dns_name)/health

# Service info
curl http://$(terraform output -raw alb_dns_name)/

# Metrics
curl http://$(terraform output -raw alb_dns_name)/metrics
```

### **3. View Logs**
```bash
# Stream logs in real-time
aws logs tail $(terraform output -raw cloudwatch_log_group) --follow

# View last 10 minutes
aws logs tail $(terraform output -raw cloudwatch_log_group) --since 10m
```

### **4. Scale the Service**
```bash
# Scale to 5 tasks
aws ecs update-service \
  --cluster $(terraform output -raw ecs_cluster_name) \
  --service $(terraform output -raw ecs_service_name) \
  --desired-count 5
```

### **5. Update Docker Image**
```bash
# Push new image to ECR
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/rag-streaming:latest

# Force new deployment
aws ecs update-service \
  --cluster $(terraform output -raw ecs_cluster_name) \
  --service $(terraform output -raw ecs_service_name) \
  --force-new-deployment
```

---

## Troubleshooting

### **Issue: Service won't start**
```bash
# Check task status
aws ecs list-tasks --cluster $(terraform output -raw ecs_cluster_name)

# Describe tasks
aws ecs describe-tasks \
  --cluster $(terraform output -raw ecs_cluster_name) \
  --tasks <task-arn>

# Check logs
aws logs tail $(terraform output -raw cloudwatch_log_group) --follow
```

**Common causes:**
- Docker image not found in ECR
- LLM endpoint unreachable
- Qdrant credentials invalid
- Insufficient resources (CPU/Memory)

### **Issue: Health checks failing**
```bash
# Check task logs
aws logs tail $(terraform output -raw cloudwatch_log_group) --since 5m

# Verify ALB target health
aws elbv2 describe-target-health \
  --target-group-arn $(aws elbv2 describe-target-groups \
    --names rag-streaming-production-tg \
    --query "TargetGroups[0].TargetGroupArn" --output text)
```

**Common causes:**
- Application not starting (check logs)
- Health check endpoint returning non-200
- Security group blocking traffic

### **Issue: Can't connect to WebSocket**
```bash
# Verify ALB listener
aws elbv2 describe-listeners \
  --load-balancer-arn $(terraform output -raw alb_arn)

# Check security groups
aws ec2 describe-security-groups \
  --group-ids $(terraform output -raw alb_security_group_id)
```

**Common causes:**
- ALB not internet-facing
- Security group blocking port 80
- Client using wrong URL format

---

## Cost Estimation

**Monthly costs (approximate):**

| Component | Specification | Monthly Cost |
|-----------|---------------|--------------|
| Fargate Tasks | 2 tasks × 1 vCPU × 3GB | ~$50 |
| Application Load Balancer | 1 ALB | ~$23 |
| Data Transfer | ~100 GB/month | ~$9 |
| CloudWatch Logs | ~10 GB ingestion | ~$5 |
| **Total** | | **~$87/month** |

**Cost reduction strategies:**
- Use Fargate Spot (70% discount, less reliable)
- Reduce min_capacity to 1
- Decrease log retention to 3 days
- Use smaller task sizes for dev/test

---

## Maintenance

### **Update Service**
```bash
# Update task definition (after changing variables)
terraform apply -target=aws_ecs_task_definition.rag_service

# Deploy changes
aws ecs update-service \
  --cluster $(terraform output -raw ecs_cluster_name) \
  --service $(terraform output -raw ecs_service_name) \
  --force-new-deployment
```

### **Modify Infrastructure**
```bash
# Edit terraform.tfvars
# Then apply changes
terraform plan
terraform apply
```

### **Destroy Everything**
```bash
# Destroy all resources
terraform destroy

# Or destroy specific resource
terraform destroy -target=aws_ecs_service.rag_service
```

---

## Additional Resources

- [AWS Fargate Documentation](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/AWS_Fargate.html)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [ALB WebSocket Support](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/introduction.html)

---

## Support

If you encounter issues:

1. Check CloudWatch Logs first
2. Verify all credentials and endpoints
3. Review security group rules
4. Check ECS service events

**Useful commands:**
```bash
# Service events
aws ecs describe-services \
  --cluster $(terraform output -raw ecs_cluster_name) \
  --services $(terraform output -raw ecs_service_name) \
  --query "services[0].events[0:5]"

# Task failures
aws ecs describe-tasks \
  --cluster $(terraform output -raw ecs_cluster_name) \
  --tasks <task-arn> \
  --query "tasks[0].containers[0].reason"
```

---

**Happy Deploying!**