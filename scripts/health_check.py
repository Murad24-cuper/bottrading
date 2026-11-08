"""Read-only one-screen status check using the last persisted MT5 heartbeat."""
from pathlib import Path
from datetime import datetime,timezone
import os,sqlite3,sys,yaml

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.paths import project_paths
from src.process_utils import pid_is_running
from src.dashboard.presentation import translate_message

def pid_running(pid):
    return pid_is_running(pid)

def read_pid(path):
    try: return int(Path(path).read_text(encoding='utf-8').split()[0])
    except (OSError,ValueError,IndexError): return None

def main():
    config=yaml.safe_load((ROOT/'config.yaml').read_text(encoding='utf-8'))
    data_dir,_=project_paths(ROOT)
    db_path=Path(os.getenv('BOT_DB_PATH') or config['db_path']); db_path=db_path if db_path.is_absolute() else ROOT/db_path
    try:
        connection=sqlite3.connect(db_path.as_uri()+'?mode=ro',uri=True,timeout=3); connection.row_factory=sqlite3.Row
        status=connection.execute('SELECT * FROM bot_status WHERE id=1').fetchone()
        latest=connection.execute('SELECT balance,equity FROM equity_snapshots ORDER BY time DESC LIMIT 1').fetchone()
        today=datetime.now(timezone.utc).date().isoformat()
        pnl=connection.execute("SELECT COALESCE(SUM(COALESCE(profit,0)+COALESCE(commission,0)+COALESCE(swap,0)),0) FROM trades WHERE status='closed' AND substr(close_time,1,10)=?",(today,)).fetchone()[0]
        pnl+=connection.execute("SELECT COALESCE(SUM(COALESCE(profit,0)+COALESCE(commission,0)+COALESCE(swap,0)),0) FROM partial_closes WHERE substr(time,1,10)=?",(today,)).fetchone()[0]
        open_count=connection.execute("SELECT COUNT(*) FROM trades WHERE status='open'").fetchone()[0]
        scan_rows=connection.execute("SELECT scan_total,scan_scanned,scan_top_n,scan_signals FROM bot_status WHERE id=1").fetchone()
        events=connection.execute("SELECT time,level,source,message FROM bot_events WHERE level IN ('WARNING','ERROR','CRITICAL') ORDER BY time DESC LIMIT 5").fetchall()
        connection.close()
    except (sqlite3.Error,OSError) as exc:
        print(f'DB: əlçatan deyil ({exc})'); return 1
    now=datetime.now(timezone.utc)
    heartbeat=None
    if status and status['time']:
        stamp=datetime.fromisoformat(status['time'].replace('Z','+00:00'))
        if stamp.tzinfo is None: stamp=stamp.replace(tzinfo=timezone.utc)
        heartbeat=(now-stamp.astimezone(timezone.utc)).total_seconds()
    supervisor=pid_running(read_pid(data_dir/'supervisor.pid'))
    bot=pid_running(read_pid(data_dir/'bot.lock'))
    columns=set(status.keys()) if status else set()
    connected=bool(status and status['mt5_connected'])
    trade_allowed=bool(status and status['trade_allowed']) if 'trade_allowed' in columns else False
    demo=bool(status and str(status['account_type']).upper()=='DEMO')
    fresh=heartbeat is not None and heartbeat<=60
    healthy=bot and supervisor and connected and trade_allowed and demo and fresh
    scan=dict(scan_rows) if scan_rows else {}
    print('=== Bot sağlamlıq yoxlaması ===')
    print(f'MT5 bağlantısı: {"Bəli" if connected else "Xeyr"} · avtomatik ticarət: {"icazəli" if trade_allowed else "bağlı"}')
    print(f'Hesab növü: {status["account_type"] if status else "Məlumat yoxdur"}')
    print(f'Bot işləyir: {"Bəli" if bot else "Xeyr"} · nəzarətçi: {"Bəli" if supervisor else "Xeyr"}')
    print(f'Balans: {float(latest["balance"]):.2f} $ · kapital: {float(latest["equity"]):.2f} $' if latest else 'Balans/kapital: Məlumat yoxdur')
    print(f'Ürək döyüntüsü: {heartbeat:.0f} san əvvəl' if heartbeat is not None else 'Ürək döyüntüsü: Məlumat yoxdur')
    print(f'Skan: cəmi {scan.get("scan_total",0)} · yoxlanıb {scan.get("scan_scanned",0)} · təhlil {scan.get("scan_top_n",0)} · siqnal {scan.get("scan_signals",0)}')
    print(f'Açıq mövqelər: {open_count} · bugünkü bağlı P/L: {float(pnl or 0):+.2f} $')
    print('Son WARNING+ hadisələri:')
    for event in events: print(f'  {event["time"]} · {event["level"]} · {event["source"]} · {translate_message(event["message"])}')
    if not events: print('  Yoxdur')
    print('Nəticə: sağlamdır' if healthy else 'Nəticə: yoxlama tələb olunur')
    return 0 if healthy else 1

if __name__=='__main__': raise SystemExit(main())
