import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.services.crash_service import process_crashes

logger = logging.getLogger("crash-agent")

scheduler = BackgroundScheduler()


def start_scheduler() -> None:
    scheduler.add_job(
        process_crashes,
        "interval",
        minutes=5,
        id="process_crashes",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started: processing crashes every 5 minutes")


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler stopped")
