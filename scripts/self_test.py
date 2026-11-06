"""Run local safety and availability checks; never prints credentials."""
from __future__ import annotations
from pathlib import Path
from datetime import datetime,timezone
import argparse,os,shutil,socket,sqlite3,subprocess,sys,json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.config import load_settings

def main():
    if hasattr(sys.stdout,'reconfigure'): sys.stdout.reconfigure(encoding='utf-8',errors='replace')
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--mt5',action='store_true',help='Check terminal connectivity (avoid while the bot is using MT5).'); args=parser.parse_args()
    settings=load_settings(); root=settings.root; checks=[]
    def check(name,ok,detail): checks.append((name,bool(ok),detail))
    check('DEMO rejimi',settings.config['account']['mode']=='demo','Hesab rejimi DEMO olmalıdır.')
    check('Real hesab qoruması',not settings.allow_real,'ALLOW_REAL aktiv olmamalıdır.')
    check('MT5 parolunun Git qoruması',subprocess.run(['git','check-ignore','-q','.env'],cwd=root,check=False).returncode==0,'.env Git-də izlənməməlidir.')
    free=shutil.disk_usage(root).free/1024**3
    check('Disk sahəsi',free>=5,f'{free:.1f} GB boşdur; xəbərdarlıq həddi 5 GB-dır.')
    required={'trades','signals','daily_stats','equity_snapshots','bot_events','commands','maintenance_runs'}
    try:
        with sqlite3.connect(settings.db_path) as connection: present={row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        check('SQLite sxemi',required.issubset(present),'SQLite cədvəlləri mövcuddur.' if required.issubset(present) else 'Bəzi tələb olunan cədvəllər yoxdur.')
    except sqlite3.Error as exc: check('SQLite sxemi',False,f'Database açılmadı: {exc}')
    try:
        with sqlite3.connect(settings.db_path) as connection:
            connection.row_factory=sqlite3.Row; row=connection.execute('SELECT time,status,account_type,mt5_connected,trade_allowed FROM bot_status WHERE id=1').fetchone()
        age=(datetime.now(timezone.utc)-datetime.fromisoformat(row['time'].replace('Z','+00:00')).astimezone(timezone.utc)).total_seconds() if row else float('inf')
        check('DEMO heartbeat',bool(row and row['account_type']=='DEMO' and row['status']=='running' and age<=90),f"Son heartbeat {age:.0f} san əvvəl; hesab DEMO olmalıdır.")
        check('MT5 icazələri',bool(row and row['mt5_connected'] and row['trade_allowed']),'MT5 bağlantısı və algo trading icazəsi aktiv olmalıdır.')
    except (sqlite3.Error,ValueError,TypeError) as exc: check('DEMO heartbeat',False,f'Status oxunmadı: {exc}')
    check('STOP faylı',not (root/'STOP').exists(),'STOP faylı olmamalıdır.')
    try: gate=json.loads((settings.data_dir/'brain'/'gate.json').read_text(encoding='utf-8'))
    except (OSError,ValueError): gate={}
    check('Beyin təhlükəsiz rejimi',not settings.config.get('brain',{}).get('enabled',False) or gate.get('status')=='PASS','Qəbul yoxlamasından keçməyən beyin müşahidə rejimində qalmalıdır.')
    try:
        with socket.create_connection(('127.0.0.1',8501),timeout=2): dashboard=True
    except OSError: dashboard=False
    check('Panel',dashboard,'Panel 127.0.0.1:8501 ünvanında dinləməlidir.')
    if args.mt5:
        from src.mt5_client import MT5Client
        try:
            with MT5Client(settings) as client:
                account=client.mt5.account_info(); terminal=client.mt5.terminal_info()
                demo=account is not None and account.trade_mode==client.mt5.ACCOUNT_TRADE_MODE_DEMO
                check('MT5 demo hesabı',demo,'MT5 hesabı DEMO olmalıdır.')
                check('MT5 algo trading',bool(terminal and terminal.trade_allowed),'Terminal alqoritmik ticarətə icazə verməlidir.')
        except Exception as exc: check('MT5 bağlantısı',False,f'MT5 bağlantısı alınmadı: {exc}')
    for name,passed,detail in checks: print(f"{'🟢' if passed else '🔴'} {name}: {detail}")
    return 0 if all(ok for _,ok,_ in checks) else 1

if __name__=='__main__': raise SystemExit(main())
