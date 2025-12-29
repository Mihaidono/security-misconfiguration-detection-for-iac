# providers.tf
provider "aws" {
  region = "us-east-1"
}

# ----------------------
# VPC and Networking (slight differences)
# ----------------------
resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = { Name = "main_vpc_variant" }
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id
  tags = { Name = "main_igw_variant" }
}

resource "aws_subnet" "public_a" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = "us-east-1a"
  map_public_ip_on_launch = true
  tags = { Name = "public_a_variant" }
}

resource "aws_subnet" "public_b" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = "us-east-1b"
  map_public_ip_on_launch = true
  tags = { Name = "public_b_variant" }
}

resource "aws_subnet" "private_a" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.10.0/24"
  availability_zone = "us-east-1a"
  tags = { Name = "private_a_variant" }
}

resource "aws_subnet" "private_b" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.11.0/24"
  availability_zone = "us-east-1b"
  tags = { Name = "private_b_variant" }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }
  tags = { Name = "public_rt_variant" }
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
# Security Groups (introduce subtle issues)
# ----------------------
resource "aws_security_group" "web_sg" {
  name        = "web_sg_variant"
  description = "Allow HTTP only, missing SSH"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # No SSH ingress rule → potential anomaly
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "web_sg_variant" }
}

resource "aws_security_group" "db_sg" {
  name        = "db_sg_variant"
  description = "Allow MySQL from public subnet (wrong)"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 3306
    to_port     = 3306
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # Too permissive → anomaly
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "db_sg_variant" }
}

# ----------------------
# EC2 Instances (different instance type)
# ----------------------
resource "aws_instance" "web_1" {
  ami           = "ami-0c94855ba95c71c99"
  instance_type = "t2.micro"  # Smaller instance → anomaly
  subnet_id     = aws_subnet.public_a.id
  security_groups = [aws_security_group.web_sg.name]
  tags = { Name = "web-server-1-variant" }
}

resource "aws_instance" "web_2" {
  ami           = "ami-0c94855ba95c71c99"
  instance_type = "t2.micro"  # Smaller instance
  subnet_id     = aws_subnet.public_b.id
  security_groups = [aws_security_group.web_sg.name]
  tags = { Name = "web-server-2-variant" }
}

# ----------------------
# RDS Database (less secure)
# ----------------------
resource "aws_db_instance" "app_db" {
  allocated_storage    = 20  # smaller than original
  engine               = "mysql"
  engine_version       = "8.0"
  instance_class       = "db.t2.micro"  # smaller
  name                 = "prod_appdb_variant"
  username             = "admin"
  password             = "WeakPass123!"  # weaker password
  publicly_accessible  = true             # should be false
  multi_az             = false            # removed multi-AZ → anomaly
  vpc_security_group_ids = [aws_security_group.db_sg.id]
  skip_final_snapshot  = true
  tags = { Name = "app_db_variant" }
}

# ----------------------
# S3 Buckets (overly permissive)
# ----------------------
resource "aws_s3_bucket" "logs" {
  bucket = "prod-app-logs-bucket-variant"
  acl    = "public-read"  # Should be private → anomaly
  versioning { enabled = true }
  tags = { Name = "logs_bucket_variant" }
}

resource "aws_s3_bucket" "uploads" {
  bucket = "prod-app-uploads-bucket-variant"
  acl    = "private"
  versioning { enabled = true }
  tags = { Name = "uploads_bucket_variant" }
}

# ----------------------
# Lambda (unchanged)
# ----------------------
resource "aws_iam_role" "lambda_role" {
  name = "lambda_exec_role_variant"
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
  function_name    = "app_processor_variant"
  role             = aws_iam_role.lambda_role.arn
  handler          = "index.handler"
  runtime          = "python3.11"
  source_code_hash = filebase64sha256("lambda_function.zip")
}
