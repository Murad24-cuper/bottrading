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
        description=notifier.last_error_description or 'Təsvir mövcud deyil.'
        print(f'Telegram test failed: HTTP {status}; description: {description}' if status is not None else f'Telegram test failed: no HTTP status; description: {description}')
        return 1
    print(f'Test bildirişi Telegram-a göndərildi · HTTP {notifier.last_http_status}.')
    return 0

if __name__=='__main__': raise SystemExit(main())
