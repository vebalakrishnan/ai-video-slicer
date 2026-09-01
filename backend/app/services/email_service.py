"""Email notification service (Module 6).

Sends completion/failure emails via plain smtplib. SMTP errors are always
logged and swallowed - never raised - so a notification failure can never
fail the surrounding Celery pipeline (see CLAUDE.md and TASKS.md item 6).
"""
import logging
import smtplib
from email.message import EmailMessage
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from app.models.video_job import VideoJob

logger = logging.getLogger(__name__)


class SMTPSettings(Protocol):
    """Structural type for the subset of Settings this module reads.

    Matches app.config.Settings' SMTP_* fields - kept as a Protocol
    (rather than importing Settings directly) so tests can pass a
    lightweight stand-in object instead of the real settings singleton.
    """

    SMTP_HOST: str
    SMTP_PORT: str
    SMTP_USER: str
    SMTP_PASSWORD: str


def _send_email(smtp_settings: SMTPSettings, to_email: str, subject: str, body: str) -> None:
    """Build and send a single plain-text email. Logs and swallows any error."""
    if not smtp_settings.SMTP_HOST:
        logger.info("SMTP_HOST not configured - skipping email to %s (%s)", to_email, subject)
        return

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = smtp_settings.SMTP_USER or "noreply@aivideoslicer.local"
    message["To"] = to_email
    message.set_content(body)

    try:
        port = int(smtp_settings.SMTP_PORT or "587")
        with smtplib.SMTP(smtp_settings.SMTP_HOST, port, timeout=15) as server:
            server.starttls()
            if smtp_settings.SMTP_USER and smtp_settings.SMTP_PASSWORD:
                server.login(smtp_settings.SMTP_USER, smtp_settings.SMTP_PASSWORD)
            server.send_message(message)
        logger.info("Sent email to %s: %s", to_email, subject)
    except (smtplib.SMTPException, OSError, ValueError) as exc:
        logger.warning("Failed to send email to %s (%s): %s", to_email, subject, exc)


def send_completion_email(
    to_email: str, video_job: "VideoJob", smtp_settings: SMTPSettings
) -> None:
    """Notify the user that their shorts finished processing (completed/partial)."""
    status = getattr(video_job.status, "value", video_job.status)
    if status == "partial":
        subject = f"Your shorts are ready (partial) - \"{video_job.title or 'Untitled video'}\""
        body = (
            f"Processing finished for \"{video_job.title or 'your video'}\", but only a "
            "limited number of strong short clips were found.\n\n"
            "Details: "
            f"{video_job.error_message or 'Fewer than 5 sufficiently strong segments were found.'}"
            "\n\n"
            "Sign in to AI Video Slicer to review the available results."
        )
    else:
        subject = f"Your shorts are ready - \"{video_job.title or 'Untitled video'}\""
        body = (
            f"Your shorts for \"{video_job.title or 'your video'}\" have finished processing "
            "and are ready to view/download.\n\n"
            "Sign in to AI Video Slicer to review and download your clips."
        )
    _send_email(smtp_settings, to_email, subject, body)


def send_failure_email(to_email: str, video_job: "VideoJob", smtp_settings: SMTPSettings) -> None:
    """Notify the user that processing failed."""
    subject = f"Processing failed - \"{video_job.title or 'Untitled video'}\""
    body = (
        f"We were unable to process \"{video_job.title or 'your video'}\".\n\n"
        f"Reason: {video_job.error_message or 'An unexpected error occurred.'}\n\n"
        "Please try submitting the video again, or contact support if the problem persists."
    )
    _send_email(smtp_settings, to_email, subject, body)
