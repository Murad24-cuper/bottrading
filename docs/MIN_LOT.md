# Small-Account Feasibility Analysis: XM Micro Account ($50 Target & Current $1,000)

**Date:** 2026-11-10  
**Context:** Evaluation of minimum contract sizes, tick values, and minimum volume constraints for a real XM Micro account targeted at a \$50 initial balance vs. current \$1,000 DEMO balance.  
**Purpose:** Pure decision-support report. No risk settings or hard ceilings are altered by this document.

---

## 1. Specification Foundations: Standard vs. Micro

| Asset Class | Standard Contract Size | Micro Contract Size | Tick Size | Standard Tick Value (per lot) | Micro Tick Value (per lot) | Min Volume | Min Step |
|---|---|---|---|---|---|---|---|
| **Forex Majors** (EURUSD, GBPUSD, AUDUSD) | 100,000 units | 1,000 units | 0.00001 | \$1.00 | **\$0.01** | 0.01 (or 0.10) | 0.01 |
| **Forex Yen Crosses** (USDJPY, EURJPY) | 100,000 units | 1,000 units | 0.001 | ~\$0.634 | **~\$0.00634** | 0.01 (or 0.10) | 0.01 |
| **Gold** (GOLD / GOLDmicro) | 100 oz | 1 oz (or 10 oz) | 0.01 | \$1.00 | **\$0.01** | 0.01 (or 0.10) | 0.01 |
| **Silver** (SILVER / SILVERmicro) | 5,000 oz | 50 oz | 0.001 | \$5.00 | **\$0.05** | 0.10 | 0.01 |
| **US500** (US500Cash) | 1 contract | 1 contract | 0.01 | \$0.01 | **\$0.01** | 0.10 | 0.10 |
| **US100 / NAS100** (US100Cash) | 1 contract | 1 contract | 0.01 | \$0.01 | **\$0.01** | 0.10 | 0.10 |
| **US30** (US30Cash) | 1 contract | 1 contract | 0.01 | \$0.01 | **\$0.01** | 0.10 | 0.10 |
| **GER40** (GER40Cash) | 1 contract | 1 contract | 0.01 | ~\$0.0108 | **~\$0.0108** | 0.10 | 0.10 |
| **BTCUSD** | 1 coin | 1 coin | 0.01 | \$0.01 | **\$0.01** | 0.01 | 0.01 |
| **ETHUSD** | 1 coin | 1 coin | 0.01 | \$0.01 | **\$0.01** | 0.02 | 0.01 |

---

## 2. Dollar Risk of Minimum Volume per Symbol

The minimum dollar risk is determined by:
$$\text{Min Dollar Risk} = \frac{\text{Stop Distance}}{\text{Tick Size}} \times \text{Tick Value per Lot} \times \text{Volume Min}$$

| Symbol | Broker Symbol | Typical Stop | Stop Distance | Volume Min | Risk per 1 Lot | **Min Dollar Risk** |
|---|---|---|---|---|---|---|
| **EURUSD** | `EURUSDmicro` | 30 pips | 0.0030 (300 ticks) | 0.01 lot | \$3.00 | **\$0.030** |
| **GBPUSD** | `GBPUSDmicro` | 35 pips | 0.0035 (350 ticks) | 0.01 lot | \$3.50 | **\$0.035** |
| **USDJPY** | `USDJPYmicro` | 35 pips | 0.350 (350 ticks) | 0.01 lot | \$2.22 | **\$0.022** |
| **AUDUSD** | `AUDUSDmicro` | 30 pips | 0.0030 (300 ticks) | 0.01 lot | \$3.00 | **\$0.030** |
| **USDCAD** | `USDCADmicro` | 30 pips | 0.0030 (300 ticks) | 0.01 lot | \$2.12 | **\$0.021** |
| **EURJPY** | `EURJPYmicro` | 35 pips | 0.350 (350 ticks) | 0.01 lot | \$2.22 | **\$0.022** |
| **GBPJPY** | `GBPJPYmicro` | 40 pips | 0.400 (400 ticks) | 0.01 lot | \$2.54 | **\$0.025** |
| **GOLD** | `GOLDmicro` (1 oz) | \$10.00 move | 10.00 (1,000 ticks) | 0.01 lot | \$10.00 | **\$0.100** |
| **GOLD (0.1 min)**| `GOLDmicro` (0.1 min) | \$10.00 move | 10.00 (1,000 ticks) | 0.10 lot | \$10.00 | **\$1.000** |
| **SILVER** | `SILVERmicro` | \$0.50 move | 0.500 (500 ticks) | 0.10 lot | \$25.00 | **\$2.500** |
| **US500** | `US500Cash` | 20 index pts | 20.00 (2,000 ticks) | 0.10 lot | \$20.00 | **\$2.000** |
| **NAS100** | `US100Cash` | 60 index pts | 60.00 (6,000 ticks) | 0.10 lot | \$60.00 | **\$6.000** |
| **US30** | `US30Cash` | 150 index pts | 150.00 (15,000 ticks) | 0.10 lot | \$150.00 | **\$15.000** |
| **GER40** | `GER40Cash` | 60 index pts | 60.00 (6,000 ticks) | 0.10 lot | \$65.00 | **\$6.500** |
| **BTCUSD** | `BTCUSD` | \$1,000 move | 1,000.00 (100k ticks) | 0.01 lot | \$1,000.00 | **\$10.000** |
| **ETHUSD** | `ETHUSD` | \$40 move | 40.00 (4,000 ticks) | 0.02 lot | \$40.00 | **\$0.800** |
| **GOLD24-7** | `GOLD24-7` | \$10.00 move | 10.00 (1,000 ticks) | 0.01 lot | \$10.00 | **\$0.100** |
| **Altcoins_INDX** | `Altcoins_INDX` | 50 pts | 50.00 (5,000 ticks) | 0.10 lot | \$50.00 | **\$5.000** |
| **Crypto_10** | `Crypto_10` | 50 pts | 50.00 (5,000 ticks) | 0.10 lot | \$50.00 | **\$5.000** |

---

## 3. Tradability Matrix at Target \$50 Balance

Risk budget per trade at \$50:
- **0.10%:** \$0.050
- **0.25%:** \$0.125
- **0.50%:** \$0.250
- **1.00%:** \$0.500

| Symbol | Min Dollar Risk | \$50 @ 0.10% (\$0.05) | \$50 @ 0.25% (\$0.125) | \$50 @ 0.50% (\$0.25) | \$50 @ 1.00% (\$0.50) | Feasibility Summary |
|---|---|---|---|---|---|---|
| **EURUSDmicro** | \$0.030 | **YES** | **YES** | **YES** | **YES** | Tradable at all risk tiers |
| **GBPUSDmicro** | \$0.035 | **YES** | **YES** | **YES** | **YES** | Tradable at all risk tiers |
| **USDJPYmicro** | \$0.022 | **YES** | **YES** | **YES** | **YES** | Tradable at all risk tiers |
| **AUDUSDmicro** | \$0.030 | **YES** | **YES** | **YES** | **YES** | Tradable at all risk tiers |
| **USDCADmicro** | \$0.021 | **YES** | **YES** | **YES** | **YES** | Tradable at all risk tiers |
| **EURJPYmicro** | \$0.022 | **YES** | **YES** | **YES** | **YES** | Tradable at all risk tiers |
| **GBPJPYmicro** | \$0.025 | **YES** | **YES** | **YES** | **YES** | Tradable at all risk tiers |
| **GOLDmicro (0.01)**| \$0.100 | NO | **YES** | **YES** | **YES** | Tradable from 0.25% risk upwards |
| **GOLDmicro (0.10)**| \$1.000 | NO | NO | NO | NO | Requires \$100+ account or 2% risk |
| **SILVERmicro** | \$2.500 | NO | NO | NO | NO | Not tradable at \$50 |
| **US500Cash** | \$2.000 | NO | NO | NO | NO | Min risk is 4.0% of \$50 |
| **US100Cash** | \$6.000 | NO | NO | NO | NO | Min risk is 12.0% of \$50 |
| **US30Cash** | \$15.000 | NO | NO | NO | NO | Min risk is 30.0% of \$50 |
| **GER40Cash** | \$6.500 | NO | NO | NO | NO | Min risk is 13.0% of \$50 |
| **BTCUSD** | \$10.000 | NO | NO | NO | NO | Min risk is 20.0% of \$50 |
| **ETHUSD** | \$0.800 | NO | NO | NO | NO | Min risk is 1.6% of \$50 |
| **GOLD24-7** | \$0.100 | NO | **YES** | **YES** | **YES** | Tradable from 0.25% risk upwards |

---

## 4. Tradability Matrix at Current \$1,000 DEMO Balance

Risk budget per trade at \$1,000:
- **0.10%:** \$1.00
- **0.25%:** \$2.50
- **0.50%:** \$5.00
- **1.00%:** \$10.00

| Symbol | Min Dollar Risk | \$1,000 @ 0.10% (\$1.00) | \$1,000 @ 0.25% (\$2.50) | \$1,000 @ 0.50% (\$5.00) | \$1,000 @ 1.00% (\$10.00) |
|---|---|---|---|---|---|
| **Forex Majors (Micro)** | \$0.02 - \$0.03 | **YES** | **YES** | **YES** | **YES** |
| **Forex Crosses (Micro)**| \$0.02 - \$0.03 | **YES** | **YES** | **YES** | **YES** |
| **GOLDmicro (0.01)** | \$0.10 | **YES** | **YES** | **YES** | **YES** |
| **GOLDmicro (0.10)** | \$1.00 | **YES** | **YES** | **YES** | **YES** |
| **ETHUSD** | \$0.80 | **YES** | **YES** | **YES** | **YES** |
| **US500Cash** | \$2.00 | NO | **YES** | **YES** | **YES** |
| **SILVERmicro** | \$2.50 | NO | **YES** | **YES** | **YES** |
| **US100Cash** | \$6.00 | NO | NO | NO | **YES** |
| **GER40Cash** | \$6.50 | NO | NO | NO | **YES** |
| **BTCUSD** | \$10.00 | NO | NO | NO | **YES** |
| **US30Cash** | \$15.00 | NO | NO | NO | NO (Needs \$1.5k+) |

---

## 5. Strategic Conclusions & Profile Recommendations

1. **At \$50 Initial Balance:**
   - **Forex (7 pairs)** is 100% tradable across all risk tiers down to 0.10% (\$0.05 budget) with Micro lot sizing.
   - **Gold (GOLDmicro / GOLD24-7)** is tradable at $\ge 0.25\%$ risk (\$0.125 budget for 0.01 lot).
   - **Indices and Crypto** (`US500`, `US100`, `US30`, `GER40`, `BTCUSD`) **CANNOT** be traded at \$50 without violating the 1% maximum locked risk ceiling (minimum dollar risk is \$2.00 to \$15.00 per trade).
2. **Planned "micro_50" Profile Design:**
   - **Universe:** Confined strictly to Forex (`EURUSD`, `GBPUSD`, `USDJPY`, `AUDUSD`, `USDCAD`, `EURJPY`, `GBPJPY`) and `GOLDmicro` (at $\ge 0.25\%$).
   - **Risk per Trade:** 0.25% to 0.50% (feasible and strictly below the 1.0% locked ceiling).
   - **Indices & Crypto:** Excluded from `micro_50` to guarantee zero `min lot exceeds risk` errors and strict capital preservation.
