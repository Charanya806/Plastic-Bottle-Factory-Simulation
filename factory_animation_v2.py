import pygame
import sys
import random
import math
import os
import cv2
import numpy as np
import csv
import json
from datetime import datetime
pygame.init()
# ── Audio Mixer & Synthesizer ──────────────────────────────────────────────────
try:
    pygame.mixer.init(frequency=22050, size=-16, channels=1)
except Exception as e:
    print(f"Pygame mixer initialization failed: {e}")
# Keep cache of synthesized sounds
SOUNDS = {}
def get_sine_sound(frequency, duration, volume=0.08):
    try:
        sample_rate = 22050
        n_samples = int(sample_rate * duration)
        t = np.linspace(0, duration, n_samples, False)
        # Sine wave
        val = np.sin(2 * np.pi * frequency * t) * 32767 * volume
        # Fade out envelope to avoid clicks
        envelope = np.linspace(1.0, 0.0, n_samples)
        val = (val * envelope).astype(np.int16)
        return pygame.mixer.Sound(buffer=val)
    except Exception as e:
        print(f"Sound synthesis error: {e}")
        return None
def play_alert(event_type):
    if not pygame.mixer or not pygame.mixer.get_init():
        return
    try:
        if event_type == "defect":
            if "defect" not in SOUNDS:
                # C4, short low alert beep
                SOUNDS["defect"] = get_sine_sound(261.63, 0.20, volume=0.15)
            if SOUNDS["defect"]: SOUNDS["defect"].play()
            
        elif event_type == "warning":
            if "warning" not in SOUNDS:
                # Two quick alarm tones (A5, 880Hz)
                sample_rate = 22050
                duration = 0.4
                n_samples = int(sample_rate * duration)
                t = np.linspace(0, duration, n_samples, False)
                mask = np.zeros_like(t)
                mask[0:int(sample_rate * 0.15)] = 1.0
                mask[int(sample_rate * 0.22):int(sample_rate * 0.37)] = 1.0
                val = np.sin(2 * np.pi * 880.00 * t) * 32767 * 0.12 * mask
                SOUNDS["warning"] = pygame.mixer.Sound(buffer=val.astype(np.int16))
            if SOUNDS["warning"]: SOUNDS["warning"].play()
            
        elif event_type == "batch_complete":
            if "batch_complete" not in SOUNDS:
                # Three ascending chimes: E5 (659Hz), G5 (784Hz), C6 (1046Hz)
                sample_rate = 22050
                duration = 0.5
                n_samples = int(sample_rate * duration)
                t = np.linspace(0, duration, n_samples, False)
                val = np.zeros_like(t)
                s1 = int(sample_rate * 0.15)
                val[0:s1] = np.sin(2 * np.pi * 659.25 * t[0:s1]) * np.linspace(1.0, 0.2, s1)
                s2 = int(sample_rate * 0.30)
                val[s1:s2] = np.sin(2 * np.pi * 783.99 * t[s1:s2]) * np.linspace(1.0, 0.2, s2-s1)
                s3 = n_samples
                val[s2:s3] = np.sin(2 * np.pi * 1046.50 * t[s2:s3]) * np.linspace(1.0, 0.0, s3-s2)
                val = val * 32767 * 0.1
                SOUNDS["batch_complete"] = pygame.mixer.Sound(buffer=val.astype(np.int16))
            if SOUNDS["batch_complete"]: SOUNDS["batch_complete"].play()
            
        elif event_type == "resume":
            if "resume" not in SOUNDS:
                # Quick double chirp (B5, 987Hz)
                sample_rate = 22050
                duration = 0.25
                n_samples = int(sample_rate * duration)
                t = np.linspace(0, duration, n_samples, False)
                mask = np.zeros_like(t)
                mask[0:int(sample_rate * 0.08)] = 1.0
                mask[int(sample_rate * 0.12):int(sample_rate * 0.20)] = 1.0
                val = np.sin(2 * np.pi * 987.77 * t) * 32767 * 0.1 * mask
                SOUNDS["resume"] = pygame.mixer.Sound(buffer=val.astype(np.int16))
            if SOUNDS["resume"]: SOUNDS["resume"].play()
    except Exception as e:
        print(f"Error playing audio cue: {e}")
# ── Window ────────────────────────────────────────────────────────────────────
SCREEN_W, SCREEN_H = 1400, 820
SCREEN = pygame.display.set_mode((SCREEN_W, SCREEN_H), pygame.RESIZABLE)
pygame.display.set_caption("Plastic Bottle Factory - Vision Engineering Console")
CLOCK = pygame.time.Clock()
# ── Fonts ─────────────────────────────────────────────────────────────────────
def get_font(name, size, bold=False):
    try:
        return pygame.font.SysFont(name, size, bold=bold)
    except:
        return pygame.font.Font(None, size)
F_TITLE  = get_font("Segoe UI", 24, bold=True)
F_LABEL  = get_font("Segoe UI", 14, bold=True)
F_VALUE  = get_font("Segoe UI", 20, bold=True)
F_SMALL  = get_font("Segoe UI", 12)
F_HUGE   = get_font("Segoe UI", 34, bold=True)
# ── Palette ───────────────────────────────────────────────────────────────────
BG          = (8,  12,  20)    # Cyber Navy
PANEL_BG    = (15, 23,  40, 230) # Frosted Glass Overlay
PANEL_DARK  = (10, 15,  26)    # Dark Card Fill
BORDER      = (33, 47,  71)    # Structural Borders
ACCENT_BLUE = (0,  180, 255)   # Laser Cyan/Blue
ACCENT_GRN  = (16, 185, 129)   # Pass Green
ACCENT_RED  = (244, 63,  94)   # Defect Ruby Red
ACCENT_YLW  = (245, 158, 11)   # Alarm Yellow
ACCENT_PRP  = (168, 85,  247)  # Scan Purple
ACCENT_ORG  = (249, 115, 22)   # Shape/Speed Orange
TEXT_HI     = (243, 244, 246)  # High Contrast text
TEXT_MID    = (156, 163, 175)  # Medium grey
TEXT_DIM    = (100, 116, 139)  # Slate grey
CONVEYOR_C  = (20, 27,  38)    # Conveyor core
CONVEYOR_S  = (38, 48,  68)    # Conveyor belt moving slots
# ── Layout regions ────────────────────────────────────────────────────────────
def compute_layout(w, h):
    left_w   = 280
    right_w  = 280
    mid_w    = w - left_w - right_w
    conv_h   = 42
    conv_y   = h // 2 + 50
    conv_x   = left_w + 30
    conv_len = mid_w - 140 # Gap left for the physical sorting chutes/bins
    
    # CV Panel layout
    cv_x = left_w + 14
    cv_y = h - 310
    cv_w = mid_w - 148 # matches the conveyor end (680px width)
    cv_h = 210
    
    return dict(
        left_x=0, left_w=left_w,
        right_x=w - right_w, right_w=right_w,
        mid_x=left_w, mid_w=mid_w,
        conv_x=conv_x, conv_y=conv_y, conv_len=conv_len, conv_h=conv_h,
        cv_x=cv_x, cv_y=cv_y, cv_w=cv_w, cv_h=cv_h
    )
LO = compute_layout(SCREEN_W, SCREEN_H)
# ── Glassmorphic Beveled Card Helper ──────────────────────────────────────────
def rrect(surf, color, rect, r=10, border=0, border_color=None):
    rect_obj = pygame.Rect(rect)
    if len(color) == 4:
        # Translucent overlay
        temp_surf = pygame.Surface((rect_obj.width, rect_obj.height), pygame.SRCALPHA)
        pygame.draw.rect(temp_surf, color, (0, 0, rect_obj.width, rect_obj.height), border_radius=r)
        surf.blit(temp_surf, (rect_obj.x, rect_obj.y))
    else:
        pygame.draw.rect(surf, color, rect_obj, border_radius=r)
        
    if border and border_color:
        pygame.draw.rect(surf, border_color, rect_obj, int(border), border_radius=r)
def draw_beveled_card(surf, x, y, w, h, bg_color=PANEL_DARK, border_color=BORDER, bevel_color=(255, 255, 255, 12), r=10):
    # Drop shadow
    rrect(surf, (4, 6, 12, 160), (x + 1, y + 2, w, h), r=r)
    # Base background card
    rrect(surf, bg_color, (x, y, w, h), r=r, border=1.5, border_color=border_color)
    # Inner light reflection highlight (bevel)
    rrect(surf, (0, 0, 0, 0), (x + 1, y + 1, w - 2, h - 2), r=r-1, border=1, border_color=bevel_color)
def label(surf, text, x, y, font=F_LABEL, color=TEXT_MID):
    surf.blit(font.render(text, True, color), (x, y))
def hbar(surf, x, y, w, h, value, maxi, color, bg=(20, 27, 38)):
    rrect(surf, bg, (x, y, w, h), r=h//2)
    fill = int(w * max(0.0, min(value, maxi)) / maxi)
    if fill > 0:
        rrect(surf, color, (x, y, fill, h), r=h//2)
def draw_glow_dot(surf, x, y, color, r=6):
    if len(color) == 3:
        color = (*color, 255)
    glow = pygame.Surface((r*4, r*4), pygame.SRCALPHA)
    glow_alpha = color[3] // 3
    gc = (*color[:3], glow_alpha)
    pygame.draw.circle(glow, gc, (r*2, r*2), r*2)
    pygame.draw.circle(surf, color, (x, y), r)
    surf.blit(glow, (x - r*2, y - r*2), special_flags=pygame.BLEND_RGBA_ADD)
# ── Dynamic Mathematical Icons ────────────────────────────────────────────────
def draw_cog_icon(surf, cx, cy, r, angle, color):
    pygame.draw.circle(surf, color, (cx, cy), r - 3, 2)
    pygame.draw.circle(surf, color, (cx, cy), 2)
    for i in range(8):
        theta = angle + i * (2.0 * math.pi / 8.0)
        tx1 = cx + int((r - 3) * math.cos(theta))
        ty1 = cy + int((r - 3) * math.sin(theta))
        tx2 = cx + int((r + 2) * math.cos(theta))
        ty2 = cy + int((r + 2) * math.sin(theta))
        pygame.draw.line(surf, color, (tx1, ty1), (tx2, ty2), 2)
def draw_box_icon(surf, cx, cy, color):
    pygame.draw.rect(surf, color, (cx - 7, cy - 3, 14, 10), 2, border_radius=1)
    pygame.draw.line(surf, color, (cx - 7, cy - 3), (cx - 10, cy - 6), 2)
    pygame.draw.line(surf, color, (cx + 7, cy - 3), (cx + 10, cy - 6), 2)
    pygame.draw.line(surf, color, (cx - 10, cy - 6), (cx + 10, cy - 6), 2)
def draw_shield_icon(surf, cx, cy, color):
    points = [
        (cx, cy - 6),
        (cx + 6, cy - 4),
        (cx + 6, cy + 1),
        (cx, cy + 7),
        (cx - 6, cy + 1),
        (cx - 6, cy - 4),
    ]
    pygame.draw.polygon(surf, color, points, 2)
# ── Bins Accumulator ──────────────────────────────────────────────────────────
def draw_visual_bin(surf, bx, by, bw, bh, count, color):
    rrect(surf, (color[0]//5, color[1]//5, color[2]//5), (bx, by, bw, bh), r=4)
    cap_w, cap_h = 5, 10
    max_capsules = 16
    capsules_to_draw = min(max_capsules, count) if count < 40 else (count % max_capsules + 2)
    
    cols = 4
    for i in range(capsules_to_draw):
        col_idx = i % cols
        row_idx = i // cols
        cx = bx + 5 + col_idx * (cap_w + 3)
        cy = by + bh - 5 - (row_idx + 1) * (cap_h + 2)
        if cy > by + 2:
            rrect(surf, color, (cx, cy, cap_w, cap_h), r=1.5)
            
    front_color = (color[0]//2, color[1]//2, color[2]//2, 150)
    rrect(surf, front_color, (bx, by + bh // 3, bw, bh * 2 // 3), r=4, border=1, border_color=color)
# ── Live History Chart ────────────────────────────────────────────────────────
def draw_line_chart(surf, x, y, w, h, history, min_val, max_val, title, color):
    draw_beveled_card(surf, x, y, w, h)
    
    px, py = x + 10, y + 25
    pw, ph = w - 20, h - 35
    
    for i in range(4):
        gy = py + i * (ph // 3)
        pygame.draw.line(surf, (16, 24, 38), (px, gy), (px + pw, gy), 1)
    for i in range(5):
        gx = px + i * (pw // 4)
        pygame.draw.line(surf, (16, 24, 38), (gx, py), (gx, py + ph), 1)
        
    label(surf, title, x + 12, y + 8, font=F_SMALL, color=TEXT_DIM)
    
    if len(history) > 1:
        points = []
        for idx, val in enumerate(history):
            pt_x = px + (idx / (len(history) - 1)) * pw
            val_pct = (val - min_val) / (max_val - min_val) if max_val != min_val else 0.5
            val_pct = max(0.0, min(1.0, val_pct))
            pt_y = py + ph - val_pct * ph
            points.append((int(pt_x), int(pt_y)))
            
        pygame.draw.lines(surf, color, False, points, 2)
        
        area_surf = pygame.Surface((pw, ph), pygame.SRCALPHA)
        area_pts = [(px, py + ph)] + points + [(points[-1][0], py + ph)]
        local_pts = [(pt[0] - px, pt[1] - py) for pt in area_pts]
        pygame.draw.polygon(area_surf, (*color, 25), local_pts)
        surf.blit(area_surf, (px, py))
# ── Gauges ────────────────────────────────────────────────────────────────────
def draw_circular_gauge(surf, cx, cy, r, val, min_val, max_val, title, unit, color):
    card_rect = (cx - r - 12, cy - r - 25, r * 2 + 24, r * 2 + 55)
    draw_beveled_card(surf, card_rect[0], card_rect[1], card_rect[2], card_rect[3])
    
    val_pct = max(0.0, min(1.0, (val - min_val) / (max_val - min_val)))
    needle_deg = 225 - (val_pct * 270)
    needle_rad = math.radians(needle_deg)
    
    rect = pygame.Rect(cx - r, cy - r + 10, r * 2, r * 2)
    pygame.draw.arc(surf, (22, 33, 50), rect, math.radians(-45), math.radians(225), 6)
    
    if needle_deg < 225:
        pygame.draw.arc(surf, color, rect, math.radians(needle_deg), math.radians(225), 8)
        
    for deg in range(-45, 226, 30):
        rad = math.radians(deg)
        tx1 = cx + int((r - 2) * math.cos(rad))
        ty1 = (cy + 10) - int((r - 2) * math.sin(rad))
        tx2 = cx + int((r + 3) * math.cos(rad))
        ty2 = (cy + 10) - int((r + 3) * math.sin(rad))
        pygame.draw.line(surf, (33, 47, 71), (tx1, ty1), (tx2, ty2), 1)
        
    needle_len = r - 4
    nx = cx + int(needle_len * math.cos(needle_rad))
    ny = (cy + 10) - int(needle_len * math.sin(needle_rad))
    pygame.draw.line(surf, color, (cx, cy + 10), (nx, ny), 3)
    pygame.draw.circle(surf, TEXT_HI, (cx, cy + 10), 6)
    pygame.draw.circle(surf, PANEL_DARK, (cx, cy + 10), 3)
    
    title_txt = F_SMALL.render(title, True, TEXT_DIM)
    surf.blit(title_txt, (cx - title_txt.get_width() // 2, cy - r - 14))
    
    val_str = f"{val:.1f}" if isinstance(val, float) else f"{val}"
    val_txt = F_VALUE.render(f"{val_str}{unit}", True, TEXT_HI)
    surf.blit(val_txt, (cx - val_txt.get_width() // 2, cy + r - 8))
def draw_semi_circular_gauge(surf, cx, cy, r, val, title, unit, color):
    card_rect = (cx - r - 12, cy - r - 12, r * 2 + 24, r + 55)
    draw_beveled_card(surf, card_rect[0], card_rect[1], card_rect[2], card_rect[3])
    
    val_pct = max(0.0, min(1.0, val / 100.0))
    needle_deg = 180 - (val_pct * 180)
    needle_rad = math.radians(needle_deg)
    
    rect = pygame.Rect(cx - r, cy - r + 15, r * 2, r * 2)
    pygame.draw.arc(surf, (22, 33, 50), rect, math.radians(0), math.radians(180), 6)
    
    if needle_deg < 180:
        pygame.draw.arc(surf, color, rect, math.radians(needle_deg), math.radians(180), 8)
        
    for deg in range(0, 181, 30):
        rad = math.radians(deg)
        tx1 = cx + int((r - 2) * math.cos(rad))
        ty1 = (cy + 15) - int((r - 2) * math.sin(rad))
        tx2 = cx + int((r + 3) * math.cos(rad))
        ty2 = (cy + 15) - int((r + 3) * math.sin(rad))
        pygame.draw.line(surf, (33, 47, 71), (tx1, ty1), (tx2, ty2), 1)
        
    needle_len = r - 2
    nx = cx + int(needle_len * math.cos(needle_rad))
    ny = (cy + 15) - int(needle_len * math.sin(needle_rad))
    pygame.draw.line(surf, color, (cx, cy + 15), (nx, ny), 3)
    pygame.draw.circle(surf, TEXT_HI, (cx, cy + 15), 6)
    pygame.draw.circle(surf, PANEL_DARK, (cx, cy + 15), 3)
    
    title_txt = F_SMALL.render(title, True, TEXT_DIM)
    surf.blit(title_txt, (cx - title_txt.get_width() // 2, cy - r - 2))
    
    val_str = f"{val:.1f}" if isinstance(val, float) else f"{val}"
    val_txt = F_VALUE.render(f"{val_str}{unit}", True, TEXT_HI)
    surf.blit(val_txt, (cx - val_txt.get_width() // 2, cy + 18))
# ── Bottle Class ──────────────────────────────────────────────────────────────
class Bottle:
    def __init__(self, x, conv_y, bottle_id=0):
        self.conv_y = conv_y
        self.start_x = x
        self.y = conv_y
        self.bottle_id = bottle_id
        self.reset()
    def reset(self):
        self.x = self.start_x
        self.y = self.conv_y
        self.depth = random.uniform(0.90, 1.06)
        self.checked = False
        self.status = "IN_TRANSIT"
        self.defect_reason = ""
        self.body_color = ACCENT_BLUE
        self.metrics = self._gen()
    def _gen(self):
        return {
            "shape":  max(0.80, random.gauss(0.98, 0.04)),
            "crack":  0.0 if random.random() > 0.15 else random.uniform(0.02, 0.08),
            "scale":  random.gauss(1.0, 0.04),
            "color_off": random.gauss(0.0, 9.0),
            "label":  random.random() > 0.08,
        }
    def inspect(self):
        issues = []
        m = self.metrics
        if m["shape"] < 0.91:      issues.append("Shape distortion")
        if m["crack"] > 0.0:       issues.append("Crack detected")
        if abs(m["color_off"]) > 13: issues.append("Colour variance")
        if abs(m["scale"] - 1.0) > 0.05: issues.append("Size error")
        if not m["label"]:         issues.append("Label missing")
        return issues
    def update(self, running):
        if running:
            if self.status in ("IN_TRANSIT", "GOOD", "DEFECT"):
                self.x += SPEED * self.depth
                self.y = self.conv_y
            elif self.status == "SORTING_GOOD":
                self.x += SPEED * 1.6
                self.y += 2.8
            elif self.status == "SORTING_DEFECT":
                self.x += SPEED * 0.9
                self.y += 4.5
    def draw(self, surf):
        m = self.metrics
        bw = int(22 * m["scale"])
        bh = int(48 * m["scale"])
        bx = int(self.x)
        by = int(self.y) - bh + 4
        # Shadow
        if self.status in ("IN_TRANSIT", "GOOD", "DEFECT"):
            pygame.draw.ellipse(surf, (4, 6, 10), (bx + 2, by + bh - 4, bw, 6))
        # Translucent glass drawing surface
        bt_surf = pygame.Surface((bw + 10, bh + 15), pygame.SRCALPHA)
        
        base_color = self.body_color
        if abs(m["color_off"]) > 13:
            shifted = [max(0, min(255, c + int(m["color_off"] * 4))) for c in base_color]
            base_color = tuple(shifted)
        alpha = 190
        fill_color = (*base_color[:3], alpha)
        # Body skewing logic for warped shape defect
        body_rect = pygame.Rect(4, 12, bw, bh - 12)
        if m["shape"] < 0.91:
            points = [
                (4 + int(bw * 0.12), 12),
                (4 + int(bw * 0.88), 12),
                (4 + int(bw * 1.15), bh),
                (4 - int(bw * 0.15), bh)
            ]
            pygame.draw.polygon(bt_surf, fill_color, points)
        else:
            pygame.draw.rect(bt_surf, fill_color, body_rect, border_radius=6)
        # Wavy water animation inside bottle
        if self.status != "SORTING_DEFECT" and self.status != "DEFECT":
            liquid_col = (56, 189, 248, 200) # Shiny sky water
        else:
            liquid_col = (244, 63, 94, 200) # Contaminated ruby
            
        liquid_h = int((bh - 15) * 0.65)
        liquid_y = bh - liquid_h
        pygame.draw.rect(bt_surf, liquid_col, (6, liquid_y, bw - 4, liquid_h - 2), border_bottom_left_radius=4, border_bottom_right_radius=4)
        
        # Sine-wave micro sloshing
        wave_amp = 2
        wave_freq = 0.4
        t = pygame.time.get_ticks() * 0.008
        for wx in range(6, bw - 2):
            offset_y = math.sin((self.x + wx) * wave_freq + t) * wave_amp
            wy = liquid_y + offset_y
            pygame.draw.line(bt_surf, liquid_col, (wx, wy), (wx, liquid_y + 3), 1)
        # Neck
        nw = bw // 3
        nx = 4 + (bw - nw) // 2
        pygame.draw.rect(bt_surf, fill_color, (nx, 4, nw, 8))
        # Cap
        cap_col = (244, 63, 94) if (not m["label"] and m["crack"] > 0) else (59, 130, 246)
        pygame.draw.rect(bt_surf, cap_col, (nx - 1, 0, nw + 2, 5), border_radius=1)
        # Label stripe
        if m["label"]:
            label_y = 12 + int((bh - 12) * 0.28)
            pygame.draw.rect(bt_surf, (243, 244, 246, 230), (5, label_y, bw - 2, 13), border_radius=1)
            pygame.draw.line(bt_surf, (75, 85, 99), (8, label_y + 3), (bw - 2, label_y + 3), 1)
            pygame.draw.line(bt_surf, (75, 85, 99), (8, label_y + 7), (bw - 4, label_y + 7), 1)
        # Crack mark
        if m["crack"] > 0:
            cx = 4 + bw // 2
            cy = 12 + (bh - 12) // 2
            pygame.draw.line(bt_surf, (244, 63, 94), (cx - 4, cy - 5), (cx + 2, cy - 1), 2)
            pygame.draw.line(bt_surf, (244, 63, 94), (cx + 2, cy - 1), (cx - 2, cy + 5), 2)
        # High reflection glass highlights
        pygame.draw.line(bt_surf, (255, 255, 255, 95), (7, 14), (7, bh - 4), 2)
        # Draw the bottle onto screen
        surf.blit(bt_surf, (bx - 4, by - 12))
        # Glowing outline check rings and unique ID draw above
        if self.checked and self.status in ("GOOD", "DEFECT"):
            c = ACCENT_GRN if self.status == "GOOD" else ACCENT_RED
            pygame.draw.rect(surf, c, (bx - 3, by - 14, bw + 6, bh + 18), 2, border_radius=8)
            
            # Print tiny sequential ID on top of the bottle scanner outline
            id_txt = F_SMALL.render(f"#{self.bottle_id}", True, c)
            surf.blit(id_txt, (bx + bw // 2 - id_txt.get_width() // 2, by - 28))
# ── Simulated OpenCV Video Feed Generator ─────────────────────────────────────
def generate_cv_frame(bottle_obj):
    h, w = 120, 80
    frame = np.zeros((h, w, 3), dtype=np.uint8)
    frame[:] = (20, 27, 38) # Slate-grey background of scanner box
    
    m = bottle_obj.metrics
    scale = m["scale"]
    bw = int(22 * scale)
    bh = int(48 * scale)
    
    bx = (w - bw) // 2
    by = h - bh - 15
    
    base_color = list(bottle_obj.body_color)
    # Swap to standard BGR for OpenCV
    base_color = [base_color[2], base_color[1], base_color[0]]
    
    if abs(m["color_off"]) > 13:
        base_color = [max(0, min(255, c + int(m["color_off"] * 4))) for c in base_color]
        
    # Draw Silhouette
    if m["shape"] < 0.91:
        pts = np.array([
            [bx + int(bw * 0.12), by],
            [bx + int(bw * 0.88), by],
            [bx + int(bw * 1.15), by + bh],
            [bx - int(bw * 0.15), by + bh]
        ], np.int32)
        cv2.fillPoly(frame, [pts], base_color)
    else:
        cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), base_color, -1)
        
    # Draw Liquid level
    liquid_h = int((bh - 12) * 0.65)
    liquid_y = by + bh - liquid_h
    if bottle_obj.status in ("DEFECT", "SORTING_DEFECT") or (not bottle_obj.checked and bottle_obj.inspect()):
        liq_color = (64, 63, 244) # BGR ruby defective
    else:
        liq_color = (248, 189, 56) # BGR sky blue
        
    cv2.rectangle(frame, (bx + 2, liquid_y), (bx + bw - 2, by + bh - 2), liq_color, -1)
    
    # Neck
    nw = bw // 3
    nx = bx + (bw - nw) // 2
    cv2.rectangle(frame, (nx, by - 8), (nx + nw, by), base_color, -1)
    
    # Cap
    cap_color = (64, 63, 244) if (not m["label"] and m["crack"] > 0) else (246, 130, 59)
    cv2.rectangle(frame, (nx - 1, by - 12), (nx + nw + 1, by - 8), cap_color, -1)
    
    # Label stripe
    if m["label"]:
        label_y = by + int(bh * 0.28)
        cv2.rectangle(frame, (bx + 2, label_y), (bx + bw - 2, label_y + 12), (246, 244, 243), -1)
        
    # Crack mark
    if m["crack"] > 0:
        cx = bx + bw // 2
        cy = by + bh // 2
        cv2.line(frame, (cx - 4, cy - 4), (cx + 4, cy + 4), (0, 0, 255), 2)
        cv2.line(frame, (cx - 4, cy + 4), (cx + 4, cy - 4), (0, 0, 255), 2)
        
    return frame
def process_cv_inspection(frame):
    # 1. Grayscale conversion
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    # 2. Gaussian blur
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    # 3. Canny edge detection
    edges = cv2.Canny(blurred, 30, 100)
    # 4. Contour detection
    contours, _ = cv2.findContours(edges.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # 5. Overlays
    contour_overlay = frame.copy()
    if contours:
        cv2.drawContours(contour_overlay, contours, -1, (0, 255, 0), 1)
        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            if w > 5 and h > 5:
                cv2.rectangle(contour_overlay, (x, y), (x + w, y + h), (255, 0, 0), 1)
                
    return gray, edges, contour_overlay
def cv_to_pygame(cv_img):
    if len(cv_img.shape) == 2:
        cv_img = cv2.cvtColor(cv_img, cv2.COLOR_GRAY2RGB)
    else:
        cv_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
    
    h, w, c = cv_img.shape
    surf = pygame.image.frombuffer(cv_img.tobytes(), (w, h), 'RGB')
    return surf
# ── Conveyor and stage zones ──────────────────────────────────────────────────
def draw_conveyor(surf, lo, anim_tick, running):
    cx, cy, clen, ch = lo["conv_x"], lo["conv_y"], lo["conv_len"], lo["conv_h"]
    h = surf.get_height()
    
    # Structural stand legs
    for leg_x in (cx + 80, cx + clen - 120):
        pygame.draw.rect(surf, (33, 41, 54), (leg_x, cy + ch, 18, h - (cy + ch) - 100), border_radius=2)
        pygame.draw.rect(surf, (4, 6, 10), (leg_x + 2, cy + ch + 4, 14, h - (cy + ch) - 104), border_radius=2)
        pygame.draw.line(surf, (24, 32, 45), (leg_x, cy + ch + 15), (leg_x - 16, cy + ch), 3)
        pygame.draw.line(surf, (24, 32, 45), (leg_x + 18, cy + ch + 15), (leg_x + 34, cy + ch), 3)
        pygame.draw.rect(surf, (15, 23, 42), (leg_x - 6, h - 104, 30, 8), border_radius=2)
        
    # Ambient shadow behind track
    pygame.draw.rect(surf, (15, 23, 42), (cx - 15, cy - 6, clen + 30, ch + 12), border_radius=12)
    pygame.draw.rect(surf, BORDER, (cx - 15, cy - 6, clen + 30, ch + 12), 2, border_radius=12)
    
    # Roller pulleys
    pygame.draw.circle(surf, (71, 85, 105), (cx, cy + ch // 2), ch // 2 - 2)
    pygame.draw.circle(surf, (30, 41, 59), (cx, cy + ch // 2), ch // 2 - 2, 2)
    pygame.draw.circle(surf, (71, 85, 105), (cx + clen, cy + ch // 2), ch // 2 - 2)
    pygame.draw.circle(surf, (30, 41, 59), (cx + clen, cy + ch // 2), ch // 2 - 2, 2)
    
    rot_angle = (anim_tick * 0.08) if running else 0.0
    for rx in (cx, cx + clen):
        for i in range(3):
            theta = rot_angle + i * (2.0 * math.pi / 3.0)
            spoke_x = rx + int((ch // 2 - 5) * math.cos(theta))
            spoke_y = (cy + ch // 2) + int((ch // 2 - 5) * math.sin(theta))
            pygame.draw.line(surf, (203, 213, 225), (rx, cy + ch // 2), (spoke_x, spoke_y), 3)
            pygame.draw.circle(surf, (203, 213, 225), (rx, cy + ch // 2), 4)
    # Main belt track base
    pygame.draw.rect(surf, CONVEYOR_C, (cx, cy, clen, ch), border_radius=6)
    
    stripe_w = 12
    stripe_space = 32
    offset = int(anim_tick * SPEED) % stripe_space if running else 0
    for i in range(-stripe_space, clen + stripe_space, stripe_space):
        sx = cx + i + offset
        if sx < cx:
            continue
        if sx > cx + clen - stripe_w:
            draw_w = max(0, cx + clen - sx)
        else:
            draw_w = stripe_w
            
        if draw_w > 0:
            pygame.draw.polygon(surf, CONVEYOR_S, [
                (sx, cy + 4),
                (sx + draw_w, cy + 4),
                (sx + draw_w - 6, cy + ch - 4),
                (sx - 6, cy + ch - 4)
            ])
            
    pygame.draw.rect(surf, (148, 163, 184), (cx - 15, cy - 3, clen + 30, 4), border_radius=2)
    pygame.draw.rect(surf, (148, 163, 184), (cx - 15, cy + ch - 1, clen + 30, 4), border_radius=2)
def draw_stages(surf, lo, anim_tick, bottles, running):
    cx, cy, clen, ch = lo["conv_x"], lo["conv_y"], lo["conv_len"], lo["conv_h"]
    STAGES = [
        ("MOLDING",     ACCENT_GRN,  0.00, 0.25),
        ("COOLING",     ACCENT_BLUE, 0.25, 0.50),
        ("SHAPING",     ACCENT_ORG,  0.50, 0.75),
        ("INSPECTION",  ACCENT_PRP,  0.75, 1.00),
    ]
    
    for name, color, t0, t1 in STAGES:
        sx = cx + int(clen * t0) + 4
        sw = int(clen * (t1 - t0)) - 8
        sy = cy - 80
        sh = 50
        
        in_zone = False
        zone_start = cx + int(clen * t0)
        zone_end = cx + int(clen * t1)
        for b in bottles:
            if b.status in ("IN_TRANSIT", "GOOD", "DEFECT") and (zone_start <= b.x <= zone_end):
                in_zone = True
                break
                
        panel_bg = (*color, 45) if (in_zone and running) else (18, 25, 42, 190)
        border_col = color if (in_zone and running) else BORDER
        
        draw_beveled_card(surf, sx, sy, sw, sh, bg_color=panel_bg, border_color=border_col)
        
        text_col = TEXT_HI if (in_zone and running) else TEXT_MID
        label(surf, name, sx + sw//2 - F_LABEL.size(name)[0]//2, sy + 8, font=F_LABEL, color=text_col)
        
        pulse = int(120 + 75 * math.sin(pygame.time.get_ticks() * 0.005))
        c_glow = (*color, pulse) if (in_zone and running) else (*TEXT_DIM, 80)
        draw_glow_dot(surf, sx + 15, sy + 16, c_glow, r=4)
        
        if in_zone and running:
            if name == "MOLDING":
                heat = int(100 + 100 * math.sin(anim_tick * 0.25))
                overlay = pygame.Surface((sw, cy - (sy + sh)), pygame.SRCALPHA)
                pygame.draw.rect(overlay, (244, 63, 94, heat // 7), (0, 0, sw, cy - (sy + sh)))
                surf.blit(overlay, (sx, sy + sh))
            elif name == "COOLING":
                for i in range(3):
                    px = sx + (anim_tick * 2.5 + i * 28) % sw
                    py = sy + sh + (anim_tick + i * 18) % (cy - (sy + sh))
                    pygame.draw.circle(surf, (56, 189, 248, 140), (int(px), int(py)), 3)
            elif name == "SHAPING":
                press_y = (anim_tick % 24) * 1.3
                pygame.draw.line(surf, ACCENT_ORG, (sx + 10, sy + sh + press_y), (sx + sw - 10, sy + sh + press_y), 2)
            elif name == "INSPECTION":
                laser_y = sy + sh + (cy - (sy + sh)) // 2 + int(math.sin(anim_tick * 0.18) * ((cy - (sy + sh)) // 2.3))
                pygame.draw.line(surf, ACCENT_PRP, (sx, laser_y), (sx + sw, laser_y), 2)
                glow = pygame.Surface((sw, 6), pygame.SRCALPHA)
                pygame.draw.rect(glow, (168, 85, 247, 130), (0, 0, sw, 6))
                surf.blit(glow, (sx, laser_y - 3))
    ix = cx + int(clen * 0.82)
    pygame.draw.line(surf, ACCENT_PRP, (ix, cy-80), (ix, cy+ch+6), 2)
    label(surf, "▼ AI SCANNER", ix-28, cy-94, color=ACCENT_PRP)
def draw_sorting_station(surf, lo, deflector_angle):
    cx, cy, clen, ch = lo["conv_x"], lo["conv_y"], lo["conv_len"], lo["conv_h"]
    end_x = cx + clen
    
    pygame.draw.line(surf, (47, 55, 75), (end_x, cy + 10), (end_x + 55, cy + 55), 4)
    pygame.draw.line(surf, (47, 55, 75), (end_x, cy + ch - 10), (end_x + 45, cy + ch + 35), 4)
    pygame.draw.line(surf, (127, 45, 45), (end_x + 8, cy + ch), (end_x + 30, cy + ch + 65), 4)
    
    pivot_x = end_x + 5
    pivot_y = cy + 4
    arm_len = 36
    
    rad = math.radians(deflector_angle)
    arm_end_x = pivot_x + int(arm_len * math.sin(rad))
    arm_end_y = pivot_y + int(arm_len * math.cos(rad))
    
    pygame.draw.line(surf, ACCENT_ORG, (pivot_x, pivot_y), (arm_end_x, arm_end_y), 6)
    pygame.draw.circle(surf, (156, 163, 175), (pivot_x, pivot_y), 6)
# ── Left panel: metrics & touch controller ────────────────────────────────────
def draw_left(surf, lo, w, h, produced, good, defective, packaged, waste, efficiency, temp, state, alert, batch_num, anim_tick, mx, my):
    lx, lw = lo["left_x"], lo["left_w"]
    
    rrect(surf, PANEL_BG, (lx, 0, lw, h), r=0)
    pygame.draw.line(surf, BORDER, (lx+lw-1, 0), (lx+lw-1, h), 1)
    y = 16
    label(surf, "SYSTEM DASHBOARD", lx+18, y, color=ACCENT_BLUE)
    
    clock_str = datetime.now().strftime("%H:%M:%S")
    if (pygame.time.get_ticks() // 500) % 2 != 0:
        clock_str = clock_str.replace(":", " ")
        
    rrect(surf, PANEL_DARK, (lx + lw - 92, y - 4, 80, 24), r=4, border=1, border_color=BORDER)
    label(surf, clock_str, lx + lw - 82, y + 2, font=F_SMALL, color=ACCENT_GRN)
    
    y += 24
    pygame.draw.line(surf, BORDER, (lx+12, y), (lx+lw-12, y))
    y += 14
    def card(title, val_str, sub, accent, yy, size_h=80, has_icon=None):
        draw_beveled_card(surf, lx+12, yy, lw-24, size_h, border_color=accent)
        label(surf, title, lx+22, yy+10, font=F_SMALL, color=TEXT_DIM)
        surf.blit(F_VALUE.render(val_str, True, accent), (lx+22, yy+26))
        label(surf, sub, lx+22, yy+54, font=F_SMALL, color=TEXT_MID)
        
        if has_icon == "cog":
            draw_cog_icon(surf, lx + lw - 32, yy + 24, 8, anim_tick * 0.05, accent)
        elif has_icon == "box":
            draw_box_icon(surf, lx + lw - 32, yy + 24, accent)
        elif has_icon == "shield":
            draw_shield_icon(surf, lx + lw - 32, yy + 24, accent)
            
        return yy + size_h + 12
    y = card("PRODUCTION TOTALS", f"P: {produced}", f"Good: {good}  ·  Defect: {defective}", ACCENT_BLUE, y, has_icon="cog")
    
    batch_inspected = produced % 1000
    if produced > 0 and produced % 1000 == 0 and "STOP" in state:
        batch_inspected = 1000
        
    y = card(f"BATCH #{batch_num} PROGRESS", f"{batch_inspected} / 1000 btls", f"Next pause at {batch_num * 1000}", ACCENT_PRP, y, size_h=86, has_icon="box")
    hbar(surf, lx+22, y-26, lw-44, 6, batch_inspected, 1000, ACCENT_PRP)
    gauge_y = y + 55
    temp_col = ACCENT_RED if temp >= OVERHEAT_TEMP - 3 else ACCENT_YLW if temp >= 40 else ACCENT_GRN
    draw_circular_gauge(surf, lx + lw // 2, gauge_y, 45, temp, 20.0, 55.0, "THERMAL MONITOR", "°C", temp_col)
    y += 140
    state_col = ACCENT_RED if "STOP" in state or "PAUSE" in state or "OVERHEAT" in state else ACCENT_GRN
    draw_beveled_card(surf, lx+12, y, lw-24, 72, border_color=state_col)
    label(surf, "CONTROLLER STATUS", lx+22, y+8, font=F_SMALL, color=TEXT_DIM)
    surf.blit(F_LABEL.render(state, True, state_col), (lx+22, y+24))
    
    alert_txt = alert[:24] + "..." if len(alert) > 24 else alert
    label(surf, alert_txt, lx+22, y+46, font=F_SMALL, color=TEXT_MID)
    draw_shield_icon(surf, lx + lw - 32, y + 24, state_col)
    y += 84
    # Touch-screen responsive controller panel
    pygame.draw.line(surf, BORDER, (lx+12, y), (lx+lw-12, y))
    y += 10
    label(surf, "TOUCH CONTROLLER", lx+18, y, font=F_LABEL, color=ACCENT_BLUE)
    y += 20
    
    # 1. Start/Resume button
    btn_start_rect = pygame.Rect(lx + 12, y, lw - 24, 30)
    hover_start = btn_start_rect.collidepoint(mx, my)
    c_start = (20, 160, 90) if hover_start else (10, 120, 70)
    draw_beveled_card(surf, btn_start_rect.x, btn_start_rect.y, btn_start_rect.width, btn_start_rect.height, bg_color=c_start, border_color=ACCENT_GRN)
    lbl = F_LABEL.render("▶  START / RESUME BELT", True, TEXT_HI)
    surf.blit(lbl, (btn_start_rect.x + btn_start_rect.width // 2 - lbl.get_width() // 2, btn_start_rect.y + 6))
    y += 38
    
    # 2. Stop/Pause button
    btn_stop_rect = pygame.Rect(lx + 12, y, lw - 24, 30)
    hover_stop = btn_stop_rect.collidepoint(mx, my)
    c_stop = (180, 40, 60) if hover_stop else (130, 20, 40)
    draw_beveled_card(surf, btn_stop_rect.x, btn_stop_rect.y, btn_stop_rect.width, btn_stop_rect.height, bg_color=c_stop, border_color=ACCENT_RED)
    lbl = F_LABEL.render("❚❚  EMERGENCY STOP (PAUSE)", True, TEXT_HI)
    surf.blit(lbl, (btn_stop_rect.x + btn_stop_rect.width // 2 - lbl.get_width() // 2, btn_stop_rect.y + 6))
    y += 38
    
    # 3. Reset button
    btn_reset_rect = pygame.Rect(lx + 12, y, lw - 24, 30)
    hover_reset = btn_reset_rect.collidepoint(mx, my)
    c_reset = (180, 120, 20) if hover_reset else (130, 80, 10)
    draw_beveled_card(surf, btn_reset_rect.x, btn_reset_rect.y, btn_reset_rect.width, btn_reset_rect.height, bg_color=c_reset, border_color=ACCENT_YLW)
    lbl = F_LABEL.render("⟲  SYSTEM RESET SESSION", True, TEXT_HI)
    surf.blit(lbl, (btn_reset_rect.x + btn_reset_rect.width // 2 - lbl.get_width() // 2, btn_reset_rect.y + 6))
    y += 38
    
    # 4. Help Manual button
    btn_help_rect = pygame.Rect(lx + 12, y, lw - 24, 30)
    hover_help = btn_help_rect.collidepoint(mx, my)
    c_help = (51, 65, 85) if hover_help else PANEL_DARK
    draw_beveled_card(surf, btn_help_rect.x, btn_help_rect.y, btn_help_rect.width, btn_help_rect.height, bg_color=c_help, border_color=BORDER)
    lbl = F_LABEL.render("🛈  OPERATOR MANUAL", True, TEXT_HI)
    surf.blit(lbl, (btn_help_rect.x + btn_help_rect.width // 2 - lbl.get_width() // 2, btn_help_rect.y + 6))
    
    return btn_start_rect, btn_stop_rect, btn_reset_rect, btn_help_rect
# ── Right panel: vision analytics, containers & reports ───────────────────────
def draw_right(surf, lo, w, h, produced, defective, packaged, waste, efficiency, temp_history, mx, my):
    rx, rw = lo["right_x"], lo["right_w"]
    rrect(surf, PANEL_BG, (rx, 0, rw, h), r=0)
    pygame.draw.line(surf, BORDER, (rx, 0), (rx, h), 1)
    y = 16
    label(surf, "VISION ANALYTICS (AI)", rx+18, y, color=ACCENT_PRP)
    y += 24
    pygame.draw.line(surf, BORDER, (rx+10, y), (rx+rw-10, y))
    y += 14
    draw_line_chart(surf, rx + 12, y, rw - 24, 115, temp_history, 20.0, 55.0, "REAL-TIME TEMPERATURE PROFILE", ACCENT_ORG)
    y += 127
    label(surf, "OPERATIONAL YIELD", rx+18, y, color=ACCENT_PRP)
    y += 20
    
    draw_semi_circular_gauge(surf, rx + rw // 2, y + 42, 50, efficiency, "LINE YIELD", "%", ACCENT_GRN)
    y += 124
    defect_rate = (defective / produced * 100) if produced else 0.0
    dr_color = ACCENT_RED if defect_rate >= 12 else ACCENT_YLW if defect_rate > 5 else ACCENT_GRN
    
    draw_beveled_card(surf, rx+12, y, rw-24, 46, border_color=dr_color)
    label(surf, "Rolling Defect Rate", rx+22, y+6, font=F_SMALL, color=TEXT_DIM)
    surf.blit(F_VALUE.render(f"{defect_rate:.2f}%", True, dr_color), (rx+22, y+20))
    y += 58
    pygame.draw.line(surf, BORDER, (rx+12, y), (rx+rw-12, y))
    y += 10
    label(surf, "SORTING CONTAINERS", rx+18, y, color=ACCENT_BLUE)
    y += 22
    # Card 1: Packaged Cargo
    draw_beveled_card(surf, rx+12, y, rw-24, 76, border_color=ACCENT_GRN)
    label(surf, "PACKAGED CARGO", rx+22, y+8, font=F_LABEL, color=ACCENT_GRN)
    surf.blit(F_HUGE.render(str(packaged), True, ACCENT_GRN), (rx+22, y+24))
    draw_visual_bin(surf, rx + rw - 70, y + 13, 44, 50, packaged, ACCENT_GRN)
    y += 88
    # Card 2: Scrap Metal Bin
    draw_beveled_card(surf, rx+12, y, rw-24, 76, border_color=ACCENT_RED)
    label(surf, "SCRAP METAL BIN", rx+22, y+8, font=F_LABEL, color=ACCENT_RED)
    surf.blit(F_HUGE.render(str(waste), True, ACCENT_RED), (rx+22, y+24))
    draw_visual_bin(surf, rx + rw - 70, y + 13, 44, 50, waste, ACCENT_RED)
    y += 88
    # Open Reports Directory touch button
    btn_reports_rect = pygame.Rect(rx + 12, y, rw - 24, 32)
    hover_reports = btn_reports_rect.collidepoint(mx, my)
    c_reports = (120, 60, 180) if hover_reports else (80, 30, 130)
    draw_beveled_card(surf, btn_reports_rect.x, btn_reports_rect.y, btn_reports_rect.width, btn_reports_rect.height, bg_color=c_reports, border_color=ACCENT_PRP)
    lbl = F_LABEL.render("⎙  OPEN REPORTS ARCHIVE", True, TEXT_HI)
    surf.blit(lbl, (btn_reports_rect.x + btn_reports_rect.width // 2 - lbl.get_width() // 2, btn_reports_rect.y + 6))
    
    return btn_reports_rect
# ── Bottom Center Computer Vision Inspection Panel ────────────────────────────
def draw_cv_panel(surf, x, y, w, h, data):
    draw_beveled_card(surf, x, y, w, h, bg_color=PANEL_BG, border_color=ACCENT_PRP)
    
    label(surf, "AI COMPUTER VISION INSPECTION PIPELINE", x + 15, y + 10, font=F_LABEL, color=ACCENT_PRP)
    
    feed_y = y + 35
    frame_w, frame_h = 80, 120
    
    # 1. BGR camera feed
    rrect(surf, PANEL_DARK, (x + 15, feed_y, frame_w, frame_h), r=6, border=1, border_color=BORDER)
    if data["frame"]:
        surf.blit(data["frame"], (x + 15, feed_y))
    label(surf, "BGR FEED", x + 20, feed_y + frame_h + 4, font=F_SMALL, color=TEXT_DIM)
    
    # 2. Canny edges feed
    rrect(surf, PANEL_DARK, (x + 110, feed_y, frame_w, frame_h), r=6, border=1, border_color=BORDER)
    if data["edges"]:
        surf.blit(data["edges"], (x + 110, feed_y))
    label(surf, "CANNY EDGES", x + 112, feed_y + frame_h + 4, font=F_SMALL, color=TEXT_DIM)
    
    # 3. Contour outline overlay
    rrect(surf, PANEL_DARK, (x + 205, feed_y, frame_w, frame_h), r=6, border=1, border_color=BORDER)
    if data["overlay"]:
        surf.blit(data["overlay"], (x + 205, feed_y))
    label(surf, "CONTOURS", x + 215, feed_y + frame_h + 4, font=F_SMALL, color=TEXT_DIM)
    
    # 4. Feature checks bars
    bar_x = x + 305
    bar_w = 200
    
    metrics = [
        ("Shape Consistency", data["shape_score"], ACCENT_BLUE),
        ("Size/Scale Match", data["size_score"], ACCENT_ORG),
        ("Surface Crack Inspect", data["surface_score"], ACCENT_PRP),
        ("Color Alignment", data["color_score"], ACCENT_YLW),
        ("Label Verification", data["label_score"], ACCENT_GRN)
    ]
    
    for idx, (m_name, m_val, m_col) in enumerate(metrics):
        by = y + 32 + idx * 30
        label(surf, m_name, bar_x, by, font=F_SMALL, color=TEXT_MID)
        score_str = f"{m_val}%"
        label(surf, score_str, bar_x + bar_w - 30, by, font=F_SMALL, color=m_col)
        hbar(surf, bar_x, by + 16, bar_w, 6, m_val, 100, m_col)
        
    # 5. Holographic decision board
    box_x = x + 530
    box_w = w - 545
    box_h = 145
    
    status = data["overall"]
    if status == "GOOD" or status == "SORTING_GOOD":
        card_col = ACCENT_GRN
        card_bg = (16, 185, 129, 30)
        lbl_text = "PASS"
        sub_text = "OK - SPEC COMPLIANT"
    elif status == "DEFECT" or status == "SORTING_DEFECT":
        card_col = ACCENT_RED
        card_bg = (244, 63, 94, 30)
        lbl_text = "FAIL"
        sub_text = data["reason"].upper()
    else:
        card_col = TEXT_DIM
        card_bg = (100, 116, 139, 15)
        lbl_text = "STANDBY"
        sub_text = "AWAITING BOTTLE"
        
    draw_beveled_card(surf, box_x, feed_y, box_w, box_h, bg_color=card_bg, border_color=card_col, r=8)
    
    lbl_s = F_HUGE.render(lbl_text, True, card_col)
    surf.blit(lbl_s, (box_x + box_w // 2 - lbl_s.get_width() // 2, feed_y + 20))
    
    sub_text_wrapped = sub_text
    if len(sub_text_wrapped) > 18:
        sub_text_wrapped = sub_text_wrapped[:16] + "..."
    lbl_sub = F_SMALL.render(sub_text_wrapped, True, TEXT_HI)
    surf.blit(lbl_sub, (box_x + box_w // 2 - lbl_sub.get_width() // 2, feed_y + 70))
    
    if data["bottle_id"] > 0:
        id_lbl = f"ID: #{data['bottle_id']}"
        lbl_id = F_SMALL.render(id_lbl, True, TEXT_MID)
        surf.blit(lbl_id, (box_x + box_w // 2 - lbl_id.get_width() // 2, feed_y + 105))
# ── Header ────────────────────────────────────────────────────────────────────
def draw_header(surf, w, h, state, batch_num):
    rrect(surf, PANEL_DARK, (0, 0, w, 54), r=0)
    pygame.draw.line(surf, BORDER, (0, 54), (w, 54), 1)
    
    title = "◈  PLASTIC BOTTLE FACTORY DIGITAL TWIN"
    surf.blit(F_TITLE.render(title, True, TEXT_HI), (w//2 - F_TITLE.size(title)[0]//2, 14))
    
    dot_col = ACCENT_RED if "STOP" in state or "OVERHEAT" in state or "PAUSE" in state else ACCENT_GRN
    pulse_alpha = int(120 + 85 * math.sin(pygame.time.get_ticks() * 0.005))
    draw_glow_dot(surf, w - 40, 27, (*dot_col, pulse_alpha), r=7)
    
    status_lbl = f"{state} (BATCH #{batch_num})"
    surf.blit(F_LABEL.render(status_lbl, True, dot_col), (w - 55 - F_LABEL.size(status_lbl)[0], 19))
    label(surf, "ECOPLAST AUTOMATION", 20, 20, font=F_LABEL, color=ACCENT_BLUE)
# ── Inspection feedback strip ─────────────────────────────────────────────────
def draw_feedback(surf, lo, w, h, last_reason, machine_state):
    lw = lo["left_w"]
    rw = lo["right_w"]
    fx = lw + 14
    fw = w - lw - rw - 28
    fy = h - 90
    fh = 78
    draw_beveled_card(surf, fx, fy, fw, fh, bg_color=(15, 23, 40, 230))
    label(surf, "AI VISION SCAN INSPECTION FEEDBACK", fx+18, fy+10, font=F_SMALL, color=ACCENT_PRP)
    if last_reason in ("OK", "NO INSPECTION YET") or "PASS: OK" in last_reason:
        col = ACCENT_GRN if "PASS" in last_reason or last_reason == "OK" else TEXT_MID
        draw_glow_dot(surf, fx + 18, fy + 38, col, r=5)
    else:
        col = ACCENT_RED
        draw_glow_dot(surf, fx + 18, fy + 38, col, r=5)
        
    surf.blit(F_VALUE.render(last_reason, True, col), (fx + 34, fy + 26))
    rules = "Batch cycle limit: 1000 bottles  ·  Defect Scram Lockout: 12 count / 12% rate  ·  Continuous production active"
    label(surf, rules, fx+18, fy+54, font=F_SMALL, color=TEXT_DIM)
# ── Batch Report Exporter ─────────────────────────────────────────────────────
def save_batch_reports(batch_num, good, defective, defect_breakdown, avg_temp, max_temp, duration_s, speed, rating_str, start_id, end_id):
    project_dir = os.path.dirname(os.path.abspath(__file__))
    reports_dir = os.path.join(project_dir, "reports")
    batch_dir = os.path.join(reports_dir, f"batch_{batch_num:04d}")
    os.makedirs(batch_dir, exist_ok=True)
    
    efficiency = (good / 10.0)
    defect_rate = (defective / 10.0)
    
    mins = int(duration_s // 60)
    secs = int(duration_s % 60)
    duration_formatted = f"{mins:02d}:{secs:02d}"
    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 1. JSON Report
    json_path = os.path.join(batch_dir, "batch_report.json")
    json_data = {
        "batch_number": batch_num,
        "timestamp": timestamp_str,
        "starting_bottle_id": start_id,
        "ending_bottle_id": end_id,
        "total_bottles": 1000,
        "good_bottles": good,
        "defective_bottles": defective,
        "quality_rate_percent": efficiency,
        "defect_rate_percent": defect_rate,
        "efficiency_percent": efficiency,
        "rating": rating_str,
        "average_temperature_c": round(avg_temp, 2),
        "maximum_temperature_c": round(max_temp, 2),
        "conveyor_speed_mps": speed,
        "duration_seconds": round(duration_s, 2),
        "duration_formatted": duration_formatted,
        "defect_breakdown": defect_breakdown
    }
    
    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=4)
    except Exception as e:
        print(f"Error saving JSON report: {e}")
        
    # 2. CSV Report
    csv_path = os.path.join(batch_dir, "batch_report.csv")
    try:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Parameter", "Value"])
            writer.writerow(["Batch Number", batch_num])
            writer.writerow(["Timestamp", timestamp_str])
            writer.writerow(["Starting Bottle ID", start_id])
            writer.writerow(["Ending Bottle ID", end_id])
            writer.writerow(["Total Bottles", 1000])
            writer.writerow(["Good Bottles", good])
            writer.writerow(["Defective Bottles", defective])
            writer.writerow(["Quality Rate (%)", f"{efficiency:.2f}%"])
            writer.writerow(["Defect Rate (%)", f"{defect_rate:.2f}%"])
            writer.writerow(["Efficiency (%)", f"{efficiency:.2f}%"])
            writer.writerow(["Rating", rating_str])
            writer.writerow(["Average Temp (°C)", f"{avg_temp:.2f}"])
            writer.writerow(["Maximum Temp (°C)", f"{max_temp:.2f}"])
            writer.writerow(["Conveyor Speed (m/s)", speed])
            writer.writerow(["Duration (s)", f"{duration_s:.2f}"])
            writer.writerow(["Duration Formatted", duration_formatted])
            writer.writerow([])
            writer.writerow(["Defect Type", "Count"])
            for defect_type, count in defect_breakdown.items():
                writer.writerow([defect_type, count])
    except Exception as e:
        print(f"Error saving CSV report: {e}")
        
    # 3. Master Production History CSV
    master_csv_path = os.path.join(reports_dir, "production_history.csv")
    file_exists = os.path.exists(master_csv_path)
    try:
        with open(master_csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow([
                    "Batch Number", "Timestamp", "Starting ID", "Ending ID",
                    "Total Bottles", "Good Bottles", "Defective Bottles",
                    "Quality Rate (%)", "Defect Rate (%)", "Efficiency (%)",
                    "Avg Temp (°C)", "Max Temp (°C)", "Duration (s)"
                ])
            writer.writerow([
                batch_num, timestamp_str, start_id, end_id,
                1000, good, defective,
                f"{efficiency:.2f}", f"{defect_rate:.2f}", f"{efficiency:.2f}",
                f"{avg_temp:.2f}", f"{max_temp:.2f}", f"{duration_s:.2f}"
            ])
        return True
    except Exception as e:
        print(f"Error updating production history: {e}")
        return False
# ── Batch Report Popup Modal ──────────────────────────────────────────────────
def draw_report_popup(surf, w, h, batch_num, good, defective, defect_breakdown, avg_temp, max_temp, duration_s, speed, rating_str, countdown_s, show_saved_msg, saved_ok):
    overlay = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(overlay, (6, 9, 15, 210), (0, 0, w, h))
    surf.blit(overlay, (0, 0))
    
    pw, ph = 680, 520
    px = (w - pw) // 2
    py = (h - ph) // 2
    
    rrect(surf, (4, 5, 8, 220), (px + 6, py + 6, pw, ph), r=16)
    draw_beveled_card(surf, px, py, pw, ph, bg_color=(20, 29, 46, 255), border_color=ACCENT_BLUE, r=16)
    
    title = "BATCH PRODUCTION REPORT"
    surf.blit(F_TITLE.render(title, True, TEXT_HI), (px + pw // 2 - F_TITLE.size(title)[0] // 2, py + 20))
    
    sub = f"Batch #{batch_num}  ·  EcoPlast Automation Twin  ·  Status: SUCCESS"
    surf.blit(F_LABEL.render(sub, True, TEXT_MID), (px + pw // 2 - F_LABEL.size(sub)[0] // 2, py + 48))
    
    pygame.draw.line(surf, BORDER, (px + 30, py + 72), (px + pw - 30, py + 72), 1)
    
    # Left Column: Yield summaries and KPIs
    c1_x, c1_y, c1_w, c1_h = px + 30, py + 85, 290, 115
    draw_beveled_card(surf, c1_x, c1_y, c1_w, c1_h)
    label(surf, "BATCH YIELD SUMMARY", c1_x + 14, c1_y + 12, font=F_SMALL, color=TEXT_DIM)
    label(surf, "Total Processed: 1000", c1_x + 14, c1_y + 32, font=F_LABEL, color=TEXT_HI)
    
    draw_glow_dot(surf, c1_x + 20, c1_y + 64, ACCENT_GRN, r=4)
    label(surf, f"Good Bottles: {good}", c1_x + 32, c1_y + 56, font=F_LABEL, color=ACCENT_GRN)
    
    draw_glow_dot(surf, c1_x + 20, c1_y + 88, ACCENT_RED, r=4)
    label(surf, f"Defects: {defective}", c1_x + 32, c1_y + 80, font=F_LABEL, color=ACCENT_RED)
    
    c2_x, c2_y, c2_w, c2_h = px + 30, py + 215, 290, 140
    draw_beveled_card(surf, c2_x, c2_y, c2_w, c2_h)
    label(surf, "OPERATIONAL KPIs", c2_x + 14, c2_y + 10, font=F_SMALL, color=TEXT_DIM)
    label(surf, f"Average Temp: {avg_temp:.1f} °C", c2_x + 14, c2_y + 28, font=F_SMALL, color=TEXT_HI)
    label(surf, f"Maximum Temp: {max_temp:.1f} °C", c2_x + 14, c2_y + 50, font=F_SMALL, color=ACCENT_RED if max_temp >= OVERHEAT_TEMP - 3 else ACCENT_YLW)
    
    mins = int(duration_s // 60)
    secs = int(duration_s % 60)
    label(surf, f"Cycle Duration: {mins:02d}:{secs:02d}", c2_x + 14, c2_y + 72, font=F_SMALL, color=TEXT_HI)
    label(surf, f"Conveyor Speed: {speed:.1f} m/s", c2_x + 14, c2_y + 94, font=F_SMALL, color=ACCENT_BLUE)
    
    hbar(surf, c2_x + 14, c2_y + 118, 262, 6, avg_temp, 55, ACCENT_RED if avg_temp >= 40 else ACCENT_GRN)
    
    # Right Column: Visual Defect Breakdown
    c3_x, c3_y, c3_w, c3_h = px + 340, py + 85, 310, 270
    draw_beveled_card(surf, c3_x, c3_y, c3_w, c3_h, border_color=ACCENT_PRP)
    label(surf, "VISION DEFECT ANALYSIS", c3_x + 14, c3_y + 12, font=F_SMALL, color=ACCENT_PRP)
    
    defects_list = [
        ("Shape Distortion", defect_breakdown.get("Shape distortion", 0), ACCENT_RED),
        ("Size Deviation", defect_breakdown.get("Size error", 0), ACCENT_ORG),
        ("Surface/Crack", defect_breakdown.get("Crack detected", 0), ACCENT_YLW),
        ("Color Alignment", defect_breakdown.get("Colour variance", 0), ACCENT_BLUE),
        ("Label Missing", defect_breakdown.get("Label missing", 0), ACCENT_PRP)
    ]
    
    max_d_count = max([d[1] for d in defects_list] + [1])
    
    for idx, (d_name, d_count, d_col) in enumerate(defects_list):
        dy = c3_y + 40 + idx * 44
        label(surf, d_name, c3_x + 14, dy, font=F_SMALL, color=TEXT_HI)
        label(surf, str(d_count), c3_x + c3_w - 40, dy, font=F_LABEL, color=d_col)
        hbar(surf, c3_x + 14, dy + 20, c3_w - 28, 6, d_count, max_d_count, d_col)
        
    # Status Save Confirmation strip
    c4_x, c4_y, c4_w, c4_h = px + 30, py + 370, 620, 50
    draw_beveled_card(surf, c4_x, c4_y, c4_w, c4_h)
    
    if show_saved_msg:
        save_msg = "✓ BATCH REPORT SUCCESSFULLY ARCHIVED IN CSV & JSON" if saved_ok else "✗ ERROR ARCHIVING REPORTS. WRITE PERMISSION DENIED."
        save_col = ACCENT_GRN if saved_ok else ACCENT_RED
        draw_glow_dot(surf, c4_x + 22, c4_y + 25, save_col, r=5)
        label(surf, save_msg, c4_x + 38, c4_y + 16, font=F_LABEL, color=save_col)
    else:
        eff_pct = (good / 10.0)
        draw_glow_dot(surf, c4_x + 22, c4_y + 25, ACCENT_GRN, r=5)
        label(surf, f"Efficiency: {eff_pct:.1f}% Yield Rating  ·  {rating_str}", c4_x + 38, c4_y + 16, font=F_LABEL, color=TEXT_HI)
        
    # Interactive Buttons
    mx, my = pygame.mouse.get_pos()
    
    btn_continue = pygame.Rect(px + 30, py + ph - 75, 190, 42)
    c_hover = btn_continue.collidepoint(mx, my)
    c_col = (40, 220, 120) if c_hover else ACCENT_GRN
    draw_beveled_card(surf, btn_continue.x, btn_continue.y, btn_continue.width, btn_continue.height, bg_color=c_col, border_color=TEXT_HI if c_hover else BORDER)
    btn_str = f"Resume ({countdown_s}s)" if countdown_s > 0 else "Resume Production"
    lbl = F_LABEL.render(btn_str, True, BG)
    surf.blit(lbl, (btn_continue.x + btn_continue.width // 2 - lbl.get_width() // 2, btn_continue.y + 12))
    
    btn_save = pygame.Rect(px + 235, py + ph - 75, 190, 42)
    s_hover = btn_save.collidepoint(mx, my)
    s_col = (56, 189, 248) if s_hover else ACCENT_BLUE
    draw_beveled_card(surf, btn_save.x, btn_save.y, btn_save.width, btn_save.height, bg_color=s_col, border_color=TEXT_HI if s_hover else BORDER)
    lbl = F_LABEL.render("Save Report Files", True, BG)
    surf.blit(lbl, (btn_save.x + btn_save.width // 2 - lbl.get_width() // 2, btn_save.y + 12))
    
    btn_dismiss = pygame.Rect(px + 440, py + ph - 75, 210, 42)
    d_hover = btn_dismiss.collidepoint(mx, my)
    d_col = (51, 65, 85) if d_hover else PANEL_DARK
    draw_beveled_card(surf, btn_dismiss.x, btn_dismiss.y, btn_dismiss.width, btn_dismiss.height, bg_color=d_col, border_color=BORDER)
    lbl = F_LABEL.render("Close (Standby)", True, TEXT_HI)
    surf.blit(lbl, (btn_dismiss.x + btn_dismiss.width // 2 - lbl.get_width() // 2, btn_dismiss.y + 12))
    
    return btn_continue, btn_save, btn_dismiss
# ── Help / Project Manual Overlay ─────────────────────────────────────────────
def draw_help_overlay(surf, w, h):
    overlay = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(overlay, (6, 9, 15, 210), (0, 0, w, h))
    surf.blit(overlay, (0, 0))
    
    pw, ph = 740, 560
    px = (w - pw) // 2
    py = (h - ph) // 2
    
    rrect(surf, (4, 5, 8, 220), (px + 6, py + 6, pw, ph), r=16)
    draw_beveled_card(surf, px, py, pw, ph, bg_color=(15, 23, 40, 255), border_color=ACCENT_BLUE, r=16)
    
    title = "PROJECT OVERVIEW & OPERATOR GUIDE"
    surf.blit(F_TITLE.render(title, True, TEXT_HI), (px + pw // 2 - F_TITLE.size(title)[0] // 2, py + 22))
    sub = "EcoPlast Automation Twin Console  ·  Interactive Operator Help"
    surf.blit(F_LABEL.render(sub, True, TEXT_MID), (px + pw // 2 - F_LABEL.size(sub)[0] // 2, py + 52))
    
    pygame.draw.line(surf, BORDER, (px + 30, py + 78), (px + pw - 30, py + 78), 1)
    
    col1_x = px + 30
    col1_w = 320
    
    # Left Column: Production Stages
    draw_beveled_card(surf, col1_x, py + 95, col1_w, 195)
    label(surf, "MANUFACTURING PRODUCTION LINE", col1_x + 14, py + 107, font=F_LABEL, color=ACCENT_BLUE)
    
    pipeline_steps = [
        ("MOLDING", "Pre-form heating and raw bottle blow molding"),
        ("COOLING", "Liquid nitrogen spray stabilization"),
        ("SHAPING", "Pressurized contour stabilization"),
        ("INSPECTION", "Active AI vision inspection check"),
        ("SORTING", "Automatic pneumatic deflector routing")
    ]
    for idx, (step_name, step_desc) in enumerate(pipeline_steps):
        sy = py + 132 + idx * 30
        draw_glow_dot(surf, col1_x + 20, sy + 6, ACCENT_BLUE, r=3)
        label(surf, step_name, col1_x + 32, sy, font=F_SMALL, color=TEXT_HI)
        label(surf, step_desc[:36] + "...", col1_x + 115, sy, font=F_SMALL, color=TEXT_MID)
        
    # Left Column: CV Processing steps
    draw_beveled_card(surf, col1_x, py + 305, col1_w, 170)
    label(surf, "AI COMPUTER VISION PIPELINE", col1_x + 14, py + 317, font=F_LABEL, color=ACCENT_PRP)
    
    cv_steps = [
        ("BGR FRAME", "Simulated raw BGR camera image capture"),
        ("GRAYSCALE", "Luminance conversion (cv2.cvtColor)"),
        ("GAUSSIAN BLUR", "Kernel noise smoothing (cv2.GaussianBlur)"),
        ("CANNY EDGES", "Gradient edge extraction (cv2.Canny)"),
        ("CONTOURS", "Geometry extraction (cv2.findContours)")
    ]
    for idx, (cv_name, cv_desc) in enumerate(cv_steps):
        cy = py + 342 + idx * 24
        draw_glow_dot(surf, col1_x + 20, cy + 6, ACCENT_PRP, r=3)
        label(surf, cv_name, col1_x + 32, cy, font=F_SMALL, color=TEXT_HI)
        label(surf, cv_desc, col1_x + 130, cy, font=F_SMALL, color=TEXT_MID)
        
    # Right Column: Quality checks and controls
    col2_x = px + 380
    col2_w = 330
    
    draw_beveled_card(surf, col2_x, py + 95, col2_w, 195)
    label(surf, "VISION QUALITY CRITERIA", col2_x + 14, py + 107, font=F_LABEL, color=ACCENT_ORG)
    
    defects_desc = [
        ("Shape Distortion", "Body aspect ratio / skewed silhouette"),
        ("Size Deviation", "Bottle height/width scale validation"),
        ("Crack / Surface", "Local fracture or surface fracture detection"),
        ("Color Alignment", "RGB pigment concentration alignment"),
        ("Label Missing", "EcoPlast branding sticker verification")
    ]
    for idx, (def_name, def_desc) in enumerate(defects_desc):
        dy = py + 132 + idx * 30
        draw_glow_dot(surf, col2_x + 20, dy + 6, ACCENT_ORG, r=3)
        label(surf, def_name, col2_x + 32, dy, font=F_SMALL, color=TEXT_HI)
        label(surf, def_desc, col2_x + 140, dy, font=F_SMALL, color=TEXT_MID)
        
    draw_beveled_card(surf, col2_x, py + 305, col2_w, 170)
    label(surf, "OPERATOR CONTROL CHANNELS", col2_x + 14, py + 317, font=F_LABEL, color=ACCENT_YLW)
    
    controls = [
        ("[SPACE BAR]", "Toggle Play / Resume Conveyor Belt"),
        ("[S KEY]", "Emergency stop and lock belt motion"),
        ("[R KEY]", "Full system session counters reset"),
        ("[H / ? KEY]", "Toggle this help manual modal overlay"),
        ("[TOUCH UI]", "Click left card buttons for touch control")
    ]
    for idx, (ctrl_key, ctrl_desc) in enumerate(controls):
        cy = py + 342 + idx * 24
        label(surf, ctrl_key, col2_x + 20, cy, font=F_SMALL, color=ACCENT_YLW)
        label(surf, ctrl_desc, col2_x + 115, cy, font=F_SMALL, color=TEXT_MID)
        
    # Close Manual Button
    mx, my = pygame.mouse.get_pos()
    btn_close = pygame.Rect(px + pw // 2 - 100, py + ph - 62, 200, 42)
    c_hover = btn_close.collidepoint(mx, my)
    btn_bg = (51, 65, 85) if c_hover else PANEL_DARK
    draw_beveled_card(surf, btn_close.x, btn_close.y, btn_close.width, btn_close.height, bg_color=btn_bg, border_color=BORDER, r=8)
    lbl = F_LABEL.render("Close Operator Manual", True, TEXT_HI)
    surf.blit(lbl, (btn_close.x + btn_close.width // 2 - lbl.get_width() // 2, btn_close.y + 12))
    
    return btn_close
# ── Main loop ─────────────────────────────────────────────────────────────────
def run():
    global SCREEN, SCREEN_W, SCREEN_H, LO
    # Lifetime Counters
    lifetime_produced = 0
    lifetime_good = 0
    lifetime_defective = 0
    lifetime_packaged = 0
    lifetime_waste = 0
    # Batch Statistics
    batch_number = 1
    batch_spawned_count = 0
    batch_completed_count = 0
    batch_good = 0
    batch_defective = 0
    batch_packaged = 0
    batch_waste = 0
    batch_temp_sum = 0.0
    batch_temp_count = 0
    batch_temp_max = 0.0
    batch_start_time = pygame.time.get_ticks()
    batch_defects = {
        "Shape distortion": 0,
        "Size error": 0,
        "Crack detected": 0,
        "Colour variance": 0,
        "Label missing": 0
    }
    # Temperature History array for real-time lines chart
    temp_history = []
    # Controller state
    temperature = 34.0
    state = "RUNNING"
    alert = "NORMAL OPERATION"
    last_reason = "NO INSPECTION YET"
    stop_until = 0
    # Rolling safety defect check window (last 50)
    recent_inspections = []
    
    # Popup UI flags
    show_saved_text_msg = False
    saved_msg_timeout = 0
    save_was_ok = False
    show_help = False
    
    popup_timer_start = 0
    deflector_angle = 0.0
    lo = LO
    conv_x   = lo["conv_x"]
    conv_y   = lo["conv_y"]
    conv_len = lo["conv_len"]
    active_bottles = []
    bottle_pool = []
    next_bottle_id = 1
    def spawn_bottle_obj():
        nonlocal next_bottle_id
        if bottle_pool:
            b = bottle_pool.pop()
            b.conv_y = conv_y
            b.reset()
            b.x = conv_x - 40
            b.y = conv_y
        else:
            b = Bottle(conv_x - 40, conv_y, next_bottle_id)
        b.bottle_id = next_bottle_id
        next_bottle_id += 1
        active_bottles.append(b)
    def recycle_bottle_obj(b):
        if b in active_bottles:
            active_bottles.remove(b)
        bottle_pool.append(b)
    # Initialize conveyor with spaced bottles
    for i in range(5):
        init_x = conv_x + i * 150
        b = Bottle(init_x, conv_y, next_bottle_id)
        next_bottle_id += 1
        scan_x = conv_x + int(conv_len * 0.82)
        if init_x >= scan_x:
            b.checked = True
            b.status = "GOOD"
            b.body_color = ACCENT_GRN
        active_bottles.append(b)
        batch_spawned_count += 1
    # Computer Vision scan persistent state variables
    last_cv_data = {
        "frame": None,
        "edges": None,
        "overlay": None,
        "shape_score": 100,
        "size_score": 100,
        "surface_score": 100,
        "color_score": 100,
        "label_score": 100,
        "overall": "STANDBY",
        "reason": "READY FOR DISPATCH",
        "bottle_id": 0
    }
    
    # Pre-populate standby state frame in CV panel
    standby_b = Bottle(0, 0)
    standby_b.metrics = {
        "shape": 1.0,
        "scale": 1.0,
        "crack": 0.0,
        "color_off": 0.0,
        "label": True
    }
    standby_b.body_color = ACCENT_BLUE
    standby_frame = generate_cv_frame(standby_b)
    gray, edges, overlay = process_cv_inspection(standby_frame)
    last_cv_data["frame"] = cv_to_pygame(standby_frame)
    last_cv_data["edges"] = cv_to_pygame(edges)
    last_cv_data["overlay"] = cv_to_pygame(overlay)
    anim_tick = 0
    # UI Interactive collision Rects (dummies)
    btn_start_rect = pygame.Rect(0, 0, 0, 0)
    btn_stop_rect = pygame.Rect(0, 0, 0, 0)
    btn_reset_rect = pygame.Rect(0, 0, 0, 0)
    btn_help_rect = pygame.Rect(0, 0, 0, 0)
    btn_reports_rect = pygame.Rect(0, 0, 0, 0)
    btn_help_close = pygame.Rect(0, 0, 0, 0)
    btn_cont = pygame.Rect(0, 0, 0, 0)
    btn_dismiss = pygame.Rect(0, 0, 0, 0)
    btn_save_popup = pygame.Rect(0, 0, 0, 0)
    while True:
        now = pygame.time.get_ticks()
        w, h = SCREEN.get_size()
        running = (state == "RUNNING")
        mx, my = pygame.mouse.get_pos()
        # ── Event Handling ──
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif ev.type == pygame.VIDEORESIZE:
                SCREEN_W, SCREEN_H = ev.w, ev.h
                SCREEN = pygame.display.set_mode((SCREEN_W, SCREEN_H), pygame.RESIZABLE)
                w, h = SCREEN_W, SCREEN_H
                lo = compute_layout(w, h)
                conv_x, conv_y, conv_len = lo["conv_x"], lo["conv_y"], lo["conv_len"]
                for b in active_bottles:
                    b.conv_y = conv_y
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_h or ev.key == pygame.K_QUESTION:
                    show_help = not show_help
                    play_alert("resume")
                elif ev.key == pygame.K_ESCAPE:
                    if show_help:
                        show_help = False
                        play_alert("resume")
                elif ev.key == pygame.K_SPACE:
                    if show_help:
                        show_help = False
                        play_alert("resume")
                    elif state == "REPORT_POPUP":
                        state = "RUNNING"
                        alert = "BATCH PRODUCTION RESUMED"
                        batch_number += 1
                        batch_spawned_count = 0
                        batch_completed_count = 0
                        batch_good = 0
                        batch_defective = 0
                        batch_packaged = 0
                        batch_waste = 0
                        batch_temp_sum = 0.0
                        batch_temp_count = 0
                        batch_temp_max = 0.0
                        batch_start_time = now
                        recent_inspections.clear()
                        show_saved_text_msg = False
                        for k in batch_defects:
                            batch_defects[k] = 0
                        play_alert("resume")
                    else:
                        state = "RUNNING"
                        alert = "OPERATOR RESUMED"
                        recent_inspections.clear()
                        play_alert("resume")
                elif ev.key == pygame.K_s:
                    if state == "RUNNING":
                        state = "PAUSED"
                        alert = "MANUAL EMERGENCY STOP"
                        play_alert("warning")
                elif ev.key == pygame.K_r:
                    # Session Reset (preserving historical report folder content)
                    lifetime_produced = lifetime_good = lifetime_defective = 0
                    lifetime_packaged = lifetime_waste = 0
                    batch_number = 1
                    batch_spawned_count = batch_completed_count = 0
                    batch_good = batch_defective = batch_packaged = batch_waste = 0
                    batch_temp_sum = batch_temp_count = batch_temp_max = 0.0
                    batch_start_time = now
                    temperature = 34.0
                    state = "RUNNING"
                    alert = "FACTORY RESET COMPLETE"
                    last_reason = "NO INSPECTION YET"
                    recent_inspections.clear()
                    temp_history.clear()
                    active_bottles.clear()
                    bottle_pool.clear()
                    show_saved_text_msg = False
                    for k in batch_defects:
                        batch_defects[k] = 0
                    next_bottle_id = 1
                    
                    # Re-init conveyor
                    for i in range(5):
                        init_x = conv_x + i * 150
                        b = Bottle(init_x, conv_y, next_bottle_id)
                        next_bottle_id += 1
                        active_bottles.append(b)
                        batch_spawned_count += 1
                    play_alert("resume")
                    
            elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
                # Trigger click callbacks
                if show_help:
                    if btn_help_close.collidepoint(ev.pos):
                        show_help = False
                        play_alert("resume")
                elif state == "REPORT_POPUP":
                    if btn_cont.collidepoint(ev.pos) or btn_dismiss.collidepoint(ev.pos):
                        state = "RUNNING"
                        alert = "BATCH PRODUCTION RESUMED"
                        batch_number += 1
                        batch_spawned_count = 0
                        batch_completed_count = 0
                        batch_good = 0
                        batch_defective = 0
                        batch_packaged = 0
                        batch_waste = 0
                        batch_temp_sum = 0.0
                        batch_temp_count = 0
                        batch_temp_max = 0.0
                        batch_start_time = now
                        recent_inspections.clear()
                        show_saved_text_msg = False
                        for k in batch_defects:
                            batch_defects[k] = 0
                        play_alert("resume")
                    elif btn_save_popup.collidepoint(ev.pos):
                        # Manual trigger save file
                        if batch_good >= 950:
                            stars_txt = "★★★★★ Excellent"
                        elif batch_good >= 880:
                            stars_txt = "★★★★ Good"
                        else:
                            stars_txt = "★★ Average"
                        
                        duration_s = (now - batch_start_time) / 1000.0
                        avg_t = (batch_temp_sum / batch_temp_count) if batch_temp_count else temperature
                        max_t = max(batch_temp_max, temperature)
                        
                        save_was_ok = save_batch_reports(
                            batch_number, batch_good, batch_defective, batch_defects,
                            avg_t, max_t, duration_s, SPEED, stars_txt,
                            lifetime_produced - 1000 + 1, lifetime_produced
                        )
                        show_saved_text_msg = True
                        saved_msg_timeout = now + 4000
                        play_alert("resume")
                else:
                    if btn_start_rect.collidepoint(ev.pos):
                        state = "RUNNING"
                        alert = "OPERATOR RESUMED"
                        recent_inspections.clear()
                        play_alert("resume")
                    elif btn_stop_rect.collidepoint(ev.pos):
                        state = "PAUSED"
                        alert = "MANUAL EMERGENCY STOP"
                        play_alert("warning")
                    elif btn_reset_rect.collidepoint(ev.pos):
                        lifetime_produced = lifetime_good = lifetime_defective = 0
                        lifetime_packaged = lifetime_waste = 0
                        batch_number = 1
                        batch_spawned_count = batch_completed_count = 0
                        batch_good = batch_defective = batch_packaged = batch_waste = 0
                        batch_temp_sum = batch_temp_count = batch_temp_max = 0.0
                        batch_start_time = now
                        temperature = 34.0
                        state = "RUNNING"
                        alert = "FACTORY RESET COMPLETE"
                        last_reason = "NO INSPECTION YET"
                        recent_inspections.clear()
                        temp_history.clear()
                        active_bottles.clear()
                        bottle_pool.clear()
                        show_saved_text_msg = False
                        for k in batch_defects:
                            batch_defects[k] = 0
                        next_bottle_id = 1
                        
                        for i in range(5):
                            init_x = conv_x + i * 150
                            b = Bottle(init_x, conv_y, next_bottle_id)
                            next_bottle_id += 1
                            active_bottles.append(b)
                            batch_spawned_count += 1
                        play_alert("resume")
                    elif btn_help_rect.collidepoint(ev.pos):
                        show_help = True
                        play_alert("resume")
                    elif btn_reports_rect.collidepoint(ev.pos):
                        try:
                            project_dir = os.path.dirname(os.path.abspath(__file__))
                            reports_dir = os.path.join(project_dir, "reports")
                            os.makedirs(reports_dir, exist_ok=True)
                            os.startfile(reports_dir)
                            play_alert("resume")
                        except Exception as e:
                            print(f"Error opening reports directory: {e}")
        # ── Simulation & Sensors Logic ──
        if running:
            temperature += random.uniform(0.06, 0.16)
        else:
            temperature -= random.uniform(0.12, 0.28)
        temperature = max(20.0, min(temperature, 55.0))
        if running:
            temp_history.append(temperature)
            if len(temp_history) > 100:
                temp_history.pop(0)
        if stop_until and now >= stop_until:
            state = "RUNNING"
            alert = "AUTOMATIC RESTART"
            stop_until = 0
            recent_inspections.clear()
        if show_saved_text_msg and now > saved_msg_timeout:
            show_saved_text_msg = False
        to_recycle = []
        if running:
            batch_temp_sum += temperature
            batch_temp_count += 1
            batch_temp_max = max(batch_temp_max, temperature)
            # Spawn clearance check
            leftmost_x = 999999
            for b in active_bottles:
                if b.status in ("IN_TRANSIT", "GOOD", "DEFECT") and b.x < leftmost_x:
                    leftmost_x = b.x
            
            if leftmost_x > conv_x + 125:
                if batch_spawned_count < 1000:
                    spawn_bottle_obj()
                    batch_spawned_count += 1
            # Laser scan line logic
            scan_x = conv_x + int(conv_len * 0.82)
            for b in active_bottles:
                b.update(True)
                
                if (scan_x - 10 <= b.x <= scan_x + 10) and not b.checked:
                    b.checked = True
                    lifetime_produced += 1
                    batch_completed_count += 1
                    
                    # Generate real OpenCV preprocessed frames
                    cv_frame = generate_cv_frame(b)
                    gray_img, edges_img, overlay_img = process_cv_inspection(cv_frame)
                    
                    last_cv_data["frame"] = cv_to_pygame(cv_frame)
                    last_cv_data["edges"] = cv_to_pygame(edges_img)
                    last_cv_data["overlay"] = cv_to_pygame(overlay_img)
                    
                    last_cv_data["shape_score"] = int(b.metrics["shape"] * 100) if b.metrics["shape"] >= 0.91 else int(b.metrics["shape"] * 80)
                    last_cv_data["size_score"] = int((1.0 - abs(b.metrics["scale"] - 1.0)) * 100)
                    last_cv_data["surface_score"] = 100 if b.metrics["crack"] == 0 else int((1.0 - b.metrics["crack"]) * 50)
                    last_cv_data["color_score"] = int((1.0 - min(1.0, abs(b.metrics["color_off"]) / 30.0)) * 100)
                    last_cv_data["label_score"] = 100 if b.metrics["label"] else 0
                    last_cv_data["bottle_id"] = b.bottle_id
                    
                    issues = b.inspect()
                    if issues:
                        b.status = "DEFECT"
                        b.body_color = ACCENT_RED
                        b.defect_reason = issues[0]
                        
                        lifetime_defective += 1
                        lifetime_waste += 1
                        batch_defective += 1
                        batch_waste += 1
                        
                        for issue in issues:
                            if issue in batch_defects:
                                batch_defects[issue] += 1
                                
                        last_reason = f"Btl #{lifetime_produced} FAIL: {issues[0]}"
                        recent_inspections.append(False)
                        play_alert("defect")
                    else:
                        b.status = "GOOD"
                        b.body_color = ACCENT_GRN
                        
                        lifetime_good += 1
                        lifetime_packaged += 1
                        batch_good += 1
                        batch_packaged += 1
                        
                        last_reason = f"Btl #{lifetime_produced} PASS: OK"
                        recent_inspections.append(True)
                        
                    last_cv_data["overall"] = b.status
                    last_cv_data["reason"] = issues[0] if issues else "OK"
                    
                    if len(recent_inspections) > 50:
                        recent_inspections.pop(0)
                    # 1000 bottle batch cycle logic
                    if batch_completed_count >= 1000:
                        state = "REPORT_POPUP"
                        alert = f"BATCH #{batch_number} REPORT GENERATED"
                        popup_timer_start = now
                        stop_until = 0
                        
                        if batch_good >= 950:
                            stars_txt = "★★★★★ Excellent"
                        elif batch_good >= 880:
                            stars_txt = "★★★★ Good"
                        else:
                            stars_txt = "★★ Average"
                        
                        duration_s = (now - batch_start_time) / 1000.0
                        avg_t = (batch_temp_sum / batch_temp_count) if batch_temp_count else temperature
                        max_t = max(batch_temp_max, temperature)
                        
                        # Save files automatically on transition
                        save_was_ok = save_batch_reports(
                            batch_number, batch_good, batch_defective, batch_defects,
                            avg_t, max_t, duration_s, SPEED, stars_txt,
                            lifetime_produced - 1000 + 1, lifetime_produced
                        )
                        show_saved_text_msg = True
                        saved_msg_timeout = now + 4000
                        play_alert("batch_complete")
                # Chute transitions
                if b.status == "GOOD" and b.x > conv_x + conv_len:
                    b.status = "SORTING_GOOD"
                elif b.status == "DEFECT" and b.x > conv_x + conv_len:
                    b.status = "SORTING_DEFECT"
                elif b.status == "IN_TRANSIT" and b.x > conv_x + conv_len:
                    b.status = "SORTING_GOOD"
                # Recycle
                if b.status in ("SORTING_GOOD", "SORTING_DEFECT") and b.y > conv_y + 90:
                    to_recycle.append(b)
            # Safety locks
            if temperature >= OVERHEAT_TEMP:
                state = "OVERHEAT STOP"
                alert = "OVERHEAT ALARM — COOLING ACTIVE"
                stop_until = now + 3200
                play_alert("warning")
            if len(recent_inspections) >= 30:
                recent_defects = recent_inspections.count(False)
                recent_rate = recent_defects / len(recent_inspections)
                if recent_defects >= HIGH_DEFECT_COUNT or recent_rate >= MAX_DEFECT_RATE:
                    state = "DEFECT STOP"
                    alert = f"SAFETY SCRAM: HIGH DEFECT RATE ({recent_rate*100.0:.1f}%)"
                    stop_until = now + 4000
                    play_alert("warning")
        else:
            for b in active_bottles:
                if b.status in ("SORTING_GOOD", "SORTING_DEFECT"):
                    b.update(True)
                    if b.y > conv_y + 90:
                        to_recycle.append(b)
        # Recycle completed items
        for b in to_recycle:
            recycle_bottle_obj(b)
        # Interpolate sorting deflector arm angle
        target_angle = 0.0
        for b in active_bottles:
            if b.status == "SORTING_DEFECT" and b.x < conv_x + conv_len + 60:
                target_angle = 45.0
                break
        deflector_angle += (target_angle - deflector_angle) * 0.22
        # ── Draw Phase ──
        SCREEN.fill(BG)
        # Draw blueprint grid pattern
        mx, mw = lo["mid_x"], lo["mid_w"]
        rrect(SCREEN, (10, 16, 28, 200), (mx, 54, mw, h - 54), r=0)
        grid_size = 35
        for gx in range(mx, mx + mw, grid_size):
            pygame.draw.line(SCREEN, (15, 23, 40), (gx, 54), (gx, h), 1)
        for gy in range(54, h, grid_size):
            pygame.draw.line(SCREEN, (15, 23, 40), (mx, gy), (mx + mw, gy), 1)
        draw_header(SCREEN, w, h, state, batch_number)
        draw_conveyor(SCREEN, lo, anim_tick, running)
        draw_stages(SCREEN, lo, anim_tick, active_bottles, running)
        draw_sorting_station(SCREEN, lo, deflector_angle)
        # Draw bottles
        for b in active_bottles:
            b.draw(SCREEN)
        # Draw left/right responsive dashboards
        total_eff = (lifetime_good / lifetime_produced * 100) if lifetime_produced else 0.0
        
        btn_start_rect, btn_stop_rect, btn_reset_rect, btn_help_rect = draw_left(
            SCREEN, lo, w, h, lifetime_produced, lifetime_good, lifetime_defective,
            lifetime_packaged, lifetime_waste, total_eff, temperature, state, alert, batch_number, anim_tick, mx, my
        )
        btn_reports_rect = draw_right(
            SCREEN, lo, w, h, lifetime_produced, lifetime_defective,
            lifetime_packaged, lifetime_waste, total_eff, temp_history, mx, my
        )
        # Draw Computer Vision bottom center panel
        draw_cv_panel(SCREEN, lo["cv_x"], lo["cv_y"], lo["cv_w"], lo["cv_h"], last_cv_data)
        # Draw scanning feedback text bar
        draw_feedback(SCREEN, lo, w, h, last_reason, state)
        # Side frame division lines
        pygame.draw.line(SCREEN, BORDER, (lo["left_w"], 54), (lo["left_w"], h), 1)
        pygame.draw.line(SCREEN, BORDER, (lo["right_x"], 54), (lo["right_x"], h), 1)
        # Draw Batch report modal popup if active
        if state == "REPORT_POPUP":
            elapsed_popup = now - popup_timer_start
            countdown_sec = max(0, 10 - int(elapsed_popup / 1000))
            
            if batch_good >= 950:
                stars = "★★★★★ Excellent"
            elif batch_good >= 880:
                stars = "★★★★ Good"
            else:
                stars = "★★ Average"
                
            duration = (now - batch_start_time) / 1000.0
            avg_temp = (batch_temp_sum / batch_temp_count) if batch_temp_count else temperature
            max_temp = max(batch_temp_max, temperature)
            
            btn_cont, btn_save_popup, btn_dismiss = draw_report_popup(
                SCREEN, w, h, batch_number, batch_good, batch_defective, batch_defects,
                avg_temp, max_temp, duration, SPEED, stars, countdown_sec,
                show_saved_text_msg, save_was_ok
            )
            
            # Auto-resume timeout (10 seconds)
            if elapsed_popup >= 10000:
                state = "RUNNING"
                alert = "BATCH PRODUCTION RESUMED"
                batch_number += 1
                batch_spawned_count = 0
                batch_completed_count = 0
                batch_good = 0
                batch_defective = 0
                batch_packaged = 0
                batch_waste = 0
                batch_temp_sum = 0.0
                batch_temp_count = 0
                batch_temp_max = 0.0
                batch_start_time = now
                recent_inspections.clear()
                show_saved_text_msg = False
                for k in batch_defects:
                    batch_defects[k] = 0
                play_alert("resume")
        # Draw manual help guide overlay if active
        if show_help:
            btn_help_close = draw_help_overlay(SCREEN, w, h)
        pygame.display.flip()
        
        if running:
            anim_tick += 1
            
        CLOCK.tick(60)
if __name__ == "__main__":
    run()
