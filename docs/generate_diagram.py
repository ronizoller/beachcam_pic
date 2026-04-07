#!/usr/bin/env python3
"""
Generate hardware wiring diagram as PNG
Run: python generate_diagram.py
Output: hardware_wiring.png
"""

from PIL import Image, ImageDraw, ImageFont
import os

# Image settings
WIDTH = 1600
HEIGHT = 1100
BG_COLOR = (250, 250, 250)

# Colors
BLACK = (0, 0, 0)
RED = (220, 50, 50)
BLUE = (50, 100, 220)
GREEN = (50, 180, 80)
YELLOW = (200, 160, 30)
ORANGE = (230, 130, 50)
PURPLE = (150, 80, 180)
GRAY = (120, 120, 120)
LIGHT_GRAY = (200, 200, 200)
WHITE = (255, 255, 255)
DARK_GRAY = (60, 60, 60)

# Component colors
BATTERY_COLOR = (144, 238, 144)
TP4056_COLOR = (135, 206, 235)
SWITCH_COLOR = (222, 184, 135)
ESP32_COLOR = (70, 70, 70)
EINK_COLOR = (230, 230, 240)
EINK_HAT_COLOR = (200, 200, 220)
PI_COLOR = (255, 182, 193)


def get_fonts():
    """Try to load fonts, fall back to default"""
    try:
        font_large = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
        font_medium = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
        font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 11)
        font_title = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 28)
    except:
        font_large = ImageFont.load_default()
        font_medium = font_large
        font_small = font_large
        font_title = font_large
    return font_title, font_large, font_medium, font_small


def draw_box(draw, x, y, w, h, fill_color, label, sublabel="", fonts=None):
    """Draw a component box with centered labels"""
    font_large, font_medium, font_small = fonts[1], fonts[2], fonts[3]

    # Draw box with border
    draw.rounded_rectangle((x, y, x+w, y+h), radius=8, fill=fill_color, outline=BLACK, width=2)

    # Center the label
    if sublabel:
        draw.text((x + w//2, y + h//2 - 12), label, fill=BLACK, font=font_medium, anchor="mm")
        draw.text((x + w//2, y + h//2 + 8), sublabel, fill=GRAY, font=font_small, anchor="mm")
    else:
        draw.text((x + w//2, y + h//2), label, fill=BLACK, font=font_medium, anchor="mm")


def draw_wire(draw, points, color, width=3):
    """Draw a wire through multiple points"""
    for i in range(len(points) - 1):
        draw.line([points[i], points[i+1]], fill=color, width=width)


def draw_connector(draw, x, y, label, font, above=True):
    """Draw a connection point with label"""
    draw.ellipse((x-5, y-5, x+5, y+5), fill=LIGHT_GRAY, outline=BLACK, width=1)
    offset = -15 if above else 15
    draw.text((x, y + offset), label, fill=BLACK, font=font, anchor="mm")


def main():
    img = Image.new('RGB', (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)
    fonts = get_fonts()
    font_title, font_large, font_medium, font_small = fonts

    # Title
    draw.text((WIDTH//2, 35), "Surf E-Ink Frame - Hardware Wiring Diagram",
              fill=BLACK, font=font_title, anchor="mm")

    # =========== BATTERY ===========
    draw_box(draw, 80, 120, 160, 80, BATTERY_COLOR, "LiPo Battery", "3.7V 2000mAh", fonts)
    draw.text((160, 215), "JST PH2.0", fill=GRAY, font=font_small, anchor="mm")

    # =========== TP4056 ===========
    draw_box(draw, 80, 280, 160, 100, TP4056_COLOR, "TP4056 Charger", "USB-C + Protection", fonts)
    draw.text((160, 395), "PH2.0 socket", fill=GRAY, font=font_small, anchor="mm")

    # USB-C charging arrow
    draw.text((30, 310), "USB-C", fill=BLUE, font=font_small, anchor="rm")
    draw.text((30, 325), "charge", fill=GRAY, font=font_small, anchor="rm")
    draw.line([(35, 320), (80, 320)], fill=BLUE, width=2)
    draw.polygon([(80, 320), (70, 315), (70, 325)], fill=BLUE)

    # =========== SWITCH ===========
    draw_box(draw, 100, 450, 120, 50, SWITCH_COLOR, "KCD11 Switch", "", fonts)
    draw.text((160, 515), "ON/OFF", fill=GRAY, font=font_small, anchor="mm")

    # =========== ESP32 ===========
    esp_x, esp_y = 380, 300
    esp_w, esp_h = 220, 200
    draw_box(draw, esp_x, esp_y, esp_w, esp_h, ESP32_COLOR, "", "", fonts)
    draw.text((esp_x + esp_w//2, esp_y + 25), "ESP32 DevKitC 32U", fill=WHITE, font=font_medium, anchor="mm")
    draw.text((esp_x + esp_w//2, esp_y + 45), "WiFi + USB-C", fill=LIGHT_GRAY, font=font_small, anchor="mm")

    # ESP32 left pins
    esp_pins_left = [("5V", 340), ("3V3", 380), ("GND", 420)]
    for label, py in esp_pins_left:
        draw.ellipse((esp_x - 8, py - 5, esp_x + 2, py + 5), fill=LIGHT_GRAY, outline=WHITE)
        draw.text((esp_x - 15, py), label, fill=WHITE, font=font_small, anchor="rm")

    # ESP32 right pins
    esp_pins_right = [("GPIO23", 330), ("GPIO18", 360), ("GPIO5", 390),
                      ("GPIO17", 420), ("GPIO16", 450), ("GPIO4", 480)]
    for label, py in esp_pins_right:
        px = esp_x + esp_w
        draw.ellipse((px - 2, py - 5, px + 8, py + 5), fill=LIGHT_GRAY, outline=WHITE)
        draw.text((px + 15, py), label, fill=WHITE, font=font_small, anchor="lm")

    # =========== E-INK DISPLAY ===========
    eink_x, eink_y = 850, 80
    draw_box(draw, eink_x, eink_y, 300, 200, EINK_COLOR, "E-Ink Display", "", fonts)
    draw.text((eink_x + 150, eink_y + 60), "1.54\" (test)", fill=GRAY, font=font_medium, anchor="mm")
    draw.text((eink_x + 150, eink_y + 85), "or", fill=GRAY, font=font_small, anchor="mm")
    draw.text((eink_x + 150, eink_y + 110), "13.3\" Spectra 6 (prod)", fill=GRAY, font=font_medium, anchor="mm")
    draw.text((eink_x + 150, eink_y + 140), "6-color, SPI", fill=GRAY, font=font_small, anchor="mm")

    # E-Ink HAT
    hat_x, hat_y = 900, 320
    draw_box(draw, hat_x, hat_y, 200, 80, EINK_HAT_COLOR, "E-Ink HAT", "Driver Board", fonts)

    # Ribbon cable
    draw.rectangle((eink_x + 140, eink_y + 200, eink_x + 160, hat_y), fill=ORANGE, outline=DARK_GRAY)
    draw.text((eink_x + 180, eink_y + 220), "ribbon", fill=GRAY, font=font_small, anchor="lm")

    # HAT pins
    hat_h = 80
    hat_pins = [("VCC", 915), ("GND", 950), ("DIN", 985), ("CLK", 1020), ("CS", 1055)]
    for label, px in hat_pins:
        draw.ellipse((px - 5, hat_y + hat_h + 5, px + 5, hat_y + hat_h + 15), fill=GRAY, outline=BLACK)
        draw.text((px, hat_y + hat_h + 30), label, fill=BLACK, font=font_small, anchor="mm")
    hat_pins2 = [("DC", 930), ("RST", 980), ("BUSY", 1040)]
    for label, px in hat_pins2:
        draw.ellipse((px - 5, hat_y + hat_h + 45, px + 5, hat_y + hat_h + 55), fill=GRAY, outline=BLACK)
        draw.text((px, hat_y + hat_h + 70), label, fill=BLACK, font=font_small, anchor="mm")

    # =========== WIRING ===========

    # Battery to TP4056 (JST connector - thick)
    draw.line([(160, 200), (160, 280)], fill=DARK_GRAY, width=6)
    draw.text((180, 240), "JST", fill=GRAY, font=font_small, anchor="lm")

    # TP4056 OUT+ to Switch (red)
    draw_wire(draw, [(240, 310), (280, 310), (280, 475), (220, 475)], RED, 4)
    draw.text((285, 390), "OUT+", fill=RED, font=font_small, anchor="lm")

    # TP4056 OUT- to ESP32 GND (black)
    draw_wire(draw, [(240, 350), (320, 350), (320, 420), (380, 420)], BLACK, 4)
    draw.text((325, 385), "OUT-", fill=DARK_GRAY, font=font_small, anchor="lm")

    # Switch to ESP32 5V (red)
    draw_wire(draw, [(220, 475), (300, 475), (300, 340), (380, 340)], RED, 4)

    # ESP32 3V3 to E-Ink VCC (red)
    draw_wire(draw, [(380, 380), (350, 380), (350, 560), (915, 560), (915, 415)], RED, 3)

    # ESP32 GND to E-Ink GND (black)
    draw_wire(draw, [(380, 420), (340, 420), (340, 580), (950, 580), (950, 415)], BLACK, 3)

    # SPI Wires
    spi_connections = [
        (600, 330, 985, BLUE, "DIN"),      # GPIO23 -> DIN
        (600, 360, 1020, YELLOW, "CLK"),   # GPIO18 -> CLK
        (600, 390, 1055, ORANGE, "CS"),    # GPIO5 -> CS
        (600, 420, 930, GREEN, "DC"),      # GPIO17 -> DC
        (600, 450, 980, WHITE, "RST"),     # GPIO16 -> RST
        (600, 480, 1040, PURPLE, "BUSY"),  # GPIO4 -> BUSY
    ]

    y_offset = 600
    for esp_px, esp_py, hat_px, color, name in spi_connections:
        if name in ["DIN", "CLK", "CS"]:
            # Top row HAT pins
            draw_wire(draw, [(esp_px, esp_py), (700, esp_py), (700, y_offset), (hat_px, y_offset), (hat_px, 415)], color, 2)
        else:
            # Bottom row HAT pins
            draw_wire(draw, [(esp_px, esp_py), (720, esp_py), (720, y_offset + 40), (hat_px, y_offset + 40), (hat_px, 455)], color, 2)
        y_offset += 12

    # =========== RASPBERRY PI (separate) ===========
    draw.line([(50, 720), (1550, 720)], fill=LIGHT_GRAY, width=2)
    draw.text((WIDTH//2, 745), "SEPARATE SYSTEM - Wall Powered (not connected to battery)",
              fill=GRAY, font=font_medium, anchor="mm")

    pi_x, pi_y = 150, 800
    draw_box(draw, pi_x, pi_y, 250, 120, PI_COLOR, "Raspberry Pi", "Zero W v1.1", fonts)
    draw.text((pi_x + 125, pi_y + 90), "WiFi built-in", fill=GRAY, font=font_small, anchor="mm")

    # Pi power
    draw.text((pi_x - 10, pi_y + 40), "5V", fill=RED, font=font_small, anchor="rm")
    draw.text((pi_x - 10, pi_y + 55), "Micro USB", fill=GRAY, font=font_small, anchor="rm")
    draw.text((pi_x - 10, pi_y + 70), "(Android charger)", fill=GRAY, font=font_small, anchor="rm")
    draw.line([(pi_x - 5, pi_y + 50), (pi_x, pi_y + 50)], fill=RED, width=3)

    # WiFi arrow
    draw.line([(pi_x + 250, pi_y + 60), (pi_x + 400, pi_y + 60)], fill=BLUE, width=2)
    draw.polygon([(pi_x + 400, pi_y + 60), (pi_x + 385, pi_y + 52), (pi_x + 385, pi_y + 68)], fill=BLUE)
    draw.text((pi_x + 325, pi_y + 40), "WiFi (HTTP)", fill=BLUE, font=font_medium, anchor="mm")
    draw.text((pi_x + 450, pi_y + 60), "ESP32 fetches images", fill=GRAY, font=font_small, anchor="lm")

    # =========== LEGEND ===========
    legend_x = 1250
    legend_y = 750
    draw.text((legend_x, legend_y), "Wire Colors:", fill=BLACK, font=font_medium, anchor="lm")

    legend_items = [
        (RED, "Red = Power (+)"),
        (BLACK, "Black = Ground (-)"),
        (BLUE, "Blue = DIN (data)"),
        (YELLOW, "Yellow = CLK (clock)"),
        (ORANGE, "Orange = CS (select)"),
        (GREEN, "Green = DC (data/cmd)"),
        (WHITE, "White = RST (reset)"),
        (PURPLE, "Purple = BUSY"),
    ]

    for i, (color, label) in enumerate(legend_items):
        y = legend_y + 25 + i * 22
        draw.rectangle((legend_x, y - 6, legend_x + 25, y + 6), fill=color, outline=BLACK)
        draw.text((legend_x + 35, y), label, fill=BLACK, font=font_small, anchor="lm")

    # =========== NOTES ===========
    notes_y = 980
    draw.text((80, notes_y), "Notes:", fill=BLACK, font=font_medium, anchor="lm")
    notes = [
        "• Battery connects to TP4056 via JST PH2.0 connector (no soldering needed)",
        "• Switch goes between TP4056 OUT+ and ESP32 5V pin",
        "• E-Ink display powered from ESP32 3V3 pin (safe 3.3V)",
        "• All SPI wires are male-to-female Dupont cables (20cm)",
    ]
    for i, note in enumerate(notes):
        draw.text((80, notes_y + 20 + i * 18), note, fill=GRAY, font=font_small, anchor="lm")

    # Save
    output_path = os.path.join(os.path.dirname(__file__), "hardware_wiring.png")
    img.save(output_path, "PNG", quality=95)
    print(f"Saved: {output_path}")

    return img


if __name__ == "__main__":
    main()
