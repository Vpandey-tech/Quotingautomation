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
    'mild_steel': {
        'name': 'Mild Steel (A36)',
        'density': 7.85,
        'base_inr_kg': 70.0,
        'machinability': 0.7,
        'grade': 'A36',
        'standard': 'IS 2062 E250',
        'tensile_strength': '400-550 MPa',
        'yield_strength': '250-350 MPa',
        'notes': 'Most common structural steel',
        'category': 'Ferrous Metals',
        'metals_dev_key': None,
        'wb_code': None,
        'mrr_cm3_hr': 252,
        'finish_factor': 1.0,
        'price_usd_kg': 0.8187,
    },
    'low_carbon_steel': {
        'name': 'Low Carbon Steel (1018)',
        'density': 7.87,
        'base_inr_kg': 75.0,
        'machinability': 0.65,
        'grade': '1018',
        'standard': 'IS 1570 Fe410',
        'tensile_strength': '380-450 MPa',
        'yield_strength': '205-305 MPa',
        'notes': 'Good weldability',
        'category': 'Ferrous Metals',
        'metals_dev_key': None,
        'wb_code': None,
        'mrr_cm3_hr': 234,
        'finish_factor': 1.0,
        'price_usd_kg': 0.8772,
    },
    'medium_carbon_steel': {
        'name': 'Medium Carbon Steel (1045)',
        'density': 7.85,
        'base_inr_kg': 80.0,
        'machinability': 0.6,
        'grade': '1045',
        'standard': 'IS 1570 Fe500',
        'tensile_strength': '550-700 MPa',
        'yield_strength': '350-550 MPa',
        'notes': 'Higher strength, lower ductility',
        'category': 'Ferrous Metals',
        'metals_dev_key': None,
        'wb_code': None,
        'mrr_cm3_hr': 216,
        'finish_factor': 1.0,
        'price_usd_kg': 0.9357,
    },
    'high_carbon_steel': {
        'name': 'High Carbon Steel (1095)',
        'density': 7.86,
        'base_inr_kg': 85.0,
        'machinability': 0.45,
        'grade': '1095',
        'standard': 'IS 1570 Fe600',
        'tensile_strength': '650-900 MPa',
        'yield_strength': '400-650 MPa',
        'notes': 'High strength, low ductility',
        'category': 'Ferrous Metals',
        'metals_dev_key': None,
        'wb_code': None,
        'mrr_cm3_hr': 162,
        'finish_factor': 1.0,
        'price_usd_kg': 0.9942,
    },
    'free_machining_steel': {
        'name': 'Free Machining Steel (1212)',
        'density': 7.85,
        'base_inr_kg': 70.0,
        'machinability': 0.9,
        'grade': '1212',
        'standard': 'IS 1570',
        'tensile_strength': '400-550 MPa',
        'yield_strength': '205-350 MPa',
        'notes': 'High sulfur for machinability',
        'category': 'Ferrous Metals',
        'metals_dev_key': None,
        'wb_code': None,
        'mrr_cm3_hr': 324,
        'finish_factor': 1.0,
        'price_usd_kg': 0.8187,
    },
    'alloy_steel': {
        'name': 'Alloy Steel (4140)',
        'density': 7.85,
        'base_inr_kg': 115.0,
        'machinability': 0.65,
        'grade': '4140',
        'standard': 'IS 4031',
        'tensile_strength': '650-900 MPa',
        'yield_strength': '415-700 MPa',
        'notes': 'Chromium-molybdenum',
        'category': 'Ferrous Metals',
        'metals_dev_key': None,
        'wb_code': None,
        'mrr_cm3_hr': 234,
        'finish_factor': 1.0,
        'price_usd_kg': 1.345,
    },
    'tool_steel_d2': {
        'name': 'Tool Steel (D2)',
        'density': 7.7,
        'base_inr_kg': 450.0,
        'machinability': 0.4,
        'grade': 'D2',
        'standard': 'IS 4454',
        'tensile_strength': '1500-2000 MPa',
        'yield_strength': '1000-1500 MPa',
        'notes': 'High carbon, high chromium',
        'category': 'Ferrous Metals',
        'metals_dev_key': None,
        'wb_code': None,
        'mrr_cm3_hr': 144,
        'finish_factor': 1.0,
        'price_usd_kg': 5.2632,
    },
    'stainless_steel_304': {
        'name': 'Stainless Steel 304',
        'density': 8.0,
        'base_inr_kg': 275.0,
        'machinability': 0.5,
        'grade': '304',
        'standard': 'IS 5517',
        'tensile_strength': '500-700 MPa',
        'yield_strength': '205-300 MPa',
        'notes': 'Most common stainless',
        'category': 'Ferrous Metals',
        'metals_dev_key': None,
        'wb_code': None,
        'mrr_cm3_hr': 180,
        'finish_factor': 1.0,
        'price_usd_kg': 3.2164,
    },
    'stainless_steel_304l': {
        'name': 'Stainless Steel 304L',
        'density': 8.0,
        'base_inr_kg': 295.0,
        'machinability': 0.5,
        'grade': '304L',
        'standard': 'IS 5517',
        'tensile_strength': '480-670 MPa',
        'yield_strength': '170-280 MPa',
        'notes': 'Low carbon version of 304',
        'category': 'Ferrous Metals',
        'metals_dev_key': None,
        'wb_code': None,
        'mrr_cm3_hr': 180,
        'finish_factor': 1.0,
        'price_usd_kg': 3.4503,
    },
    'stainless_steel_316': {
        'name': 'Stainless Steel 316',
        'density': 8.0,
        'base_inr_kg': 375.0,
        'machinability': 0.45,
        'grade': '316',
        'standard': 'IS 5517',
        'tensile_strength': '500-700 MPa',
        'yield_strength': '205-300 MPa',
        'notes': 'Marine grade, corrosion resistant',
        'category': 'Ferrous Metals',
        'metals_dev_key': None,
        'wb_code': None,
        'mrr_cm3_hr': 162,
        'finish_factor': 1.0,
        'price_usd_kg': 4.386,
    },
    'stainless_steel_316l': {
        'name': 'Stainless Steel 316L',
        'density': 8.0,
        'base_inr_kg': 395.0,
        'machinability': 0.45,
        'grade': '316L',
        'standard': 'IS 5517',
        'tensile_strength': '480-670 MPa',
        'yield_strength': '170-280 MPa',
        'notes': 'Low carbon version of 316',
        'category': 'Ferrous Metals',
        'metals_dev_key': None,
        'wb_code': None,
        'mrr_cm3_hr': 162,
        'finish_factor': 1.0,
        'price_usd_kg': 4.6199,
    },
    'stainless_steel_410': {
        'name': 'Stainless Steel 410',
        'density': 7.75,
        'base_inr_kg': 225.0,
        'machinability': 0.6,
        'grade': '410',
        'standard': 'IS 5517',
        'tensile_strength': '450-650 MPa',
        'yield_strength': '205-350 MPa',
        'notes': 'Martensitic, heat treatable',
        'category': 'Ferrous Metals',
        'metals_dev_key': None,
        'wb_code': None,
        'mrr_cm3_hr': 216,
        'finish_factor': 1.0,
        'price_usd_kg': 2.6316,
    },
    'cast_iron_gray': {
        'name': 'Cast Iron (Gray) (Class 20)',
        'density': 7.2,
        'base_inr_kg': 100.0,
        'machinability': 0.8,
        'grade': 'Class 20',
        'standard': 'IS 210',
        'tensile_strength': '140-200 MPa',
        'yield_strength': '-',
        'notes': 'Good vibration damping',
        'category': 'Ferrous Metals',
        'metals_dev_key': None,
        'wb_code': None,
        'mrr_cm3_hr': 288,
        'finish_factor': 1.0,
        'price_usd_kg': 1.1696,
    },
    'cast_iron_ductile': {
        'name': 'Cast Iron (Ductile) (60-40-18)',
        'density': 7.1,
        'base_inr_kg': 150.0,
        'machinability': 0.7,
        'grade': '60-40-18',
        'standard': 'IS 1865',
        'tensile_strength': '415-600 MPa',
        'yield_strength': '275-450 MPa',
        'notes': 'Spheroidal graphite',
        'category': 'Ferrous Metals',
        'metals_dev_key': None,
        'wb_code': None,
        'mrr_cm3_hr': 252,
        'finish_factor': 1.0,
        'price_usd_kg': 1.7544,
    },
    'aluminum_6061': {
        'name': 'Aluminum 6061',
        'density': 2.7,
        'base_inr_kg': 225.0,
        'machinability': 0.9,
        'grade': '6061',
        'standard': 'IS 737',
        'tensile_strength': '180-310 MPa',
        'yield_strength': '110-270 MPa',
        'notes': 'Most versatile aluminum alloy',
        'category': 'Non-Ferrous Metals',
        'metals_dev_key': 'lme_aluminum',
        'wb_code': 'PALUM',
        'mrr_cm3_hr': 324,
        'finish_factor': 1.0,
        'price_usd_kg': 2.6316,
    },
    'aluminum_6063': {
        'name': 'Aluminum 6063',
        'density': 2.7,
        'base_inr_kg': 200.0,
        'machinability': 0.95,
        'grade': '6063',
        'standard': 'IS 737',
        'tensile_strength': '150-250 MPa',
        'yield_strength': '90-210 MPa',
        'notes': 'Good extrudability',
        'category': 'Non-Ferrous Metals',
        'metals_dev_key': 'lme_aluminum',
        'wb_code': 'PALUM',
        'mrr_cm3_hr': 342,
        'finish_factor': 1.0,
        'price_usd_kg': 2.3392,
    },
    'aluminum_7075': {
        'name': 'Aluminum 7075',
        'density': 2.8,
        'base_inr_kg': 315.0,
        'machinability': 0.7,
        'grade': '7075',
        'standard': 'IS 737',
        'tensile_strength': '500-600 MPa',
        'yield_strength': '400-550 MPa',
        'notes': 'High strength, aircraft grade',
        'category': 'Non-Ferrous Metals',
        'metals_dev_key': 'lme_aluminum',
        'wb_code': 'PALUM',
        'mrr_cm3_hr': 252,
        'finish_factor': 1.0,
        'price_usd_kg': 3.6842,
    },
    'copper': {
        'name': 'Copper (ETP)',
        'density': 8.96,
        'base_inr_kg': 750.0,
        'machinability': 0.2,
        'grade': 'ETP',
        'standard': 'IS 191',
        'tensile_strength': '200-250 MPa',
        'yield_strength': '30-70 MPa',
        'notes': 'Highest conductivity',
        'category': 'Non-Ferrous Metals',
        'metals_dev_key': 'lme_copper',
        'wb_code': 'PCOPP',
        'mrr_cm3_hr': 72,
        'finish_factor': 1.0,
        'price_usd_kg': 8.7719,
    },
    'brass_60_40': {
        'name': 'Brass (60/40)',
        'density': 8.4,
        'base_inr_kg': 500.0,
        'machinability': 0.8,
        'grade': '-',
        'standard': 'IS 200',
        'tensile_strength': '350-450 MPa',
        'yield_strength': '100-200 MPa',
        'notes': 'Cu 60%, Zn 40%',
        'category': 'Non-Ferrous Metals',
        'metals_dev_key': None,
        'wb_code': None,
        'mrr_cm3_hr': 288,
        'finish_factor': 1.0,
        'price_usd_kg': 5.848,
    },
    'brass_70_30': {
        'name': 'Brass (70/30)',
        'density': 8.53,
        'base_inr_kg': 550.0,
        'machinability': 0.7,
        'grade': '-',
        'standard': 'IS 200',
        'tensile_strength': '300-400 MPa',
        'yield_strength': '80-180 MPa',
        'notes': 'Cu 70%, Zn 30%',
        'category': 'Non-Ferrous Metals',
        'metals_dev_key': None,
        'wb_code': None,
        'mrr_cm3_hr': 252,
        'finish_factor': 1.0,
        'price_usd_kg': 6.4327,
    },
    'phosphor_bronze': {
        'name': 'Phosphor Bronze (C51000)',
        'density': 8.7,
        'base_inr_kg': 675.0,
        'machinability': 0.4,
        'grade': 'C51000',
        'standard': '-',
        'tensile_strength': '350-500 MPa',
        'yield_strength': '150-300 MPa',
        'notes': 'Cu-Sn-P alloy',
        'category': 'Non-Ferrous Metals',
        'metals_dev_key': None,
        'wb_code': None,
        'mrr_cm3_hr': 144,
        'finish_factor': 1.0,
        'price_usd_kg': 7.8947,
    },
    'titanium_grade_2': {
        'name': 'Titanium Grade 2',
        'density': 4.51,
        'base_inr_kg': 2750.0,
        'machinability': 0.4,
        'grade': 'Grade 2',
        'standard': '-',
        'tensile_strength': '340-450 MPa',
        'yield_strength': '275-380 MPa',
        'notes': 'High strength-to-weight',
        'category': 'Non-Ferrous Metals',
        'metals_dev_key': None,
        'wb_code': None,
        'mrr_cm3_hr': 144,
        'finish_factor': 1.0,
        'price_usd_kg': 32.1637,
    },
    'titanium_grade_5': {
        'name': 'Titanium Grade 5 (6Al-4V)',
        'density': 4.43,
        'base_inr_kg': 3250.0,
        'machinability': 0.35,
        'grade': 'Grade 5 (6Al-4V)',
        'standard': '-',
        'tensile_strength': '900-1000 MPa',
        'yield_strength': '800-950 MPa',
        'notes': 'Most common Ti alloy',
        'category': 'Non-Ferrous Metals',
        'metals_dev_key': None,
        'wb_code': None,
        'mrr_cm3_hr': 126,
        'finish_factor': 1.0,
        'price_usd_kg': 38.0117,
    },
    'magnesium_az91d': {
        'name': 'Magnesium (AZ91D)',
        'density': 1.81,
        'base_inr_kg': 350.0,
        'machinability': 0.9,
        'grade': 'AZ91D',
        'standard': '-',
        'tensile_strength': '160-230 MPa',
        'yield_strength': '90-150 MPa',
        'notes': 'Lightest structural metal',
        'category': 'Non-Ferrous Metals',
        'metals_dev_key': None,
        'wb_code': None,
        'mrr_cm3_hr': 324,
        'finish_factor': 1.0,
        'price_usd_kg': 4.0936,
    },
    'nickel_200': {
        'name': 'Nickel 200',
        'density': 8.9,
        'base_inr_kg': 1350.0,
        'machinability': 0.3,
        'grade': '200',
        'standard': '-',
        'tensile_strength': '300-400 MPa',
        'yield_strength': '50-150 MPa',
        'notes': 'Corrosion resistant',
        'category': 'Non-Ferrous Metals',
        'metals_dev_key': 'lme_nickel',
        'wb_code': 'PNICK',
        'mrr_cm3_hr': 108,
        'finish_factor': 1.0,
        'price_usd_kg': 15.7895,
    },
    'monel_400': {
        'name': 'Monel 400',
        'density': 8.8,
        'base_inr_kg': 1750.0,
        'machinability': 0.3,
        'grade': '-',
        'standard': '-',
        'tensile_strength': '450-600 MPa',
        'yield_strength': '170-300 MPa',
        'notes': 'Cu-Ni alloy',
        'category': 'Non-Ferrous Metals',
        'metals_dev_key': None,
        'wb_code': None,
        'mrr_cm3_hr': 108,
        'finish_factor': 1.0,
        'price_usd_kg': 20.4678,
    },
    'inconel_625': {
        'name': 'Inconel 625',
        'density': 8.44,
        'base_inr_kg': 3000.0,
        'machinability': 0.25,
        'grade': '-',
        'standard': '-',
        'tensile_strength': '760-1000 MPa',
        'yield_strength': '350-700 MPa',
        'notes': 'Ni-Cr-Mo alloy',
        'category': 'Non-Ferrous Metals',
        'metals_dev_key': 'lme_nickel',
        'wb_code': 'PNICK',
        'mrr_cm3_hr': 90,
        'finish_factor': 1.0,
        'price_usd_kg': 35.0877,
    },
    'abs_plastic': {
        'name': 'ABS',
        'density': 1.04,
        'base_inr_kg': 175.0,
        'machinability': 0.6,
        'grade': '-',
        'standard': '-',
        'tensile_strength': '35-55 MPa',
        'yield_strength': '20-45 MPa',
        'notes': 'Acrylonitrile butadiene styrene',
        'category': 'Plastics',
        'metals_dev_key': None,
        'wb_code': None,
        'mrr_cm3_hr': 216,
        'finish_factor': 0.7,
        'price_usd_kg': 2.0468,
    },
    'abs_flame_retardant': {
        'name': 'ABS (Flame Retardant)',
        'density': 1.06,
        'base_inr_kg': 225.0,
        'machinability': 0.55,
        'grade': '-',
        'standard': '-',
        'tensile_strength': '30-50 MPa',
        'yield_strength': '15-40 MPa',
        'notes': 'Fire resistant',
        'category': 'Plastics',
        'metals_dev_key': None,
        'wb_code': None,
        'mrr_cm3_hr': 198,
        'finish_factor': 0.7,
        'price_usd_kg': 2.6316,
    },
    'polypropylene': {
        'name': 'Polypropylene (PP)',
        'density': 0.9,
        'base_inr_kg': 115.0,
        'machinability': 0.8,
        'grade': '-',
        'standard': '-',
        'tensile_strength': '30-40 MPa',
        'yield_strength': '25-35 MPa',
        'notes': 'Semi-crystalline',
        'category': 'Plastics',
        'metals_dev_key': None,
        'wb_code': None,
        'mrr_cm3_hr': 288,
        'finish_factor': 0.7,
        'price_usd_kg': 1.345,
    },
    'polyethylene_hdpe': {
        'name': 'Polyethylene (HDPE)',
        'density': 0.95,
        'base_inr_kg': 105.0,
        'machinability': 0.85,
        'grade': '-',
        'standard': '-',
        'tensile_strength': '20-30 MPa',
        'yield_strength': '15-25 MPa',
        'notes': 'High density',
        'category': 'Plastics',
        'metals_dev_key': None,
        'wb_code': None,
        'mrr_cm3_hr': 306,
        'finish_factor': 0.7,
        'price_usd_kg': 1.2281,
    },
    'polycarbonate': {
        'name': 'Polycarbonate (PC)',
        'density': 1.2,
        'base_inr_kg': 325.0,
        'machinability': 0.3,
        'grade': '-',
        'standard': '-',
        'tensile_strength': '55-75 MPa',
        'yield_strength': '50-65 MPa',
        'notes': 'High impact strength',
        'category': 'Plastics',
        'metals_dev_key': None,
        'wb_code': None,
        'mrr_cm3_hr': 108,
        'finish_factor': 0.7,
        'price_usd_kg': 3.8012,
    },
    'nylon_pa6': {
        'name': 'Nylon (PA6)',
        'density': 1.13,
        'base_inr_kg': 275.0,
        'machinability': 0.4,
        'grade': '-',
        'standard': '-',
        'tensile_strength': '60-85 MPa',
        'yield_strength': '40-60 MPa',
        'notes': 'Polyamide 6',
        'category': 'Plastics',
        'metals_dev_key': None,
        'wb_code': None,
        'mrr_cm3_hr': 144,
        'finish_factor': 0.7,
        'price_usd_kg': 3.2164,
    },
    'nylon_pa66': {
        'name': 'Nylon (PA66)',
        'density': 1.14,
        'base_inr_kg': 315.0,
        'machinability': 0.35,
        'grade': '-',
        'standard': '-',
        'tensile_strength': '70-95 MPa',
        'yield_strength': '50-75 MPa',
        'notes': 'Polyamide 66',
        'category': 'Plastics',
        'metals_dev_key': None,
        'wb_code': None,
        'mrr_cm3_hr': 126,
        'finish_factor': 0.7,
        'price_usd_kg': 3.6842,
    },
    'acrylic_pmma': {
        'name': 'Acrylic (PMMA)',
        'density': 1.18,
        'base_inr_kg': 225.0,
        'machinability': 0.5,
        'grade': '-',
        'standard': '-',
        'tensile_strength': '50-75 MPa',
        'yield_strength': '40-65 MPa',
        'notes': 'Polymethyl methacrylate',
        'category': 'Plastics',
        'metals_dev_key': None,
        'wb_code': None,
        'mrr_cm3_hr': 180,
        'finish_factor': 0.7,
        'price_usd_kg': 2.6316,
    },
    'pom_delrin': {
        'name': 'POM (Delrin)',
        'density': 1.41,
        'base_inr_kg': 400.0,
        'machinability': 0.3,
        'grade': '-',
        'standard': '-',
        'tensile_strength': '60-75 MPa',
        'yield_strength': '50-65 MPa',
        'notes': 'Polyoxymethylene',
        'category': 'Plastics',
        'metals_dev_key': None,
        'wb_code': None,
        'mrr_cm3_hr': 108,
        'finish_factor': 0.7,
        'price_usd_kg': 4.6784,
    },
    'pet_plastic': {
        'name': 'PET',
        'density': 1.37,
        'base_inr_kg': 150.0,
        'machinability': 0.6,
        'grade': '-',
        'standard': '-',
        'tensile_strength': '50-70 MPa',
        'yield_strength': '40-60 MPa',
        'notes': 'Polyethylene terephthalate',
        'category': 'Plastics',
        'metals_dev_key': None,
        'wb_code': None,
        'mrr_cm3_hr': 216,
        'finish_factor': 0.7,
        'price_usd_kg': 1.7544,
    },
    'peek_plastic': {
        'name': 'PEEK',
        'density': 1.32,
        'base_inr_kg': 2250.0,
        'machinability': 0.2,
        'grade': '-',
        'standard': '-',
        'tensile_strength': '90-110 MPa',
        'yield_strength': '70-90 MPa',
        'notes': 'Polyether ether ketone',
        'category': 'Plastics',
        'metals_dev_key': None,
        'wb_code': None,
        'mrr_cm3_hr': 72,
        'finish_factor': 0.7,
        'price_usd_kg': 26.3158,
    },
    'ptfe_teflon': {
        'name': 'PTFE (Teflon)',
        'density': 2.2,
        'base_inr_kg': 600.0,
        'machinability': 0.1,
        'grade': '-',
        'standard': '-',
        'tensile_strength': '20-40 MPa',
        'yield_strength': '5-15 MPa',
        'notes': 'Polytetrafluoroethylene',
        'category': 'Plastics',
        'metals_dev_key': None,
        'wb_code': None,
        'mrr_cm3_hr': 36,
        'finish_factor': 0.7,
        'price_usd_kg': 7.0175,
    },
    'pvc_plastic': {
        'name': 'PVC',
        'density': 1.35,
        'base_inr_kg': 100.0,
        'machinability': 0.6,
        'grade': '-',
        'standard': '-',
        'tensile_strength': '40-60 MPa',
        'yield_strength': '30-50 MPa',
        'notes': 'Polyvinyl chloride',
        'category': 'Plastics',
        'metals_dev_key': None,
        'wb_code': None,
        'mrr_cm3_hr': 216,
        'finish_factor': 0.7,
        'price_usd_kg': 1.1696,
    },
    'epoxy_resin': {
        'name': 'Epoxy',
        'density': 1.25,
        'base_inr_kg': 300.0,
        'machinability': 0.1,
        'grade': '-',
        'standard': '-',
        'tensile_strength': '30-90 MPa',
        'yield_strength': '-',
        'notes': 'Epoxy resin',
        'category': 'Plastics',
        'metals_dev_key': None,
        'wb_code': None,
        'mrr_cm3_hr': 36,
        'finish_factor': 0.7,
        'price_usd_kg': 3.5088,
    },
    'phenolic': {
        'name': 'Phenolic',
        'density': 1.35,
        'base_inr_kg': 200.0,
        'machinability': 0.05,
        'grade': '-',
        'standard': '-',
        'tensile_strength': '35-65 MPa',
        'yield_strength': '-',
        'notes': 'Phenol formaldehyde',
        'category': 'Plastics',
        'metals_dev_key': None,
        'wb_code': None,
        'mrr_cm3_hr': 18,
        'finish_factor': 0.7,
        'price_usd_kg': 2.3392,
    },
    'gfrp': {
        'name': 'GFRP (Epoxy/E-Glass)',
        'density': 1.9500000000000002,
        'base_inr_kg': 450.0,
        'machinability': 0.5,
        'grade': 'Epoxy/E-Glass',
        'standard': '-',
        'tensile_strength': '300-1000 MPa',
        'yield_strength': '-',
        'notes': 'Glass fiber reinforced',
        'category': 'Composites',
        'metals_dev_key': None,
        'wb_code': None,
        'mrr_cm3_hr': 180,
        'finish_factor': 1.0,
        'price_usd_kg': 5.2632,
    },
    'cfrp': {
        'name': 'CFRP (Epoxy/Carbon)',
        'density': 1.55,
        'base_inr_kg': 1500.0,
        'machinability': 0.5,
        'grade': 'Epoxy/Carbon',
        'standard': '-',
        'tensile_strength': '600-1500 MPa',
        'yield_strength': '-',
        'notes': 'Carbon fiber reinforced',
        'category': 'Composites',
        'metals_dev_key': None,
        'wb_code': None,
        'mrr_cm3_hr': 180,
        'finish_factor': 1.0,
        'price_usd_kg': 17.5439,
    },
    'kevlar_epoxy': {
        'name': 'Kevlar/Epoxy (Epoxy/Kevlar)',
        'density': 1.38,
        'base_inr_kg': 2000.0,
        'machinability': 0.5,
        'grade': 'Epoxy/Kevlar',
        'standard': '-',
        'tensile_strength': '1200-1500 MPa',
        'yield_strength': '-',
        'notes': 'Aramid fiber',
        'category': 'Composites',
        'metals_dev_key': None,
        'wb_code': None,
        'mrr_cm3_hr': 180,
        'finish_factor': 1.0,
        'price_usd_kg': 23.3918,
    },
    'aluminum_sic': {
        'name': 'Aluminum/SiC (Aluminum/SiC particles)',
        'density': 2.8,
        'base_inr_kg': 1150.0,
        'machinability': 0.5,
        'grade': 'Aluminum/SiC particles',
        'standard': '-',
        'tensile_strength': '300-600 MPa',
        'yield_strength': '-',
        'notes': 'Particle reinforced',
        'category': 'Composites',
        'metals_dev_key': 'lme_aluminum',
        'wb_code': 'PALUM',
        'mrr_cm3_hr': 180,
        'finish_factor': 1.0,
        'price_usd_kg': 13.4503,
    },
    'alumina_al2o3': {
        'name': 'Alumina (Al2O3) (99.50%)',
        'density': 3.8499999999999996,
        'base_inr_kg': 650.0,
        'machinability': 0.5,
        'grade': '99.50%',
        'standard': '-',
        'tensile_strength': '200-300 MPa',
        'yield_strength': '-',
        'notes': 'High hardness, brittle',
        'category': 'Ceramics',
        'metals_dev_key': None,
        'wb_code': None,
        'mrr_cm3_hr': 180,
        'finish_factor': 4.5,
        'price_usd_kg': 7.6023,
    },
    'zirconia_zro2': {
        'name': 'Zirconia (ZrO2)',
        'density': 5.8,
        'base_inr_kg': 1250.0,
        'machinability': 0.5,
        'grade': '-',
        'standard': '-',
        'tensile_strength': '200-400 MPa',
        'yield_strength': '-',
        'notes': 'Toughened zirconia',
        'category': 'Ceramics',
        'metals_dev_key': None,
        'wb_code': None,
        'mrr_cm3_hr': 180,
        'finish_factor': 4.5,
        'price_usd_kg': 14.6199,
    },
    'silicon_nitride': {
        'name': 'Silicon Nitride (Si3N4)',
        'density': 3.2,
        'base_inr_kg': 2000.0,
        'machinability': 0.5,
        'grade': 'Si3N4',
        'standard': '-',
        'tensile_strength': '200-500 MPa',
        'yield_strength': '-',
        'notes': 'High temperature',
        'category': 'Ceramics',
        'metals_dev_key': None,
        'wb_code': None,
        'mrr_cm3_hr': 180,
        'finish_factor': 4.5,
        'price_usd_kg': 23.3918,
    },
    'silicon_carbide': {
        'name': 'Silicon Carbide (SiC)',
        'density': 3.1,
        'base_inr_kg': 1500.0,
        'machinability': 0.5,
        'grade': 'SiC',
        'standard': '-',
        'tensile_strength': '200-400 MPa',
        'yield_strength': '-',
        'notes': 'High hardness',
        'category': 'Ceramics',
        'metals_dev_key': None,
        'wb_code': None,
        'mrr_cm3_hr': 180,
        'finish_factor': 4.5,
        'price_usd_kg': 17.5439,
    },
    'tungsten_carbide': {
        'name': 'Tungsten Carbide (WC)',
        'density': 15.35,
        'base_inr_kg': 3000.0,
        'machinability': 0.5,
        'grade': 'WC',
        'standard': '-',
        'tensile_strength': '500-1500 MPa',
        'yield_strength': '-',
        'notes': 'Cemented carbide',
        'category': 'Ceramics',
        'metals_dev_key': None,
        'wb_code': None,
        'mrr_cm3_hr': 180,
        'finish_factor': 4.5,
        'price_usd_kg': 35.0877,
    },
    'inconel_600': {
        'name': 'Inconel 600',
        'density': 8.42,
        'base_inr_kg': 2500.0,
        'machinability': 0.3,
        'grade': '600',
        'standard': '-',
        'tensile_strength': '600-800 MPa',
        'yield_strength': '-',
        'notes': 'Ni-Cr alloy',
        'category': 'Exotic Alloys',
        'metals_dev_key': 'lme_nickel',
        'wb_code': 'PNICK',
        'mrr_cm3_hr': 108,
        'finish_factor': 3.5,
        'price_usd_kg': 29.2398,
    },
    'inconel_718': {
        'name': 'Inconel 718',
        'density': 8.19,
        'base_inr_kg': 3000.0,
        'machinability': 0.25,
        'grade': '718',
        'standard': '-',
        'tensile_strength': '1000-1300 MPa',
        'yield_strength': '-',
        'notes': 'Ni-Cr-Fe alloy',
        'category': 'Exotic Alloys',
        'metals_dev_key': 'lme_nickel',
        'wb_code': 'PNICK',
        'mrr_cm3_hr': 90,
        'finish_factor': 3.5,
        'price_usd_kg': 35.0877,
    },
    'waspaloy': {
        'name': 'Waspaloy',
        'density': 8.36,
        'base_inr_kg': 3500.0,
        'machinability': 0.2,
        'grade': '-',
        'standard': '-',
        'tensile_strength': '900-1200 MPa',
        'yield_strength': '-',
        'notes': 'Ni-Co-Cr alloy',
        'category': 'Exotic Alloys',
        'metals_dev_key': None,
        'wb_code': None,
        'mrr_cm3_hr': 72,
        'finish_factor': 3.5,
        'price_usd_kg': 40.9357,
    },
    'hastelloy_x': {
        'name': 'Hastelloy X',
        'density': 8.22,
        'base_inr_kg': 3500.0,
        'machinability': 0.2,
        'grade': 'X',
        'standard': '-',
        'tensile_strength': '700-900 MPa',
        'yield_strength': '-',
        'notes': 'Ni-Cr-Fe-Mo alloy',
        'category': 'Exotic Alloys',
        'metals_dev_key': 'lme_nickel',
        'wb_code': 'PNICK',
        'mrr_cm3_hr': 72,
        'finish_factor': 3.5,
        'price_usd_kg': 40.9357,
    },
    'molybdenum': {
        'name': 'Molybdenum',
        'density': 10.22,
        'base_inr_kg': 4500.0,
        'machinability': 0.35,
        'grade': '-',
        'standard': '-',
        'tensile_strength': '500-700 MPa',
        'yield_strength': '-',
        'notes': 'High melting point',
        'category': 'Exotic Alloys',
        'metals_dev_key': None,
        'wb_code': None,
        'mrr_cm3_hr': 126,
        'finish_factor': 3.5,
        'price_usd_kg': 52.6316,
    },
    'tungsten': {
        'name': 'Tungsten',
        'density': 19.25,
        'base_inr_kg': 6000.0,
        'machinability': 0.25,
        'grade': '-',
        'standard': '-',
        'tensile_strength': '600-1000 MPa',
        'yield_strength': '-',
        'notes': 'Highest melting point',
        'category': 'Exotic Alloys',
        'metals_dev_key': None,
        'wb_code': None,
        'mrr_cm3_hr': 90,
        'finish_factor': 3.5,
        'price_usd_kg': 70.1754,
    },
    'tantalum': {
        'name': 'Tantalum',
        'density': 16.6,
        'base_inr_kg': 7000.0,
        'machinability': 0.2,
        'grade': '-',
        'standard': '-',
        'tensile_strength': '300-500 MPa',
        'yield_strength': '-',
        'notes': 'Corrosion resistant',
        'category': 'Exotic Alloys',
        'metals_dev_key': None,
        'wb_code': None,
        'mrr_cm3_hr': 72,
        'finish_factor': 3.5,
        'price_usd_kg': 81.8713,
    },
}

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

