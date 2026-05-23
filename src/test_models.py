from models.log import Log
from datetime import datetime

# Test 1: Valid log
try:
    log = Log(
        timestamp = datetime.now(),
        service_name="auth-service",
        log_level="ERROR",
        message="Authentication failed",
        request_id="req-123",
        user_id="user-456"
    )
    print(" Test 1 passed: Valid log created")
    print(f" Log: {log}")
except Exception as e:
    print(" Test 1 failed: {e}")

# Test 2: Invalid log_level 
try:
    log = Log(
        timestamp=datetime.now(),
        service_name="auth-service",
        log_level="INVALID", # This should fail validation!
        message="Error"
    )
    print(" Test2 failed: Should have rejected invalid log_level")
except Exception as e:
    print(" Test2 passed: Correctly rejected invalid log_level")
    print(f"  Error: {e}")

# Test 3: Missing required field
try:
    log = Log(
        timestamp=datetime.now(),
        service_name="auth-service"
    )
    print("✗ Test 3 failed: Should have rejected missing fields")
except Exception as e:
    print(f"✓ Test 3 passed: Correctly rejected missing fields")
