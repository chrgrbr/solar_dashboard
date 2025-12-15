#!/usr/bin/env python3
"""
Solar Data Module
Provides structured data for different display screens
"""

import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()


def get_realtime_data(token, plant_id):
    """
    Get real-time power data (Screen 1)
    
    Returns:
        dict: {
            'timestamp': str,
            'solar_power_w': float,
            'consumption_w': float,
            'grid_feedin_w': float,
            'grid_import_w': float,
            'grid_net_w': float,  # positive = exporting, negative = importing
        }
    """
    import requests
    
    base_url = "https://kostal-solar-portal.com"
    headers = {'Authorization': f'Bearer {token}'}
    
    # Get today's date range
    today = datetime.now()
    date_from = today.replace(hour=0, minute=0, second=0).strftime('%Y-%m-%dT%H:%M:%S.000')
    date_to = today.replace(hour=23, minute=59, second=59).strftime('%Y-%m-%dT%H:%M:%S.999')
    
    # Fetch power data
    power_url = f"{base_url}/api/chart-data/{plant_id}/power"
    power_params = {'from': date_from, 'to': date_to, 'interval': 'TEN_MINUTES'}
    
    resp = requests.get(power_url, params=power_params, headers=headers, timeout=30)
    resp.raise_for_status()
    power_data = resp.json()['timeSeries']
    
    # Get latest non-zero values
    def get_latest(series_name):
        values = power_data.get(series_name, [])
        for entry in reversed(values):
            if entry.get('value') is not None and entry['value'] != 0:
                return entry['value'], entry['timestamp']
        if values:
            return values[-1]['value'], values[-1]['timestamp']
        return 0.0, None
    
    solar_power, timestamp = get_latest('pv_consumption_power')
    consumption, _ = get_latest('home_consumption_power')
    grid_feedin, _ = get_latest('grid_feedin_power')
    grid_import, _ = get_latest('grid_consumption_power')
    
    return {
        'timestamp': timestamp or datetime.now().isoformat(),
        'solar_power_w': solar_power,
        'consumption_w': consumption,
        'grid_feedin_w': grid_feedin,
        'grid_import_w': grid_import,
        'grid_net_w': grid_feedin - grid_import,
    }


def get_daily_data(token, plant_id):
    """
    Get today's statistics (Screen 2)
    
    Returns:
        dict: {
            'date': str,
            'total_generation_wh': float,
            'fed_to_grid_wh': float,
            'self_consumed_wh': float,
            'total_consumption_wh': float,
            'from_solar_wh': float,
            'from_grid_wh': float,
            'self_sufficiency_pct': float,
        }
    """
    import requests
    
    base_url = "https://kostal-solar-portal.com"
    headers = {'Authorization': f'Bearer {token}'}
    
    # Get today's date range
    today = datetime.now()
    date_from = today.replace(hour=0, minute=0, second=0).strftime('%Y-%m-%dT%H:%M:%S.000')
    date_to = today.replace(hour=23, minute=59, second=59).strftime('%Y-%m-%dT%H:%M:%S.999')
    
    # Fetch generation data
    gen_url = f"{base_url}/api/chart-data/{plant_id}/generation"
    gen_params = {'from': date_from, 'to': date_to, 'interval': 'DAY'}
    gen_resp = requests.get(gen_url, params=gen_params, headers=headers, timeout=30)
    gen_resp.raise_for_status()
    gen_data = gen_resp.json()['timeSeries']
    
    # Fetch consumption data
    cons_url = f"{base_url}/api/chart-data/{plant_id}/home-consumption"
    cons_params = {'from': date_from, 'to': date_to, 'interval': 'DAY'}
    cons_resp = requests.get(cons_url, params=cons_params, headers=headers, timeout=30)
    cons_resp.raise_for_status()
    cons_data = cons_resp.json()['timeSeries']
    
    # Extract values
    total_generation = gen_data.get('total_yield', [{}])[0].get('value', 0)
    fed_to_grid = gen_data.get('feed_in_yield', [{}])[0].get('value', 0)
    self_consumed = gen_data.get('self_consumption_yield', [{}])[0].get('value', 0)
    
    total_consumption = cons_data.get('total_consumption_yield', [{}])[0].get('value', 0)
    from_solar = cons_data.get('pv_consumption_yield', [{}])[0].get('value', 0)
    from_grid = cons_data.get('grid_consumption_yield', [{}])[0].get('value', 0)
    
    # Calculate self-sufficiency
    self_sufficiency = 0.0
    if total_consumption > 0:
        self_sufficiency = (from_solar / total_consumption) * 100
    
    return {
        'date': today.strftime('%d.%m.%Y'),
        'total_generation_wh': total_generation,
        'fed_to_grid_wh': fed_to_grid,
        'self_consumed_wh': self_consumed,
        'total_consumption_wh': total_consumption,
        'from_solar_wh': from_solar,
        'from_grid_wh': from_grid,
        'self_sufficiency_pct': self_sufficiency,
    }


def get_monthly_data(token, plant_id):
    """
    Get last 30 days statistics (Screen 3)
    
    Returns:
        dict: {
            'period': str (e.g., "14.11 - 14.12"),
            'total_generation_wh': float,
            'fed_to_grid_wh': float,
            'self_consumed_wh': float,
            'total_consumption_wh': float,
            'from_solar_wh': float,
            'from_grid_wh': float,
            'self_sufficiency_pct': float,
            'daily_average_wh': float,
        }
    """
    import requests
    
    base_url = "https://kostal-solar-portal.com"
    headers = {'Authorization': f'Bearer {token}'}
    
    # Get last 30 days range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    date_from = start_date.replace(hour=0, minute=0, second=0).strftime('%Y-%m-%dT%H:%M:%S.000')
    date_to = end_date.replace(hour=23, minute=59, second=59).strftime('%Y-%m-%dT%H:%M:%S.999')
    
    # Fetch generation data
    gen_url = f"{base_url}/api/chart-data/{plant_id}/generation"
    gen_params = {'from': date_from, 'to': date_to, 'interval': 'DAY'}
    gen_resp = requests.get(gen_url, params=gen_params, headers=headers, timeout=30)
    gen_resp.raise_for_status()
    gen_data = gen_resp.json()['timeSeries']
    
    # Fetch consumption data
    cons_url = f"{base_url}/api/chart-data/{plant_id}/home-consumption"
    cons_params = {'from': date_from, 'to': date_to, 'interval': 'DAY'}
    cons_resp = requests.get(cons_url, params=cons_params, headers=headers, timeout=30)
    cons_resp.raise_for_status()
    cons_data = cons_resp.json()['timeSeries']
    
    # Sum up all days
    total_generation = sum(entry['value'] for entry in gen_data.get('total_yield', []))
    fed_to_grid = sum(entry['value'] for entry in gen_data.get('feed_in_yield', []))
    self_consumed = sum(entry['value'] for entry in gen_data.get('self_consumption_yield', []))
    
    total_consumption = sum(entry['value'] for entry in cons_data.get('total_consumption_yield', []))
    from_solar = sum(entry['value'] for entry in cons_data.get('pv_consumption_yield', []))
    from_grid = sum(entry['value'] for entry in cons_data.get('grid_consumption_yield', []))
    
    # Calculate self-sufficiency and average
    self_sufficiency = 0.0
    if total_consumption > 0:
        self_sufficiency = (from_solar / total_consumption) * 100
    
    daily_average = total_generation / 30
    
    period_str = f"{start_date.strftime('%d.%m')} - {end_date.strftime('%d.%m')}"
    
    return {
        'period': period_str,
        'total_generation_wh': total_generation,
        'fed_to_grid_wh': fed_to_grid,
        'self_consumed_wh': self_consumed,
        'total_consumption_wh': total_consumption,
        'from_solar_wh': from_solar,
        'from_grid_wh': from_grid,
        'self_sufficiency_pct': self_sufficiency,
        'daily_average_wh': daily_average,
    }


# Test data generation (save to file for development)
if __name__ == "__main__":
    import json
    import requests
    from auth import get_bearer_token
    
    plant_id = os.environ.get('KOSTAL_PLANT_ID', '1082166')
    
    print("Fetching data for development...")
    
    try:
        token = get_bearer_token(verbose=False)
        
        # Fetch all three screens worth of data
        print("\n[1/3] Fetching real-time data...")
        realtime = get_realtime_data(token, plant_id)
        
        print("[2/3] Fetching daily data...")
        daily = get_daily_data(token, plant_id)
        
        print("[3/3] Fetching monthly data...")
        monthly = get_monthly_data(token, plant_id)
        
        # Also fetch power time series for timeline visualization
        print("[4/4] Fetching power time series for timeline...")
        base_url = "https://kostal-solar-portal.com"
        headers = {'Authorization': f'Bearer {token}'}
        
        today = datetime.now()
        date_from = today.replace(hour=0, minute=0, second=0).strftime('%Y-%m-%dT%H:%M:%S.000')
        date_to = today.replace(hour=23, minute=59, second=59).strftime('%Y-%m-%dT%H:%M:%S.999')
        
        power_url = f"{base_url}/api/chart-data/{plant_id}/power"
        power_params = {'from': date_from, 'to': date_to, 'interval': 'TEN_MINUTES'}
        
        power_resp = requests.get(power_url, params=power_params, headers=headers, timeout=30)
        power_resp.raise_for_status()
        power_timeseries = power_resp.json()['timeSeries']['pv_consumption_power']
        
        # Combine into one structure
        all_data = {
            'realtime': realtime,
            'daily': daily,
            'monthly': monthly,
            'power_timeseries': power_timeseries,  # Add this for timeline graph
            'fetched_at': datetime.now().isoformat()
        }
        
        # Save to file
        output_file = './tmp/solar_display_data.json'
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Data saved to {output_file}")
        print("\nPreview:")
        print(json.dumps(all_data, indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()