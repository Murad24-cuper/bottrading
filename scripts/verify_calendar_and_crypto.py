"""Read-only check of the MT5 calendar export and weekend crypto quotes."""
from pathlib import Path
from datetime import datetime,timezone
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.config import load_settings
from src.mt5_client import MT5Client
from src.news import parse_calendar,terminal_calendar_path
from src.symbols import SymbolService
from src.time_utils import mt5_epoch_to_utc
from src.time_utils import detect_server_utc_offset,server_utc_offset


def main():
    settings=load_settings()
    if settings.config['account']['mode']!='demo' or settings.allow_real:
        raise SystemExit('Read-only diagnostics require DEMO mode and ALLOW_REAL=false.')
    now=datetime.now(timezone.utc)
    with MT5Client(settings) as client:
        mt5=client.mt5; account=mt5.account_info()
        if account is None or account.trade_mode!=getattr(mt5,'ACCOUNT_TRADE_MODE_DEMO',0):
            raise SystemExit('Refusing diagnostics: connected account is not DEMO.')
        path=terminal_calendar_path(mt5)
        print('Server UTC offset:',server_utc_offset(mt5))
        print('Calendar file:',str(path) if path else 'terminal data path unavailable')
        if path and path.is_file():
            events,modified=parse_calendar(path)
            age=(now-modified).total_seconds()/60 if modified else float('inf')
            print(f'Calendar freshness: {age:.1f} min; parsed events={len(events)}')
            upcoming=sorted((event for event in events if event.time>=now),key=lambda event:event.time)[:5]
            for event in upcoming:
                print(f'{event.time.isoformat()} · {event.currency} · {event.importance} · {event.name}')
        else: print('Calendar freshness: missing; no upcoming events can be shown.')
        service=SymbolService(mt5,settings)
        for alias in ('BTCUSD','ETHUSD'):
            symbol=service.resolve_alias(alias)
            if not symbol:
                print(f'{alias}: alias unresolved')
                continue
            selected=bool(mt5.symbol_select(symbol,True)); info=mt5.symbol_info(symbol); tick=mt5.symbol_info_tick(symbol)
            raw=(getattr(tick,'time_msc',0)/1000 if tick and getattr(tick,'time_msc',0) else getattr(tick,'time',0) if tick else 0)
            converted=mt5_epoch_to_utc(raw,mt5) if raw else None
            age=(now-converted).total_seconds() if converted else None
            tradable,reason=service.is_tradable(symbol,check_session=False)
            print(f'{alias}->{symbol}: selected={selected} trade_mode={getattr(info,"trade_mode",None)} raw_tick={datetime.fromtimestamp(raw,timezone.utc).isoformat() if raw else None} tick_utc={converted.isoformat() if converted else None} age_s={round(age,1) if age is not None else None} tradable={tradable} reason={reason}')
    return 0


if __name__=='__main__': raise SystemExit(main())
