from datetime import datetime, timezone
from src.notify import TelegramNotifier
def test_telegram_rate_limit_and_retry_without_logging_secrets():
    calls=[]
    class Response: status_code=200
    def post(url, **kwargs):
        calls.append((url,kwargs)); return Response()
    clock=[datetime(2026,11,6,tzinfo=timezone.utc)]
    notifier=TelegramNotifier('secret-token','123456',5,post,lambda:clock[0])
    assert notifier.send('mt5','Xəta yoxdur')
    assert not notifier.send('mt5','təkrar')
    notifier._deliver('sınaq')
    assert calls and calls[-1][1]['timeout']==5
    assert 'secret-token' in calls[-1][0]
    notifier.enabled=False
    assert notifier.send('disabled','gizli') is False

def test_telegram_retries_once_after_http_error():
    calls=[]
    class Response:
        def __init__(self,status): self.status_code=status
    def post(url,**kwargs):
        calls.append(url); return Response(500 if len(calls)==1 else 200)
    notifier=TelegramNotifier('token','chat',post=post)
    notifier._deliver('test')
    assert len(calls)==2

def test_telegram_error_description_is_available_without_echoing_credentials():
    class Response:
        status_code=400
        def json(self): return {'description':'Bad Request: chat not found'}
    notifier=TelegramNotifier('secret-token','private-chat-id',post=lambda *a,**k:Response())
    assert not notifier._deliver('test')
    assert notifier.last_http_status==400
    assert notifier.last_error_description=='Bad Request: chat not found'
    assert 'secret-token' not in notifier.last_error_description
    assert 'private-chat-id' not in notifier.last_error_description
