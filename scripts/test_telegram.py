"""Send one explicit Telegram connectivity test without exposing credentials."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.config import load_settings
from src.notify import TelegramNotifier

def main():
    settings=load_settings()
    notifier=TelegramNotifier(rate_limit_minutes=settings.config['notify']['rate_limit_minutes'])
    if not notifier.enabled:
        print('Bildirişlər söndürülüb. .env daxilində Telegram məlumatlarını doldurun.')
        return 1
    notifier.send('manual_test','✅ Ticarət botu Telegram bildiriş testi uğurludur.')
    notifier.queue.join()
    if notifier.failures:
        status=notifier.last_http_status
        print(f'Telegram test failed: HTTP {status}' if status is not None else 'Telegram test failed: no HTTP status (network/API unreachable)')
        return 1
    print('Test bildirişi Telegram-a göndərildi.')
    return 0

if __name__=='__main__': raise SystemExit(main())
