terraform {
    required_providers {
        aws = {
            source = "hashicorp/aws"
            version = "~> 5.0"
        }
    }
}

provider "aws" {
    region = var.aws_region
}

resource "aws_s3_bucket" "logs" {
    bucket = var.s3_bucket_name

    tags = {
    Project = "log-analytics"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "logs_lifecycle" {
    bucket = aws_s3_bucket.logs.id

    rule {
        id     = "move-to-glacier"
        status = "Enabled"

        filter {}

        transition {
        days          = 90
        storage_class = "GLACIER"
        }

        expiration {
        days = 365
        }
    }

}

resource "aws_s3_bucket_versioning" "logs" {
  bucket = aws_s3_bucket.logs.id
  versioning_configuration {
    status = "Disabled"
  }
}