"""
Test suite for market data ingestion:
- Real-time EFFR query via Federal Reserve Bank of New York API.
- Offline Excel loader fallback.
- Futures settlement price-to-rate transformation (R = 100 - P).
"""

import sys
from pathlib import Path

# Add src folder to Python module lookup path
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(SRC_DIR))

from data_feed import (
    fetch_effr_from_nyfed,
    load_effr_from_excel,
    parse_futures_prices_to_rates,
)


def test_fetch_effr_from_nyfed() -> None:
    """
    Validates online ingestion of the latest EFFR from NY Fed public API.
    """
    print("\n[1/3] Testing NY Fed API endpoint...")
    effr = fetch_effr_from_nyfed()
    print(f"       Retrieved EFFR: {effr:.2f}%")

    assert isinstance(effr, float), f"Expected float, got {type(effr)}"
    assert 0.0 < effr < 15.0, f"EFFR rate out of realistic bounds: {effr}%"


def test_load_effr_from_excel() -> None:
    """
    Validates offline parsing of EFFR from exported NY Fed spreadsheet.
    Checks root directory and data/ directory for Search.xlsx.
    """
    print("\n[2/3] Testing offline Excel parser...")
    candidate_paths = [
        ROOT_DIR / "Search.xlsx",
        ROOT_DIR / "data" / "Search.xlsx",
    ]

    excel_path = next((p for p in candidate_paths if p.exists()), None)

    if excel_path is None:
        print("       Search.xlsx not found in root or data/ directory. Skipping Excel test.")
        return

    effr_excel = load_effr_from_excel(excel_path)
    print(f"       Extracted EFFR from {excel_path.name}: {effr_excel:.2f}%")

    assert isinstance(effr_excel, float), f"Expected float, got {type(effr_excel)}"
    assert abs(effr_excel - 3.88) < 1e-4, f"Expected 3.88%, got {effr_excel}%"


def test_parse_futures_prices_to_rates() -> None:
    """
    Validates the CME 30-Day Fed Funds futures pricing equation: R_avg = 100 - Price.
    """
    print("\n[3/3] Testing futures price-to-rate conversion...")
    mock_settlement_prices = {
        1: 96.12,   # Jan: R_avg = 3.88%
        2: 96.25,   # Feb: R_avg = 3.75%
        3: 96.50,   # Mar: R_avg = 3.50%
    }

    implied_rates = parse_futures_prices_to_rates(mock_settlement_prices)

    assert abs(implied_rates[1] - 3.88) < 1e-9, f"Expected 3.88, got {implied_rates[1]}"
    assert abs(implied_rates[2] - 3.75) < 1e-9, f"Expected 3.75, got {implied_rates[2]}"
    assert abs(implied_rates[3] - 3.50) < 1e-9, f"Expected 3.50, got {implied_rates[3]}"
    print("       Conversion matches R = 100 - P exactly.")


if __name__ == "__main__":
    print("=" * 80)
    print("RUNNING DATA FEED TEST SUITE")
    print("=" * 80)
    test_fetch_effr_from_nyfed()
    test_load_effr_from_excel()
    test_parse_futures_prices_to_rates()
    print("\nAll data feed tests completed successfully.")
    