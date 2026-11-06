"""Azerbaijani dashboard labels and display formatting."""
from __future__ import annotations

from datetime import datetime, timezone
import re

from zoneinfo import ZoneInfo

AZ_TZ = ZoneInfo('Asia/Baku')

DIRECTION_LABELS = {'buy': 'Alış', 'sell': 'Satış'}
STRATEGY_LABELS = {
    'trend_pullback': 'Trend',
    'mean_reversion': 'Geri dönüş',
    'breakout': 'Qırılma',
    'volatility_scalp': 'Sürətli',
}
CLOSE_REASON_LABELS = {
    'tp': 'Hədəfə çatdı',
    'partial_tp': 'Qazancın bir hissəsi götürüldü',
    'trail': 'Qazanc qorundu (izləyən stop)',
    'early_exit': 'Erkən çıxış - risk artdı',
    'extended': 'Uzadılıb (qazanc qorunur)',
    'sl': 'Zərər həddi',
    'momentum_lost': 'Hərəkət zəiflədi',
    'stagnant': 'Yerində sayırdı',
    'time': 'Vaxt bitdi (20 dəq)',
    'session_close': 'Bazar bağlanır',
    'manual': 'Əl ilə bağlandı',
    'kill': 'Təcili dayandırma',
    'weekly_stop': 'Həftəlik limit',
    'error': 'Xəta',
}

_MESSAGE_LABELS = {
    'kill switch active': 'Təcili dayandırma aktivdir',
    'STOP kill switch is active': 'Təcili dayandırma aktivdir',
    'symbol session closes soon': 'Alətin sessiyası tezliklə bağlanır',
    'daily loss limit reached': 'Günlük zərər limiti aşılıb',
    'weekly loss limit reached': 'Həftəlik zərər limiti aşılıb',
    'maximum open positions reached': 'Açıq mövqelərin maksimum sayına çatılıb',
    'maximum positions for asset group reached': 'Aktiv qrupu üzrə mövqelərin limiti aşılıb',
    'symbol already has open position': 'Bu alətdə artıq açıq mövqe var',
    'symbol cooldown active': 'Alət üzrə gözləmə müddəti aktivdir',
    'maximum trades for symbol today reached': 'Bu gün alət üzrə əməliyyat limiti aşılıb',
    'underlying already has open position': 'Eyni əsas aktiv üzrə mövqe artıq var',
    'maximum positions for underlying group reached': 'Əsas aktiv qrupu üzrə mövqe limiti aşılıb',
    'maximum net exposure for': 'Xalis valyuta riski limiti aşılıb:',
    'stop-loss is required': 'Zərər dayandırma əmri tələb olunur',
    'take-profit is required': 'Mənfəət hədəfi tələb olunur',
    'invalid SL/TP side': 'Zərər həddi və hədəf qiymətin düzgün tərəfində deyil',
    'risk/reward below minimum': 'Risk/mükafat nisbəti minimumdan aşağıdır',
    'cost-to-target ratio too high': 'Xərc/hədəf nisbəti çox yüksəkdir',
    'margin usage cap exceeded': 'Marja istifadəsi limiti aşılıb',
    'min lot exceeds risk': 'Minimum lot icazə verilən riskdən çoxdur',
    'consecutive cycle error limit reached': 'Ardıcıl dövr xətalarının limiti aşılıb',
    'shadow mode': 'Sınaq rejimidir; əməliyyat göndərilmir',
    'strategy not allowed live': 'Strategiyaya canlı rejimdə icazə yoxdur',
    'scanner candidate limit reached': 'Skaner namizədlərinin limitinə çatılıb',
    'expected value is non-positive': 'Gözlənilən nəticə xərclərdən sonra müsbət deyil',
    'below scanner.min_score': 'Skaner balı minimum həddən aşağıdır',
    'Refused open:': 'Əməliyyat açılmadı:',
    'Refused close:': 'Əməliyyat bağlanmadı:',
    'Refused partial close:': 'Qismən bağlama rədd edildi:',
    'Refused SL/TP modification:': 'Zərər həddi/mənfəət hədəfi dəyişdirilmədi:',
    'order_calc_margin failed:': 'Marjanın hesablanması alınmadı:',
    'order_send rejected': 'Broker əmri rədd etdi',
    'order_send failed:': 'Brokerə əmr göndərilmədi:',
    'account_info failed:': 'Hesab məlumatı alınmadı:',
    'MT5 initialize failed': 'MT5 terminalını başladmaq alınmadı',
    'MT5 trade_allowed=false': 'MT5-də avtomatik ticarət icazəsi bağlıdır',
    'MT5 health or algorithmic trading permission blocks new entries': 'MT5 sağlamlığı və ya avtomatik ticarət icazəsi yeni əməliyyatları bloklayır',
    'maximum trades today reached': 'Gündəlik əməliyyat limitinə çatılıb',
    'PC UTC saatı MT5 server vaxtından': 'Kompüterin UTC saatı MT5 server vaxtından',
    'Saat uyğunluğu yoxlanıla bilmədi': 'Saat uyğunluğu yoxlanıla bilmədi',
    'MT5 login failed:': 'MT5 hesabına giriş alınmadı:',
    'stale tick / market closed': 'Qiymət köhnədir və ya bazar bağlıdır',
    'symbol is not enabled for full trading': 'Alətdə tam ticarətə icazə yoxdur',
    'spread too high relative to recent volatility': 'Spread son dəyişkənliyə görə yüksəkdir',
    'spread_too_large_vs_target': 'Spread hədəfə görə yüksəkdir',
    'required_timeframe_missing': 'Tələb olunan zaman intervalı yoxdur',
    'market_regime_trending_up': 'Bazar yuxarı trenddədir',
    'market_regime_trending_down': 'Bazar aşağı trenddədir',
    'market_regime_high_volatility': 'Bazarda dəyişkənlik yüksəkdir',
    'market_regime_quiet': 'Bazar sakitdir',
    'price_inside_bollinger_bands': 'Qiymət Bollinger zolaqlarının daxilindədir',
    'rsi_confirmation_failed': 'RSI təsdiqi alınmadı',
    'pullback_not_confirmed': 'Geri çəkilmə təsdiqlənmədi',
    'higher_timeframe_trend_not_aligned': 'Yuxarı zaman intervalındakı trend uyğun deyil',
    'adx_below_minimum': 'ADX minimum həddən aşağıdır',
    'atr_expansion_below_minimum': 'ATR artımı minimum həddən aşağıdır',
    'range_not_broken': 'Qiymət diapazonu qırılmayıb',
    'tick_volume_below_minimum': 'Tick həcmi minimum həddən aşağıdır',
    'volatility_below_minimum': 'Dəyişkənlik minimum həddən aşağıdır',
    'rsi_not_overbought': 'RSI həddən artıq alış zonasını göstərmir',
    'rsi_not_oversold': 'RSI həddən artıq satış zonasını göstərmir',
    'indicator_values_not_ready': 'İndikator məlumatları hələ hazır deyil',
    'missing_required_timeframe': 'Tələb olunan zaman intervalı yoxdur',
    'missing_M15_history': 'M15 tarixçəsi yoxdur',
    'missing_M1_M5_history': 'M1 və M5 tarixçəsi yoxdur',
    'insufficient_range_history': 'Diapazon üçün tarixçə kifayət etmir',
    'atr_not_ready': 'ATR məlumatı hələ hazır deyil',
    'no_directional_momentum': 'İstiqamətli impuls yoxdur',
    'not_near_support_or_resistance': 'Qiymət dəstək və ya müqavimət səviyyəsinə yaxın deyil',
}

_REPLACEMENTS = (
    ('Scan total=', 'Skanlama · cəmi='),
    ('Connected to account', 'Hesaba qoşuldu'),
    ('margin mode=', 'marja rejimi='),
    ('MT5 algorithmic trading is disabled in terminal settings', 'MT5 terminalında alqoritmik ticarət söndürülüb'),
    ('Modify SL/TP ticket=', 'SL/TP dəyişdirildi · bilet='),
    ('Partial close ticket=', 'Qismən bağlandı · bilet='),
    ('Close-all requested reason=', 'Hamısını bağlama istənildi · səbəb='),
    ('Close accepted ticket=', 'Bağlama qəbul edildi · bilet='),
    ('No changes', 'Dəyişiklik yoxdur'),
    ('success=False', 'uğurlu deyil'),
    ('success=True', 'uğurlu'),
    ('reason=partial_tp', 'səbəb=Qazancın bir hissəsi götürüldü'),
    ('reason=sl', 'səbəb=Zərər həddi'),
    ('reason=tp', 'səbəb=Hədəfə çatdı'),
    ('scanned=', 'yoxlanıb='),
    ('complete=', 'tamamlandı='),
    ('stage1_passed=', 'ticarətə uyğun='),
    ('top_movers_selected=', 'seçilmiş alət='),
    ('analysed=', 'təhlil edilib='),
    ('signals=', 'siqnallar='),
    ('seconds=', 'saniyə='),
    ('stage1_rejections=', 'imtina səbəbləri='),
    ('strategy_diagnostics=', 'strategiya qeydləri='),
    ('Open bot positions by asset group:', 'Açıq bot mövqeləri, aktiv qrupları üzrə:'),
    ('Bot started mode=', 'Bot başladı · rejim='),
    ('bot exiting reason=', 'Bot dayandı · səbəb='),
    ('Weekly drawdown stop reached:', 'Həftəlik kapital limiti aşıldı:'),
    ('Supervisor restart limit reached:', 'Nəzarətçinin yenidən başlatma limiti doldu:'),
    ('Restarting bot after exit code', 'Bot yenidən başladılır · çıxış kodu'),
    ('Bot child started PID=', 'Bot prosesi başladı · PID='),
    ('Supervisor started PID=', 'Nəzarətçi başladı · PID='),
    ('account=', 'hesab='),
    ('equity=', 'kapital='),
    ('enabled=', 'aktiv='),
    ('allowed_live=', 'canlı rejimə icazəli='),
    ('Processed command', 'Əmr icra edildi'),
    ('Close accepted ticket=', 'Bağlama qəbul edildi · bilet='),
    ('Synced closed ticket=', 'Bağlanan əməliyyat sinxronlaşdırıldı · bilet='),
    ('Opened ', 'Açıldı: '),
    (' ticket=', ' · bilet='),
    (' volume=', ' · həcm='),
    (' reason=', ' · səbəb='),
    (' profit=', ' · nəticə='),
    (' success=', ' · uğurlu='),
    (' error=', ' · xəta='),
    (' seconds=', ' saniyə='),
    ('forex', 'valyuta'),
    ('metals', 'metallar'),
    ('indices', 'indekslər'),
    ('energy', 'enerji'),
    ('crypto', 'kripto'),
    ('stocks', 'səhmlər'),
    ('hedging', 'hedcinq'),
    ('netting', 'netinq'),
    ('trend_pullback', 'Trend'),
    ('mean_reversion', 'Geri dönüş'),
    ('volatility_scalp', 'Sürətli'),
    ('breakout', 'Qırılma'),
)


def direction_label(value: str | None) -> str:
    return DIRECTION_LABELS.get(str(value or '').lower(), 'Naməlum')


def strategy_label(value: str | None) -> str:
    return STRATEGY_LABELS.get(str(value or '').lower(), 'Digər')


def close_reason_label(value: str | None) -> str:
    return CLOSE_REASON_LABELS.get(str(value or '').lower(), 'Digər')


def format_money(value: float | int | None, signed: bool = False) -> str:
    if value is None:
        return '—'
    amount = float(value)
    return f'{amount:+,.2f} $' if signed else f'{amount:,.2f} $'


def format_duration(minutes: float) -> str:
    total = max(0, int(minutes))
    hours, mins = divmod(total, 60)
    if hours:
        return f'{hours} saat' + (f' {mins} dəq' if mins else '')
    return f'{mins} dəq'


def local_time(value: str | datetime, fmt: str = '%H:%M') -> str:
    try:
        parsed = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        parsed = parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)
        return parsed.astimezone(AZ_TZ).strftime(fmt)
    except (ValueError, TypeError):
        return str(value or '')


def translate_message(message: str | None) -> str:
    """Translate known bot messages while preserving symbols and numeric details."""
    value = str(message or '')
    for source, target in sorted(_MESSAGE_LABELS.items(), key=lambda pair: len(pair[0]), reverse=True):
        value = value.replace(source, target)
    value = re.sub(r'\bDEMO\b', 'DEMO', value)
    for source, target in _REPLACEMENTS:
        value = value.replace(source, target)
    return value
