import io

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


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


def test_evidence_is_scoped_to_the_case_buyer_and_seller(
    client: TestClient,
    db: Session,
    auth_headers_for_user,
    tmp_path,
) -> None:
    from app.models.file_upload import FileUpload
    from tests.factories import make_buyer, make_case, make_order, make_seller, unique

    owner = make_seller(db)
    intruder = make_seller(db)
    buyer = make_buyer(db)
    order = make_order(db, owner, buyer)
    case = make_case(db, order, category="damaged")

    evidence_path = tmp_path / "evidence.jpg"
    evidence_path.write_bytes(b"\xff\xd8\xff evidence")
    record = FileUpload(
        uploader_id=buyer.user_id,
        case_id=case.id,
        original_filename="evidence.jpg",
        stored_filename=f"{unique('file')}.jpg",
        mime_type="image/jpeg",
        file_size_bytes=evidence_path.stat().st_size,
        storage_path=str(evidence_path),
    )
    db.add(record)
    db.flush()

    url = f"/api/v1/files/{record.id}"

    owner_res = client.get(url, headers=auth_headers_for_user(owner.user_id, "seller"))
    assert owner_res.status_code == 200

    buyer_res = client.get(url, headers=auth_headers_for_user(buyer.user_id, "buyer"))
    assert buyer_res.status_code == 200

    intruder_res = client.get(
        url, headers=auth_headers_for_user(intruder.user_id, "seller")
    )
    assert intruder_res.status_code == 403
