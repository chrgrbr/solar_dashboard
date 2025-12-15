#!/usr/bin/env python3
"""
Authentication module for Kostal Solar Portal
Logs in and extracts bearer token using Selenium
"""

import os
import time
import json
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Load environment variables from .env file
load_dotenv()

def make_driver():
    """
    Create Chrome driver with correct settings for Mac and Raspberry Pi
    Auto-detects platform and uses appropriate paths
    """
    import platform
    
    options = Options()
    
    # Detect platform
    system = platform.system()
    machine = platform.machine()
    
    if system == "Linux" and ("arm" in machine or "aarch64" in machine):
        # Raspberry Pi
        options.binary_location = "/usr/bin/chromium"
        service = Service("/usr/bin/chromedriver")
    else:
        # Mac or other systems - use webdriver-manager
        service = Service(ChromeDriverManager().install())
    
    # Common options for all platforms
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    
    # CRITICAL: Enable performance logging to capture network requests
    options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

    return webdriver.Chrome(service=service, options=options)


def get_bearer_token(verbose=True):
    """
    Login to Kostal portal and extract bearer token
    
    Reads credentials from environment variables:
    - KOSTAL_USERNAME: Email address
    - KOSTAL_PASSWORD: Password
    
    Args:
        verbose: Print detailed progress messages
    
    Returns:
        str: Bearer token
        
    Raises:
        ValueError: If credentials not found in environment
        Exception: If login fails
    """
    
    # Get credentials from environment
    username = os.environ.get('KOSTAL_USERNAME')
    password = os.environ.get('KOSTAL_PASSWORD')
    
    if not username or not password:
        raise ValueError(
            "Credentials not found. Set environment variables:\n"
            "  export KOSTAL_USERNAME='your.email@example.com'\n"
            "  export KOSTAL_PASSWORD='your_password'"
        )
    
    if verbose:
        print(f"   Username: {username[:20]}...")
        print(f"   Starting Chrome...")
    
    # Use the make_driver function which has all the correct settings
    try:
        driver = make_driver()
        if verbose:
            print("   ✓ Chrome started with network monitoring...")
    except Exception as e:
        raise Exception(
            f"Could not start ChromeDriver.\n"
            f"Error: {e}\n\n"
            f"Make sure Chromium and ChromeDriver are installed:\n"
            f"  sudo apt-get install chromium-browser chromium-chromedriver"
        )
    
    try:
        # Navigate to portal
        if verbose:
            print("   Navigating to portal...")
        driver.get("https://kostal-solar-portal.com")
        
        # Wait for page to load
        time.sleep(2)
        
        # Handle cookie banner - click "Accept All" or "Deny All"
        if verbose:
            print("   Handling cookie banner...")
        try:
            # Wait for cookie banner to appear and click "Deny All" to close it quickly
            deny_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Deny All') or contains(text(), 'Alle ablehnen')]"))
            )
            deny_button.click()
            if verbose:
                print("   ✓ Dismissed cookie banner")
            time.sleep(1)
        except:
            # Try "Accept All" if "Deny All" not found
            try:
                accept_button = WebDriverWait(driver, 2).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accept All') or contains(text(), 'Alle akzeptieren')]"))
                )
                accept_button.click()
                if verbose:
                    print("   ✓ Accepted cookies")
                time.sleep(1)
            except:
                if verbose:
                    print("   No cookie banner found")
        
        # Wait for cookie banner to disappear
        time.sleep(1)
        
        # Click "Einloggen" (Login) button
        if verbose:
            print("   Clicking login button...")
        try:
            # Wait for button to be present, then use JavaScript to click it (bypasses overlay)
            login_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//span[contains(@class, 'mdc-button__label') and contains(text(), 'Einloggen')]/parent::button"))
            )
            # Use JavaScript click to bypass any overlays
            driver.execute_script("arguments[0].click();", login_button)
            if verbose:
                print("   ✓ Clicked 'Einloggen'")
            time.sleep(3)
        except Exception as e:
            raise Exception(f"Could not find 'Einloggen' button: {e}")
        
        # Now wait for the Azure B2C login form
        if verbose:
            print("   Waiting for login form...")
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "signInName"))
        )
        
        # Fill credentials
        if verbose:
            print("   Entering credentials...")
        driver.find_element(By.ID, "signInName").send_keys(username)
        driver.find_element(By.ID, "password").send_keys(password)
        driver.find_element(By.ID, "next").click()
        
        # Wait for redirect to portal
        if verbose:
            print("   Waiting for authentication...")
        WebDriverWait(driver, 30).until(
            lambda d: "kostal-solar-portal.com" in d.current_url 
                     and "b2clogin" not in d.current_url
        )
        
        # Wait a bit more for the app to make API calls
        if verbose:
            print("   Capturing bearer token from network requests...")
        time.sleep(5)  # Give the app time to make authenticated API calls
        
        # Navigate to plant page to trigger API calls
        plant_id = os.environ.get('KOSTAL_PLANT_ID', '1082166')
        if verbose:
            print(f"   Navigating to plant {plant_id} to trigger API calls...")
        driver.get(f"https://kostal-solar-portal.com/plant/{plant_id}/chart-data-dashboard")
        
        # Wait for page to load and make API calls
        if verbose:
            print("   Waiting for API calls...")
        time.sleep(8)
        
        # Extract bearer token from network logs
        token = None
        logs = driver.get_log('performance')
        
        for entry in logs:
            try:
                log = json.loads(entry['message'])['message']
                
                # Look for Network.requestWillBeSent events
                if log.get('method') == 'Network.requestWillBeSent':
                    request = log.get('params', {}).get('request', {})
                    headers = request.get('headers', {})
                    
                    # Check if this request has an Authorization header
                    if 'Authorization' in headers:
                        auth_header = headers['Authorization']
                        if auth_header.startswith('Bearer '):
                            token = auth_header.replace('Bearer ', '')
                            if verbose:
                                print(f"   ✓ Found bearer token ({len(token)} chars)")
                            break
            except:
                continue
        
        if not token:
            raise Exception("Failed to extract bearer token - no Authorization headers captured")
        
        # Save token to file for reuse
        token_file = "./tmp/bearer_token.txt"
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(token_file), exist_ok=True)
        
        with open(token_file, 'w') as f:
            f.write(token)
        if verbose:
            print(f"   ✓ Token saved to {token_file}")
        
        return token
        
    finally:
        driver.quit()


if __name__ == "__main__":
    # Test authentication
    try:
        token = get_bearer_token()
        print(f"✓ Authentication successful")
        print(f"Token: {token[:50]}...")
    except Exception as e:
        print(f"✗ Authentication failed: {e}")