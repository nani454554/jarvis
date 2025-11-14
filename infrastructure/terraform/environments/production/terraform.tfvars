# Production Environment Variables

project_name = "jarvis"
environment  = "production"
aws_region   = "us-east-1"

# Network
vpc_cidr = "10.0.0.0/16"

# Domain
domain_name       = "jarvis.yourdomain.com"
route53_zone_id   = "Z1234567890ABC"
ssl_certificate_arn = "arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012"

# EC2
ami_id   = "ami-0c55b159cbfafe1f0"  # Amazon Linux 2 with GPU drivers
key_name = "jarvis-production-key"

# Alarms
alarm_email = "devops@yourdomain.com"
