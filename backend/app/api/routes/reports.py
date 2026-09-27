"""
Report generation. Currently a single CSV export of complaints — the
spec's "export reports" requirement in the Admin Panel. PDF/scheduled
reports are natural follow-ons but weren't asked for with enough
specificity to build without guessing a format; CSV covers the actual
need (get complaint data into a spreadsheet) directly.
"""

import csv
import io
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.deps import require_roles
from app.database import get_db
from app.models.complaint import ComplaintStatus, ComplaintType
from app.models.user import User, UserRole
from app.services import complaint_service

router = APIRouter()

CSV_COLUMNS = [
    "id",
    "source",
    "complaint_type",
    "status",
    "is_duplicate",
    "location_text",
    "address",
    "classification_confidence",
    "submitted_at",
]


@router.get("/complaints/csv", summary="Export complaints as CSV (officer/admin only)")
def export_complaints_csv(
    status_filter: Optional[ComplaintStatus] = Query(None, alias="status"),
    complaint_type: Optional[ComplaintType] = None,
    submitted_from: Optional[datetime] = None,
    submitted_to: Optional[datetime] = None,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles(UserRole.OFFICER, UserRole.ADMIN)),
):
    # Reuses complaint_service's filtering so this stays consistent with
    # GET /api/complaints rather than re-implementing the same filters;
    # capped at a generous limit since this is a direct export, not a
    # paginated UI list.
    items, _total = complaint_service.list_complaints(
        db,
        status_filter=status_filter,
        complaint_type=complaint_type,
        submitted_from=submitted_from,
        submitted_to=submitted_to,
        limit=50_000,
    )

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(CSV_COLUMNS)
    for complaint in items:
        writer.writerow(
            [
                str(complaint.id),
                complaint.source.value,
                complaint.complaint_type.value,
                complaint.status.value,
                complaint.is_duplicate,
                complaint.location_text or "",
                complaint.address or "",
                complaint.classification_confidence or "",
                complaint.submitted_at.isoformat(),
            ]
        )
    buffer.seek(0)

    filename = f"complaints_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        buffer,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
