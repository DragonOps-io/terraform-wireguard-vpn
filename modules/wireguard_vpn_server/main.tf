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

  owners = ["137112412989"] # Amazon
}

locals {
  config_file = "[Interface]\nAddress = ${var.wireguard_ip_address}\nListenPort = ${var.wireguard_port}\nPrivateKey = ${var.wireguard_private_key}"
}

resource "aws_instance" "vpn" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = "t3.micro"
  vpc_security_group_ids = [aws_security_group.vpn.id]
  subnet_id              = var.subnet_id
  user_data              = <<-EOT
    #!/bin/bash
    sudo yum update -y
    sudo dnf install wireguard-tools -y
    sudo dnf install iptables -y
    sudo mkdir /etc/wireguard/
    echo -e '${var.wireguard_private_key}' | sudo tee /etc/wireguard/privatekey
    echo -e '${var.wireguard_public_key}' | sudo tee /etc/wireguard/publickey
    echo 'net.ipv4.ip_forward=1' | sudo tee -a /etc/sysctl.d/10-wireguard.conf
    echo 'net.ipv6.conf.all.forwarding=1' | sudo tee -a /etc/sysctl.d/10-wireguard.conf
    sudo sysctl -p /etc/sysctl.d/10-wireguard.conf
    echo -e '${local.config_file}' | sudo tee /etc/wireguard/wg0.conf
    systemctl enable wg-quick@wg0
    sudo systemctl start wg-quick@wg0
    sudo iptables -A FORWARD -i wg0 -j ACCEPT
    sudo iptables -t nat -A POSTROUTING -o ens5 -j MASQUERADE
  EOT

  associate_public_ip_address = true
  iam_instance_profile        = aws_iam_instance_profile.wireguard_profile.name

  tags = {
    Name = "${var.environment}-wireguard-vpn"
  }
}

resource "aws_eip" "wireguard" {
  instance = aws_instance.vpn.id
}

resource "aws_iam_role" "wireguard_role" {
  name               = "${var.environment}-wireguard-vpn-role"
  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": {
    "Effect": "Allow",
    "Principal": {"Service": ["ec2.amazonaws.com", "ssm.amazonaws.com"]},
    "Action": "sts:AssumeRole"
  }
}
EOF
}

resource "aws_iam_instance_profile" "wireguard_profile" {
  name = "${var.environment}-wireguard-vpn-profile"
  role = aws_iam_role.wireguard_role.name
}

resource "aws_iam_role_policy_attachment" "this" {
  role       = aws_iam_role.wireguard_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy" "wireguard_policy" {
  name   = "${var.environment}-wireguard-kms-decrypt"
  role   = aws_iam_role.wireguard_role.name
  policy = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "kms:Decrypt"
            ],
            "Resource": "arn:aws:kms:${var.region}:${var.account_id}:key/*"
        }
    ]
}
EOF
}

resource "aws_security_group" "vpn" {
  name        = "${var.environment}-wireguard-vpn"
  description = "SG for Wireguard VPN Server - ${var.environment}"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = var.wireguard_port
    to_port     = var.wireguard_port
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["18.206.107.24/29"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.environment}-wireguard-vpn"
  }
}

resource "aws_ssm_parameter" "wireguard_config_file" {
  name  = "/${var.environment}/wireguard/config_file"
  type  = "SecureString"
  value = local.config_file
  lifecycle {
    ignore_changes = [
      value
    ]
  }
}
