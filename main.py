#!/usr/bin/env python3
"""
Kostal Solar Dashboard - Main Controller
Handles e-paper display updates and button interactions

Buttons:
- Button 1: Show realtime data
- Button 2: Show daily statistics
- Button 3: Show monthly statistics
- Button 4: Show timeline graph

Command line flags:
- --mock: Run without e-paper hardware (saves to ./tmp/*.png)
- --offline: Skip authentication/API, only use cached data from ./tmp/solar_display_data.json
"""

import os
import sys
import time
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Configuration
PLANT_ID = os.environ.get('KOSTAL_PLANT_ID', '1082166')
DATA_FILE = './tmp/solar_display_data.json'
DATA_CACHE_MINUTES = 15  # Refresh data every 15 minutes
SCREEN_TIMEOUT_MINUTES = 30  # Return to screen 1 after inactivity


class SolarDashboard:
    """Main dashboard controller"""
    
    def __init__(self, mock_mode=False, offline_mode=False):
        """
        Initialize dashboard

        Args:
            mock_mode: If True, run without actual e-paper hardware (for testing)
            offline_mode: If True, never fetch data from API, only use cached data
        """
        self.mock_mode = mock_mode
        self.offline_mode = offline_mode
        self.display_available = False  # Separate flag for display hardware
        self.current_screen = 'realtime'  # Default screen
        self.last_data_fetch = None
        self.last_button_press = datetime.now()
        self.cached_data = None
        self.cached_screens = {}
        self.buttons = {}  # Store button objects for shutdown combo detection
        
        # Initialize e-paper display (only if not in mock mode)
        if not mock_mode:
            self.init_display()
        
        print("Solar Dashboard initialized")
        print(f"Mock mode: {mock_mode}")
        print(f"Offline mode: {offline_mode}")
        print(f"Display available: {self.display_available}")
    
    def init_display(self):
        """Initialize Waveshare e-paper display"""
        try:
            # Try different import paths for Waveshare library
            # Rev 2.2 uses epd2in7_V2
            try:
                from waveshare_epd import epd2in7_V2
                self.epd = epd2in7_V2.EPD()
            except ImportError:
                # Fallback to standard version
                from waveshare_epd import epd2in7
                self.epd = epd2in7.EPD()
            
            self.epd.init()
            self.epd.Clear()
            
            self.display_available = True
            print("✓ E-paper display initialized (2.7 inch)")
            
        except ImportError as e:
            self.display_available = False
            print("✗ Waveshare e-paper library not found!")
            print(f"  Error: {e}")
            print("  Install it from: https://github.com/waveshare/e-Paper")
            print("  Running in mock mode instead...")
            self.mock_mode = True
        except Exception as e:
            self.display_available = False
            print(f"✗ Failed to initialize display: {e}")
            print("  Running in mock mode instead...")
            self.mock_mode = True
    
    def fetch_fresh_data(self, force_reauth=False):
        """Fetch fresh data from API

        Args:
            force_reauth: Force re-authentication even if cached token exists
        """
        print("\n[Fetching data from API...]")

        # Show loading screen if display is available
        if self.display_available:
            try:
                from loading_screen import create_loading_screen
                loading_img = create_loading_screen("Lade Solar-Daten...")
                buffer = self.epd.getbuffer(loading_img)
                self.epd.display(buffer)
            except:
                pass  # If loading screen fails, continue anyway

        try:
            from auth import get_bearer_token
            from solar_data import get_realtime_data, get_daily_data, get_monthly_data
            import requests

            # Try to use cached token first (unless force_reauth)
            token = None
            token_file = './tmp/bearer_token.txt'

            if not force_reauth and os.path.exists(token_file):
                try:
                    with open(token_file, 'r') as f:
                        token = f.read().strip()
                    print("  → Using cached token...")
                except:
                    pass

            # If no cached token, authenticate
            if not token:
                print("  → Authenticating...")
                token = get_bearer_token(verbose=False)
            
            # Try to fetch data with current token
            try:
                # Fetch all data
                print("  → Fetching realtime data...")
                realtime = get_realtime_data(token, PLANT_ID)

                print("  → Fetching daily data...")
                daily = get_daily_data(token, PLANT_ID)

                print("  → Fetching monthly data...")
                monthly = get_monthly_data(token, PLANT_ID)

                # Fetch power timeseries for timeline
                print("  → Fetching power timeseries...")
                base_url = "https://kostal-solar-portal.com"
                headers = {'Authorization': f'Bearer {token}'}

                today = datetime.now()
                date_from = today.replace(hour=0, minute=0, second=0).strftime('%Y-%m-%dT%H:%M:%S.000')
                date_to = today.replace(hour=23, minute=59, second=59).strftime('%Y-%m-%dT%H:%M:%S.999')

                power_url = f"{base_url}/api/chart-data/{PLANT_ID}/power"
                power_params = {'from': date_from, 'to': date_to, 'interval': 'TEN_MINUTES'}

                power_resp = requests.get(power_url, params=power_params, headers=headers, timeout=30)
                power_resp.raise_for_status()
                timeseries_data = power_resp.json()['timeSeries']

            except requests.exceptions.HTTPError as e:
                # If token is invalid (401/403), re-authenticate and retry
                if e.response.status_code in [401, 403]:
                    print("  ✗ Token expired or invalid")
                    if force_reauth:
                        # Already tried re-auth, give up
                        raise
                    print("  → Re-authenticating...")
                    # Recursively retry with force_reauth=True
                    return self.fetch_fresh_data(force_reauth=True)
                else:
                    # Other HTTP error, re-raise
                    raise

            # Calculate total PV generation: pv_consumption_power + grid_feedin_power
            pv_consumption = timeseries_data.get('pv_consumption_power', [])
            grid_feedin = timeseries_data.get('grid_feedin_power', [])

            pv_gen_calculated = []
            for i in range(min(len(pv_consumption), len(grid_feedin))):
                timestamp = pv_consumption[i]['timestamp']
                # Total solar = what we use directly + what we feed to grid
                total_solar = pv_consumption[i]['value'] + grid_feedin[i]['value']
                pv_gen_calculated.append({
                    'timestamp': timestamp,
                    'value': total_solar
                })

            # Get house consumption for comparison
            home_consumption = timeseries_data.get('home_consumption_power', [])

            power_timeseries = {
                'pv_gen': pv_gen_calculated,  # Calculated total solar generation
                'home_consumption_power': home_consumption  # Total house consumption
            }
            
            # Combine all data
            all_data = {
                'realtime': realtime,
                'daily': daily,
                'monthly': monthly,
                'power_timeseries': power_timeseries,
                'fetched_at': datetime.now().isoformat()
            }
            
            # Save to file
            os.makedirs('./tmp', exist_ok=True)
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(all_data, f, indent=2, ensure_ascii=False)
            
            print("  ✓ Data fetched and saved")
            
            self.cached_data = all_data
            self.last_data_fetch = datetime.now()
            
            # Clear screen cache to force regeneration
            self.cached_screens = {}
            
            return all_data
            
        except Exception as e:
            print(f"  ✗ Failed to fetch data: {e}")

            # Check if it's a Selenium timeout
            if "timeout" in str(e).lower() or "timed out" in str(e).lower():
                print("\n  Authentication timed out.")
            return None
    
    def load_data(self, force_refresh=False):
        """
        Load data (from cache or fetch fresh)

        Args:
            force_refresh: Force fetch from API even if cache is fresh
        """
        # In offline mode, NEVER fetch from API
        if self.offline_mode:
            # Try to load from cache file
            if self.cached_data:
                return self.cached_data

            try:
                with open(DATA_FILE, 'r') as f:
                    data = json.load(f)
                    self.cached_data = data

                    # Set last_data_fetch to prevent auto-refresh attempts
                    if not self.last_data_fetch:
                        self.last_data_fetch = datetime.now()

                    print(f"  ✓ Loaded cached data from {DATA_FILE}")
                    return data
            except FileNotFoundError:
                print(f"✗ No cached data found at {DATA_FILE}")
                print("  Run without --offline first to fetch and cache data")
                return None

        # Normal mode: check if we need to refresh
        needs_refresh = force_refresh

        if not needs_refresh and self.last_data_fetch:
            age = datetime.now() - self.last_data_fetch
            if age > timedelta(minutes=DATA_CACHE_MINUTES):
                needs_refresh = True

        if not needs_refresh and not self.cached_data:
            needs_refresh = True

        # Fetch fresh data if needed
        if needs_refresh:
            data = self.fetch_fresh_data()
            if data:
                return data

        # Try to load from cache file
        if self.cached_data:
            return self.cached_data

        try:
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
                self.cached_data = data
                return data
        except FileNotFoundError:
            print("✗ No cached data found, fetching fresh data...")
            return self.fetch_fresh_data()
    
    def generate_screen_image(self, screen_name):
        """
        Generate screen image
        
        Args:
            screen_name: 'realtime', 'daily', 'monthly', or 'timeline'
        
        Returns:
            PIL.Image
        """
        # Check cache
        if screen_name in self.cached_screens:
            return self.cached_screens[screen_name]
        
        # Load data
        data = self.load_data()
        if not data:
            print("✗ No data available")
            return None
        
        # Generate screens
        from epaper_screens import create_all_screens
        
        print(f"  → Generating {screen_name} screen...")
        screens = create_all_screens(data)
        
        # Cache all screens
        self.cached_screens = screens
        
        return screens.get(screen_name)
    
    def display_screen(self, screen_name):
        """
        Display a screen on the e-paper
        
        Args:
            screen_name: 'realtime', 'daily', 'monthly', or 'timeline'
        """
        print(f"\n[Displaying: {screen_name}]")
        
        # Generate image
        image = self.generate_screen_image(screen_name)
        
        if not image:
            print("✗ Failed to generate screen")
            return
        
        # Update current screen
        self.current_screen = screen_name
        self.last_button_press = datetime.now()
        
        if self.display_available:
            # Display is available - use it!
            try:
                # Check if image is grayscale or 1-bit
                if image.mode == 'L':
                    # Grayscale image (4 levels for timeline)
                    # V2 driver supports grayscale - note capital I in Init
                    self.epd.Init_4Gray()
                    buffer = self.epd.getbuffer_4Gray(image)
                    self.epd.display_4Gray(buffer)
                    self.epd.init()  # Re-init for normal mode after grayscale
                else:
                    # 1-bit image (normal black/white)
                    buffer = self.epd.getbuffer(image)
                    self.epd.display(buffer)
                
                print("  ✓ Display updated")
            except Exception as e:
                print(f"  ✗ Display error: {e}")
                # Fall back to saving file
                filename = f'./tmp/current_display_{screen_name}.png'
                image.save(filename)
                print(f"  ✓ (Fallback) Saved to {filename}")
        else:
            # No display - save to file
            filename = f'./tmp/current_display_{screen_name}.png'
            image.save(filename)
            print(f"  ✓ (Mock) Saved to {filename}")
    
    def shutdown(self):
        """Coordinated shutdown - clear display and power off Pi"""
        import subprocess

        print("\n[Shutdown] Button combo detected (1+4)")
        print("  → Clearing display...")

        if self.display_available:
            try:
                self.epd.init()
                self.epd.Clear()
                print("  ✓ Display cleared")
                self.epd.sleep()
                print("  ✓ Display put to sleep")
            except Exception as e:
                print(f"  ✗ Failed to clear display: {e}")

        print("  → Closing buttons...")
        for btn in self.buttons.values():
            try:
                btn.close()
            except:
                pass

        # Power off the Pi (or just exit in mock mode)
        if not self.mock_mode:
            print("\n✓ Shutting down Raspberry Pi in 3 seconds...")
            time.sleep(3)  # Give user time to see the message
            subprocess.run(['sudo', 'systemctl', 'poweroff'])
        else:
            print("\n✓ Shutdown complete (mock mode - not powering off)")
            sys.exit(0)

    def button_1_pressed(self):
        """Button 1: Show realtime screen (or shutdown if Button 4 also pressed)"""
        time.sleep(0.5)  # Brief delay to detect simultaneous press

        # Check for shutdown combo
        if self.buttons.get(4) and self.buttons[4].is_pressed:
            self.shutdown()
            return

        print("\n[Button 1] Realtime")
        self.display_screen('realtime')

    def button_2_pressed(self):
        """Button 2: Show daily screen"""
        print("\n[Button 2] Daily")
        self.display_screen('daily')

    def button_3_pressed(self):
        """Button 3: Show monthly screen"""
        print("\n[Button 3] Monthly")
        self.display_screen('monthly')

    def button_4_pressed(self):
        """Button 4: Show timeline (or shutdown if Button 1 also pressed)"""
        time.sleep(0.5)  # Brief delay to detect simultaneous press

        # Check for shutdown combo
        if self.buttons.get(1) and self.buttons[1].is_pressed:
            self.shutdown()
            return

        print("\n[Button 4] Timeline")
        self.display_screen('timeline')
    
    def check_auto_refresh(self):
        """Check if we need to auto-refresh data or return to default screen"""
        now = datetime.now()
        
        # Auto-refresh data every DATA_CACHE_MINUTES
        if self.last_data_fetch:
            age = now - self.last_data_fetch
            if age > timedelta(minutes=DATA_CACHE_MINUTES):
                print("\n[Auto-refresh] Data is stale, refreshing...")
                self.load_data(force_refresh=True)
                # Update current screen
                self.display_screen(self.current_screen)
        
        # Return to screen 1 after inactivity
        if self.last_button_press:
            inactive = now - self.last_button_press
            if inactive > timedelta(minutes=SCREEN_TIMEOUT_MINUTES):
                if self.current_screen != 'realtime':
                    print("\n[Timeout] Returning to realtime screen...")
                    self.display_screen('realtime')
    
    def run(self):
        """Main loop (for systems without GPIO buttons)"""
        print("\n" + "="*60)
        print("DASHBOARD RUNNING (Mock Mode - No GPIO)")
        print("="*60)
        print("\nCommands:")
        print("  1 - Show realtime")
        print("  2 - Show daily")
        print("  3 - Show monthly")
        print("  4 - Show timeline")
        print("  q - Quit")
        print()
        
        # Initial display
        self.display_screen('realtime')
        
        # Command loop
        while True:
            try:
                cmd = input("\nCommand: ").strip().lower()
                
                if cmd == '1':
                    self.button_1_pressed()
                elif cmd == '2':
                    self.button_2_pressed()
                elif cmd == '3':
                    self.button_3_pressed()
                elif cmd == '4':
                    self.button_4_pressed()
                elif cmd == 'q':
                    print("Exiting...")
                    break
                else:
                    print("Invalid command")
                    
            except KeyboardInterrupt:
                print("\n\nExiting...")
                break
    
    def run_with_gpio(self):
        """Main loop with GPIO button support (for Raspberry Pi)"""
        try:
            from gpiozero import Button
        except ImportError:
            print("✗ gpiozero not available")
            print("  Install: pip install gpiozero")
            print("  Running in keyboard mode instead...")
            return self.run()
        
        # GPIO pin mapping for Rev 2.2 HAT (using gpiozero)
        BUTTON_1_PIN = 5   # KEY1
        BUTTON_2_PIN = 6   # KEY2
        BUTTON_3_PIN = 13  # KEY3
        BUTTON_4_PIN = 19  # KEY4
        
        print("\n" + "="*60)
        print("DASHBOARD RUNNING")
        print("="*60)
        print(f"Button 1: Realtime")
        print(f"Button 2: Daily")
        print(f"Button 3: Monthly")
        print(f"Button 4: Timeline")
        print()
        
        # Create button objects with gpiozero (no conflicts!)
        try:
            btn1 = Button(BUTTON_1_PIN)
            btn2 = Button(BUTTON_2_PIN)
            btn3 = Button(BUTTON_3_PIN)
            btn4 = Button(BUTTON_4_PIN)

            # Store buttons for shutdown combo detection
            self.buttons = {1: btn1, 2: btn2, 3: btn3, 4: btn4}

            # Assign button handlers
            btn1.when_pressed = lambda: self.button_1_pressed()
            btn2.when_pressed = lambda: self.button_2_pressed()
            btn3.when_pressed = lambda: self.button_3_pressed()
            btn4.when_pressed = lambda: self.button_4_pressed()

            
        except Exception as e:
            print(f"✗ Failed to setup buttons: {e}")
            print("  Falling back to keyboard mode...")
            return self.run()
        
        # Initial display
        self.display_screen('realtime')
        
        try:
            # Main loop - just keep alive and check for auto-refresh
            print("\n✓ Dashboard running! Press buttons or Ctrl+C to exit.\n")
            
            while True:
                # Check for auto-refresh
                self.check_auto_refresh()
                time.sleep(10)  # Check every 10 seconds
                
        except KeyboardInterrupt:
            print("\n\nShutting down...")
        finally:
            # Clean up gpiozero buttons
            for btn in self.buttons.values():
                try:
                    btn.close()
                except:
                    pass

            # Clear and sleep display
            if self.display_available:
                try:
                    self.epd.init()
                    self.epd.Clear()
                    self.epd.sleep()
                    print("✓ Display cleared and put to sleep")
                except:
                    pass


def main():
    """Main entry point"""
    # Determine if we're on Raspberry Pi with GPIO
    try:
        import RPi.GPIO
        has_gpio = True
    except ImportError:
        has_gpio = False

    # Check command line args
    mock_mode = '--mock' in sys.argv or not has_gpio
    offline_mode = '--offline' in sys.argv

    # Create dashboard
    dashboard = SolarDashboard(mock_mode=mock_mode, offline_mode=offline_mode)

    # Run appropriate mode
    if has_gpio and not mock_mode:
        dashboard.run_with_gpio()
    else:
        dashboard.run()


if __name__ == "__main__":
    main()