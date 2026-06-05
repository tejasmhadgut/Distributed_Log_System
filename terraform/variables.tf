variable "aws_region" {
    default = "us-east-2"
}

variable "s3_bucket_name" {
    description = "Must be globally unique - add your name/suffix"
    default = "log-analytics-archive-tejas"
}

variable "instance_type" {
    default = "t3.micro"
}

variable "key_pair_name" {
    description = "Name of an existing EC2 key pair for SSH access"
}
