from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .schemas import ChatRequest, UserActivity, UserStats


class AnalyticsService:
    def __init__(self, data_dir: Path) -> None:
        self.log_path = data_dir / "user_activity.jsonl"
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log_chat(self, request: ChatRequest) -> None:
        activity = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": request.session_id,
            "user_name": request.user_name,
            "user_email": request.user_email,
            "user_phone": request.user_phone,
            "question": request.question,
            "used_documents": request.use_documents,
        }
        with self.log_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(activity, ensure_ascii=True) + "\n")

    def get_stats(self, recent_limit: int = 20) -> UserStats:
        activities = self._read_activities()
        unique_keys = {
            self._user_key(activity)
            for activity in activities
            if self._user_key(activity)
        }
        recent = activities[-recent_limit:]
        return UserStats(
            total_messages=len(activities),
            unique_users=len(unique_keys),
            recent_activity=recent[::-1],
        )

    def _read_activities(self) -> list[UserActivity]:
        if not self.log_path.exists():
            return []

        activities: list[UserActivity] = []
        with self.log_path.open("r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if not line:
                    continue
                try:
                    activities.append(UserActivity.model_validate_json(line))
                except ValueError:
                    continue
        return activities

    def _user_key(self, activity: UserActivity) -> str | None:
        return (
            activity.user_email
            or activity.user_phone
            or activity.session_id
            or activity.user_name
        )
