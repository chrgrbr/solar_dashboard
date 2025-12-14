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
    Screen 4: Timeline graph showing solar power curve over the day
    Uses matplotlib for professional graph rendering
    """
    fig, ax = plt.subplots(figsize=(2.64, 1.76), dpi=100)
    fig.patch.set_facecolor('white')
    
    if power_timeseries and len(power_timeseries) > 0:
        # Extract timestamps and values
        timestamps = []
        values_w = []
        
        for entry in power_timeseries:
            try:
                ts = datetime.fromisoformat(entry['timestamp'])
                timestamps.append(ts)
                values_w.append(entry['value'])
            except:
                continue
        
        if timestamps and values_w:
            # Convert to kW
            values_kw = [v / 1000 for v in values_w]
            
            # Plot line
            ax.plot(timestamps, values_kw, color='black', linewidth=1.5)
            ax.fill_between(timestamps, values_kw, alpha=0.3, color='gray')
            
            # Formatting
            ax.set_title(f'TAGESVERLAUF - {daily_data["date"]}', fontsize=10, weight='bold', pad=5)
            ax.set_ylabel('kW', fontsize=8)
            # Removed: ax.set_xlabel('Uhrzeit', fontsize=8)  # Takes too much space
            
            # X-axis formatting (show hours)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            ax.xaxis.set_major_locator(mdates.HourLocator(interval=3))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=6)
            ax.tick_params(axis='y', labelsize=6)
            
            # Grid
            ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            
            # Stats with Ø symbol
            max_kw = max(values_kw)
            avg_kw = sum(values_kw) / len(values_kw)
            total_kwh = daily_data['total_generation_wh'] / 1000
            
            stats_text = f'Max: {max_kw:.1f}kW  |  Ø: {avg_kw:.1f}kW  |  Heute: {total_kwh:.1f}kWh'
            fig.text(0.5, 0.02, stats_text, fontsize=6, ha='center', va='bottom')
        else:
            ax.text(0.5, 0.5, 'Keine Daten', ha='center', va='center', 
                   fontsize=10, transform=ax.transAxes)
    else:
        ax.text(0.5, 0.5, 'Keine Daten verfuegbar', ha='center', va='center',
               fontsize=10, transform=ax.transAxes)
    
    plt.tight_layout()
    
    # Convert to PIL Image
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, facecolor='white', edgecolor='none')
    buf.seek(0)
    img = Image.open(buf)
    plt.close()
    
    # Convert to 1-bit
    img = img.convert('1')
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
