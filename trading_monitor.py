#!/usr/bin/env python3
"""
Trading Monitor — surveille les grids Martin toutes les 2 minutes.
Recentre automatiquement si le prix sort du range.
Log tout. Autonome.
"""

import json
import time
import logging
import urllib.request
import subprocess
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(message)s',
    handlers=[
        logging.FileHandler('trading_monitor.log'),
        logging.StreamHandler()
    ]
)
log = logging.getLogger('trading_monitor')

VM_KEY = str(Path.home() / '.ssh' / 'martin_vm.key')
VM_HOST = 'ubuntu@141.253.108.141'
API_BASE = 'http://localhost:8081/api'

def ssh_cmd(cmd):
    """Run command on VM via SSH."""
    result = subprocess.run(
        ['ssh', '-i', VM_KEY, '-o', 'StrictHostKeyChecking=no', VM_HOST, cmd],
        capture_output=True, text=True, timeout=30
    )
    return result.stdout.strip()

def get_grid_status(instrument):
    """Get grid status from Martin API."""
    raw = ssh_cmd(f'curl -s {API_BASE}/grid/status/{instrument} 2>/dev/null')
    if raw and raw.startswith('{'):
        return json.loads(raw)
    return None

def get_active_grids():
    """Get list of active grid instruments."""
    raw = ssh_cmd(f'curl -s {API_BASE}/grid/active 2>/dev/null')
    if raw and raw.startswith('['):
        return json.loads(raw)
    return []

def get_kraken_price(pair):
    """Get current price from Kraken public API."""
    try:
        resp = urllib.request.urlopen(
            f'https://api.kraken.com/0/public/Ticker?pair={pair}',
            timeout=10
        )
        data = json.loads(resp.read())
        for key, val in data.get('result', {}).items():
            return float(val['c'][0])
    except Exception:
        return None

def recenter_grid(instrument, capital, leverage, spacing, levels, max_loss):
    """Stop and restart grid at current price."""
    log.info(f"RECENTER {instrument}")
    ssh_cmd(f'curl -s -X POST {API_BASE}/grid/stop/{instrument} 2>/dev/null')
    time.sleep(3)
    result = ssh_cmd(
        f'curl -s -X POST "{API_BASE}/grid/start?instrument={instrument}'
        f'&capital={capital}&leverage={leverage}&gridSpacingPct={spacing}'
        f'&totalLevels={levels}&maxLossPercent={max_loss}" 2>/dev/null'
    )
    log.info(f"Recentered: {result[:100]}")

# Kraken pair mapping
KRAKEN_PAIRS = {
    'PF_ADAUSD': 'ADAUSD',
    'PF_DOTUSD': 'DOTUSD',
    'PF_ETHUSD': 'ETHUSD',
    'PF_SOLUSD': 'SOLUSD',
    'PF_LINKUSD': 'LINKUSD',
    'PF_XRPUSD': 'XRPUSD',
}

def monitor_cycle():
    """One monitoring cycle."""
    grids = get_active_grids()
    if not grids:
        log.info("No active grids")
        return

    for instrument in grids:
        status = get_grid_status(instrument)
        if not status or not status.get('active'):
            continue

        center = status['centerPrice']
        upper = status['upperBound']
        lower = status['lowerBound']
        rt = status['completedRoundTrips']
        profit = status['totalProfit']
        fills = len(status.get('fills', []))
        capital = status['capital']
        leverage = status['leverage']
        spacing = round(status['gridSpacing'] / center * 100, 1) if center > 0 else 2.0
        levels = status['totalLevels']
        max_loss = status['maxLossPercent']

        # Get current price
        kraken_pair = KRAKEN_PAIRS.get(instrument, instrument.replace('PF_', ''))
        current_price = get_kraken_price(kraken_pair)

        if current_price is None:
            log.warning(f"{instrument}: can't get price")
            continue

        # Check if price is outside grid range
        margin = (upper - lower) * 0.1  # 10% buffer
        outside = current_price > upper + margin or current_price < lower - margin

        # Log status
        distance_pct = abs(current_price - center) / center * 100
        log.info(
            f"{instrument}: price={current_price:.4f} center={center:.4f} "
            f"({distance_pct:+.1f}%) RT={rt} profit={profit} fills={fills}"
            f"{' [OUTSIDE RANGE]' if outside else ''}"
        )

        # Check fills
        if fills > 0:
            last_fill = status['fills'][-1]
            log.info(f"  Last fill: {last_fill['side']} @ {last_fill['price']} at {last_fill['filledAt'][:19]}")

        # Auto-recenter if price is outside range
        if outside:
            log.warning(f"{instrument}: price {current_price} outside range [{lower}, {upper}] — recentering")
            recenter_grid(instrument, capital, leverage, spacing, levels, max_loss)

def main():
    log.info("=" * 50)
    log.info("Trading Monitor started")
    log.info("Monitoring every 2 minutes")
    log.info("=" * 50)

    while True:
        try:
            monitor_cycle()
        except Exception as e:
            log.error(f"Monitor error: {e}")

        time.sleep(120)  # 2 minutes

if __name__ == '__main__':
    main()
