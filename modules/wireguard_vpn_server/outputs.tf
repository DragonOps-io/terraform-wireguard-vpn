output "wireguard_public_endpoint" {
  value = "${aws_eip.wireguard.public_ip}:${var.wireguard_port}"
}

output "wireguard_instance_id" {
  value = aws_eip.wireguard.instance
}

output "wireguard_public_key" {
  value = var.wireguard_public_key
}