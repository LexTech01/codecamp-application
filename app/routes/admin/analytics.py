"""Analytics and pipeline view routes."""
from flask import render_template
from flask_login import login_required, current_user
from app import db
from app.models.application import Application
from app.pipeline import pipeline
from app.models.assessment import TestAttempt
from app.routes.admin import admin_bp
from app.utils.decorators import admin_required


@admin_bp.route("/pipeline")
@login_required
@admin_required
def pipeline():
    apps = Application.query.filter_by(is_submitted=True).all()
    columns = {k: [] for k in pipeline.KANBAN_MAP}
    for app in apps:
        for col, stages in pipeline.KANBAN_MAP.items():
            if app.pipeline_stage in stages:
                columns[col].append(app)
                break
    return render_template("admin/pipeline.html", columns=columns, kanban_keys=list(pipeline.KANBAN_MAP.keys()))


@admin_bp.route("/analytics")
@login_required
@admin_required
def analytics():
    total = Application.query.filter_by(is_submitted=True).count()
    stages = {}
    for stage in pipeline.STAGES:
        stages[stage] = Application.query.filter_by(pipeline_stage=stage, is_submitted=True).count()
    attempts = TestAttempt.query.filter(TestAttempt.completed_at.isnot(None)).all()
    scores = [a.score for a in attempts if a.score is not None]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0
    score_buckets = [
        sum(1 for s in scores if 0 <= s < 20),
        sum(1 for s in scores if 20 <= s < 40),
        sum(1 for s in scores if 40 <= s < 60),
        sum(1 for s in scores if 60 <= s < 80),
        sum(1 for s in scores if 80 <= s <= 100),
    ]
    return render_template(
        "admin/analytics.html",
        stats={
            "total": total,
            "stages": stages,
            "avg_score": avg_score,
            "attempts": len(attempts),
            "score_buckets": score_buckets,
        },
    )
