"""Tac vu nen cua server (chay trong cung tien trinh, khoi dong tu lifespan cua app).

Moi vong lap chi goi mot ham nghiep vu trong services/ - ham do test duoc rieng, khong phu
thuoc vong lap. Moi luot mo mot phien DB rieng (khong co request nen nhat ky ghi la "he thong").

| Tac vu                     | Chu ky                          | Viec                                   |
|----------------------------|---------------------------------|----------------------------------------|
| auto_close_sessions        | 60 giay                         | dong phien qua han, sinh ban ghi vang  |
| cleanup_evidence           | 24 gio (chay ngay khi khoi dong)| xoa anh bang chung qua han luu tru     |
| send_notification_emails   | NOTIFY_EMAIL_INTERVAL_SECONDS   | gui email thong bao phu huynh (SMTP)   |
"""
import asyncio
import logging

from app.core.config import settings
from app.db.database import SessionLocal
from app.services import email_service, evidence_cleanup, parent_notify, session_service

logger = logging.getLogger(__name__)

AUTO_CLOSE_INTERVAL_SECONDS = 60
CLEANUP_INTERVAL_SECONDS = 24 * 3600


async def auto_close_sessions_loop() -> None:
    while True:
        db = SessionLocal()
        try:
            session_service.auto_close_expired_sessions(db)
        except Exception:
            logger.exception("Loi khi tu dong dong phien diem danh")
        finally:
            db.close()
        await asyncio.sleep(AUTO_CLOSE_INTERVAL_SECONDS)


async def cleanup_evidence_loop() -> None:
    while True:
        db = SessionLocal()
        try:
            deleted = evidence_cleanup.cleanup_expired_evidence(db)
            if deleted:
                logger.info("Da xoa %s anh bang chung qua han", deleted)
        except Exception:
            logger.exception("Loi khi don anh bang chung qua han")
        finally:
            db.close()
        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)


async def send_notification_emails_loop() -> None:
    while True:
        try:
            await asyncio.to_thread(parent_notify.send_pending_emails)
        except Exception:
            logger.exception("Loi khi gui email thong bao")
        await asyncio.sleep(settings.NOTIFY_EMAIL_INTERVAL_SECONDS)


def start_background_jobs() -> list[asyncio.Task]:
    """Khoi dong cac tac vu nen; tra ve danh sach task de huy khi tat app."""
    if not settings.BACKGROUND_JOBS_ENABLED:
        return []
    tasks = [asyncio.create_task(cleanup_evidence_loop()),
             asyncio.create_task(auto_close_sessions_loop())]
    if email_service.is_configured():
        tasks.append(asyncio.create_task(send_notification_emails_loop()))
    return tasks


def stop_background_jobs(tasks: list[asyncio.Task]) -> None:
    for task in tasks:
        task.cancel()
