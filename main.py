#!/usr/bin/env python3
"""
Kostal Solar Dashboard - Main Controller
Handles e-paper display updates and button interactions

Buttons:
- Button 1: Show realtime data
- Button 2: Show daily statistics
- Button 3: Show monthly statistics
- Button 4: Refresh data from API
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
PLANT_ID = os.environ.get('KOSTAL_PLANT_ID')
DATA_FILE = './tmp/solar_display_data.json'
DATA_CACHE_MINUTES = 15  # Refresh data every 15 minutes
SCREEN_TIMEOUT_MINUTES = 30  # Return to screen 1 after inactivity


class SolarDashboard:
    """Main dashboard controller"""
    
    def __init__(self, mock_mode=False):
        """
        Initialize dashboard
        
        Args:
            mock_mode: If True, run without actual e-paper hardware (for testing)
        """
        self.mock_mode = mock_mode
        self.display_available = False  # Separate flag for display hardware
        self.current_screen = 'realtime'  # Default screen
        self.last_data_fetch = None
        self.last_button_press = datetime.now()
        self.cached_data = None
        self.cached_screens = {}
        
        # Initialize e-paper display (only if not in mock mode)
        if not mock_mode:
            self.init_display()
        
        print("Solar Dashboard initialized")
        print(f"Mock mode: {mock_mode}")
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
    
    def fetch_fresh_data(self):
        """Fetch fresh data from API"""
        print("\n[Fetching data from API...]")
        
        try:
            from auth import get_bearer_token
            from solar_data import get_realtime_data, get_daily_data, get_monthly_data
            import requests
            
            # Authenticate
            print("  → Authenticating...")
            token = get_bearer_token(verbose=False)
            
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
            power_timeseries = power_resp.json()['timeSeries']['pv_consumption_power']
            
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
            return None
    
    def load_data(self, force_refresh=False):
        """
        Load data (from cache or fetch fresh)
        
        Args:
            force_refresh: Force fetch from API even if cache is fresh
        """
        # Check if we need to refresh
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
    
    def button_1_pressed(self):
        """Button 1: Show realtime screen"""
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
        """Button 4: Refresh data and show timeline"""
        print("\n[Button 4] Refresh & Timeline")
        self.load_data(force_refresh=True)
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
        print("  4 - Refresh & show timeline")
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
            import RPi.GPIO as GPIO
        except ImportError:
            print("✗ RPi.GPIO not available")
            print("  Running in mock mode instead...")
            return self.run()
        
        # GPIO pin mapping (adjust based on your Waveshare HAT)
        # Check Waveshare wiki for your specific model
        BUTTON_1_PIN = 5   # KEY1
        BUTTON_2_PIN = 6   # KEY2
        BUTTON_3_PIN = 13  # KEY3
        BUTTON_4_PIN = 19  # KEY4
        
        print("\n" + "="*60)
        print("DASHBOARD RUNNING (GPIO Mode)")
        print("="*60)
        print(f"Button 1 (GPIO {BUTTON_1_PIN}): Realtime")
        print(f"Button 2 (GPIO {BUTTON_2_PIN}): Daily")
        print(f"Button 3 (GPIO {BUTTON_3_PIN}): Monthly")
        print(f"Button 4 (GPIO {BUTTON_4_PIN}): Refresh & Timeline")
        print()
        
        # Clean up any existing GPIO configuration
        GPIO.setwarnings(False)
        GPIO.cleanup()
        
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        
        try:
            GPIO.setup(BUTTON_1_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.setup(BUTTON_2_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.setup(BUTTON_3_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.setup(BUTTON_4_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        except Exception as e:
            print(f"✗ Failed to setup GPIO pins: {e}")
            print("  Falling back to mock mode...")
            GPIO.cleanup()
            return self.run()
        
        # Button callbacks
        try:
            GPIO.add_event_detect(BUTTON_1_PIN, GPIO.FALLING, callback=lambda x: self.button_1_pressed(), bouncetime=300)
            GPIO.add_event_detect(BUTTON_2_PIN, GPIO.FALLING, callback=lambda x: self.button_2_pressed(), bouncetime=300)
            GPIO.add_event_detect(BUTTON_3_PIN, GPIO.FALLING, callback=lambda x: self.button_3_pressed(), bouncetime=300)
            GPIO.add_event_detect(BUTTON_4_PIN, GPIO.FALLING, callback=lambda x: self.button_4_pressed(), bouncetime=300)
        except RuntimeError as e:
            print(f"✗ Failed to add button detection: {e}")
            print("  This usually means:")
            print("    1. Buttons are already configured (try: sudo pkill python)")
            print("    2. GPIO pins are in use by another process")
            print("    3. HAT is not properly connected")
            print("\n  Continuing without buttons - use keyboard commands...")
            GPIO.cleanup()
            # Don't call self.run() - just continue with keyboard input below
        
        # Initial display
        self.display_screen('realtime')
        
        try:
            # Main loop
            print("\n✓ Dashboard running!")
            print("  Press buttons OR type commands: 1/2/3/4, Ctrl+C to exit\n")
            
            # Run both GPIO monitoring and keyboard input
            import select
            import sys
            
            while True:
                # Check for auto-refresh
                self.check_auto_refresh()
                
                # Check for keyboard input (non-blocking)
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    cmd = sys.stdin.readline().strip()
                    if cmd == '1':
                        self.button_1_pressed()
                    elif cmd == '2':
                        self.button_2_pressed()
                    elif cmd == '3':
                        self.button_3_pressed()
                    elif cmd == '4':
                        self.button_4_pressed()
                    elif cmd.lower() == 'q':
                        print("Exiting...")
                        break
                
                time.sleep(0.1)  # Small sleep to prevent CPU spinning
                
        except KeyboardInterrupt:
            print("\n\nShutting down...")
        finally:
            GPIO.cleanup()
            if self.display_available:
                self.epd.sleep()


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
    
    # Create dashboard
    dashboard = SolarDashboard(mock_mode=mock_mode)
    
    # Run appropriate mode
    if has_gpio and not mock_mode:
        dashboard.run_with_gpio()
    else:
        dashboard.run()


if __name__ == "__main__":
    main()