# Production Environment - Complete Infrastructure

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }

  backend "s3" {
    bucket         = "jarvis-terraform-state"
    key            = "production/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "jarvis-terraform-locks"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
      Owner       = "DevOps Team"
    }
  }
}

# Data Sources
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Local Variables
locals {
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }

  availability_zones = ["${var.aws_region}a", "${var.aws_region}b", "${var.aws_region}c"]
}

# VPC
module "vpc" {
  source = "../../modules/vpc"

  project_name       = var.project_name
  environment        = var.environment
  vpc_cidr           = var.vpc_cidr
  availability_zones = local.availability_zones
  enable_nat_gateway = true
  enable_flow_logs   = true

  tags = local.common_tags
}

# S3 Buckets
module "s3_models" {
  source = "../../modules/s3"

  project_name              = var.project_name
  environment               = var.environment
  bucket_suffix             = "models"
  versioning_enabled        = true
  enable_lifecycle_rules    = false
  enable_intelligent_tiering = true

  tags = local.common_tags
}

module "s3_data" {
  source = "../../modules/s3"

  project_name           = var.project_name
  environment            = var.environment
  bucket_suffix          = "data"
  versioning_enabled     = true
  enable_lifecycle_rules = true
  object_expiration_days = 365

  tags = local.common_tags
}

module "s3_logs" {
  source = "../../modules/s3"

  project_name           = var.project_name
  environment            = var.environment
  bucket_suffix          = "logs"
  versioning_enabled     = false
  enable_lifecycle_rules = true
  object_expiration_days = 90

  tags = local.common_tags
}

# RDS PostgreSQL
module "rds" {
  source = "../../modules/rds"

  project_name          = var.project_name
  environment           = var.environment
  vpc_id                = module.vpc.vpc_id
  private_subnet_ids    = module.vpc.private_subnet_ids
  app_security_group_id = module.ec2.security_group_id

  instance_class              = "db.r6g.xlarge"
  allocated_storage           = 100
  max_allocated_storage       = 500
  multi_az                    = true
  backup_retention_period     = 30
  deletion_protection         = true
  performance_insights_enabled = true

  tags = local.common_tags

  depends_on = [module.vpc]
}

# ElastiCache Redis
module "elasticache" {
  source = "../../modules/elasticache"

  project_name          = var.project_name
  environment           = var.environment
  vpc_id                = module.vpc.vpc_id
  private_subnet_ids    = module.vpc.private_subnet_ids
  app_security_group_id = module.ec2.security_group_id

  node_type                  = "cache.r6g.large"
  num_cache_nodes            = 3
  automatic_failover_enabled = true
  multi_az_enabled          = true
  snapshot_retention_limit   = 7
  auth_token_enabled        = true

  tags = local.common_tags

  depends_on = [module.vpc]
}

# Application Load Balancer
module "alb" {
  source = "../../modules/alb"

  project_name            = var.project_name
  environment             = var.environment
  vpc_id                  = module.vpc.vpc_id
  public_subnet_ids       = module.vpc.public_subnet_ids
  ssl_certificate_arn     = var.ssl_certificate_arn
  enable_deletion_protection = true
  enable_access_logs      = true
  access_logs_bucket      = module.s3_logs.bucket_id

  tags = local.common_tags

  depends_on = [module.vpc, module.s3_logs]
}

# EC2 Auto Scaling Group
module "ec2" {
  source = "../../modules/ec2"

  project_name           = var.project_name
  environment            = var.environment
  vpc_id                 = module.vpc.vpc_id
  private_subnet_ids     = module.vpc.private_subnet_ids
  alb_security_group_id  = module.alb.alb_security_group_id
  target_group_arn       = module.alb.backend_target_group_arn

  ami_id           = var.ami_id
  instance_type    = "g4dn.xlarge"  # GPU instance
  key_name         = var.key_name
  min_size         = 2
  max_size         = 10
  desired_capacity = 3

  db_host          = module.rds.address
  db_name          = module.rds.database_name
  redis_host       = module.elasticache.primary_endpoint
  s3_bucket_models = module.s3_models.bucket_id
  s3_bucket_data   = module.s3_data.bucket_id
  aws_region       = var.aws_region

  tags = local.common_tags

  depends_on = [module.vpc, module.rds, module.elasticache, module.alb]
}

# Route 53
resource "aws_route53_record" "main" {
  zone_id = var.route53_zone_id
  name    = var.domain_name
  type    = "A"

  alias {
    name                   = module.alb.alb_dns_name
    zone_id                = module.alb.alb_zone_id
    evaluate_target_health = true
  }
}

# CloudWatch Dashboard
resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${var.project_name}-${var.environment}"

  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/EC2", "CPUUtilization", { stat = "Average" }],
            ["AWS/RDS", "CPUUtilization", { stat = "Average" }],
            ["AWS/ElastiCache", "CPUUtilization", { stat = "Average" }]
          ]
          period = 300
          stat   = "Average"
          region = var.aws_region
          title  = "CPU Utilization"
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/ApplicationELB", "TargetResponseTime", { stat = "Average" }],
            [".", "RequestCount", { stat = "Sum" }]
          ]
          period = 300
          region = var.aws_region
          title  = "ALB Performance"
        }
      }
    ]
  })
}

# SNS Topic for Alarms
resource "aws_sns_topic" "alarms" {
  name = "${var.project_name}-${var.environment}-alarms"

  tags = local.common_tags
}

resource "aws_sns_topic_subscription" "alarms_email" {
  topic_arn = aws_sns_topic.alarms.arn
  protocol  = "email"
  endpoint  = var.alarm_email
}
