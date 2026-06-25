#!/bin/bash
# TRACE Backend Deployment Script for EC2
# Run from local machine: ./deploy_ec2.sh

set -e

EC2_IP="51.20.185.26"
EC2_USER="ubuntu"
KEY_PATH="~/.ssh/trace-key.pem"  # Update this path

echo "🚀 Deploying TRACE backend to EC2..."

# Copy project files to EC2
echo "📁 Copying files..."
rsync -avz --exclude='node_modules' --exclude='__pycache__' --exclude='.git' \
    -e "ssh -i $KEY_PATH" \
    ./backend/ $EC2_USER@$EC2_IP:/home/ubuntu/trace/backend/

rsync -avz --exclude='node_modules' --exclude='__pycache__' --exclude='.git' \
    -e "ssh -i $KEY_PATH" \
    ./requirements.txt ./setup.sh $EC2_USER@$EC2_IP:/home/ubuntu/trace/

# Install dependencies on EC2
echo "📦 Installing dependencies..."
ssh -i $KEY_PATH $EC2_USER@$EC2_IP << 'EOF'
    cd /home/ubuntu/trace
    
    # Install Python dependencies
    pip install -r requirements.txt
    
    # Run setup script (downloads VideoSeal model, etc.)
    chmod +x setup.sh
    ./setup.sh
    
    # Create systemd service for FastAPI
    sudo tee /etc/systemd/system/trace.service > /dev/null << 'SERVICE'
[Unit]
Description=TRACE FastAPI Backend
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/trace
EnvironmentFile=/home/ubuntu/trace/.env
ExecStart=/usr/bin/python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
SERVICE

    # Enable and start service
    sudo systemctl daemon-reload
    sudo systemctl enable trace
    sudo systemctl restart trace
    
    echo "✅ Backend deployed and running!"
    sudo systemctl status trace --no-pager
EOF

echo "🎉 Deployment complete!"
echo "Backend URL: http://$EC2_IP:8000"
echo "API docs: http://$EC2_IP:8000/docs"
