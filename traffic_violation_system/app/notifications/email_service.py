"""Email notification service (non-blocking via worker queue)."""

from __future__ import annotations

import smtplib
from email.message import EmailMessage
from pathlib import Path

from app.config.settings import get_settings
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class EmailNotificationService:
    def __init__(self) -> None:
        self.settings = get_settings()

    @property
    def is_configured(self) -> bool:
        return bool(
            self.settings.notification_enabled
            and self.settings.smtp_host
            and self.settings.smtp_from
        )

    def send_violation_email(
        self,
        *,
        recipient: str,
        violation_title: str,
        violation_id: int,
        date_str: str,
        time_str: str,
        location: str,
        vehicle_number: str | None,
        image_path: str | None,
    ) -> None:
        if not self.is_configured:
            logger.info("Email notification skipped (SMTP not configured).")
            return

        message = EmailMessage()
        message["Subject"] = f"Traffic Violation Report #{violation_id}"
        message["From"] = self.settings.smtp_from
        message["To"] = recipient
        message.set_content(
            "\n".join(
                [
                    f"Violation Title: {violation_title}",
                    f"Date: {date_str}",
                    f"Time: {time_str}",
                    f"Location: {location}",
                    f"Vehicle Number: {vehicle_number or 'Unknown'}",
                    f"Violation ID: {violation_id}",
                ]
            )
        )

        if image_path and Path(image_path).exists():
            image_bytes = Path(image_path).read_bytes()
            message.add_attachment(
                image_bytes,
                maintype="image",
                subtype="jpeg",
                filename=Path(image_path).name,
            )

        with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port, timeout=30) as smtp:
            if self.settings.smtp_use_tls:
                smtp.starttls()
            if self.settings.smtp_user and self.settings.smtp_password:
                smtp.login(self.settings.smtp_user, self.settings.smtp_password)
            smtp.send_message(message)

        logger.info("Violation email sent for violation_id=%s", violation_id)
