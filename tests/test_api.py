"""
Crypto Tracker API Test Suite
Tests the /api/coins endpoint for availability, currency support, and data integrity.
Run locally:  pytest tests/test_api.py -v
"""
import pytest
import requests

REQUIRED_FIELDS = [
    "id", "symbol", "name", "current_price",
    "market_cap", "price_change_percentage_24h", "high_24h", "low_24h"
]


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def coins_usd(crypto_server):
    r = requests.get(f"{crypto_server}/api/coins", params={"currency": "usd"}, timeout=10)
    r.raise_for_status()
    return r.json()

@pytest.fixture(scope="module")
def coins_eur(crypto_server):
    r = requests.get(f"{crypto_server}/api/coins", params={"currency": "eur"}, timeout=10)
    r.raise_for_status()
    return r.json()

@pytest.fixture(scope="module")
def coins_gbp(crypto_server):
    r = requests.get(f"{crypto_server}/api/coins", params={"currency": "gbp"}, timeout=10)
    r.raise_for_status()
    return r.json()


# ── Test Case 1: Server Availability ─────────────────────────────────────────

class TestServerAvailability:
    def test_returns_http_200(self, crypto_server):
        r = requests.get(f"{crypto_server}/api/coins", params={"currency": "usd"}, timeout=10)
        assert r.status_code == 200

    def test_response_time_under_5_seconds(self, crypto_server):
        r = requests.get(f"{crypto_server}/api/coins", params={"currency": "usd"}, timeout=10)
        assert r.elapsed.total_seconds() < 5, (
            f"Response took {r.elapsed.total_seconds():.2f}s (limit: 5s)"
        )

    def test_response_is_json_array(self, coins_usd):
        assert isinstance(coins_usd, list), "Response should be a JSON array"

    def test_response_is_not_empty(self, coins_usd):
        assert len(coins_usd) > 0, "Response array should not be empty"

    def test_all_coins_have_required_fields(self, coins_usd):
        for coin in coins_usd:
            for field in REQUIRED_FIELDS:
                assert field in coin, f"Coin '{coin.get('name')}' missing field: '{field}'"

    def test_all_prices_are_non_negative(self, coins_usd):
        for coin in coins_usd:
            assert coin["current_price"] is not None, f"{coin['name']}: current_price is null"
            assert coin["current_price"] >= 0, f"{coin['name']}: current_price is negative"


# ── Test Case 2: Currency Support ─────────────────────────────────────────────

class TestCurrencySupport:
    @pytest.mark.parametrize("currency", ["usd", "eur", "gbp"])
    def test_currency_returns_200(self, crypto_server, currency):
        r = requests.get(f"{crypto_server}/api/coins", params={"currency": currency}, timeout=10)
        assert r.status_code == 200, f"Currency '{currency}' returned {r.status_code}"

    @pytest.mark.parametrize("currency", ["usd", "eur", "gbp"])
    def test_currency_returns_non_empty_array(self, crypto_server, currency):
        r = requests.get(f"{crypto_server}/api/coins", params={"currency": currency}, timeout=10)
        data = r.json()
        assert isinstance(data, list) and len(data) > 0

    def test_eur_bitcoin_price_is_positive(self, coins_eur):
        btc = next((c for c in coins_eur if c["id"] == "bitcoin"), None)
        assert btc is not None, "Bitcoin not found in EUR response"
        assert btc["current_price"] > 0

    def test_gbp_bitcoin_price_is_positive(self, coins_gbp):
        btc = next((c for c in coins_gbp if c["id"] == "bitcoin"), None)
        assert btc is not None, "Bitcoin not found in GBP response"
        assert btc["current_price"] > 0

    def test_usd_price_differs_from_eur_price(self, coins_usd, coins_eur):
        """Prices should differ across currencies (FX sanity check)."""
        btc_usd = next((c for c in coins_usd if c["id"] == "bitcoin"), None)
        btc_eur = next((c for c in coins_eur if c["id"] == "bitcoin"), None)
        assert btc_usd and btc_eur, "Bitcoin missing from one of the responses"
        assert btc_usd["current_price"] != btc_eur["current_price"], (
            "USD and EUR prices should not be equal"
        )


# ── Test Case 3: Data Integrity ───────────────────────────────────────────────

class TestDataIntegrity:
    def test_at_least_10_coins_returned(self, coins_usd):
        assert len(coins_usd) >= 10, f"Expected >= 10 coins, got {len(coins_usd)}"

    @pytest.mark.parametrize("coin_id", ["bitcoin", "ethereum", "tether"])
    def test_top_coins_are_present(self, coins_usd, coin_id):
        found = any(c["id"] == coin_id for c in coins_usd)
        assert found, f"Expected top coin '{coin_id}' not found in response"

    def test_24h_high_gte_low(self, coins_usd):
        for coin in coins_usd:
            if coin["high_24h"] is not None and coin["low_24h"] is not None:
                assert coin["high_24h"] >= coin["low_24h"], (
                    f"{coin['name']}: 24h high ({coin['high_24h']}) < 24h low ({coin['low_24h']})"
                )

    def test_market_cap_is_positive(self, coins_usd):
        for coin in coins_usd:
            if coin["market_cap"] is not None:
                assert coin["market_cap"] >= 0, f"{coin['name']}: market_cap is negative"

    def test_coin_symbols_are_uppercase(self, coins_usd):
        for coin in coins_usd:
            assert coin["symbol"] == coin["symbol"].upper(), (
                f"Symbol '{coin['symbol']}' for {coin['name']} should be uppercase"
            )
