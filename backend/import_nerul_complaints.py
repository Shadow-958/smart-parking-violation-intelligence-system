import random
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.models.complaint import (
    Complaint,
    ComplaintSource,
    ComplaintType,
    ComplaintStatus,
)

settings = get_settings()

# ---------------------------------------------------------
# DATABASE
# ---------------------------------------------------------

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

# ---------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------

TOTAL_COMPLAINTS = 150

# ---------------------------------------------------------
# NERUL LOCATIONS
# ---------------------------------------------------------

LOCATIONS = [
    ("Nerul Railway Station", 19.0330, 73.0297),
    ("SIES Graduate School of Technology", 19.0435, 73.0250),
    ("Palm Beach Road", 19.0355, 73.0195),
    ("Sector 15, Nerul", 19.0415, 73.0265),
    ("Sector 18, Nerul", 19.0345, 73.0255),
    ("Nerul Bus Depot", 19.0368, 73.0235),
    ("Jewel of Navi Mumbai", 19.0450, 73.0190),
    ("Sector 10, Nerul", 19.0385, 73.0310),
    ("Sector 20, Nerul", 19.0325, 73.0220),
    ("Nerul East Market", 19.0375, 73.0300),
]

# ---------------------------------------------------------
# COMPLAINT TYPES
# ---------------------------------------------------------

VIOLATIONS = [
    (
        ComplaintType.NO_PARKING_ZONE,
        "A vehicle is parked in a designated No Parking zone.",
    ),
    (
        ComplaintType.ILLEGAL_PARKING,
        "A vehicle is illegally parked on the roadside.",
    ),
    (
        ComplaintType.DOUBLE_PARKING,
        "A vehicle is double parked and obstructing traffic.",
    ),
    (
        ComplaintType.FOOTPATH_PARKING,
        "A vehicle is parked on the footpath and blocking pedestrians.",
    ),
    (
        ComplaintType.EMERGENCY_EXIT_BLOCKING,
        "A vehicle is blocking an emergency exit.",
    ),
]

# ---------------------------------------------------------
# TIME DISTRIBUTION
# ---------------------------------------------------------
# Generate realistic parking complaints at different times.

TIME_RANGES = [
    (6, 9),
    (9, 12),
    (12, 15),
    (15, 18),
    (18, 21),
    (21, 23),
]


def random_datetime():

    now = datetime.now(timezone.utc)

    # Random date within previous 30 days
    days_ago = random.randint(0, 29)

    date = now - timedelta(days=days_ago)

    # Random time period
    start_hour, end_hour = random.choice(TIME_RANGES)

    hour = random.randint(start_hour, end_hour)
    minute = random.randint(0, 59)
    second = random.randint(0, 59)

    return date.replace(
        hour=hour,
        minute=minute,
        second=second,
        microsecond=0,
    )


def create_complaint():

    location_name, base_lat, base_lon = random.choice(LOCATIONS)

    complaint_type, description = random.choice(VIOLATIONS)

    # Small random movement around the location.
    # This creates clusters instead of putting every complaint
    # at exactly the same coordinate.
    latitude = base_lat + random.uniform(-0.0015, 0.0015)
    longitude = base_lon + random.uniform(-0.0015, 0.0015)

    submitted_at = random_datetime()

    complaint = Complaint(
        id=uuid.uuid4(),

        user_id=None,

        source=ComplaintSource.HISTORICAL_IMPORT,

        raw_text=(
            f"{description} "
            f"Location: {location_name}, Nerul, Navi Mumbai."
        ),

        location_text=(
            f"{location_name}, Nerul, Navi Mumbai"
        ),

        contact_name="Synthetic Demo Data",

        contact_phone=None,

        contact_email="demo@example.com",

        complaint_type=complaint_type,

        classification_confidence=random.uniform(0.85, 0.99),

        is_duplicate=False,

        duplicate_of_id=None,

        duplicate_similarity_score=None,

        embedding=None,

        address=(
            f"{location_name}, Nerul, Navi Mumbai"
        ),

        status=ComplaintStatus.APPROVED,

        submitted_at=submitted_at,

        updated_at=submitted_at,
    )

    # PostGIS geometry
    complaint.geom = (
        f"SRID=4326;"
        f"POINT({longitude} {latitude})"
    )

    return complaint


def main():

    db = SessionLocal()

    try:

        print("=" * 60)
        print("NERUL SYNTHETIC COMPLAINT IMPORT")
        print("=" * 60)

        complaints = []

        for i in range(TOTAL_COMPLAINTS):

            complaint = create_complaint()

            complaints.append(complaint)

        db.add_all(complaints)

        db.commit()

        print()
        print(f"Successfully inserted {len(complaints)} complaints.")
        print()
        print("Coverage:")
        print("  Location : Nerul, Navi Mumbai")
        print("  Period   : Previous 30 days")
        print("  Times    : Multiple times throughout the day")
        print("  Source   : historical_import")
        print()

    except Exception as e:

        db.rollback()

        print("IMPORT FAILED")
        print(e)

    finally:

        db.close()


if __name__ == "__main__":
    main()