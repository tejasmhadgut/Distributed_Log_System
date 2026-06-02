import time
import json
import boto3
import os
from datetime import datetime
from src.db.clickhouse import get_logs_for_archival, delete_archived_logs
from src.db.postgres import track_archive, update_archive_status, get_failed_archives, increment_archive_retry

AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET = os.getenv("S3_BUCKET", "log-analytics-archive")
ARCHIVE_INTERVAL = int(os.getenv("ARCHIVE_INTERVAL_SECONDS", 300))

s3_client = None

def init_s3():
    global s3_client
    if AWS_ACCESS_KEY and AWS_SECRET_KEY:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY,
            region_name=AWS_REGION
        )
        try:
            s3_client.head_bucket(Bucket=S3_BUCKET)
            print(f"✓ S3 bucket '{S3_BUCKET}' accessible")
        except Exception as e:
            print(f"⚠ S3 bucket not accessible: {e}")
    else:
        print("⚠ AWS credentials not provided, S3 archival will be skipped")

def get_s3_client():
    global s3_client
    if s3_client is None:
        init_s3()
    return s3_client

def determine_tier(days_old: int) -> str:
    if days_old < 90:
        return "warm"
    elif days_old < 365:
        return "cold"
    else:
        return "archive"

def archive_logs_batch(logs: list) -> tuple[bool, str]:
    if not logs or not get_s3_client():
        return False, "No logs or S3 not configured"

    try:
        first_log_ts = logs[0][1]
        days_old = (datetime.now(first_log_ts.tzinfo) - first_log_ts).days
        tier = determine_tier(days_old)

        date_parts = first_log_ts.strftime("%Y/%m/%d")
        timestamp_str = first_log_ts.strftime("%Y%m%d_%H%M%S")
        s3_key = f"{tier}/{date_parts}/{timestamp_str}_{len(logs)}_logs.jsonl"

        jsonl_content = ""
        for log in logs:
            log_dict = {
                "id": log[0],
                "timestamp": log[1].isoformat() if log[1] else None,
                "service_name": log[2],
                "log_level": log[3],
                "message": log[4],
                "request_id": log[5],
                "user_id": log[6],
                "latency_ms": log[7],
                "metadata": log[8],
                "span_id": log[9],
                "parent_span_id": log[10]
            }
            jsonl_content += json.dumps(log_dict) + "\n"

        s3 = get_s3_client()
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=jsonl_content.encode('utf-8'),
            ContentType='application/x-ndjson',
            Metadata={
                'archive-tier': tier,
                'log-count': str(len(logs)),
                'archived-at': datetime.now().isoformat()
            }
        )

        print(f"✓ Archived {len(logs)} logs to s3://{S3_BUCKET}/{s3_key}")
        return True, s3_key

    except Exception as e:
        print(f"✗ Error archiving logs: {e}")
        return False, str(e)

def process_archive_cycle():
    try:
        logs = get_logs_for_archival(older_than_days=7, limit=10000)

        if not logs:
            print("ℹ No logs to archive")
            return

        print(f"Found {len(logs)} logs to archive")

        success, s3_path = archive_logs_batch(logs)

        if success:
            archive_id = track_archive(len(logs), s3_path, "warm", "PENDING")
            log_ids = [log[0] for log in logs]
            deleted_count = delete_archived_logs(log_ids)
            update_archive_status(archive_id, "SUCCESS")
            print(f"✓ Archive cycle complete: {deleted_count} logs deleted")
        else:
            archive_id = track_archive(len(logs), "unknown", "warm", "FAILED", s3_path)
            print(f"✗ Archive failed, logged in archive_id={archive_id}")

    except Exception as e:
        print(f"✗ Archive cycle failed: {e}")

def retry_failed_archives():
    try:
        failed = get_failed_archives()
        if not failed:
            return

        print(f"ℹ Retrying {len(failed)} failed archives")

        for archive in failed:
            archive_id, log_count, s3_path, tier, retry_count = archive
            try:
                increment_archive_retry(archive_id)
                update_archive_status(archive_id, "RETRY", f"Attempt {retry_count + 1}")
                print(f"✓ Queued retry for archive_id={archive_id}")
            except Exception as e:
                update_archive_status(archive_id, "FAILED", f"Retry failed: {str(e)}")
                print(f"✗ Retry failed for archive_id={archive_id}")

    except Exception as e:
        print(f"✗ Retry cycle failed: {e}")

def start_archiver():
    init_s3()
    print(f"✓ Archiver started, running every {ARCHIVE_INTERVAL}s")

    try:
        while True:
            process_archive_cycle()
            retry_failed_archives()
            time.sleep(ARCHIVE_INTERVAL)
    except KeyboardInterrupt:
        print("\n✓ Archiver shutting down")

if __name__ == '__main__':
    start_archiver()
