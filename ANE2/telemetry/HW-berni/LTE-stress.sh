#!/bin/bash
# ─────────────────────────────────────────────
#  LTE Stress Test  —  RPi 5 / ppp0
#  Usage: ./LTE-stress-test.sh [duration_sec]
#         Default duration: 300s (5 min)
# ─────────────────────────────────────────────
export LC_ALL=C

# ── Config ──────────────────────────────────
INTERFACE="ppp0"
DURATION="${1:-300}"
LOG_FILE="benchmark_$(date +%Y%m%d_%H%M%S).csv"
PING_HOST="8.8.8.8"
PING_COUNT=5
DL_URL="http://speedtest.tele2.net/10MB.zip"
DL_BYTES=1024000        # 10 MB chunk per iteration
DL_TIMEOUT=30            # curl hard timeout (s)
PING_TIMEOUT=10          # ping deadline (s)

# ── Colours ─────────────────────────────────
RED='\033[0;31m'; YEL='\033[0;33m'; GRN='\033[0;32m'
CYA='\033[0;36m'; BLD='\033[1m'; RST='\033[0m'

# ── Pre-flight checks ────────────────────────
die() { echo -e "${RED}[ERROR]${RST} $*" >&2; exit 1; }

command -v curl  >/dev/null 2>&1 || die "curl not found"
command -v ping  >/dev/null 2>&1 || die "ping not found"

# Verify interface exists and is UP
ip link show "$INTERFACE" >/dev/null 2>&1 \
  || die "Interface $INTERFACE not found"

IP_ADDR=$(ip -4 addr show "$INTERFACE" 2>/dev/null \
  | awk '/inet / {print $2}' | cut -d/ -f1 | head -1)

[[ -n "$IP_ADDR" ]] \
  || die "No IPv4 address on $INTERFACE — is the modem connected?"

# Verify routing: a quick 3-packet probe before the loop
echo -e "${CYA}[init]${RST} Verifying connectivity on $INTERFACE ($IP_ADDR)..."
if ! ping -c 3 -W 5 -I "$INTERFACE" "$PING_HOST" >/dev/null 2>&1; then
  die "Pre-flight ping failed via $INTERFACE. Check modem/APN."
fi

# ── CSV header ──────────────────────────────
echo "timestamp,latency_min_ms,latency_avg_ms,latency_max_ms,latency_stddev_ms,packet_loss_pct,download_bps,download_mbps" \
  > "$LOG_FILE"

# ── Signal / exit handler ───────────────────
ITER=0
cleanup() {
  echo ""
  echo -e "${BLD}── Test stopped after $ITER iterations ──${RST}"
  echo -e "Log saved to: ${GRN}$LOG_FILE${RST}"
  summarise
  exit 0
}
trap cleanup INT TERM

# ── Summary stats (awk, no bc needed) ───────
summarise() {
  [[ $ITER -eq 0 ]] && return
  awk -F',' 'NR>1 {
    sum_lat+=$3; sum_dl+=$7; n++
    if ($3>0 && ($3<min_lat || min_lat==0)) min_lat=$3
    if ($3>max_lat) max_lat=$3
    if ($7>max_dl) max_dl=$7
  }
  END {
    if(n==0) exit
    printf "\n%-22s %s\n","Samples:", n
    printf "%-22s %.1f ms  (min %.1f / max %.1f)\n",\
      "Avg latency:", sum_lat/n, min_lat, max_lat
    printf "%-22s %.2f Mbps  (peak %.2f)\n",\
      "Avg download:", sum_dl/n/1e6, max_dl/1e6
  }' "$LOG_FILE"
}

# ── Helper: coloured speed label ─────────────
speed_label() {   # arg: bps (float)
  local mbps; mbps=$(awk "BEGIN{printf \"%.2f\",$1/1e6}")
  if   awk "BEGIN{exit !($1 > 3000000)}"; then
    echo -e "${GRN}${mbps} Mbps${RST}"
  elif awk "BEGIN{exit !($1 > 500000)}";  then
    echo -e "${YEL}${mbps} Mbps${RST}"
  else
    echo -e "${RED}${mbps} Mbps${RST}"
  fi
}

# ── Main loop ────────────────────────────────
END_TIME=$(( SECONDS + DURATION ))
echo ""
echo -e "${BLD}LTE Stress Test${RST} — interface: ${CYA}$INTERFACE${RST}  IP: $IP_ADDR"
echo -e "Duration: ${DURATION}s  |  Log: ${GRN}$LOG_FILE${RST}"
echo -e "Press ${BLD}Ctrl+C${RST} to stop early.\n"
printf "%-20s %-12s %-12s %-14s %-6s\n" \
  "Timestamp" "Latency" "Stddev" "Download" "Loss%"
printf '%0.s─' {1..66}; echo

while [[ $SECONDS -lt $END_TIME ]]; do
  TS=$(date +"%Y-%m-%d %H:%M:%S")

  # ── 1. Ping (forced via interface name, not IP, for reliability) ──
  PING_RAW=$(ping -c "$PING_COUNT" \
                  -W 3 \
                  -I "$INTERFACE" \
                  -q \
                  "$PING_HOST" 2>/dev/null)

  # Extract min/avg/max/mdev from final summary line
  PING_STATS=$(echo "$PING_RAW" | awk -F'[=/]' '/rtt/{print $5,$6,$7,$8}')
  P_MIN=$(echo "$PING_STATS" | awk '{print $1}')
  P_AVG=$(echo "$PING_STATS" | awk '{print $2}')
  P_MAX=$(echo "$PING_STATS" | awk '{print $3}')
  P_STD=$(echo "$PING_STATS" | awk '{print $4}')
  LOSS=$(echo "$PING_RAW"   | awk -F'[,%]' '/packet loss/{for(i=1;i<=NF;i++) if($i~/[0-9]/ && $(i+1)~"packet") print $i+0}')

  # Defaults on failure
  P_MIN="${P_MIN:-0}"; P_AVG="${P_AVG:-0}"
  P_MAX="${P_MAX:-0}"; P_STD="${P_STD:-0}"
  LOSS="${LOSS:-100}"

  # ── 2. Download via ppp0 ─────────────────
  SPEED=$(curl \
    --interface "$INTERFACE" \
    --range "0-${DL_BYTES}" \
    --output /dev/null \
    --silent \
    --max-time "$DL_TIMEOUT" \
    --connect-timeout 10 \
    --retry 1 \
    --retry-delay 2 \
    --write-out "%{speed_download}" \
    "$DL_URL" 2>/dev/null)

  # curl returns empty string or "0" on failure
  [[ -z "$SPEED" || "$SPEED" == "0.000" ]] && SPEED="0"

  # ── 3. Log & display ─────────────────────
  echo "$TS,$P_MIN,$P_AVG,$P_MAX,$P_STD,$LOSS,$SPEED,$(awk "BEGIN{printf \"%.3f\",$SPEED/1e6}")" \
    >> "$LOG_FILE"

  LAT_COL="${P_AVG} ms"
  if   awk "BEGIN{exit !($P_AVG>200||$P_AVG==0)}"; then LAT_COL="${RED}${LAT_COL}${RST}"
  elif awk "BEGIN{exit !($P_AVG>100)}";             then LAT_COL="${YEL}${LAT_COL}${RST}"
  else                                                   LAT_COL="${GRN}${LAT_COL}${RST}"
  fi

  LOSS_COL="${LOSS}%"
  [[ "$LOSS" != "0" ]] && LOSS_COL="${YEL}${LOSS_COL}${RST}"

  printf "%-20s %-22b %-22b %-24b %-6b\n" \
    "$TS" \
    "$LAT_COL" \
    "±${P_STD} ms" \
    "$(speed_label "$SPEED")" \
    "$LOSS_COL"

  (( ITER++ ))
done

echo ""
echo -e "${GRN}Test complete.${RST}"
summarise
echo -e "\nLog: ${GRN}$LOG_FILE${RST}"