#!/bin/bash

#######################################
# JARVIS - Master Deployment Script
# Deploys entire infrastructure and application
#######################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="jarvis"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# Default values
ENVIRONMENT="${1:-production}"
AWS_REGION="${AWS_REGION:-us-east-1}"
SKIP_TERRAFORM="${SKIP_TERRAFORM:-false}"
SKIP_DOCKER="${SKIP_DOCKER:-false}"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_dependencies() {
    log_info "Checking dependencies..."
    
    local deps=("terraform" "aws" "docker" "docker-compose" "jq" "git")
    local missing_deps=()
    
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            missing_deps+=("$dep")
        fi
    done
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        log_error "Missing dependencies: ${missing_deps[*]}"
        log_info "Install them using:"
        log_info "  - Terraform: https://www.terraform.io/downloads.html"
        log_info "  - AWS CLI: https://aws.amazon.com/cli/"
        log_info "  - Docker: https://docs.docker.com/get-docker/"
        log_info "  - jq: sudo apt-get install jq (or brew install jq)"
        exit 1
    fi
    
    log_success "All dependencies found"
}

check_aws_credentials() {
    log_info "Checking AWS credentials..."
    
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured"
        log_info "Run: aws configure"
        exit 1
    fi
    
    local account_id=$(aws sts get-caller-identity --query Account --output text)
    log_success "AWS credentials valid (Account: $account_id)"
}

create_terraform_backend() {
    log_info "Setting up Terraform backend..."
    
    local bucket_name="${PROJECT_NAME}-terraform-state"
    local table_name="${PROJECT_NAME}-terraform-locks"
    
    # Create S3 bucket for state
    if ! aws s3 ls "s3://$bucket_name" 2>/dev/null; then
        log_info "Creating S3 bucket: $bucket_name"
        aws s3 mb "s3://$bucket_name" --region "$AWS_REGION"
        aws s3api put-bucket-versioning \
            --bucket "$bucket_name" \
            --versioning-configuration Status=Enabled
        aws s3api put-bucket-encryption \
            --bucket "$bucket_name" \
            --server-side-encryption-configuration \
            '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
        log_success "S3 bucket created"
    else
        log_info "S3 bucket already exists"
    fi
    
    # Create DynamoDB table for locks
    if ! aws dynamodb describe-table --table-name "$table_name" --region "$AWS_REGION" &>/dev/null; then
        log_info "Creating DynamoDB table: $table_name"
        aws dynamodb create-table \
            --table-name "$table_name" \
            --attribute-definitions AttributeName=LockID,AttributeType=S \
            --key-schema AttributeName=LockID,KeyType=HASH \
            --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 \
            --region "$AWS_REGION"
        
        # Wait for table to be active
        aws dynamodb wait table-exists --table-name "$table_name" --region "$AWS_REGION"
        log_success "DynamoDB table created"
    else
        log_info "DynamoDB table already exists"
    fi
}

setup_secrets() {
    log_info "Setting up AWS Secrets Manager..."
    
    local secrets=(
        "openai-api-key"
        "anthropic-api-key"
        "db-password"
        "redis-auth-token"
    )
    
    for secret in "${secrets[@]}"; do
        local secret_name="${PROJECT_NAME}/${ENVIRONMENT}/$secret"
        
        if ! aws secretsmanager describe-secret --secret-id "$secret_name" --region "$AWS_REGION" &>/dev/null; then
            log_warning "Secret not found: $secret_name"
            log_info "Please enter value for $secret (or press Enter to skip):"
            read -s secret_value
            
            if [ -n "$secret_value" ]; then
                aws secretsmanager create-secret \
                    --name "$secret_name" \
                    --secret-string "$secret_value" \
                    --region "$AWS_REGION"
                log_success "Secret created: $secret_name"
            else
                log_warning "Skipped: $secret_name"
            fi
        else
            log_info "Secret already exists: $secret_name"
        fi
    done
}

deploy_infrastructure() {
    if [ "$SKIP_TERRAFORM" = "true" ]; then
        log_warning "Skipping Terraform deployment"
        return
    fi
    
    log_info "Deploying infrastructure with Terraform..."
    
    cd "$ROOT_DIR/infrastructure/terraform/environments/$ENVIRONMENT"
    
    # Initialize Terraform
    log_info "Running terraform init..."
    terraform init -upgrade
    
    # Validate configuration
    log_info "Running terraform validate..."
    terraform validate
    
    # Plan changes
    log_info "Running terraform plan..."
    terraform plan -out=tfplan
    
    # Ask for confirmation
    log_warning "Review the plan above. Continue with apply? (yes/no)"
    read -r confirmation
    
    if [ "$confirmation" != "yes" ]; then
        log_error "Deployment cancelled"
        exit 1
    fi
    
    # Apply changes
    log_info "Running terraform apply..."
    terraform apply tfplan
    
    # Save outputs
    terraform output -json > "$ROOT_DIR/terraform-outputs.json"
    
    log_success "Infrastructure deployed successfully"
    
    cd "$ROOT_DIR"
}

upload_ai_models() {
    log_info "Uploading AI models to S3..."
    
    local models_bucket=$(jq -r '.s3_models_bucket.value' "$ROOT_DIR/terraform-outputs.json")
    
    if [ -z "$models_bucket" ] || [ "$models_bucket" = "null" ]; then
        log_error "Could not find S3 models bucket from Terraform outputs"
        return 1
    fi
    
    if [ -d "$ROOT_DIR/models" ]; then
        log_info "Syncing models directory to s3://$models_bucket/models/"
        aws s3 sync "$ROOT_DIR/models" "s3://$models_bucket/models/" \
            --exclude "*.gitkeep" \
            --exclude ".DS_Store"
        log_success "Models uploaded"
    else
        log_warning "Models directory not found. Create $ROOT_DIR/models and add model files"
    fi
}

build_docker_images() {
    if [ "$SKIP_DOCKER" = "true" ]; then
        log_warning "Skipping Docker build"
        return
    fi
    
    log_info "Building Docker images..."
    
    cd "$ROOT_DIR"
    
    # Get ECR repository URLs from Terraform outputs (if using ECR)
    local account_id=$(aws sts get-caller-identity --query Account --output text)
    local ecr_registry="${account_id}.dkr.ecr.${AWS_REGION}.amazonaws.com"
    
    # Login to ECR
    log_info "Logging in to ECR..."
    aws ecr get-login-password --region "$AWS_REGION" | \
        docker login --username AWS --password-stdin "$ecr_registry"
    
    # Build backend image
    log_info "Building backend image..."
    docker build \
        -f docker/Dockerfile.backend \
        -t "${PROJECT_NAME}-backend:latest" \
        -t "${ecr_registry}/${PROJECT_NAME}-backend:latest" \
        -t "${ecr_registry}/${PROJECT_NAME}-backend:${ENVIRONMENT}" \
        backend/
    
    # Build frontend image
    log_info "Building frontend image..."
    docker build \
        -f docker/Dockerfile.frontend \
        -t "${PROJECT_NAME}-frontend:latest" \
        -t "${ecr_registry}/${PROJECT_NAME}-frontend:latest" \
        -t "${ecr_registry}/${PROJECT_NAME}-frontend:${ENVIRONMENT}" \
        frontend/
    
    # Push to ECR
    log_info "Pushing images to ECR..."
    docker push "${ecr_registry}/${PROJECT_NAME}-backend:latest"
    docker push "${ecr_registry}/${PROJECT_NAME}-backend:${ENVIRONMENT}"
    docker push "${ecr_registry}/${PROJECT_NAME}-frontend:latest"
    docker push "${ecr_registry}/${PROJECT_NAME}-frontend:${ENVIRONMENT}"
    
    log_success "Docker images built and pushed"
}

deploy_application() {
    log_info "Deploying application to EC2 instances..."
    
    # Get Auto Scaling Group name from Terraform outputs
    local asg_name=$(jq -r '.ec2_asg_name.value' "$ROOT_DIR/terraform-outputs.json" 2>/dev/null)
    
    if [ -z "$asg_name" ] || [ "$asg_name" = "null" ]; then
        log_warning "Could not find ASG name. Skipping instance update"
        return
    fi
    
    # Trigger instance refresh
    log_info "Starting instance refresh for ASG: $asg_name"
    aws autoscaling start-instance-refresh \
        --auto-scaling-group-name "$asg_name" \
        --preferences MinHealthyPercentage=50,InstanceWarmup=300 \
        --region "$AWS_REGION"
    
    log_success "Instance refresh started. This will take several minutes."
    log_info "Monitor progress with: aws autoscaling describe-instance-refreshes --auto-scaling-group-name $asg_name"
}

run_database_migrations() {
    log_info "Running database migrations..."
    
    local db_host=$(jq -r '.rds_endpoint.value' "$ROOT_DIR/terraform-outputs.json" | cut -d: -f1)
    
    if [ -z "$db_host" ] || [ "$db_host" = "null" ]; then
        log_error "Could not find RDS endpoint"
        return 1
    fi
    
    # Run migrations using Docker
    cd "$ROOT_DIR/backend"
    
    docker run --rm \
        -v "$(pwd):/app" \
        -e DATABASE_URL="postgresql://jarvis:PASSWORD@${db_host}:5432/jarvis_db" \
        "${PROJECT_NAME}-backend:latest" \
        alembic upgrade head
    
    log_success "Database migrations completed"
}

verify_deployment() {
    log_info "Verifying deployment..."
    
    local app_url=$(jq -r '.application_url.value' "$ROOT_DIR/terraform-outputs.json" 2>/dev/null)
    
    if [ -z "$app_url" ] || [ "$app_url" = "null" ]; then
        log_warning "Could not find application URL from Terraform outputs"
        return
    fi
    
    log_info "Testing application health..."
    
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -sf "${app_url}/health" > /dev/null; then
            log_success "Application is healthy!"
            log_success "Access your application at: $app_url"
            return 0
        fi
        
        log_info "Attempt $attempt/$max_attempts - Waiting for application..."
        sleep 10
        ((attempt++))
    done
    
    log_error "Application did not become healthy within expected time"
    return 1
}

show_summary() {
    log_info "Deployment Summary"
    echo "=================================================="
    
    if [ -f "$ROOT_DIR/terraform-outputs.json" ]; then
        echo "Application URL: $(jq -r '.application_url.value' "$ROOT_DIR/terraform-outputs.json")"
        echo "ALB DNS: $(jq -r '.alb_dns_name.value' "$ROOT_DIR/terraform-outputs.json")"
        echo "RDS Endpoint: $(jq -r '.rds_endpoint.value' "$ROOT_DIR/terraform-outputs.json")"
        echo "Redis Endpoint: $(jq -r '.redis_endpoint.value' "$ROOT_DIR/terraform-outputs.json")"
        echo "S3 Models Bucket: $(jq -r '.s3_models_bucket.value' "$ROOT_DIR/terraform-outputs.json")"
        echo "S3 Data Bucket: $(jq -r '.s3_data_bucket.value' "$ROOT_DIR/terraform-outputs.json")"
    fi
    
    echo "=================================================="
    
    log_info "Next steps:"
    echo "1. Access the application at the URL above"
    echo "2. Monitor CloudWatch logs: aws logs tail /aws/ec2/${PROJECT_NAME}-${ENVIRONMENT} --follow"
    echo "3. Check CloudWatch dashboard: AWS Console > CloudWatch > Dashboards"
    echo "4. Set up monitoring alerts if needed"
}

# Main execution
main() {
    echo "=================================================="
    echo "  JARVIS Deployment Script"
    echo "  Environment: $ENVIRONMENT"
    echo "  Region: $AWS_REGION"
    echo "=================================================="
    echo ""
    
    check_dependencies
    check_aws_credentials
    create_terraform_backend
    setup_secrets
    deploy_infrastructure
    upload_ai_models
    build_docker_images
    deploy_application
    run_database_migrations
    verify_deployment
    show_summary
    
    log_success "Deployment completed successfully! 🚀"
}

# Run main function
main "$@"
