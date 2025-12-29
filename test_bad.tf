provider "aws" {
  region = "us-east-1"
}

# ANOMALY 1: Unexpectedly large/expensive instance type
# (If you trained on 't2.micro', this 'p3.16xlarge' will look very strange mathematically)
resource "aws_instance" "crypto_miner_hidden" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "p3.16xlarge"
  
  tags = {
    Name        = "HiddenMiner"
    Environment = "ShadowOps" 
  }
}

# ANOMALY 2: High Risk Security Group
# (Opening Port 22 to 0.0.0.0/0 is a classic security violation)
resource "aws_security_group" "allow_everyone" {
  name        = "allow_all_traffic"
  description = "Allow all inbound traffic"

  ingress {
    description = "SSH from anywhere"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# ANOMALY 3: Missing standard tags or unusual configuration
# (If your valid data always has 'Department' or 'CostCenter' tags, this looks 'empty' to the model)
resource "aws_instance" "rogue_server" {
  ami           = "ami-0123456789abcdef0"
  instance_type = "c5.large"
  # Note: No tags provided here
}