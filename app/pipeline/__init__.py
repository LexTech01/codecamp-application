class PipelineMachine:
    STAGES = [
        "submitted",
        "under_review",
        "test_invited",
        "test_completed",
        "interview_scheduled",
        "interview_completed",
        "accepted",
        "rejected",
        "waitlisted",
        "onboarding",
        "enrolled",
    ]

    TRANSITIONS = {
        "draft": ["submitted"],
        "submitted": ["under_review", "test_invited", "rejected"],
        "under_review": ["test_invited", "rejected", "waitlisted"],
        "test_invited": ["test_completed", "rejected"],
        "test_completed": ["interview_scheduled", "accepted", "rejected"],
        "interview_scheduled": ["interview_completed", "rejected", "no_show"],
        "interview_completed": ["accepted", "rejected", "waitlisted"],
        "rejected": ["waitlisted"],
        "waitlisted": ["test_invited"],
        "accepted": ["onboarding"],
        "onboarding": ["enrolled"],
        "enrolled": ["enrolled"],
    }

    ADMIN_TRANSITIONS = {
        "submitted": ["under_review", "test_invited", "rejected"],
        "under_review": ["test_invited", "rejected", "waitlisted"],
        "test_invited": ["test_completed", "rejected"],
        "test_completed": ["interview_scheduled", "accepted", "rejected", "waitlisted"],
        "interview_scheduled": ["rejected"],
        "interview_completed": ["accepted", "rejected", "waitlisted"],
        "accepted": ["onboarding"],
        "onboarding": ["enrolled"],
        "rejected": ["test_invited"],
        "waitlisted": ["test_invited"],
    }

    KANBAN_MAP = {
        "new": ["submitted"],
        "test": ["test_invited", "test_completed"],
        "interview": ["interview_scheduled", "interview_completed"],
        "accepted": ["accepted", "onboarding", "enrolled"],
        "rejected": ["rejected", "waitlisted"],
    }

    STAGE_PROGRESSION = [
        "submitted",
        "under_review",
        "test_invited",
        "test_completed",
        "interview_scheduled",
        "interview_completed",
        "accepted",
        "onboarding",
        "enrolled",
    ]

    STATUS_LABELS = {
        "draft": "Draft",
        "submitted": "Submitted",
        "under_review": "Under Review",
        "test_invited": "Test Invited",
        "test_completed": "Test Completed",
        "interview_scheduled": "Interview Scheduled",
        "interview_completed": "Interview Completed",
        "accepted": "Accepted",
        "rejected": "Rejected",
        "waitlisted": "Waitlisted",
        "onboarding": "Onboarding",
        "enrolled": "Enrolled",
    }

    PROGRESS_TRACK = [
        "submitted", "test_invited", "test_completed",
        "interview_scheduled", "interview_completed", "accepted",
    ]

    def can_advance(self, current_stage, target_stage):
        return target_stage in self.TRANSITIONS.get(current_stage, [])

    def available_actions(self, stage):
        return self.ADMIN_TRANSITIONS.get(stage, [])

    def check_access(self, current_stage, allowed_stages):
        if current_stage in allowed_stages:
            return True
        if current_stage in self.STAGE_PROGRESSION and any(s in self.STAGE_PROGRESSION for s in allowed_stages):
            current_idx = self.STAGE_PROGRESSION.index(current_stage)
            max_allowed_idx = max(
                self.STAGE_PROGRESSION.index(s) for s in allowed_stages if s in self.STAGE_PROGRESSION
            )
            if current_idx > max_allowed_idx:
                return True
        return False

    def status_label(self, stage):
        return self.STATUS_LABELS.get(stage, stage.replace("_", " ").title())

    def progress_percent(self, stage):
        if stage in ("rejected", "waitlisted", "onboarding", "enrolled"):
            return 100
        try:
            idx = self.PROGRESS_TRACK.index(stage)
            return int((idx + 1) / len(self.PROGRESS_TRACK) * 100)
        except ValueError:
            return 0

    def notify_content(self, from_stage, to_stage):
        title = "Application Update"
        message = f"Your application status is now: {self.status_label(to_stage)}"
        if to_stage == "accepted":
            title = "Application Passed"
            message = "Congratulations, your application has passed. Cohort placement will follow."
        elif to_stage == "rejected":
            title = "Application Rejected"
            message = "Your application was not selected at this time."
        elif to_stage == "waitlisted":
            title = "Application Waitlisted"
            message = "Your application has been waitlisted. We'll notify you when there is an update."
        return title, message

    def stage_for_kanban(self, column):
        mapping = {
            "new": "submitted",
            "review": "under_review",
            "test": "test_invited",
            "interview": "interview_scheduled",
            "accepted": "accepted",
            "rejected": "rejected",
        }
        return mapping.get(column, "submitted")


pipeline = PipelineMachine()
