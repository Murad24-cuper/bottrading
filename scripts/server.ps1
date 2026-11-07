param([ValidateSet('status','logs','health','tunnel','vnc-tunnel','stop','start')][string]$Action='status')
$ErrorActionPreference='Stop'
$Server='ec2-user@16.192.113.6'
$Key=Join-Path $env:USERPROFILE 'Downloads\bot.pem'
if (!(Test-Path $Key)) { throw "SSH key not found: $Key" }
switch ($Action) {
  'status' { ssh -i $Key $Server 'cd /opt/tradingbot && sudo docker compose -f deploy/linux/compose.yaml ps' }
  'logs' { ssh -i $Key $Server 'sudo docker compose -f /opt/tradingbot/deploy/linux/compose.yaml logs --tail=100' }
  'health' { ssh -i $Key $Server 'cd /opt/tradingbot && sudo docker compose -f deploy/linux/compose.yaml exec -T mt5bot wine "C:\Program Files\Python311\python.exe" scripts/health_check.py' }
  'tunnel' { ssh -i $Key -N -L 8501:127.0.0.1:8501 $Server }
  'vnc-tunnel' { ssh -i $Key -N -L 5900:127.0.0.1:5900 $Server }
  'stop' { ssh -i $Key $Server 'touch /opt/tradingbot/data/supervisor.stop; sleep 3; cd /opt/tradingbot && sudo docker compose -f deploy/linux/compose.yaml stop mt5bot dashboard' }
  'start' { ssh -i $Key $Server 'rm -f /opt/tradingbot/STOP /opt/tradingbot/data/supervisor.stop; cd /opt/tradingbot && sudo docker compose -f deploy/linux/compose.yaml up -d' }
}
