"""Report-only monthly DEMO exploration summary."""
from __future__ import annotations
from datetime import datetime, timezone
import json
from pathlib import Path

FOCUS=('EURUSD','GBPUSD','USDJPY','AUDUSD','USDCAD','EURJPY','GBPJPY','GOLD')

def focus_symbol(symbol: str) -> bool:
    name=str(symbol).upper()
    return any(name.startswith(logical) for logical in FOCUS)
BACKTEST={
 'session_breakout':('Session Breakout',-0.0817,-0.2836,-0.2488),
 'opening_range_breakout':('Opening Range Breakout',-0.0354,-0.0658,-0.1375),
 'vwap_reversion':('VWAP Reversion',-0.0363,-0.0463,-0.0523),
 'donchian_breakout':('Donchian Breakout',-0.0518,-0.0518,0.0202),
 'ts_momentum':('TS Momentum',-0.0274,-0.0340,-0.0161),
 'index_pullback_200d':('Index Pullback',0.1926,0.1921,0.3562),
}

def build_monthly_report(db, month: str) -> str:
    year,mon=map(int,month.split('-')); start=f'{year:04d}-{mon:02d}-01T00:00:00+00:00'
    end_dt=datetime(year+int(mon==12),mon%12+1,1,tzinfo=timezone.utc); end=end_dt.isoformat()
    with db.connect() as c:
        rows=[dict(r) for r in c.execute("SELECT symbol,strategy,features,profit,commission,swap,status FROM trades WHERE mode IN ('exploration','weekend_exploration') AND open_time>=? AND open_time<? ORDER BY open_time",(start,end))]
    rows=[r for r in rows if focus_symbol(r['symbol'])]
    lines=[f'# Aylıq DEMO araşdırma hesabatı — {year:04d}-{mon:02d}','',
      'Bu hesabat müşahidə üçündür. Heç bir strategiyanı adi ticarətə avtomatik keçirmir. Xərclər bağlanmış əməliyyatların brokerdə qeydə alınmış komissiya/swap və saxlanmış faktiki nəticələrindən götürülür.','',
      '| Ailə | Variant | DEMO əməliyyat | Qazanma faizi | Gözlənilən nəticə (R) | Profit factor | Maks. azalma (R) | Backtest aralığı (R) | Status |','|---|---|---:|---:|---:|---:|---:|---:|---|']
    for key,(label,bt,lo,hi) in BACKTEST.items():
      variants=sorted({str(json.loads(r['features'] or '{}').get('exploration',{}).get('variant','v1')) for r in rows if r['strategy']==key}) or ['v1']
      for variant in variants:
        selected=[r for r in rows if r['strategy']==key and str(json.loads(r['features'] or '{}').get('exploration',{}).get('variant','v1'))==variant and r['status']=='closed']
        rs=[]
        for r in selected:
          feat=json.loads(r['features'] or '{}'); risk=float(feat.get('sizing',{}).get('planned_stop_risk_money') or 0)
          if risk>0: rs.append(sum(float(r.get(k) or 0) for k in ('profit','commission','swap'))/risk)
        n=len(rs); wins=sum(x>0 for x in rs); gross_win=sum(x for x in rs if x>0); gross_loss=-sum(x for x in rs if x<0)
        ev=sum(rs)/n if n else 0; pf=gross_win/gross_loss if gross_loss else (float('inf') if gross_win else 0)
        eq=peak=0; dd=0
        for x in rs:
          eq+=x; peak=max(peak,eq); dd=max(dd,peak-eq)
        promising=n>=50 and ev>0 and lo<=ev<=hi
        status='Ümidverici (müşahidə)' if promising else ('50 əməliyyat və daha çox tələb olunur' if n<50 else 'meyarlara uyğun deyil')
        pf_text='∞' if pf==float('inf') else f'{pf:.2f}'
        lines.append(f'| {label} | {variant} | {n} | {wins/n if n else 0:.1%} | {ev:+.3f} | {pf_text} | {dd:.2f} | [{lo:+.3f}, {hi:+.3f}] | {status} |')
    if not rows: lines.extend(['','Bu ay uyğun forex və qızıl DEMO araşdırma əməliyyatı yoxdur.'])
    lines.extend(['','Mənbə: yalnız forex və GOLD DEMO exploration əməliyyatları. “Ümidverici” etiketi ən azı 50 bağlanmış əməliyyat, müsbət xərclərdən sonrakı expectancy və backtest aralığında nəticə tələb edir; qərar vermir və ticarət rejimini dəyişmir.'])
    return '\n'.join(lines)+'\n'

def write_monthly_report(db, output_path: str|Path, month: str, notifier=None) -> Path:
    target=Path(output_path); target.parent.mkdir(parents=True,exist_ok=True)
    body=build_monthly_report(db,month); target.write_text(body,encoding='utf-8')
    db.mark_maintenance_done('monthly_report',month,datetime.now(timezone.utc))
    db.log_event('INFO','monthly_report',f'Monthly DEMO exploration report generated: {month}')
    if notifier: notifier.send(f'monthly_report_{month}',body[:3500])
    return target
