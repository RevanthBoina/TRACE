#!/bin/bash
# Run once to set up EventBridge schedule for RDS start/stop
# Requires AWS CLI configured with admin permissions

REGION="eu-north-1"
DB_ID="trace-postgres-db"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# 1. Create IAM role for Lambda
aws iam create-role --role-name trace-rds-scheduler \
  --assume-role-policy-document '{
    "Version":"2012-10-17",
    "Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]
  }'

aws iam put-role-policy --role-name trace-rds-scheduler \
  --policy-name rds-startstop \
  --policy-document "{
    \"Version\":\"2012-10-17\",
    \"Statement\":[{
      \"Effect\":\"Allow\",
      \"Action\":[\"rds:StartDBInstance\",\"rds:StopDBInstance\"],
      \"Resource\":\"arn:aws:rds:${REGION}:${ACCOUNT_ID}:db:${DB_ID}\"
    },{
      \"Effect\":\"Allow\",
      \"Action\":[\"logs:CreateLogGroup\",\"logs:CreateLogStream\",\"logs:PutLogEvents\"],
      \"Resource\":\"*\"
    }]
  }"

# 2. Create Lambda zip
cat > /tmp/rds_scheduler.py << 'EOF'
import boto3, os
rds = boto3.client('rds', region_name=os.environ['AWS_REGION'])
DB_ID = 'trace-postgres-db'

def handler(event, context):
    action = event.get('action')
    if action == 'start':
        rds.start_db_instance(DBInstanceIdentifier=DB_ID)
    elif action == 'stop':
        rds.stop_db_instance(DBInstanceIdentifier=DB_ID)
EOF

cd /tmp && zip rds_scheduler.zip rds_scheduler.py

sleep 10 # wait for IAM role to propagate

# 3. Create Lambda function
aws lambda create-function \
  --function-name trace-rds-scheduler \
  --runtime python3.12 \
  --handler rds_scheduler.handler \
  --role "arn:aws:iam::${ACCOUNT_ID}:role/trace-rds-scheduler" \
  --zip-file fileb:///tmp/rds_scheduler.zip \
  --region "$REGION"

LAMBDA_ARN="arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:trace-rds-scheduler"

# 4. EventBridge rule — start at 7am UTC daily
aws events put-rule \
  --name trace-rds-start \
  --schedule-expression "cron(0 7 * * ? *)" \
  --region "$REGION"

aws events put-targets \
  --rule trace-rds-start \
  --targets "Id=1,Arn=${LAMBDA_ARN},Input={\"action\":\"start\"}" \
  --region "$REGION"

aws lambda add-permission \
  --function-name trace-rds-scheduler \
  --statement-id trace-rds-start \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --source-arn "arn:aws:events:${REGION}:${ACCOUNT_ID}:rule/trace-rds-start" \
  --region "$REGION"

# 5. EventBridge rule — stop at 11pm UTC daily
aws events put-rule \
  --name trace-rds-stop \
  --schedule-expression "cron(0 23 * * ? *)" \
  --region "$REGION"

aws events put-targets \
  --rule trace-rds-stop \
  --targets "Id=1,Arn=${LAMBDA_ARN},Input={\"action\":\"stop\"}" \
  --region "$REGION"

aws lambda add-permission \
  --function-name trace-rds-scheduler \
  --statement-id trace-rds-stop \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --source-arn "arn:aws:events:${REGION}:${ACCOUNT_ID}:rule/trace-rds-stop" \
  --region "$REGION"

echo "✅ Done — RDS will start at 7am UTC and stop at 11pm UTC daily"
echo "   Adjust cron expressions above to match your timezone/usage hours"
