"""Test integral: login 2FA -> verificar OTP -> /me.
También: crear colaborador -> activar -> login 2FA -> acceso.
"""
import json
import sys
from urllib.error import HTTPError
from urllib.request import urlopen, Request
from urllib.parse import urlencode

BASE = "http://localhost:8000/api/v1"


def post(url, data=None, json_body=None, headers=None, expect_error=False):
    h = headers or {}
    if json_body is not None:
        body = json.dumps(json_body).encode()
        h["Content-Type"] = "application/json"
    elif data is not None:
        body = urlencode(data).encode()
        h["Content-Type"] = "application/x-www-form-urlencoded"
    else:
        body = None
    try:
        r = urlopen(Request(f"{BASE}{url}", data=body, headers=h))
        return json.loads(r.read()), r.status
    except HTTPError as e:
        result = json.loads(e.read())
        if expect_error:
            return result, e.code
        print(f"  [FAIL] {url} => {e.code}: {result}")
        sys.exit(1)


def get(url, headers=None, expect_error=False):
    try:
        r = urlopen(Request(f"{BASE}{url}", headers=headers or {}))
        return json.loads(r.read()), r.status
    except HTTPError as e:
        result = json.loads(e.read())
        if expect_error:
            return result, e.code
        print(f"  [FAIL] {url} => {e.code}: {result}")
        sys.exit(1)


def test_login_2fa():
    print("=== Test 1: Login 2FA flow (admin) ===")

    # Step 1: login -> should get 2FA challenge
    resp, code = post("/auth/login", data={"username": "admin@demo.org", "password": "Admin123!"})
    assert resp.get("requires_2fa") is True, f"Expected requires_2fa, got {resp}"
    assert "session_token" in resp, "Missing session_token"
    assert "demo_otp" in resp and resp["demo_otp"], f"Expected demo_otp in demo mode, got {resp}"
    session_token = resp["session_token"]
    demo_otp = resp["demo_otp"]
    print(f"  [OK] 2FA challenge received. demo_otp={demo_otp}")

    # Step 2: try to use session_token to access /me -> should fail with 403
    resp, code = get("/auth/me", headers={"Authorization": f"Bearer {session_token}"}, expect_error=True)
    assert code == 403, f"Expected 403 for pre_2fa token, got {code}"
    print("  [OK] pre_2fa token blocked from /me (403)")

    # Step 3: verify with wrong OTP -> should fail
    resp, code = post("/auth/verify-2fa", json_body={"session_token": session_token, "otp_code": "000000"}, expect_error=True)
    assert code == 401, f"Expected 401 for wrong OTP, got {code}"
    print("  [OK] Wrong OTP rejected (401)")

    # Step 4: verify with correct OTP -> should get JWT
    resp, code = post("/auth/verify-2fa", json_body={"session_token": session_token, "otp_code": demo_otp})
    assert "access_token" in resp, f"Expected access_token, got {resp}"
    final_token = resp["access_token"]
    print("  [OK] Correct OTP -> JWT issued")

    # Step 5: use final token to access /me
    resp, code = get("/auth/me", headers={"Authorization": f"Bearer {final_token}"})
    assert resp["email"] == "admin@demo.org", f"Expected admin email, got {resp['email']}"
    assert resp["role_name"] == "SYSTEM_ADMIN", f"Expected SYSTEM_ADMIN role"
    print(f"  [OK] /me works with final token: {resp['full_name']} ({resp['role_name']})")

    return final_token


def test_endpoints_with_token(token):
    print("\n=== Test 2: All endpoints with authenticated token ===")
    headers = {"Authorization": f"Bearer {token}"}

    resp, _ = get("/identity/users", headers=headers)
    print(f"  [OK] Users: {len(resp)} users")

    resp, _ = get("/records/", headers=headers)
    print(f"  [OK] Records: {len(resp)} records")

    resp, _ = get("/audit/", headers=headers)
    print(f"  [OK] Audit: {len(resp)} entries")

    resp, _ = get("/templates/", headers=headers)
    print(f"  [OK] Templates: {len(resp)} templates")

    resp, _ = get("/certificates/", headers=headers)
    print(f"  [OK] Certificates: {len(resp)} certificates")


def test_activation_flow(admin_token):
    print("\n=== Test 3: Create collaborator -> Activate -> Login 2FA ===")
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Create collaborator
    resp, code = post("/identity/collaborators", json_body={
        "full_name": "Test User 2FA",
        "email": "test2fa@demo.org",
        "area_id": 1,
        "access_level_code": 3,
    }, headers=headers)
    assert code == 200, f"Expected 200, got {code}"
    activation_link = resp.get("activation_link")
    assert activation_link, "Expected activation_link in demo mode"
    raw_token = activation_link.split("token=")[1]
    print(f"  [OK] Collaborator created. Activation token: {raw_token[:16]}...")

    # Activate
    resp, code = post("/identity/activate", json_body={"token": raw_token, "password": "TestPass123!"})
    assert code == 200, f"Activation failed: {resp}"
    print("  [OK] Account activated")

    # Login -> 2FA
    resp, code = post("/auth/login", data={"username": "test2fa@demo.org", "password": "TestPass123!"})
    assert resp.get("requires_2fa") is True
    demo_otp = resp["demo_otp"]
    session_token = resp["session_token"]
    print(f"  [OK] 2FA challenge for new user. demo_otp={demo_otp}")

    # Verify OTP
    resp, code = post("/auth/verify-2fa", json_body={"session_token": session_token, "otp_code": demo_otp})
    assert "access_token" in resp
    final_token = resp["access_token"]
    print("  [OK] OTP verified -> JWT issued")

    # Access /me
    resp, code = get("/auth/me", headers={"Authorization": f"Bearer {final_token}"})
    assert resp["email"] == "test2fa@demo.org"
    assert resp["role_name"] == "AREA_OPERATOR"
    print(f"  [OK] New user /me: {resp['full_name']} ({resp['role_name']})")


def test_level4_blocked():
    print("\n=== Test 4: Level 4 blocked from records ===")
    resp, _ = post("/auth/login", data={"username": "externo@demo.org", "password": "Ext123!"})
    demo_otp = resp["demo_otp"]
    session_token = resp["session_token"]
    resp, _ = post("/auth/verify-2fa", json_body={"session_token": session_token, "otp_code": demo_otp})
    token4 = resp["access_token"]

    resp, code = get("/records/", headers={"Authorization": f"Bearer {token4}"}, expect_error=True)
    assert code == 403, f"Expected 403, got {code}"
    print("  [OK] Level 4 blocked from records (403)")


if __name__ == "__main__":
    admin_token = test_login_2fa()
    test_endpoints_with_token(admin_token)
    test_activation_flow(admin_token)
    test_level4_blocked()
    print("\n=== ALL TESTS PASSED ===")
