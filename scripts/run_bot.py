"""Run the configured live/shadow loop. No order is sent in shadow mode."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.config import load_settings
from src.bot import TradingBot

def main():
    try: settings=load_settings()
    except ValueError as exc: raise SystemExit(f'Configuration error: {exc}')
    bot=TradingBot(settings)
    bot.run_forever()
    return 0

if __name__=='__main__': raise SystemExit(main())
