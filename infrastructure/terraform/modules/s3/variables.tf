variable "project_name" {
  description = "Project name"
  type        = string
}

variable "environment" {
  description = "Environment"
  type        = string
}

variable "bucket_suffix" {
  description = "Bucket name suffix (e.g., 'models', 'data', 'logs')"
  type        = string
}

variable "versioning_enabled" {
  description = "Enable versioning"
  type        = bool
  default     = true
}

variable "kms_key_id" {
  description = "KMS key ID for encryption"
  type        = string
  default     = null
}

variable "enable_lifecycle_rules" {
  description = "Enable lifecycle rules"
  type        = bool
  default     = true
}

variable "object_expiration_days" {
  description = "Days until objects expire"
  type        = number
  default     = 365
}

variable "allow_cloudfront_access" {
  description = "Allow CloudFront access"
  type        = bool
  default     = false
}

variable "cloudfront_distribution_arn" {
  description = "CloudFront distribution ARN"
  type        = string
  default     = null
}

variable "allowed_principals" {
  description = "List of IAM principal ARNs allowed to access bucket"
  type        = list(string)
  default     = []
}

variable "enable_cors" {
  description = "Enable CORS"
  type        = bool
  default     = false
}

variable "cors_allowed_headers" {
  description = "CORS allowed headers"
  type        = list(string)
  default     = ["*"]
}

variable "cors_allowed_methods" {
  description = "CORS allowed methods"
  type        = list(string)
  default     = ["GET", "PUT", "POST", "DELETE", "HEAD"]
}

variable "cors_allowed_origins" {
  description = "CORS allowed origins"
  type        = list(string)
  default     = ["*"]
}

variable "cors_expose_headers" {
  description = "CORS expose headers"
  type        = list(string)
  default     = ["ETag"]
}

variable "enable_logging" {
  description = "Enable access logging"
  type        = bool
  default     = false
}

variable "logging_bucket" {
  description = "Bucket for access logs"
  type        = string
  default     = null
}

variable "enable_replication" {
  description = "Enable cross-region replication"
  type        = bool
  default     = false
}

variable "replication_destination_bucket" {
  description = "Destination bucket ARN for replication"
  type        = string
  default     = null
}

variable "replication_kms_key_id" {
  description = "KMS key ID for replication encryption"
  type        = string
  default     = null
}

variable "enable_notifications" {
  description = "Enable bucket notifications"
  type        = bool
  default     = false
}

variable "notification_topic_arn" {
  description = "SNS topic ARN for notifications"
  type        = string
  default     = null
}

variable "notification_lambda_arn" {
  description = "Lambda ARN for notifications"
  type        = string
  default     = null
}

variable "enable_intelligent_tiering" {
  description = "Enable intelligent tiering"
  type        = bool
  default     = false
}

variable "tags" {
  description = "Tags"
  type        = map(string)
  default     = {}
}
