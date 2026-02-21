#!/usr/bin/env python3
"""Simple proxy server: serves static files and proxies /api/coins to CoinGecko."""
import json
import os
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

PORT = 3000
API_URL = (
    "https://api.coingecko.com/api/v3/coins/markets"
    "?vs_currency={currency}&order=market_cap_desc"
    "&per_page=20&page=1&sparkline=false&price_change_percentage=24h"
)

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=os.path.dirname(os.path.abspath(__file__)), **kwargs)

    def log_message(self, format, *args):
        pass  # suppress per-request logs

    def do_GET(self):
        if self.path.startswith("/api/coins"):
            self._proxy_coins()
        else:
            super().do_GET()

    def _proxy_coins(self):
        currency = "usd"
        if "currency=" in self.path:
            currency = self.path.split("currency=")[-1].split("&")[0]

        url = API_URL.format(currency=currency)
        try:
            req = Request(url, headers={"User-Agent": "CryptoTracker/1.0"})
            with urlopen(req, timeout=10) as resp:
                data = resp.read()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data)
        except (URLError, HTTPError) as e:
            error = json.dumps({"error": str(e)}).encode()
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(error)

if __name__ == "__main__":
    httpd = HTTPServer(("", PORT), Handler)
    print(f"🚀 Crypto Tracker running at http://localhost:{PORT}")
    httpd.serve_forever()
