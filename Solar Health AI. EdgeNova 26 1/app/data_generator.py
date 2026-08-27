'''
Purpose: Create realistic solar panel data for the demo

What it does:

Generates 500-1000 panels with realistic attributes

Simulates degradation based on years of operation

Includes manufacturer, wattage, temperature, dust levels

AI Prompt: "Write a Python script that generates synthetic solar panel data with columns: panel_id, manufacturer, original_wattage, current_wattage, years_operating, degradation_rate, temperature, dust_level, efficiency. Use realistic values based on research."
'''
"""
Generates a synthetic fleet of solar panels, clustered around real Indian
solar park sites so the Fleet Map reads as an actual deployment rather than
random points scattered across the country.
"""
"""
data_generator.py - Sample data generator for SolarPanel Health AI
Team Optisuns

Models ONE solar farm (Bhadla Solar Park, Rajasthan — the world's largest,
2,245 MW) rather than scattering panels across multiple cities. Panels are
laid out in a two-level grid:
  1. The farm is divided into a BLOCK_ROWS x BLOCK_COLS grid of maintenance
     blocks (e.g. "Block A1" .. "Block F8"), the way a site this large is
     actually subdivided for inspection/O&M crews.
  2. Within each block, panels are placed on their own tidy sub-grid of
     rows/columns (not randomly scattered) so the map reads as an installed
     panel array rather than random dots.
"""

import math
import os
import random
import string
from collections import defaultdict
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

np.random.seed(42)
random.seed(42)

MANUFACTURERS = ["SunPower", "LG", "Panasonic", "Jinko", "Trina", "Canadian Solar"]

FARM_NAME = "Bhadla Solar Park, Rajasthan"
FARM_CENTER_LAT = 27.5397
FARM_CENTER_LON = 71.9153

# Half-extents (degrees) chosen so the bounding box approximates Bhadla's
# real ~14,000 acre (~57 km^2) footprint:
#   lat: 0.033 deg * 2 * 111 km/deg            ~ 7.3 km
#   lon: 0.039 deg * 2 * 111*cos(27.5deg) km/deg ~ 7.7 km  -> ~56 km^2 total
LAT_HALF_EXTENT_DEG = 0.033
LON_HALF_EXTENT_DEG = 0.039

# Maintenance block grid covering the farm.
BLOCK_ROWS = 6
BLOCK_COLS = 8
TOTAL_BLOCKS = BLOCK_ROWS * BLOCK_COLS


def _block_bounds(block_row: int, block_col: int):
    lat_min = FARM_CENTER_LAT - LAT_HALF_EXTENT_DEG
    lon_min = FARM_CENTER_LON - LON_HALF_EXTENT_DEG
    block_h = (2 * LAT_HALF_EXTENT_DEG) / BLOCK_ROWS
    block_w = (2 * LON_HALF_EXTENT_DEG) / BLOCK_COLS
    return (
        lat_min + block_row * block_h, lat_min + (block_row + 1) * block_h,
        lon_min + block_col * block_w, lon_min + (block_col + 1) * block_w,
    )


def generate_panel_data(num_panels: int = 1000) -> pd.DataFrame:
    row_labels = string.ascii_uppercase[:BLOCK_ROWS]

    # Assign panels to blocks round-robin so every block gets a near-equal
    # share (an even spread, the way a real installer would fill a site).
    block_of_panel = [i % TOTAL_BLOCKS for i in range(num_panels)]

    # How many panels land in each block, and the row/col grid that fits
    # them as a near-square array (e.g. 21 panels -> 5 rows x 5 cols).
    panels_per_block = defaultdict(int)
    for b in block_of_panel:
        panels_per_block[b] += 1

    grid_dims = {}
    for b, count in panels_per_block.items():
        rows = max(1, round(math.sqrt(count)))
        cols = max(1, math.ceil(count / rows))
        grid_dims[b] = (rows, cols)

    position_in_block = defaultdict(int)
    panels = []

    for i in range(num_panels):
        manufacturer = random.choice(MANUFACTURERS)
        original_wattage = random.choice([400, 450, 500, 550])
        years_operating = int(np.random.randint(0, 16))
        degradation_rate = float(np.random.uniform(0.005, 0.015))
        current_wattage = round(original_wattage * ((1 - degradation_rate) ** years_operating), 1)
        temperature = round(float(np.random.normal(40, 10)), 1)
        temperature = max(20, min(60, temperature))
        dust_level = round(float(np.random.uniform(0, 25)), 1)
        efficiency = round((current_wattage / original_wattage) * 100, 1)

        days_ago = np.random.randint(0, 15 * 365)
        install_date = datetime.now() - timedelta(days=int(days_ago))

        b = block_of_panel[i]
        block_row, block_col = divmod(b, BLOCK_COLS)
        lat_min, lat_max, lon_min, lon_max = _block_bounds(block_row, block_col)

        grid_rows, grid_cols = grid_dims[b]
        pos = position_in_block[b]
        position_in_block[b] += 1
        gr, gc = divmod(pos, grid_cols)

        # Center each panel within its grid cell -> even rows/columns,
        # not a random scatter.
        frac_lat = (gr + 0.5) / grid_rows
        frac_lon = (gc + 0.5) / grid_cols
        latitude = round(lat_min + frac_lat * (lat_max - lat_min), 5)
        longitude = round(lon_min + frac_lon * (lon_max - lon_min), 5)

        block_label = f"Block {row_labels[block_row]}{block_col + 1}"

        panels.append({
            "panel_id": f"PANEL-{i:05d}",
            "manufacturer": manufacturer,
            "original_wattage": original_wattage,
            "current_wattage": current_wattage,
            "years_operating": years_operating,
            "degradation_rate": round(degradation_rate * 100, 2),
            "temperature": temperature,
            "dust_level": dust_level,
            "efficiency": efficiency,
            "installation_date": install_date.strftime("%Y-%m-%d"),
            "farm": FARM_NAME,
            "block": block_label,
            "latitude": latitude,
            "longitude": longitude,
        })

    return pd.DataFrame(panels)


def main():
    print("☀️ SolarPanel Health AI - Data Generator")
    print("Team Optisuns\n")
    print(f"Generating 1000 sample solar panels across {FARM_NAME}...")
    print(f"Layout: {BLOCK_ROWS}x{BLOCK_COLS} maintenance blocks, panels arranged in rows/columns\n")

    df = generate_panel_data(1000)

    os.makedirs("data", exist_ok=True)
    df.to_csv("data/solar_farm_data.csv", index=False)

    print(f"✅ Generated {len(df)} panels")
    print("📁 Saved to: data/solar_farm_data.csv")
    print("\n📊 Data Summary:")
    print(f"   - Farm: {FARM_NAME}")
    print(f"   - Blocks: {df['block'].nunique()}")
    print(f"   - Manufacturers: {df['manufacturer'].nunique()}")
    print(f"   - Avg Efficiency: {df['efficiency'].mean():.1f}%")
    print(f"   - Latitude range: {df['latitude'].min():.5f} to {df['latitude'].max():.5f}")
    print(f"   - Longitude range: {df['longitude'].min():.5f} to {df['longitude'].max():.5f}")


if __name__ == "__main__":
    main()