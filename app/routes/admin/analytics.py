"""Analytics and pipeline view routes."""
from flask import render_template
from flask_login import login_required, current_user
from sqlalchemy import func
from app import db
from app.models.application import Application
from app.pipeline import pipeline as pipeline_machine
from app.models.assessment import TestAttempt
from app.routes.admin import admin_bp
from app.utils.decorators import admin_required


@admin_bp.route("/pipeline")
@login_required
@admin_required
def pipeline():
    apps = Application.query.filter_by(is_submitted=True).all()
    columns = {k: [] for k in pipeline_machine.KANBAN_MAP}
    for app in apps:
        for col, stages in pipeline_machine.KANBAN_MAP.items():
            if app.pipeline_stage in stages:
                columns[col].append(app)
                break
    return render_template("admin/pipeline.html", columns=columns, kanban_keys=list(pipeline_machine.KANBAN_MAP.keys()))


@admin_bp.route("/analytics")
@login_required
@admin_required
def analytics():
    total = Application.query.filter_by(is_submitted=True).count()

    # Single GROUP BY query replacing 13 individual COUNT queries
    stage_counts = dict(
        db.session.query(
            Application.pipeline_stage,
            func.count(Application.id)
        ).filter(
            Application.is_submitted == True
        ).group_by(
            Application.pipeline_stage
        ).all()
    )
    stages = {s: stage_counts.get(s, 0) for s in pipeline_machine.STAGES}

    # Single query for all completed attempt scores
    score_rows = (
        db.session.query(TestAttempt.score)
        .filter(TestAttempt.completed_at.isnot(None))
        .all()
    )
    scores = [r[0] for r in score_rows if r[0] is not None]
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
            "attempts": len(scores),
            "score_buckets": score_buckets,
        },
    )