"""
Currency Conversion Service

Fetches live USD → INR exchange rate with caching.
Provides Section A & B conversion formulas per senior's instructions.

Section A (Material Prices): INR = (USD/kg × rate) + ₹150/kg
Section B (Machine Rates):   INR = (USD/hr ÷ 10) × rate × 1.5
"""

import httpx
from datetime import datetime, timedelta
from typing import Optional

# ── Cache ────────────────────────────────────────────────────────────────────
_rate_cache: Optional[float] = None
_rate_cache_time: Optional[datetime] = None
RATE_CACHE_TTL = timedelta(hours=12)
DEFAULT_USD_INR = 85.50  # Fallback rate (March 2026 approx)


async def get_usd_to_inr() -> dict:
    """
    Fetch live USD → INR exchange rate with cascading fallback.
    Returns dict with rate, source, and timestamp.
    """
    global _rate_cache, _rate_cache_time

    if _rate_cache and _rate_cache_time and (datetime.utcnow() - _rate_cache_time) < RATE_CACHE_TTL:
        return {
            "rate": _rate_cache,
            "source": "cached",
            "timestamp": _rate_cache_time.isoformat(),
        }

    # ── Priority 1: exchangerate-api (free, no key) ──────────────────────────
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get("https://open.er-api.com/v6/latest/USD")
        if resp.status_code == 200:
            data = resp.json()
            if data.get("result") == "success":
                rate = float(data["rates"].get("INR", DEFAULT_USD_INR))
                _rate_cache = rate
                _rate_cache_time = datetime.utcnow()
                return {
                    "rate": rate,
                    "source": "exchangerate-api",
                    "timestamp": datetime.utcnow().isoformat(),
                }
    except Exception:
        pass

    # ── Priority 2: frankfurter.app (free, no key, ECB data) ─────────────────
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get("https://api.frankfurter.app/latest?from=USD&to=INR")
        if resp.status_code == 200:
            data = resp.json()
            rate = float(data.get("rates", {}).get("INR", DEFAULT_USD_INR))
            _rate_cache = rate
            _rate_cache_time = datetime.utcnow()
            return {
                "rate": rate,
                "source": "frankfurter",
                "timestamp": datetime.utcnow().isoformat(),
            }
    except Exception:
        pass

    # ── Priority 3: Hardcoded fallback ───────────────────────────────────────
    return {
        "rate": DEFAULT_USD_INR,
        "source": "fallback",
        "timestamp": datetime.utcnow().isoformat(),
        "note": "Using fallback rate. Live exchange rate APIs unreachable.",
    }


# ── Conversion formulas (per senior's instructions) ─────────────────────────

def convert_material_price(usd_per_kg: float, exchange_rate: float) -> float:
    """
    Section A: Material price conversion.
    Formula: (USD/kg × exchange_rate) + ₹150/kg
    """
    return round((usd_per_kg * exchange_rate) + 150.0, 2)


def convert_machine_rate(usd_per_hr: float, exchange_rate: float) -> float:
    """
    Section B: Machine rate conversion.
    Formula: (USD/hr ÷ 10) × exchange_rate × 1.5

    Example: $62/hr → $6.2 → 6.2 × 85.50 → ₹530.10 → × 1.5 → ₹795.15/hr
    """
    return round((usd_per_hr / 10.0) * exchange_rate * 1.5, 2)


def convert_setup_fee(usd_setup: float, exchange_rate: float) -> float:
    """
    Setup fee conversion — same formula as machine rates.
    Formula: (USD ÷ 10) × exchange_rate × 1.5
    """
    return round((usd_setup / 10.0) * exchange_rate * 1.5, 2)
