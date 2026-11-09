"""Backtest statistics, validation warnings and report artifact generation."""
from __future__ import annotations
from datetime import datetime,timezone,timedelta
from itertools import product
from pathlib import Path
import pandas as pd

def _trade_frame(trades):
    frame=pd.DataFrame(trades)
    if frame.empty: return frame
    if 'net_profit' not in frame: frame['net_profit']=frame.get('profit',0)+frame.get('commission',0)+frame.get('swap',0)
    frame['close_time']=pd.to_datetime(frame['close_time'],utc=True)
    if 'hour' not in frame:
        basis=frame['open_time'] if 'open_time' in frame else frame['close_time']
        frame['hour']=pd.to_datetime(basis,utc=True).dt.hour
    return frame

def _metrics(frame,equity_curve=None,start_equity=None):
    if frame.empty:
        return {'trades':0,'win_rate':0.0,'average_win':0.0,'average_loss':0.0,'expectancy':0.0,'profit_factor':0.0,'max_drawdown':0.0,'max_drawdown_pct':0.0,'longest_losing_streak':0,'average_holding_minutes':0.0,'total_costs':0.0,'return_pct':0.0,'sharpe':0.0,'sortino':0.0,'calmar':0.0}
    net=frame.net_profit.astype(float); wins=net[net>0]; losses=net[net<0]
    gross_profit=float(wins.sum()); gross_loss=float(-losses.sum()); pf=gross_profit/gross_loss if gross_loss else (float('inf') if gross_profit else 0.0)
    if equity_curve:
        eq=pd.DataFrame(equity_curve).equity.astype(float); peak=eq.cummax(); dd=peak-eq; dd_pct=dd/peak.replace(0,pd.NA)*100
        max_dd=float(dd.max()); max_dd_pct=float(dd_pct.max()) if dd_pct.notna().any() else 0.0; start=float(equity_curve[0].get('equity',0))
    else:
        start=float(start_equity or 0); curve=start+net.cumsum(); peak=curve.cummax(); dd=peak-curve
        max_dd=float(dd.max()); dd_pct=dd/peak.replace(0,pd.NA)*100; max_dd_pct=float(dd_pct.max()) if dd_pct.notna().any() else 0.0
    streak=longest=0
    for value in net:
        streak=streak+1 if value<0 else 0; longest=max(longest,streak)
    deviation=float(net.std(ddof=1)) if len(net)>1 else 0.0
    downside=net[net<0]; downside_dev=float((downside.pow(2).mean())**.5) if len(downside) else 0.0
    sharpe=float(net.mean()/deviation*(len(net)**.5)) if deviation>0 else 0.0
    sortino=float(net.mean()/downside_dev*(len(net)**.5)) if downside_dev>0 else 0.0
    total_return=float(net.sum()/start*100) if start else 0.0
    calmar=total_return/max_dd_pct if max_dd_pct>0 else (float('inf') if total_return>0 else 0.0)
    return {'trades':int(len(frame)),'win_rate':float((net>0).mean()),'average_win':float(wins.mean()) if len(wins) else 0.0,'average_loss':float(losses.mean()) if len(losses) else 0.0,'expectancy':float(net.mean()),'profit_factor':pf,'max_drawdown':max_dd,'max_drawdown_pct':max_dd_pct,'longest_losing_streak':longest,'average_holding_minutes':float(frame.get('holding_minutes',pd.Series(0,index=frame.index)).mean()),'total_costs':float(frame.get('costs',pd.Series(0,index=frame.index)).sum()),'return_pct':total_return,'sharpe':sharpe,'sortino':sortino,'calmar':calmar}

def monte_carlo(trades,start_equity,iterations=10_000,seed=7,ruin_equity=0.0):
    """Bootstrap net trade outcomes and report terminal equity, drawdown and ruin.

    This is an IID trade-order sensitivity analysis, not a slippage/path model.
    """
    import numpy as np
    values=np.asarray([float(row.get('net_profit',row.get('profit',0)+row.get('commission',0)+row.get('swap',0))) for row in trades],dtype=float)
    if len(values)==0: return {'iterations':0,'terminal_equity_percentiles':None,'max_drawdown_percentiles':None,'ruin_probability':0.0}
    if iterations<=0 or start_equity<=0: raise ValueError('iterations and start_equity must be positive')
    rng=np.random.default_rng(seed); endings=np.empty(iterations); drawdowns=np.empty(iterations); ruins=0
    for i in range(iterations):
        path=float(start_equity)+np.cumsum(rng.choice(values,size=len(values),replace=True))
        peak=np.maximum.accumulate(np.r_[float(start_equity),path])[1:]
        dd=(peak-path)/np.maximum(peak,1e-12)*100
        endings[i]=path[-1]; drawdowns[i]=float(dd.max(initial=0))
        ruins+=bool(np.any(path<=float(ruin_equity)))
    return {'iterations':int(iterations),'terminal_equity_percentiles':{str(q):float(np.percentile(endings,q)) for q in (5,50,95)},
            'max_drawdown_percentiles':{str(q):float(np.percentile(drawdowns,q)) for q in (5,50,95)},
            'ruin_probability':ruins/iterations}

def metrics_by(trades,dimension,start_equity=None):
    frame=_trade_frame(trades)
    if frame.empty: return pd.DataFrame()
    return pd.DataFrame([{'group':str(key),**_metrics(group,start_equity=start_equity)} for key,group in frame.groupby(dimension,dropna=False)]).rename(columns={'group':dimension})

def validate(trades,equity_curve,in_sample_pct=.7):
    frame=_trade_frame(trades)
    if frame.empty: return {'overall':_metrics(frame,equity_curve),'in_sample':_metrics(frame),'out_of_sample':_metrics(frame),'warnings':['No trades were generated.'],'per_strategy':[]}
    frame=frame.sort_values('close_time')
    if len(frame)>1:
        first,last=frame.close_time.min(),frame.close_time.max()
        split_time=first+(last-first)*float(in_sample_pct)
        ins=frame[frame.close_time<=split_time]; oos=frame[frame.close_time>split_time]
        if ins.empty or oos.empty:
            split=max(1,min(len(frame)-1,int(len(frame)*in_sample_pct))); ins=frame.iloc[:split]; oos=frame.iloc[split:]
    else: ins=frame; oos=frame.iloc[0:0]
    start_equity=float(equity_curve[0].get('equity',0)) if equity_curve else 0.0
    overall=_metrics(frame,equity_curve,start_equity); in_metrics=_metrics(ins,start_equity=start_equity); out_metrics=_metrics(oos,start_equity=start_equity)
    warnings=[]
    if len(frame)<100: warnings.append(f'Fewer than 100 trades ({len(frame)}).')
    if len(oos) and in_metrics['expectancy']>0 and out_metrics['expectancy']<.5*in_metrics['expectancy']: warnings.append('Out-of-sample expectancy is below 50% of in-sample expectancy.')
    if frame.symbol.nunique()==1 and len(frame)>1: warnings.append('Profit depends on a single symbol.')
    if len(frame)>=5 and frame.net_profit.nlargest(min(3,len(frame))).sum()>=.8*max(0,float(frame.net_profit.sum())): warnings.append('Profit depends on a few trades.')
    gross=max(0,float(frame.profit.sum())); costs=float(frame.costs.sum()) if 'costs' in frame else 0
    if gross and costs>.5*gross: warnings.append('Costs exceed 50% of gross profit.')
    per=[]
    for name,group in frame.groupby('strategy'):
        sub_metrics=_metrics(group,start_equity=start_equity); sub_ins=group[group.close_time<=split_time] if len(frame)>1 else group; sub_oos=group[group.close_time>split_time] if len(frame)>1 else group.iloc[0:0]
        if sub_ins.empty and len(group): sub_ins=group.iloc[:1]
        expect_oos=_metrics(sub_oos)['expectancy'] if len(sub_oos) else 0.0
        reasons=[]
        if sub_metrics['expectancy']<=0 or sub_metrics['profit_factor']<1: verdict='FAIL'; reasons.append('non-positive expectancy or profit factor below 1')
        elif sub_metrics['trades']<100 or expect_oos<.5*_metrics(sub_ins)['expectancy'] or (sub_metrics['total_costs']>.5*max(0,float(group.profit.sum()))): verdict='WEAK'; reasons.append('insufficient sample or weak out-of-sample/cost robustness')
        else: verdict='PASS'; reasons.append('sample, expectancy, profit factor and cost checks passed')
        per.append({'strategy':name,**sub_metrics,'in_sample_expectancy':_metrics(sub_ins)['expectancy'],'out_of_sample_expectancy':expect_oos,'verdict':verdict,'reasons':'; '.join(reasons)})
    return {'overall':overall,'in_sample':in_metrics,'out_of_sample':out_metrics,'warnings':warnings,'per_strategy':per}

def walk_forward(history_start,history_end,grid_by_strategy,run_window,optimize_months=6,test_months=2):
    """Optimize a bounded Cartesian grid on rolling train windows, report test windows.

    `run_window(start, end, strategy_name, params)` must return trade rows.
    Each strategy grid is capped at twenty combinations.
    """
    start=pd.Timestamp(history_start); end=pd.Timestamp(history_end)
    start=start.tz_localize('UTC') if start.tzinfo is None else start.tz_convert('UTC')
    end=end.tz_localize('UTC') if end.tzinfo is None else end.tz_convert('UTC')
    rows=[]
    for name,grid in grid_by_strategy.items():
        keys=list(grid); combos=[dict(zip(keys,values)) for values in product(*(grid[k] for k in keys))][:20] or [{}]
        train_start=start
        while train_start+pd.DateOffset(months=optimize_months+test_months)<=end:
            train_end=train_start+pd.DateOffset(months=optimize_months); test_end=train_end+pd.DateOffset(months=test_months)
            best=None; best_exp=float('-inf')
            for params in combos:
                training=run_window(train_start.to_pydatetime(),train_end.to_pydatetime(),name,params)
                exp=_metrics(_trade_frame(training))['expectancy']
                if exp>best_exp: best,best_exp=params,exp
            testing=run_window(train_end.to_pydatetime(),test_end.to_pydatetime(),name,best or {})
            rows.append({'strategy':name,'train_start':train_start.isoformat(),'train_end':train_end.isoformat(),'test_end':test_end.isoformat(),'params':best or {},'in_sample_expectancy':best_exp,'out_of_sample_expectancy':_metrics(_trade_frame(testing))['expectancy'],'test_trades':len(testing)})
            train_start+=pd.DateOffset(months=test_months)
    return rows

def save_report(result,output_root='reports',in_sample_pct=.7):
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'); directory=Path(output_root)/stamp; directory.mkdir(parents=True,exist_ok=True)
    trades=result.trades; frame=_trade_frame(trades); equity=pd.DataFrame(result.equity_curve)
    frame.to_csv(directory/'trades.csv',index=False)
    metrics=validate(trades,result.equity_curve,in_sample_pct)
    for warning in metrics['warnings']: print(f'WARNING: {warning}')
    start_equity=float(equity.equity.iloc[0]) if not equity.empty else 0.0
    metrics_by(trades,'symbol',start_equity).to_csv(directory/'per_symbol.csv',index=False)
    metrics_by(trades,'strategy',start_equity).to_csv(directory/'per_strategy.csv',index=False)
    metrics_by(trades,'asset_group',start_equity).to_csv(directory/'per_asset_group.csv',index=False)
    metrics_by(trades,'hour',start_equity).to_csv(directory/'per_hour.csv',index=False)
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(10,5))
    if not equity.empty: ax.plot(pd.to_datetime(equity.time,utc=True),equity.equity); ax.set_ylabel('Equity')
    ax.set_title('Portfolio equity'); ax.grid(True,alpha=.25); fig.tight_layout(); fig.savefig(directory/'equity.png',dpi=140); plt.close(fig)
    lines=['# Backtest summary','',f"Trades: {metrics['overall']['trades']}",f"Expectancy after costs: {metrics['overall']['expectancy']:.4f}",f"Profit factor: {metrics['overall']['profit_factor']:.4f}",f"Maximum drawdown: {metrics['overall']['max_drawdown']:.4f} ({metrics['overall']['max_drawdown_pct']:.2f}%)",'', '## In-sample / out-of-sample',f"In-sample expectancy: {metrics['in_sample']['expectancy']:.4f}",f"Out-of-sample expectancy: {metrics['out_of_sample']['expectancy']:.4f}",'','## Strategy verdicts']
    lines += [f"- {row['strategy']}: **{row['verdict']}** — {row['reasons']}" for row in metrics['per_strategy']]
    lines += ['', '## Warnings']+[f'- {warning}' for warning in metrics['warnings']]
    (directory/'summary.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return directory,metrics
