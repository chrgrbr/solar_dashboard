#!/usr/bin/env python3
"""
Boot/Loading screen for Solar Dashboard
Creates a simple loading message for the e-paper display
"""

from PIL import Image, ImageDraw, ImageFont
import os


def get_font(size, bold=False):
    """Get DejaVu font with cross-platform support"""
    font_name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    
    font_paths = [
        f"/usr/share/fonts/truetype/dejavu/{font_name}",
        f"/Library/Fonts/{font_name}",
    ]
    
    for path in font_paths:
        try:
            return ImageFont.truetype(path, size)
        except:
            continue
    
    return ImageFont.load_default()


def create_loading_screen(message="Lade Daten..."):
    """
    Create a loading screen with a customizable message
    
    Args:
        message: Text to display (default: "Lade Daten...")
    
    Returns:
        PIL.Image (264x176, 1-bit)
    """
    img = Image.new('1', (264, 176), 255)
    draw = ImageDraw.Draw(img)
    
    font_title = get_font(24, bold=True)
    font_large = get_font(18)
    
    # Title
    draw.text((20, 40), "Kostal Solar", fill=0, font=font_title)
    draw.text((20, 70), "Dashboard", fill=0, font=font_title)
    
    # Loading message
    draw.text((20, 120), message, fill=0, font=font_large)
    
    # Simple loading bar
    draw.rectangle([(20, 145), (244, 155)], outline=0, width=2)
    
    return img


def create_custom_screen_from_file(filepath):
    """
    Load a custom image from file for boot screen
    
    Args:
        filepath: Path to image file (will be converted to 1-bit)
    
    Returns:
        PIL.Image (264x176, 1-bit) or None if file not found
    """
    try:
        img = Image.open(filepath)
        # Resize to fit display
        img = img.resize((264, 176))
        # Convert to 1-bit
        img = img.convert('L')
        return img
    except FileNotFoundError:
        return None
    except Exception as e:
        print(f"Error loading custom screen: {e}")
        return None


# Test
if __name__ == "__main__":
    import os
    os.makedirs('./tmp', exist_ok=True)
    
    # Create loading screen
    img = create_loading_screen("Lade Daten...")
    img.save('./tmp/loading_screen.png')
    print("✓ Loading screen saved to ./tmp/loading_screen.png")
    
    # Example with custom message
    img2 = create_loading_screen("Verbinde mit Portal...")
    img2.save('./tmp/loading_screen2.png')
    print("✓ Custom loading screen saved to ./tmp/loading_screen2.png")