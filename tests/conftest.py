"""
pytest configuration: spins up a mock CoinGecko server and the crypto proxy server
so tests never hit the real CoinGecko API (no rate limits, no flakiness).
"""
import json
import os
import subprocess
import sys
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

import pytest
import requests

# ── Static fixture data (realistic CoinGecko response shape) ─────────────────
FIXTURE_COINS = [
    {
        "id": "bitcoin", "symbol": "BTC", "name": "Bitcoin",
        "image": "https://example.com/btc.png",
        "current_price": 68000, "market_cap": 1340000000000,
        "market_cap_rank": 1, "price_change_percentage_24h": 2.5,
        "high_24h": 69000, "low_24h": 67000,
    },
    {
        "id": "ethereum", "symbol": "ETH", "name": "Ethereum",
        "image": "https://example.com/eth.png",
        "current_price": 2000, "market_cap": 240000000000,
        "market_cap_rank": 2, "price_change_percentage_24h": -1.2,
        "high_24h": 2050, "low_24h": 1950,
    },
    {
        "id": "tether", "symbol": "USDT", "name": "Tether",
        "image": "https://example.com/usdt.png",
        "current_price": 1.0, "market_cap": 110000000000,
        "market_cap_rank": 3, "price_change_percentage_24h": 0.01,
        "high_24h": 1.001, "low_24h": 0.999,
    },
]

# Extend to 20 coins so count assertions pass
for i in range(4, 21):
    FIXTURE_COINS.append({
        "id": f"coin-{i}", "symbol": f"C{i}",  "name": f"Coin {i}",
        "image": f"https://example.com/c{i}.png",
        "current_price": 100 * i, "market_cap": 1000000000 * i,
        "market_cap_rank": i, "price_change_percentage_24h": float(i % 5),
        "high_24h": 110 * i, "low_24h": 90 * i,
    })

# EUR prices are ~0.92x USD; GBP ~0.79x
FX = {"usd": 1.0, "eur": 0.92, "gbp": 0.79}


class MockCoinGeckoHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        currency = params.get("vs_currency", ["usd"])[0].lower()
        rate = FX.get(currency, 1.0)

        coins = []
        for c in FIXTURE_COINS:
            coin = dict(c)
            for field in ("current_price", "market_cap", "high_24h", "low_24h"):
                if coin[field] is not None:
                    coin[field] = round(coin[field] * rate, 4)
            coins.append(coin)

        body = json.dumps(coins).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)


# ── Session-scoped fixtures ───────────────────────────────────────────────────

@pytest.fixture(scope="session")
def mock_coingecko():
    """Start a mock CoinGecko server in a background thread."""
    server = HTTPServer(("127.0.0.1", 18765), MockCoinGeckoHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield "http://127.0.0.1:18765"
    server.shutdown()


@pytest.fixture(scope="session")
def crypto_server(mock_coingecko):
    """Start the crypto proxy server pointing at the mock CoinGecko."""
    env = os.environ.copy()
    env["COINGECKO_BASE_URL"] = mock_coingecko
    env["PORT"] = "13000"

    server_path = os.path.join(os.path.dirname(__file__), "..", "server.py")
    proc = subprocess.Popen(
        [sys.executable, server_path],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Wait until ready
    for _ in range(20):
        try:
            requests.get("http://localhost:13000", timeout=1)
            break
        except Exception:
            time.sleep(0.3)

    yield "http://localhost:13000"
    proc.terminate()
    proc.wait()
