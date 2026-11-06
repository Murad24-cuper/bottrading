"""Small-account sizing simulation using cached broker symbol specifications."""
from __future__ import annotations
from .queries import get_performance_report, get_supervisor_restart_count, _rows
from ..risk import calc_volume


def readiness_checks(start_utc,end_utc,path=None):
    report=get_performance_report(start_utc,end_utc,path)['overall']
    restarts=get_supervisor_restart_count(start_utc,end_utc,path)
    critical=_rows(path,"SELECT COUNT(*) AS n FROM bot_events WHERE level='CRITICAL' AND time>=? AND time<?",(start_utc,end_utc))
    no_critical=int(critical[0]['n'])==0 if critical else True
    return [
        ('Ən azı 100 bağlanmış əməliyyat',report['trades']>=100),
        ('Xərclərdən sonrakı gözlənilən nəticə müsbətdir',report['expectancy']>0),
        ('Orta qazanc orta zərərdən az deyil',report['average_win']>=report['average_loss']),
        ('Maksimum azalma 10%-dən aşağıdır',report['equity_samples']>0 and report['max_drawdown_pct']<10),
        ('Gözlənilməz yenidən başlamalar yoxdur',restarts==0),
        ('Ciddi xəta qeydə alınmayıb',no_critical),
    ]


def simulate_small_account(signals,balance,risk_pct,specs):
    possible=0; min_lot_rejected=0; unavailable=0
    for signal in signals:
        spec=specs.get(signal.get('symbol'))
        if not spec:
            unavailable+=1; continue
        volume,reason=calc_volume(float(balance),float(risk_pct),float(signal.get('entry') or 0),float(signal.get('sl') or 0),spec)
        if volume>0: possible+=1
        elif reason=='min lot exceeds risk': min_lot_rejected+=1
        else: unavailable+=1
    return {'signals':len(signals),'possible':possible,'min_lot_rejected':min_lot_rejected,'unavailable':unavailable}
