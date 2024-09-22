# Private instance for dev VPC
resource "aws_instance" "private_instance_dev" {
  ami                         = data.aws_ami.amazon_linux.id
  instance_type               = "t3.micro"
  subnet_id                   = module.vpc_dev.private_subnets[0]
  vpc_security_group_ids = [aws_security_group.private_sg_dev.id]
  associate_public_ip_address = false

  tags = {
    DeployedBy = "terraform"
    Name       = "private-dev"
  }
}

resource "aws_security_group" "private_sg_dev" {
  name        = "private-sg-dev"
  description = "Security group for private EC2 instance"
  vpc_id      = module.vpc_dev.vpc_id

  ingress {
    description = "Allow all traffic from within the VPC."
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [module.vpc_dev.vpc_cidr_block]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = {
    DeployedBy = "terraform"
    Name       = "private-dev"
  }
}

# Private instance for stage VPC
resource "aws_instance" "private_instance_stage" {
  ami                         = data.aws_ami.amazon_linux.id
  instance_type               = "t3.micro"
  subnet_id                   = module.vpc_stage.private_subnets[0]
  vpc_security_group_ids = [aws_security_group.private_sg_stage.id]
  associate_public_ip_address = false

  tags = {
    DeployedBy = "terraform"
    Name       = "private-stage"
  }
}

resource "aws_security_group" "private_sg_stage" {
  name        = "private-sg-stage"
  description = "Security group for private EC2 instance"
  vpc_id      = module.vpc_stage.vpc_id

  ingress {
    description = "Allow all traffic from within the VPC."
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [module.vpc_stage.vpc_cidr_block]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = {
    DeployedBy = "terraform"
    Name       = "private-stage"
  }
}



