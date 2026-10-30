from datetime import datetime

from database.db import db


class Interview(db.Model):

    __tablename__ = "interviews"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    role = db.Column(
        db.String(100),
        nullable=False
    )

    final_score = db.Column(
        db.Float,
        nullable=False
    )

    percentage = db.Column(
        db.Float,
        nullable=False
    )

    strengths = db.Column(
        db.Text,
        nullable=True
    )

    weaknesses = db.Column(
        db.Text,
        nullable=True
    )

    improvement_suggestions = db.Column(
        db.Text,
        nullable=True
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )