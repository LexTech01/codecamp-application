"""Gallery images shown on the public landing page and gallery page."""
from datetime import datetime, timezone
from app import db

GALLERY_CATEGORIES = ("events", "programs", "campus")


class GalleryItem(db.Model):
    __tablename__ = "gallery_items"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    alt = db.Column(db.String(200), nullable=True)
    category = db.Column(db.String(50), nullable=False, default="events")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "file": f"images/gallery/{self.filename}",
            "alt": self.alt or "",
            "category": self.category,
        }
