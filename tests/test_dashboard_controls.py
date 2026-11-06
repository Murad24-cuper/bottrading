from datetime import datetime,timezone
from pathlib import Path

from src.dashboard import app


def test_start_control_launches_detached_virtualenv_and_removes_pause(tmp_path,monkeypatch):
    monkeypatch.setattr(app,'ROOT',tmp_path)
    monkeypatch.setattr(app,'DB_PATH',tmp_path/'data'/'bot.db')
    monkeypatch.setattr(app.queries,'get_bot_status',lambda path:None)
    (tmp_path/'STOP').write_text('PAUSE\n',encoding='utf-8')
    launched=[]
    monkeypatch.setattr(app.subprocess,'Popen',lambda *args,**kwargs:launched.append((args,kwargs)))
    ok,message=app._start_bot()
    assert ok and not (tmp_path/'STOP').exists()
    args,kwargs=launched[0]
    assert Path(args[0][0])==tmp_path/'.venv'/'Scripts'/'python.exe'
    assert 'DETACHED_PROCESS' in dir(app.subprocess) or kwargs['creationflags'] & 0x8
    assert 'CREATE_NEW_PROCESS_GROUP' in dir(app.subprocess) or kwargs['creationflags'] & 0x200
    assert kwargs['cwd']==tmp_path and kwargs['stdout'] is app.subprocess.DEVNULL

def test_start_control_refuses_a_fresh_heartbeat(tmp_path,monkeypatch):
    monkeypatch.setattr(app,'ROOT',tmp_path)
    monkeypatch.setattr(app,'DB_PATH',tmp_path/'data'/'bot.db')
    monkeypatch.setattr(app.queries,'get_bot_status',lambda path:{'time':datetime.now(timezone.utc).isoformat()})
    monkeypatch.setattr(app.subprocess,'Popen',lambda *args,**kwargs:(_ for _ in ()).throw(AssertionError('must not launch')))
    ok,message=app._start_bot()
    assert not ok and 'already appears' in message
