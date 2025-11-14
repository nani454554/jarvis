output "security_group_id" {
  description = "Instance security group ID"
  value       = aws_security_group.instance.id
}

output "autoscaling_group_name" {
  description = "Auto Scaling group name"
  value       = aws_autoscaling_group.main.name
}

output "launch_template_id" {
  description = "Launch template ID"
  value       = aws_launch_template.main.id
}

output "iam_role_arn" {
  description = "IAM role ARN"
  value       = aws_iam_role.instance.arn
}
