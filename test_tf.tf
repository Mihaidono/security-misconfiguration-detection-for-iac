# providers.tf
provider "aws" {
  region = "us-east-1"
}

# ----------------------
# VPC and Networking
# ----------------------
resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name = "main_vpc"
  }
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id
  tags = { Name = "main_igw" }
}

resource "aws_subnet" "public_a" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = "us-east-1a"
  map_public_ip_on_launch = true
  tags = { Name = "public_a" }
}

resource "aws_subnet" "public_b" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = "us-east-1b"
  map_public_ip_on_launch = true
  tags = { Name = "public_b" }
}

resource "aws_subnet" "private_a" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.10.0/24"
  availability_zone = "us-east-1a"
  tags = { Name = "private_a" }
}

resource "aws_subnet" "private_b" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.11.0/24"
  availability_zone = "us-east-1b"
  tags = { Name = "private_b" }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }
  tags = { Name = "public_rt" }
}

resource "aws_route_table_association" "public_a" {
  subnet_id      = aws_subnet.public_a.id
  route_table_id = aws_route_table.public.id
}
resource "aws_route_table_association" "public_b" {
  subnet_id      = aws_subnet.public_b.id
  route_table_id = aws_route_table.public.id
}

# ----------------------
# Security Groups
# ----------------------
resource "aws_security_group" "web_sg" {
  name        = "web_sg"
  description = "Allow HTTP and SSH"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["203.0.113.10/32"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "web_sg" }
}

resource "aws_security_group" "db_sg" {
  name        = "db_sg"
  description = "Allow MySQL from web_sg"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 3306
    to_port     = 3306
    protocol    = "tcp"
    security_groups = [aws_security_group.web_sg.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "db_sg" }
}

# ----------------------
# EC2 Instances
# ----------------------
resource "aws_instance" "web_1" {
  ami           = "ami-0c94855ba95c71c99"
  instance_type = "t3.medium"
  subnet_id     = aws_subnet.public_a.id
  security_groups = [aws_security_group.web_sg.name]
  tags = { Name = "web-server-1" }
}

resource "aws_instance" "web_2" {
  ami           = "ami-0c94855ba95c71c99"
  instance_type = "t3.medium"
  subnet_id     = aws_subnet.public_b.id
  security_groups = [aws_security_group.web_sg.name]
  tags = { Name = "web-server-2" }
}

# ----------------------
# RDS Database
# ----------------------
resource "aws_db_instance" "app_db" {
  allocated_storage    = 50
  engine               = "mysql"
  engine_version       = "8.0"
  instance_class       = "db.t3.medium"
  name                 = "prod_appdb"
  username             = "admin"
  password             = "ComplexPass123!"
  publicly_accessible  = false
  multi_az             = true
  vpc_security_group_ids = [aws_security_group.db_sg.id]
  skip_final_snapshot  = true
  tags = { Name = "app_db" }
}

# ----------------------
# S3 Buckets
# ----------------------
resource "aws_s3_bucket" "logs" {
  bucket = "prod-app-logs-bucket"
  acl    = "private"
  versioning { enabled = true }
  tags = { Name = "logs_bucket" }
}

resource "aws_s3_bucket" "uploads" {
  bucket = "prod-app-uploads-bucket"
  acl    = "private"
  versioning { enabled = true }
  tags = { Name = "uploads_bucket" }
}

# ----------------------
# IAM Role & Lambda
# ----------------------
resource "aws_iam_role" "lambda_role" {
  name = "lambda_exec_role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action = "sts:AssumeRole",
      Effect = "Allow",
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_attach" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_lambda_function" "processor" {
  filename         = "lambda_function.zip"
  function_name    = "app_processor"
  role             = aws_iam_role.lambda_role.arn
  handler          = "index.handler"
  runtime          = "python3.11"
  source_code_hash = filebase64sha256("lambda_function.zip")
}

# ----------------------
# Outputs
# ----------------------
output "web_instance_ips" {
  value = [aws_instance.web_1.public_ip, aws_instance.web_2.public_ip]
}

output "db_endpoint" {
  value = aws_db_instance.app_db.endpoint
}

output "logs_bucket" {
  value = aws_s3_bucket.logs.bucket
}

output "uploads_bucket" {
  value = aws_s3_bucket.uploads.bucket
}
