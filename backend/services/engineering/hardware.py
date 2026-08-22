"""
Hardware Lookup Client — step.parts API integration
Resolves off-the-shelf standard hardware (fasteners, bearings, standoffs, dowel pins, etc.)
by fuzzy query or spec into standard STEP models and metadata.
"""

import httpx
import logging
import os
from typing import Dict, Any, Optional, List

logger = logging.getLogger("hardware_lookup")

STEP_PARTS_BASE_URL = os.getenv("STEP_PARTS_API_URL", "https://api.step.parts/v1")
STEP_PARTS_API_KEY = os.getenv("STEP_PARTS_API_KEY", "")

# Standard fallback catalog for common standard hardware when offline / no API key
OFFLINE_HARDWARE_CATALOG: Dict[str, Dict[str, Any]] = {
    "m3_shcs": {
        "id": "fastener_m3_shcs",
        "name": "M3 Socket Head Cap Screw",
        "category": "fastener",
        "thread": "M3x0.5",
        "head_diameter_mm": 5.5,
        "head_height_mm": 3.0,
        "drive": "2.5mm Hex",
        "standard": "ISO 4762 / DIN 912",
        "step_available": False,
    },
    "m4_shcs": {
        "id": "fastener_m4_shcs",
        "name": "M4 Socket Head Cap Screw",
        "category": "fastener",
        "thread": "M4x0.7",
        "head_diameter_mm": 7.0,
        "head_height_mm": 4.0,
        "drive": "3.0mm Hex",
        "standard": "ISO 4762 / DIN 912",
        "step_available": False,
    },
    "m5_shcs": {
        "id": "fastener_m5_shcs",
        "name": "M5 Socket Head Cap Screw",
        "category": "fastener",
        "thread": "M5x0.8",
        "head_diameter_mm": 8.5,
        "head_height_mm": 5.0,
        "drive": "4.0mm Hex",
        "standard": "ISO 4762 / DIN 912",
        "step_available": False,
    },
    "m6_shcs": {
        "id": "fastener_m6_shcs",
        "name": "M6 Socket Head Cap Screw",
        "category": "fastener",
        "thread": "M6x1.0",
        "head_diameter_mm": 10.0,
        "head_height_mm": 6.0,
        "drive": "5.0mm Hex",
        "standard": "ISO 4762 / DIN 912",
        "step_available": False,
    },
    "m8_shcs": {
        "id": "fastener_m8_shcs",
        "name": "M8 Socket Head Cap Screw",
        "category": "fastener",
        "thread": "M8x1.25",
        "head_diameter_mm": 13.0,
        "head_height_mm": 8.0,
        "drive": "6.0mm Hex",
        "standard": "ISO 4762 / DIN 912",
        "step_available": False,
    },
    "m10_shcs": {
        "id": "fastener_m10_shcs",
        "name": "M10 Socket Head Cap Screw",
        "category": "fastener",
        "thread": "M10x1.5",
        "head_diameter_mm": 16.0,
        "head_height_mm": 10.0,
        "drive": "8.0mm Hex",
        "standard": "ISO 4762 / DIN 912",
        "step_available": False,
    },
    "608_bearing": {
        "id": "bearing_608_2rs",
        "name": "608-2RS Deep Groove Ball Bearing",
        "category": "bearing",
        "bore_mm": 8.0,
        "outer_diameter_mm": 22.0,
        "width_mm": 7.0,
        "standard": "ISO 15 / DIN 625",
        "step_available": False,
    },
    "6204_bearing": {
        "id": "bearing_6204",
        "name": "6204 Deep Groove Ball Bearing",
        "category": "bearing",
        "bore_mm": 20.0,
        "outer_diameter_mm": 47.0,
        "width_mm": 14.0,
        "standard": "ISO 15 / DIN 625",
        "step_available": False,
    },
    "6205_bearing": {
        "id": "bearing_6205",
        "name": "6205 Deep Groove Ball Bearing",
        "category": "bearing",
        "bore_mm": 25.0,
        "outer_diameter_mm": 52.0,
        "width_mm": 15.0,
        "standard": "ISO 15 / DIN 625",
        "step_available": False,
    },
}


async def search_hardware_parts(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Search step.parts for off-the-shelf parts matching query.
    Falls back gracefully to standard local engineering catalog if unavailable.
    """
    q_norm = query.strip().lower()
    
    # 1. Try step.parts API if configured or reachable
    if STEP_PARTS_API_KEY:
        try:
            headers = {"Authorization": f"Bearer {STEP_PARTS_API_KEY}"}
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(
                    f"{STEP_PARTS_BASE_URL}/search",
                    params={"q": q_norm, "limit": limit},
                    headers=headers
                )
                if res.status_code == 200:
                    data = res.json()
                    parts = data.get("results", [])
                    if parts:
                        return parts
        except Exception as e:
            logger.debug(f"step.parts API query failed: {e}")

    # 2. Local fallback matching
    results = []
    for key, item in OFFLINE_HARDWARE_CATALOG.items():
        if key in q_norm or item["name"].lower() in q_norm or any(w in item["name"].lower() for w in q_norm.split()):
            results.append(item)
            if len(results) >= limit:
                break

    return results


async def get_hardware_step(part_id: str, destination_dir: str) -> Optional[str]:
    """
    Download STEP file for standard part if available from step.parts.
    """
    if not STEP_PARTS_API_KEY or not part_id:
        return None

    try:
        headers = {"Authorization": f"Bearer {STEP_PARTS_API_KEY}"}
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get(f"{STEP_PARTS_BASE_URL}/parts/{part_id}/step", headers=headers)
            if res.status_code == 200:
                os.makedirs(destination_dir, exist_ok=True)
                dest_file = os.path.join(destination_dir, f"{part_id}.step")
                with open(dest_file, "wb") as f:
                    f.write(res.content)
                return dest_file
    except Exception as e:
        logger.warning(f"Failed to download STEP for part {part_id}: {e}")

    return None
