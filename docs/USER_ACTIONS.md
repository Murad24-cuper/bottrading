# İstifadəçinin etməli olduğu addımlar

## Telegram bildirişi

Botun Telegram-a qoşulmasını yoxlamaq üçün layihə qovluğunda bu əmri bir dəfə
işlədin:

```powershell
.\.venv\Scripts\python.exe scripts\test_telegram.py
```

Tokeni və chat ID-ni heç kimə göndərməyin. Test `chat not found` qaytararsa:

1. Telegram-da botla şəxsi söhbət açın və **Start** düyməsinə basın; qrupdursa,
   botu qrupa əlavə edin və qrupda bir mesaj yazın.
2. Brauzerdə `https://api.telegram.org/bot<TOKEN>/getUpdates` ünvanını açın.
   `<TOKEN>` yerinə bot tokenini yalnız öz brauzerinizdə daxil edin.
3. Cavabda son mesajın `chat` obyektindəki `id` dəyərini tapın. Qrup ID-si çox
   vaxt mənfi rəqəm olur. Tokeni və cavabın qalan hissəsini paylaşmayın.
4. Bu ID-ni `.env` faylında `TELEGRAM_CHAT_ID` dəyərinə əl ilə yazın və test
   əmrini yenidən başladın.

## MT5 təqvim ixracatçısı (istəyə bağlı)

Bot MT5 terminalının `MQL5\Files\calendar_events.csv` faylını oxuyur. Yeni
versiyada fayl yoxdursa və ya köhnədirsə, bot HTTPS təqvim keşindən istifadə
edir. İxracatçını əlavə etmək üçün MT5-də **File → Open Data Folder** seçin,
`MQL5\Files` qovluğunu açın və ixracatçının CSV-ni həmin yerə yazdığını yoxlayın.
CSV vaxtları UTC olmalıdır; paneldə aktiv mənbə və yenilənmə yaşı göstərilir.

## Windows fasiləsiz işləmə

- `scripts\install_autostart.ps1` cari Windows istifadəçisi üçün
  `XMTradingBotSupervisor` logon task-ını yaradır. Task Scheduler Library-də
  həmin adı yoxlayın.
- Windows **Settings → System → Power & battery → Screen and sleep** bölməsində
  bot işləyən vaxt kompüterin yuxuya getməməsini seçin. Supervisor da işləyərkən
  yuxunu bloklayır; kompüter sönülü və ya enerji kəsilmiş olsa işləyə bilməz.
- Avtomatik giriş yalnız etibar etdiyiniz şəxsi kompüterdə istifadə olunmalıdır.
  Windows AutoAdminLogon qurulması hesab parolunu sistemdə saxlayır; bunu aktiv
  etməzdən əvvəl fiziki giriş təhlükəsizliyini özünüz qiymətləndirin.
- Paneldən **Botu dayandır** seçəndə supervisor da dayanır. Yenidən başlatmaq
  üçün paneldə **Botu başlat** düyməsini basın. `STOP` faylı fasilə üçündür;
  silinməsi botu özü başlamır.
