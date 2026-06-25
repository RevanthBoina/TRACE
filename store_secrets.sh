#!/bin/bash
set -e

echo "📦 Storing TRACE secrets in AWS Parameter Store..."

if [ ! -f .env ]; then
  echo "❌ .env file not found. Run from project root."
  exit 1
fi

source .env

aws ssm put-parameter --name "/trace/AWS_ACCESS_KEY_ID"     --value "$AWS_ACCESS_KEY_ID"     --type "SecureString" --overwrite
aws ssm put-parameter --name "/trace/AWS_SECRET_ACCESS_KEY" --value "$AWS_SECRET_ACCESS_KEY" --type "SecureString" --overwrite
aws ssm put-parameter --name "/trace/AWS_REGION"            --value "$AWS_REGION"            --type "String"       --overwrite
aws ssm put-parameter --name "/trace/S3_UPLOAD_BUCKET"      --value "$S3_UPLOAD_BUCKET"      --type "String"       --overwrite
aws ssm put-parameter --name "/trace/S3_OUTPUT_BUCKET"      --value "$S3_OUTPUT_BUCKET"      --type "String"       --overwrite
aws ssm put-parameter --name "/trace/DATABASE_URL"          --value "$DATABASE_URL"          --type "SecureString" --overwrite
aws ssm put-parameter --name "/trace/RESEND_API_KEY"        --value "$RESEND_API_KEY"        --type "SecureString" --overwrite

echo "✅ All secrets stored in AWS Parameter Store"
