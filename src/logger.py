import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

def get_logger(name):
    logger = logging.getLogger(name)
    if logger.handlers: return logger
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s')
    console = logging.StreamHandler(); console.setFormatter(fmt); logger.addHandler(console)
    path = Path(__file__).resolve().parents[1] / 'logs' / 'bot.log'; path.parent.mkdir(exist_ok=True)
    file = RotatingFileHandler(path,maxBytes=5*1024*1024,backupCount=5,encoding='utf-8'); file.setFormatter(fmt); logger.addHandler(file)
    return logger

def log_warning_event(logger, db, source, message):
    logger.warning(message); db.log_event('WARNING',source,message)
