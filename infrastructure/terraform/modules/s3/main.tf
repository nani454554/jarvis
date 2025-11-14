
# S3 Module - Secure Object Storage

terraform {
  required_version = ">= 1.5.0"
}

# S3 Bucket
resource "aws_s3_bucket" "main" {
  bucket = "${var.project_name}-${var.environment}-${var.bucket_suffix}"

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-${var.environment}-${var.bucket_suffix}"
    }
  )
}

# Block Public Access
resource "aws_s3_bucket_public_access_block" "main" {
  bucket = aws_s3_bucket.main.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Versioning
resource "aws_s3_bucket_versioning" "main" {
  bucket = aws_s3_bucket.main.id

  versioning_configuration {
    status = var.versioning_enabled ? "Enabled" : "Disabled"
  }
}

# Server-Side Encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "main" {
  bucket = aws_s3_bucket.main.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = var.kms_key_id != null ? "aws:kms" : "AES256"
      kms_master_key_id = var.kms_key_id
    }
    bucket_key_enabled = var.kms_key_id != null ? true : false
  }
}

# Lifecycle Rules
resource "aws_s3_bucket_lifecycle_configuration" "main" {
  count  = var.enable_lifecycle_rules ? 1 : 0
  bucket = aws_s3_bucket.main.id

  rule {
    id     = "transition-to-ia"
    status = "Enabled"

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER_IR"
    }

    transition {
      days          = 180
      storage_class = "DEEP_ARCHIVE"
    }

    expiration {
      days = var.object_expiration_days
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }

  rule {
    id     = "delete-incomplete-multipart"
    status = "Enabled"

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# Bucket Policy
resource "aws_s3_bucket_policy" "main" {
  bucket = aws_s3_bucket.main.id
  policy = data.aws_iam_policy_document.bucket_policy.json
}

data "aws_iam_policy_document" "bucket_policy" {
  statement {
    sid    = "EnforcedTLS"
    effect = "Deny"
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    actions = ["s3:*"]
    resources = [
      aws_s3_bucket.main.arn,
      "${aws_s3_bucket.main.arn}/*"
    ]
    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }

  dynamic "statement" {
    for_each = var.allow_cloudfront_access ? [1] : []
    content {
      sid    = "AllowCloudFrontAccess"
      effect = "Allow"
      principals {
        type        = "Service"
        identifiers = ["cloudfront.amazonaws.com"]
      }
      actions   = ["s3:GetObject"]
      resources = ["${aws_s3_bucket.main.arn}/*"]
      condition {
        test     = "StringEquals"
        variable = "AWS:SourceArn"
        values   = [var.cloudfront_distribution_arn]
      }
    }
  }

  dynamic "statement" {
    for_each = length(var.allowed_principals) > 0 ? [1] : []
    content {
      sid    = "AllowPrincipals"
      effect = "Allow"
      principals {
        type        = "AWS"
        identifiers = var.allowed_principals
      }
      actions = [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ]
      resources = [
        aws_s3_bucket.main.arn,
        "${aws_s3_bucket.main.arn}/*"
      ]
    }
  }
}

# CORS Configuration
resource "aws_s3_bucket_cors_configuration" "main" {
  count  = var.enable_cors ? 1 : 0
  bucket = aws_s3_bucket.main.id

  cors_rule {
    allowed_headers = var.cors_allowed_headers
    allowed_methods = var.cors_allowed_methods
    allowed_origins = var.cors_allowed_origins
    expose_headers  = var.cors_expose_headers
    max_age_seconds = 3600
  }
}

# Logging
resource "aws_s3_bucket_logging" "main" {
  count  = var.enable_logging ? 1 : 0
  bucket = aws_s3_bucket.main.id

  target_bucket = var.logging_bucket
  target_prefix = "${var.project_name}/${var.environment}/${var.bucket_suffix}/"
}

# Replication Configuration
resource "aws_s3_bucket_replication_configuration" "main" {
  count = var.enable_replication ? 1 : 0

  depends_on = [aws_s3_bucket_versioning.main]

  role   = aws_iam_role.replication[0].arn
  bucket = aws_s3_bucket.main.id

  rule {
    id     = "replicate-all"
    status = "Enabled"

    destination {
      bucket        = var.replication_destination_bucket
      storage_class = "STANDARD_IA"

      encryption_configuration {
        replica_kms_key_id = var.replication_kms_key_id
      }
    }
  }
}

# IAM Role for Replication
resource "aws_iam_role" "replication" {
  count = var.enable_replication ? 1 : 0
  name  = "${var.project_name}-${var.environment}-${var.bucket_suffix}-replication-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "s3.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_role_policy" "replication" {
  count = var.enable_replication ? 1 : 0
  name  = "${var.project_name}-${var.environment}-${var.bucket_suffix}-replication-policy"
  role  = aws_iam_role.replication[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "s3:GetReplicationConfiguration",
          "s3:ListBucket"
        ]
        Effect = "Allow"
        Resource = [
          aws_s3_bucket.main.arn
        ]
      },
      {
        Action = [
          "s3:GetObjectVersionForReplication",
          "s3:GetObjectVersionAcl"
        ]
        Effect = "Allow"
        Resource = [
          "${aws_s3_bucket.main.arn}/*"
        ]
      },
      {
        Action = [
          "s3:ReplicateObject",
          "s3:ReplicateDelete"
        ]
        Effect = "Allow"
        Resource = [
          "${var.replication_destination_bucket}/*"
        ]
      }
    ]
  })
}

# Bucket Notification
resource "aws_s3_bucket_notification" "main" {
  count  = var.enable_notifications ? 1 : 0
  bucket = aws_s3_bucket.main.id

  dynamic "topic" {
    for_each = var.notification_topic_arn != null ? [1] : []
    content {
      topic_arn = var.notification_topic_arn
      events    = ["s3:ObjectCreated:*", "s3:ObjectRemoved:*"]
    }
  }

  dynamic "lambda_function" {
    for_each = var.notification_lambda_arn != null ? [1] : []
    content {
      lambda_function_arn = var.notification_lambda_arn
      events              = ["s3:ObjectCreated:*"]
    }
  }
}

# Intelligent Tiering
resource "aws_s3_bucket_intelligent_tiering_configuration" "main" {
  count  = var.enable_intelligent_tiering ? 1 : 0
  bucket = aws_s3_bucket.main.id
  name   = "entire-bucket"

  tiering {
    access_tier = "DEEP_ARCHIVE_ACCESS"
    days        = 180
  }

  tiering {
    access_tier = "ARCHIVE_ACCESS"
    days        = 90
  }
}
