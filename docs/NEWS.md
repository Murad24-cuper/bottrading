# MT5 economic calendar exporter

`mql5/CalendarExporter.mq5` uses the MT5 economic calendar read APIs and writes `calendar_events.csv` in `MQL5/Files`. It does not contain any order functions. The Python scanner reads that file from the connected terminal's data directory and blocks new entries on mapped symbols within 15 minutes of a high-impact event. If the file is missing or older than two hours, the conservative 12:30–14:30 UTC fallback applies to USD, EUR, GBP and JPY linked instruments.

To run it, compile the script in MetaEditor, then in MT5 Navigator > Scripts drag **CalendarExporter** onto one chart. It refreshes every 15 minutes and should remain running. Confirm `MQL5/Files/calendar_events.csv` exists and its modification time advances. Terminal calendar access can be unavailable in some broker environments; in that case the Python fallback remains active. The exporter and Python parser store event times as UTC.

The script was compiled locally with MetaEditor (0 errors). It has not been attached to a chart or verified against XM's calendar feed yet, so the live calendar integration remains pending that terminal-level check.
# Economic calendar sources

The live scanner uses `MQL5/Files/calendar_events.csv` from its existing MT5
session when the file is no older than 24 hours. If it is absent or stale, the
scanner refreshes the public ForexFactory-format weekly JSON feed over HTTPS
every six hours and caches the unmodified feed under `data/calendar/`. Feed
timestamps carrying ISO offsets are converted to UTC. A recent cached response
continues to work during a network outage. The conservative 12:30–14:30 UTC
USD/EUR/GBP/JPY entry window is used only when neither source has usable data.
The dashboard reports the selected source and last refresh age. The exporter
remains supported and is still the preferred source while fresh.
