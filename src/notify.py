"""Non-blocking, rate-limited Telegram notifications."""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from queue import Queue, Empty
from threading import Thread, Lock
import os
import logging


class TelegramNotifier:
    def __init__(self, token=None, chat_id=None, rate_limit_minutes=5, post=None, clock=None):
        self.token=(token if token is not None else os.getenv('TELEGRAM_BOT_TOKEN','')).strip()
        self.chat_id=(chat_id if chat_id is not None else os.getenv('TELEGRAM_CHAT_ID','')).strip()
        self.enabled=bool(self.token and self.chat_id)
        self.rate_limit=timedelta(minutes=int(rate_limit_minutes))
        self.post=post
        self.clock=clock or (lambda:datetime.now(timezone.utc))
        self.queue=Queue(); self._last={}; self._lock=Lock(); self._thread=None
        self.failures=0; self.last_http_status=None; self.last_error_description=None
        if self.enabled:
            self._thread=Thread(target=self._worker,name='telegram-notifier',daemon=True); self._thread.start()

    def send(self,event_type,text):
        if not self.enabled: return False
        now=self.clock()
        with self._lock:
            last=self._last.get(str(event_type))
            if event_type!='daily_summary' and last and now-last<self.rate_limit: return False
            self._last[str(event_type)]=now
        self.queue.put(str(text)[:4000]); return True

    def _worker(self):
        while True:
            try: message=self.queue.get(timeout=1)
            except Empty: continue
            try:
                if not self._deliver(message):
                    self.failures+=1
                    logging.getLogger('bot.notify').warning('Telegram bildirişi iki cəhddən sonra göndərilmədi')
            finally: self.queue.task_done()

    def _deliver(self,message):
        post=self.post
        if post is None:
            try:
                import requests
                post=requests.post
            except ImportError: return
        url=f'https://api.telegram.org/bot{self.token}/sendMessage'
        for _ in range(2):
            try:
                response=post(url,json={'chat_id':self.chat_id,'text':message},timeout=5)
                self.last_http_status=int(getattr(response,'status_code',200))
                if self.last_http_status<400: return True
                try: self.last_error_description=str(response.json().get('description') or 'Telegram returned an error')
                except Exception: self.last_error_description='Telegram returned an error without a readable description'
            except Exception as exc:
                self.last_error_description=f'{type(exc).__name__}: network/API request failed'
                continue
        return False

    def flush(self):
        """Wait for queued notifications during an orderly process shutdown."""
        if self.enabled: self.queue.join()


class TelegramCommandPoller:
    """Accept allowlisted Telegram commands and route them through SQLite."""
    COMMANDS={'/status':'status','/today':'today','/positions':'positions','/pause':'pause','/resume':'resume','/stop':'stop','/health':'health'}
    def __init__(self,db,token=None,chat_id=None,ttl_seconds=60,get=None,post=None,clock=None):
        self.db=db; self.token=(token if token is not None else os.getenv('TELEGRAM_BOT_TOKEN','')).strip()
        self.chat_id=(chat_id if chat_id is not None else os.getenv('TELEGRAM_CHAT_ID','')).strip()
        self.enabled=bool(self.token and self.chat_id); self.ttl_seconds=int(ttl_seconds); self.get=get; self.post=post
        self.clock=clock or __import__('time').sleep; self.offset=0; self._stop=__import__('threading').Event(); self._thread=None
    def _requests(self):
        import requests
        return requests.get,requests.post
    def _send(self,text):
        get,post=self._requests() if self.post is None else (None,self.post)
        response=post(f'https://api.telegram.org/bot{self.token}/sendMessage',json={'chat_id':self.chat_id,'text':text[:4000]},timeout=5)
        return int(getattr(response,'status_code',200))<400
    def poll_once(self):
        """Poll and enqueue each new authorized command once; return accepted count."""
        if not self.enabled: return 0
        if self.get is None: get,_=self._requests()
        else: get=self.get
        response=get(f'https://api.telegram.org/bot{self.token}/getUpdates',params={'offset':self.offset,'timeout':0,'allowed_updates':['message']},timeout=5)
        if int(getattr(response,'status_code',200))>=400: return 0
        payload=response.json(); accepted=0
        if not payload.get('ok'): return 0
        for update in payload.get('result',[]):
            update_id=int(update.get('update_id',-1)); self.offset=max(self.offset,update_id+1)
            message=update.get('message') or {}; chat=str((message.get('chat') or {}).get('id',''))
            text=str(message.get('text') or '').strip().split()
            if update_id<0 or not self.db.record_telegram_update(update_id): continue
            if chat!=self.chat_id or not text: continue
            command=text[0].split('@',1)[0].lower()
            action=self.COMMANDS.get(command)
            if command=='/closeall':
                action='close_all' if len(text)==2 and text[1].upper()=='YES' else None
                reply='Bütün mövqeləri bağlamaq üçün /closeall YES göndərin.' if action is None else 'Bütün mövqeləri bağlama əmri növbəyə əlavə edildi.'
            elif action: reply='Komanda təhlükəsiz icra növbəsinə əlavə edildi.'
            else: reply='Naməlum komanda. Dəstəklənənlər: /status /today /positions /pause /resume /stop /closeall /health.'
            if action:
                try: self.db.insert_command(action,self.ttl_seconds); accepted+=1
                except ValueError: reply='Eyni komanda artıq növbədədir və ya icra olunur.'
            self._send(reply)
        return accepted
    def start(self):
        if not self.enabled or self._thread and self._thread.is_alive(): return
        import threading
        self._stop.clear(); self._thread=threading.Thread(target=self._run,name='telegram-command-poller',daemon=True); self._thread.start()
    def _run(self):
        import logging
        logger=logging.getLogger('bot.telegram_commands')
        while not self._stop.is_set():
            try: self.poll_once()
            except Exception as exc: logger.warning('Telegram command polling failed: %s',type(exc).__name__)
            self.clock(2.0)
    def stop(self):
        self._stop.set()
        if self._thread and self._thread is not __import__('threading').current_thread(): self._thread.join(timeout=6)

