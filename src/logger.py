import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from .paths import project_paths

def get_logger(name):
    logger = logging.getLogger(name)
    if logger.handlers: return logger
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s')
    console = logging.StreamHandler(); console.setFormatter(fmt); logger.addHandler(console)
    root=Path(__file__).resolve().parents[1]; path=project_paths(root)[1] / 'bot.log'; path.parent.mkdir(parents=True,exist_ok=True)
    file = RotatingFileHandler(path,maxBytes=5*1024*1024,backupCount=5,encoding='utf-8'); file.setFormatter(fmt); logger.addHandler(file)
    return logger

def log_warning_event(logger, db, source, message, level='WARNING'):
    """Write a warning or error to both the normal logger and bot_events."""
    value=logging._nameToLevel.get(str(level).upper(),logging.WARNING)
    if value < logging.WARNING: value=logging.WARNING
    logger.log(value,message)
    db.log_event(logging.getLevelName(value),source,message)
