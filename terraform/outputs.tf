output "ec2_public_ip" {
  description = "SSH and app access: ssh ec2-user@<this-ip>"
  value       = aws_instance.app.public_ip
}

output "s3_bucket_name" {
  description = "Put this in your .env as S3_BUCKET"
  value       = aws_s3_bucket.logs.id
}

output "iam_access_key_id" {
  description = "Put this in your .env as AWS_ACCESS_KEY_ID"
  value       = aws_iam_access_key.app.id
}

output "iam_secret_access_key" {
  description = "Put this in your .env as AWS_SECRET_ACCESS_KEY"
  sensitive   = true
  value       = aws_iam_access_key.app.secret
}
