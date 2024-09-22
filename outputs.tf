output "private_instance_dev" {
  value = aws_instance.private_instance_dev.private_ip
}

output "private_instance_stage" {
  value = aws_instance.private_instance_stage.private_ip
}