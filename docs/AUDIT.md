# Müstəqil Kod və Sistem Auditi Hesabatı (Independent Read-Only Audit)

**Tarix:** 2026-11-09  
**Rejim:** Read-Only Audit (kod, konfiqurasiya və məlumatlara toxunulmayıb; MT5 terminalına qoşulmayıb; `.env` oxunmayıb).  
**Mühit:** `.venv-audit` (ayrılmış virtual mühit).

---

## 1. İcra İcmalı (Executive Summary)

Bu müstəqil audit ticarət botunun (`tradingbot`) kod bazasının etibarlılığını, risk idarəetməsini, icra təhlükəsizliyini, vaxt mexanizmlərini, maşın öyrənməsi/arxitektur səhvlərini və dayanıqlığını yoxlamaq məqsədilə aparılmışdır.

### Aşkarlanmış Problemlərin Statistikası

| Dərəcə (Severity) | Say | Təsvir |
|:---|:---:|:---|
| **CRITICAL** | 5 | Hesabın birbaşa sıradan çıxmasına (margin call / wipeout), nizamlanmayan risqlərə və ya ticarətin tam dayanmasına səbəb ola biləcək xətalar. |
| **HIGH** | 5 | Riskin məhdudlaşdırılması qaydalarının pozulması, model sızmaları və ya kritik əməliyyat bloklamaları. |
| **MEDIUM** | 6 | Məntiqi xətalar, təhlükəsizlik boşluqları, saat/sessiya sapmaları və test çatışmazlıqları. |
| **LOW** | 2 | İcra dayanıqlığına xırda təsirlər və istifadəsiz köhnə kodlar. |
| **CƏMİ** | **18** | |

---

## 2. Ən Kritik 5 Problem (Top 5 Issues)

1. **[CRIT-01] Stop-Loss-suz Qalan Mövqelər Serverdə Qorumasız Buraxılır:** Bot serverdə stop-loss təyin edilmədiyini aşkar etdikdə yeni girişləri bloklayır, lakin açıq mövqeyə təcili SL qoymur və onu bağlamır. Bazar kəskin əksinə getdikdə hesab tam sıfırlana bilər.
2. **[CRIT-02] `MT5CallProxy` Hər Sorğuda Thread Yaradır və MT5 Thread-Safe Deyil:** Hər bir MT5 funksiya çağırışı üçün yeni OS daemon thread başladılır. MT5 C-API thread-safe olmadığı üçün və gecikmələrdə thread-lər öldürülə bilmədiyi üçün IPC korlanır, proses donur və nəzarətçi (watchdog) botu məcburi dayandırır (`ERROR_LEDGER.md`-dəki 6 izahsız donmanın əsas səbəbi).
3. **[CRIT-03] Komissiyasız və Yeni Hesablarda Ticarətin Qapalı Dairə (Deadlock) ilə Bloklanması:** Komissiya yalnız keçmiş bağlanan əməliyyatlardan hesablandığı üçün yeni və ya komissiyasız (0.0 USD) hesablarda komissiya həmişə `unknown` qalır və `cost_map` bütün girişləri daimi bloklayır.
4. **[CRIT-04] Requote / Price Change Zamanı Yenidən Göndərilən Sifarişlərdə Həcm və Risk Yenidən Hesablanmır:** Qiymət dəyişdikdə yeni qiymət götürülür, lakin SL məsafəsi artarsa və ya SL/TP tərəfi pozularsa həcm yenidən hesablanmır; nəticədə risk limiti (0.25%) aşıla bilər.
5. **[CRIT-05] Qismən İcra (IOC Partial Fill) Mövqe İzləməsini Pozur və Mövqeni DB-də Əbədi Açıq Saxlayır:** Əgər broker sifarişin yalnız bir hissəsini icra edərsə, DB-yə faktiki icra deyil, ilkin tələb olunan həcm yazılır. Nəticədə mövqe tam bağlandıqda sistem bunu natamam qapanma hesab edir və mövqe DB-də əbədi açıq qalaraq risk limitlərini kəsir.

---

## 3. Avtomatlaşdırılmış Alətlərin Nəticələri (Part 1 Summary)

Xam alət çıxışları `docs/audit_raw/` qovluğunda saxlanılmışdır:

1. **Ruff (`docs/audit_raw/ruff.txt`):**
   - 648 xəta tapıldı (507-si avtomatik düzəldilə biləndir). Əsasən import sırası (I001), sətir uzunluğu, istifadə olunmayan dəyişənlər və formatlama uyğunsuzluqlarıdır.
2. **Mypy (`docs/audit_raw/mypy.txt`):**
   - 62 mənbə faylından 10-da 30 tip xətası aşkar edildi.
   - Ən vacib tip xətaları: `src/patterns/fibonacci.py:23,25` (`None` ilə müqayisə nəticəsində potensial runtime `TypeError`), `src/costs.py:54` (`object` üzərində əməliyyat), `src/backtest/engine.py:304` (`set` indeksləməsi xətası).
3. **Bandit (`docs/audit_raw/bandit.txt`):**
   - 7,821 sətir kod skan edildi. 0 High, 15 Medium, 19 Low təhlükəsizlik xətası tapıldı.
   - Medium məsələlər: `src/news.py:86` (B314 - XML Entity hücumlarına həssas `xml.etree.ElementTree.fromstring`), `src/news.py:164` (B310 - `urllib.request.urlopen` sxem yoxlaması), `src/db.py` (B608 - SQL sorğularının f-string ilə dinamik yığılması).
4. **Pip-audit (`docs/audit_raw/pip_audit.txt`):**
   - `requirements.txt` daxilindəki asılılıqlar yoxlanıldı: Məlum təhlükəsizlik boşluğu (vulnerability) aşkarlanmadı (`No known vulnerabilities found`).
5. **Vulture (`docs/audit_raw/vulture.txt`):**
   - `--min-confidence 80` ilə işlədildikdə 0 ölü kod tapıldı.
   - Standart 60% konfidensiyada 53 potensial istifadəsiz element (köhnə modellər `TradeRequest`, `Position`, köhnə köməkçi funksiyalar) aşkar edildi.
6. **Pytest və Coverage (`docs/audit_raw/pytest_cov.txt`):**
   - 273 testdən **269-u keçdi, 4 test uğursuz oldu (FAILED)**.
   - Uğursuz olan 4 test (`test_brain_dataset.py`, `test_history.py` x3) Windows AppLocker / WDAC siyasətinin `pyarrow._parquet.pyd` DLL faylını bloklaması səbəbindən baş verdi.
   - **60%-dən aşağı örtüyü (coverage) olan modullar:**
     - `src/brain/dataset.py`: **14%**
     - `src/dashboard/app.py`: **20%**
     - `src/strategies/mean_reversion.py`: **34%**
     - `src/executor.py`: **45%** (Kritik icra modulunun yarıdan çoxu test edilmir!)
     - `src/market_data.py`: **49%**
   - Ümumi kod örtüyü: **75%**.

---

## 4. Ətraflı Audit Nəticələri (Detailed Findings)

### CRITICAL SEVERITY

#### [CRIT-01] Stop-loss-suz qalan açıq mövqelər üçün avtomatik qoruyucu icra mexanizmi yoxdur
- **Fayl və Sətir:** [src/bot.py#L181-L195](file:///c:/Users/Murad/Desktop/tradingbot/src/bot.py#L181-L195), [src/executor.py#L73-L93](file:///c:/Users/Murad/Desktop/tradingbot/src/executor.py#L73-L93)
- **Problem nədir:**
  `executor.open_trade()` funksiyası brokerə `TRADE_ACTION_DEAL` göndərərkən `sl` parametrini ötürür, lakin əməliyyat açıldıqdan sonra serverdə mövqenin (`positions_get`) stop-loss parametrinin həqiqətən təyin olunduğunu təsdiqləmir. Daha pisi, `bot._health()` funksiyasında `missing_sl` yoxlaması stop-loss-suz mövqe aşkar etdikdə yalnız `_entries_health_blocked = True` edir, CRITICAL hadisə qeyd edir və teleqrama xəbərdarlıq göndərir. Sistem bu açıq mövqeyə nə təcili stop-loss yerləşdirmir (`modify_sl_tp`), nə də onu dərhal bağlamır.
- **Hesaba Təsiri (Risk):**
  Broker stop parametrini qəbul etmədikdə (məsələn, ECN/STP market execution rejimində birbaşa SL icazə verilmədikdə və ya kotirovka sürüşməsində), mövqe bazarda tamamilə **stopsuz və müdafiəsiz** qalır. İnternet kəsildikdə və ya qəfil xəbər partlayışında mövqe bütün depoziti məhv edə bilər (margin call / stop out).
- **Tövsiyə olunan Həll:**
  1. `open_trade()` uğurla icra edildikdən dərhal sonra `positions_get(ticket=ticket)` yoxlanılmalı, əgər `p.sl == 0` olarsa, təcili `TRADE_ACTION_SLTP` göndərilməlidir.
  2. `bot._health()` daxilində `missing_sl` tapıldıqda dərhal `executor.modify_sl_tp()` ilə ilkin stop təyin edilməli, bu da alınmazsa, `executor.close_position(ticket, 'kill')` çağırılaraq qorunmayan mövqe bazardan çıxarılmalıdır.

---

#### [CRIT-02] `MT5CallProxy` qeyri-sabit şəkildə thread generasiya edir və MT5 IPC asılmalarına səbəb olur
- **Fayl və Sətir:** [src/mt5_client.py#L12-L31](file:///c:/Users/Murad/Desktop/tradingbot/src/mt5_client.py#L12-L31), [src/supervisor.py#L20-L35](file:///c:/Users/Murad/Desktop/tradingbot/src/supervisor.py#L20-L35), [config.yaml#L198](file:///c:/Users/Murad/Desktop/tradingbot/config.yaml#L198), [docs/ERROR_LEDGER.md#L18-L30](file:///c:/Users/Murad/Desktop/tradingbot/docs/ERROR_LEDGER.md#L18-L30)
- **Problem nədir:**
  `MT5CallProxy` hər bir MT5 funksiya çağırışı üçün yeni bir daemon OS thread-i yaradır (`threading.Thread(target=invoke, daemon=True).start()`). Dəqiqədə yüzlərlə çağırış edilir. MetaTrader 5 Python kitabxanası rəsmi sənədləşməsində **thread-safe deyil**. Əgər MT5 funksiyası (məsələn, `copy_rates_from_pos` və ya `initialize`) C səviyyəsində asılı qalarsa, `result.get(timeout=20)` timeout xətası atır, lakin arxa plandakı thread C-API daxilində asılı qalır və öldürülə bilmir. Sonrakı thread-lər eyni IPC kanalına daxil olduqda MT5 terminalı tam donur. Bundan əlavə, `_health()` və ya `ensure_connected()` ardıcıl 5 çağırışda timeout alarsa (5 × 20s = 100s), bu müddət nəzarətçinin `supervisor.hang_seconds: 90` limitini aşır. Nəticədə `ERROR_LEDGER.md`-dəki 6 həll olunmamış watchdog hadisəsi (#9, #10, #18, #19, #20, #21) baş verir və nəzarətçi botu öldürür.
- **Hesaba Təsiri (Risk):**
  Bot dövriyyəsi donur; açıq mövqelərin dinamik idarə edilməsi (breakeven, trailing stop, vaxt çıxışı, sessiya çıxışı) dayanır. Watchdog prosesi `TerminateProcess` ilə qəfil öldürdükdə MT5 IPC kanalı zədələnmiş qalır və növbəti child proses də yenidən başlatma dövrünə (crash loop) düşür.
- **Tövsiyə olunan Həll:**
  Hər çağırış üçün müstəqil thread açmaq əvəzinə, MT5 ilə əlaqə tək bir worker proses/thread üzərindən növbə (queue) ilə aparılmalıdır. `supervisor.hang_seconds` 90 saniyədən ən azı 180-240 saniyəyə qaldırılmalı və `_health()` daxilində ilk MT5 timeout-dan sonra bütün mövqelər üzrə 20 saniyəlik dövrlər təkrarlanmadan dövrədən tez çıxılmalıdır.

---

#### [CRIT-03] Komissiyasız hesablar və yeni hesablar üçün "Cost Gate" ticarəti daimi bloklayır (Catch-22 Deadlock)
- **Fayl və Sətir:** [src/market_data.py#L75-L84](file:///c:/Users/Murad/Desktop/tradingbot/src/market_data.py#L75-L84), [src/scanner.py#L424-L425](file:///c:/Users/Murad/Desktop/tradingbot/src/scanner.py#L424-L425), [src/costs.py#L24-L25](file:///c:/Users/Murad/Desktop/tradingbot/src/costs.py#L24-L25)
- **Problem nədir:**
  `market_data.get_cost_estimate` broker komissiyasını öyrənmək üçün son 30 günün bağlanmış `deals` tarixçəsini axtarır. Sətir 81: `if commission: samples.append(commission/float(deal.volume))`. Əgər hesab yenidirsə (heç bir ticarət olmayıb) və ya broker hesabı **sıfır komissiyalıdırsa** (yalnız spread tətbiq edilən standart/demo hesablar):
  1. `samples` siyahısı həmişə boş qalır;
  2. `commission_per_lot` dəyəri `None` olur və `commission_known = False` qayıdır;
  3. `scanner.py:424` şərti işə düşür: `elif not cost.get('commission_known', False): cost_gate_reason = 'cost map commission unknown'`;
  4. Bütün ticarət siqnalları qeyd-şərtsiz rədd edilir. Bot heç vaxt əməliyyat aça bilmədiyi üçün tarixçədə heç vaxt deal yaranmır və sistem sonsuz çıxılmaz vəziyyətə düşür.
- **Hesaba Təsiri (Risk):**
  Bot normal rejimdə heç bir ticarət aça bilmir; sistem tamamilə iflic olur.
- **Tövsiyə olunan Həll:**
  1. `config.yaml` daxilində `cost_model.default_commission_per_lot: 0.0` parametri əlavə olunmalıdır.
  2. Əgər tarixçədə komissiyası 0 olan deal-lar varsa, bu `commission_known = True` və `commission = 0.0` kimi qəbul edilməlidir (hazırda `if commission:` yoxlaması sıfırı `False` sayır).

---

#### [CRIT-04] Requote zamanı həcm və risk yenidən hesablanmadan təkrar sifariş göndərilir
- **Fayl və Sətir:** [src/executor.py#L75-L79](file:///c:/Users/Murad/Desktop/tradingbot/src/executor.py#L75-L79)
- **Problem nədir:**
  Broker `TRADE_RETCODE_REQUOTE` (10004) və ya `TRADE_RETCODE_PRICE_CHANGED` (10020) qaytardıqda, icraçı yeni qiyməti `tick.ask / bid`-dən götürür və birbaşa təkrar `order_send(req)` edir. Bu zaman:
  - Yeni qiymətin `sl_price` və `tp_price` arasında olub-olmaması yoxlanılmır;
  - `calc_volume` yenidən çağırılmır. Əgər alış əməliyyatında qiymət yuxarı sıçrayıbsa, SL-ə qədər olan məsafə böyüyüb və köhnə lot həcmi ilə girildikdə itki riski büdcədən xeyli çox olacaq.
- **Hesaba Təsiri (Risk):**
  Sürətli bazarda requote zamanı ticarətə daxil olarkən faktiki stop itkisi təyin olunmuş 0.25% risk tavanını aşır və hesab planlaşdırıldığından artıq zərərə məruz qalır.
- **Tövsiyə olunan Həll:**
  Requote zamanı yeni qiymətlə stop arasındakı məsafə yoxlanılmalı, `calc_volume` yenidən çağırılmalı və yalnız `new_volume >= volume` olduğu halda (və ya həcm azaldılaraq) sifariş yenilənməlidir; əks halda sifariş ləğv edilməlidir.

---

#### [CRIT-05] Broker tərəfindən qismən icra (Partial Fill) ticarət həcmini və DB statusunu daimi pozur
- **Fayl və Sətir:** [src/executor.py#L81-L93](file:///c:/Users/Murad/Desktop/tradingbot/src/executor.py#L81-L93), [src/executor.py#L391-L402](file:///c:/Users/Murad/Desktop/tradingbot/src/executor.py#L391-L402)
- **Problem nədir:**
  `open_trade` zamanı broker `ORDER_FILLING_IOC` rejimində sifarişin yalnız bir hissəsini icra edə bilər (məsələn, 1.0 lot əvəzinə 0.4 lot). Faktiki icra olunmuş həcm `result.volume` daxilində qayıdır. Lakin sətir 88-də DB-yə faktiki həcm deyil, ilkin göndərilən həcm yazılır:
  `self.db.insert_trade(..., volume=volume, initial_volume=volume, ...)`
  Daha sonra mövqe bağlandıqda, `sync_positions` (sətir 398) yoxlayır:
  `if initial_volume and accumulated+deal_volume < initial_volume-1e-8:`
  Brokerdə cəmi 0.4 lot bağlandığı üçün, sistem bunu əsas mövqenin tam bağlanması deyil, 1.0 lotun natamam hissəvi bağlanması hesab edir (`_record_partial_deal`). Nəticədə `update_trade_close` heç vaxt çağırılmır!
- **Hesaba Təsiri (Risk):**
  Brokerdə artıq bağlanmış mövqe SQLite `trades` cədvəlində **həmişə açıq (`status='open'`) qalır**. Nəticədə `max_open_positions`, `max_positions_per_group` və valyuta risk limitləri bu xəyali mövqeyə görə dolur və bot gələcək bütün əməliyyatları əsassız yerə bloklayır.
- **Tövsiyə olunan Həll:**
  `insert_trade` çağırışında `float(getattr(result, 'volume', volume) or volume)` istifadə edilməli və mövqe açıldıqdan dərhal sonra `positions_get` ilə faktiki açılmış həcm təsdiqlənməlidir.

---

### HIGH SEVERITY

#### [HIGH-01] `demo_exploration` konfiqurasiyası vasitəsilə kilidlənmiş risk tavanlarının (Locked Ceilings) aşılması
- **Fayl və Sətir:** [src/config.py#L19-L30](file:///c:/Users/Murad/Desktop/tradingbot/src/config.py#L19-L30), [src/bot.py#L390-L400](file:///c:/Users/Murad/Desktop/tradingbot/src/bot.py#L390-L400)
- **Problem nədir:**
  `config.py` daxilindəki `validate_risk_ceilings` funksiyası yalnız `config['risk']` bölməsini yoxlayır. O, `config['demo_exploration']` və `config['weekend']` bölmələrini yoxlamır. Əgər istifadəçi və ya kənar skript `demo_exploration.risk_per_trade_pct: 1.0` yazarsa, validator heç bir xəta vermədən konfiqurasiyanı qəbul edir. Nəticədə `bot.py:390`-da `risk_pct` kilidlənmiş 0.25% tavanını aşaraq 1.0% tətbiq olunur. Eyni zamanda eksplorasiya rejimi adaptiv strategiya qapılarını da kənara qoyur (`bot.py:337`).
- **Hesaba Təsiri (Risk):**
  Layihənin "heç bir konfiqurasiya risk tavanlarını aşa bilməz" tələbi pozulur. Hesabda gözləniləndən 4-10 dəfə artıq risklə əməliyyatlar açıla bilər.
- **Tövsiyə olunan Həll:**
  `validate_risk_ceilings()` funksiyasında `demo_exploration` və `weekend` altındakı `risk_per_trade_pct` və `max_open_positions` dəyərlərinin də `LOCKED_RISK_CEILINGS`-ə uyğunluğu məcburi yoxlanılmalıdır.

---

#### [HIGH-02] Açıq risk həcminin (`current_open_risk`) hesablanmasında mənfəətdə olan trailing stop-lar risk kimi toplanır
- **Fayl və Sətir:** [src/bot.py#L417-L424](file:///c:/Users/Murad/Desktop/tradingbot/src/bot.py#L417-L424)
- **Problem nədir:**
  `bot._candidate()` funksiyasında ümumi portfel riskini yoxlamaq üçün hər bir açıq mövqenin riski hesablanır:
  `current_open_risk += _risk_money(abs(float(position.price_open) - stop), float(position.volume), position_spec)`
  Burada istiqamət nəzərə alınmadan birbaşa `abs(open - stop)` götürülür. Əgər alış mövqeyində stop mənfəət zonasına çəkilibsə (`stop > price_open`, məsələn +50 punkt kilidlənmiş qazanc), bu mövqe üçün faktiki risk sıfırdır. Lakin `abs()` funksiyası həmin 50 punktluq qazancı 50 punktluq RİSK kimi hesablayır!
- **Hesaba Təsiri (Risk):**
  Qazancda olan və stopu qorunan mövqelər artdıqca süni şəkildə `current_open_risk` şişir, `max_total_open_risk_pct` (5%) limitini doldurur və yeni ticarət imkanlarını əsassız yerə bloklayır.
- **Tövsiyə olunan Həll:**
  Açıq risk hesabı istiqamətə görə aparılmalıdır:
  Alış üçün: `risk_dist = max(0.0, float(position.price_open) - stop)`
  Satış üçün: `risk_dist = max(0.0, stop - float(position.price_open))`.

---

#### [HIGH-03] Xronoloji təmizləmə pəncərəsinin (Purge Window) qısa olması səbəbindən Train/Validation/Test sızması
- **Fayl və Sətir:** [src/brain/training.py#L7-L16](file:///c:/Users/Murad/Desktop/tradingbot/src/brain/training.py#L7-L16), [src/brain/dataset.py#L71](file:///c:/Users/Murad/Desktop/tradingbot/src/brain/dataset.py#L71)
- **Problem nədir:**
  `chronological_splits` funksiyasında `purge_minutes = 20` qəbul edilir. Lakin `build_labeled_outcomes` daxilində əməliyyatların maksimal saxlanma müddəti (`timeout_minutes`) 60-120 dəqiqəyə qədərdir. Təlim (train) dövrünün sonunda açılmış bir əməliyyat növbəti 120 dəqiqə ərzində bazarda qalır və onun nəticəsi (label) artıq validasiya dövrünə düşən şamlar əsasında formalaşır.
- **Hesaba Təsiri (Risk):**
  Gələcək məlumatların təlim dəstinə sızması (lookahead data leakage) səbəbindən ML modelinin arxayınlığı şişirdilir. Model real bazarda işləyərkən gözlənilən nəticəni vermir və zərər yazır.
- **Tövsiyə olunan Həll:**
  `chronological_splits()` daxilində `purge_minutes` dəyəri ən azı maksimal saxlanma müddətinə (`max_hold_extended_minutes`, yəni 120 dəqiqəyə) bərabər təyin edilməlidir.

---

#### [HIGH-04] Windows WDAC / AppLocker siyasəti PyArrow Parquet mühərrikini bloklayır
- **Fayl və Sətir:** [src/history.py#L137](file:///c:/Users/Murad/Desktop/tradingbot/src/history.py#L137), [src/brain/dataset.py#L55](file:///c:/Users/Murad/Desktop/tradingbot/src/brain/dataset.py#L55), `tests/test_history.py`
- **Problem nədir:**
  Sistemdə aktiv olan Windows Defender Application Control (WDAC) siyasəti `pyarrow._parquet.pyd` DLL faylının icrasını bloklayır (`An Application Control policy has blocked this file`). Pytest zamanı uğursuz olan 4 test birbaşa bu bloklamaya görə `to_parquet` zamanı qırılır.
- **Hesaba Təsiri (Risk):**
  Əgər `config.yaml`-da `history.incremental_refresh_enabled: true` edilərsə, botun dövriyyəsi `history.py` daxilində `to_parquet` çağırdığı anda kəsiləcək və bütün ticarət dövrü xəta ilə dayanacaq. Offline təlim datasının hazırlanması da mümkün deyil.
- **Tövsiyə olunan Həll:**
  `history.py` və `dataset.py` daxilində `pyarrow` uğursuz olduqda `fastparquet` və ya SQLite/CSV ehtiyat mexanizmi əlavə edilməli, yaxud Windows AppLocker siyasətində venv qovluğunun native fayllarına icazə verilməlidir.

---

#### [HIGH-05] `Database.get_pnl_since` sorğusunda `magic` filtrinin olmaması kənar əməliyyatların botu dayandırmasına səbəb olur
- **Fayl və Sətir:** [src/db.py#L493-L498](file:///c:/Users/Murad/Desktop/tradingbot/src/db.py#L493-L498), [src/bot.py#L324-L327](file:///c:/Users/Murad/Desktop/tradingbot/src/bot.py#L324-L327)
- **Problem nədir:**
  `get_pnl_since(dt)` funksiyası verilənlər bazasından PnL cəmini hesablayarkən `magic` nömrəsini yoxlamır:
  `SELECT COALESCE(SUM(COALESCE(profit,0)+COALESCE(commission,0)+COALESCE(swap,0)),0) FROM trades WHERE status='closed' AND close_time>=?`
  Əgər eyni bazada əl ilə açılmış və ya başqa botun əməliyyatları varsa, onların zərərləri birbaşa botun gündəlik və həftəlik zərərinə əlavə edilir.
- **Hesaba Təsiri (Risk):**
  Hesabda əl ilə edilmiş bir zərərli ticarət botun `daily_loss_limit_pct` limitini vaxtından əvvəl doldura və botun ticarətini əsassız dayandıra bilər; yaxud əksinə, kənar qazanc botun zərərini maskalayaraq stop limitlərinin işləməsinə mane ola bilər.
- **Tövsiyə olunan Həll:**
  `get_pnl_since(dt, magic=None)` parametrləşdirilməli və `bot._pnl_periods()` daxilində `self.settings.magic_number` ötürülməlidir.

---

### MEDIUM SEVERITY

#### [MED-01] Əsas İcra Modulunda Test Örtüyünün Aşağı Olması (`executor.py` 45%)
- **Fayl və Sətir:** [src/executor.py](file:///c:/Users/Murad/Desktop/tradingbot/src/executor.py) (Örtük: 45%), [src/market_data.py](file:///c:/Users/Murad/Desktop/tradingbot/src/market_data.py) (Örtük: 49%)
- **Problem nədir:**
  Ticarətin birbaşa icra olunduğu, mövqelərin bağlandığı və stopların idarə edildiyi `executor.py` faylının 230 sətri (55%-i) heç bir vahid test (unit test) tərəfindən yoxlanılmır. Xüsusilə requote, qismən icra, adverse move exit və xəbər qorunması kodları tamamilə kənarda qalıb.
- **Hesaba Təsiri (Risk):**
  İcra məntiqindəki gizli xətalar yalnız real bazar mühitində pul itkisi ilə üzə çıxacaq.
- **Tövsiyə olunan Həll:**
  `tests/test_executor_safety.py` daxilinə brokerin xəta kodları, requote, qismən doldurma və vaxt çıxışı ssenarilərini əhatə edən mock testlər əlavə edilməlidir.

---

#### [MED-02] Xəbər Təqvimi Yüklənməsində Təhlükəsizlik Boşluqları (XXE və Sxemsiz URL)
- **Fayl və Sətir:** [src/news.py#L86](file:///c:/Users/Murad/Desktop/tradingbot/src/news.py#L86), [src/news.py#L164](file:///c:/Users/Murad/Desktop/tradingbot/src/news.py#L164)
- **Problem nədir:**
  Bandit analizində `news.py:86`-da `xml.etree.ElementTree.fromstring` (B314) və `news.py:164`-də `urllib.request.urlopen` (B310) qeydə alınıb. Həmçinin XML formatında vaxt zonası `datetime.strptime().replace(tzinfo=eastern)` ilə təyin olunur ki, bu da ABŞ yay/qış vaxtına keçid bazar günlərində 1 saatlıq səhv yaradır.
- **Hesaba Təsiri (Risk):**
  Kənar mənbədən gələn zədələnmiş XML parseri çökdürə bilər; saat xətası isə botun yüksək təsirli xəbərlərdən (NFP, CPI) əvvəl mövqeləri bağlamamasına səbəb ola bilər.
- **Tövsiyə olunan Həll:**
  `defusedxml` kitabxanasından istifadə edilməli və yalnız təsdiqlənmiş HTTPS URL-lərə icazə verilməlidir.

---

#### [MED-03] `fibonacci.py` Modulunda ATR Sıfır Olduqda Runtime `TypeError` Çökməsi
- **Fayl və Sətir:** [src/patterns/fibonacci.py#L25](file:///c:/Users/Murad/Desktop/tradingbot/src/patterns/fibonacci.py#L25)
- **Problem nədir:**
  Sətir 21-də ATR sıfır olduqda `distance_atr: None` yazılır. Sətir 25-də isə:
  `'reaction_level': min(touched, key=lambda x: x['distance_atr']) if rejection else None`
  Python 3-də `min()` funksiyası `None` ilə `float` arasında müqayisə apara bilmir və `TypeError: '<' not supported between instances of 'NoneType' and 'float'` xətası ataraq skaneri çökdürür.
- **Hesaba Təsiri (Risk):**
  Yastı (flat) və ya yeni alətlərdə Fibonacci reaksiyası hesablanarkən skan dövrəsi qırılır.
- **Tövsiyə olunan Həll:**
  Sətir 25-dəki lambda sətir 22-dəki kimi təhlükəsiz edilməlidir:
  `key=lambda x: x['distance_atr'] if x['distance_atr'] is not None else float('inf')`.

---

#### [MED-04] Verilənlər Bazasında Dinamik SQL Konstruksiyası (B608)
- **Fayl və Sətir:** [src/db.py#L125](file:///c:/Users/Murad/Desktop/tradingbot/src/db.py#L125), [src/db.py#L131](file:///c:/Users/Murad/Desktop/tradingbot/src/db.py#L131), [src/db.py#L425](file:///c:/Users/Murad/Desktop/tradingbot/src/db.py#L425)
- **Problem nədir:**
  Cədvəl və sütun adları birbaşa f-string vasitəsilə SQL sorğusuna birləşdirilir: `f"INSERT INTO {table} ({','.join(columns)}) VALUES ..."`
- **Hesaba Təsiri (Risk):**
  SQL Injection riski və sütun adlarında gözlənilməz simvollar olduqda sorğunun qırılması.
- **Tövsiyə olunan Həll:**
  Sütun adları icazə verilən ağ siyahı (whitelist) ilə tutuşdurulduqdan sonra sorğuya daxil edilməlidir.

---

#### [MED-05] Server Saat Fərqinin Həftəsonu Qeyri-müəyyənliyində `timedelta(0)` Defoltuna Düşməsi
- **Fayl və Sətir:** [src/time_utils.py#L55](file:///c:/Users/Murad/Desktop/tradingbot/src/time_utils.py#L55)
- **Problem nədir:**
  `detect_server_utc_offset()` funksiyası kotirovkaların təzəliyini yoxlayır. Əgər həftəsonu kriptovalyuta kotirovkaları da daxil olmaqla heç bir təzə kotirovka tapılmazsa, funksiya susmaya görə `return timedelta(0)` (UTC+0) qaytarır. Lakin əksər MT5 brokerləri Şərqi Avropa vaxtı ilə (UTC+2 və ya UTC+3) işləyir.
- **Hesaba Təsiri (Risk):**
  Həftəsonu açılış və ya bağlanış saatları 2-3 saat fərqlə hesablanır, sessiya filtri vaxtından tez və ya gec işə düşür.
- **Tövsiyə olunan Həll:**
  Sonuncu məlum olan ofset bazada saxlanılmalı və ya `config.yaml` daxilində ehtiyat broker saat qurşağı (məsələn, `default_server_utc_offset_hours: 2`) təyin edilməlidir.

---

#### [MED-06] Nəzarətçi (Watchdog) Donma Hesabatında Uşaq Prosesin Deyil, Nəzarətçinin Traceback-ini Yazır
- **Fayl və Sətir:** [src/supervisor.py#L45](file:///c:/Users/Murad/Desktop/tradingbot/src/supervisor.py#L45), [scripts/run_forever.py#L184](file:///c:/Users/Murad/Desktop/tradingbot/scripts/run_forever.py#L184)
- **Problem nədir:**
  Watchdog donma aşkar etdikdə `write_hang_report` çağırır və `faulthandler.dump_traceback()` icra edir. Lakin bu kod nəzarətçinin öz prosesində icra olunduğu üçün hesabata yalnız nəzarətçinin gözləmə vəziyyətindəki thread-ləri düşür; donmuş bot prosesinin hansı sətirdə ilişib qaldığı qeydə alınmır.
- **Hesaba Təsiri (Risk):**
  İnsidentlərin kök səbəbini (root cause) müəyyən etmək mümkün olmur (`ERROR_LEDGER.md`-dəki donmaların indiyədək həll olunmamasının əsas səbəbi).
- **Tövsiyə olunan Həll:**
  Bot prosesini öldürməzdən əvvəl Windows platformasında uyğun siqnal və ya xüsusi IPC vasitəsilə child prosesin özünün stack trace-ini `crash.log`-a atması təmin edilməlidir.

---

### LOW SEVERITY

#### [LOW-01] SQLite `_RetryConnection` Yalnız Tək Təkrar və 50ms Gözləmə Tətbiq Edir
- **Fayl və Sətir:** [src/db.py#L8-L25](file:///c:/Users/Murad/Desktop/tradingbot/src/db.py#L8-L25)
- **Problem nədir:**
  Bazanın kilidlənməsi halında `_RetryConnection` yalnız bir dəfə 50ms gözləyir və təkrar edir. Dashboard ağır analitik sorğu icra edərsə və ya VACUUM işləyərsə, bot dərhal `OperationalError: database is locked` xətası alır.
- **Hesaba Təsiri (Risk):**
  Nadir hallarda dövrə xətaları və ya hadisələrin bazaya yazıla bilməməsi.
- **Tövsiyə olunan Həll:**
  Eksponensial geri çəkilmə ilə 3-5 təkrar cəhdi tətbiq olunmalıdır.

---

#### [LOW-02] İstifadəsiz Qalmış Köhnə Kodlar və Modellər (Vulture 60% Confidence)
- **Fayl və Sətir:** [src/models.py#L16, L36](file:///c:/Users/Murad/Desktop/tradingbot/src/models.py#L16-L36), [src/strategy_base.py#L18](file:///c:/Users/Murad/Desktop/tradingbot/src/strategy_base.py#L18), [src/db.py#L273](file:///c:/Users/Murad/Desktop/tradingbot/src/db.py#L273)
- **Problem nədir:**
  İstifadəsiz `TradeRequest`, `Position` klassları, `DummyStrategy` və köhnə hesabat funksiyaları layihədə qalmaqdadır.
- **Hesaba Təsiri (Risk):**
  Sistem üçün təhlükə yaratmır, lakin kod bazasını qarışıq saxlayır.
- **Tövsiyə olunan Həll:**
  Növbəti refaktorinq zamanı köhnə kod qalıqları təmizlənməlidir.

---

## 5. Qısa Xülasə (Azərbaycan dilində)

Bu müstəqil audit zamanı ticarət botunun arxitekturası, icra mexanizmləri, risk hesablamaları və konfiqurasiyası dərindən araşdırılmışdır. 

Sistemdə bir sıra güclü qoruyucu mexanizmlər mövcuddur (məsələn, risk tavanlarının konfiqurasiya səviyyəsində yoxlanması, STOP faylı kill-switch, çoxmərhələli sessiya və spread filtrləri, trailing stop və breakeven qaydaları). Bununla belə, **hesab üçün birbaşa təhlükə yaradan 5 kritik və 5 yüksək dərəcəli çatışmazlıq** aşkarlanmışdır:

1. **Stop-Loss Boşluğu:** Broker əməliyyat açarkən stop-loss-u qəbul etmədikdə bot mövqeni bazarda stopsuz buraxır və onu nə bağlayır, nə də təkrar stop təyin edir. Bu, qəfil bazar hərəkətlərində hesabı tam sıfırlaya bilər.
2. **Watchdog Donmalarının Əsas Səbəbi:** `MT5CallProxy` hər əməliyyatda yeni thread yaradır. MT5 C-kitabxanası thread-safe olmadığı üçün bu yanaşma dövriyyələrin donmasına, timeout-ların toplanaraq 90 saniyəni aşmasına və nəzarətçinin botu zorla öldürməsinə gətirib çıxarır (`ERROR_LEDGER.md`-dəki 6 izahsız donmanın sirri məhz budur).
3. **Komissiyasız və Təzə Hesabların Bloklanması:** Komissiya yalnız keçmiş ticarət tarixçəsindən hesablandığı üçün təzə və ya sıfır komissiyalı hesablarda bot heç vaxt ticarət aça bilmir (deadlock).
4. **Requote Zamanı Risk Hesabının İtirilməsi:** Qiymət dəyişdikdə yeni qiymətlə stop arasındakı məsafə artarsa, lot həcmi azaldılmadan köhnə həcmlə bazara girilir və 0.25% risk tavanı aşılır.
5. **Qismən İcra Xətası:** Qismən icra olunan mövqelər DB-də əbədi olaraq açıq qalır və portfel limitlərini doldurur.

**Yekun tövsiyə:** Bot real hesaba və ya məsuliyyətli DEMO sınağına buraxılmazdan əvvəl yuxarıda göstərilən 5 kritik xəta və `MT5CallProxy` arxitekturası mütləq şəkildə düzəldilməlidir.
