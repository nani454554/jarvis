output "bucket_id" {
  description = "Bucket ID"
  value       = aws_s3_bucket.main.id
}

output "bucket_arn" {
  description = "Bucket ARN"
  value       = aws_s3_bucket.main.arn
}

output "bucket_domain_name" {
  description = "Bucket domain name"
  value       = aws_s3_bucket.main.bucket_domain_name
}

output "bucket_regional_domain_name" {
  description = "Bucket regional domain name"
  value       = aws_s3_bucket.main.bucket_regional_domain_name
}
