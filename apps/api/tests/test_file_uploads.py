import io

from fastapi.testclient import TestClient


def test_upload_valid_jpeg(client: TestClient) -> None:
    # Register buyer
    res = client.post(
        "/api/v1/auth/register/buyer",
        json={
            "email": "upload_buyer@test.com",
            "password": "Password123!",
            "full_name": "Upload Buyer",
        },
    )
    token = res.json()["token"]

    # Valid JPEG header \xFF\xD8\xFF + dummy content
    jpeg_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb"
    files = {"file": ("damage_photo.jpg", io.BytesIO(jpeg_bytes), "image/jpeg")}

    upload_res = client.post(
        "/api/v1/files/upload",
        headers={"Authorization": f"Bearer {token}"},
        files=files,
    )
    assert upload_res.status_code == 201
    data = upload_res.json()
    assert "file_id" in data
    assert data["filename"] == "damage_photo.jpg"
    assert data["mime_type"] == "image/jpeg"

    # Fetch file
    get_res = client.get(
        data["url"],
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_res.status_code == 200
    assert get_res.content == jpeg_bytes


def test_upload_invalid_mime_type_rejected(client: TestClient) -> None:
    res = client.post(
        "/api/v1/auth/register/buyer",
        json={
            "email": "mime_buyer@test.com",
            "password": "Password123!",
            "full_name": "Mime Buyer",
        },
    )
    token = res.json()["token"]

    files = {"file": ("script.exe", io.BytesIO(b"MZ1234567890"), "application/octet-stream")}
    upload_res = client.post(
        "/api/v1/files/upload",
        headers={"Authorization": f"Bearer {token}"},
        files=files,
    )
    assert upload_res.status_code == 400
    detail = upload_res.json().get("error", {}).get("message") or upload_res.json().get(
        "detail", ""
    )
    assert "Unsupported file type" in detail


def test_upload_corrupted_magic_bytes_rejected(client: TestClient) -> None:
    res = client.post(
        "/api/v1/auth/register/buyer",
        json={
            "email": "magic_buyer@test.com",
            "password": "Password123!",
            "full_name": "Magic Buyer",
        },
    )
    token = res.json()["token"]

    # Claims image/jpeg but content is plain text
    files = {
        "file": ("fake.jpg", io.BytesIO(b"This is just plain text, not a jpeg!"), "image/jpeg")
    }
    upload_res = client.post(
        "/api/v1/files/upload",
        headers={"Authorization": f"Bearer {token}"},
        files=files,
    )
    assert upload_res.status_code == 400
    detail = upload_res.json().get("error", {}).get("message") or upload_res.json().get(
        "detail", ""
    )
    assert "File signature does not match" in detail
