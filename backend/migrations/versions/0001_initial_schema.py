"""initial schema: users, complaints, complaint_images, vehicle_detections,
predictions, hotspots, officer_recommendations

Revision ID: 0001
Revises:
Create Date: 2026-07-26

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import geoalchemy2

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PostGIS must be enabled before any Geometry columns are created
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    op.execute("CREATE TYPE user_role AS ENUM ('citizen', 'officer', 'admin')")
    op.execute("CREATE TYPE complaint_source AS ENUM ('portal', 'mobile_app', 'email', 'social_media')")
    op.execute(
        "CREATE TYPE complaint_type AS ENUM "
        "('illegal_parking', 'double_parking', 'no_parking_zone', "
        "'footpath_parking', 'emergency_exit_blocking', 'unclassified')"
    )
    op.execute(
        "CREATE TYPE complaint_status AS ENUM "
        "('pending', 'approved', 'rejected', 'duplicate', 'resolved')"
    )
    op.execute(
        "CREATE TYPE prediction_type AS ENUM "
        "('hotspot_forecast', 'violation_probability', 'enforcement_time', 'officer_deployment')"
    )
    op.execute(
        "CREATE TYPE recommendation_status AS ENUM "
        "('suggested', 'accepted', 'dismissed', 'completed')"
    )

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("username", sa.String(64), nullable=False, unique=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(150)),
        sa.Column("phone_number", sa.String(32)),
        sa.Column("role", postgresql.ENUM("citizen", "officer", "admin", name="user_role", create_type=False), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_users_username", "users", ["username"])
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "complaints",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("source", postgresql.ENUM("portal", "mobile_app", "email", "social_media", name="complaint_source", create_type=False), nullable=False),
        sa.Column("raw_text", sa.Text, nullable=False),
        sa.Column("location_text", sa.Text),
        sa.Column("contact_name", sa.String(150)),
        sa.Column("contact_phone", sa.String(32)),
        sa.Column("contact_email", sa.String(255)),
        sa.Column("cleaned_text", sa.Text),
        sa.Column("extracted_location_entity", sa.Text),
        sa.Column(
            "complaint_type",
            postgresql.ENUM(
                "illegal_parking", "double_parking", "no_parking_zone",
                "footpath_parking", "emergency_exit_blocking", "unclassified",
                name="complaint_type", create_type=False,
            ),
            server_default="unclassified",
        ),
        sa.Column("classification_confidence", sa.Float),
        sa.Column("is_duplicate", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("duplicate_of_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("complaints.id"), nullable=True),
        sa.Column("duplicate_similarity_score", sa.Float),
        sa.Column("geom", geoalchemy2.Geometry(geometry_type="POINT", srid=4326)),
        sa.Column("address", sa.Text),
        sa.Column(
            "status",
            postgresql.ENUM("pending", "approved", "rejected", "duplicate", "resolved", name="complaint_status", create_type=False),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("submitted_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_complaints_status", "complaints", ["status"])
    op.create_index("ix_complaints_complaint_type", "complaints", ["complaint_type"])
    op.create_index("ix_complaints_geom", "complaints", ["geom"], postgresql_using="gist")

    op.create_table(
        "complaint_images",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("complaint_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("complaints.id"), nullable=False),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("original_filename", sa.String(255)),
        sa.Column("content_type", sa.String(100)),
        sa.Column("file_size_bytes", sa.Integer),
        sa.Column("processed", sa.Boolean, server_default=sa.false()),
        sa.Column("uploaded_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_complaint_images_complaint_id", "complaint_images", ["complaint_id"])

    op.create_table(
        "vehicle_detections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("complaint_image_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("complaint_images.id"), nullable=False),
        sa.Column("vehicle_class", sa.String(50), nullable=False),
        sa.Column("detection_confidence", sa.Float, nullable=False),
        sa.Column("bbox_x", sa.Float, nullable=False),
        sa.Column("bbox_y", sa.Float, nullable=False),
        sa.Column("bbox_width", sa.Float, nullable=False),
        sa.Column("bbox_height", sa.Float, nullable=False),
        sa.Column("is_illegal_parking", sa.Boolean),
        sa.Column("illegal_parking_reason", sa.String(255)),
        sa.Column("model_name", sa.String(100), server_default="yolov8n"),
        sa.Column("model_version", sa.String(50)),
        sa.Column("detected_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_vehicle_detections_complaint_image_id", "vehicle_detections", ["complaint_image_id"])

    op.create_table(
        "predictions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "prediction_type",
            postgresql.ENUM(
                "hotspot_forecast", "violation_probability", "enforcement_time", "officer_deployment",
                name="prediction_type", create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("geom", geoalchemy2.Geometry(geometry_type="POINT", srid=4326)),
        sa.Column("predicted_value", sa.Float),
        sa.Column("confidence", sa.Float),
        sa.Column("payload", sa.JSON),
        sa.Column("model_name", sa.String(100), nullable=False),
        sa.Column("model_version", sa.String(50)),
        sa.Column("valid_from", sa.DateTime(timezone=True)),
        sa.Column("valid_to", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_predictions_geom", "predictions", ["geom"], postgresql_using="gist")
    op.create_index("ix_predictions_type", "predictions", ["prediction_type"])

    op.create_table(
        "hotspots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("geom", geoalchemy2.Geometry(geometry_type="POINT", srid=4326), nullable=False),
        sa.Column("radius_meters", sa.Float, server_default="200.0"),
        sa.Column("violation_count", sa.Integer, nullable=False),
        sa.Column("risk_score", sa.Float, nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_hotspots_geom", "hotspots", ["geom"], postgresql_using="gist")

    op.create_table(
        "officer_recommendations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("hotspot_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hotspots.id"), nullable=True),
        sa.Column("officer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("geom", geoalchemy2.Geometry(geometry_type="POINT", srid=4326), nullable=False),
        sa.Column("recommended_time_start", sa.Time),
        sa.Column("recommended_time_end", sa.Time),
        sa.Column("priority_score", sa.Float, nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM("suggested", "accepted", "dismissed", "completed", name="recommendation_status", create_type=False),
            nullable=False,
            server_default="suggested",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_officer_recommendations_geom", "officer_recommendations", ["geom"], postgresql_using="gist")


def downgrade() -> None:
    op.drop_table("officer_recommendations")
    op.drop_table("hotspots")
    op.drop_table("predictions")
    op.drop_table("vehicle_detections")
    op.drop_table("complaint_images")
    op.drop_table("complaints")
    op.drop_table("users")

    op.execute("DROP TYPE IF EXISTS recommendation_status")
    op.execute("DROP TYPE IF EXISTS prediction_type")
    op.execute("DROP TYPE IF EXISTS complaint_status")
    op.execute("DROP TYPE IF EXISTS complaint_type")
    op.execute("DROP TYPE IF EXISTS complaint_source")
    op.execute("DROP TYPE IF EXISTS user_role")
