"""Non-blocking, rate-limited Telegram notifications."""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from queue import Queue, Empty
from threading import Thread, Lock
import os


class TelegramNotifier:
    def __init__(self, token=None, chat_id=None, rate_limit_minutes=5, post=None, clock=None):
        self.token=(token if token is not None else os.getenv('TELEGRAM_BOT_TOKEN','')).strip()
        self.chat_id=(chat_id if chat_id is not None else os.getenv('TELEGRAM_CHAT_ID','')).strip()
        self.enabled=bool(self.token and self.chat_id)
        self.rate_limit=timedelta(minutes=int(rate_limit_minutes))
        self.post=post
        self.clock=clock or (lambda:datetime.now(timezone.utc))
        self.queue=Queue(); self._last={}; self._lock=Lock(); self._thread=None
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
            try: self._deliver(message)
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
                if getattr(response,'status_code',200)<400: return
            except Exception:
                continue

