from datetime import datetime,timezone
from pathlib import Path

from src.dashboard import app


def test_start_control_launches_detached_supervisor_and_logs_output(tmp_path,monkeypatch):
    monkeypatch.setattr(app,'ROOT',tmp_path)
    monkeypatch.setattr(app,'DATA_DIR',tmp_path/'data')
    monkeypatch.setattr(app,'LOG_DIR',tmp_path/'logs')
    monkeypatch.setattr(app,'DB_PATH',tmp_path/'data'/'bot.db')
    monkeypatch.setattr(app.queries,'get_bot_status',lambda path:None)
    (tmp_path/'STOP').write_text('PAUSE\n',encoding='utf-8')
    (tmp_path/'data').mkdir(parents=True,exist_ok=True)
    (tmp_path/'data'/'supervisor.stop').write_text('stale marker\n',encoding='utf-8')
    launched=[]
    monkeypatch.setattr(app.subprocess,'Popen',lambda *args,**kwargs:launched.append((args,kwargs)))
    ok,message=app._start_bot()
    assert ok and not (tmp_path/'STOP').exists()
    args,kwargs=launched[0]
    assert Path(args[0][0])==tmp_path/'.venv'/'Scripts'/'pythonw.exe'
    assert Path(args[0][1])==tmp_path/'scripts'/'run_forever.py'
    assert 'DETACHED_PROCESS' in dir(app.subprocess) or kwargs['creationflags'] & 0x8
    assert 'CREATE_NEW_PROCESS_GROUP' in dir(app.subprocess) or kwargs['creationflags'] & 0x200
    assert kwargs['cwd']==tmp_path and kwargs['stdout'].name==str(tmp_path/'logs'/'bot_stdout.log')
    assert kwargs['stderr'] is app.subprocess.STDOUT
    if hasattr(app.subprocess,'CREATE_BREAKAWAY_FROM_JOB'):
        assert kwargs['creationflags'] & app.subprocess.CREATE_BREAKAWAY_FROM_JOB
    assert not (tmp_path/'data'/'supervisor.stop').exists()

def test_start_control_refuses_a_fresh_heartbeat(tmp_path,monkeypatch):
    monkeypatch.setattr(app,'ROOT',tmp_path)
    monkeypatch.setattr(app,'DB_PATH',tmp_path/'data'/'bot.db')
    monkeypatch.setattr(app.queries,'get_bot_status',lambda path:{'time':datetime.now(timezone.utc).isoformat()})
    monkeypatch.setattr(app.subprocess,'Popen',lambda *args,**kwargs:(_ for _ in ()).throw(AssertionError('must not launch')))
    ok,message=app._start_bot()
    assert not ok and 'already appears' in message

def test_start_control_falls_back_when_breakaway_from_job_is_denied(tmp_path,monkeypatch):
    monkeypatch.setattr(app,'ROOT',tmp_path)
    monkeypatch.setattr(app,'DATA_DIR',tmp_path/'data')
    monkeypatch.setattr(app,'LOG_DIR',tmp_path/'logs')
    monkeypatch.setattr(app,'DB_PATH',tmp_path/'data'/'bot.db')
    monkeypatch.setattr(app.queries,'get_bot_status',lambda path:None)
    calls=[]
    def popen(*args,**kwargs):
        calls.append(kwargs['creationflags'])
        if len(calls)==1: raise OSError('breakaway not permitted')
        return object()
    monkeypatch.setattr(app.subprocess,'Popen',popen)
    ok,_=app._start_bot()
    assert ok and len(calls)==2
    assert calls[0] & 0x01000000
    assert not calls[1] & 0x01000000
