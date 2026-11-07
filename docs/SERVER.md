# Serverdə işə salma və idarəetmə

Bot və panel EC2 serverində işləyir. Serverdə MT5 terminalı Wine ilə açılır;
Windows kompüterində botu və terminalı eyni vaxtda işlətməyin. Hesab `DEMO`
olmalı və `.env`-də `ALLOW_REAL=false` qalmalıdır. `.env` yalnız serverdə
`/opt/tradingbot/.env` yolundadır; onu git-ə və Docker image-ə daxil etməyin.

## Panel

PowerShell-də layihə qovluğundan `.scriptsserver.ps1 tunnel` işlədin və
`http://127.0.0.1:8501` ünvanını açın. SSH tuneli açıq qalmalıdır.

## Başlatma və dayandırma

- `.scriptsserver.ps1 status` — konteyner statusu
- `.scriptsserver.ps1 health` — bot/MT5 sağlamlıq yoxlaması
- `.scriptsserver.ps1 logs` — son konteyner jurnalları
- `.scriptsserver.ps1 start` — STOP markerlərini götürüb xidməti başladır
- `.scriptsserver.ps1 stop` — botu dayandırır və konteynerləri saxlayır;
  brokerdəki mövqelər açıq qala bilər

Paneldə Start/Stop idarəetməsi də mövcuddur. `STOP` faylı yeni ticarəti
bloklayır. `data/supervisor.stop` supervisora dayandırma istəyidir.
Transfer zamanı Windows layihəsində də `runtime.location: server` yazılır;
bu guard yerli botun yenidən başladılmasının qarşısını alır. Yalnız server
konteynerində `BOT_LOCATION=server` verildikdə server botu başlayır.

## VNC və MT5 quraşdırılması

Serverdə VNC yalnız loopback üzərindədir. Tuneli `.scriptsserver.ps1 vnc-tunnel`
ilə açın və VNC Viewer-də `127.0.0.1:5900` qoşulun. Əgər terminal qurulmayıbsa,
Firefox XM rəsmi MT5 səhifəsini göstərir. Oradan MT5 for PC yükləyin, Wine ilə
quraşdırıcını açın və standart `C:\Program Files` yoluna quraşdırın; login
dialoqunda DEMO hesabını istifadə edin, Algo Trading-i aktiv edin. Terminal
əlçatan olandan sonra serverdə `scripts/check_connection.py` və
`scripts/health_check.py` yoxlamalarını aparın. Parolu jurnal və ekranlarda
göstərməyin.

## Yeniləmə və nasazlıq

`.scriptsdeploy.ps1` lokal testləri işlədir, yalnız git-dəki kodu arxivləşdirib
serverə köçürür, sonra konteynerləri yenidən qurur. `.env`, `data/` və `logs/`
arxivə daxil deyil. Dashboard tunelini işlətdikdən sonra URL lokaldır; serverin
8501 və 5900 portları internetə açılmır. Bağlantı alınmırsa EC2 reachability,
key path və `ssh -v` nəticəsini yoxlayın.

## Məlumat və server xərci

DB, tarixçə və beyin faylları `/opt/tradingbot/data`, jurnallar
`/opt/tradingbot/logs` qovluğundadır. Server xərclərini azaltmaq üçün botu
dayandırın, sonra AWS Console-da instance-i Stop edin; EBS storage xərci davam
edəcək. Tam silmədən əvvəl ehtiyat nüsxə alın.

Local data-nı silmək qərarını 24 saatlıq uğurlu server işindən sonra özünüz
verin. Aşağıdakı əmrlər geri qaytarılmır; bu sənəd faylları silmir:

```powershell
Remove-Item -Recurse -Force .\data
Remove-Item -Recurse -Force .\logs
Remove-Item -Force .\.env
```
