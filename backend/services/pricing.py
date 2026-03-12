"""
Metal Pricing Service — Phase 4 (INR Edition)

Price sources (in order of priority):
1. metals.dev API         — free tier (100 req/month), LME data, no credit card
2. World Bank Commodities — free, no key, updated monthly
3. Hardcoded fallback     — LME-based estimates, March 2026

All base prices are stored in USD/kg internally.
Final prices are converted to INR/kg using:
  Section A formula: INR = (USD × exchange_rate) + ₹150/kg
"""

import os, httpx
from datetime import datetime, timedelta
from typing import Optional

# ── Material catalogue ────────────────────────────────────────────────────────
MATERIALS = {
    "aluminum_6061": {
        "name":          "Aluminum 6061",
        "density":       2.70,
        "price_usd_kg":  2.50,
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
        "metals_dev_key": None,
        "wb_code":       None,
        "mrr_cm3_hr":    168,
        "machinability": 0.40,
        "finish_factor": 1.3,
    },
    "mild_steel": {
        "name":          "Mild Steel (AISI 1018 / EN-8)",
        "density":       7.85,
        "price_usd_kg":  0.75,
        "metals_dev_key": None,
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
        "metals_dev_key": None,
        "wb_code":       None,
        "mrr_cm3_hr":    510,
        "machinability": 1.00,
        "finish_factor": 0.9,
    },
    "inconel_718": {
        "name":          "Inconel 718",
        "density":       8.19,
        "price_usd_kg":  58.00,
        "metals_dev_key": "lme_nickel",
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
        "price_usd_kg":  25.00,
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
    """Fetch current metal prices (USD/kg) with cascading fallback."""
    global _price_cache, _cache_time

    if _price_cache and _cache_time and (datetime.utcnow() - _cache_time) < CACHE_TTL:
        return _price_cache

    fallback = {mid: m["price_usd_kg"] for mid, m in MATERIALS.items()}

    # ── Priority 1: metals.dev ───────────────────────────────────────────────
    api_key = os.getenv("METALS_DEV_API_KEY", "")
    if api_key:
        result = await _fetch_metals_dev(api_key, fallback)
        if result:
            _price_cache = result
            _cache_time  = datetime.utcnow()
            return result

    # ── Priority 2: World Bank ───────────────────────────────────────────────
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
        "note":      "Using LME-based estimates (Mar 2026). Add METALS_DEV_API_KEY for live prices.",
    }
    _price_cache = result
    _cache_time  = datetime.utcnow()
    return result


async def _fetch_metals_dev(api_key: str, fallback: dict) -> Optional[dict]:
    """metals.dev — LME official data, free tier."""
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

        for mid, mat in MATERIALS.items():
            dev_key = mat.get("metals_dev_key")
            if dev_key and dev_key in metals:
                raw_price = float(metals[dev_key])
                if mid == "inconel_718":
                    prices[mid] = round(raw_price * 6, 2)
                else:
                    prices[mid] = round(raw_price, 4)

        if "lme_copper" in metals and "lme_zinc" in metals:
            cu_kg = float(metals["lme_copper"])
            zn_kg = float(metals["lme_zinc"])
            prices["brass_360"] = round(cu_kg * 0.615 + zn_kg * 0.355 + 0.5, 2)

        if "lme_nickel" in metals:
            ni_kg = float(metals["lme_nickel"])
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
    """World Bank Pink Sheet — free, no API key."""
    try:
        indicators = {
            "PALUM": "aluminum_6061",
            "PCOPP": "copper",
            "PNICK": None,
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
                            usd_per_kg = float(value) / 1000.0
                            if mat_id:
                                prices[mat_id] = round(usd_per_kg, 4)
                            elif ind_id == "PNICK":
                                prices["inconel_718"] = round(usd_per_kg * 6, 2)
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
