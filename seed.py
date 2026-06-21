"""
Seed script — populates PostgreSQL with alert rules for all services.
Run once after deployment: python3 seed.py --host http://localhost:8000
"""

import argparse
import requests

SERVICES = ["auth-service", "payment-service", "api-gateway", "user-service", "order-service"]

RULES = [
    {"metric_type": "error_rate", "threshold": 5.0},
    {"metric_type": "latency_p95", "threshold": 500.0},
]


def get_token(host):
    res = requests.post(f"{host}/auth/login", json={"username": "admin", "password": "admin123"})
    res.raise_for_status()
    return res.json()["access_token"]


def get_existing_rules(host, headers):
    res = requests.get(f"{host}/alert_rules", headers=headers)
    res.raise_for_status()
    return res.json()


def seed_rules(host, token):
    headers = {"Authorization": f"Bearer {token}"}
    existing = get_existing_rules(host, headers).get("rules", [])
    existing_keys = {(r["service_name"], r["metric_type"]) for r in existing}

    created = 0
    for service in SERVICES:
        for rule in RULES:
            key = (service, rule["metric_type"])
            if key in existing_keys:
                print(f"  SKIP  {service} / {rule['metric_type']} (already exists)")
                continue
            payload = {
                "service_name": service,
                "metric_type": rule["metric_type"],
                "threshold": rule["threshold"],
            }
            res = requests.post(f"{host}/alert_rules", json=payload, headers=headers)
            if res.ok:
                print(f"  CREATE {service} / {rule['metric_type']} > {rule['threshold']}")
                created += 1
            else:
                print(f"  ERROR  {service} / {rule['metric_type']}: {res.text}")

    print(f"\nDone — {created} rules created, {len(existing_keys)} already existed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="http://localhost:8000")
    args = parser.parse_args()

    print(f"Seeding {args.host}")
    token = get_token(args.host)
    print("✓ Authenticated")
    seed_rules(args.host, token)
