#!/bin/bash

#######################################
# JARVIS - Destroy Infrastructure Script
# Safely tears down all AWS resources
#######################################

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ENVIRONMENT="${1:-production}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

destroy_infrastructure() {
    cd "$ROOT_DIR/infrastructure/terraform/environments/$ENVIRONMENT"
    
    echo "=================================================="
    echo "  ⚠️  DESTRUCTIVE OPERATION ⚠️"
    echo "  This will DELETE all resources in: $ENVIRONMENT"
    echo "=================================================="
    echo ""
    
    # Show what will be destroyed
    terraform plan -destroy
    
    echo ""
    log_warning "Are you ABSOLUTELY SURE you want to destroy everything?"
    log_warning "Type 'destroy-$ENVIRONMENT' to confirm:"
    read -r confirmation
    
    if [ "$confirmation" != "destroy-$ENVIRONMENT" ]; then
        log_error "Confirmation failed. Aborting."
        exit 1
    fi
    
    # Disable deletion protection on RDS
    log_warning "Disabling RDS deletion protection..."
    terraform apply -auto-approve -target=module.rds -var="deletion_protection=false"
    
    # Destroy everything
    log_warning "Starting destruction..."
    terraform destroy -auto-approve
    
    log_success "Infrastructure destroyed"
}

cleanup_s3_buckets() {
    log_warning "Emptying S3 buckets..."
    
    local buckets=(
        "jarvis-${ENVIRONMENT}-models"
        "jarvis-${ENVIRONMENT}-data"
        "jarvis-${ENVIRONMENT}-logs"
    )
    
    for bucket in "${buckets[@]}"; do
        if aws s3 ls "s3://$bucket" &>/dev/null; then
            echo "Emptying bucket: $bucket"
            aws s3 rm "s3://$bucket" --recursive
            aws s3 rb "s3://$bucket" --force
        fi
    done
}

delete_secrets() {
    log_warning "Deleting secrets from Secrets Manager..."
    
    local secrets=$(aws secretsmanager list-secrets \
        --query "SecretList[?starts_with(Name, 'jarvis/${ENVIRONMENT}/')].Name" \
        --output text)
    
    for secret in $secrets; do
        echo "Deleting secret: $secret"
        aws secretsmanager delete-secret --secret-id "$secret" --force-delete-without-recovery
    done
}

main() {
    destroy_infrastructure
    cleanup_s3_buckets
    delete_secrets
    
    log_success "Complete teardown finished! 💥"
}

main "$@"
