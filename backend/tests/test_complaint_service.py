"""
Unit tests for the image-validation branch of complaint_service, using a
mocked DB session/query chain rather than a real Postgres+PostGIS
instance. Full integration tests (create -> list -> filter -> status
transition against a live test database) belong in a future
test_complaints_api.py once a test-DB fixture exists.
"""

import io
import os
import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://user:pass@localhost/db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests-only")

from app.services import complaint_service  # noqa: E402


def _fake_upload_file(content: bytes, content_type: str, filename: str = "photo.jpg"):
    return SimpleNamespace(
        file=io.BytesIO(content),
        content_type=content_type,
        filename=filename,
    )


def _db_with_complaint(complaint_id: uuid.UUID):
    """A MagicMock DB session whose query().options().filter().first()
    chain returns a stand-in Complaint with the given id."""
    fake_complaint = SimpleNamespace(id=complaint_id, images=[])
    db = MagicMock()
    db.query.return_value.options.return_value.filter.return_value.first.return_value = fake_complaint
    return db


def test_rejects_unsupported_content_type():
    complaint_id = uuid.uuid4()
    db = _db_with_complaint(complaint_id)
    upload = _fake_upload_file(b"not-really-an-image", content_type="application/pdf")

    try:
        complaint_service.save_complaint_image(db, complaint_id, upload)
        assert False, "expected InvalidImageError for a non-image content type"
    except complaint_service.InvalidImageError as exc:
        assert "Unsupported image type" in str(exc)


def test_rejects_oversized_image(monkeypatch):
    monkeypatch.setattr(complaint_service.settings, "MAX_UPLOAD_SIZE_MB", 1)  # 1MB cap for this test
    complaint_id = uuid.uuid4()
    db = _db_with_complaint(complaint_id)

    oversized_content = b"0" * (2 * 1024 * 1024)  # 2MB, over the 1MB cap
    upload = _fake_upload_file(oversized_content, content_type="image/jpeg")

    try:
        complaint_service.save_complaint_image(db, complaint_id, upload)
        assert False, "expected InvalidImageError for an oversized image"
    except complaint_service.InvalidImageError as exc:
        assert "exceeds" in str(exc)


def test_missing_complaint_raises_not_found():
    db = MagicMock()
    db.query.return_value.options.return_value.filter.return_value.first.return_value = None

    try:
        complaint_service.get_complaint(db, uuid.uuid4())
        assert False, "expected ComplaintNotFoundError for a missing complaint"
    except complaint_service.ComplaintNotFoundError:
        pass
