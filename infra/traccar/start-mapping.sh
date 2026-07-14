#!/bin/bash
# Start a mapping day: Traccar up, public tunnel up, Mac kept awake.
# Prints the URL to put in Traccar Client. Run BEFORE leaving the house.
set -e
cd "$(dirname "$0")"

colima status >/dev/null 2>&1 || colima start
docker-compose up -d

# keep the Mac awake while you're out (tunnel + server must stay reachable)
pgrep -f "caffeinate -dims" >/dev/null || (nohup caffeinate -dims >/dev/null 2>&1 &)

# public HTTPS tunnel to the ingest port (URL changes each time this restarts!)
pkill -f "cloudflared tunnel --url" 2>/dev/null || true
sleep 1
nohup cloudflared tunnel --url http://localhost:5055 > /tmp/quecombi-tunnel.log 2>&1 &
echo "waiting for tunnel…"
for i in $(seq 1 30); do
  URL=$(grep -o "https://[a-z0-9-]*\.trycloudflare\.com" /tmp/quecombi-tunnel.log | head -1 || true)
  [ -n "$URL" ] && break
  sleep 2
done
[ -z "$URL" ] && { echo "tunnel failed — see /tmp/quecombi-tunnel.log"; exit 1; }

echo
echo "══════════════════════════════════════════════════"
echo "  Traccar Client server URL (update it on the phone"
echo "  if it changed since last time):"
echo
echo "      $URL"
echo
echo "  identifier: mauricio-1 · web UI: http://localhost:8082"
echo "  Mac will stay awake (caffeinate). Buen viaje."
echo "══════════════════════════════════════════════════"
