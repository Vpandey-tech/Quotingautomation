"""
Metal Pricing Service — Phase 5 (INR Edition)

Price sources (in order of priority):
1. metals.dev API         — free tier (100 req/month), LME data, no credit card
2. World Bank Commodities — free, no key, updated monthly
3. Hardcoded fallback     — LME-based estimates, March 2026

All base prices are stored in USD/kg internally.
Final prices are converted to INR/kg using:
  - Local Indian Base Rates (Pune/Ahmedabad market defaults)
  - Scaled by global commodity price fluctuation index if live API is connected.
  - Falls back to local Indian base rates directly to avoid inflated quotes.
"""

import os, httpx, json
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
        "base_inr_kg":   225.0,
        "grade":         "6061-T6",
        "standard":      "ASTM B211",
        "tensile_strength": "310 MPa",
        "yield_strength":   "276 MPa",
        "notes":         "Excellent weldability and structural strength",
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
        "base_inr_kg":   320.0,
        "grade":         "7075-T6",
        "standard":      "ASTM B211",
        "tensile_strength": "572 MPa",
        "yield_strength":   "503 MPa",
        "notes":         "Aircraft grade, high strength-to-weight ratio",
    },
    "commercial_aluminium_he30": {
        "name":          "Commercial Aluminium (HE30)",
        "density":       2.70,
        "price_usd_kg":  2.20,
        "metals_dev_key": "lme_aluminum",
        "wb_code":       "PALUM",
        "mrr_cm3_hr":    400,
        "machinability": 0.95,
        "finish_factor": 1.0,
        "base_inr_kg":   210.0,
        "grade":         "HE30",
        "standard":      "IS 737",
        "tensile_strength": "290 MPa",
        "yield_strength":   "250 MPa",
        "notes":         "Common Indian structural alloy",
    },
    "mild_steel": {
        "name":          "Mild Steel (A36 / IS 2062)",
        "density":       7.85,
        "price_usd_kg":  0.75,
        "metals_dev_key": "lme_iron",
        "wb_code":       "PIORECR",
        "mrr_cm3_hr":    250,
        "machinability": 0.70,
        "finish_factor": 1.0,
        "base_inr_kg":   70.0,
        "grade":         "A36",
        "standard":      "IS 2062 E250",
        "tensile_strength": "400-550 MPa",
        "yield_strength":   "250-350 MPa",
        "notes":         "Most common structural steel",
    },
    "low_carbon_steel_1018": {
        "name":          "Low Carbon Steel (1018)",
        "density":       7.87,
        "price_usd_kg":  0.80,
        "metals_dev_key": None,
        "wb_code":       None,
        "mrr_cm3_hr":    240,
        "machinability": 0.65,
        "finish_factor": 1.0,
        "base_inr_kg":   75.0,
        "grade":         "1018",
        "standard":      "IS 1570 Fe410",
        "tensile_strength": "380-450 MPa",
        "yield_strength":   "205-305 MPa",
        "notes":         "Good weldability",
    },
    "medium_carbon_steel_1045": {
        "name":          "Medium Carbon Steel (1045)",
        "density":       7.85,
        "price_usd_kg":  0.85,
        "metals_dev_key": None,
        "wb_code":       None,
        "mrr_cm3_hr":    220,
        "machinability": 0.60,
        "finish_factor": 1.1,
        "base_inr_kg":   80.0,
        "grade":         "1045",
        "standard":      "IS 1570 Fe500",
        "tensile_strength": "550-700 MPa",
        "yield_strength":   "350-550 MPa",
        "notes":         "Higher strength, lower ductility",
    },
    "high_carbon_steel_1095": {
        "name":          "High Carbon Steel (1095)",
        "density":       7.86,
        "price_usd_kg":  0.90,
        "metals_dev_key": None,
        "wb_code":       None,
        "mrr_cm3_hr":    200,
        "machinability": 0.45,
        "finish_factor": 1.2,
        "base_inr_kg":   85.0,
        "grade":         "1095",
        "standard":      "IS 1570 Fe600",
        "tensile_strength": "650-900 MPa",
        "yield_strength":   "400-650 MPa",
        "notes":         "High strength, low ductility",
    },
    "free_machining_steel_1212": {
        "name":          "Free Machining Steel (1212)",
        "density":       7.85,
        "price_usd_kg":  0.78,
        "metals_dev_key": None,
        "wb_code":       None,
        "mrr_cm3_hr":    350,
        "machinability": 0.90,
        "finish_factor": 0.9,
        "base_inr_kg":   70.0,
        "grade":         "1212",
        "standard":      "IS 1570",
        "tensile_strength": "400-550 MPa",
        "yield_strength":   "205-350 MPa",
        "notes":         "High sulfur for machinability",
    },
    "alloy_steel_4140": {
        "name":          "Alloy Steel (4140)",
        "density":       7.85,
        "price_usd_kg":  1.20,
        "metals_dev_key": None,
        "wb_code":       None,
        "mrr_cm3_hr":    180,
        "machinability": 0.65,
        "finish_factor": 1.2,
        "base_inr_kg":   115.0,
        "grade":         "4140",
        "standard":      "IS 4031",
        "tensile_strength": "650-900 MPa",
        "yield_strength":   "415-700 MPa",
        "notes":         "Chromium-molybdenum",
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
        "base_inr_kg":   450.0,
        "grade":         "D2",
        "standard":      "IS 4454",
        "tensile_strength": "1500-2000 MPa",
        "yield_strength":   "1000-1500 MPa",
        "notes":         "High carbon, high chromium",
    },
    "stainless_steel_304": {
        "name":          "Stainless Steel 304",
        "density":       8.00,
        "price_usd_kg":  2.90,
        "metals_dev_key": "lme_nickel",
        "wb_code":       None,
        "mrr_cm3_hr":    168,
        "machinability": 0.50,
        "finish_factor": 1.3,
        "base_inr_kg":   275.0,
        "grade":         "304",
        "standard":      "IS 5517",
        "tensile_strength": "500-700 MPa",
        "yield_strength":   "205-300 MPa",
        "notes":         "Most common stainless",
    },
    "stainless_steel_304l": {
        "name":          "Stainless Steel 304L",
        "density":       8.00,
        "price_usd_kg":  3.10,
        "metals_dev_key": "lme_nickel",
        "wb_code":       None,
        "mrr_cm3_hr":    160,
        "machinability": 0.50,
        "finish_factor": 1.3,
        "base_inr_kg":   295.0,
        "grade":         "304L",
        "standard":      "IS 5517",
        "tensile_strength": "480-670 MPa",
        "yield_strength":   "170-280 MPa",
        "notes":         "Low carbon version of 304",
    },
    "stainless_steel_316": {
        "name":          "Stainless Steel 316",
        "density":       8.00,
        "price_usd_kg":  3.60,
        "metals_dev_key": "lme_nickel",
        "wb_code":       None,
        "mrr_cm3_hr":    152,
        "machinability": 0.45,
        "finish_factor": 1.4,
        "base_inr_kg":   375.0,
        "grade":         "316",
        "standard":      "IS 5517",
        "tensile_strength": "500-700 MPa",
        "yield_strength":   "205-300 MPa",
        "notes":         "Marine grade, corrosion resistant",
    },
    "stainless_steel_316l": {
        "name":          "Stainless Steel 316L",
        "density":       8.00,
        "price_usd_kg":  3.50,
        "metals_dev_key": "lme_nickel",
        "wb_code":       None,
        "mrr_cm3_hr":    150,
        "machinability": 0.45,
        "finish_factor": 1.4,
        "base_inr_kg":   395.0,
        "grade":         "316L",
        "standard":      "IS 5517",
        "tensile_strength": "480-670 MPa",
        "yield_strength":   "170-280 MPa",
        "notes":         "Low carbon version of 316",
    },
    "stainless_steel_410": {
        "name":          "Stainless Steel 410",
        "density":       7.75,
        "price_usd_kg":  2.20,
        "metals_dev_key": None,
        "wb_code":       None,
        "mrr_cm3_hr":    180,
        "machinability": 0.60,
        "finish_factor": 1.2,
        "base_inr_kg":   225.0,
        "grade":         "410",
        "standard":      "IS 5517",
        "tensile_strength": "450-650 MPa",
        "yield_strength":   "205-350 MPa",
        "notes":         "Martensitic, heat treatable",
    },
    "cast_iron_gray": {
        "name":          "Cast Iron (Gray Class 20)",
        "density":       7.20,
        "price_usd_kg":  1.10,
        "metals_dev_key": None,
        "wb_code":       None,
        "mrr_cm3_hr":    300,
        "machinability": 0.80,
        "finish_factor": 0.9,
        "base_inr_kg":   100.0,
        "grade":         "Class 20",
        "standard":      "IS 210",
        "tensile_strength": "140-200 MPa",
        "yield_strength":   "N/A",
        "notes":         "Good vibration damping",
    },
    "cast_iron_ductile": {
        "name":          "Cast Iron (Ductile 60-40-18)",
        "density":       7.10,
        "price_usd_kg":  1.60,
        "metals_dev_key": None,
        "wb_code":       None,
        "mrr_cm3_hr":    250,
        "machinability": 0.70,
        "finish_factor": 1.0,
        "base_inr_kg":   150.0,
        "grade":         "60-40-18",
        "standard":      "IS 1865",
        "tensile_strength": "415-600 MPa",
        "yield_strength":   "275-450 MPa",
        "notes":         "Spheroidal graphite",
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
        "base_inr_kg":   3250.0,
        "grade":         "Grade 5",
        "standard":      "ASTM B348",
        "tensile_strength": "950 MPa",
        "yield_strength":   "880 MPa",
        "notes":         "Extremely high strength and corrosion resistance",
    },
    "copper": {
        "name":          "Copper (C101)",
        "density":       8.96,
        "price_usd_kg":  9.60,
        "metals_dev_key": "lme_copper",
        "wb_code":       "PCOPP",
        "mrr_cm3_hr":    200,
        "machinability": 0.35,
        "finish_factor": 1.0,
        "base_inr_kg":   750.0,
        "grade":         "C101",
        "standard":      "IS 191",
        "tensile_strength": "220 MPa",
        "yield_strength":   "60 MPa",
        "notes":         "Excellent electrical and thermal conductivity",
    },
    "brass_360": {
        "name":          "Brass 360",
        "density":       8.50,
        "price_usd_kg":  6.00,
        "metals_dev_key": "lme_copper",
        "wb_code":       None,
        "mrr_cm3_hr":    350,
        "machinability": 1.00,
        "finish_factor": 0.9,
        "base_inr_kg":   500.0,
        "grade":         "C360",
        "standard":      "ASTM B16",
        "tensile_strength": "330 MPa",
        "yield_strength":   "140 MPa",
        "notes":         "Highly machinable, excellent for precision details",
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
        "base_inr_kg":   3500.0,
        "grade":         "Inconel 718",
        "standard":      "ASTM B637",
        "tensile_strength": "1240 MPa",
        "yield_strength":   "1036 MPa",
        "notes":         "Nickel-based superalloy, high temperature strength",
    },
    "pla_plastic": {
        "name":          "PLA Plastic",
        "density":       1.25,
        "price_usd_kg":  2.50,
        "metals_dev_key": None,
        "wb_code":       None,
        "mrr_cm3_hr":    60,
        "machinability": 1.00,
        "finish_factor": 0.5,
        "base_inr_kg":   200.0,
        "grade":         "Standard 3D",
        "standard":      "N/A",
        "tensile_strength": "50 MPa",
        "yield_strength":   "N/A",
        "notes":         "Biodegradable, standard prototyping filament",
    },
    "abs_plastic": {
        "name":          "ABS Plastic",
        "density":       1.04,
        "price_usd_kg":  2.20,
        "metals_dev_key": None,
        "wb_code":       None,
        "mrr_cm3_hr":    55,
        "machinability": 1.00,
        "finish_factor": 0.6,
        "base_inr_kg":   175.0,
        "grade":         "Injection/3D",
        "standard":      "N/A",
        "tensile_strength": "40 MPa",
        "yield_strength":   "N/A",
        "notes":         "Impact resistant, standard durable plastic",
    },
    "nylon_plastic": {
        "name":          "Nylon (PA6)",
        "density":       1.14,
        "price_usd_kg":  3.20,
        "metals_dev_key": None,
        "wb_code":       None,
        "mrr_cm3_hr":    80,
        "machinability": 0.80,
        "finish_factor": 0.8,
        "base_inr_kg":   275.0,
        "grade":         "PA6",
        "standard":      "N/A",
        "tensile_strength": "80 MPa",
        "yield_strength":   "N/A",
        "notes":         "Excellent wear resistance and low friction",
    },
    "polycarbonate": {
        "name":          "Polycarbonate (PC)",
        "density":       1.20,
        "price_usd_kg":  3.80,
        "metals_dev_key": None,
        "wb_code":       None,
        "mrr_cm3_hr":    70,
        "machinability": 0.75,
        "finish_factor": 0.9,
        "base_inr_kg":   325.0,
        "grade":         "PC",
        "standard":      "N/A",
        "tensile_strength": "65 MPa",
        "yield_strength":   "N/A",
        "notes":         "Transparent, extremely high impact resistance",
    },
}

# LME Baseline prices corresponding to standard values
LME_BASELINE_USD = {
    "lme_aluminum": 2.50,
    "lme_copper": 9.60,
    "lme_nickel": 18.00,
}

# ── Price cache ───────────────────────────────────────────────────────────────
_price_cache: Optional[dict] = None
_cache_time:  Optional[datetime] = None
CACHE_TTL = timedelta(hours=6)


async def get_live_prices() -> dict:
    """Fetch current metal prices (USD/kg) with cascading fallback."""
    global _price_cache, _cache_time

    if _price_cache and _rate_cache_fresh():
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

    # ── Priority 1b: APISED / Metals-API ──────────────────────────────────────
    apised_key = os.getenv("APISED_METALS_API_KEY") or os.getenv("METALS_API_KEY")
    if apised_key:
        result = await _fetch_apised_metals(apised_key, fallback)
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
        "note":      "Using LME-based estimates. Add METALS_DEV_API_KEY for live prices.",
    }
    _price_cache = result
    _cache_time  = datetime.utcnow()
    return result


def _rate_cache_fresh() -> bool:
    if not _cache_time:
        return False
    return (datetime.utcnow() - _cache_time) < CACHE_TTL


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
                elif mid == "commercial_aluminium_he30":
                    prices[mid] = round(raw_price * 0.88, 4)
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


async def _fetch_apised_metals(api_key: str, fallback: dict) -> Optional[dict]:
    """APISED / Metals-API.com — standard industrial commodity API fallback."""
    try:
        url = f"https://metals-api.com/api/latest?access_key={api_key}&base=USD"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
        if resp.status_code != 200:
            url = f"https://api.metals-api.com/v1/latest?access_key={api_key}&base=USD"
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                
        if resp.status_code != 200:
            return None
            
        data = resp.json()
        if not data.get("success"):
            return None
            
        rates = data.get("rates", {})
        prices = dict(fallback)
        
        def get_usd_per_kg(symbol):
            if symbol in rates:
                rate = float(rates[symbol])
                if rate > 0:
                    if rate < 1.0:
                        price_per_ounce = 1.0 / rate
                        return round(price_per_ounce * 32.1507, 4)
                    else:
                        return round(rate, 4)
            return None

        # Aluminum
        al_price = get_usd_per_kg("LME-ALU") or get_usd_per_kg("ALU")
        if al_price:
            prices["aluminum_6061"] = al_price
            prices["aluminum_7075"] = round(al_price * 1.35, 4)
            prices["commercial_aluminium_he30"] = round(al_price * 0.88, 4)
            
        # Copper / Brass
        cu_price = get_usd_per_kg("XCU") or get_usd_per_kg("COPPER")
        if cu_price:
            prices["copper"] = cu_price
            prices["brass_360"] = round(cu_price * 0.8, 2)
            
        # Nickel / Inconel / Stainless
        ni_price = get_usd_per_kg("XNI") or get_usd_per_kg("NICKEL")
        if ni_price:
            prices["inconel_718"] = round(ni_price * 6, 2)
            prices["stainless_steel_304"] = round(0.80 + ni_price * 0.09, 2)
            prices["stainless_steel_316l"] = round(1.10 + ni_price * 0.12, 2)

        return {
            "prices":    prices,
            "source":    "apised_metals",
            "timestamp": datetime.utcnow().isoformat(),
            "note":      "Live prices from APISED / Metals-API.",
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
            "note":      "Prices from World Bank Pink Sheet.",
        }
    except Exception:
        return None

# ── Stored Prices Persistence ────────────────────────────────────────────────
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "materials_db.json")

def load_stored_prices():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                data = json.load(f)
                for mid, prices in data.items():
                    if mid in MATERIALS:
                        if "base_inr_kg" in prices:
                            MATERIALS[mid]["base_inr_kg"] = float(prices["base_inr_kg"])
                        if "price_usd_kg" in prices:
                            MATERIALS[mid]["price_usd_kg"] = float(prices["price_usd_kg"])
        except Exception as e:
            print("[PRICING] Error loading stored prices:", e)

def save_stored_prices():
    try:
        data = {
            mid: {
                "base_inr_kg": m["base_inr_kg"],
                "price_usd_kg": m["price_usd_kg"]
            }
            for mid, m in MATERIALS.items()
        }
        with open(DB_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print("[PRICING] Error saving stored prices:", e)

# Initial load on import
load_stored_prices()

