# Bazar ertəsi yoxlamaları

Bazar ertəsi 07:00 UTC-dən sonra, bot DEMO hesabında işləyərkən:

1. `python scripts/self_test.py` — DEMO qoruması, `.env` izlənməməsi, heartbeat, MT5 icazələri, STOP faylı və panel yoxlamaları hamısı yaşıl olmalıdır.
2. `python scripts/health_check.py` — heartbeat, bağlantı, dövr müddəti, skan edilən fokus alətləri, açıq mövqelər və son WARNING/ERROR/CRITICAL hadisələrinə baxın.
3. Dashboard-da ilk 2 saat ərzində siqnalları strategiya və alətə görə yoxlayın. Hər açıq mövqedə SL və TP olmalıdır; eyni simvolda maksimum 1 mövqe.
4. 2 saatlıq pəncərədə ən azı 5 fərqli simvol və 2 qrupdan əməliyyat görünüb-görünmədiyini yoxlayın. Heç bir ticarəti bu kvotanı tamamlamaq üçün məcbur etməyin.
5. Kəşf əməliyyatlarının sayı, risk ölçüsü və ayrı dashboard cədvəlini yoxlayın. REAL hesabda bu rejim avtomatik bağlı olmalıdır.
6. Təqvim ixracının fayl vaxtı 2 saatdan yeni olduğunu və yüksək təsirli ilk USD/EUR/GBP/JPY hadisəsi ətrafında yeni girişlərin bloklandığını yoxlayın.
7. Hər siqnal üçün `signals.features` içində checklist, qonşu yaddaş, ehtimal, EV və təklif olunan ölçünün yazıldığını yoxlayın. Beyin PASS almadan `brain.enabled` aktiv etməyin.
8. `bot_events`-də dövr müddəti, tarixçə yeniləmələri və ERROR/CRITICAL hadisələrini izləyin.

Yoxlama əmrləri layihə qovluğunda:

```powershell
.\.venv\Scripts\python.exe scripts/self_test.py
.\.venv\Scripts\python.exe scripts/health_check.py
.\.venv\Scripts\python.exe scripts/check_connection.py
.\.venv\Scripts\python.exe -m pytest -q
```
