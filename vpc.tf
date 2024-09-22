module "vpc_dev" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.13.0"

  name            = "dev"
  cidr            = "10.50.0.0/16"                     # Non-overlapping with other networks
  public_subnets  = ["10.50.10.0/24", "10.50.20.0/24"] # Within your network cidr, non-overlapping other subnets
  private_subnets = ["10.50.30.0/24", "10.50.40.0/24"] # Within your network cidr, non-overlapping other subnets
  azs             = slice(sort(data.aws_availability_zones.available.names), 0, 3)

  enable_nat_gateway = true
  single_nat_gateway = true

  tags = {
    DeployedBy = "terraform"
    Name       = "dev"
  }
}

module "vpc_stage" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.13.0"

  name            = "stage"
  cidr            = "10.30.0.0/16"                     # Non-overlapping with other networks
  public_subnets  = ["10.30.10.0/24", "10.30.20.0/24"] # Within your network cidr, non-overlapping other subnets
  private_subnets = ["10.30.30.0/24", "10.30.40.0/24"] # Within your network cidr, non-overlapping other subnets
  azs             = slice(sort(data.aws_availability_zones.available.names), 0, 3)

  enable_nat_gateway = true
  single_nat_gateway = true

  tags = {
    DeployedBy = "terraform"
    Name       = "stage"
  }
}