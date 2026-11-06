"""Single-user local Streamlit dashboard backed solely by SQLite."""
from __future__ import annotations
from datetime import datetime,timezone,time as dt_time,timedelta
from pathlib import Path
import hmac,os,subprocess,time,json
import sys
import yaml
import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from dotenv import load_dotenv

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from src.dashboard import queries
from src.dashboard.readiness import readiness_checks, simulate_small_account
from src.paths import project_paths
from src.dashboard.presentation import (AZ_TZ, close_reason_label,
                                        direction_label, format_duration,
                                        feature_label, format_money, local_time,
                                        strategy_label, translate_message)
load_dotenv(ROOT/'.env',override=False)
DATA_DIR,LOG_DIR=project_paths(ROOT)
_APP_CONFIG=yaml.safe_load((ROOT/'config.yaml').read_text(encoding='utf-8'))
_configured_db=Path(_APP_CONFIG.get('db_path','data/bot.db'))
DB_PATH=Path(os.getenv('BOT_DB_PATH','')) if os.getenv('BOT_DB_PATH') else (_configured_db if _configured_db.is_absolute() else ROOT/_configured_db)

def _lock_pid():
    try: return int((DATA_DIR/'bot.lock').read_text(encoding='utf-8').split()[0])
    except (OSError,ValueError,IndexError): return None

def _supervisor_pid():
    try: return int((DATA_DIR/'supervisor.pid').read_text(encoding='utf-8').strip())
    except (OSError,ValueError): return None

def _supervisor_running():
    pid=_supervisor_pid()
    if pid and _pid_running(pid): return True
    if pid:
        try: (DATA_DIR/'supervisor.pid').unlink(missing_ok=True)
        except OSError: pass
    return False

def _pid_running(pid):
    if not pid: return False
    if os.name=='nt':
        import ctypes
        from ctypes import wintypes
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
        kernel.OpenProcess.restype=wintypes.HANDLE
        kernel.GetExitCodeProcess.argtypes=[wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD)]
        kernel.GetExitCodeProcess.restype=wintypes.BOOL
        kernel.CloseHandle.argtypes=[wintypes.HANDLE]
        handle=kernel.OpenProcess(0x1000,False,int(pid))  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle: return ctypes.get_last_error()==5  # Access denied still means the PID exists.
        try:
            exit_code=wintypes.DWORD()
            return bool(kernel.GetExitCodeProcess(handle,ctypes.byref(exit_code)) and exit_code.value==259)  # STILL_ACTIVE
        finally: kernel.CloseHandle(handle)
    try: os.kill(int(pid),0); return True
    except (OSError,ValueError,ProcessLookupError): return False

def _heartbeat_fresh(status,now=None):
    try: return bool(status and status.get('time') and (now or datetime.now(timezone.utc))-_as_utc(status['time'])<=timedelta(seconds=60))
    except (ValueError,TypeError): return False

def _start_bot():
    """Start one detached bot process, with both UI and bot locks guarding races."""
    status=queries.get_bot_status(DB_PATH); pid=_lock_pid(); running=_pid_running(pid); supervisor_running=_supervisor_running()
    lock_path=DATA_DIR/'bot.lock'
    if lock_path.exists() and not running:
        lock_path.unlink(missing_ok=True)
    if running or supervisor_running or _heartbeat_fresh(status): return False,'Bot already appears to be running.'
    guard=DATA_DIR/'dashboard-start.lock'; guard.parent.mkdir(parents=True,exist_ok=True)
    try: handle=guard.open('x',encoding='utf-8')
    except FileExistsError: return False,'A Start request is already in progress.'
    try:
        handle.write(f'{os.getpid()} {time.time_ns()}\n'); handle.close()
        stop=ROOT/'STOP'
        if stop.exists(): stop.unlink()
        (DATA_DIR/'supervisor.stop').unlink(missing_ok=True)
        python=ROOT/'.venv'/'Scripts'/'pythonw.exe'; script=ROOT/'scripts'/'run_forever.py'
        log_path=LOG_DIR/'bot_stdout.log'; log_path.parent.mkdir(parents=True,exist_ok=True)
        flags=getattr(subprocess,'DETACHED_PROCESS',0x00000008)|getattr(subprocess,'CREATE_NEW_PROCESS_GROUP',0x00000200)
        breakaway=getattr(subprocess,'CREATE_BREAKAWAY_FROM_JOB',0x01000000)
        with log_path.open('a',encoding='utf-8',buffering=1) as output:
            options={'cwd':ROOT,'stdin':subprocess.DEVNULL,'stdout':output,'stderr':subprocess.STDOUT,'close_fds':True}
            try: subprocess.Popen([str(python),str(script)],creationflags=flags|breakaway,**options)
            except OSError: subprocess.Popen([str(python),str(script)],creationflags=flags,**options)
        return True,'Bot start requested.'
    except Exception as exc:
        (ROOT/'STOP').write_text('PAUSE\n',encoding='utf-8')
        return False,f'Could not start bot: {exc}'
    finally:
        try: handle.close()
        except Exception: pass
        guard.unlink(missing_ok=True)

def _command_ttl():
    import yaml
    config=yaml.safe_load((ROOT/'config.yaml').read_text(encoding='utf-8'))
    return int(config['live']['command_ttl_seconds'])

def _authenticated():
    password=os.getenv('DASHBOARD_PASSWORD','')
    if not password: return True
    if st.session_state.get('dashboard_authenticated'): return True
    with st.form('dashboard_login'):
        entered=st.text_input('Panel parolu',type='password'); submitted=st.form_submit_button('Daxil ol')
    if submitted:
        if hmac.compare_digest(entered,password): st.session_state.dashboard_authenticated=True; st.rerun()
        else: st.error('Parol yanlışdır')
    return False

def _as_utc(value):
    parsed=datetime.fromisoformat(str(value).replace('Z','+00:00'))
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)

def _local(value,tz=None,fmt='%Y-%m-%d %H:%M:%S'):
    return local_time(value,fmt)


def _money_color(value):
    number=float(value or 0)
    return 'color: #16803c; font-weight: 600' if number>0 else 'color: #c62828; font-weight: 600' if number<0 else 'color: #777'


def _metric_card(label,value,color='#dfe7f1',detail=''):
    st.markdown('<div class="metric-card">'+f'<div class="metric-label">{label}</div>'+f'<div class="metric-value" style="color:{color}">{value}</div>'+f'<div class="metric-detail">{detail}</div></div>',unsafe_allow_html=True)

def main():
    st.set_page_config(page_title='Ticarət botu',layout='wide')
    st_autorefresh(interval=2000,key='dashboard_refresh')
    if not _authenticated(): return
    now_local=datetime.now(AZ_TZ); today=now_local.date()
    today_start=datetime.combine(today,dt_time.min,tzinfo=AZ_TZ).astimezone(timezone.utc).isoformat()
    today_end=(datetime.combine(today,dt_time.min,tzinfo=AZ_TZ)+timedelta(days=1)).astimezone(timezone.utc).isoformat()
    selected=st.session_state.get('detail_date',today)
    detail_start=datetime.combine(selected,dt_time.min,tzinfo=AZ_TZ).astimezone(timezone.utc).isoformat()
    detail_end=(datetime.combine(selected,dt_time.min,tzinfo=AZ_TZ)+timedelta(days=1)).astimezone(timezone.utc).isoformat()
    status=queries.get_bot_status(DB_PATH); snapshot=queries.get_latest_snapshot(DB_PATH)
    summary=queries.get_day_summary(today_start,today_end,DB_PATH)
    stale=not _heartbeat_fresh(status); pid=_lock_pid(); supervisor_running=_supervisor_running(); process_running=_pid_running(pid) or supervisor_running
    account=(status or {}).get('account_type','UNKNOWN').upper(); paused=(ROOT/'STOP').exists()
    mt5_connected=bool((status or {}).get('mt5_connected',0)) and not stale
    if not process_running:
        status_text='🔴 Bot dayanıb'; status_kind='bad'
    elif stale:
        status_text='🔴 Bot cavab vermir · son ürək döyüntüsü 60 saniyədən köhnədir'; status_kind='bad'
    elif not mt5_connected:
        status_text='🔴 MT5 ilə əlaqə yoxdur'; status_kind='bad'
    elif status and not bool(status.get('trade_allowed',1)):
        status_text='🔴 MT5-də avtomatik ticarət icazəsi bağlıdır'; status_kind='bad'
    elif paused:
        status_text='🟡 Fasilədə'; status_kind='warn'
    else:
        status_text=f'🟢 Bot işləyir · {account if account == "DEMO" else "Hesab"} hesab'; status_kind='good'
    colors={'good':'#167d3f','warn':'#a66a00','bad':'#b42318'}
    st.markdown(f'<div class="status-bar" style="background:{colors[status_kind]}">{status_text}</div>',unsafe_allow_html=True)
    restart_count=queries.get_supervisor_restart_count(today_start,today_end,DB_PATH)
    st.caption(f'Nəzarətçi: {"işləyir" if supervisor_running else "dayanıb"} · Bu gün yenidən başladılma: {restart_count}')
    st.markdown('<style>.status-bar{color:white;padding:.75rem 1rem;border-radius:.55rem;font-weight:650;margin:.4rem 0 1rem}.metric-card{padding:1.1rem 1rem;border:1px solid rgba(128,128,128,.25);border-radius:.7rem;min-height:105px}.metric-label{font-size:.95rem;opacity:.8}.metric-value{font-size:1.7rem;font-weight:700;margin-top:.3rem}.metric-detail{font-size:.8rem;opacity:.75;margin-top:.2rem}div[data-testid="stButton"] button{min-height:3rem;font-weight:650}</style>',unsafe_allow_html=True)

    tab_main, tab_report, tab_analysis, tab_prepare, tab_detail = st.tabs(['Əsas', 'Hesabat', 'Analiz', 'Hazırlıq', 'Ətraflı'])
    with tab_main:
        controls=st.columns([1.4,1.15,1.4])
        if st.session_state.get('action_message'):
            message=st.session_state.pop('action_message'); level=st.session_state.pop('action_level','info')
            getattr(st,level if level in {'success','warning','error','info'} else 'info')(message)
        with controls[0]:
            if st.button('⏹ Botu dayandır' if process_running else '▶ Botu başlat',key='main_bot_toggle',use_container_width=True):
                if process_running:
                    try:
                        queries.enqueue_command('stop',DB_PATH,ttl_seconds=_command_ttl())
                        st.session_state.action_message='Dayandırma əmri göndərildi.'; st.session_state.action_level='success'
                    except Exception as exc:
                        st.session_state.action_message=f'Dayandırma əmri göndərilmədi: {translate_message(exc)}'; st.session_state.action_level='error'
                else:
                    ok,message=_start_bot()
                    st.session_state.action_message='Botun başladılması istənildi.' if ok else f'Bot başlamadı: {translate_message(message)}'
                    st.session_state.action_level='success' if ok else 'error'
                st.rerun()
        with controls[1]:
            paused=(ROOT/'STOP').exists()
            if st.button('▶ Davam et' if paused else '⏸ Fasilə',key='pause_toggle',disabled=not process_running,use_container_width=True):
                command='resume' if paused else 'pause'
                try:
                    queries.enqueue_command(command,DB_PATH,ttl_seconds=_command_ttl())
                    st.session_state.action_message='Davam etmə əmri göndərildi.' if paused else 'Fasilə əmri göndərildi.'
                    st.session_state.action_level='success'
                except Exception as exc:
                    st.session_state.action_message=f'Əmr göndərilmədi: {translate_message(exc)}'; st.session_state.action_level='error'
                st.rerun()
        with controls[2]:
            with st.expander('Hamısını bağla və dayan',expanded=False):
                confirm=st.checkbox('Bütün açıq mövqelərin bağlanmasını təsdiq edirəm',key='confirm_close_all')
                if st.button('Hamısını bağla və dayan',key='close_all_stop',disabled=not (confirm and process_running),use_container_width=True):
                    try:
                        queries.enqueue_command('close_all_stop',DB_PATH,ttl_seconds=_command_ttl())
                        st.session_state.action_message='Bütün mövqeləri bağlama və dayandırma əmri göndərildi.'; st.session_state.action_level='success'
                    except Exception as exc:
                        st.session_state.action_message=f'Əmr göndərilmədi: {translate_message(exc)}'; st.session_state.action_level='error'
                    st.rerun()

        daily_result=float(summary['net_pnl']); result_color='#16803c' if daily_result>0 else '#c62828' if daily_result<0 else '#777'
        metrics=st.columns(4)
        with metrics[0]: _metric_card('Balans',format_money(snapshot.get('balance') if snapshot else None))
        with metrics[1]: _metric_card('Bu günkü nəticə',format_money(daily_result,signed=True),result_color)
        with metrics[2]: _metric_card('Hazırda yatırılıb',format_money(snapshot.get('margin') if snapshot else None))
        with metrics[3]: _metric_card('Əməliyyatlar',str(summary['trades']),detail=f'{summary["win_rate"]:.1%} qazanma faizi')
        diversity=queries.get_today_diversity(today_start,today_end,DB_PATH)
        st.caption(f"Bu gün: {diversity['symbols']} fərqli alət, {diversity['groups']} qrup")

        opened=queries.get_open_positions(DB_PATH); now_utc=datetime.now(timezone.utc)
        for row in opened:
            row['duration']=format_duration((now_utc-_as_utc(row['open_time'])).total_seconds()/60)
            row['extension_status']='Uzadılıb' if int(row.get('extended_minutes') or 0)>0 else '—'
            row['direction_label']=direction_label(row['direction']); row['strategy_label']=strategy_label(row['strategy'])
            row['net_result']=float(row.get('profit') or 0)+float(row.get('commission') or 0)+float(row.get('swap') or 0)
        st.subheader('Açıq mövqelər')
        if opened:
            open_frame=pd.DataFrame([{'Alət':r['symbol'],'İstiqamət':r['direction_label'],'Nəticə':r['net_result'],'Açıq müddət':r['duration'],'Strategiya':r['strategy_label'],'Status':r['extension_status']} for r in opened])
            st.table(open_frame.style.format({'Nəticə':lambda value:format_money(value,signed=True)}).map(_money_color,subset=['Nəticə']))
        else: st.caption('Açıq bot mövqeyi yoxdur.')

        st.subheader('Bu gün bağlanan əməliyyatlar')
        closed=queries.get_closed_trades(today_start,today_end,DB_PATH)
        if closed:
            closed_frame=pd.DataFrame([{'Saat':local_time(r['close_time']),'Alət':r['symbol'],'İstiqamət':direction_label(r['direction']),'Nəticə':r['net_profit'],'Səbəb':close_reason_label(r['close_reason'])} for r in closed])
            st.table(closed_frame.style.format({'Nəticə':lambda value:format_money(value,signed=True)}).map(_money_color,subset=['Nəticə']))
        else: st.caption('Bu gün bağlanan əməliyyat yoxdur.')

        st.subheader('Bu günkü balans dəyişməsi')
        curve=queries.get_equity_curve(today_start,today_end,DB_PATH)
        if curve:
            curve_frame=pd.DataFrame(curve); curve_frame['Saat']=pd.to_datetime(curve_frame.time,utc=True).dt.tz_convert(AZ_TZ)
            st.line_chart(curve_frame.set_index('Saat')[['equity']].rename(columns={'equity':'Kapital'}),height=190)
        else: st.caption('Bu gün üçün kapital qeydi yoxdur.')

    with tab_report:
        now_utc=datetime.now(timezone.utc); seven_start=(now_utc-timedelta(days=7)).isoformat(); all_start='1970-01-01T00:00:00+00:00'
        for label,period_start,period_end in [('Bu gün',today_start,today_end),('Son 7 gün',seven_start,now_utc.isoformat()),('Bütün tarix',all_start,now_utc.isoformat())]:
            report=queries.get_performance_report(period_start,period_end,DB_PATH); overall=report['overall']
            st.subheader(label)
            cards=st.columns(6)
            cards[0].metric('Əməliyyatlar',overall['trades']); cards[1].metric('Qazanma faizi',f"{overall['win_rate']:.1%}")
            cards[2].metric('Orta qazanc',format_money(overall['average_win'])); cards[3].metric('Orta zərər',format_money(overall['average_loss']))
            cards[4].metric('Gözlənilən nəticə',format_money(overall['expectancy'],signed=True)); cards[5].metric('Cəmi nəticə',format_money(overall['total_pnl'],signed=True))
            drawdown=f"{overall['max_drawdown_pct']:.2f}%" if overall['max_drawdown_pct'] is not None else 'Məlumat yoxdur'
            st.caption(f"Maksimum azalma: {drawdown} · təxmini əməliyyat xərcləri: {format_money(overall['estimated_costs'])}")
            for title,key in [('Strategiyaya görə','by_strategy'),('Aktiv qrupuna görə','by_asset_group'),('Bağlanma səbəbinə görə','by_close_reason')]:
                rows=report[key]
                if rows:
                    st.markdown(f'**{title}**')
                    st.dataframe(pd.DataFrame([{'Ad':name,'Əməliyyat':v['trades'],'Qazanma %':f"{v['win_rate']:.1%}",'Orta qazanc':format_money(v['average_win']),'Orta zərər':format_money(v['average_loss']),'Gözlənilən nəticə':format_money(v['expectancy'],signed=True),'Nəticə':format_money(v['total_pnl'],signed=True),'Komissiya':format_money(v['estimated_costs'])} for name,v in rows.items()]),use_container_width=True,hide_index=True)
        st.subheader('Son 30 günün günlük nəticəsi')
        daily=queries.get_daily_pnl(DB_PATH,30)
        if daily:
            daily_frame=pd.DataFrame(daily); daily_frame['Tarix']=pd.to_datetime(daily_frame.date)
            st.bar_chart(daily_frame.set_index('Tarix')[['pnl']].rename(columns={'pnl':'Nəticə ($)'}),height=220)
        else: st.caption('Günlük nəticə məlumatı yoxdur.')
        stored=queries.get_daily_report_rows(DB_PATH,30)
        if stored:
            st.subheader('Saxlanmış günlük hesabatlar')
            st.dataframe(pd.DataFrame([{'Tarix':r['date'],'Nəticə':format_money(r['payload'].get('pnl'),signed=True),'Əməliyyat':r['payload'].get('trades_count',0)} for r in stored]),use_container_width=True,hide_index=True)

    with tab_analysis:
        st.subheader('Xüsusiyyətlərin müşahidə nəticələri')
        st.info('Bunlar bağlanmış əməliyyatlardan hesablanan müşahidələrdir. Hazırda heç biri ticarət qərarlarında istifadə olunmur.')
        impact=queries.get_feature_impact(DB_PATH)
        if impact:
            st.dataframe(pd.DataFrame([{'Xüsusiyyət':feature_label(row['feature']),'Əməliyyat sayı':row['trades'],'Qazanma faizi':f"{row['win_rate']:.1%}",'Fərq (baseline ilə)':f"{row['win_rate_difference']:+.1%}",'Orta nəticə':format_money(row['expectancy'],signed=True),'Sübut olunub?':'Bəli' if row['meaningful'] else 'Hələ az məlumat' if row['trades']<30 else 'Xeyr'} for row in impact]),use_container_width=True,hide_index=True)
        else: st.caption('Xüsusiyyətlər üzrə müqayisə üçün hələ bağlanmış əməliyyat yoxdur.')

    with tab_prepare:
        now_utc=datetime.now(timezone.utc); seven_start=(now_utc-timedelta(days=7)).isoformat(); seven_end=now_utc.isoformat()
        st.subheader('Son 7 gün üzrə hazırlıq yoxlaması')
        for label,passed in readiness_checks(seven_start,seven_end,DB_PATH):
            st.markdown(('✅ ' if passed else '🔴 ')+label)
        dashboard_cfg=yaml.safe_load((ROOT/'config.yaml').read_text(encoding='utf-8')).get('dashboard',{})
        sim_cols=st.columns(2)
        balance=sim_cols[0].number_input('Real hesab məbləği ($)',min_value=1.0,value=float(dashboard_cfg.get('real_balance_default',100)),step=10.0)
        risk_pct=sim_cols[1].number_input('Planlaşdırılan risk (%)',min_value=.01,value=float(dashboard_cfg.get('real_risk_pct_default',1.0)),step=.1)
        raw=yaml.safe_load((ROOT/'config.yaml').read_text(encoding='utf-8'))
        history_dir=Path(raw.get('history',{}).get('data_dir','data/history')); history_dir=history_dir if history_dir.is_absolute() else ROOT/history_dir
        try: specs=json.loads((history_dir/'symbol_specs.json').read_text(encoding='utf-8'))
        except (OSError,ValueError): specs={}
        signal_rows=queries.get_signals_period(seven_start,seven_end,DB_PATH)
        sim=simulate_small_account(signal_rows,balance,risk_pct,specs)
        st.info(f"Son 7 gündəki {sim['signals']} siqnaldan bu kapital və risklə {sim['possible']} əməliyyat açmaq olardı; {sim['min_lot_rejected']} siqnal minimum lot riskə görə rədd edilərdi. {sim['unavailable']} siqnal üçün broker spesifikasiyası və ya düzgün SL yoxdur.")

    with tab_detail:
        with st.expander('Ətraflı məlumat',expanded=False):
            stats=status or {}; heartbeat_age=(datetime.now(timezone.utc)-_as_utc(status['time'])).total_seconds() if status and status.get('time') else None
            st.subheader('Hesab və skanlama')
            diversity=queries.get_today_diversity(today_start,today_end,DB_PATH)
            group_labels={'forex':'Valyuta','metals':'Metallar','indices':'İndekslər','energy':'Enerji','crypto':'Kripto','stocks':'Səhmlər','other':'Digər'}
            st.caption('Bu gün qruplar üzrə əməliyyatlar')
            if diversity['per_group']:
                st.table(pd.DataFrame([{'Qrup':group_labels.get(group,group),'Əməliyyat sayı':count} for group,count in sorted(diversity['per_group'].items(),key=lambda item:-item[1])]))
                st.caption('Bu gün ən çox işlənən alətlər: '+', '.join(f'{name} ({count})' for name,count in diversity['top_symbols']))
            else: st.caption('Bu gün hələ bağlanmış əməliyyat yoxdur.')
            detail_metrics=st.columns(4)
            detail_metrics[0].metric('Kapital',format_money(snapshot.get('equity') if snapshot else None))
            detail_metrics[1].metric('Sərbəst marja',format_money(snapshot.get('free_margin') if snapshot else None))
            detail_metrics[2].metric('MT5 əlaqəsi','Aktivdir' if mt5_connected else 'Yoxdur')
            detail_metrics[3].metric('Ürək döyüntüsü',f'{heartbeat_age:.0f} san' if heartbeat_age is not None else 'Məlumat yoxdur')
            st.caption(f'Skanlama: cəmi {stats.get("scan_total",0)} · yoxlanıb {stats.get("scan_scanned",0)} · ticarətə uyğun {stats.get("scan_stage1_passed",0)} · təhlil edilən alətlər {stats.get("scan_top_n",0)} · siqnallar {stats.get("scan_signals",0)} · {float(stats.get("scan_seconds",0) or 0):.2f} san')
            target=int(_APP_CONFIG.get('scanner',{}).get('target_open_positions',15))
            st.caption(f'Açıq bot mövqeləri: {len(opened)} / {target} hədəf (hədəf məcburi əməliyyat sayı deyil)')
            skips=queries.get_top_skip_reasons_since((datetime.now(timezone.utc)-timedelta(hours=1)).isoformat(),DB_PATH,5)
            st.subheader('Son 1 saatın əsas imtina səbəbləri')
            if skips: st.dataframe(pd.DataFrame([{'Səbəb':translate_message(r['skip_reason']),'Say':r['count']} for r in skips]),use_container_width=True,hide_index=True)
            else: st.caption('Son 1 saatda imtina edilmiş siqnal yoxdur.')
            adaptive=queries.get_adaptive_gates(DB_PATH)
            st.subheader('Müvəqqəti söndürülən strategiyalar və qruplar')
            if adaptive:
                group_names={'forex':'Valyuta','metals':'Metallar','indices':'İndekslər','energy':'Enerji','crypto':'Kripto','stocks':'Səhmlər','other':'Digər'}
                st.table(pd.DataFrame([{'Növ':'Strategiya' if r['scope']=='strategy' else 'Alət qrupu','Ad':strategy_label(r['name']) if r['scope']=='strategy' else group_names.get(r['name'],r['name']),'Son 20 əməliyyatın gözlənilən nəticəsi':format_money(r['expectancy'],signed=True),'Səbəb':'Son bağlanmış əməliyyatlardakı orta nəticə mənfidir','Nümunə':r['sample_size'],'Söndürülüb':'Bəli · '+local_time(r['disabled_until'])} for r in adaptive]))
            else: st.caption('Hazırda müvəqqəti söndürülən strategiya və qrup yoxdur.')
            try:
                import ast
                rejections=stats.get('scan_rejections') or '{}'; rejections=ast.literal_eval(rejections) if isinstance(rejections,str) else rejections
            except (ValueError,SyntaxError): rejections={}
            if rejections: st.table(pd.DataFrame([{'Səbəb':translate_message(k),'Say':v} for k,v in rejections.items()]))
            try:
                diagnostics=stats.get('strategy_diagnostics') or '{}'; diagnostics=json.loads(diagnostics) if isinstance(diagnostics,str) else diagnostics
            except (ValueError,TypeError): diagnostics={}
            rows=[{'Strategiya':strategy_label(name),'Səbəb':translate_message(reason),'Say':count} for name,counts in diagnostics.items() for reason,count in counts.items()]
            if rows: st.table(pd.DataFrame(rows))

            st.subheader('Ətraflı əməliyyat məlumatı')
            selected=st.date_input('Tarix · Bakı vaxtı',value=selected,key='detail_date',format='DD.MM.YYYY')
            detail_start=datetime.combine(selected,dt_time.min,tzinfo=AZ_TZ).astimezone(timezone.utc).isoformat()
            detail_end=(datetime.combine(selected,dt_time.min,tzinfo=AZ_TZ)+timedelta(days=1)).astimezone(timezone.utc).isoformat()
            detail_closed=queries.get_closed_trades(detail_start,detail_end,DB_PATH)
            if detail_closed:
                full_closed=pd.DataFrame([{'Saat':local_time(r['close_time']),'Alət':r['symbol'],'İstiqamət':direction_label(r['direction']),'Həcm':r['volume'],'Açılış qiyməti':r['open_price'],'Bağlanış qiyməti':r['close_price'],'SL':r.get('sl'),'TP':r.get('tp'),'Nəticə':r['net_profit'],'Səbəb':close_reason_label(r['close_reason']),'Strategiya':strategy_label(r['strategy'])} for r in detail_closed])
                st.table(full_closed.style.format({'Nəticə':lambda value:format_money(value,signed=True)}).map(_money_color,subset=['Nəticə']))
            else: st.caption('Seçilən tarixdə bağlanan əməliyyat yoxdur.')
            if opened:
                full_open=pd.DataFrame([{'Alət':r['symbol'],'İstiqamət':direction_label(r['direction']),'Həcm':r['volume'],'Açılış qiyməti':r['open_price'],'Nəticə':r['net_result'],'SL':r['sl'],'TP':r['tp'],'Açıq vaxt':local_time(r['open_time']),'Strategiya':r['strategy_label']} for r in opened])
                st.table(full_open.style.format({'Nəticə':lambda value:format_money(value,signed=True)}).map(_money_color,subset=['Nəticə']))
            st.subheader('Qismən bağlamalar')
            partials=queries.get_partial_closes(detail_start,detail_end,DB_PATH)
            if partials:
                partial_frame=pd.DataFrame([{'Saat':local_time(r['time']),'Alət':r['symbol'],'Həcm':r['volume'],'Qiymət':r['price'],'Nəticə':float(r['profit'] or 0)+float(r['commission'] or 0)+float(r['swap'] or 0),'Səbəb':close_reason_label(r['reason'])} for r in partials])
                st.table(partial_frame.style.format({'Nəticə':lambda value:format_money(value,signed=True)}).map(_money_color,subset=['Nəticə']))
            else: st.caption('Seçilən tarixdə qismən bağlama yoxdur.')

            st.subheader('Siqnallar')
            signals=queries.get_latest_signals(DB_PATH,50)
            if signals:
                signal_rows=[{'Saat':local_time(r['time']),'Alət':r['symbol'],'Strategiya':strategy_label(r['strategy']),'İstiqamət':direction_label(r['direction']),'Bal':r.get('score',0),'Əminlik':f'{float(r.get("confidence") or 0):.1%}','İcra edildi':'Bəli' if r.get('taken') else 'Xeyr','Səbəb':translate_message(r.get('skip_reason'))} for r in signals]
                st.table(pd.DataFrame(signal_rows))
            else: st.caption('Qeydə alınmış siqnal yoxdur.')

            st.subheader('Son əmrlər')
            commands=queries.get_recent_commands(DB_PATH,10)
            command_names={'pause':'Fasilə','resume':'Davam et','stop':'Dayandır','close_all':'Hamısını bağla','close_all_stop':'Hamısını bağla və dayan'}
            command_status={'pending':'Gözləyir','running':'İcra olunur','done':'Tamamlandı','failed':'Uğursuz','expired':'Vaxtı bitib'}
            if commands:
                st.table(pd.DataFrame([{'Vaxt':local_time(c.get('created_at') or c.get('time')),'Əmr':command_names.get(c['command'],c['command']),'Vəziyyət':command_status.get(c['status'],c['status']),'Məlumat':translate_message(c.get('message'))} for c in commands]))
            else: st.caption('Son əmr yoxdur.')

            st.subheader('Bot hadisələri')
            events=queries.get_recent_events(DB_PATH,30)
            level_names={'INFO':'MƏLUMAT','WARNING':'XƏBƏRDARLIQ','ERROR':'XƏTA','CRITICAL':'CİDDİ XƏTA'}
            source_names={'bot':'Bot','scanner':'Skaner','executor':'İcraçı','mt5_client':'MT5'}
            if events: st.table(pd.DataFrame([{'Vaxt':local_time(e['time']),'Səviyyə':level_names.get(e['level'],e['level']),'Mənbə':source_names.get(e['source'],e['source']),'Məlumat':translate_message(e['message'])} for e in events]))
            else: st.caption('Bot hadisəsi qeydə alınmayıb.')

            st.subheader('Son 30 günün nəticəsi')
            daily_stats=queries.get_daily_pnl(DB_PATH,30)
            if daily_stats:
                daily_frame=pd.DataFrame(daily_stats); daily_frame['Tarix']=pd.to_datetime(daily_frame.date)
                st.bar_chart(daily_frame.set_index('Tarix')[['pnl']].rename(columns={'pnl':'Nəticə ($)'}),height=220)
            else: st.caption('Günlük statistika hələ yoxdur.')

if __name__=='__main__': main()
