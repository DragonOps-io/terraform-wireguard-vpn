data "aws_caller_identity" "account" {}

data "aws_availability_zones" "available" {
  state = "available" # Filter for available AZs
}

data "aws_ami" "amazon_linux" {
  most_recent = true

  filter {
    name   = "name"
    values = ["al2023-ami-2023*x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  owners = ["137112412989"]
}