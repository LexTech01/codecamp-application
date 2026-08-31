"""Seed the initial gallery images into the database.

Copies the legacy gallery images from app/static/images/ into
app/static/images/gallery/ and creates GalleryItem rows (idempotent).

Run from the project root:

    python -m scripts.seed_gallery
"""
import os
import sys
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models.gallery import GalleryItem

# (source filename in static/images, alt, category)
SEED = [
    ("IMG_8385.JPG", "CodeCamp Event 1", "events"),
    ("IMG_8386.JPG", "CodeCamp Event 2", "events"),
    ("IMG_8387.JPG", "CodeCamp Event 3", "events"),
    ("IMG_8388.JPG", "CodeCamp Event 4", "events"),
    ("img5.JPG", "CodeCamp Event 5", "events"),
    ("IMG_8393.JPG", "CodeCamp Event 6", "events"),
    ("software.jpeg", "Software Engineering Class", "programs"),
    ("telecom.jpeg", "Networking & Telecom Lab", "programs"),
    ("hero-img3.JPG", "Campus Life 1", "campus"),
    ("hero-img4.jpeg", "Campus Life 2", "campus"),
    ("image1.jpeg", "Students Collaborating", "campus"),
    ("image3.jpeg", "Graduation Ceremony", "campus"),
]


def main():
    app = create_app()
    with app.app_context():
        src_dir = os.path.join(app.root_path, "static", "images")
        dst_dir = os.path.join(app.root_path, "static", "images", "gallery")
        os.makedirs(dst_dir, exist_ok=True)

        existing = {g.filename for g in GalleryItem.query.all()}
        added = 0
        for fname, alt, category in SEED:
            if fname in existing:
                continue
            src = os.path.join(src_dir, fname)
            if not os.path.exists(src):
                print(f"SKIP missing source: {fname}")
                continue
            shutil.copy2(src, os.path.join(dst_dir, fname))
            db.session.add(GalleryItem(filename=fname, alt=alt, category=category))
            added += 1

        db.session.commit()
        print(f"Added {added} gallery item(s). Total: {GalleryItem.query.count()}")


if __name__ == "__main__":
    main()
