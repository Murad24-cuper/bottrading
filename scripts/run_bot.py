"""Run the configured live/shadow loop. No order is sent in shadow mode."""
from pathlib import Path
import faulthandler
import logging
import sys
import threading
import traceback
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.config import load_settings
from src.bot import TradingBot
from src.db import Database
from src.notify import TelegramNotifier
from src.paths import project_paths

ROOT=Path(__file__).resolve().parents[1]
_crash_file=None


def install_crash_handlers():
    """Persist fatal Python and thread tracebacks for detached launches."""
    global _crash_file
    _,log_dir=project_paths(ROOT); log_dir.mkdir(parents=True,exist_ok=True)
    _crash_file=(log_dir/'crash.log').open('a',encoding='utf-8',buffering=1)
    faulthandler.enable(file=_crash_file,all_threads=True)
    old_sys_hook=sys.excepthook
    def handle_exception(exc_type,exc_value,exc_traceback):
        if exc_type is SystemExit: return old_sys_hook(exc_type,exc_value,exc_traceback)
        logging.getLogger('bot.crash').critical('Uncaught main-thread exception',exc_info=(exc_type,exc_value,exc_traceback))
        _crash_file.write(f'Uncaught main-thread exception: {exc_type.__name__}: {exc_value}\n')
        traceback.print_exception(exc_type,exc_value,exc_traceback,file=_crash_file)
        TelegramNotifier().send('crash',f'💥 Botda gözlənilməz xəta baş verdi: {exc_type.__name__}: {exc_value}')
        return old_sys_hook(exc_type,exc_value,exc_traceback)
    sys.excepthook=handle_exception
    def handle_thread_exception(args):
        logging.getLogger('bot.crash').critical('Uncaught thread exception',exc_info=(args.exc_type,args.exc_value,args.exc_traceback))
        _crash_file.write(f'Uncaught thread exception in {args.thread.name}: {args.exc_type.__name__}: {args.exc_value}\n')
        traceback.print_exception(args.exc_type,args.exc_value,args.exc_traceback,file=_crash_file)
        TelegramNotifier().send('crash',f'💥 Bot axınında gözlənilməz xəta: {args.exc_type.__name__}: {args.exc_value}')
    threading.excepthook=handle_thread_exception


def log_exit(db,reason,level='INFO'):
    """Record an explicit process exit reason without including credentials."""
    message=f'bot exiting reason={reason}'
    logging.getLogger('bot.crash').log(getattr(logging,level.upper(),logging.INFO),message)
    if db is not None:
        try: db.log_event(level,'bot',message)
        except Exception: logging.getLogger('bot.crash').exception('Could not save bot exit event')

def main():
    install_crash_handlers()
    db=None; bot=None; reason='startup failed'; result=1
    try:
        settings=load_settings()
        db=Database(settings.db_path)
        bot=TradingBot(settings,db=db)
        bot.run_forever()
        reason=bot.exit_reason or 'run loop returned'
        result=1 if reason=='error limit reached' else 0
        return result
    except BaseException as exc:
        reason=f'uncaught {type(exc).__name__}: {exc}'
        log_exit(db,reason,'CRITICAL')
        raise
    finally:
        if bot is None: log_exit(db,reason,'INFO' if result==0 else 'ERROR')

if __name__=='__main__':
    if sys.stdout is None or sys.stderr is None:
        _,log_dir=project_paths(ROOT); detached_log=log_dir/'bot_stdout.log'; detached_log.parent.mkdir(parents=True,exist_ok=True)
        stream=detached_log.open('a',encoding='utf-8',buffering=1); sys.stdout=stream; sys.stderr=stream
    raise SystemExit(main())
