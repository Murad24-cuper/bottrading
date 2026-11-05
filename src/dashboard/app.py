"""Single-user local Streamlit dashboard backed solely by SQLite."""
from __future__ import annotations
from datetime import datetime,timezone,time as dt_time,timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import hmac,os
import sys
import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from dotenv import load_dotenv

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from src.dashboard import queries
DB_PATH=Path(os.getenv('BOT_DB_PATH',ROOT/'data'/'bot.db'))
load_dotenv(ROOT/'.env',override=False)

def _authenticated():
    password=os.getenv('DASHBOARD_PASSWORD','')
    if not password: return True
    if st.session_state.get('dashboard_authenticated'): return True
    with st.form('dashboard_login'):
        entered=st.text_input('Dashboard password',type='password'); submitted=st.form_submit_button('Unlock')
    if submitted:
        if hmac.compare_digest(entered,password): st.session_state.dashboard_authenticated=True; st.rerun()
        else: st.error('Incorrect password')
    return False

def _as_utc(value):
    parsed=datetime.fromisoformat(str(value).replace('Z','+00:00'))
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)

def _local(value,tz):
    if not value: return ''
    try: return _as_utc(value).astimezone(tz).strftime('%Y-%m-%d %H:%M:%S')
    except (ValueError,TypeError): return str(value)

def main():
    st.set_page_config(page_title='Trading Bot Dashboard',layout='wide')
    st_autorefresh(interval=2000,key='dashboard_refresh')
    if not _authenticated(): return
    local_tz=datetime.now().astimezone().tzinfo or ZoneInfo('UTC')
    now_local=datetime.now(local_tz); selected=st.sidebar.date_input('View day',value=now_local.date())
    start_local=datetime.combine(selected,dt_time.min,tzinfo=local_tz); end_local=start_local+timedelta(days=1)
    start_utc=start_local.astimezone(timezone.utc).isoformat(); end_utc=end_local.astimezone(timezone.utc).isoformat()
    status=queries.get_bot_status(DB_PATH); snapshot=queries.get_latest_snapshot(DB_PATH)
    summary=queries.get_day_summary(start_utc,end_utc,DB_PATH)
    stale=True
    if status and status.get('time'):
        try: stale=(datetime.now(timezone.utc)-_as_utc(status['time'])).total_seconds()>30
        except (ValueError,TypeError): stale=True
    mode=(status or {}).get('mode','UNKNOWN').upper(); account=(status or {}).get('account_type','UNKNOWN').upper()
    state=(status or {}).get('status','stopped')
    if stale: st.error(f'Bot status: no heartbeat > 30 s · mode {mode} · account {account}')
    elif state in {'running','managing_only'}: st.success(f'Bot status: {state.replace("_"," ")} · mode {mode} · account {account}')
    else: st.error(f'Bot status: {state} · mode {mode} · account {account}')
    st.caption(f'Selected day shown in local time ({now_local.tzname() or "local"}): {selected.isoformat()}')

    cols=st.columns(5)
    cols[0].metric('Balance',f'{snapshot["balance"]:,.2f}' if snapshot else '—')
    cols[1].metric('Equity',f'{snapshot["equity"]:,.2f}' if snapshot else '—')
    cols[2].metric('Free margin',f'{snapshot["free_margin"]:,.2f}' if snapshot else '—')
    cols[3].metric('Today net P/L',f'{summary["net_pnl"]:,.2f}')
    cols[4].metric('Trades · wins/losses',f'{summary["trades"]} · {summary["wins"]}/{summary["losses"]}',f'win rate {summary["win_rate"]:.1%}')
    cols=st.columns(4)
    cols[0].metric('Invested now',f'{snapshot["margin"]:,.2f}' if snapshot else '—')
    daily_stats=queries.get_daily_pnl(DB_PATH,30)
    peak=0.0
    stats_date=start_local.astimezone(timezone.utc).date().isoformat()
    day_stats=queries.get_day_stats(stats_date,DB_PATH)
    if day_stats: peak=float(day_stats[0].get('invested_margin_peak') or 0)
    cols[1].metric('Peak margin today',f'{peak:,.2f}')
    cols[2].metric('Taken today',f'{summary["taken"]:,.2f}')
    cols[3].metric('Lost today',f'{summary["lost"]:,.2f}')

    st.sidebar.header('Controls')
    if st.sidebar.button('Pause new trades',use_container_width=True):
        try: queries.enqueue_command('pause',DB_PATH); st.sidebar.success('Pause command queued')
        except Exception as exc: st.sidebar.error(f'Could not queue pause: {exc}')
    if st.sidebar.button('Resume trades',use_container_width=True):
        try: queries.enqueue_command('resume',DB_PATH); st.sidebar.success('Resume command queued')
        except Exception as exc: st.sidebar.error(f'Could not queue resume: {exc}')
    confirm=st.sidebar.checkbox('I confirm: close all bot positions')
    if st.sidebar.button('Close all positions',disabled=not confirm,use_container_width=True):
        try: queries.enqueue_command('close_all',DB_PATH); st.sidebar.warning('Close-all command queued for the bot')
        except Exception as exc: st.sidebar.error(f'Could not queue close-all: {exc}')

    st.subheader('Open positions')
    opened=queries.get_open_positions(DB_PATH)
    if opened:
        now_utc=datetime.now(timezone.utc)
        for row in opened:
            row['minutes_open']=max(0,(now_utc-_as_utc(row['open_time'])).total_seconds()/60)
            row['open_time_local']=_local(row['open_time'],local_tz)
        st.dataframe(pd.DataFrame(opened)[['symbol','direction','volume','open_price','profit','sl','tp','minutes_open','strategy']],use_container_width=True,hide_index=True)
    else: st.caption('No open bot positions.')

    st.subheader('Closed trades')
    closed=queries.get_closed_trades(start_utc,end_utc,DB_PATH)
    if closed:
        for row in closed: row['close_time_local']=_local(row['close_time'],local_tz)
        st.dataframe(pd.DataFrame(closed)[['close_time_local','symbol','direction','volume','open_price','close_price','net_profit','close_reason','strategy']],use_container_width=True,hide_index=True)
    else: st.caption('No closed trades for the selected day.')

    st.subheader('Latest signals')
    signals=queries.get_latest_signals(DB_PATH,50)
    if signals:
        for row in signals: row['time_local']=_local(row['time'],local_tz)
        st.dataframe(pd.DataFrame(signals)[['time_local','symbol','strategy','direction','score','confidence','taken','skip_reason']],use_container_width=True,hide_index=True)
    else: st.caption('No signals recorded.')

    st.subheader('Recent bot events')
    events=queries.get_recent_events(DB_PATH,30)
    for event in events:
        stamp=_local(event['time'],local_tz); message=f'{stamp} · {event["level"]} · {event["source"]}: {event["message"]}'
        if event['level'] in {'WARNING','ERROR','CRITICAL'}: st.warning(message)
        else: st.write(message)

    left,right=st.columns(2)
    with left:
        st.subheader('Equity today')
        curve=queries.get_equity_curve(start_utc,end_utc,DB_PATH)
        if curve:
            frame=pd.DataFrame(curve); frame['time_local']=pd.to_datetime(frame.time,utc=True).dt.tz_convert(local_tz); st.line_chart(frame.set_index('time_local')[['equity','balance']])
        else: st.caption('No equity snapshots for the selected day.')
    with right:
        st.subheader('Daily P/L · last 30 UTC days')
        if daily_stats:
            frame=pd.DataFrame(daily_stats); frame['date']=pd.to_datetime(frame.date); st.bar_chart(frame.set_index('date')[['pnl']])
        else: st.caption('No daily statistics recorded yet.')

if __name__=='__main__': main()
