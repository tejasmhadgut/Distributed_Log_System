import boto3
import json
import os
from src.db.postgres import get_warm_archives

S3_BUCKET = os.getenv("S3_BUCKET", "log-analytics-archive")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

_s3_client = None


def get_s3_client():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client(
            "s3",
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=AWS_REGION,
        )
    return _s3_client


def read_s3_jsonl(s3_key: str) -> list[dict]:
    s3 = get_s3_client()
    response = s3.get_object(Bucket=S3_BUCKET, Key=s3_key)
    body = response["Body"].read().decode("utf-8")
    results = []
    for line in body.splitlines():
        line = line.strip()
        if line:
            results.append(json.loads(line))
    return results


def search_warm_logs(
    service: str,
    level: str,
    start_date: str,
    end_date: str,
    limit: int = 100,
) -> list[dict]:
    s3_paths = get_warm_archives(start_date, end_date)

    if not s3_paths:
        return []

    results = []
    for s3_key in s3_paths:
        if len(results) >= limit:
            break
        try:
            logs = read_s3_jsonl(s3_key)
        except Exception as e:
            print(f"Warning: could not read {s3_key}: {e}")
            continue

        for log in logs:
            if service and log.get("service_name") != service:
                continue
            if level and log.get("log_level") != level:
                continue
            results.append(log)
            if len(results) >= limit:
                break

    return results
