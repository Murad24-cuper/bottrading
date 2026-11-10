"""Calibrate on validation and write one untouched holdout prediction set."""
from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
import json,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import pandas as pd
from src.parquet_compat import read_parquet,write_parquet

from src.brain.checklist import evaluate as evaluate_checklist
from src.brain.memory import prepare_memory,query_memory
from src.brain.training import fit_probability_calibration,calibrate_probability
from src.config import load_settings
from src.features import build_features
from src.indicators import atr
from src.levels import key_levels
from src.patterns.chart import detect_chart_patterns
from src.patterns.candles import detect_candlestick_patterns
from src.patterns.fibonacci import fibonacci_retracement
from src.trade_rules import stop_target_from_atr


def _load_frames(history:Path,symbols:list[str]) -> dict:
    data={}
    for symbol in symbols:
        frames={}
        for tf in ('M1','M5','M15','H1'):
            path=history/f'{symbol}_{tf}.parquet'
            if path.is_file():
                frame=read_parquet(path).sort_index(); ix=pd.DatetimeIndex(frame.index)
                frame.index=ix.tz_localize('UTC') if ix.tz is None else ix.tz_convert('UTC')
                frames[tf]=frame
        data[symbol]=frames
    return data


def _closed_frames(frames:dict,stamp:pd.Timestamp) -> dict:
    delta={'M1':1,'M5':5,'M15':15,'H1':60}; out={}
    for tf,frame in frames.items():
        end=int(frame.index.searchsorted(stamp-pd.Timedelta(minutes=delta[tf]),side='right'))
        if end>0: out[tf]=frame.iloc[max(0,end-250):end]
    return out


def _checklists(rows:pd.DataFrame,history:Path,config:dict) -> dict:
    """Compute existing closed-bar checklist once per symbol and sample time."""
    frames=_load_frames(history,rows.symbol.unique().tolist()); results={}; weights=config['brain']['checklist']['weights']
    for symbol,time_text in rows[['symbol','time']].drop_duplicates().itertuples(index=False,name=None):
        stamp=pd.Timestamp(time_text); candles=_closed_frames(frames[symbol],stamp)
        features=build_features(candles); m1=candles.get('M1'); m15=candles.get('M15')
        weekend=bool(rows.loc[(rows.symbol==symbol)&(rows.time==time_text),'weekend'].iloc[0])
        observations={'session':{'active':True},'signal_context':{'direction':'neutral'},'chart_patterns':{},'candlestick_patterns':[],'fibonacci':{},'key_levels':{}}
        if m1 is None or len(m1)<20:
            for direction in ('buy','sell'): results[(symbol,time_text,direction)]={'score':0.0,'blocking_failures':['missing M1 history'],'reason':'Tarix çatışmır'}
            continue
        entry=float(m1.close.iloc[-1]); atr_value=float(atr(m1).iloc[-1])
        if not np.isfinite(atr_value) or atr_value<=0:
            for direction in ('buy','sell'): results[(symbol,time_text,direction)]={'score':0.0,'blocking_failures':['invalid ATR'],'reason':'ATR hesablana bilmədi'}
            continue
        for tf in ('M5','M15'):
            if tf in candles: observations['chart_patterns'][tf]=detect_chart_patterns(candles[tf],tf)
        for tf in ('M1','M5'):
            if tf in candles: observations['candlestick_patterns']+=detect_candlestick_patterns(candles[tf],tf)
        if m15 is not None:
            observations['fibonacci']['M15']=fibonacci_retracement(m15,'M15')
            levels=key_levels(m15)
            observations['key_levels']={'support':levels.get('below',{}).get('price') if levels.get('below') else None,
                'resistance':levels.get('above',{}).get('price') if levels.get('above') else None}
        horizon=float(config.get('weekend',{}).get('move_horizon_minutes',60) if weekend else config['risk']['move_horizon_minutes'])
        for direction in ('buy','sell'):
            _,target=stop_target_from_atr(entry,direction,atr_value,0.0,float(config['risk']['sl_move_mult']),float(config['risk']['tp_move_mult']),horizon)
            results[(symbol,time_text,direction)]=evaluate_checklist(features,direction,weights,observations,entry,target)
    return results


def _sample_period(frame:pd.DataFrame) -> pd.DataFrame:
    stamps=pd.to_datetime(frame.time,utc=True)
    return frame.loc[((stamps.dt.hour*60+stamps.dt.minute)%120)==0].copy()


def _predict(rows:pd.DataFrame,indexes:dict,calibration:dict|None,config:dict,checks:dict) -> pd.DataFrame:
    brain=config['brain']; out=[]
    for row in rows.itertuples(index=False):
        stamp=datetime.fromisoformat(str(row.time).replace('Z','+00:00')).astimezone(timezone.utc)
        memory=indexes.get((bool(row.weekend),str(row.asset_group)))
        found=query_memory(np.asarray(row.vector,dtype=np.float32),memory or [],stamp,str(row.symbol),
            int(brain.get('k_neighbors',300)),int(brain.get('query_exclude_same_symbol_days',1)))
        raw=found.get('probability'); p=calibrate_probability(raw,calibration) if raw is not None and calibration else raw
        avg_win=float(found.get('avg_win_r') or 0); avg_loss=float(found.get('avg_loss_r') or 0)
        ev=p*avg_win-(1-p)*avg_loss if p is not None else None
        check=checks.get((str(row.symbol),str(row.time),str(row.direction)),{})
        check_ok=float(check.get('score',0))>=float(brain['min_checklist']) and not check.get('blocking_failures')
        memory_ok=bool(p is not None and p>=float(brain['min_probability']) and ev is not None and ev>float(brain['min_ev_r']))
        out.append({'time':str(row.time),'symbol':str(row.symbol),'asset_group':str(row.asset_group),'direction':str(row.direction),
            'weekend':bool(row.weekend),'probability_raw':raw,'probability':p,'actual_win':int(row.win),'net_r':float(row.net_r),
            'neighbor_count':int(found.get('count') or 0),'avg_win_r':avg_win,'avg_loss_r':avg_loss,'expected_value_r':ev,
            'checklist_score':float(check.get('score',0)),'checklist_reason':str(check.get('reason','')),
            'checklist_only':bool(check_ok),'memory_only':bool(memory_ok),'both':bool(check_ok and memory_ok),
            'current_rule':False,'subperiod':'','nearest_cases':json.dumps(found.get('cases',[]),ensure_ascii=False)})
    return pd.DataFrame(out)


def main() -> int:
    settings=load_settings(require_credentials=False)
    if settings.config['account']['mode']!='demo' or settings.allow_real: raise SystemExit('Prediction build requires DEMO configuration and ALLOW_REAL=false.')
    brain=settings.data_dir/'brain'; source=read_parquet(brain/'labeled_outcomes.parquet')
    reference=read_parquet(brain/'reference.parquet'); weekend_ref=read_parquet(brain/'weekend_reference.parquet')
    indexes={}
    for weekend,frame in ((False,reference[~reference.weekend.astype(bool)]),(True,weekend_ref)):
        for group,group_rows in frame.groupby('asset_group'):
            indexes[(weekend,str(group))]=prepare_memory(group_rows.to_dict('records'))
    history=settings.data_dir/'history'; validation_source=_sample_period(source[source.split=='validation'])
    validation_checks=_checklists(validation_source,history,settings.config)
    validation_raw=_predict(validation_source,indexes,None,settings.config,validation_checks)
    valid=validation_raw.probability_raw.notna()
    if not valid.any(): raise SystemExit('Validation produced no causal memory probabilities; holdout was not used.')
    calibration=fit_probability_calibration(validation_raw.loc[valid,'probability_raw'],validation_raw.loc[valid,'actual_win'],bins=10)
    validation=validation_raw.copy()
    validation['probability']=validation.probability_raw.map(lambda p:calibrate_probability(p,calibration) if pd.notna(p) else np.nan)
    validation['expected_value_r']=validation.probability*validation.avg_win_r-(1-validation.probability)*validation.avg_loss_r
    validation['memory_only']=(validation.probability>=float(settings.config['brain']['min_probability'])) & (validation.expected_value_r>float(settings.config['brain']['min_ev_r']))
    thresholds=sorted({float(settings.config['brain']['min_probability']),.60,.65,.70,.75})
    active_groups=set(validation.asset_group.unique()); rounds=[]
    for round_no,threshold in enumerate(thresholds,1):
        eligible=validation[validation.checklist_only & validation.memory_only & (validation.probability>=threshold) & validation.asset_group.isin(active_groups)]
        if eligible.empty:
            rounds.append({'round':round_no,'probability_floor':threshold,'trades':0,'expectancy_r':None,'change':'No validation candidates satisfy unchanged checklist, probability, and EV floors.'})
            continue
        group_ev=eligible.groupby('asset_group').net_r.mean(); active_groups=set(group_ev[group_ev>0].index)
        rounds.append({'round':round_no,'probability_floor':threshold,'trades':len(eligible),'expectancy_r':float(eligible.net_r.mean()),'positive_groups':sorted(active_groups),'change':'Retain validation-positive asset groups.'})
        if not active_groups: break
    validation['both']=validation.checklist_only & validation.memory_only & validation.asset_group.isin(active_groups)
    write_parquet(validation,brain/'validation_predictions.parquet',index=False)
    (brain/'calibration.json').write_text(json.dumps(calibration,indent=2),encoding='utf-8')
    (brain/'validation_rounds.json').write_text(json.dumps({'rounds':rounds,'active_groups':sorted(active_groups),'built_at_utc':datetime.now(timezone.utc).isoformat()},indent=2),encoding='utf-8')
    # Freeze all choices before this sole holdout prediction pass.
    test_source=_sample_period(source[source.split=='test']); test_checks=_checklists(test_source,history,settings.config)
    test=_predict(test_source,indexes,calibration,settings.config,test_checks)
    test['both']=test.checklist_only & test.memory_only & test.asset_group.isin(active_groups)
    if len(test):
        stamps=pd.to_datetime(test.time,utc=True); edges=np.linspace(stamps.min().value,stamps.max().value,4)
        test['subperiod']=pd.cut(stamps.astype('int64'),edges,labels=['1','2','3'],include_lowest=True).astype(str)
    write_parquet(test,brain/'test_predictions.parquet',index=False)
    print(f'Validation rows: {len(validation):,}; usable raw predictions: {int(valid.sum()):,}; tuning rounds: {len(rounds)}; active groups: {sorted(active_groups)}')
    print(f'Holdout predictions written once: {len(test):,} rows; {brain / "test_predictions.parquet"}')
    print('Current-rule baseline is unavailable; current_rule remains false.')
    return 0


if __name__=='__main__': raise SystemExit(main())
