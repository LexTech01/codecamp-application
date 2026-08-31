"""Tests for the admin-managed public gallery."""
import os
from io import BytesIO
from app import db
from app.models.user import User
from app.models.gallery import GalleryItem


def _create_admin(app, email="admin@test.com"):
    with app.app_context():
        u = User(email=email, first_name="Admin", last_name="One", role="admin")
        u.set_password("password123")
        db.session.add(u)
        db.session.commit()
        return u.id


def _create_student(app, email="stu@test.com"):
    with app.app_context():
        u = User(email=email, first_name="Stu", last_name="Dent", role="student")
        u.set_password("password123")
        db.session.add(u)
        db.session.commit()
        return u.id


def _login(client, user_id):
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user_id)
        sess["_fresh"] = True
        sess["_sess_v"] = 1


def _gallery_folder(app):
    return os.path.join(app.root_path, "static", "images", "gallery")


def test_gallery_admin_page_requires_admin(app, client):
    stu_id = _create_student(app)
    _login(client, stu_id)
    resp = client.get("/admin/gallery")
    assert resp.status_code == 302  # student redirected away


def test_admin_uploads_gallery_image(app, client):
    admin_id = _create_admin(app)
    _login(client, admin_id)
    data = {
        "alt": "Grand Opening",
        "category": "events",
        "image": (BytesIO(b"fake-image-bytes"), "opening.png"),
    }
    resp = client.post(
        "/admin/gallery", data=data, content_type="multipart/form-data"
    )
    assert resp.status_code == 302

    with app.app_context():
        item = GalleryItem.query.first()
        assert item is not None
        assert item.alt == "Grand Opening"
        assert item.category == "events"
        assert item.filename.endswith("opening.png")
        saved = os.path.join(_gallery_folder(app), item.filename)
        assert os.path.exists(saved)
        with open(saved, "rb") as f:
            assert f.read() == b"fake-image-bytes"
        # cleanup
        try:
            os.remove(saved)
        except OSError:
            pass


def test_admin_deletes_gallery_image(app, client):
    admin_id = _create_admin(app)
    with app.app_context():
        item = GalleryItem(filename="tmp_delete.jpg", alt="X", category="campus")
        db.session.add(item)
        db.session.commit()
        item_id = item.id
        # create a stub file on disk to confirm it is removed
        path = os.path.join(_gallery_folder(app), "tmp_delete.jpg")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(b"stub")
    _login(client, admin_id)
    resp = client.post(f"/admin/gallery/{item_id}/delete")
    assert resp.status_code == 302
    with app.app_context():
        assert GalleryItem.query.get(item_id) is None
        assert not os.path.exists(path)


def test_public_gallery_renders_db_images(app, client):
    with app.app_context():
        db.session.add(GalleryItem(filename="x.png", alt="Alpha", category="events"))
        db.session.commit()
    resp = client.get("/gallery")
    assert resp.status_code == 200
    assert b"Alpha" in resp.data
    assert b"images/gallery/x.png" in resp.data


def test_landing_shows_latest_gallery_images(app, client):
    with app.app_context():
        for i in range(6):
            db.session.add(GalleryItem(filename=f"g{i}.png", alt=f"Alt {i}", category="events"))
        db.session.commit()
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "images/gallery/g0.png" in html
