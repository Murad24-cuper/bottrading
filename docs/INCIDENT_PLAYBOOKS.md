# Incident detection and response

The bot and supervisor record incidents in `bot_events`. Telegram alerts are
queued when credentials are configured; notification failures do not stop the
bot.

| Incident | Automatic response | Operator action |
|---|---|---|
| Owned position has no stop-loss | Critical event and Telegram alert; blocks new entries until the position has an SL. It does not modify or close the position automatically. | Check the position in MT5. Restore a valid SL manually, then verify the bot reports recovery. |
| MT5 disconnects while positions are open | The bot retries the connection; repeated failure blocks entries and alerts. Position sync and management resume after reconnect. | Check the terminal is logged in and connected to the broker. Do not launch a second MT5 Python session. |
| Repeated order submissions are rejected | After `health.order_rejections_before_alert` consecutive failures, record a critical event and send one alert; a successful order resets the counter. | Review the recorded broker retcode/message, symbol trading hours, volume, margin and stop distance. |
| Margin level falls below threshold | Blocks new entries and alerts once; sends a recovery event when margin returns above `health.min_margin_level_pct`. | Reduce exposure or add funds through the broker client; never increase bot risk limits. |
| Heartbeat is stale | Supervisor writes a hang report, terminates the stuck child and applies the restart policy; critical event is sent to Telegram. | Review `logs/crash.log` and `logs/bot.log` if the supervisor reaches its restart cap. |
| Disk space is low | Supervisor records a warning and sends a Telegram alert, throttled to once per hour. | Free disk space without deleting the database or the seven retained backups. |
| Both calendar sources fail | Conservative UTC news window is used, event is logged, and Telegram is alerted once until a source recovers. | Check the calendar exporter and HTTPS access; the fallback window remains active meanwhile. |

Thresholds are in `config.yaml` under `health`. Hard trading risk limits remain
separate and cannot be relaxed by these incident settings.
