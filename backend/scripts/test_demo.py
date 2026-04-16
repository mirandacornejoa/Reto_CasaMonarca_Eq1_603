"""Script de pruebas rapidas para validar todos los endpoints de la demo."""
import json
import urllib.request
import urllib.parse
import urllib.error
import sys

BASE = "http://localhost:8000/api/v1"

def login(email, password):
    data = urllib.parse.urlencode({"username": email, "password": password}).encode()
    req = urllib.request.Request(f"{BASE}/auth/login", data=data, method="POST")
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())["access_token"]

def api(method, path, token=None, body=None):
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    if body:
        req.add_header("Content-Type", "application/json")
    try:
        resp = urllib.request.urlopen(req)
        return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())

def test(desc, status, expected, actual_status, actual_body=None):
    ok = actual_status == expected
    mark = "[PASS]" if ok else "[FAIL]"
    print(f"  {mark} {desc} -> {actual_status} (esperado {expected})")
    if not ok and actual_body:
        detail = actual_body.get("detail", str(actual_body)[:100])
        print(f"        Detalle: {detail}")
    return ok

passed = 0
failed = 0

print("=== 1. Login todos los roles ===")
tokens = {}
for email, pwd, label in [
    ("admin@demo.org", "Admin123!", "admin"),
    ("coordinador@demo.org", "Coord123!", "coordinador"),
    ("operador@demo.org", "Oper123!", "operador"),
    ("externo@demo.org", "Ext123!", "externo"),
]:
    try:
        tokens[label] = login(email, pwd)
        ok = test(f"Login {label}", 200, 200, 200)
    except urllib.error.HTTPError as e:
        ok = test(f"Login {label}", 200, 200, e.code, json.loads(e.read()))
    passed += ok
    failed += not ok

print("\n=== 2. Auth /me para cada rol ===")
for label, token in tokens.items():
    s, b = api("GET", "/auth/me", token)
    ok = test(f"/me {label}", 200, 200, s)
    if ok:
        print(f"        Nivel: {b.get('access_level_code')}, Rol: {b.get('role_name')}")
    passed += ok
    failed += not ok

print("\n=== 3. Admin: Listar usuarios ===")
s, b = api("GET", "/users/", tokens["admin"])
ok = test("GET /users/ (admin)", 200, 200, s)
if ok:
    print(f"        Total usuarios: {len(b)}")
passed += ok; failed += not ok

print("\n=== 4. RBAC: Coordinador NO puede listar usuarios ===")
s, b = api("GET", "/users/", tokens["coordinador"])
ok = test("GET /users/ (coordinador)", 403, 403, s, b)
passed += ok; failed += not ok

print("\n=== 5. Admin: Listar certificados ===")
s, b = api("GET", "/certificates/", tokens["admin"])
ok = test("GET /certificates/ (admin)", 200, 200, s)
if ok:
    print(f"        Total certificados: {len(b)}")
    if b:
        print(f"        Primer cert: serial={b[0]['serial_number'][:12]}..., status={b[0]['status']}, fingerprint={b[0]['fingerprint'][:16]}...")
passed += ok; failed += not ok

print("\n=== 6. Externo: Vista publica certificados ===")
s, b = api("GET", "/certificates/public", tokens["externo"])
ok = test("GET /certificates/public (externo)", 200, 200, s)
passed += ok; failed += not ok

print("\n=== 7. Validar certificado ===")
s, b = api("GET", "/certificates/validate/1", tokens["externo"])
ok = test("GET /certificates/validate/1 (externo)", 200, 200, s)
if ok:
    print(f"        Valido: {b.get('is_valid')}, Mensaje: {b.get('message')}")
passed += ok; failed += not ok

print("\n=== 8. Externo NO puede ver detalle completo de cert ===")
s, b = api("GET", "/certificates/1", tokens["externo"])
ok = test("GET /certificates/1 (externo)", 403, 403, s, b)
passed += ok; failed += not ok

print("\n=== 9. Listar registros (todos) ===")
for label in ["admin", "coordinador", "operador", "externo"]:
    s, b = api("GET", "/records/", tokens[label])
    ok = test(f"GET /records/ ({label})", 200, 200, s)
    if ok and label == "admin":
        print(f"        Total registros: {len(b)}")
        if b:
            print(f"        Primer registro: {b[0]['name_or_alias']}, hash={b[0].get('sha256_hash', 'N/A')[:16]}...")
    passed += ok; failed += not ok

print("\n=== 10. Crear registro (operador) ===")
new_rec = {
    "name_or_alias": "Test Record API",
    "nationality": "Mexico",
    "observations": "Registro creado por test automatizado",
    "status": "REGISTRADO"
}
s, b = api("POST", "/records/", tokens["operador"], new_rec)
ok = test("POST /records/ (operador)", 201, 201, s, b)
if ok:
    rec_id = b["id"]
    print(f"        ID: {rec_id}, Hash: {b.get('sha256_hash', 'N/A')[:16]}...")
passed += ok; failed += not ok

print("\n=== 11. Externo NO puede crear registro ===")
s, b = api("POST", "/records/", tokens["externo"], new_rec)
ok = test("POST /records/ (externo)", 403, 403, s, b)
passed += ok; failed += not ok

print("\n=== 12. Editar registro (coordinador) ===")
update = {"observations": "Actualizado por coordinador"}
s, b = api("PUT", "/records/1", tokens["coordinador"], update)
ok = test("PUT /records/1 (coordinador)", 200, 200, s, b)
if ok:
    print(f"        Hash actualizado: {b.get('sha256_hash', 'N/A')[:16]}...")
passed += ok; failed += not ok

print("\n=== 13. Externo NO puede editar ===")
s, b = api("PUT", "/records/1", tokens["externo"], update)
ok = test("PUT /records/1 (externo)", 403, 403, s, b)
passed += ok; failed += not ok

print("\n=== 14. Consultar hash de registro ===")
s, b = api("GET", "/records/1/hash", tokens["admin"])
ok = test("GET /records/1/hash (admin)", 200, 200, s)
if ok:
    print(f"        Hash: {b.get('sha256_hash', 'N/A')}")
passed += ok; failed += not ok

print("\n=== 15. Bitacora (admin) ===")
s, b = api("GET", "/audit/", tokens["admin"])
ok = test("GET /audit/ (admin)", 200, 200, s)
if ok:
    print(f"        Total entradas: {len(b)}")
    for entry in b[:3]:
        print(f"        - {entry['action']} | {entry['resource']} | {entry['result']} | hash={entry.get('hash_related', '-')}")
passed += ok; failed += not ok

print("\n=== 16. RBAC: bitacora prohibida para otros roles ===")
for label in ["coordinador", "operador", "externo"]:
    s, b = api("GET", "/audit/", tokens[label])
    ok = test(f"GET /audit/ ({label})", 403, 403, s, b)
    passed += ok; failed += not ok

print(f"\n{'='*50}")
print(f"RESULTADOS: {passed} pasaron, {failed} fallaron, {passed+failed} total")
if failed == 0:
    print("TODOS LOS TESTS PASARON")
else:
    print(f"ATENCION: {failed} tests fallaron")
