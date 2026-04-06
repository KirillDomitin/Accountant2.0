import logging
import logging.handlers
from pathlib import Path

LOG_DIR = Path("logs")
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging() -> None:
    LOG_DIR.mkdir(exist_ok=True)

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    # INFO+ → logs/app.log, ротация каждые сутки, хранить 30 дней
    info_handler = logging.handlers.TimedRotatingFileHandler(
        LOG_DIR / "app.log",
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
        utc=True,
    )
    info_handler.setLevel(logging.INFO)
    info_handler.setFormatter(formatter)

    # ERROR+ → logs/error.log, ротация каждые сутки, хранить 90 дней
    error_handler = logging.handlers.TimedRotatingFileHandler(
        LOG_DIR / "error.log",
        when="midnight",
        interval=1,
        backupCount=90,
        encoding="utf-8",
        utc=True,
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)

    # Консоль — INFO+
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(info_handler)
    root_logger.addHandler(error_handler)
    root_logger.addHandler(console_handler)

    # Заглушить шумных либовых логгеров
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
