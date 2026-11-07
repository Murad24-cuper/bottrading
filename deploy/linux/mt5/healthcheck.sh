#!/bin/sh
set -eu
test -f /opt/tradingbot/data/bot_status.json || true
pgrep -f 'Xvfb' >/dev/null
pgrep -f 'x11vnc' >/dev/null
if [ -e /opt/tradingbot/STOP ]; then exit 0; fi
pgrep -f 'terminal64.exe|terminal64' >/dev/null
pgrep -f 'run_forever.py' >/dev/null
