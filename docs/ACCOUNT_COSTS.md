# Account and Symbol Facts & Cost Model v1

Generated: 2026-11-09T19:10:30.930813+00:00 UTC

## 1. Account Facts

- **Account Login:** `346494979`
- **Trade Mode:** `DEMO` (Verified DEMO)
- **Balance:** `1000.00 USD`
- **Equity:** `1000.00 USD`
- **Currency:** `USD`
- **Leverage:** `1:1000`
- **Company / Broker:** `XM Global Limited`
- **Server:** `XMGlobal-MT5 10`

## 2. Symbol Specifications and Live Cost Parameters

| Symbol | Logical | Group | Digits | Point | Spread (pts) | Live Spread (pts) | Min Vol | Step | Tick Size | Tick Value | Comm / Lot (Side) | Comm Source |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `BTCUSD` | `BTCUSD` | crypto | 2 | 0.01 | 4000.0 | 4000.0 | 0.01 | 0.01 | 0.01 | 0.0100 | 0.00 | conservative default (0.0) |
| `ETHUSD` | `ETHUSD` | crypto | 2 | 0.01 | 300.0 | 300.0 | 0.02 | 0.01 | 0.01 | 0.0100 | 0.00 | conservative default (0.0) |
| `EURUSD` | `EURUSD` | forex | 5 | 1e-05 | 20.0 | 19.5 | 0.01 | 0.01 | 1e-05 | 1.0000 | 0.00 | deal history |
| `GBPUSD` | `GBPUSD` | forex | 5 | 1e-05 | 24.0 | 23.3 | 0.01 | 0.01 | 1e-05 | 1.0000 | 0.00 | deal history |
| `USDJPY` | `USDJPY` | forex | 3 | 0.001 | 26.0 | 23.6 | 0.01 | 0.01 | 0.001 | 0.6327 | 0.00 | deal history |
| `AUDUSD` | `AUDUSD` | forex | 5 | 1e-05 | 23.0 | 23.7 | 0.01 | 0.01 | 1e-05 | 1.0000 | 0.00 | deal history |
| `USDCAD` | `USDCAD` | forex | 5 | 1e-05 | 28.0 | 29.4 | 0.01 | 0.01 | 1e-05 | 0.7074 | 0.00 | conservative default (0.0) |
| `US500Cash` | `US500` | indices | 2 | 0.01 | 80.0 | 80.0 | 0.1 | 0.1 | 0.01 | 0.0100 | 0.00 | deal history |
| `US100Cash` | `NAS100` | indices | 2 | 0.01 | 290.0 | 292.2 | 0.1 | 0.1 | 0.01 | 0.0100 | 0.00 | conservative default (0.0) |
| `US30Cash` | `US30` | indices | 2 | 0.01 | 600.0 | 600.0 | 0.1 | 0.1 | 0.01 | 0.0100 | 0.00 | conservative default (0.0) |
| `GER40Cash` | `GER40` | indices | 2 | 0.01 | 260.0 | 260.0 | 0.1 | 0.1 | 0.01 | 0.0100 | 0.00 | deal history |
| `Altcoins_INDX` | `Altcoins_INDX` | indices | 2 | 0.01 | 352.0 | 352.0 | 0.05 | 0.01 | 0.01 | 0.0100 | 0.00 | conservative default (0.0) |
| `Crypto_10` | `Crypto_10` | indices | 2 | 0.01 | 12710.0 | 12710.0 | 0.01 | 0.01 | 0.01 | 0.0100 | 0.00 | conservative default (0.0) |
| `GOLD` | `GOLD` | metals | 2 | 0.01 | 54.0 | 54.5 | 0.01 | 0.01 | 0.01 | 1.0000 | 0.00 | conservative default (0.0) |
| `GOLD24-7` | `GOLD24-7` | metals | 2 | 0.01 | 198.0 | 198.0 | 0.01 | 0.01 | 0.01 | 1.0000 | 0.00 | conservative default (0.0) |

## 3. Conservative Cost Model v1

### Formula & Definition
Per symbol, round-trip cost is calculated as:
$$\text{Cost} = \left( \max(\text{Spread}_{\text{symbol\_info}}, \text{Spread}_{\text{live\_median}}) \times 1.25 + \text{Slippage} \right) \times \frac{\text{TickValue}}{\text{TickSize}} + 2 \times \text{Commission}_{\text{side}}$$

**Slippage Assumptions:**
- **Forex:** 1.0 point
- **Indices & Gold:** 2.0 points
- **Crypto:** 0.1% of market price

### Resulting Cost per 1.0 Lot (Account Currency)

| Symbol | Asset Group | Effective Spread | Slippage | Spread Cost (1.25x) | Round-Trip Comm | Total Cost / Lot (USD) |
|---|---|---|---|---|---|---|
| `BTCUSD` | crypto | 40 | 0.1% of price | $50.00 | $0.00 | **$124.67** |
| `ETHUSD` | crypto | 3 | 0.1% of price | $3.75 | $0.00 | **$5.87** |
| `EURUSD` | forex | 0.0002 | 1.0 point | $25.00 | $0.00 | **$26.00** |
| `GBPUSD` | forex | 0.00024 | 1.0 point | $30.00 | $0.00 | **$31.00** |
| `USDJPY` | forex | 0.026 | 1.0 point | $20.56 | $0.00 | **$21.20** |
| `AUDUSD` | forex | 0.00023732 | 1.0 point | $29.66 | $0.00 | **$30.66** |
| `USDCAD` | forex | 0.00029441 | 1.0 point | $26.03 | $0.00 | **$26.74** |
| `US500Cash` | indices | 0.8 | 2.0 points | $1.00 | $0.00 | **$1.02** |
| `US100Cash` | indices | 2.9216 | 2.0 points | $3.65 | $0.00 | **$3.67** |
| `US30Cash` | indices | 6 | 2.0 points | $7.50 | $0.00 | **$7.52** |
| `GER40Cash` | indices | 2.6 | 2.0 points | $3.25 | $0.00 | **$3.27** |
| `Altcoins_INDX` | indices | 3.52 | 2.0 points | $4.40 | $0.00 | **$4.42** |
| `Crypto_10` | indices | 127.1 | 2.0 points | $158.88 | $0.00 | **$158.90** |
| `GOLD` | metals | 0.54453 | 2.0 points | $68.07 | $0.00 | **$70.07** |
| `GOLD24-7` | metals | 1.98 | 2.0 points | $247.50 | $0.00 | **$249.50** |

## 4. Sources of Facts

1. **Account Parameters:** MT5 C-API `account_info()` directly via MT5CallProxy.
2. **Symbol Specs:** MT5 C-API `symbol_info(sym)` (point, digits, contract_size, tick_size, tick_value, volume min/step).
3. **Live Spreads:** `data/bot.db` table `spread_samples` collected during live trading cycles.
4. **Commissions:** Historical `history_deals_get` 90-day window deals; if no deals found, broker `symbol_info.trade_commission` or default 0.0 with `commission_estimated=True`.
5. **Data Manifests:** `data/history/manifests/*.json` matching downloaded parquet partitions.
