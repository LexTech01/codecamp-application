"""Background PDF generation tasks."""
import os
import logging
from celery import current_task
from app.celery_app import celery
from app import create_app

logger = logging.getLogger(__name__)


@celery.task(bind=True, max_retries=2, default_retry_delay=30)
def generate_cohort_pdf(self, cohort_id):
    from flask import render_template
    from weasyprint import HTML
    from datetime import datetime, timezone
    from app.models.cohort import Cohort
    from app.models.application import Application

    app = create_app()
    pdf_dir = app.config.get("PDF_EXPORT_DIR", os.path.join(app.root_path, "static", "exports"))
    os.makedirs(pdf_dir, exist_ok=True)

    with app.app_context():
        cohort = Cohort.query.get_or_404(cohort_id)
        members = Application.query.filter_by(cohort_name=cohort.name).order_by(
            Application.updated_at.desc()
        ).all()
        html = render_template(
            "admin/cohort_pdf.html",
            cohort=cohort,
            members=members,
            today=datetime.now(timezone.utc),
        )
        filename = f"{cohort.name.replace(' ', '_')}_roster.pdf"
        filepath = os.path.join(pdf_dir, filename)
        HTML(string=html).write_pdf(filepath)

        current_task.update_state(state="SUCCESS", meta={"file": filename, "path": filepath})
        logger.info("PDF generated: %s", filepath)
        return {"file": filename, "path": filepath}
