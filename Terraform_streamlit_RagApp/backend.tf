terraform {
  backend "s3" {
    bucket        = "kubernetes-terraform-api"
    key           = "repo-a/terraform.tfstate"
    region        = "us-east-1"
    use_lockfile  = true
  }
}
