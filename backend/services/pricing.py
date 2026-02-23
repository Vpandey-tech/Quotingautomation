"""
Metal Pricing Service — Phase 3 (v3 — Production)

Price sources (in order of priority):
1. metals.dev API         — free tier (100 req/month), LME data, no credit card
2. World Bank Commodities — free, no key, updated monthly
3. Hardcoded fallback     — LME-based estimates, Feb 2026

All prices are returned in USD/kg.

Why metals.dev?
  - Reliable LME-sourced data (lme_aluminum, lme_copper, lme_nickel, etc.)
  - Free tier: 100 requests/month (with 6hr cache = ~4/day = ~120/month)
  - Returns JSON with `unit=kg` support → direct USD/kg, no conversion needed
  - No credit card required for free tier
"""

import os, httpx
from datetime import datetime, timedelta
from typing import Optional

# ── Material catalogue ────────────────────────────────────────────────────────
# Machinability ratings (Gemini ref: SS304 takes 2.5× longer than Al 6061)
MATERIALS = {
    "aluminum_6061": {
        "name":          "Aluminum 6061",
        "density":       2.70,
        "price_usd_kg":  2.50,      # LME Al ~$2,500/ton (Feb 2026)
        "metals_dev_key": "lme_aluminum",
        "wb_code":       "PALUM",
        "mrr_cm3_hr":    420,
        "machinability": 1.00,
        "finish_factor": 1.0,
    },
    "stainless_steel_304": {
        "name":          "Stainless Steel 304",
        "density":       7.93,
        "price_usd_kg":  2.90,
        "metals_dev_key": None,     # Derived from nickel price
        "wb_code":       None,
        "mrr_cm3_hr":    168,       # 2.5× slower than Al
        "machinability": 0.40,
        "finish_factor": 1.3,
    },
    "mild_steel": {
        "name":          "Mild Steel (AISI 1018)",
        "density":       7.85,
        "price_usd_kg":  0.75,
        "metals_dev_key": None,     # No direct LME ticker
        "wb_code":       "PIORECR",
        "mrr_cm3_hr":    250,
        "machinability": 0.60,
        "finish_factor": 1.0,
    },
    "titanium_ti6al4v": {
        "name":          "Titanium Ti-6Al-4V",
        "density":       4.43,
        "price_usd_kg":  30.00,
        "metals_dev_key": None,
        "wb_code":       None,
        "mrr_cm3_hr":    35,
        "machinability": 0.18,
        "finish_factor": 2.5,
    },
    "copper": {
        "name":          "Copper (C101)",
        "density":       8.96,
        "price_usd_kg":  9.60,
        "metals_dev_key": "lme_copper",
        "wb_code":       "PCOPP",
        "mrr_cm3_hr":    320,
        "machinability": 0.70,
        "finish_factor": 1.1,
    },
    "brass_360": {
        "name":          "Brass (C360 Free-Machining)",
        "density":       8.50,
        "price_usd_kg":  7.40,
        "metals_dev_key": None,     # ~65% copper + 35% zinc
        "wb_code":       None,
        "mrr_cm3_hr":    510,
        "machinability": 1.00,
        "finish_factor": 0.9,
    },
    "inconel_718": {
        "name":          "Inconel 718",
        "density":       8.19,
        "price_usd_kg":  58.00,
        "metals_dev_key": "lme_nickel",   # Ni as proxy × 6 alloy premium
        "wb_code":       "PNICK",
        "mrr_cm3_hr":    18,
        "machinability": 0.08,
        "finish_factor": 4.0,
    },
    "aluminum_7075": {
        "name":          "Aluminum 7075-T6",
        "density":       2.81,
        "price_usd_kg":  4.20,
        "metals_dev_key": "lme_aluminum",
        "wb_code":       "PALUM",
        "mrr_cm3_hr":    380,
        "machinability": 0.85,
        "finish_factor": 1.1,
    },
    "stainless_steel_316l": {
        "name":          "Stainless Steel 316L",
        "density":       7.99,
        "price_usd_kg":  3.50,
        "metals_dev_key": None,
        "wb_code":       None,
        "mrr_cm3_hr":    150,
        "machinability": 0.35,
        "finish_factor": 1.4,
    },
    "tool_steel_d2": {
        "name":          "Tool Steel D2",
        "density":       7.70,
        "price_usd_kg":  5.50,
        "metals_dev_key": None,
        "wb_code":       None,
        "mrr_cm3_hr":    60,
        "machinability": 0.25,
        "finish_factor": 2.0,
    },
    "pla_plastic": {
        "name":          "PLA (3D Print)",
        "density":       1.25,
        "price_usd_kg":  25.00,     # Filament price
        "metals_dev_key": None,
        "wb_code":       None,
        "mrr_cm3_hr":    60,
        "machinability": 1.00,
        "finish_factor": 0.5,
    },
    "abs_plastic": {
        "name":          "ABS (3D Print)",
        "density":       1.04,
        "price_usd_kg":  22.00,
        "metals_dev_key": None,
        "wb_code":       None,
        "mrr_cm3_hr":    55,
        "machinability": 1.00,
        "finish_factor": 0.6,
    },
}

# ── Price cache ───────────────────────────────────────────────────────────────
_price_cache: Optional[dict] = None
_cache_time:  Optional[datetime] = None
CACHE_TTL = timedelta(hours=6)


async def get_live_prices() -> dict:
    """
    Fetch current metal prices with cascading fallback.
    """
    global _price_cache, _cache_time

    if _price_cache and _cache_time and (datetime.utcnow() - _cache_time) < CACHE_TTL:
        return _price_cache

    fallback = {mid: m["price_usd_kg"] for mid, m in MATERIALS.items()}

    # ── Priority 1: metals.dev (LME data, free tier) ─────────────────────────
    api_key = os.getenv("METALS_DEV_API_KEY", "")
    if api_key:
        result = await _fetch_metals_dev(api_key, fallback)
        if result:
            _price_cache = result
            _cache_time  = datetime.utcnow()
            return result

    # ── Priority 2: World Bank (free, no key) ────────────────────────────────
    result = await _fetch_world_bank(fallback)
    if result:
        _price_cache = result
        _cache_time  = datetime.utcnow()
        return result

    # ── Priority 3: Hardcoded fallback ───────────────────────────────────────
    result = {
        "prices":    fallback,
        "source":    "fallback",
        "timestamp": datetime.utcnow().isoformat(),
        "note":      "Using LME-based estimates (Feb 2026). Add METALS_DEV_API_KEY for live prices.",
    }
    _price_cache = result
    _cache_time  = datetime.utcnow()
    return result


async def _fetch_metals_dev(api_key: str, fallback: dict) -> Optional[dict]:
    """
    metals.dev — LME official data.
    Free tier: 100 requests/month, no credit card.
    Endpoint: GET /v1/latest?api_key=KEY&currency=USD&unit=kg
    Returns prices in USD/kg directly (no conversion needed).
    """
    try:
        url = f"https://api.metals.dev/v1/latest?api_key={api_key}&currency=USD&unit=kg"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)

        if resp.status_code != 200:
            return None

        data = resp.json()
        if data.get("status") != "success":
            return None

        metals = data.get("metals", {})
        prices = dict(fallback)

        # Map metals.dev keys → our material IDs (already in USD/kg)
        for mid, mat in MATERIALS.items():
            dev_key = mat.get("metals_dev_key")
            if dev_key and dev_key in metals:
                raw_price = float(metals[dev_key])
                if mid == "inconel_718":
                    # Nickel is proxy — apply 6× alloy premium for Inconel 718
                    prices[mid] = round(raw_price * 6, 2)
                else:
                    prices[mid] = round(raw_price, 4)

        # Derive brass from copper + zinc if available
        if "lme_copper" in metals and "lme_zinc" in metals:
            # Brass C360 ≈ 61.5% Cu + 35.5% Zn + 3% Pb
            cu_kg = float(metals["lme_copper"])
            zn_kg = float(metals["lme_zinc"])
            prices["brass_360"] = round(cu_kg * 0.615 + zn_kg * 0.355 + 0.5, 2)

        # Derive SS304 from nickel if available (Ni is ~8% of SS304 cost driver)
        if "lme_nickel" in metals:
            ni_kg = float(metals["lme_nickel"])
            # SS304 ≈ base steel ($0.80/kg) + Ni surcharge (8-10% Ni content)
            prices["stainless_steel_304"] = round(0.80 + ni_kg * 0.09, 2)

        return {
            "prices":    prices,
            "source":    "metals_dev",
            "timestamp": datetime.utcnow().isoformat(),
            "note":      "Live LME prices from metals.dev API.",
        }
    except Exception:
        return None


async def _fetch_world_bank(fallback: dict) -> Optional[dict]:
    """
    World Bank Pink Sheet — completely free, no API key.
    Indicators: PALUM (Aluminum USD/mt), PCOPP (Copper USD/mt), PNICK (Nickel USD/mt)
    """
    try:
        # Fetch each indicator separately (World Bank multi-indicator is unreliable)
        indicators = {
            "PALUM": "aluminum_6061",
            "PCOPP": "copper",
            "PNICK": None,  # Used for Inconel derivation
        }
        prices = dict(fallback)
        fetched_any = False

        async with httpx.AsyncClient(timeout=12.0) as client:
            for ind_id, mat_id in indicators.items():
                try:
                    url = (
                        f"https://api.worldbank.org/v2/en/indicator/{ind_id}"
                        "?format=json&mrv=1&frequency=M&per_page=1"
                    )
                    resp = await client.get(url)
                    if resp.status_code != 200:
                        continue

                    data = resp.json()
                    if not isinstance(data, list) or len(data) < 2:
                        continue

                    records = data[1] or []
                    for rec in records:
                        value = rec.get("value")
                        if value:
                            usd_per_kg = float(value) / 1000.0  # USD/mt → USD/kg
                            if mat_id:
                                prices[mat_id] = round(usd_per_kg, 4)
                            elif ind_id == "PNICK":
                                # Derive Inconel from Nickel
                                prices["inconel_718"] = round(usd_per_kg * 6, 2)
                                # Derive SS304 from Nickel
                                prices["stainless_steel_304"] = round(0.80 + usd_per_kg * 0.09, 2)
                            fetched_any = True
                            break
                except Exception:
                    continue

        if not fetched_any:
            return None

        return {
            "prices":    prices,
            "source":    "world_bank",
            "timestamp": datetime.utcnow().isoformat(),
            "note":      "Prices from World Bank Pink Sheet (most recent monthly average).",
        }
    except Exception:
        return None
