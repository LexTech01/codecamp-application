"""Tests for admin user management and bulk applicant actions."""
import csv
from io import StringIO
import pytest
from app import db
from app.models.user import User
from app.models.application import Application
from app.models.notification import Notification


def _create_admin(app, email="admin@test.com"):
    with app.app_context():
        u = User(email=email, first_name="Admin", last_name="One", role="admin")
        u.set_password("password123")
        db.session.add(u)
        db.session.commit()
        return u.id


def _create_student(app, email="stu@test.com", first="Stu", last="Dent"):
    with app.app_context():
        u = User(email=email, first_name=first, last_name=last, role="student")
        u.set_password("password123")
        db.session.add(u)
        db.session.commit()
        return u.id


def _login(client, user_id):
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user_id)
        sess["_fresh"] = True
        sess["_sess_v"] = 1


def _submit_application(app, user_id, program="Software Engineering", stage="submitted"):
    with app.app_context():
        a = Application(
            user_id=user_id,
            is_submitted=True,
            pipeline_stage=stage,
            status=stage,
            field_of_study=program,
        )
        db.session.add(a)
        db.session.commit()
        return a.id


# ── User management ─────────────────────────────────────────────


def test_users_page_lists_all(app, client):
    admin_id = _create_admin(app)
    _create_student(app)
    _login(client, admin_id)
    resp = client.get("/admin/users")
    assert resp.status_code == 200
    assert b"stu@test.com" in resp.data


def test_promote_student_to_admin(app, client):
    admin_id = _create_admin(app)
    stu_id = _create_student(app)
    _login(client, admin_id)
    resp = client.post(f"/admin/users/{stu_id}/role", data={"role": "admin"})
    assert resp.status_code == 302
    with app.app_context():
        assert User.query.get(stu_id).role == "admin"


def test_demote_student_self_blocked(app, client):
    admin_id = _create_admin(app)
    _login(client, admin_id)
    resp = client.post(f"/admin/users/{admin_id}/role", data={"role": "student"})
    assert resp.status_code == 302
    with app.app_context():
        assert User.query.get(admin_id).role == "admin"


def test_deactivate_student(app, client):
    admin_id = _create_admin(app)
    stu_id = _create_student(app)
    _login(client, admin_id)
    resp = client.post(f"/admin/users/{stu_id}/deactivate", data={"reason": "spam"})
    assert resp.status_code == 302
    with app.app_context():
        u = User.query.get(stu_id)
        assert u.is_active is False
        assert u.deactivated_reason == "spam"
        assert u.deactivated_at is not None


def test_reactivate_student(app, client):
    admin_id = _create_admin(app)
    stu_id = _create_student(app)
    _login(client, admin_id)
    client.post(f"/admin/users/{stu_id}/deactivate", data={"reason": ""})
    resp = client.post(f"/admin/users/{stu_id}/reactivate")
    assert resp.status_code == 302
    with app.app_context():
        u = User.query.get(stu_id)
        assert u.is_active is True
        assert u.deactivated_reason is None


def test_deactivated_user_cannot_be_admin_acted_on_self(app, client):
    admin_id = _create_admin(app)
    _login(client, admin_id)
    resp = client.post(f"/admin/users/{admin_id}/deactivate", data={"reason": ""})
    assert resp.status_code == 302
    with app.app_context():
        assert User.query.get(admin_id).is_active is True


# ── Bulk actions ────────────────────────────────────────────────


def test_bulk_move_to_under_review(app, client):
    admin_id = _create_admin(app)
    s1 = _create_student(app, "s1@test.com")
    s2 = _create_student(app, "s2@test.com")
    a1 = _submit_application(app, s1)
    a2 = _submit_application(app, s2)
    _login(client, admin_id)
    resp = client.post("/admin/applicants/bulk-action", data={
        "app_ids": [str(a1), str(a2)],
        "action": "move_to_under_review",
    })
    assert resp.status_code == 302
    with app.app_context():
        assert Application.query.get(a1).pipeline_stage == "under_review"
        assert Application.query.get(a2).pipeline_stage == "under_review"


def test_bulk_reject_with_reason(app, client):
    admin_id = _create_admin(app)
    s1 = _create_student(app, "r1@test.com")
    a1 = _submit_application(app, s1)
    _login(client, admin_id)
    resp = client.post("/admin/applicants/bulk-action", data={
        "app_ids": [str(a1)],
        "action": "reject",
        "reason": "Not eligible",
    })
    assert resp.status_code == 302
    with app.app_context():
        app_obj = Application.query.get(a1)
        assert app_obj.pipeline_stage == "rejected"
        assert app_obj.rejection_reason == "Not eligible"


def test_bulk_action_creates_notification(app, client):
    admin_id = _create_admin(app)
    s1 = _create_student(app, "n@test.com")
    a1 = _submit_application(app, s1)
    _login(client, admin_id)
    client.post("/admin/applicants/bulk-action", data={
        "app_ids": [str(a1)],
        "action": "move_to_under_review",
    })
    with app.app_context():
        assert Notification.query.filter_by(user_id=s1).count() == 1


def test_bulk_action_no_selection(app, client):
    admin_id = _create_admin(app)
    _login(client, admin_id)
    resp = client.post("/admin/applicants/bulk-action", data={"action": "reject"})
    assert resp.status_code == 302


# ── CSV export ──────────────────────────────────────────────────


def test_export_applicants_csv(app, client):
    admin_id = _create_admin(app)
    s1 = _create_student(app, "csv@test.com", first="Csv", last="User")
    a1 = _submit_application(app, s1, program="Networking")
    _login(client, admin_id)
    resp = client.get("/admin/applicants/export.csv")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["Content-Type"]
    content = resp.data.decode("utf-8")
    rows = list(csv.reader(StringIO(content)))
    assert rows[0][0] == "First Name"
    assert any(r[2] == "csv@test.com" for r in rows)


def test_export_respects_stage_filter(app, client):
    admin_id = _create_admin(app)
    s1 = _create_student(app, "keep@test.com")
    s2 = _create_student(app, "out@test.com")
    a1 = _submit_application(app, s1, stage="submitted")
    _submit_application(app, s2, stage="rejected")
    _login(client, admin_id)
    resp = client.get("/admin/applicants/export.csv?stage=submitted")
    content = resp.data.decode("utf-8")
    assert "keep@test.com" in content
    assert "out@test.com" not in content
