import httpx
import random

def main():
    client = httpx.Client(base_url="http://127.0.0.1:3000", timeout=10.0)

    # 1. Check visual assets
    print("--- 1. Testing Visual Assets ---")
    assets = [
        "/images/tree.png",
        "/visuals/decision-paths.svg",
        "/visuals/store-connect.svg",
        "/visuals/policy-shield.svg",
    ]
    for asset in assets:
        r = client.get(asset)
        assert r.status_code == 200, f"Asset {asset} failed with {r.status_code}"
        print(f"[OK] {asset} -> HTTP {r.status_code} ({len(r.content)} bytes)")

    # 2. Check seller login
    print("\n--- 2. Testing Seller Login ---")
    r = client.post("/api/v1/auth/login", json={"email": "seller@store.com", "password": "Password123!"})
    assert r.status_code == 200, f"Seller login failed: {r.text}"
    data = r.json()
    print(f"[OK] Seller login: redirect={data.get('redirect_uri')}, cookies={list(r.cookies.keys())}")

    # Check seller audit & customers
    r_audit = client.get("/api/v1/seller/audit")
    assert r_audit.status_code == 200, f"Seller audit failed: {r_audit.text}"
    print(f"[OK] Seller audit: {len(r_audit.json())} entries")

    # 3. Check buyer login
    print("\n--- 3. Testing Buyer Login ---")
    buyer_client = httpx.Client(base_url="http://127.0.0.1:3000", timeout=10.0)
    r = buyer_client.post("/api/v1/auth/login", json={"email": "buyer@example.com", "password": "Password123!"})
    assert r.status_code == 200, f"Buyer login failed: {r.text}"
    data = r.json()
    print(f"[OK] Buyer login: redirect={data.get('redirect_uri')}, cookies={list(r.cookies.keys())}")

    # Check buyer orders API
    r_orders = buyer_client.get("/api/v1/buyer/orders")
    assert r_orders.status_code == 200, f"Orders API failed: {r_orders.text}"
    orders = r_orders.json()
    print(f"[OK] Buyer orders API returned {len(orders)} orders")
    for o in orders:
        assert "total_amount" in o
        for item in o.get("items", []):
            assert "total_price" in item, f"Missing total_price in item: {item}"
            assert isinstance(item["total_price"], (int, float)), f"total_price is not numeric: {item['total_price']}"
    print("[OK] All buyer order items have valid numeric total_price")

    # 4. Check buyer registration
    print("\n--- 4. Testing Buyer Registration ---")
    rnd_email = f"buyer_{random.randint(10000, 99999)}@example.com"
    r = client.post("/api/v1/auth/register/buyer", json={
        "email": rnd_email,
        "password": "Password123!",
        "full_name": "Verified Customer",
        "phone": "+1 555-0122",
    })
    assert r.status_code == 201, f"Buyer registration failed: {r.text}"
    data = r.json()
    print(f"[OK] Buyer registration: created user {rnd_email}, redirect={data.get('redirect_uri')}")

    # 5. Check logout
    print("\n--- 5. Testing Logout ---")
    r = client.post("/api/v1/auth/logout")
    assert r.status_code == 200, f"Logout failed: {r.text}"
    print(f"[OK] Logout successful: {r.json().get('message')}")

    # 6. Check landing and auth pages load HTTP 200
    print("\n--- 6. Testing Page Route Statuses ---")
    routes = [
        "/",
        "/login",
        "/login/seller",
        "/login/buyer",
        "/register/seller",
        "/register/buyer",
        "/buyer",
        "/seller",
        "/buyer/orders",
        "/buyer/sellers",
        "/seller/dashboard",
        "/seller/audit",
        "/seller/customers",
        "/seller/approvals",
    ]
    for route in routes:
        r = client.get(route, follow_redirects=False)
        assert r.status_code == 200, f"Route {route} returned {r.status_code}"
        print(f"[OK] {route} -> HTTP {r.status_code}")

    print("\nALL VERIFICATION CHECKS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    main()
