from src.supervisor import clear_stale_pid_lock, run_restart_supervisor
import faulthandler
import sys
import threading
from types import SimpleNamespace


def test_supervisor_restarts_failed_child_with_backoff():
    outcomes=iter([1,0]); stop={'value':False}; calls=[]; delays=[]; events=[]
    def child():
        value=next(outcomes); calls.append(value)
        if len(calls)==2: stop['value']=True
        return value
    result=run_restart_supervisor(child,lambda:stop['value'],lambda level,msg:events.append((level,msg)),
                                  (10,30,60),5,3600,delays.append,lambda:0)
    assert result==0 and calls==[1,0] and delays==[10]
    assert any('Restarting bot after exit code 1' in msg for _,msg in events)


def test_supervisor_does_not_restart_after_stop_command():
    calls=[]; events=[]; stop={'value':False}
    def child(): calls.append('run'); stop['value']=True; return 0
    result=run_restart_supervisor(child,lambda:stop['value'],lambda level,msg:events.append((level,msg)),sleep=lambda _:None)
    assert result==0 and calls==['run']


def test_supervisor_stops_after_restart_limit_and_logs_critical():
    calls=[]; events=[]; now=[0]
    def child(): calls.append('crash'); return 1
    def sleep(seconds): now[0]+=seconds
    result=run_restart_supervisor(child,lambda:False,lambda level,msg:events.append((level,msg)),
                                  (10,30,60),2,3600,sleep,lambda:now[0])
    assert result==1 and len(calls)==3
    assert [level for level,msg in events].count('WARNING')==2
    assert any(level=='CRITICAL' and 'restart limit' in msg for level,msg in events)


def test_supervisor_removes_only_confirmed_dead_bot_lock(tmp_path):
    lock=tmp_path/'bot.lock'; lock.write_text('1234 token',encoding='utf-8')
    assert not clear_stale_pid_lock(lock,lambda pid:True) and lock.exists()
    assert clear_stale_pid_lock(lock,lambda pid:False) and not lock.exists()
    lock.write_text('damaged',encoding='utf-8')
    assert not clear_stale_pid_lock(lock,lambda pid:False) and lock.exists()


def test_crash_handlers_capture_main_and_thread_tracebacks(tmp_path,monkeypatch):
    from scripts import run_bot
    old_sys=sys.excepthook; old_thread=threading.excepthook
    monkeypatch.setattr(run_bot,'ROOT',tmp_path)
    run_bot.install_crash_handlers()
    try:
        try: raise RuntimeError('main crash test')
        except RuntimeError: sys.excepthook(*sys.exc_info())
        try: raise ValueError('thread crash test')
        except ValueError as exc:
            threading.excepthook(SimpleNamespace(exc_type=type(exc),exc_value=exc,exc_traceback=exc.__traceback__,thread=SimpleNamespace(name='test-thread')))
        assert faulthandler.is_enabled()
        text=(tmp_path/'logs'/'crash.log').read_text(encoding='utf-8')
        assert 'main crash test' in text and 'thread crash test' in text and 'Traceback' in text
    finally:
        faulthandler.disable()
        run_bot._crash_file.close()
        sys.excepthook=old_sys; threading.excepthook=old_thread
