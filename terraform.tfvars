availability_zones     = ["us-east-1a", "us-east-1b"]
vpc_cidr               = "10.0.0.0/16"
public_subnet_cidrs    = ["10.0.1.0/24", "10.0.2.0/24"]
private_subnet_cidrs   = ["10.0.3.0/24", "10.0.4.0/24"]
github_connection_arn = "arn:aws:codeconnections:us-east-1:826695974453:connection/a1587b46-c4b3-47cb-b7da-fc8081bb4a98"

github_owner = "applied-gen-ai"
github_repo  = "rag_service"
github_branch = "main"
project_name = "rag-app"
ecs_cluster_name  = "RagApp-fargate-cluster"
ecs_service_name  = "rag-app-service"
environment = "dev"