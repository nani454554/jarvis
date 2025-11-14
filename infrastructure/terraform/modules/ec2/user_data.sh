#!/bin/bash
set -e

# User Data Script for JARVIS EC2 Instance
echo "Starting JARVIS instance setup..."

# Update system
sudo yum update -y
sudo yum install -y docker git python3.11 python3.11-pip

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Start Docker
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker ec2-user

# Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
rm -rf aws awscliv2.zip

# Install CloudWatch Agent
wget https://s3.amazonaws.com/amazoncloudwatch-agent/amazon_linux/amd64/latest/amazon-cloudwatch-agent.rpm
sudo rpm -U ./amazon-cloudwatch-agent.rpm
rm amazon-cloudwatch-agent.rpm

# Configure CloudWatch Agent
cat > /opt/aws/amazon-cloudwatch-agent/etc/config.json <<EOF
{
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/jarvis/*.log",
            "log_group_name": "/aws/ec2/${project_name}-${environment}",
            "log_stream_name": "{instance_id}/application"
          }
        ]
      }
    }
  },
  "metrics": {
    "namespace": "${project_name}/${environment}",
    "metrics_collected": {
      "cpu": {
        "measurement": [
          {"name": "cpu_usage_idle", "rename": "CPU_IDLE", "unit": "Percent"},
          "cpu_usage_iowait"
        ],
        "metrics_collection_interval": 60,
        "totalcpu": false
      },
      "disk": {
        "measurement": [
          {"name": "used_percent", "rename": "DISK_USED", "unit": "Percent"}
        ],
        "metrics_collection_interval": 60,
        "resources": ["*"]
      },
      "mem": {
        "measurement": [
          {"name": "mem_used_percent", "rename": "MEM_USED", "unit": "Percent"}
        ],
        "metrics_collection_interval": 60
      }
    }
  }
}
EOF

sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
    -a fetch-config \
    -m ec2 \
    -s \
    -c file:/opt/aws/amazon-cloudwatch-agent/etc/config.json

# Create application directory
sudo mkdir -p /opt/jarvis
sudo chown -R ec2-user:ec2-user /opt/jarvis
cd /opt/jarvis

# Create log directory
sudo mkdir -p /var/log/jarvis
sudo chown -R ec2-user:ec2-user /var/log/jarvis

# Get secrets from AWS Secrets Manager
export DB_PASSWORD=$(aws secretsmanager get-secret-value \
    --secret-id ${project_name}/${environment}/db-password \
    --region ${aws_region} \
    --query SecretString \
    --output text)

export OPENAI_API_KEY=$(aws secretsmanager get-secret-value \
    --secret-id ${project_name}/${environment}/openai-api-key \
    --region ${aws_region} \
    --query SecretString \
    --output text)

# Create environment file
cat > /opt/jarvis/.env <<EOF
# Database
DATABASE_URL=postgresql://jarvis:$DB_PASSWORD@${db_host}:5432/${db_name}

# Redis
REDIS_URL=redis://${redis_host}:6379/0
CELERY_BROKER_URL=redis://${redis_host}:6379/1

# AWS
AWS_REGION=${aws_region}
S3_BUCKET_MODELS=${s3_bucket_models}
S3_BUCKET_DATA=${s3_bucket_data}

# AI Services
OPENAI_API_KEY=$OPENAI_API_KEY

# Application
ENVIRONMENT=${environment}
DEBUG=False
LOG_LEVEL=INFO
EOF

# Download AI models from S3
echo "Downloading AI models from S3..."
aws s3 sync s3://${s3_bucket_models}/models /opt/jarvis/models

# Clone repository (replace with your repo)
# git clone https://github.com/your-org/jarvis.git .

# Build and run with Docker Compose
# docker-compose -f docker-compose.prod.yml up -d

echo "JARVIS instance setup complete!"
