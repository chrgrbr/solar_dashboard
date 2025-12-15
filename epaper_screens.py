#!/usr/bin/env python3
"""
E-Paper Display Generator
Creates all 4 screens for the Waveshare 2.7" display (264x176 pixels)

Screens:
1. Realtime (Echtzeit) - Current power values
2. Daily (Heute) - Today's statistics  
3. Monthly (30 Tage) - 30-day statistics
4. Timeline (Tagesverlauf) - Power curve graph

Usage:
    from epaper_screens import create_all_screens
    images = create_all_screens(data)
    # images = {'realtime': img1, 'daily': img2, 'monthly': img3, 'timeline': img4}
"""

import os
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import io


# ============================================================================
# FONT CONFIGURATION
# ============================================================================

FONT_TITLE = 20
FONT_LARGE = 18
FONT_MEDIUM = 14
FONT_SMALL = 12


def get_font(size, bold=False):
    """Get DejaVu font with cross-platform support (Mac/Raspberry Pi)"""
    font_name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    
    font_paths = [
        f"/usr/share/fonts/truetype/dejavu/{font_name}",  # Raspberry Pi / Linux
        f"/Library/Fonts/{font_name}",                     # Mac
        f"./fonts/{font_name}",                            # Local
    ]
    
    for path in font_paths:
        try:
            return ImageFont.truetype(path, size)
        except:
            continue
    
    return ImageFont.load_default()


def configure_matplotlib_fonts():
    """Configure matplotlib to use DejaVu Sans"""
    import matplotlib.font_manager as fm
    
    dejavu_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/Library/Fonts/DejaVuSans.ttf",
    ]
    
    for path in dejavu_paths:
        if os.path.exists(path):
            fm.fontManager.addfont(path)
            plt.rcParams['font.family'] = 'DejaVu Sans'
            return

configure_matplotlib_fonts()


# ============================================================================
# SCREEN 1: REALTIME (Echtzeit-Daten)
# ============================================================================

def create_screen_realtime(data):
    """
    Screen 1: Real-time power data
    Shows current solar, consumption, grid status in Watts
    """
    img = Image.new('1', (264, 176), 255)
    draw = ImageDraw.Draw(img)
    
    # Load fonts
    font_title = get_font(FONT_TITLE, bold=True)
    font_large = get_font(FONT_LARGE)
    font_medium = get_font(FONT_MEDIUM)
    font_small = get_font(FONT_SMALL)
    
    # Extract timestamp
    try:
        timestamp = datetime.fromisoformat(data['timestamp'])
        time_str = timestamp.strftime('%H:%M')
    except:
        time_str = datetime.now().strftime('%H:%M')
    
    # Header
    draw.text((5, 2), "ECHTZEIT", fill=0, font=font_title)
    draw.text((180, 5), time_str, fill=0, font=font_medium)
    draw.line([(0, 25), (264, 25)], fill=0, width=2)
    
    # Solar power (in Watts)
    solar_w = data['solar_power_w']
    draw.text((5, 35), "Solarleistung:", fill=0, font=font_medium)
    draw.text((150, 32), f"{solar_w:>6.0f} W", fill=0, font=font_large)
    
    # Consumption (in Watts)
    consumption_w = data['consumption_w']
    draw.text((5, 60), "Verbrauch:", fill=0, font=font_medium)
    draw.text((150, 57), f"{consumption_w:>6.0f} W", fill=0, font=font_large)
    
    # Grid feed-in (in Watts)
    feedin_w = data['grid_feedin_w']
    draw.text((5, 85), "Einspeisung:", fill=0, font=font_medium)
    draw.text((150, 82), f"{feedin_w:>6.0f} W", fill=0, font=font_large)
    
    # Grid import (in Watts)
    import_w = data['grid_import_w']
    draw.text((5, 110), "Netzbezug:", fill=0, font=font_medium)
    draw.text((150, 107), f"{import_w:>6.0f} W", fill=0, font=font_large)
    
    # Status indicator
    net_w = data['grid_net_w']
    if net_w > 100:
        status = "↑ Einspeisung"
    elif net_w < -100:
        status = "↓ Netzbezug"
    else:
        status = "~ Ausgeglichen"
    
    draw.line([(0, 135), (264, 135)], fill=0, width=1)
    draw.text((5, 145), "Status:", fill=0, font=font_small)
    draw.text((60, 143), status, fill=0, font=font_medium)
    
    return img


# ============================================================================
# SCREEN 2: DAILY (Tagesstatistik)
# ============================================================================

def create_screen_daily(data):
    """
    Screen 2: Today's statistics
    Shows daily generation and consumption totals
    """
    img = Image.new('1', (264, 176), 255)
    draw = ImageDraw.Draw(img)
    
    font_title = get_font(FONT_TITLE, bold=True)
    font_large = get_font(FONT_LARGE)
    font_medium = get_font(FONT_MEDIUM)
    font_small = get_font(FONT_SMALL)
    
    # Header
    draw.text((5, 2), "HEUTE", fill=0, font=font_title)
    draw.text((160, 5), data['date'], fill=0, font=font_medium)
    draw.line([(0, 25), (264, 25)], fill=0, width=2)
    
    # Generation
    gen_kwh = data['total_generation_wh'] / 1000
    draw.text((5, 32), "Erzeugung:", fill=0, font=font_medium)
    draw.text((155, 29), f"{gen_kwh:6.2f} kWh", fill=0, font=font_large)
    
    feedin_kwh = data['fed_to_grid_wh'] / 1000
    draw.text((15, 52), "→ Eingespeist", fill=0, font=font_small)
    draw.text((160, 50), f"{feedin_kwh:5.2f} kWh", fill=0, font=font_medium)
    
    self_kwh = data['self_consumed_wh'] / 1000
    draw.text((15, 68), "→ Eigenverbrauch", fill=0, font=font_small)
    draw.text((160, 66), f"{self_kwh:5.2f} kWh", fill=0, font=font_medium)
    
    # Consumption
    cons_kwh = data['total_consumption_wh'] / 1000
    draw.text((5, 88), "Verbrauch:", fill=0, font=font_medium)
    draw.text((155, 85), f"{cons_kwh:6.2f} kWh", fill=0, font=font_large)
    
    solar_kwh = data['from_solar_wh'] / 1000
    draw.text((15, 108), "→ Von Solar", fill=0, font=font_small)
    draw.text((160, 106), f"{solar_kwh:5.2f} kWh", fill=0, font=font_medium)
    
    grid_kwh = data['from_grid_wh'] / 1000
    draw.text((15, 124), "→ Vom Netz", fill=0, font=font_small)
    draw.text((160, 122), f"{grid_kwh:5.2f} kWh", fill=0, font=font_medium)
    
    # Self-sufficiency
    draw.line([(0, 145), (264, 145)], fill=0, width=1)
    draw.text((5, 153), "Autarkie:", fill=0, font=font_medium)
    draw.text((155, 150), f"{data['self_sufficiency_pct']:5.1f} %", fill=0, font=font_large)
    
    return img


# ============================================================================
# SCREEN 3: MONTHLY (30-Tage-Statistik)
# ============================================================================

def create_screen_monthly(data):
    """
    Screen 3: Last 30 days statistics
    Shows monthly generation and consumption totals
    """
    img = Image.new('1', (264, 176), 255)
    draw = ImageDraw.Draw(img)
    
    font_title = get_font(FONT_TITLE, bold=True)
    font_large = get_font(FONT_LARGE)
    font_medium = get_font(FONT_MEDIUM)
    font_small = get_font(FONT_SMALL)
    
    # Header
    draw.text((5, 2), "30 TAGE", fill=0, font=font_title)
    draw.text((140, 5), data['period'], fill=0, font=font_medium)
    draw.line([(0, 25), (264, 25)], fill=0, width=2)
    
    # Generation
    gen_kwh = data['total_generation_wh'] / 1000
    draw.text((5, 32), "Erzeugung:", fill=0, font=font_medium)
    draw.text((155, 29), f"{gen_kwh:6.1f} kWh", fill=0, font=font_large)
    
    avg_kwh = data['daily_average_wh'] / 1000
    draw.text((15, 52), "→ Ø täglich", fill=0, font=font_small)
    draw.text((160, 50), f"{avg_kwh:5.1f} kWh", fill=0, font=font_medium)
    
    feedin_kwh = data['fed_to_grid_wh'] / 1000
    draw.text((15, 68), "→ Eingespeist", fill=0, font=font_small)
    draw.text((160, 66), f"{feedin_kwh:5.1f} kWh", fill=0, font=font_medium)
    
    # Consumption
    cons_kwh = data['total_consumption_wh'] / 1000
    draw.text((5, 88), "Verbrauch:", fill=0, font=font_medium)
    draw.text((155, 85), f"{cons_kwh:6.1f} kWh", fill=0, font=font_large)
    
    solar_kwh = data['from_solar_wh'] / 1000
    draw.text((15, 108), "→ Von Solar", fill=0, font=font_small)
    draw.text((160, 106), f"{solar_kwh:5.1f} kWh", fill=0, font=font_medium)
    
    grid_kwh = data['from_grid_wh'] / 1000
    draw.text((15, 124), "→ Vom Netz", fill=0, font=font_small)
    draw.text((160, 122), f"{grid_kwh:5.1f} kWh", fill=0, font=font_medium)
    
    # Self-sufficiency
    draw.line([(0, 145), (264, 145)], fill=0, width=1)
    draw.text((5, 153), "Autarkie:", fill=0, font=font_medium)
    draw.text((155, 150), f"{data['self_sufficiency_pct']:5.1f} %", fill=0, font=font_large)
    
    return img


# ============================================================================
# SCREEN 4: TIMELINE (Tagesverlauf)
# ============================================================================

def create_screen_timeline(daily_data, power_timeseries):
    """
    Screen 4: Timeline graph showing solar generation AND house consumption
    Uses 4-level grayscale with filled areas and dashed/solid lines
    Light gray = consumption only (grid import)
    Dark gray = overlap (self-consumption)
    """
    # Create 4-level grayscale image (L mode: 0=black, 85=dark gray, 170=light gray, 255=white)
    img = Image.new('L', (264, 176), 255)  # Start with white background
    draw = ImageDraw.Draw(img)
    
    # Get font
    try:
        font_title = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 10)
        font_small = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 7)
    except:
        font_title = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    # Title
    draw.text((5, 2), f'Tagesverlauf - {daily_data["date"]}', fill=0, font=font_title)
    
    # Extract data
    pv_gen_data = None
    consumption_data = None
    
    if power_timeseries:
        if isinstance(power_timeseries, dict):
            pv_gen_data = power_timeseries.get('pv_gen', [])
            consumption_data = power_timeseries.get('home_consumption_power', [])
        else:
            pv_gen_data = power_timeseries
    
    if not pv_gen_data or len(pv_gen_data) == 0:
        draw.text((80, 80), 'Keine Daten verfügbar', fill=0, font=font_small)
        return img.convert('L')
    
    # Parse generation data
    gen_timestamps = []
    gen_values_w = []
    
    for entry in pv_gen_data:
        try:
            ts = datetime.fromisoformat(entry['timestamp'])
            gen_timestamps.append(ts)
            gen_values_w.append(entry['value'])
        except:
            continue
    
    # Parse consumption data
    cons_timestamps = []
    cons_values_w = []
    
    if consumption_data:
        for entry in consumption_data:
            try:
                ts = datetime.fromisoformat(entry['timestamp'])
                cons_timestamps.append(ts)
                cons_values_w.append(entry['value'])
            except:
                continue
    
    if not gen_timestamps:
        draw.text((80, 80), 'Keine Daten', fill=0, font=font_small)
        return img.convert('L')
    
    # Convert to kW
    gen_values_kw = [v / 1000 for v in gen_values_w]
    cons_values_kw = [v / 1000 for v in cons_values_w] if cons_values_w else []
    
    # Graph dimensions
    graph_x = 30
    graph_y = 20
    graph_w = 225
    graph_h = 125
    
    # Find max value for scaling
    max_val = max(gen_values_kw)
    if cons_values_kw:
        max_val = max(max_val, max(cons_values_kw))
    max_val = max(max_val, 0.1)  # Avoid division by zero
    
    # Draw axes (light gray)
    draw.line([(graph_x, graph_y), (graph_x, graph_y + graph_h)], fill=170, width=1)  # Y-axis
    draw.line([(graph_x, graph_y + graph_h), (graph_x + graph_w, graph_y + graph_h)], fill=170, width=1)  # X-axis
    
    # Draw grid lines (very light gray)
    for i in range(1, 5):
        y = graph_y + int(graph_h * i / 5)
        draw.line([(graph_x, y), (graph_x + graph_w, y)], fill=200, width=1)
    
    # Function to convert data point to pixel coordinates
    def to_pixel(timestamp_idx, value_kw, num_points):
        x = graph_x + int((timestamp_idx / max(num_points - 1, 1)) * graph_w)
        y = graph_y + graph_h - int((value_kw / max_val) * graph_h)
        return (x, y)
    
    # Calculate minimum of both curves at each point for overlap
    if len(cons_values_kw) > 1 and len(gen_values_kw) > 1 and len(cons_values_kw) == len(gen_values_kw):
        # Fill light gray under consumption ONLY where it exceeds generation
        points_cons = [to_pixel(i, val, len(cons_values_kw)) for i, val in enumerate(cons_values_kw)]
        points_gen = [to_pixel(i, gen_values_kw[i], len(gen_values_kw)) for i in range(len(gen_values_kw))]
        
        # Fill under consumption line (light gray for total)
        polygon_points = points_cons + [(graph_x + graph_w, graph_y + graph_h), (graph_x, graph_y + graph_h)]
        draw.polygon(polygon_points, fill=170)
        
        # Fill under generation line (dark gray - creates overlap effect)
        polygon_points = points_gen + [(graph_x + graph_w, graph_y + graph_h), (graph_x, graph_y + graph_h)]
        draw.polygon(polygon_points, fill=85)
        
    elif len(cons_values_kw) > 1:
        # Only consumption data
        points = [to_pixel(i, val, len(cons_values_kw)) for i, val in enumerate(cons_values_kw)]
        polygon_points = points + [(graph_x + graph_w, graph_y + graph_h), (graph_x, graph_y + graph_h)]
        draw.polygon(polygon_points, fill=170)
        
    elif len(gen_values_kw) > 1:
        # Only generation data
        points = [to_pixel(i, val, len(gen_values_kw)) for i, val in enumerate(gen_values_kw)]
        polygon_points = points + [(graph_x + graph_w, graph_y + graph_h), (graph_x, graph_y + graph_h)]
        draw.polygon(polygon_points, fill=85)
    
    # Draw CONSUMPTION line DASHED (black)
    if len(cons_values_kw) > 1:
        points = [to_pixel(i, val, len(cons_values_kw)) for i, val in enumerate(cons_values_kw)]
        for i in range(len(points) - 1):
            if i % 2 == 0:  # Dashed
                draw.line([points[i], points[i + 1]], fill=0, width=2)
    
    # Draw GENERATION line SOLID (black)
    if len(gen_values_kw) > 1:
        points = [to_pixel(i, val, len(gen_values_kw)) for i, val in enumerate(gen_values_kw)]
        for i in range(len(points) - 1):
            draw.line([points[i], points[i + 1]], fill=0, width=2)
    
    # Y-axis label
    draw.text((8, graph_y + int(graph_h/2) - 10), 'kW', fill=0, font=font_small)
    
    # Y-axis tick labels
    draw.text((5, graph_y - 5), f'{max_val:.1f}', fill=0, font=font_small)
    draw.text((5, graph_y + graph_h - 5), '0', fill=0, font=font_small)
    
    # X-axis time labels (multiple points)
    if gen_timestamps and len(gen_timestamps) > 0:
        # Show times at 0%, 25%, 50%, 75%, 100%
        indices = [0, len(gen_timestamps)//4, len(gen_timestamps)//2, 3*len(gen_timestamps)//4, len(gen_timestamps)-1]
        for idx in indices:
            if idx < len(gen_timestamps):
                time_str = gen_timestamps[idx].strftime('%H:%M')
                x_pos = graph_x + int((idx / (len(gen_timestamps) - 1)) * graph_w) - 10
                draw.text((x_pos, graph_y + graph_h + 2), time_str, fill=0, font=font_small)
    
    # Return as grayscale (4 levels)
    return img


# ============================================================================
# MAIN FUNCTION
# ============================================================================

def create_all_screens(data):
    """
    Create all 4 screens from data dictionary
    
    Args:
        data: dict with keys 'realtime', 'daily', 'monthly', 'power_timeseries'
              (as generated by solar_data.py)
    
    Returns:
        dict: {'realtime': Image, 'daily': Image, 'monthly': Image, 'timeline': Image}
    """
    screens = {}
    
    screens['realtime'] = create_screen_realtime(data['realtime'])
    screens['daily'] = create_screen_daily(data['daily'])
    screens['monthly'] = create_screen_monthly(data['monthly'])
    screens['timeline'] = create_screen_timeline(data['daily'], data.get('power_timeseries'))
    
    return screens


# ============================================================================
# TEST / STANDALONE MODE
# ============================================================================

if __name__ == "__main__":
    import json
    
    # Create output directory
    os.makedirs('./tmp', exist_ok=True)
    
    # Load test data
    try:
        with open('./tmp/solar_display_data.json', 'r') as f:
            all_data = json.load(f)
    except FileNotFoundError:
        print("✗ No test data found. Run solar_data.py first to generate test data.")
        exit(1)
    
    print("Generating all 4 e-paper screens...")
    
    # Generate all screens
    screens = create_all_screens(all_data)
    
    # Save preview images
    screens['realtime'].save('./tmp/screen1_realtime.png')
    print("✓ Screen 1 (Realtime) saved to ./tmp/screen1_realtime.png")
    
    screens['daily'].save('./tmp/screen2_daily.png')
    print("✓ Screen 2 (Daily) saved to ./tmp/screen2_daily.png")
    
    screens['monthly'].save('./tmp/screen3_monthly.png')
    print("✓ Screen 3 (Monthly) saved to ./tmp/screen3_monthly.png")
    
    screens['timeline'].save('./tmp/screen4_timeline.png')
    print("✓ Screen 4 (Timeline) saved to ./tmp/screen4_timeline.png")
    
    print("\n✅ All screens generated successfully!")
    print("These images are ready to be sent to the e-paper display.")