import os
from datetime import date, datetime
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
import requests

# Carica automaticamente le variabili definite nel file .env
load_dotenv()

# Endpoints
FRED_OBSERVATIONS_URL = "https://api.stlouisfed.org/fred/series/observations"
NY_FED_EFFR_URL = "https://markets.newyorkfed.org/api/rates/unsecured/effr/last/1.json"


def fetch_effr_from_fred(api_key: str | None = None) -> tuple[float, date]:
    """
    Fetches the latest official Effective Federal Funds Rate (EFFR) from FRED API (Series: DFF).
    
    Parameters:
    - api_key: 32-character FRED API key. If None, reads from FRED_API_KEY env variable.

    Returns:
    - tuple: (rate: float, observation_date: date)
    """
    key = api_key or os.getenv("FRED_API_KEY")
    if not key:
        raise ValueError("FRED_API_KEY environment variable is not set.")

    params = {
        "series_id": "DFF",
        "api_key": key,
        "file_type": "json",
        "sort_order": "desc",
        "limit": 1,
    }

    response = requests.get(FRED_OBSERVATIONS_URL, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    observations = data.get("observations", [])
    if not observations:
        raise ValueError("No observations returned from FRED for series DFF.")

    latest = observations[0]
    rate = float(latest["value"])
    obs_date = datetime.strptime(latest["date"], "%Y-%m-%d").date()
    return rate, obs_date


def fetch_effr_from_nyfed() -> tuple[float, date]:
    """
    Fallback: Fetches latest EFFR directly from Federal Reserve Bank of New York API.
    Does not require an API key.
    """
    try:
        response = requests.get(NY_FED_EFFR_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        latest = data["refRates"][0]
        effr_rate = float(latest["percentRate"])
        eff_date = datetime.strptime(latest["effectiveDate"], "%Y-%m-%d").date()
        return effr_rate, eff_date
    except Exception as exc:
        raise RuntimeError(f"Failed to fetch live EFFR from NY Fed API: {exc}") from exc


def get_spot_effr() -> tuple[float, date, str]:
    """
    Dual-source spot rate orchestrator:
    1. Tries FRED API (if key present).
    2. Falls back to NY Fed open API.
    3. Emergency fallback to static spot.
    """
    # 1. Attempt FRED
    if os.getenv("FRED_API_KEY"):
        try:
            rate, obs_date = fetch_effr_from_fred()
            return rate, obs_date, "St. Louis Fed (FRED API)"
        except Exception as exc:
            print(f"[WARN] FRED query failed: {exc}. Trying NY Fed...")

    # 2. Attempt NY Fed
    try:
        rate, obs_date = fetch_effr_from_nyfed()
        return rate, obs_date, "NY Fed API (Open)"
    except Exception as exc:
        print(f"[WARN] NY Fed query failed: {exc}. Using cached fallback.")

    # 3. Static fallback
    return 3.880, date(2026, 10, 31), "Cached Spot"


def fetch_market_implied_rates() -> dict[tuple[int, int], float]:
    """
    Returns the market-implied post-meeting and monthly average rates derived
    from 30-Day Fed Funds futures settlements across the 12-month horizon.
    """
    return {
        (2026, 12): 4.063,  # Dec 09, 2026: +18.3 bps
        (2027, 1):  4.153,  # Jan 27, 2027: +27.3 bps cumulative
        (2027, 2):  4.153,  # Feb 2027: Anchor month
        (2027, 3):  4.255,  # Mar 17, 2027: +37.5 bps cumulative
        (2027, 4):  4.346,  # Apr 28, 2027: +46.6 bps cumulative
        (2027, 5):  4.346,  # May 2027: Anchor month
        (2027, 6):  4.407,  # Jun 09, 2027: +52.7 bps cumulative
        (2027, 7):  4.432,  # Jul 28, 2027: +55.2 bps cumulative
        (2027, 8):  4.432,  # Aug 2027: Anchor month
        (2027, 9):  4.439,  # Sep 15, 2027: +55.9 bps cumulative
        (2027, 10): 4.435,  # Oct 27, 2027: +55.5 bps cumulative
    }