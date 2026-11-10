from datetime import datetime,timezone
from pathlib import Path
import yaml
from src.paths import project_paths
from src.db import Database


def test_project_data_and_log_directories_use_config_or_environment(tmp_path,monkeypatch):
    monkeypatch.delenv('BOT_DATA_DIR',raising=False); monkeypatch.delenv('BOT_LOG_DIR',raising=False)
    (tmp_path/'config.yaml').write_text(yaml.safe_dump({'paths':{'data_dir':'store','logs_dir':'runtime'}}),encoding='utf-8')
    assert project_paths(tmp_path)==(tmp_path/'store',tmp_path/'runtime')
    monkeypatch.setenv('BOT_DATA_DIR','custom-data')
    monkeypatch.setenv('BOT_LOG_DIR','custom-logs')
    assert project_paths(tmp_path)==(tmp_path/'custom-data',tmp_path/'custom-logs')


def test_health_check_reads_database_without_mt5_connection(tmp_path,monkeypatch,capsys):
    from scripts import health_check
    config={'db_path':'data/bot.db','paths':{'data_dir':'data','logs_dir':'logs'}}
    (tmp_path/'config.yaml').write_text(yaml.safe_dump(config),encoding='utf-8')
    monkeypatch.setattr(health_check,'ROOT',tmp_path)
    (tmp_path/'data').mkdir()
    (tmp_path/'data'/'bot.lock').write_text(f'{__import__("os").getpid()} lock',encoding='utf-8')
    (tmp_path/'data'/'supervisor.pid').write_text(str(__import__('os').getpid()),encoding='utf-8')
    db=Database(tmp_path/'data'/'bot.db')
    now=datetime.now(timezone.utc).isoformat()
    db.upsert_bot_status(time=now,cycle=1,mode='trade',status='running',account_type='DEMO',equity=100,last_error='',mt5_connected=1,trade_allowed=1,scan_total=20,scan_scanned=20,scan_top_n=10,scan_signals=2)
    db.insert_equity_snapshot(time=now,balance=100,equity=100,margin=0,free_margin=100,open_positions=0)
    assert health_check.main()==0
    output=capsys.readouterr().out
    assert 'MT5 bağlantısı: Bəli' in output and 'Balans: 100.00 $' in output
    assert 'MT5' not in output.splitlines()[0]

def test_health_check_configures_utf8_output_for_windows_console():
    from scripts.health_check import configure_console_encoding
    class Console:
        def __init__(self): self.options=None
        def reconfigure(self,**options): self.options=options
    console=Console()
    configure_console_encoding(console)
    assert console.options=={'encoding':'utf-8','errors':'replace'}
