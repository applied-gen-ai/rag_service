data "terraform_remote_state" "eks" {
  backend = "s3"

  config = {
    bucket        = "kubernetes-terraform-api"
    key           = "eks-cluster/terraform.tfstate"
    region        = "us-east-1"
  }
}
