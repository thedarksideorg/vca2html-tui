import os
import sys
import time
import stat
import textwrap
import pandas as pd
import numpy as np
import difflib
import re
import shutil
import random
import json
import hashlib
import math
import base64
from datetime import datetime, timezone

GLOBAL_LICENSE = "Copyright © 2026 Daniel Casada. This program is free software; You can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation. This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE."
GLOBAL_DISCLAIMER = "This application was created to help optical lab technicians get lens technical specifications into legacy LMS systems. This tool tries to take industry \"standard VCA files\", parse them properly, then format them into a human readable format. It is not affiliated with National Optronics™ (DAC Vision™) or any proprietary LMS manufacturer. There is absolutely no support for this tool and I am not responsible for any invalid information, errors, or any data loss. This application comes as is and you must use at your own risk."

POLL_RATE = 0.01

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DB_DIR = os.path.join(DATA_DIR, 'db')
IMPORT_DIR = os.path.join(DATA_DIR, 'import')
ORIGINALS_DIR = os.path.join(DATA_DIR, 'originals')
VAULT_DIR = os.path.join(DB_DIR,'.vault')
PURGED_DIR = os.path.join(DB_DIR,'purged')
CORRUPT_DIR = os.path.join(DB_DIR,'currupt')
TEMP_DIR = os.path.join(DATA_DIR,'.temp')
HTML_DIR = os.path.join(DATA_DIR,'HTML')
HTML_DATA_DIR = os.path.join(HTML_DIR, 'data')
HTML_FONT_DIR = os.path.join(HTML_DATA_DIR,'fonts')
HTML_DB_DIR = os.path.join(HTML_DATA_DIR, 'db')

CONFIG_FILE = os.path.join(DATA_DIR, '.config')
DB_FILE = os.path.join(DB_DIR, 'master_lens_db.json')
SIG_FILE = os.path.join(DB_DIR, '.sig')

DEFAULT_CONFIG = {
    "nerd_fonts": False,
    "admin_enabled": True,
    "sys_auth": "c94bec1f5512d6508e50fcd325635357b3c25e90f07ac5635801dd536486bb84",
    "mfg_map": {}
}

CUSTOM_SCHEMA = [
    "MFG", "CLASS", "DESCRIPTION", "MATCODE", "MATBRAND", "PRODUCT", "STYLE", 
    "FILTER", "COAT", "COATBRAND", "OPCR", "OPCL", "DIAMETER", "SPH/BASE", 
    "CYL/ADD", "RADIUSF", "RADIUSB", "CT", "ET", "INSET", "DROP", "DINDEX", 
    "NINDEX", "EINDEX", "ABBE", "DENSITY", "PRPOUT", "PRPUP", "SEGW", "SEGT", 
    "INTHT", "SLAB", "CARRAD", "BOWLD", "VERTD", "DIADIA", "SEGSEP", "UPADD", 
    "SPECIAL", "CATCODE", "FILTERBRAND", "DRPIN", "DRPUP", "NRPIN", "NRPUP", 
    "DIAH", "DIAN", "OBJCLEAR", "OBJRADIUS", 
    "SAFE_INDEX", "TRUE_FRONT", "TRUE_BACK", "SAG" 
]

SCHEMA_LOOKUP = {re.sub(r'[^a-zA-Z0-9]', '', col).lower(): col for col in CUSTOM_SCHEMA}

SCHEMA_ALIAS = {
    "frntrad": "RADIUSF", "frontradius": "RADIUSF",
    "bckrad": "RADIUSB", "backradius": "RADIUSB",
    "cthk": "CT", "centerthick": "CT",
    "ethk": "ET", "edgethick": "ET",
    "segwd": "SEGW", "segwidth": "SEGW",
    "segthk": "SEGT", "segthick": "SEGT",
    "intht": "INTHT", "intermediateht": "INTHT",
    "bwldiam": "BOWLD", "bowldia": "BOWLD",
    "verdiam": "VERTD", "verdia": "VERTD",
    "hordiam": "DIAH", "horizontaldia": "DIAH",
    "nomdiam": "DIAN", "nominaldia": "DIAN",
    "lrpin": "INSET", "lrpdown": "DROP",
    "nref": "NINDEX", "carrad": "CARRAD", "carrierradius": "CARRAD",
    "diam": "DIAMETER", "material": "MATCODE",
    "materialbrand": "MATBRAND", "matbrand": "MATBRAND",
    "productname": "PRODUCT", "prod": "PRODUCT",
    "color": "FILTER", "tint": "FILTER",
    "coating": "COAT", "coatings": "COAT", "coatcode": "COAT",
    "rightopc": "OPCR", "ropc": "OPCR", "opcr": "OPCR", "opc": "OPCR", "upc": "OPCR",
    "leftopc": "OPCL", "lopc": "OPCL", "opcl": "OPCL"
}

ascii_art = [
    r"██╗   ██╗ ██████╗ █████╗   ██████╗ ██╗  ██╗████████╗███╗   ███╗██╗        ████████╗██╗   ██╗██╗",
    r"██║   ██║██╔════╝██╔══██╗ ╚════██╗ ██║  ██║╚══██╔══╝████╗ ████║██║        ╚══██╔══╝██║   ██║██║",
    r"██║   ██║██║     ███████║  █████╔╝ ███████║   ██║   ██╔████╔██║██║           ██║   ██║   ██║██║",
    r"╚██╗ ██╔╝██║     ██╔══██║ ██╔═══╝  ██╔══██║   ██║   ██║╚██╔╝██║██║           ██║   ██║   ██║██║",
    r" ╚████╔╝ ╚██████╗██║  ██║ ███████╗ ██║  ██║   ██║   ██║ ╚═╝ ██║███████╗      ██║   ╚██████╔╝██║",
    r"  ╚═══╝   ╚═════╝╚═╝  ╚═╝ ╚══════╝ ╚═╝  ╚═╝   ╚═╝   ╚═╝     ╚═╝╚══════╝      ╚═╝    ╚═════╝ ╚═╝"
]

# ----- UTILITY FUNCTIONS ----- #

def load_config():
    cfg = DEFAULT_CONFIG.copy()
    
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                user_cfg = json.load(f)
                
                # ----- Non-Destructive Merge ----- #
                for k, v in user_cfg.items():
                    if k == "mfg_map" and isinstance(v, dict):
                        cfg["mfg_map"].update(v)
                    else:
                        cfg[k] = v
        except: pass
        
    save_config(cfg)
    return cfg

def save_config(cfg):
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(cfg, f, indent=4)
    except: pass

def get_term_size():
    if os.name == 'nt':
        try:
            import ctypes, struct
            h = ctypes.windll.kernel32.GetStdHandle(-11)
            csbi = ctypes.create_string_buffer(22)
            if ctypes.windll.kernel32.GetConsoleScreenBufferInfo(h, csbi):
                _, _, _, _, _, left, top, right, bottom, _, _ = struct.unpack("hhhhHhhhhhh", csbi.raw)
                return (right - left + 1), (bottom - top + 1)
        except: pass
            
    try:
        sz = os.get_terminal_size(0)
        return sz.columns, sz.lines
    except OSError:
        import shutil
        sz = shutil.get_terminal_size((100, 30))
        return sz.columns, sz.lines

def check_term_size():
    term_w, term_h = get_term_size()
    return term_w >= 100 and term_h >= 30

def warn_term_size():
    while True:
        term_w, term_h = get_term_size()
        if term_w >= 100 and term_h >= 30:
            if os.name == 'nt':
                import msvcrt
                while msvcrt.kbhit(): msvcrt.getch()
            else:
                import termios
                try: termios.tcflush(sys.stdin, termios.TCIOFLUSH)
                except: pass
            
            sys.stdout.write("\033[2J\033[H")
            sys.stdout.flush()
            break
            
        sys.stdout.write("\033[2J\033[H")
        
        pause_title = "*** PAUSED ACTION ***"
        title = "[ TERMINAL TOO SMALL ]"
        dim = f"Current: {term_w}x{term_h}  |  Required: 100x30"
        msg = "Please maximize or resize your window to continue."
        
        start_y = term_h // 2 - 1
        
        # ----- Centered Pause Banner ----- #
        sys.stdout.write(f"\033[{start_y - 2};{(term_w - len(pause_title)) // 2}H{pause_title}")
        sys.stdout.write(f"\033[{start_y};{(term_w - len(title)) // 2}H{title}")
        sys.stdout.write(f"\033[{start_y + 1};{(term_w - len(dim)) // 2}H{dim}")
        sys.stdout.write(f"\033[{start_y + 3};{(term_w - len(msg)) // 2}H{msg}")
        sys.stdout.flush()
        
        if os.name == 'nt':
            import msvcrt
            while msvcrt.kbhit(): msvcrt.getch()
        else:
            import termios
            try: termios.tcflush(sys.stdin, termios.TCIOFLUSH)
            except: pass
            
        time.sleep(POLL_RATE)

def getch_timeout(timeout=POLL_RATE):
    if os.name == 'nt':
        import msvcrt
        start = time.time()
        while True:
            if msvcrt.kbhit():
                ch = msvcrt.getch()
                if ch == b'\x1b': return 'ESC'
                if ch in (b'\xe0', b'\x00'):
                    arr = msvcrt.getch()
                    if arr == b'H': return 'UP'
                    if arr == b'P': return 'DOWN'
                    if arr == b'K': return 'LEFT'
                    if arr == b'M': return 'RIGHT'
                    if arr == b'I': return 'PGUP'
                    if arr == b'Q': return 'PGDN'
                    return 'ARROWS'
                return ch.decode('utf-8', errors='ignore')
            if time.time() - start > timeout: return None
            time.sleep(0.01)
    else:
        import tty, termios, select
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            dr, _, _ = select.select([sys.stdin], [], [], timeout)
            if dr:
                ch = sys.stdin.read(1)
                if ch == '\x1b':
                    dr2, _, _ = select.select([sys.stdin], [], [], 0.01)
                    if dr2:
                        ch2 = sys.stdin.read(1)
                        if ch2 == '[':
                            ch3 = sys.stdin.read(1)
                            if ch3 == 'A': return 'UP'
                            if ch3 == 'B': return 'DOWN'
                            if ch3 == 'C': return 'RIGHT'
                            if ch3 == 'D': return 'LEFT'
                            if ch3 == '5': sys.stdin.read(1); return 'PGUP'
                            if ch3 == '6': sys.stdin.read(1); return 'PGDN'
                        return 'ARROWS'
                    return 'ESC'
                return ch
            return None
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
            
def strip_codes(text):
    return re.sub(r'\033\[[0-9;]*m', '', str(text))
    
def get_file_hash(pth):
    sha = hashlib.sha256()
    try:
        with open(pth, 'rb') as f:
            while chunk := f.read(8192):
                sha.update(chunk)
        return sha.hexdigest()
    except: return ""

def safe_float(val, default=0.0):
    try:
        if val is None or str(val).strip() == "" or str(val).strip().upper() == "ND":
            return default
        f_val = float(val)
        if f_val != f_val: 
            return default
        return f_val
    except Exception:
        return default

def color_code(val):
    raw = str(val).replace('-', '').replace(' ', '').upper().strip()
    if not raw or raw in ["NONE", "N/A", "NA"]:
        return "CLEAR"
    return raw

def strip_colors(desc):
    pattern = re.compile(r'\b(GRAY|GREY|BROWN|YELLOW|GREEN|BURGUNDY|CLEAR|BLUE|PINK|PURPLE)(?:[\-\s]*\d+)?\b', re.IGNORECASE)
    scrubbed = pattern.sub('', str(desc))
    return re.sub(r'\s+', ' ', scrubbed).strip()
    
def resolve_material(mat_str, mat_brand_str, index_val, desc_str, name_str, abbe_val, global_context=None):
    if global_context is None:
        global_context = {}
        
    c = f" {str(mat_str)} {str(mat_brand_str)} {str(desc_str)} {str(name_str)} ".upper()
    
    i_val = safe_float(index_val, 0.0)
    a_val = safe_float(abbe_val, 0.0)
    
    if re.search(r'\b(ULTRA[\s\-]?FLEX|ULTFLX)\b', c):
        return "1.60 (MR-8+)"
        
    if "POLYCARBONATE" in c or i_val == 1.586 or ("POLY" in c and "POLYURETHANE" not in c and "POLYMER" not in c):
        return "Polycarbonate"
    if "TRIVEX" in c or re.search(r'\bTR\b', c) or "PNX" in c or i_val == 1.53:
        return "Trivex"
    if "CR39" in c or "CR-39" in c or re.search(r'\bPL\b', c) or i_val == 1.50:
        return "CR-39"
        
    if 1.54 <= i_val <= 1.565:
        return "1.56"
        
    if 1.59 <= i_val <= 1.61 or "1.60" in c:
        return "1.60 (MR-8)"
        
    if 1.73 <= i_val <= 1.745 or "1.74" in c:
        return "1.74 (MR-74)"
        
    if 1.65 <= i_val <= 1.675 or "1.67" in c:
        # Start with the pre-flight inverse deduction bias (+1 if applicable)
        m10_score = global_context.get("m10_bias", 0)
        m7_score = global_context.get("m7_bias", 0)
        
        if a_val == 31: m10_score += 2
        if a_val == 32: m7_score += 2
        
        if "MR10" in c or "MR-10" in c: m10_score += 5
        if "MR7" in c or "MR-7" in c: m7_score += 5
        
        if m10_score > m7_score:
            return "1.67 (MR-10)"
        elif m7_score > m10_score:
            return "1.67 (MR-7)"
        else:
            m_key = f"1.67_{mat_str}_{desc_str}"
            if m_key in global_context:
                return global_context[m_key]
                
            sys.stdout.write("\033[2J\033[H")
            def draw_bg(tw, th):
                draw_skeleton("MATERIAL HEURISTIC TIE", f"Lens: {mat_str} {desc_str} | Index: {i_val:.2f} | Abbe: {int(a_val)}")
                
            ans = draw_z_modal("MATERIAL HEURISTIC TIE", "Is this MR-7 or MR-10? Type 7 or 10:", False, draw_bg)
            if ans and ans.strip() == "10":
                global_context[m_key] = "1.67 (MR-10)"
                return "1.67 (MR-10)"
            else:
                global_context[m_key] = "1.67 (MR-7)"
                return "1.67 (MR-7)"
                
    if mat_str and str(mat_str).strip():
        return str(mat_str).title()
    return "Unknown Material"
    
def map_lens_group(raw_desc):
    n = str(raw_desc).upper()
    
    n = re.sub(r'\b(?:HARD RESIN|RESIN|ORG)\b', 'CR-39', n)
    n = re.sub(r'\bBLUE\s*GUARD\b', 'BLUEGUARD', n)
    n = re.sub(r'\bBLUE\s*PROTECT\b', 'BLUEPROTECT', n)
    n = re.sub(r'\bBLUE\s*FILTER\b', 'BLUEFILTER', n)
    n = re.sub(r'\bPHOTOFUSION(?!\s*X)\b', 'PHOTOFUSION X', n)
    
    n = re.sub(r'\b(?:EXTRA\s*-?\s*THICK|EXTHK|ET)\b', '__ET__', n)
    n = re.sub(r'\b(?:EXTRA\s*-?\s*THIN)\b', '__E_THIN__', n)
    n = re.sub(r'\b(?:DOUBLE\s*-?\s*D|OCCUPATIONAL|OCCUP|OCC|DD)\b', '__DD__', n)
    
    # ----- Strip colors and shade suffixes so color variations roll up into one parent lens ----- #
    n = re.sub(
        r'\b(PRO GRAY|PRO GREY|PRO BROWN|EXTRA-GRAY|EXTRA-GREY|EXTRA GRAY|EXTRA GREY|EXTRAGRAY|EXTRAGREY|'
        r'GRAY|GREY|GRY|BROWN|BRN|GREEN|GRN|G15|G-15|PIONEER|PIONEEER|PIO|EMERALD|BURGUNDY|BURG|BRG|'
        r'PINK|PNK|BLUE|BLU|PURPLE|PURP|PLUM|YELLOW|YEL|YLW|ROSE|ROS|ORANGE|PRO|EXTRA|EXG)'
        r'(?:\s*[-]?\s*[123ABC])?\b', '', n
    )
    
    # ----- Strip diameter tags and basic coating suffixes ----- #
    n = re.sub(r'\bD-?\d{2,3}\b', '', n)
    n = re.sub(r'\b\d{2,3}\s*MM\b', '', n)
    
    for word in [
        'HC', 'SR', 'SHMC', 'PG', 'UT', 'YHC', 'US', 'UC', 'UNCOATED', 'HCT',
        'YOUNGERHC', 'YOUNGER HARDCOAT', 'YOUNGER HARD COAT', 'YOUNGER HARD-COAT',
        'PERMAGUARD', 'PERMA-GUARD', 'PERMA GUARD', 'ULTRATOUGH', 'ULTRA-TOUGH', 'ULTRA TOUGH',
        'ULTRASHIELD', 'ULTRA-SHIELD', 'ULTRA SHIELD', 'HARDCOAT', 'HARD COAT', 'HARD-COAT', 'HARD', 'UVRI'
    ]:
        n = re.sub(rf'\b{word}\b', '', n)
        
    n = n.replace('__ET__', 'EXTRA-THICK')
    n = n.replace('__E_THIN__', 'EXTRA-THIN')
    n = n.replace('__DD__', 'DOUBLE-D')
    return re.sub(r'\s+', ' ', n).strip()
    
def map_lens_style(row):
    raw_style = str(row.get('STYLE', row.get('Style', ''))).upper().strip()
    raw_desc = str(row.get('DESCRIPTION', row.get('Description', ''))).upper()
    raw_name = str(row.get('PRODUCT', row.get('Name', ''))).upper()
    c = f" {raw_style} {raw_desc} {raw_name} "
    
    # ----- Neutralize diameter tags so they don't trigger D-segment matches ----- #
    diam = str(row.get('DIAMETER', row.get('Diameter', ''))).strip()
    if diam:
        try:
            d_val = int(float(diam))
            c = re.sub(rf'\bD-?{d_val}\b', '', c)
        except:
            pass

    # ----- Seg Width Validation (22 to 45) ----- #
    seg_width = str(row.get('SEGW', row.get('Seg Width', ''))).strip()
    has_valid_seg = False
    if seg_width:
        try:
            s_val = int(float(seg_width))
            if 22 <= s_val <= 45:
                has_valid_seg = True
        except:
            pass

    # ----- Progressive Check ----- #
    if any(x in c for x in [' PROG ', ' PR ', ' PAL ', ' PROGRESSIVE ']) or raw_style == 'PR':
        return 6
        
    # ----- Double Seg ----- #
    if any(x in c for x in [' DOUBLE ', ' DBL ', ' QUAD ', ' DUAL ']):
        return 9 if ' EXEC ' in c or ' EXECUTIVE ' in c else 8
        
    # ----- Trifocal ----- #
    if any(x in c for x in [' TRI ', ' TRIFOCAL ', ' TF ', ' 7X ', ' 8X ', ' 10X ']) or re.search(r'\b\d+X\d+\b', c):
        if ' EXEC ' in c or ' EXECUTIVE ' in c: return 11
        if ' ED ' in c: return 12
        return 10
        
    # ----- Blended Seg ----- #
    if ' BLEND ' in c: return 7
        
    # ----- Ultex ----- #
    if ' ULTEX ' in c: return 5
        
    # ----- Executive Bifocal ----- #
    if any(x in c for x in [' EXEC ', ' EXECUTIVE ']): return 4
        
    # ----- Round Bifocal ----- #
    if any(x in c for x in [' RND ', ' ROUND ', ' SEG ']): return 3
        
    # ----- Flat Top Bifocal ----- #
    if any(x in c for x in [' FT ', ' BIF ', ' BIFOCAL ']) or has_valid_seg or re.search(r'\b(?:FT|D-?)\s*(22|25|28|35|40|45)\b', c):
        return 2
        
    # ----- Single Vision (fallback) ----- #
    return 1

def map_lens_tech(data, row_mode=False):
    color_code_map = {
        "Gray": "GRY", "Brown": "BRN", "Green": "GRN", "Blue": "BLU",
        "Burgundy": "BRG", "Pink": "PNK", "Purple": "PRP", "Yellow": "YEL",
        "Rose": "ROS", "Orange": "ORG", "Extra Gray": "EXG",
        "Pro Gray": "PGY", "Pro Brown": "PBN"
    }
    
    prefix_to_base = {
        "GRY": ("Gray", "Gray"), "GREY": ("Gray", "Gray"),
        "BRN": ("Brown", "Brown"), "GRN": ("Green", "Green"),
        "PIO": ("Green", "Pioneer"), "G15": ("Green", "G15"),
        "BLU": ("Blue", "Blue"), "BRG": ("Burgundy", "Burgundy"),
        "BURG": ("Burgundy", "Burgundy"), "PNK": ("Pink", "Pink"),
        "PRP": ("Purple", "Purple"), "PURP": ("Purple", "Purple"),
        "YEL": ("Yellow", "Yellow"), "YLW": ("Yellow", "Yellow"),
        "ROS": ("Rose", "Rose"), "ORG": ("Orange", "Orange"),
        "EXG": ("Extra Gray", "Extra Gray"),
        "PGY": ("Pro Gray", "Pro Gray"), "PBN": ("Pro Brown", "Pro Brown")
    }
    
    tech_ignore_tokens = {
        "UVRI", "UV", "UV400", "UV420", "HEV", "PHOT", "PHOTO", "PHT",
        "POL", "POLAR", "POLZ", "NONE", "N/A", "NA", "CLEAR", "CLR", "ND"
    }

    def parse_single_row(row):
        row_techs = set()
        row_coats_display = set()
        row_search_tags = set()
        
        raw_desc = str(row.get('DESCRIPTION', row.get('Description', ''))).upper()
        raw_prod = str(row.get('PRODUCT', row.get('Name', ''))).upper()
        raw_filt = str(row.get('FILTER', row.get('Filter', ''))).upper()
        raw_fbrand = str(row.get('FILTERBRAND', row.get('Filter Brand', ''))).upper()
        raw_coat = str(row.get('COAT', row.get('Coating', ''))).upper().strip()
        raw_cbrand = str(row.get('COATBRAND', row.get('Coating Brand', ''))).upper()
        
        combined = f" {raw_desc} {raw_prod} {raw_filt} {raw_fbrand} {raw_cbrand} {raw_coat} "
        c_pad = combined.replace('-', ' ').replace('/', ' ')
        
        c_pad_color = c_pad
        for bf_word in ['BLUE FILTER', 'BLUE BLOCKER', 'BLUE PROTECT', 'BLUE GUARD', 'BLUEGUARD', 'BLUEP', 'UV420', 'FUL PROTECT', 'GUARD']:
            c_pad_color = c_pad_color.replace(bf_word, '')
        c_pad_coat = c_pad.replace(' ', '')

        is_photochromic = False
        is_polarized = False
        
        if any(x in c_pad for x in [' XTRA ACTIVE', ' XA ', ' XTRA ']): row_techs.add('Xtra-Active'); is_photochromic = True
        elif any(x in c_pad for x in [' QUICK CHANGE', ' Q CHANGE', ' QC ']): row_techs.add('Quick-Change'); is_photochromic = True
        elif ' SUNSYNC' in c_pad: row_techs.add('SunSync'); is_photochromic = True
        elif any(x in c_pad for x in [' SENSITIVITY', ' SENSITY', ' SENS ']): row_techs.add('Sensity'); is_photochromic = True
        elif any(x in c_pad for x in [' PFX', ' PHOTOFUSION']): row_techs.add('PhotoFusion X'); is_photochromic = True
        elif any(x in c_pad for x in [' TRANSITIONS', ' TRANS ', ' TRN ']): row_techs.add('Transitions'); is_photochromic = True
        elif any(x in c_pad for x in [' LIFERX', ' LIFE RX ', ' LRX ']): row_techs.add('LifeRx'); is_photochromic = True
        elif any(x in c_pad for x in [' PHOTOCHROMIC', ' PHOTO ', ' PHOT ', ' PHT ']): is_photochromic = True
        
        if ' NUPOLAR' in c_pad: row_techs.add('NuPolar'); is_polarized = True
        elif ' TRUPOLAR' in c_pad: row_techs.add('TruPolar'); is_polarized = True
        elif any(x in c_pad for x in [' SUNRX', ' SUN RX ']): row_techs.add('SunRx'); is_polarized = True
        elif any(x in c_pad for x in [' COPPERTONE', ' COPPER ']): row_techs.add('Coppertone'); is_polarized = True
        elif any(x in c_pad for x in [' POLARIZED', ' POLAR ', ' POLZ ', ' POL ']): row_techs.add('Polarized'); is_polarized = True
        
        if ' BLUE PROTECT' in c_pad or ' BP ' in c_pad: row_techs.add('Blue Protect')
        elif ' BLUEGUARD' in c_pad or ' BLUE GUARD' in c_pad or ' BG ' in c_pad: row_techs.add('BlueGuard')
        elif ' HEV' in c_pad or ' UV420' in c_pad: row_techs.add('HEV')
        elif ' FUL PROTECT' in c_pad: row_techs.add('Ful-Protect')
        elif any(x in c_pad for x in [' BLUE BLOCKER', ' BLUE FILTER']): row_techs.add('Blue Filter')
        
        if ' UVRI' in c_pad: row_techs.add('UVRI')
        if ' UV PROTECT' in c_pad: row_techs.add('UV Protect')

        filt_tokens = [t.strip() for t in re.split(r'[\s,/]+', raw_filt.replace('-', '')) if t.strip()]
        color_tokens = [t for t in filt_tokens if t not in tech_ignore_tokens]
        
        display_color = None
        opc_color = None
        
        if color_tokens:
            cand = color_tokens[-1]
            if cand == "G15":
                display_color = "Green"; opc_color = "G15"
                row_search_tags.update(["Green", "G15", "G-15", "GRN3"])
            else:
                m_tok = re.match(r'^([A-Z]+?)([123ABC])?$', cand)
                if m_tok and m_tok.group(1) in prefix_to_base:
                    pfx = m_tok.group(1)
                    shd = m_tok.group(2) or "3"
                    if shd in "ABC": shd = {"A": "1", "B": "2", "C": "3"}[shd]
                    base_col, alias_col = prefix_to_base[pfx]
                    display_color = base_col
                    short_pfx = color_code_map.get(base_col, pfx[:3])
                    opc_color = f"{pfx if pfx in ['PIO', 'PGY', 'PBN', 'EXG'] else short_pfx}{shd}"
                    row_search_tags.update([base_col, opc_color, f"{base_col} {shd}", f"{base_col}-{shd}", alias_col, f"{alias_col} {shd}", f"{alias_col}-{shd}"])

        if not display_color:
            if any(x in c_pad_color for x in [' PRO GRAY', ' PRO GREY']):
                display_color = "Pro Gray"; opc_color = "PGY3"
                row_search_tags.update(["Pro Gray", "PGY3", "Pro Gray 3", "Pro Gray-3"])
            elif ' PRO BROWN' in c_pad_color:
                display_color = "Pro Brown"; opc_color = "PBN3"
                row_search_tags.update(["Pro Brown", "PBN3", "Pro Brown 3", "Pro Brown-3"])
            elif any(x in c_pad_color for x in [' PIONEER', ' PIONEEER', ' PIO ']):
                display_color = "Green"; opc_color = "PIO3"
                row_search_tags.update(["Green", "Pioneer", "PIO3", "PIO3"])
            elif any(x in c_pad_color for x in [' G15', ' G 15']):
                display_color = "Green"; opc_color = "G15"
                row_search_tags.update(["Green", "G15", "G-15"])
            elif any(x in c_pad_color for x in [' EXTRAGREY', ' EXTRAGRAY', ' EXTRA GREY', ' EXTRA GRAY', ' EXG ']):
                display_color = "Extra Gray"; opc_color = "EXG3"
                row_search_tags.update(["Extra Gray", "EXG3", "Extra Gray 3", "Extra Gray-3"])
            else:
                shade_match = re.search(
                    r'\b(GRAY|GREY|GRY|BROWN|BRN|GREEN|GRN|EMERALD|BURGUNDY|BURG|BRG|PINK|PNK|BLUE|BLU|PURPLE|PURP|PLUM|YELLOW|YEL|YLW|ROSE|ROS|ORANGE)'
                    r'(?:\s*([123ABC]))?\b', c_pad_color
                )
                if shade_match:
                    raw_b = shade_match.group(1)
                    shd = (shade_match.group(2) or "3").upper()
                    if shd in "ABC": shd = {"A": "1", "B": "2", "C": "3"}[shd]
                    if raw_b in ['GRAY', 'GREY', 'GRY']: display_color = "Gray"
                    elif raw_b in ['BROWN', 'BRN']: display_color = "Brown"
                    elif raw_b in ['GREEN', 'GRN', 'EMERALD']: display_color = "Green"
                    elif raw_b in ['BURGUNDY', 'BURG', 'BRG']: display_color = "Burgundy"
                    elif raw_b in ['PINK', 'PNK']: display_color = "Pink"
                    elif raw_b in ['BLUE', 'BLU']: display_color = "Blue"
                    elif raw_b in ['PURPLE', 'PURP', 'PLUM']: display_color = "Purple"
                    elif raw_b in ['YELLOW', 'YEL', 'YLW']: display_color = "Yellow"
                    elif raw_b in ['ROSE', 'ROS']: display_color = "Rose"
                    elif raw_b == 'ORANGE': display_color = "Orange"
                    short_pfx = color_code_map.get(display_color, "GRY")
                    opc_color = f"{short_pfx}{shd}"
                    row_search_tags.update([display_color, opc_color, f"{display_color} {shd}", f"{display_color}-{shd}"])

        if not display_color:
            if is_photochromic or is_polarized:
                display_color = "Gray"; opc_color = "GRY3"
                row_search_tags.update(["Gray", "GRY3", "Gray 3", "Gray-3"])
            else:
                display_color = "Clear"; opc_color = "CLEAR"

        if opc_color == "NONE" or not opc_color: opc_color = "CLEAR"
        if display_color.upper() == "NONE": display_color = "Clear"

        is_ar_row = any(x in c_pad for x in [' AR ', ' A/R ', ' DURA', ' CRIZAL', ' VELA', ' HOYA', ' ECP', ' ULTRACLEAN', ' HMC', ' SHMC', ' BMC'])
        
        if any(x in c_pad for x in [' DVC ', ' CHROME ']): row_coats_display.add('DuraVision Chrome')
        elif any(x in c_pad for x in [' DVP ', ' PLATINUM ']): row_coats_display.add('DuraVision Platinum')
        elif any(x in c_pad for x in [' DVG ', ' GOLD ']): row_coats_display.add('DuraVision Gold')
        elif any(x in c_pad for x in [' DVS ', ' SILVER ']): row_coats_display.add('DuraVision Silver')
        elif ' ROCK ' in c_pad: row_coats_display.add('Crizal Rock')
        elif ' SAPPHIRE ' in c_pad: row_coats_display.add('Crizal Sapphire')
        elif ' EASY ' in c_pad: row_coats_display.add('Crizal Easy')
        elif ' VELA ' in c_pad: row_coats_display.add('Vela')
        elif is_ar_row: row_coats_display.add('A/R')
        elif any(x in c_pad for x in [' UC ', ' UNCOATED ']): row_coats_display.add('Uncoated')

        # Drop HC/SR flags entirely from the display if it has AR
        if not is_ar_row and (any(x in c_pad for x in [' HC ', ' SR ', ' SHMC ', ' PG ', ' UT ', ' YHC ', ' US ', ' HCT ', ' HARDCOAT ', ' HARD COAT ', ' HARD ']) or any(x in c_pad_coat for x in ['ULTRASHIELD', 'PERMAGUARD', 'ULTRATOUGH', 'YOUNGERHC', 'YOUNGERHARDCOAT'])):
            row_coats_display.add('Hardcoat')
            
        if 'PERMAGUARD' in c_pad_coat or ' PG ' in c_pad: row_techs.add('PermaGuard')
        if 'ULTRATOUGH' in c_pad_coat or ' UT ' in c_pad: row_techs.add('UltraTough')
        if 'YOUNGERHC' in c_pad_coat or ' YOUNGERHARDCOAT' in c_pad_coat or ' YHC ' in c_pad: row_techs.add('Younger Hardcoat')
        if 'ULTRASHIELD' in c_pad_coat or ' US ' in c_pad: row_techs.add('Ultra-Shield')

        clean_raw_coat = re.sub(r'[^A-Z0-9]', '', raw_coat)
        
        # Override OPC to strictly 'AR' if it is Anti-Reflective, bypassing SR/SRAR
        if is_ar_row:
            opc_coat = "AR"
        elif clean_raw_coat and clean_raw_coat not in ["NONE", "NA", "NAN"] and len(clean_raw_coat) <= 4:
            opc_coat = clean_raw_coat
        elif 'PERMAGUARD' in c_pad_coat or ' PG ' in c_pad: opc_coat = "PG"
        elif 'ULTRATOUGH' in c_pad_coat or ' UT ' in c_pad: opc_coat = "UT"
        elif 'YOUNGERHC' in c_pad_coat or ' YHC ' in c_pad: opc_coat = "YHC"
        elif 'ULTRASHIELD' in c_pad_coat or ' US ' in c_pad: opc_coat = "US"
        elif 'UNCOAT' in c_pad or ' UC ' in c_pad or not raw_coat: opc_coat = "UC"
        else: opc_coat = "HC"
        
        if opc_coat == "SRAR": opc_coat = "AR"

        if any(t in row_techs for t in ['Xtra-Active', 'Quick-Change', 'SunSync', 'Sensity', 'Transitions', 'PhotoFusion X', 'LifeRx']):
            row_techs.add('Photochromic')
        if any(t in row_techs for t in ['NuPolar', 'TruPolar', 'SunRx', 'Coppertone']):
            row_techs.add('Polarized')

        return display_color, opc_color, opc_coat, row_techs, row_coats_display, row_search_tags

    if row_mode:
        disp_col, opc_col, opc_coat, _, _, row_tags = parse_single_row(data)
        return disp_col, opc_col, opc_coat, row_tags

    colors_found = set()
    techs_found = set()
    coats_found = set()
    search_tags_found = set()

    for _, row in data.iterrows():
        disp_col, opc_col, opc_coat, r_techs, r_coats, r_tags = parse_single_row(row)
        if disp_col and disp_col.upper() != "NONE":
            colors_found.add(disp_col)
        techs_found.update(r_techs)
        coats_found.update(r_coats)
        search_tags_found.update(r_tags)
        if opc_coat and opc_coat != "UC":
            search_tags_found.add(opc_coat)
        if opc_col and opc_col != "CLEAR" and opc_col != "NONE":
            search_tags_found.add(opc_col)

    return sorted(list(colors_found)), sorted(list(techs_found)), sorted(list(coats_found)), sorted(list(search_tags_found))

def map_lens_desc(sample_row, is_fsv, has_add, techs_found, extracted_coats, is_universal_ar, resolved_mat):
    raw_desc = str(sample_row.get('DESCRIPTION', sample_row.get('Description', ''))).upper().strip()
    raw_name = str(sample_row.get('PRODUCT', sample_row.get('Name', ''))).upper().strip()
    mfg = str(sample_row.get('MFG', '')).upper().strip()
    
    combined_name_desc = f"{raw_desc} {raw_name}"
    combined_name_desc = re.sub(r'\b(?:HARD RESIN|RESIN|ORG)\b', 'CR-39', combined_name_desc)
    
    style_int = map_lens_style(sample_row)
    
    brand_str = ""
    is_short = False
    is_long = False
    seg_size = ""
    is_zeiss = 'ZEISS' in mfg or 'ZEISS' in combined_name_desc
    
    is_dd = False
    dd_pct = ""
    if style_int in [8, 9] or bool(re.search(r'\b(DOUBLE\s*-?\s*D|DD|OCCUPATIONAL|OCCUP|OCC)\b', combined_name_desc)):
        is_dd = True
        pct_match = re.search(r'\b(\d{2,3}%)\b', combined_name_desc)
        dd_pct = pct_match.group(1) if pct_match else ""
    
    if style_int == 6:
        clean_name = raw_name if raw_name else raw_desc
        if mfg:
            if clean_name.startswith(mfg): clean_name = clean_name[len(mfg):].strip()
            else:
                mfg_words = mfg.split()
                if mfg_words and clean_name.startswith(mfg_words[0]):
                    clean_name = clean_name[len(mfg_words[0]):].strip()
                    
        brand_scrub = clean_name
        for word in ['SF', 'SFSV', 'FSV', 'FIN', 'ORG', 'PROG', 'PROGRESSIVE', 'PAL', 'SHORT', 'SHRT', 'SHT', 'LONG', 'LNG', 'RESIN', 'POLY', 'POLYCARBONATE', 'POLYCARB', 'CR39', 'CR-39', 'TRIVEX', 'TRV']:
            brand_scrub = re.sub(rf'\b{word}\b', '', brand_scrub, flags=re.IGNORECASE)
            
        brand_scrub = re.sub(r'\s+', ' ', brand_scrub).strip()
        brand_str = brand_scrub.split()[0] if brand_scrub else "PROG"
        
        if re.match(r'^(?:1\.\d{1,3}|0?\.\d{1,3}|D\d{2,3}|HC|UC|AR|PG|UT|US|YHC|HMC)$', brand_str, flags=re.IGNORECASE):
            brand_str = "PROG"

        if re.search(r'\b(SHORT|SHRT|SHT)\b', combined_name_desc): is_short = True
        elif re.search(r'\b(LONG|LNG)\b', combined_name_desc): is_long = True

    has_puck = "PUCK" in combined_name_desc and style_int in [1, 13, 14]
    has_extra_thick = bool(re.search(r'\b(EXTRA\s*-?\s*THICK|EXTHK|ET)\b', combined_name_desc))
    has_extra_thin = bool(re.search(r'\b(EXTRA\s*-?\s*THIN)\b', combined_name_desc))

    prefix_parts = []
    if style_int == 6:
        if brand_str: prefix_parts.append(brand_str)
        if is_short: prefix_parts.append("S")
        elif is_long: prefix_parts.append("L")
    elif is_dd:
        if style_int == 9 or re.search(r'\b(?:EXEC|EXECUTIVE)\b', combined_name_desc):
            prefix_parts.append(f"DD EXEC {dd_pct}".strip())
            seg_size = "EXEC"
        else:
            match = re.search(r'\b(?:DOUBLE\s*-?\s*D|DD|OCCUPATIONAL|OCCUP|OCC|FT|D-?)(?:\s*SEG)?\s*(22|25|28|35|40|45)\b', combined_name_desc)
            seg_size = match.group(1) if match else "28"
            prefix_parts.append(f"DD{seg_size} {dd_pct}".strip())
    elif style_int in [10, 11, 12]:
        match = re.search(r'\b(\d+X\d+)\b', combined_name_desc)
        seg_size = match.group(1) if match else "7X28"
        prefix_parts.append(f"TRI {seg_size}")
    elif style_int in [2, 15]:
        match = re.search(r'\b(?:FT|D-?)(?:\s*SEG)?\s*(22|25|28|35|40|45)\b', combined_name_desc)
        seg_size = match.group(1) if match else "28"
        prefix_parts.append(f"FT{seg_size}")
    elif style_int in [3, 16]:
        match = re.search(r'\b(?:RND|ROUND)(?:\s*SEG)?\s*(\d+)', combined_name_desc)
        seg_size = match.group(1) if match else "28"
        prefix_parts.append(f"RND{seg_size}")
    elif style_int in [4]:
        prefix_parts.append("EXEC")
    elif style_int in [5, 17]:
        prefix_parts.append("ULTEX")
    elif style_int == 7:
        match = re.search(r'\b(22|25|28|35|40|45)\b', combined_name_desc)
        seg_size = match.group(1) if match else "28"
        prefix_parts.append(f"BLENDED {seg_size}")
    else:
        prefix_parts.append("FSV" if is_fsv else "SFSV")

    prefix_str = " ".join(prefix_parts)

    type_cascade_array = []
    if is_dd:
        if seg_size == "EXEC":
            base_dd = f"DD EXEC {dd_pct}".strip()
            type_cascade_array = [f"DOUBLE D EXEC {dd_pct}".strip(), f"OCCUP EXEC {dd_pct}".strip(), base_dd, base_dd]
        else:
            base_dd = f"DD{seg_size} {dd_pct}".strip()
            type_cascade_array = [f"DOUBLE D {seg_size} {dd_pct}".strip(), f"OCCUP {seg_size} {dd_pct}".strip(), base_dd, base_dd]
    elif style_int in [10, 11, 12]: type_cascade_array = [f"TRIFOCAL {seg_size}", f"TRI {seg_size}", f"TRI {seg_size}", f"TRI {seg_size}"]
    elif style_int in [2, 15]: type_cascade_array = [f"FLAT TOP {seg_size}", f"FT{seg_size}", f"FT{seg_size}", f"FT{seg_size}"]
    elif style_int in [3, 16]: type_cascade_array = [f"ROUND {seg_size}", f"RND{seg_size}", f"RND{seg_size}", f"RND{seg_size}"]
    elif style_int in [4]: type_cascade_array = ["EXECUTIVE", "EXEC", "EX", "EX"]
    elif style_int in [5, 17]: type_cascade_array = ["ULTEX", "ULTEX", "ULT", "ULT"]
    elif style_int == 7: type_cascade_array = [f"BLENDED {seg_size}", f"BLEND {seg_size}", f"BLND {seg_size}", f"BLND {seg_size}"]
    elif style_int == 6:
        if is_short: type_cascade_array = ["S", "S", "S", "S"]
        elif is_long: type_cascade_array = ["L", "L", "L", "L"]
        else: type_cascade_array = []
    else:
        base_sv = "FSV" if is_fsv else "SFSV"
        type_cascade_array = [base_sv, base_sv, base_sv, base_sv]

    tags = ["FIN" if is_fsv else "SF"]
    
    style_tag_map = {
        1: ["Single Vision"], 2: ["Flat Top", "Bifocal"], 3: ["Round", "Bifocal"], 4: ["Executive", "Bifocal"],
        5: ["Ultex", "Bifocal"], 6: ["Progressive"], 7: ["Blended Seg"], 8: ["Double Seg", "Flat Top"],
        9: ["Double Seg", "Executive"], 10: ["Trifocal", "TRI"], 11: ["Trifocal", "Executive", "TRI"], 12: ["Trifocal", "ED", "TRI"],
        13: ["Other SV", "Single Vision"], 14: ["Aspheric", "Single Vision"], 15: ["Aspheric", "Flat Top", "Bifocal"],
        16: ["Aspheric", "Round", "Bifocal"], 17: ["Aspheric", "Ultex", "Bifocal"], 18: ["Other Multi-focal"]
    }
    tags.extend(style_tag_map.get(style_int, ["Single Vision"]))
    
    if is_dd:
        if "Occupational" not in tags: tags.append("Occupational")
        if "Double D" not in tags: tags.append("Double D")
        if "Flat Top" not in tags and seg_size != "EXEC": tags.append("Flat Top")
        if "Bifocal" not in tags: tags.append("Bifocal")
        if seg_size and seg_size != "EXEC" and seg_size not in tags: tags.append(seg_size)
    else:
        if seg_size: tags.append(seg_size)
            
    if is_short: tags.append("Short")
    elif is_long: tags.append("Long")
    if has_puck: tags.append("PUCK")
    if has_extra_thick: tags.append("Extra-Thick")
    if has_extra_thin: tags.append("Extra-Thin")

    active_ar = None
    if is_universal_ar:
        coats_upper = [c.upper() for c in extracted_coats]
        ar_check_str = combined_name_desc + " " + " ".join(coats_upper)
        
        if any(x in ar_check_str for x in ['DURAVISION CHROME', 'DV CHROME', 'DVC']): active_ar = "DuraVision Chrome"
        elif any(x in ar_check_str for x in ['DURAVISION PLATINUM', 'DV PLATINUM', 'DVP']): active_ar = "DuraVision Platinum"
        elif any(x in ar_check_str for x in ['DURAVISION SILVER', 'DV SILVER', 'DVS']): active_ar = "DuraVision Silver"
        elif any(x in ar_check_str for x in ['DURAVISION GOLD', 'DV GOLD', 'DVG']): active_ar = "DuraVision Gold"
        elif 'VELA' in ar_check_str: active_ar = "Vela"
        elif any(x in ar_check_str for x in ['CRIZAL', 'CZ']): active_ar = "Crizal"
        elif any(x in ar_check_str for x in ['HOYA PREMIUM', 'HOYA PREM']): active_ar = "Hoya Premium"
        elif 'ECP' in ar_check_str: active_ar = "ECP"
        elif any(x in ar_check_str for x in ['ULTRACLEAN', 'ULTRACLN']): active_ar = "Ultraclean"
        elif any(x in ar_check_str for x in ['HMC', 'BMC', 'SHMC', ' AR ', ' A/R ', 'ANTI-REFLECTIVE']): active_ar = "A/R"

    if active_ar:
        tags.append("A/R")
        if "DuraVision" in active_ar and "DuraVision" not in tags:
            tags.append("DuraVision")
        if active_ar not in tags:
            tags.append(active_ar)

    if "UV PROTECT" in combined_name_desc or 'UV Protect' in techs_found or any("UV PROTECT" in c.upper() for c in extracted_coats):
        if "UV Protect" not in tags: tags.append("UV Protect")
        if "PLUS PLATINUM" in combined_name_desc: tags.append("UV Protect Plus Platinum")
        elif "PLUS CHROME" in combined_name_desc: tags.append("UV Protect Plus Chrome")
        elif "PLUS SILVER" in combined_name_desc: tags.append("UV Protect Plus Silver")
        elif "PLUS GOLD" in combined_name_desc: tags.append("UV Protect Plus Gold")

    if 'UVRI' in techs_found and 'UVRI' not in tags:
        tags.append('UVRI')

    color_keywords = ['PRO GRAY', 'PRO GREY', 'PRO BROWN', 'EXTRA-GRAY', 'EXTRA-GREY', 'EXTRA GRAY', 'EXTRA GREY', 'EXTRAGRAY', 'EXTRAGREY', 'GRAY', 'GREY', 'GRY', 'BROWN', 'BRN', 'GREEN', 'GRN', 'G15', 'G-15', 'PIONEER', 'PIONEEER', 'PIO', 'EMERALD', 'BURGUNDY', 'BURG', 'BRG', 'PINK', 'PNK', 'BLUE', 'BLU', 'PURPLE', 'PURP', 'PLUM', 'YELLOW', 'YEL', 'YLW', 'ROSE', 'ROS', 'ORANGE']
    
    c_pad_desc = f" {combined_name_desc} ".replace('-', ' ').replace('/', ' ').upper()
    c_pad_color = c_pad_desc
    for bf_word in ['BLUE FILTER', 'BLUE BLOCKER', 'BLUE PROTECT', 'BLUE GUARD', 'BLUEGUARD', 'BLUEP', 'UV420', 'FUL PROTECT', 'GUARD']:
        c_pad_color = c_pad_color.replace(bf_word, '')

    has_color_word = any(x in c_pad_color for x in [f" {w} " for w in color_keywords] + [f" {w}" for w in color_keywords])

    is_photochromic = any(t in techs_found or t.upper() in combined_name_desc for t in [
        'Transitions', 'PhotoFusion X', 'PhotoFusion', 'Sensitivity', 'Sensity',
        'SunSync', 'Quick-Change', 'Xtra-Active', 'Photochromic', 'LifeRx'
    ])
    
    is_polarized = any(t in techs_found or t.upper() in combined_name_desc for t in [
        'Polarized', 'NuPolar', 'TruPolar', 'SunRx', 'Coppertone'
    ])
    
    tech_list_full = []
    
    if has_color_word and not is_photochromic and not is_polarized:
        tags.append("Pre-Tint")
        tech_list_full.append("Pre-Tint")

    active_blue = None
    if is_zeiss:
        if 'BLUE PROTECT' in combined_name_desc or 'BLUEP' in combined_name_desc:
            active_blue = "Blue Protect"
        elif any(x in combined_name_desc for x in ['BLUEGUARD', 'BG', 'HEV', 'UV420']) or any(t in techs_found for t in ['HEV', 'BlueGuard', 'Blue Filter']):
            active_blue = "BlueGuard"
    else:
        if 'BLUEGUARD' in combined_name_desc or 'BLUE GUARD' in combined_name_desc: active_blue = "BlueGuard"
        elif 'BLUE PROTECT' in combined_name_desc: active_blue = "Blue Protect"
        elif any(x in combined_name_desc for x in ['HEV', 'UV420']) or 'HEV' in techs_found: active_blue = "HEV"
        elif 'FUL PROTECT' in combined_name_desc or 'FUL-PROTECT' in combined_name_desc or 'Ful-Protect' in techs_found: active_blue = "Ful-Protect"
        elif 'BLUE FILTER' in combined_name_desc or 'Blue Filter' in techs_found: active_blue = "Blue Filter"
        
    if active_blue:
        tags.append("Blue Filter")
        if active_blue not in tags: tags.append(active_blue)
    
    has_photo = False
    if 'PhotoFusion X' in techs_found or 'PhotoFusion' in techs_found or 'PHOTOFUSION X' in combined_name_desc or 'PHOTOFUSION' in combined_name_desc:
        if 'EXTRA GRAY' in c_pad_color or ' EXTRA ' in c_pad_color or ' EXG ' in c_pad_color:
            tech_list_full.append('PhotoFusion X Extra')
        else:
            tech_list_full.append('PhotoFusion X')
        has_photo = True
        
    for t in ['Xtra-Active', 'Quick-Change', 'SunSync', 'Sensity', 'Transitions', 'LifeRx']:
        if t in techs_found or t.upper() in combined_name_desc:
            tech_list_full.append(t)
            has_photo = True
            
    if not has_photo and ('Photochromic' in techs_found or 'PHOTOCHROMIC' in combined_name_desc):
        tech_list_full.append("Photochromic")
        has_photo = True
        
    if has_photo:
        tags.append("Photochromic")
        
    has_polar = False
    for t in ['NuPolar', 'TruPolar', 'SunRx', 'Coppertone', 'Polarized']:
        if t in techs_found or t.upper() in combined_name_desc:
            tech_list_full.append(t)
            has_polar = True
            break
            
    if has_polar: tags.append("Polarized")
    if active_blue: tech_list_full.append(active_blue)
    
    if "CLEARVIEW" in combined_name_desc:
        tech_list_full.append("ClearView")
        tags.append("ClearView")

    is_org = "ORG" in combined_name_desc
    is_asph = any(x in combined_name_desc for x in [' AS ', ' ASP ', ' ASPHERIC ', ' ASPH ']) and style_int not in [6, 7]

    lms_mat_str = ""
    c_mat = str(resolved_mat).upper()
    if "POLYCARBONATE" in c_mat: lms_mat_str = "POLY"
    elif "TRIVEX" in c_mat: lms_mat_str = "TRV"
    elif "CR-39" in c_mat: lms_mat_str = "CR-39"
    elif "1.56" in c_mat: lms_mat_str = "1.56"
    elif "1.60" in c_mat: lms_mat_str = "1.60"
    elif "1.67" in c_mat: lms_mat_str = "1.67"
    elif "1.74" in c_mat: lms_mat_str = "1.74"
    if "ULTRA" in c_mat or "FLEX" in c_mat: lms_mat_str = "UF"

    def run_ratchet(target_len):
        mat_cascades = {
            "POLY": ["POLYCARBONATE", "POLYCARB", "POLY", "PY", "PY"],
            "CR-39": ["CR-39", "CR-39", "CR39", "CR", "CR"],
            "TRV": ["TRIVEX", "TRIVEX", "TRVX", "TX", "TX"],
            "1.56": ["1.56", "1.56", "1.56", "1.56", "156"],
            "1.60": ["1.60", "1.60", "1.60", "1.60", "160"],
            "1.67": ["1.67", "1.67", "1.67", "1.67", "167"],
            "1.74": ["1.74", "1.74", "1.74", "1.74", "174"],
            "UF": ["ULTRA-FLEX", "ULTFLX", "UF", "UF", "UF"]
        }
        tech_cascades = {
            "Transitions": ["TRANSITIONS", "TRANS", "TRN", "TRN"],
            "PhotoFusion X Extra": ["PHOTOFUSION X EXTRA", "PFX EXTRA", "PFX EXG", "PFX EXG"],
            "PhotoFusion X": ["PHOTOFUSION X", "PFX", "PFX", "PFX"],
            "Quick-Change": ["QUICK-CHANGE", "QCHANGE", "QC", "QC"],
            "Xtra-Active": ["XTRA-ACTIVE", "XTRA", "XA", "XA"],
            "Sensity": ["SENSITY", "SENSITY", "SENS", "SENS"],
            "LifeRx": ["LIFERX", "LIFERX", "LRX", "LRX"],
            "NuPolar": ["NUPOLAR", "NUPOLAR", "POLZ", "POLZ"],
            "TruPolar": ["TRUPOLAR", "TRUPOLAR", "POLZ", "POLZ"],
            "SunRx": ["SUNRX", "SUNRX", "SUN", "SUN"],
            "Coppertone": ["COPPERTONE", "COPPER", "CT", "CT"],
            "Polarized": ["POLARIZED", "POLAR", "POLZ", "POLZ"],
            "BlueGuard": ["BLUEGUARD", "BLUEGUARD", "BG", "BG"],
            "Blue Protect": ["BLUE PROTECT", "BLUEP", "BP", "BP"],
            "Ful-Protect": ["FUL-PROTECT", "FUL-PRO", "FUL", "FUL"],
            "HEV": ["UV420", "UV420", "HEV", "HEV"],
            "Blue Filter": ["BLUE FILTER", "BLUEF", "BF", "BF"],
            "Photochromic": ["PHOTOCHROMIC", "PHOTO", "PHT", "PHT"],
            "Pre-Tint": ["PRE-TINT", "TINT", "TINT", "TINT"],
            "PermaGuard": ["PERMAGUARD", "PERMA", "PG", "PG"],
            "UltraTough": ["ULTRATOUGH", "U-TOUGH", "UT", "UT"],
            "Younger Hardcoat": ["YOUNGERHC", "YHC", "YHC", "YHC"],
            "Ultra-Shield": ["ULTRA-SHIELD", "U-SHIELD", "US", "US"],
            "ClearView": ["CLEARVIEW", "CLRVIEW", "CV", "CV"]
        }
        ar_cascades = {
            "DuraVision Chrome": ["DURAVISION CHROME", "DV CHROME", "DVC", "DVC"],
            "DuraVision Platinum": ["DURAVISION PLATINUM", "DV PLAT", "DVP", "DVP"],
            "DuraVision Silver": ["DURAVISION SILVER", "DV SILV", "DVS", "DVS"],
            "DuraVision Gold": ["DURAVISION GOLD", "DV GOLD", "DVG", "DVG"],
            "Vela": ["VELA AR", "VELA", "VELA", "VELA"],
            "Crizal": ["CRIZAL AR", "CRIZAL", "CZ", "CZ"],
            "Hoya Premium": ["HOYA PREMIUM", "HOYA PREM", "HOYA", "HOYA"],
            "ECP": ["ECP AR", "ECP", "ECP", "ECP"],
            "Ultraclean": ["ULTRACLEAN", "ULTRACLN", "UCLN", "UCLN"],
            "A/R": ["A/R", "A/R", "AR", "AR"]
        }
        
        puck_cascades = ["PUCK", "PUK", "PK", ""]
        et_cascades = ["EXTRA-THICK", "EXTHK", "ET", "ET"]
        ethin_cascades = ["EXTRA-THIN", "EX-THIN", "ETHIN", "ETHIN"]
        
        state_org = 1 if is_org else 0
        state_asph = 1 if is_asph else 0
        state_type = 0
        state_tech = 0
        state_mat = 0
        state_puck = 0 if has_puck else 3
        state_et = 0 if has_extra_thick else 4
        state_ethin = 0 if has_extra_thin else 4
        state_ar = 0 if active_ar else 4
        b_str = brand_str
        
        working_techs = list(tech_list_full)
        working_type_array = list(type_cascade_array)
        
        def build():
            parts = []
            if style_int == 6:
                if b_str: parts.append(b_str)
                if working_type_array: parts.append(working_type_array[min(state_type, len(working_type_array)-1)])
            else:
                if working_type_array: parts.append(working_type_array[min(state_type, len(working_type_array)-1)])
                if b_str: parts.append(b_str)
            if state_org == 1: parts.append("ORG")
            
            if lms_mat_str:
                m_arr = mat_cascades.get(lms_mat_str, [lms_mat_str])
                parts.append(m_arr[min(state_mat, len(m_arr)-1)])
            
            if state_asph == 1: parts.append("AS")
            
            for t in working_techs:
                t_arr = tech_cascades.get(t, [t])
                parts.append(t_arr[min(state_tech, len(t_arr)-1)])
                
            if state_et < 4: parts.append(et_cascades[state_et])
            if state_ethin < 4: parts.append(ethin_cascades[state_ethin])
                
            if state_ar < 4 and active_ar:
                a_arr = ar_cascades.get(active_ar, ["A/R", "A/R", "AR", "AR"])
                parts.append(a_arr[min(state_ar, len(a_arr)-1)])
                
            if state_puck < 3: parts.append(puck_cascades[state_puck])
                
            clean_parts = []
            for p in parts:
                if p and p not in clean_parts:
                    clean_parts.append(p)
            return " ".join(clean_parts).replace("  ", " ").strip()

        if len(build()) <= target_len: return build()
        if "ClearView" in working_techs: working_techs.remove("ClearView")
        if len(build()) <= target_len: return build()
        
        if target_len <= 15 and has_puck:
            state_puck = 2
            if len(build()) <= target_len: return build()
            state_puck = 3
            if len(build()) <= target_len: return build()
        
        for attr, val in [
            ('org', 0), ('asph', 0), ('type', 1), ('tech', 1), ('mat', 1), ('ar', 1),
            ('type', 2), ('tech', 2), ('mat', 2), ('ar', 2), ('tech', 3), ('mat', 3), ('mat', 4)
        ]:
            if attr == 'org': state_org = val
            elif attr == 'asph': state_asph = val
            elif attr == 'type': state_type = val
            elif attr == 'tech': state_tech = val
            elif attr == 'mat': state_mat = val
            elif attr == 'ar' and active_ar: state_ar = val
            if len(build()) <= target_len: return build()
            
        if has_extra_thick: state_et = 1
        if len(build()) <= target_len: return build()
        if has_extra_thin: state_ethin = 1
        if len(build()) <= target_len: return build()
        
        if has_extra_thick: state_et = 2
        if len(build()) <= target_len: return build()
        if has_extra_thin: state_ethin = 2
        if len(build()) <= target_len: return build()
        
        if active_ar: state_ar = 3
        if len(build()) <= target_len: return build()
            
        while len(working_techs) > 0:
            working_techs.pop()
            if len(build()) <= target_len: return build()
            
        if has_extra_thick: state_et = 3
        if has_extra_thin: state_ethin = 3
        if len(build()) <= target_len: return build()
        
        if has_extra_thick: state_et = 4
        if has_extra_thin: state_ethin = 4
        if len(build()) <= target_len: return build()
        
        if has_puck:
            for p_st in [1, 2, 3]:
                state_puck = p_st
                if len(build()) <= target_len: return build()
        
        return build()[:target_len].strip()

    brief_desc = run_ratchet(15)
    long_desc = run_ratchet(32)

    clean_desc = raw_desc
    clean_desc = re.sub(r'\b(?:HARD RESIN|RESIN|ORG|PLASTIC|STANDARD PLASTIC|HIGH-INDEX|HIGH INDEX|MID-INDEX|MID INDEX|HA)\b', '', clean_desc, flags=re.IGNORECASE)
    clean_desc = re.sub(r'\b(?:SINGLE VISON|SINGLE VISION|SV)\b', '', clean_desc, flags=re.IGNORECASE)
    clean_desc = re.sub(r'\bBLUE\s*GUARD\b', 'BLUEGUARD', clean_desc, flags=re.IGNORECASE)
    clean_desc = re.sub(r'\b(?:EXTRA\s*-?\s*THICK|EXTHK|ET)\b', '__ET__', clean_desc, flags=re.IGNORECASE)
    clean_desc = re.sub(r'\b(?:EXTRA\s*-?\s*THIN)\b', '__E_THIN__', clean_desc, flags=re.IGNORECASE)
    clean_desc = re.sub(r'(?:^|\s)(?:1\.\d{1,3}|0?\.\d{1,3})(?=\s|$)', ' ', clean_desc)
    clean_desc = re.sub(r'\b(?:PUCK|PUK|PK)\b', '', clean_desc, flags=re.IGNORECASE)
    clean_desc = re.sub(r'\(\s*MR-[\w\+\-]+\s*\)', '', clean_desc, flags=re.IGNORECASE)

    for word in ['PRO GRAY', 'PRO GREY', 'PRO BROWN', 'EXTRA-GRAY', 'EXTRA-GREY', 'EXTRA GRAY', 'EXTRA GREY', 'EXTRAGRAY', 'EXTRAGREY', 'XTRA-ACTIVE', 'XTRA ACTIVE', 'XTRA', 'GRAY', 'GREY', 'GRY', 'BROWN', 'BRN', 'GREEN', 'GRN', 'G15', 'G-15', 'PIONEER', 'PIONEEER', 'PIO', 'EMERALD', 'BURGUNDY', 'BURG', 'BRG', 'PINK', 'PNK', 'BLUE', 'BLU', 'PURPLE', 'PURP', 'PLUM', 'YELLOW', 'YEL', 'YLW', 'ROSE', 'ROS', 'ORANGE', 'PRO', 'EXTRA', 'XA', 'EXG', 'POLYCARBONATE', 'POLYCARB', 'POLY', 'TRIVEX', 'TRV', 'CR39', 'CR-39', 'RESIN', 'HARD RESIN', 'PLASTIC', 'STANDARD PLASTIC', 'MR-8', 'MR-8+', 'MR8', 'MR-7', 'MR7', 'MR-10', 'MR10', 'MR-74', 'MR74', 'HIGH-INDEX', 'HIGH INDEX', 'MID-INDEX', 'MID INDEX']:
        clean_desc = re.sub(rf'\b{word}(?:\s*[-]?\s*[123ABC])?\b', '', clean_desc, flags=re.IGNORECASE)

    for word in ['HC', 'SR', 'SHMC', 'PG', 'UT', 'YHC', 'US', 'UC', 'UNCOATED', 'THICK', 'THIN', 'HCT', 'YOUNGERHC', 'YOUNGER HARDCOAT', 'YOUNGER HARD COAT', 'YOUNGER HARD-COAT', 'PERMAGUARD', 'PERMA-GUARD', 'PERMA GUARD', 'ULTRATOUGH', 'ULTRA-TOUGH', 'ULTRA TOUGH', 'ULTRASHIELD', 'ULTRA-SHIELD', 'ULTRA SHIELD', 'HARDCOAT', 'HARD COAT', 'HARD-COAT', 'HARD', 'DOUBLE D', 'OCCUPATIONAL', 'OCCUP', 'OCC', 'DD', 'UVRI']:
        clean_desc = re.sub(rf'\b{word}\b', '', clean_desc, flags=re.IGNORECASE)

    clean_desc = re.sub(r'\bD\d{2,3}\b', '', clean_desc, flags=re.IGNORECASE)
    clean_desc = re.sub(r'\b\d{2,3}MM\b', '', clean_desc, flags=re.IGNORECASE)
    clean_desc = re.sub(r'\bUV400\b', 'UV', clean_desc, flags=re.IGNORECASE)

    clean_desc = clean_desc.replace('__ET__', 'EXTRA-THICK')
    clean_desc = clean_desc.replace('__E_THIN__', 'EXTRA-THIN')

    mfg_clean_str = str(sample_row.get('MFG', '')).strip()
    strip_list = prefix_parts + [mfg_clean_str, "PAL", "PROGRESSIVE", "PROG", "TRIFOCAL", "TRI", "BIFOCAL", "FLAT TOP", "SHORT", "SHRT", "SHT", "LONG", "LNG", "FSV", "SFSV", "SF", "SEMI-FINISHED", "SEMI FINISHED", "DOUBLE D", "OCCUPATIONAL", "OCCUP", "OCC", "DD", "SV", "BLENDED", "BLEND", "BLND"]

    if is_dd and dd_pct: strip_list.append(dd_pct)
    if seg_size: strip_list.append(str(seg_size))

    for p_word in strip_list:
        if p_word and len(p_word) > 1:
            clean_desc = re.sub(rf'\b{re.escape(p_word)}\b', '', clean_desc, flags=re.IGNORECASE)

    clean_desc = re.sub(r'\s+', ' ', clean_desc).strip()

    mat_tag = str(resolved_mat).strip()
    mat_tag = re.sub(r'\(\s*MR-[\w\+\-]+\s*\)', '', mat_tag, flags=re.IGNORECASE).strip()

    if resolved_mat:
        clean_desc = f"{prefix_str} {mat_tag} {clean_desc}".replace("  ", " ").strip()
    else:
        clean_desc = f"{prefix_str} {clean_desc}".replace("  ", " ").strip()

    if has_puck:
        clean_desc = f"{clean_desc} PUCK".strip()

    # ----- Synonym Injection for Search Index ----- #
    if "A/R" in tags or "AR" in tags or active_ar:
        tags = [t for t in tags if t not in ["SR", "HC", "Hardcoat", "SRAR"]]
        
    synonyms = set()
    if is_fsv:
        synonyms.update(["FSV", "Finished"])
        if "Single Vision" in tags: synonyms.add("SV")
    else:
        synonyms.update(["SF", "Semi-Finished", "Semi Finished"])
        if "Single Vision" in tags: synonyms.update(["SV", "SFSV"])
        
    if style_int == 6:
        synonyms.update(["PAL", "Prog"])
        if brand_str and brand_str != "PROG":
            synonyms.add(smart_casing(brand_str, techs_found))
            
    if style_int in [2, 15] and seg_size:
        synonyms.update([f"FT{seg_size}", f"FT-{seg_size}", f"ST{seg_size}", f"ST-{seg_size}"])
        
    if "UVRI" in tags or "UVRI" in techs_found: synonyms.add("UV")
    if "BlueGuard" in tags: synonyms.add("BG")
    if "Blue Filter" in tags: synonyms.add("BF")
    if "Blue Protect" in tags: synonyms.add("BP")
    
    # ----- Photochromic Expansions ----- #
    if "Photochromic" in tags or is_photochromic:
        synonyms.add("Photo")
        
        pfx_match = any(x in techs_found for x in ['PhotoFusion X', 'PhotoFusion X Extra', 'PhotoFusion']) or 'PHOTOFUSION' in combined_name_desc
        if pfx_match:
            synonyms.update(["PhotoFusion X", "Photo Fusion X", "PhotoFusion", "PFX"])
            
        trn_match = 'Transitions' in techs_found or 'TRANSITIONS' in combined_name_desc
        if trn_match:
            synonyms.update(["Transition", "Trans"])
            if any(x in combined_name_desc for x in ['GEN S', 'GENS', 'GEN-S']):
                synonyms.update(["TGNS", "TGEN-S"])

        qc_match = 'Quick-Change' in techs_found or 'QUICK-CHANGE' in combined_name_desc or 'QUICK CHANGE' in combined_name_desc
        if qc_match:
            synonyms.update(["Quick-Change", "Quick Change", "QC"])
            
        if 'Sensity' in techs_found or 'SENSITY' in combined_name_desc:
            synonyms.add("Sensity")
        if 'LifeRx' in techs_found or 'LIFERX' in combined_name_desc:
            synonyms.add("LifeRx")
        if 'SunSync' in techs_found or 'SUNSYNC' in combined_name_desc:
            synonyms.add("SunSync")
        if 'Xtra-Active' in techs_found or 'XTRA-ACTIVE' in combined_name_desc or 'XTRA ACTIVE' in combined_name_desc:
            synonyms.update(["Xtra-Active", "Xtra Active"])

    # ----- Material, Index, and UltraFlex Expansion ----- #
    c_mat_syn = str(resolved_mat).upper()
    
    is_uf = "ULTRA" in c_mat_syn or "FLEX" in c_mat_syn or "UF" in c_mat_syn or "ULTFLX" in c_mat_syn or "ULTRAFLEX" in combined_name_desc
    if is_uf:
        synonyms.update(["Ultra Flex", "Ultra-Flex", "UF"])
        
    if "CR-39" in c_mat_syn or "CR39" in c_mat_syn or "1.50" in c_mat_syn:
        synonyms.update(["CR-39", "CR39", "Plastic", "1.50", "150"])
    elif "POLY" in c_mat_syn or "1.59" in c_mat_syn:
        synonyms.update(["Polycarbonate", "Polycarb", "Poly", "1.59", "159"])
    elif "TRIVEX" in c_mat_syn or "1.53" in c_mat_syn:
        synonyms.update(["Trivex", "1.53", "153"])
    elif "1.56" in c_mat_syn:
        synonyms.update(["1.56", "156", "Mid-Index", "Mid Index"])
    elif "1.60" in c_mat_syn:
        synonyms.update(["1.60", "160", "High Index", "High-Index"])
        # Strict isolation for UltraFlex vs Standard MR-8
        if is_uf or "MR-8+" in c_mat_syn or "MR8+" in c_mat_syn:
            synonyms.update(["MR-8+", "MR8+"])
        elif "MR-8" in c_mat_syn or "MR8" in c_mat_syn:
            synonyms.update(["MR-8", "MR8"])
    elif "1.67" in c_mat_syn:
        synonyms.update(["1.67", "167", "High Index", "High-Index"])
        if "MR-7" in c_mat_syn or "MR7" in c_mat_syn:
            synonyms.update(["MR-7", "MR7"])
        if "MR-10" in c_mat_syn or "MR10" in c_mat_syn:
            synonyms.update(["MR-10", "MR10"])
    elif "1.74" in c_mat_syn:
        synonyms.update(["1.74", "174", "High Index", "High-Index", "MR-74", "MR74"])
    
    for syn in synonyms:
        if syn not in tags: tags.append(syn)

    return clean_desc, brief_desc, long_desc, tags, active_ar, prefix_str, prefix_parts, seg_size
    
def aggregate_specs(group_df, is_fsv, extracted_seg_size=""):
    specifications = []
    all_diameters = set()
    
    for _, row_data in group_df.iterrows():
        r_dict = {k: ("" if pd.isna(v) else v) for k, v in row_data.items()}
        
        _, opc_color_code, opc_coat_code, _ = map_lens_tech(r_dict, row_mode=True)
        
        raw_dia = safe_float(r_dict.get("DIAMETER", 0))
        dia_int = int(raw_dia) if raw_dia > 0 else 0
        dia_str = str(dia_int) if dia_int > 0 else ""
        if dia_int > 0:
            all_diameters.add(dia_int)
            
        r_opc = str(r_dict.get("OPCR", "")).strip()
        l_opc = str(r_dict.get("OPCL", "")).strip()
        if r_opc.upper() in ["NONE", "N/A", "NA", "NAN"]: r_opc = ""
        if l_opc.upper() in ["NONE", "N/A", "NA", "NAN"]: l_opc = ""
        if r_opc.endswith(".0"): r_opc = r_opc[:-2]
        if l_opc.endswith(".0"): l_opc = l_opc[:-2]
        
        # ----- Singular (S) if only one side is populated or both sides share the identical barcode ----- #
        valid_opc_s = r_opc or l_opc
        if (r_opc and not l_opc) or (l_opc and not r_opc) or (r_opc and r_opc == l_opc):
            opc_flag = "S"
        elif r_opc and l_opc and r_opc != l_opc:
            opc_flag = "SPLIT"
        else:
            opc_flag = "NONE"
            
        b_val = safe_float(r_dict.get("SPH/BASE", 0.0))
        c_val = safe_float(r_dict.get("CYL/ADD", 0.0))
        b_str = f"{b_val:+.2f}"
        c_str = f"{c_val:+.2f}"
        
        if is_fsv:
            spec_base = {
                "SPH": b_str,
                "CYL": c_str,
                "Center Thick": safe_float(r_dict.get("CT", 0.0)),
                "Edge Thick": safe_float(r_dict.get("ET", 0.0))
            }
        else:
            r_front = safe_float(r_dict.get("RADIUSF", 0.0))
            r_back = safe_float(r_dict.get("RADIUSB", 0.0))
            true_front = round(530.0 / r_front, 2) if r_front > 0 else 0.0
            true_back = round(-530.0 / r_back, 2) if r_back > 0 else 0.0
            sag_val = round(r_front - math.sqrt(r_front**2 - 25.0**2), 3) if r_front > 25.0 else 0.0
            
            raw_seg_w = str(r_dict.get("SEGW", "")).strip()
            if not raw_seg_w and extracted_seg_size:
                raw_seg_w = str(extracted_seg_size)
                
            spec_base = {
                "BASE": b_str,
                "ADD": c_str,
                "Front RAD": r_front,
                "Back RAD": r_back,
                "Front TC": true_front,
                "Back TC": true_back,
                "SAG": sag_val,
                "Center Thick": safe_float(r_dict.get("CT", 0.0)),
                "Edge Thick": safe_float(r_dict.get("ET", 0.0)),
                "Inset": str(r_dict.get("INSET", "")),
                "Drop": str(r_dict.get("DROP", "")),
                "PRP Out": str(r_dict.get("PRPOUT", "")),
                "PRP Up": str(r_dict.get("PRPUP", "")),
                "Seg Width": raw_seg_w,
                "Seg Thick": str(r_dict.get("SEGT", ""))
            }
            
        existing_spec = None
        for exist_s in specifications:
            if is_fsv:
                if exist_s.get("SPH") == b_str and exist_s.get("CYL") == c_str:
                    existing_spec = exist_s
                    break
            else:
                if exist_s.get("BASE") == b_str and exist_s.get("ADD") == c_str:
                    if abs(exist_s.get("Front TC", 0.0) - spec_base["Front TC"]) <= 0.05:
                        existing_spec = exist_s
                        break
                        
        target_spec = existing_spec if existing_spec else spec_base
        if not existing_spec:
            target_spec["Diameters"] = []
            target_spec["OPC"] = {}
            specifications.append(target_spec)
            
        if dia_int > 0 and dia_int not in target_spec["Diameters"]:
            target_spec["Diameters"].append(dia_int)
            target_spec["Diameters"].sort()
            
        if dia_str and opc_flag == "S" and valid_opc_s:
            k = f"{dia_str}_S_{opc_color_code}_{opc_coat_code}"
            target_spec["OPC"][k] = valid_opc_s
        elif dia_str and opc_flag == "SPLIT":
            if r_opc:
                target_spec["OPC"][f"{dia_str}_R_{opc_color_code}_{opc_coat_code}"] = r_opc
            if l_opc:
                target_spec["OPC"][f"{dia_str}_L_{opc_color_code}_{opc_coat_code}"] = l_opc

    # ----- FIN Power Ranges or SF Base Curves ----- #
    rollup_meta = {}
    if is_fsv:
        raw_sph = pd.to_numeric(group_df['SPH/BASE'], errors='coerce')
        raw_cyl = pd.to_numeric(group_df['CYL/ADD'], errors='coerce').fillna(0.0)
        valid_mask = raw_sph.notna()
        sph_vals = raw_sph[valid_mask]
        cyl_vals = raw_cyl[valid_mask]
        
        def fmt_closest(v_series, is_minus=False):
            if v_series.empty: return ""
            arr = sorted(v_series.unique(), key=float)
            if len(arr) == 1: return f"{arr[0]:+.2f}"
            return f"{arr[-1]:+.2f} to {arr[0]:+.2f}" if is_minus else f"{arr[0]:+.2f} to {arr[-1]:+.2f}"
            
        if not sph_vals.empty:
            m_sph = sph_vals[(sph_vals <= 0) & (cyl_vals == 0.0)]
            p_sph = sph_vals[(sph_vals > 0) & (cyl_vals == 0.0)]
            m_cyl = sph_vals[(sph_vals <= 0) & (cyl_vals != 0.0)]
            m_cyl_c = cyl_vals[(sph_vals <= 0) & (cyl_vals != 0.0)]
            p_cyl = sph_vals[(sph_vals > 0) & (cyl_vals != 0.0)]
            p_cyl_c = cyl_vals[(sph_vals > 0) & (cyl_vals != 0.0)]
            
            if not m_sph.empty: rollup_meta["PowerRange_MinusSph"] = fmt_closest(m_sph, is_minus=True)
            if not p_sph.empty: rollup_meta["PowerRange_PlusSph"] = fmt_closest(p_sph, is_minus=False)
            if not m_cyl.empty: rollup_meta["PowerRange_MinusCyl"] = f"{fmt_closest(m_cyl, is_minus=True)} SPH | {fmt_closest(m_cyl_c, is_minus=True)} CYL"
            if not p_cyl.empty: rollup_meta["PowerRange_PlusCyl"] = f"{fmt_closest(p_cyl, is_minus=False)} SPH | {fmt_closest(p_cyl_c, is_minus=True)} CYL"
    else:
        curves = sorted(pd.to_numeric(group_df['SPH/BASE'], errors='coerce').dropna().unique(), key=lambda x: abs(x))
        rollup_meta["NominalBaseCurves"] = ", ".join([f"{c:+.2f}" for c in curves])
        
    return specifications, sorted(list(all_diameters)), rollup_meta
    
def smart_casing(text, techs_list):
    t = str(text).upper()
    techs_upper = [str(x).upper() for x in techs_list]
    
    t = re.sub(r'\bPHOTOCHROMIC\b', 'PHOTOFUSION X', t)
    t = re.sub(r'\bPHOTOFUSION(?!\s*X)\b', 'PHOTOFUSION X', t)
    
    if 'NUPOLAR' in techs_upper:
        t = re.sub(r'\b(POLARIZED|POLAR|POLZ)\b', 'NUPOLAR', t)
    elif 'TRUPOLAR' in techs_upper:
        t = re.sub(r'\b(POLARIZED|POLAR|POLZ)\b', 'TRUPOLAR', t)
        
    t = t.title()

    protections = {
        r'\bGt2\b': 'GT2', r'\bCr-39\b': 'CR-39', r'\bCr39\b': 'CR39',
        r'\bA/R\b': 'A/R', r'\bA/r\b': 'A/R', r'\bNupolar\b': 'NuPolar', r'\bTrupolar\b': 'TruPolar',
        r'\bPhotofusion X\b': 'PhotoFusion X', r'\bPhotofusion\b': 'PhotoFusion',
        r'\bSunsync\b': 'SunSync', r'\bLiferx\b': 'LifeRx', r'\bSunrx\b': 'SunRx',
        r'\bHev\b': 'HEV', r'\bFsv\b': 'FSV', r'\bSfsv\b': 'SFSV', r'\bSf\b': 'SF',
        r'\bFt(\d+)\b': r'FT\1', r'\bDd(\d+)\b': r'DD\1', r'\bRnd(\d+)\b': r'RND\1', r'\bExg\b': 'EXG',
        r'\bUv\b': 'UV', r'\bUv(\d+)\b': r'UV\1', r'\bAr\b': 'AR', r'\bPg\b': 'PG',
        r'\bUt\b': 'UT', r'\bYhc\b': 'YHC', r'\bUs\b': 'US', r'\bHc\b': 'HC', r'\bUc\b': 'UC', r'\bSr\b': 'SR',
        r'\bBlueguard\b': 'BlueGuard', r'\bBlueprotect\b': 'BlueProtect', r'\bPfx\b': 'PFX',
        r'\bPal\b': 'PAL', r'\bMm\b': 'MM', r'\bExec\b': 'EXEC', r'\bUltex\b': 'ULTEX',
        r'\bAsph\b': 'ASPH', r'\bSv\b': 'SV', r'(?i)\b(\d+)x(\d+)\b': r'\1X\2',
        r'\bUvprotect\b': 'UVProtect', r'\bClearview\b': 'ClearView',
        r'\bFul-Protect\b': 'Ful-Protect', r'\bPuck\b': 'PUCK',
        r'\bTri\b': 'TRI', r'\bRnd\b': 'RND', r'\bFt\b': 'FT', r'\bAs\b': 'AS',
        r'\bHmc\b': 'HMC', r'\bHmc\+\b': 'HMC+', r'\bBmc\b': 'BMC', r'\bHct\b': 'HCT',
        r'\bMr-7\b': 'MR-7', r'\bMr-8\b': 'MR-8', r'\bMr-8\+\b': 'MR-8+', r'\bMr-10\b': 'MR-10', r'\bMr-74\b': 'MR-74',
        r'\bSunlens\b': 'SunLens', r'\bDuravision\b': 'DuraVision', r'\bUvri\b': 'UVRI'
    }
    
    for pat, repl in protections.items():
        t = re.sub(pat, repl, t)
        
    return t

# ----- INPUT HANDLERS ----- #

def file_mgr_input(ch, ctx):
    ctx['warning_msg'] = ""
    
    if ch == 'UP': ctx['lpage'] = (ctx['lpage'] - 1 + ctx['max_lpage']) % ctx['max_lpage']
    elif ch == 'DOWN': ctx['lpage'] = (ctx['lpage'] + 1) % ctx['max_lpage']
    elif ch == 'PGUP': ctx['lpage'] = max(0, ctx['lpage'] - 5)
    elif ch == 'PGDN': ctx['lpage'] = min(ctx['max_lpage'] - 1, ctx['lpage'] + 5)
    elif ch == 'LEFT': ctx['rpage'] = (ctx['rpage'] - 1 + ctx['max_rpage']) % ctx['max_rpage']
    elif ch == 'RIGHT': ctx['rpage'] = (ctx['rpage'] + 1) % ctx['max_rpage']
    elif ch == 'ESC': 
        sys.stdout.write("\033[?25l")
        return "EXIT"
    elif ch in ['BACKSPACE', '\x08', '\x7f', 'DEL']:
        ctx['user_input'] = ctx['user_input'][:-1]
    elif ch in ['\r', '\n']:
        cmd = ctx['user_input'].strip()
        
        # ----- Dynamic Command Routing ----- #
        if cmd.upper() in ["CONVERT", "ADD", "GENERATE", "MOVE"]:
            sys.stdout.write("\033[?25l")
            return cmd.upper()
            
        elif cmd.isdigit():
            idx = int(cmd)
            if 0 <= idx < len(ctx['l_items']):
                n, pth = ctx['l_items'][idx]
                
                locked = ctx.get('locked_dir')
                if n == "../" and locked and os.path.normcase(os.path.abspath(ctx['ldir'])) == os.path.normcase(os.path.abspath(locked)):
                    ctx['warning_msg'] = "\033[31m[ Directory Locked: Operation Restricted ]\033[39m"
                    ctx['user_input'] = "" 
                    return "STAY"
                
                if os.path.isdir(pth):
                    ctx['ldir'] = pth
                    ctx['lpage'] = 0
                else:
                    if not any(c[1] == pth for c in ctx['clip']):
                        ctx['clip'].append((n, pth))
            else:
                ctx['warning_msg'] = "[ Invalid Selection ]"
        elif cmd.isalpha():
            val = 0
            for char in cmd.upper(): val = val * 26 + (ord(char) - 64)
            idx = val - 1
            if 0 <= idx < len(ctx['clip']):
                ctx['clip'].pop(idx)
            else:
                ctx['warning_msg'] = "[ Invalid Selection ]"
        else:
            if cmd != "": ctx['warning_msg'] = "[ Invalid Command ]"
        ctx['user_input'] = "" 
        
    elif len(ch) == 1 and ch.isprintable():
        if len(ctx['user_input']) < 15: 
            ctx['user_input'] += ch
            
    sys.stdout.write("\033[?25l")
    return "STAY"

def playback_input(ch, ctx, term_h):
    log_lines = ctx.get('log_lines', [])
    
    vp_height = term_h - 12
    max_offset = max(0, len(log_lines) - vp_height)
    offset = ctx.get('scroll_offset', 0)
    
    if ch == 'UP': offset -= 1
    elif ch == 'DOWN': offset += 1
    elif ch == 'PGUP': offset -= vp_height
    elif ch == 'PGDN': offset += vp_height
    elif ch == 'ESC' or ch.lower() == 'q' or ch in ['\r', '\n']:
        sys.stdout.write("\033[?25l")
        return "EXIT"
        
    ctx['scroll_offset'] = max(0, min(offset, max_offset))
    return "STAY"

# ----- UI UPDATERS ---- #

def update_file_mgr_data(term_h, ctx):
    ext_filter = ['.vca', '.lds', '.csv', '.xlsx', '.xls', '.xlsm', '.xlsb', '.ods', '.fods', '.txt']
    
    try: items = os.listdir(ctx['ldir'])
    except: items = []
        
    dirs_list, files_list = [], []
    for i in items:
        pth = os.path.join(ctx['ldir'], i)
        if os.path.isdir(pth): dirs_list.append((i, pth))
        elif os.path.splitext(i)[1].lower() in ext_filter: files_list.append((i, pth))
                
    dirs_list.sort(key=lambda x: x[0].lower())
    files_list.sort(key=lambda x: x[0].lower())
    
    parent_dir = os.path.dirname(ctx['ldir']) if ctx['ldir'] != os.path.dirname(ctx['ldir']) else ctx['ldir']
    ctx['l_items'] = [("../", parent_dir)] + [(f"{d[0]}/", d[1]) for d in dirs_list] + files_list
    
    list_h = (term_h - 11) - 8 + 1 
    ctx['l_capacity'] = list_h
    ctx['r_capacity'] = max(1, list_h // 2)
    
    ctx['max_lpage'] = max(1, (len(ctx['l_items']) + ctx['l_capacity'] - 1) // ctx['l_capacity'])
    ctx['max_rpage'] = max(1, (len(ctx['clip']) + ctx['r_capacity'] - 1) // ctx['r_capacity'])
    
    if ctx['lpage'] >= ctx['max_lpage']: ctx['lpage'] = max(0, ctx['max_lpage'] - 1)
    if ctx['rpage'] >= ctx['max_rpage']: ctx['rpage'] = max(0, ctx['max_rpage'] - 1)

# ----- DRAWING UTILITES ----- #

def draw_skeleton(title, subtitle=""):
    term_w, term_h = get_term_size()
    sys.stdout.write(f"\033[1;1H╔══[{title}]{'═'*(term_w - len(title) - 6)}╗")
    for r in range(2, term_h):
        sys.stdout.write(f"\033[{r};1H║\033[{r};{term_w}H║")
    sys.stdout.write(f"\033[{term_h};1H╚══[{subtitle}]{'═'*(term_w - len(subtitle) - 6)}╝")
    
last_known_w, last_known_h = 0, 0

last_known_w, last_known_h = 0, 0

last_known_w, last_known_h = 0, 0

def draw_viewport(term_w, term_h, ctx, progress_pct=100.0, active_file="", current_val=0, total_val=0, total_types=0, total_lenses=0, is_interactive=False, title="Convert VCA", action_text="", frame_title=""):
    global scroll_offset, last_known_w, last_known_h
    
    # Dynamically measure the live terminal size for responsive word-wrapping
    live_w, live_h = get_term_size()
    
    if live_w != last_known_w or live_h != last_known_h:
        last_known_w, last_known_h = live_w, live_h
        # Calls our new unified skeleton architecture instead of the deprecated ghosts
        draw_skeleton(title, frame_title)
    
    inner_l = 4; inner_r = live_w - 3
    box_w = inner_r - inner_l + 1
    
    pb_r1 = live_h - 5; pb_r2 = live_h - 4; pb_r3 = live_h - 3
    vp_start_row = 4; vp_end_row = pb_r1 - 1
    vp_height = max(1, vp_end_row - vp_start_row - 1)
    
    # Retrieve logs safely from the context state machine
    log_lines = ctx.get('log_lines', []) if ctx else []
    
    # ----- Dynamic Word Wrapping (Option B) ----- #
    rendered_lines = []
    wrap_width = max(10, box_w - 4)
    for line in log_lines:
        wrapped = textwrap.wrap(line, width=wrap_width)
        if not wrapped:
            rendered_lines.append("")
        else:
            rendered_lines.extend(wrapped)
            
    total_logs = max(1, len(rendered_lines))
    if not is_interactive: scroll_offset = max(0, total_logs - vp_height)
    else: scroll_offset = min(scroll_offset, max(0, total_logs - vp_height))
    
    sys.stdout.write(f"\033[{vp_start_row};{inner_l}H┌{'─' * (box_w - 2)}┐")
    
    for i in range(vp_height):
        row = vp_start_row + 1 + i
        log_idx = scroll_offset + i
        log_text = rendered_lines[log_idx] if log_idx < len(rendered_lines) else ""
        
        thumb_size = max(1, int((vp_height / total_logs) * vp_height)) if len(rendered_lines) > vp_height else vp_height
        max_scroll_possible = max(1, total_logs - vp_height)
        scroll_pct = scroll_offset / max_scroll_possible if max_scroll_possible > 0 else 0
        thumb_pos = int(scroll_pct * (vp_height - thumb_size)) if len(rendered_lines) > vp_height else 0
        
        s_char = "█" if thumb_pos <= i < thumb_pos + thumb_size else "│"
        
        sys.stdout.write(f"\033[{row};{inner_l}H│ ")
        
        raw_len = 0
        if log_text:
            clean_text = re.sub(r'\x1B\[[0-9;]*[mK]', '', log_text)
            raw_len = len(clean_text)
            sys.stdout.write(f"\033[{row};{inner_l + 2}H{log_text}")
        
        space_to_fill = (inner_r - 1) - (inner_l + 2) - raw_len
        if space_to_fill > 0: sys.stdout.write(" " * space_to_fill)
            
        sys.stdout.write(f"\033[{row};{inner_r - 1}H{s_char}")
        sys.stdout.write(f"\033[{row};{inner_r}H│")
        
    sys.stdout.write(f"\033[{vp_end_row};{inner_l}H└{'─' * (box_w - 2)}┘")
    
    text_tl = f" Progress: {current_val} of {total_val} " if total_val > 0 else " Progress "
    raw_top_l = f"({text_tl})"

    raw_top_r = f"({active_file[:40] + '...' if len(active_file) > 40 else active_file})" if active_file else ""

    text_bl_1 = f" {total_types} TYPES "
    text_bl_2 = f" {total_lenses:,} LENSES "
    
    raw_bot_l = ""
    
    if action_text:
        clean_action = action_text.strip("() ")
        text_act = f" {clean_action} "
        raw_bot_l += f"({text_act})"
        
    if total_types > 0 or total_lenses > 0:
        if raw_bot_l: 
            raw_bot_l += "─"
        raw_bot_l += f"({text_bl_1}|{text_bl_2})"

    pb_inner_w = box_w - 4
    
    text_br = f" {progress_pct:5.1f}% "
    raw_br = f"({text_br})"
    
    filled = int(pb_inner_w * (progress_pct / 100.0))
    bar_str = ("#" * filled) + (" " * (pb_inner_w - filled))

    r1_len = max(0, box_w - 6 - len(raw_top_l) - len(raw_top_r))
    sys.stdout.write(f"\033[{pb_r1};{inner_l}H┌──{raw_top_l}{'─' * r1_len}{raw_top_r}──┐")
            
    sys.stdout.write(f"\033[{pb_r2};{inner_l}H│ {bar_str} │")
    
    r3_len = max(0, box_w - 6 - len(raw_bot_l) - len(raw_br))
    sys.stdout.write(f"\033[{pb_r3};{inner_l}H└──{raw_bot_l}{'─' * r3_len}{raw_br}──┘")
    
    sys.stdout.write(f"\033[{live_h};1H")
    sys.stdout.flush()
    
def draw_z_modal(title, prompt, mask=False, draw_bg=None, single_key=False):
    last_term_w, last_term_h = 0, 0
    val, force_redraw = "", True
    
    while True:
        if not check_term_size():
            warn_term_size()
            force_redraw = True
            
        term_w, term_h = get_term_size()
        if term_w != last_term_w or term_h != last_term_h:
            force_redraw, last_term_w, last_term_h = True, term_w, term_h
            
        if force_redraw:
            sys.stdout.write("\033[2J\033[H")
            # ----- Background Canvas ----- #
            if draw_bg: draw_bg(term_w, term_h) 
            
            box_w = max(50, len(prompt) + 10)
            box_h = 4 if single_key else 5
            start_y, start_x = (term_h // 2) - (box_h // 2), (term_w - box_w) // 2
            
            for i in range(box_h):
                row = start_y + i
                if i == 0: text = f"╔{'═'*(box_w-2)}╗"
                elif i == 1: text = f"║{title:^{box_w-2}}║"
                elif i == 2: text = f"║ {prompt:<{box_w-3}}║"
                # ----- dynamic text ----- #
                elif i == 3 and not single_key: text = f"║ > {val:<{box_w-5}}║"
                elif i == 3 and single_key: text = f"╚{'═'*(box_w-2)}╝"
                elif i == 4 and not single_key: text = f"╚{'═'*(box_w-2)}╝"
                sys.stdout.write(f"\033[{row};{start_x}H{text}")
                
            sys.stdout.flush()
            force_redraw = False
            
        if not single_key:
            box_w = max(50, len(prompt) + 10)
            start_y = (term_h // 2) - 2
            cursor_x = ((term_w - box_w) // 2) + 4 + len(val)
            sys.stdout.write(f"\033[{start_y + 3};{cursor_x}H\033[?25h")
        else:
            sys.stdout.write("\033[?25l")
            
        sys.stdout.flush()
        
        ch = getch_timeout(POLL_RATE)
        if ch is None: continue
        force_redraw = True
        
        # ----- Key Mode vs Text Mode ----- #
        if single_key:
            if ch == 'ESC': return None
            elif len(ch) == 1 and ch.isprintable(): return ch
        else:
            if ch in ['\r', '\n']:
                sys.stdout.write("\033[?25l")
                return val
            elif ch == 'ESC':
                sys.stdout.write("\033[?25l")
                return None
            elif ch in ['BACKSPACE', '\x08', '\x7f', 'DEL']: val = val[:-1]
            elif len(ch) == 1 and ch.isprintable() and len(val) < box_w - 7: val += ch
 
def draw_throttle(term_w, term_h, ctx, pct, active_text, current_idx, total_files, is_done=False):
    p_min = ctx.get('pace_min', 0.0)
    p_max = ctx.get('pace_max', 0.0)
    frame_rate = 0.05
    
    # ----- THEATRICAL PAUSE ----- #
    pause_time = random.uniform(p_min, p_max) if p_max > 0 else 0
    wake_up = time.time() + pause_time
    
    # ----- MICRO POLLING LOOP ----- #
    while time.time() < wake_up:
        if not check_term_size():
            warn_term_size()
            ctx['force_redraw'] = True
            
        curr_w, curr_h = get_term_size()
        if curr_w != ctx.get('last_term_w') or curr_h != ctx.get('last_term_h'):
            ctx['force_redraw'] = True
            ctx['last_term_w'] = curr_w
            ctx['last_term_h'] = curr_h
            sys.stdout.write("\033[2J\033[H")
            sys.stdout.flush()
            
        # Instantly redraw mid-sleep if the user resizes the window
        if ctx.get('force_redraw', False):
            draw_viewport(
                curr_w, curr_h, ctx, pct, active_text, current_idx, total_files, 
                is_interactive=False, 
                title=ctx.get('pb_title', "System Process"), 
                action_text=ctx.get('pb_action', "( COMPILING )"), 
                frame_title=ctx.get('pb_frame', "SYSTEM FEED")
            )
            ctx['last_draw_time'] = time.time()
            ctx['force_redraw'] = False
            
        time.sleep(POLL_RATE)
        
    # ----- AGGRESSIVE POST-PARSE ----- #
    if not check_term_size():
        warn_term_size()
        ctx['force_redraw'] = True
        
    curr_w, curr_h = get_term_size()
    if curr_w != ctx.get('last_term_w') or curr_h != ctx.get('last_term_h'):
        ctx['force_redraw'] = True
        ctx['last_term_w'] = curr_w
        ctx['last_term_h'] = curr_h
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()
        
    curr = time.time()
    last_draw = ctx.get('last_draw_time', 0)
    force = ctx.get('force_redraw', False)
    
    if curr - last_draw > frame_rate or is_done or force:
        draw_viewport(
            curr_w, curr_h, ctx, pct, active_text, current_idx, total_files, 
            is_interactive=False, 
            title=ctx.get('pb_title', "System Process"), 
            action_text=ctx.get('pb_action', "( COMPILING )"), 
            frame_title=ctx.get('pb_frame', "SYSTEM FEED")
        )
        ctx['last_draw_time'] = curr
        ctx['force_redraw'] = False
 
def draw_playback(term_w, term_h, ctx):
    total_files = len(ctx.get('clip', []))
    title = ctx.get('pb_title', 'Operations Log')
    action = ctx.get('pb_action', 'REVIEW MODE')
    frame = ctx.get('pb_frame', 'SYSTEM FEED')
    
    draw_viewport(term_w, term_h, ctx, 100.0, "Process Complete..", total_files, total_files, is_interactive=True, title=title, action_text=action, frame_title=frame)

def file_mgr(term_w, term_h, ctx):
    draw_skeleton("FILE MANAGER", f"Staging {len(ctx['clip'])} Files")
    pane_l_w = (term_w - 3) // 2
    pane_r_w = term_w - 3 - pane_l_w
    center_col = pane_l_w + 2
    
    home_dir = os.path.expanduser("~")
    if ctx['ldir'].startswith(home_dir):
        left_path = ctx['ldir'].replace(home_dir, "~", 1)
        right_path = home_dir
    else:
        left_path = ctx['ldir']
        right_path = "" # ---- If out of home, blank ----- #

    sys.stdout.write(f"\033[2;3H{left_path[:pane_l_w-4]}")
    if right_path:
        sys.stdout.write(f"\033[2;{center_col + pane_r_w - len(right_path)}H{right_path}")

    sys.stdout.write(f"\033[3;1H╟{'─'*pane_l_w}┬{'─'*pane_r_w}╢")
    for r in range(4, term_h - 8): sys.stdout.write(f"\033[{r};{center_col}H│")
    sys.stdout.write(f"\033[{term_h - 8};1H╟{'─'*pane_l_w}┴{'─'*pane_r_w}╢")
    sys.stdout.write(f"\033[4;3H{'Input VCA Files'.center(pane_l_w - 4)}")
    sys.stdout.write(f"\033[4;{center_col + 2}H{'Selected Output Files'.center(pane_r_w - 4)}")
    sys.stdout.write(f"\033[5;1H╟{'─'*pane_l_w}┼{'─'*pane_r_w}╢")
    
    l_page_str = f"(Page {ctx['lpage']+1} of {ctx['max_lpage']})"
    r_page_str = f"(Page {ctx['rpage']+1} of {ctx['max_rpage']})"
    sys.stdout.write(f"\033[6;{pane_l_w - len(l_page_str)}H{l_page_str}")
    sys.stdout.write(f"\033[6;{center_col + pane_r_w - len(r_page_str)}H{r_page_str}")
    sys.stdout.write(f"\033[7;3H  ▲ ")
    sys.stdout.write(f"\033[7;{center_col + 2}H  ◄ ")
    sys.stdout.write(f"\033[{term_h - 10};3H  ▼ ")
    sys.stdout.write(f"\033[{term_h - 10};{center_col + 2}H  ► ")

    def get_perms(path):
        try: return stat.filemode(os.stat(path).st_mode)
        except: return "----------"

    # ----- Dynamic Lock Check ----- #
    is_locked = False
    locked = ctx.get('locked_dir')
    if locked and os.path.normcase(os.path.abspath(ctx['ldir'])) == os.path.normcase(os.path.abspath(locked)):
        is_locked = True

    # ----- Draw Left Pane ----- #
    for i in range(ctx['l_capacity']):
        row_idx = 8 + i 
        idx = ctx['lpage'] * ctx['l_capacity'] + i
        sys.stdout.write(f"\033[{row_idx};3H{' ' * (pane_l_w - 2)}")
        if idx < len(ctx['l_items']):
            n, pth = ctx['l_items'][idx]
            prefix = f"[{idx:02d}]"
            perms = get_perms(pth)
            is_sel = any(c[1] == pth for c in ctx['clip'])
            name_max = pane_l_w - 6 - len(perms) - len(prefix)
            
            fmt_start = "\033[9m" if is_sel else ""
            fmt_end = "\033[29m" if is_sel else ""
            
            if n == "../" and is_locked:
                fmt_start = "\033[31;9m"
                fmt_end = "\033[39;29m"
            
            content = f"{prefix} {fmt_start}{n[:name_max]}{fmt_end}"
            pad = pane_l_w - 4 - len(prefix) - len(strip_codes(n[:name_max])) - len(perms)
            sys.stdout.write(f"\033[{row_idx};3H{content}{' ' * max(0, pad)} {perms}")

    # ----- Draw Right Pane ----- #
    for i in range(ctx['r_capacity']):
        row_idx = 8 + (i * 2) 
        idx = ctx['rpage'] * ctx['r_capacity'] + i
        sys.stdout.write(f"\033[{row_idx};{center_col + 2}H{' ' * (pane_r_w - 2)}")
        sys.stdout.write(f"\033[{row_idx + 1};{center_col + 2}H{' ' * (pane_r_w - 2)}")
        
        if idx < len(ctx['clip']):
            n, pth = ctx['clip'][idx]
            val, res = idx, ""
            while val >= 0:
                res = chr(65 + (val % 26)) + res
                val = val // 26 - 1
            
            prefix = f"[{res:>2}]" 
            perms = get_perms(pth)
            name_max = pane_r_w - 6 - len(perms) - len(prefix)
            
            pad1 = pane_r_w - 4 - len(prefix) - len(strip_codes(n[:name_max])) - len(perms)
            sys.stdout.write(f"\033[{row_idx};{center_col + 2}H{prefix} {n[:name_max]}{' ' * max(0, pad1)} {perms}")
            tree_prefix = "    └─ "
            sys.stdout.write(f"\033[{row_idx + 1};{center_col + 2}H{tree_prefix}{os.path.dirname(pth)[:pane_r_w - 4 - len(tree_prefix)]}")

    # ----- Draw Command Bar ----- #
    sys.stdout.write(f"\033[{term_h - 6};5H{' ' * (term_w - 6)}")
    sys.stdout.write(f"\033[{term_h - 6};5HSelect Files by Index Number.")
    sys.stdout.write(f"\033[{term_h - 5};5H{' ' * (term_w - 6)}")
    
    # ----- Dynamic Command ----- #
    action_str = ctx.get('action_cmd', 'EXEC')
    sys.stdout.write(f"\033[{term_h - 5};5HInput \033[4m{action_str}\033[24m to Finish Selection.")
    
    sys.stdout.write(f"\033[{term_h - 3};5H{' ' * (term_w - 6)}")
    if ctx['warning_msg']: sys.stdout.write(f"\033[{term_h - 3};5H{ctx['warning_msg']}")
        
    sys.stdout.write(f"\033[{term_h - 2};5H{' ' * (term_w - 6)}")
    sys.stdout.write(f"\033[{term_h - 2};5H> {ctx['user_input']}")
    
    cursor_col = 7 + len(ctx['user_input']) 
    sys.stdout.write(f"\033[{term_h - 2};{cursor_col}H\033[?25h")
    
# ----- TOOLS ----- #

def vca_convert(term_w, term_h, ctx):
    total_files = len(ctx.get('clip', []))
    draw_viewport(term_w, term_h, ctx, 100.0, "Batch Complete (Press ESC to return)", total_files, total_files, is_interactive=True, title="Convert VCA", action_text="( REVIEW MODE )", frame_title="VCA REFINERY: DATA SANITIZATION")
    
def vca_convert_input(ch, ctx, term_h):
    # ----- Scrolling ----- #
    log_lines = ctx.get('log_lines', [])
    
    vp_height = (term_h - 5) - 4 - 1
    max_offset = max(0, len(log_lines) - vp_height)
    offset = ctx.get('scroll_offset', 0)
    
    if ch == 'UP': offset -= 1
    elif ch == 'DOWN': offset += 1
    elif ch == 'PGUP': offset -= vp_height
    elif ch == 'PGDN': offset += vp_height
    elif ch == 'ESC' or ch.lower() == 'q':
        sys.stdout.write("\033[?25l")
        return "EXIT"
        
    ctx['scroll_offset'] = max(0, min(offset, max_offset))
    return "STAY"
    
def vca_parse_data(ctx, term_w, term_h):
    ctx['log_lines'] = []
    ctx['last_draw_time'] = 0  # universal throttle
    
    files_to_process = ctx.get('clip', [])
    total_files = len(files_to_process)
    
    cfg = load_config()
    mfg_map = cfg.get("mfg_map", {})
    
    # ----- PRE-FLIGHT ----- #
    for name, pth in files_to_process:
        ext = os.path.splitext(name)[1].lower()
        try:
            if ext in ['.xlsx', '.xls', '.xlsm', '.xlsb', '.ods']:
                df_peek = pd.read_excel(pth, dtype=str, engine='openpyxl', nrows=100)
            else:
                with open(pth, 'r', encoding='latin1', errors='ignore') as f:
                    first_line = f.readline().upper()
                if "MFG" not in first_line and "DESCRIPTION" not in first_line:
                    df_peek = pd.read_csv(pth, header=None, dtype=str, encoding='latin1', on_bad_lines='skip', engine='python', nrows=100)
                    df_peek.columns = CUSTOM_SCHEMA[:df_peek.shape[1]]
                else:
                    df_peek = pd.read_csv(pth, dtype=str, encoding='latin1', on_bad_lines='skip', engine='python', nrows=100)
            
            target_keys = list(SCHEMA_LOOKUP.keys())
            for col in df_peek.columns:
                scrubbed = re.sub(r'[^a-zA-Z0-9]', '', str(col)).lower()
                mapped_col = SCHEMA_ALIAS.get(scrubbed) or SCHEMA_LOOKUP.get(scrubbed)
                if not mapped_col:
                    matches = difflib.get_close_matches(scrubbed, target_keys, n=1, cutoff=0.85)
                    if matches: mapped_col = SCHEMA_LOOKUP[matches[0]]
                if mapped_col == "MFG":
                    unique_mfgs = df_peek[col].dropna().unique()
                    for m in unique_mfgs:
                        m_clean = str(m).strip()
                        if m_clean and m_clean not in mfg_map:
                            sys.stdout.write("\033[2J\033[H") 
                            def draw_bg(tw, th): draw_skeleton("VCA CONVERT", f"Unknown Manufacturer Code: {m_clean}")
                            ans = draw_z_modal("UNKNOWN MFG CODE", f"What does '{m_clean}' stand for?", False, draw_bg)
                            if ans:
                                mfg_map[m_clean] = ans
                                cfg["mfg_map"] = mfg_map
                                save_config(cfg)
                    break
        except: pass
    
    # ----- HARD WIPE ----- #
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()
    
    draw_throttle(term_w, term_h, ctx, 0.0, "Starting batch...", 0, total_files)
    
    for idx, (name, pth) in enumerate(files_to_process):
        current_idx = idx + 1
        pct = (current_idx / max(1, total_files)) * 100.0
        
        draw_throttle(term_w, term_h, ctx, pct, f"Parsing: {name}", current_idx, total_files)
        
        # ----- VERBOSE: INCOMING ----- #
        try: file_size_kb = os.path.getsize(pth) / 1024.0
        except: file_size_kb = 0.0
        ctx['log_lines'].append(f"[TARGET] {name} ({file_size_kb:.1f} KB)")
        
        safe_out_name = f"{os.path.splitext(name)[0]}.vca"
        dest_pth = os.path.join(IMPORT_DIR, safe_out_name)
        orig_dest_pth = os.path.join(ORIGINALS_DIR, name)
        
        try:
            ext = os.path.splitext(name)[1].lower()
            
            # ----- Excel----- #
            if ext in ['.xlsx', '.xls', '.xlsm', '.xlsb', '.ods']:
                df = pd.read_excel(pth, dtype=str, engine='openpyxl')
                ctx['log_lines'].append("  -> [INGEST] Excel binary format detected and decoded.")
            
            # ----- Text ----- #
            else:
                with open(pth, 'r', encoding='latin1', errors='ignore') as f:
                    first_line = f.readline().upper()
                    
                if "MFG" not in first_line and "DESCRIPTION" not in first_line:
                    df = pd.read_csv(pth, header=None, dtype=str, encoding='latin1', on_bad_lines='skip', engine='python')
                    df.columns = CUSTOM_SCHEMA[:df.shape[1]]
                    ctx['log_lines'].append("  -> [!] Ghost file detected: Forced master schema overlay.")
                else:
                    df = pd.read_csv(pth, dtype=str, encoding='latin1', on_bad_lines='skip', engine='python')
                
            # ----- Fuzzy Matcher ----- #
            mapped_columns = {}
            target_keys = list(SCHEMA_LOOKUP.keys())
            
            for col in df.columns:
                scrubbed = re.sub(r'[^a-zA-Z0-9]', '', str(col)).lower()
                if scrubbed in SCHEMA_ALIAS:
                    mapped_columns[col] = SCHEMA_ALIAS[scrubbed]
                elif scrubbed in SCHEMA_LOOKUP:
                    mapped_columns[col] = SCHEMA_LOOKUP[scrubbed]
                else:
                    matches = difflib.get_close_matches(scrubbed, target_keys, n=1, cutoff=0.85)
                    if matches:
                        mapped_columns[col] = SCHEMA_LOOKUP[matches[0]]
                    else:
                        mapped_columns[col] = col 
                        
            df.rename(columns=mapped_columns, inplace=True)
            
            # ----- MFG MAP ----- #
            if 'MFG' in df.columns:
                df['MFG'] = df['MFG'].apply(lambda x: mfg_map.get(str(x).strip(), x))

            # ----- Drops proprietary manufacturer math and enforces 53-column layout ----- #
            df = df.reindex(columns=CUSTOM_SCHEMA)
            df = df.replace(r'^\s*$', np.nan, regex=True)
            
            unique_products = df['DESCRIPTION'].nunique() if 'DESCRIPTION' in df.columns else 0
            
            # ----- Cascade logic for Safe Index ----- #
            n_idx = pd.to_numeric(df['NINDEX'], errors='coerce')
            d_idx = pd.to_numeric(df['DINDEX'], errors='coerce')
            e_idx = pd.to_numeric(df['EINDEX'], errors='coerce')
            df['SAFE_INDEX'] = n_idx.combine_first(d_idx).combine_first(e_idx).fillna(0.00)
            
            # ----- Calculate True Front, True Back, and SAG (Strict 1.530 Tooling Base) ----- #
            rad_f = pd.to_numeric(df['RADIUSF'], errors='coerce').replace(0.0, np.nan)
            rad_b = pd.to_numeric(df['RADIUSB'], errors='coerce').replace(0.0, np.nan)
            df['TRUE_FRONT'] = (530.0 / rad_f).round(2)
            df['TRUE_BACK'] = (-530.0 / rad_b).round(2)
            
            y = 25.0
            df['SAG'] = np.where(rad_f > y, rad_f - np.sqrt(rad_f**2 - y**2), np.nan)
            df['SAG'] = df['SAG'].round(3)
            df[['TRUE_FRONT', 'TRUE_BACK', 'SAG']] = df[['TRUE_FRONT', 'TRUE_BACK', 'SAG']].fillna(0.00)
            
            # ----- Formatting Override: Math & Zeros ----- #
            def fmt_pow(x):
                try: return f"{float(x):+.2f}" if pd.notnull(x) and str(x).strip() != "" else x
                except: return x
                
            def fmt_idx(x):
                try: return f"{float(x):.3f}" if pd.notnull(x) and str(x).strip() != "" else x
                except: return x
                
            def fmt_dec(x):
                try: return f"{float(x):.2f}" if pd.notnull(x) and str(x).strip() != "" else x
                except: return x

            # Unique formatter to strictly preserve 3 decimal places for SAG
            def fmt_sag(x):
                try: return f"{float(x):.3f}" if pd.notnull(x) and str(x).strip() != "" else x
                except: return x

            for col in ['SPH/BASE', 'CYL/ADD']:
                if col in df.columns: df[col] = df[col].apply(fmt_pow)
            for col in ['NINDEX', 'DINDEX', 'EINDEX', 'SAFE_INDEX']:
                if col in df.columns: df[col] = df[col].apply(fmt_idx)
            for col in ['RADIUSF', 'RADIUSB', 'CT', 'ET', 'TRUE_FRONT', 'TRUE_BACK']:
                if col in df.columns: df[col] = df[col].apply(fmt_dec)
            if 'SAG' in df.columns:
                df['SAG'] = df['SAG'].apply(fmt_sag)

            df = df.fillna("")
            df.to_csv(dest_pth, index=False)
            
            # ----- Archive Original File ----- #
            if os.path.exists(orig_dest_pth): os.remove(orig_dest_pth) 
            import shutil
            shutil.move(pth, orig_dest_pth)
            
            # ----- VERBOSE: OUTGOING ----- #
            try: out_size_kb = os.path.getsize(dest_pth) / 1024.0
            except: out_size_kb = 0.0
            
            ctx['log_lines'].append(f"  -> [INGEST] {len(df):,} raw lines read and normalized.")
            ctx['log_lines'].append(f"  -> [SCHEMA] 53-Column Master VCA standard enforced.")
            ctx['log_lines'].append(f"  -> [MATH] 1.530 Lap Tooling Index locked. True Curves & SAG exported.")
            ctx['log_lines'].append(f"  -> [AUDIT] Identified {unique_products:,} unique products spanning {len(df):,} lenses.")
            ctx['log_lines'].append(f"  -> [STAGED] {dest_pth} ({out_size_kb:.1f} KB)")
            
        except Exception as e:
            ctx['log_lines'].append(f"  -> [ERROR] Failed to process file: {e}")
            
        ctx['log_lines'].append("") 
        
        # ----- Theatrical UI Pacing ----- #
        draw_throttle(term_w, term_h, ctx, pct, f"Finished: {name}", current_idx, total_files)

    # ----- Final Theatrical Prompt ----- #
    ctx['log_lines'].append("")
    ctx['log_lines'].append("=" * 50)
    ctx['log_lines'].append("[ PROCESS COMPLETE ] Press [RETURN] to Continue...")
    ctx['log_lines'].append("=" * 50)

    # ----- Final Force Draw ----- #
    draw_throttle(term_w, term_h, ctx, 100.0, "Batch Completed", total_files, total_files, is_done=True)
    
    return ctx['log_lines']
    
def vca_add_data(ctx, term_w, term_h):
    ctx['log_lines'] = []
    ctx['last_draw_time'] = 0  
    
    files_to_process = ctx.get('clip', [])
    total_files = len(files_to_process)
    
    audit_passed = True
    failed_files = []
    staged_data = [] 
    
    # --- SAG tolerance ---
    tolerance = 0.006
    
    # ----- 1.67 HEURISTIC WEIGHT ----- #
    global_context = {"m10_bias": 0, "m7_bias": 0}
    listed_m10 = 0
    listed_m7 = 0
    
    for name, pth in files_to_process:
        try:
            df_peek = pd.read_csv(pth, dtype=str, encoding='latin1', on_bad_lines='skip').fillna("")
            if 'DESCRIPTION' in df_peek.columns:
                # Deduplicate by description so row count doesn't skew product line habits
                for _, row in df_peek.drop_duplicates(subset=['DESCRIPTION']).iterrows():
                    c = f" {row.get('MATCODE', '')} {row.get('MATBRAND', '')} {row.get('DESCRIPTION', '')} {row.get('PRODUCT', '')} ".upper()
                    i_val = safe_float(row.get('SAFE_INDEX', 0.0))
                    if 1.65 <= i_val <= 1.675 or "1.67" in c:
                        if "MR10" in c or "MR-10" in c:
                            listed_m10 += 1
                        if "MR7" in c or "MR-7" in c:
                            listed_m7 += 1
        except:
            pass
            
    # Inverse Deduction: If they label MR-10 more often, unlabeled 1.67s are MR-7 (and vice versa)
    if listed_m10 > listed_m7:
        global_context["m7_bias"] = 1
    elif listed_m7 > listed_m10:
        global_context["m10_bias"] = 1

    # ----- Wipe Screen ----- #
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()
    
    draw_throttle(term_w, term_h, ctx, 0.0, "Initiating Phase 1: Batch Audit", 0, total_files)

    # ----- AUDIT ----- #
    for idx, (name, pth) in enumerate(files_to_process):
        current_idx = idx + 1
        pct = (current_idx / max(1, total_files)) * 50.0 
        
        try: file_size_kb = os.path.getsize(pth) / 1024.0
        except: file_size_kb = 0.0
        
        ctx['log_lines'].append(f"[INGEST] {name} ({file_size_kb:.1f} KB) loaded for memory audit.")
        draw_throttle(term_w, term_h, ctx, pct, name, current_idx, total_files)
        
        try:
            df = pd.read_csv(pth, dtype=str, encoding='latin1', on_bad_lines='error')
            
            # ----- Schema Check ----- #
            if list(df.columns) != CUSTOM_SCHEMA:
                audit_passed = False
                failed_files.append((name, pth))
                ctx['log_lines'].append(f"  -> [REJECTED] {name}: Schema mismatch. Found {len(df.columns)} cols, expected {len(CUSTOM_SCHEMA)}.")
                continue
            else:
                ctx['log_lines'].append(f"  -> [SCHEMA] {name}: Verified exactly 53 columns across {len(df)} rows.")
                draw_throttle(term_w, term_h, ctx, pct, name, current_idx, total_files)
                
            # ----- Duplicate Purge ----- #
            orig_len = len(df)
            df.drop_duplicates(subset=CUSTOM_SCHEMA, keep='first', inplace=True)
            df.reset_index(drop=True, inplace=True)
            
            if len(df) < orig_len:
                purged = orig_len - len(df)
                ctx['log_lines'].append(f"  -> [CLEANUP] Silently purged {purged:,} identical duplicate rows.")
                draw_throttle(term_w, term_h, ctx, pct, name, current_idx, total_files)
            
            rad_f = pd.to_numeric(df['RADIUSF'], errors='coerce').replace(0.0, np.nan)
            rad_b = pd.to_numeric(df['RADIUSB'], errors='coerce').replace(0.0, np.nan)
            
            calc_front = (530.0 / rad_f).round(2).fillna(0.00)
            calc_back = (-530.0 / rad_b).round(2).fillna(0.00)
            
            y = 25.0
            calc_sag = np.where(rad_f > y, rad_f - np.sqrt(rad_f**2 - y**2), np.nan)
            calc_sag = pd.Series(calc_sag, index=df.index).round(3).fillna(0.00)
            
            file_front = pd.to_numeric(df['TRUE_FRONT'], errors='coerce').fillna(0.00)
            file_back = pd.to_numeric(df['TRUE_BACK'], errors='coerce').fillna(0.00)
            file_sag = pd.to_numeric(df['SAG'], errors='coerce').fillna(0.00)
            
            sf_mask = df['CLASS'].astype(str).str.upper().fillna('') != 'FIN'
            
            # --- Controlled Math Tolerance Threshold ---
            front_mismatch = ((calc_front - file_front).abs() > tolerance) & sf_mask
            back_mismatch = ((calc_back - file_back).abs() > tolerance) & sf_mask
            sag_mismatch = ((calc_sag - file_sag).abs() > tolerance) & sf_mask
            
            if front_mismatch.any() or back_mismatch.any() or sag_mismatch.any():
                audit_passed = False
                failed_files.append((name, pth))
                
                if front_mismatch.any():
                    bad_idx = front_mismatch.idxmax()
                    ctx['log_lines'].append(f"  -> [REJECTED] {name}: TRUE_FRONT mismatch on Row {bad_idx + 2} (Exp: {calc_front.iloc[bad_idx]:.2f}, Found: {file_front.iloc[bad_idx]:.2f})")
                elif back_mismatch.any():
                    bad_idx = back_mismatch.idxmax()
                    ctx['log_lines'].append(f"  -> [REJECTED] {name}: TRUE_BACK mismatch on Row {bad_idx + 2} (Exp: {calc_back.iloc[bad_idx]:.2f}, Found: {file_back.iloc[bad_idx]:.2f})")
                elif sag_mismatch.any():
                    bad_idx = sag_mismatch.idxmax()
                    ctx['log_lines'].append(f"  -> [REJECTED] {name}: SAG mismatch on Row {bad_idx + 2} (Exp: {calc_sag.iloc[bad_idx]:.3f}, Found: {file_sag.iloc[bad_idx]:.3f})")
                continue
            else:
                ctx['log_lines'].append(f"  -> [MATH] {name}: Tooling Index (1.530) and SAG physics verified (FIN bypassed).")
                draw_throttle(term_w, term_h, ctx, pct, name, current_idx, total_files)

            # ----- Resolve Materials & Stamp into VCA File ----- #
            df_filled = df.fillna("")
            mat_cols = ['MATCODE', 'MATBRAND', 'SAFE_INDEX', 'DESCRIPTION', 'PRODUCT', 'ABBE']
            unique_combos = df_filled[mat_cols].drop_duplicates()
            
            combo_map = {}
            for _, r in unique_combos.iterrows():
                key = tuple(r[col] for col in mat_cols)
                combo_map[key] = resolve_material(
                    r['MATCODE'], r['MATBRAND'], r['SAFE_INDEX'],
                    r['DESCRIPTION'], r['PRODUCT'], r['ABBE'], global_context
                )
                
            # Restore viewport cleanly in case draw_z_modal was triggered during tie-breaking
            sys.stdout.write("\033[2J\033[H")
            ctx['force_redraw'] = True
            
            df['MATCODE'] = [combo_map[tuple(x)] for x in df_filled[mat_cols].to_numpy()]
            df.fillna("").to_csv(pth, index=False)
            
            ctx['log_lines'].append(f"  -> [MATERIAL] {name}: Resolved {len(unique_combos)} lens families into standard materials.")
            draw_throttle(term_w, term_h, ctx, pct, name, current_idx, total_files)

            staged_data.append((name, pth, len(df)))
            
        except Exception as e:
            audit_passed = False
            failed_files.append((name, pth))
            ctx['log_lines'].append(f"  -> [REJECTED] {name}: Critical read failure ({e})")

    # ----- COMMIT OR ROLLBACK ----- #
    if audit_passed:
        total_moved_kb = 0.0
        for idx, (name, pth, row_count) in enumerate(staged_data):
            current_idx = idx + 1
            pct = 50.0 + ((current_idx / max(1, len(staged_data))) * 50.0)
            
            dest_pth = os.path.join(VAULT_DIR, name)
            try: kb = os.path.getsize(pth) / 1024.0
            except: kb = 0.0
            total_moved_kb += kb
            
            # --- Set Permissions ---
            if os.path.exists(dest_pth): 
                os.chmod(dest_pth, 0o666)  # Unlock for overwrite
                os.remove(dest_pth)
                
            shutil.move(pth, dest_pth)
            os.chmod(dest_pth, 0o444)  # Lock to Read-Only
            
            ctx['log_lines'].append(f"[VAULT] Locked {name} ({kb:.1f} KB, {row_count:,} rows) -> 0o444 (Read-Only).")
            draw_throttle(term_w, term_h, ctx, pct, name, current_idx, total_files)
            
        ctx['log_lines'].append(f"[COMMIT] Batch clearance successful. {len(staged_data)} files ({total_moved_kb:.1f} KB) secured.")
    
    else:
        ctx['log_lines'].append("")
        ctx['log_lines'].append(f"[BATCH FAILED] Atomic lock triggered. Moving corrupted files to isolation.")
        for name, pth in failed_files:
            dest_pth = os.path.join(CORRUPT_DIR, name)
            # --- Set Permissions ---
            if os.path.exists(dest_pth): 
                os.chmod(dest_pth, 0o666) # Unlock isolation folder files if overwriting
                os.remove(dest_pth)
            try:
                shutil.move(pth, dest_pth)
                ctx['log_lines'].append(f"  -> [ISOLATED] {name} moved to ./data/db/corrupt/")
            except Exception as e:
                ctx['log_lines'].append(f"  -> [ERROR] Failed to isolate {name}: {e}")

    # ----- Final Theatrical Prompt ----- #
    ctx['log_lines'].append("")
    ctx['log_lines'].append("=" * 50)
    ctx['log_lines'].append("[ PROCESS COMPLETE ] Press [RETURN] to Continue...")
    ctx['log_lines'].append("=" * 50)

    # ----- Final Force Draw ----- #
    draw_throttle(term_w, term_h, ctx, 100.0, "Batch Completed", total_files, total_files, is_done=True)
    return ctx['log_lines']
    
def vca_generate_db(ctx, term_w, term_h):
    ctx['log_lines'] = []
    ctx['last_draw_time'] = 0  
    
    # ----- Theatrical Pacing (800ms - 1200ms per lens) ----- #
    ctx['pace_min'] = 0.8
    ctx['pace_max'] = 1.2
    
    draw_throttle(term_w, term_h, ctx, 0.0, "Scanning Vault Directory...", 0, 1)
    
    vault_files = [f for f in os.listdir(VAULT_DIR) if f.lower().endswith('.vca')]
    vault_files.sort()
    total_files = len(vault_files)
    
    if total_files == 0:
        ctx['log_lines'].append("[!] Vault is empty. Aborting compilation.")
        draw_throttle(term_w, term_h, ctx, 100.0, "Aborted", 1, 1, is_done=True)
        return ctx['log_lines']
        
    current_hashes = {f: get_file_hash(os.path.join(VAULT_DIR, f)) for f in vault_files}
        
    # ----- PRE-SCAN (smooth progress bar) ----- #
    ctx['log_lines'].append("[~] Initiating High-Speed Pre-Scan Matrix...")
    draw_throttle(term_w, term_h, ctx, 0.0, "Pre-Scanning...", 0, 1)
    
    total_lenses = 0
    for file_name in vault_files:
        try:
            pth = os.path.join(VAULT_DIR, file_name)
            df = pd.read_csv(pth, dtype=str, encoding='latin1').fillna("")
            if 'SAFE_INDEX' not in df.columns:
                n_idx = pd.to_numeric(df['NINDEX'], errors='coerce')
                d_idx = pd.to_numeric(df['DINDEX'], errors='coerce')
                e_idx = pd.to_numeric(df['EINDEX'], errors='coerce')
                df['SAFE_INDEX'] = n_idx.combine_first(d_idx).combine_first(e_idx).fillna(0.00)
                
            df['NORM_CLASS'] = df['CLASS'].apply(lambda c: 'FIN' if 'FIN' in str(c).upper() else 'SF')
            df['NORM_DESC'] = df['DESCRIPTION'].apply(map_lens_group)
            
            grouped = df.groupby(['MFG', 'NORM_CLASS', 'NORM_DESC', 'MATCODE', 'SAFE_INDEX', 'ABBE'])
            total_lenses += len(grouped)
        except Exception: pass
        
    ctx['log_lines'].append(f"[✓] Pre-Scan Complete. {total_lenses} unique lens families identified.")
    ctx['log_lines'].append(f"[!] Initiating atomic master rebuild across {total_files} files.")
    ctx['log_lines'].append("")

    sandbox_lenses = {}
    used_short_ids = set()
    current_lens_processed = 0
    
    # ----- PANDAS GROUPING ----- #
    for file_name in vault_files:
        pth = os.path.join(VAULT_DIR, file_name)
        
        try:
            df = pd.read_csv(pth, dtype=str, encoding='latin1').fillna("")
            
            if 'SAFE_INDEX' not in df.columns:
                n_idx = pd.to_numeric(df['NINDEX'], errors='coerce')
                d_idx = pd.to_numeric(df['DINDEX'], errors='coerce')
                e_idx = pd.to_numeric(df['EINDEX'], errors='coerce')
                df['SAFE_INDEX'] = n_idx.combine_first(d_idx).combine_first(e_idx).fillna(0.00)
                
            df['NORM_CLASS'] = df['CLASS'].apply(lambda c: 'FIN' if 'FIN' in str(c).upper() else 'SF')
            df['NORM_DESC'] = df['DESCRIPTION'].apply(map_lens_group)
            
            grouped = df.groupby(['MFG', 'NORM_CLASS', 'NORM_DESC', 'MATCODE', 'SAFE_INDEX', 'ABBE'])
            
            for name_tuple, group in grouped:
                current_lens_processed += 1
                pct = (current_lens_processed / total_lenses) * 100.0 if total_lenses > 0 else 100.0
                
                mfg, cls_upper, norm_desc, mat, safe_idx, abbe = name_tuple
                is_fsv = (cls_upper == 'FIN')
                has_add = pd.to_numeric(group['CYL/ADD'], errors='coerce').max() > 0 if not is_fsv else False
                
                lens_hash_str = f"{mfg}_{cls_upper}_{norm_desc}_{mat}_{safe_idx}_{abbe}"
                l_id = hashlib.md5(lens_hash_str.encode()).hexdigest()[:12]
                
                extracted_colors, extracted_techs, extracted_coats, color_search_tags = map_lens_tech(group)
                
                has_non_ar = False
                for _, r_data in group.iterrows():
                    coat_str = f"{r_data.get('COAT', '')} {r_data.get('COATBRAND', '')}".upper()
                    is_ar_line = any(x in coat_str for x in ['AR', 'A/R', 'DURA', 'CRIZAL', 'VELA', 'HOYA', 'ECP', 'ULTRACLEAN', 'ANTI-REFLECTIVE', 'HMC', 'SHMC', 'BMC'])
                    if 'UNCOAT' in coat_str or 'UC' in coat_str.split():
                        has_non_ar = True
                    elif not is_ar_line and ('HC' in coat_str.split() or 'SR' in coat_str.split() or 'HARD' in coat_str or not coat_str.strip()):
                        has_non_ar = True
                is_universal_ar = not has_non_ar
                
                sample_row = group.iloc[0].to_dict()
                clean_desc, lms_brief, lms_long, tags, active_ar, prefix_str, prefix_parts, extracted_seg_size = map_lens_desc(
                    sample_row, is_fsv, has_add, extracted_techs, extracted_coats, is_universal_ar, mat
                )
                
                base_raw_desc = str(sample_row.get('DESCRIPTION', '')).strip()
                extra_dia_tags = []
                if len(group) > 1:
                    for _, r_data in group.iloc[1:].iterrows():
                        rd = str(r_data.get('DESCRIPTION', '')).strip()
                        for m in re.findall(r'\bD\d{2,3}\b|\b\d{2,3}MM\b', rd, flags=re.IGNORECASE):
                            m_up = m.upper()
                            if m_up not in base_raw_desc.upper() and m_up not in extra_dia_tags:
                                extra_dia_tags.append(m_up)
                raw_vca_desc = base_raw_desc + (" " + " ".join(extra_dia_tags) if extra_dia_tags else "")
                
                _tmp_raw = re.sub(r'\bBLUE\s*GUARD\b', 'BLUEGUARD', raw_vca_desc, flags=re.IGNORECASE)
                _tmp_raw = re.sub(r'\bBLUE\s*PROTECT\b', 'BLUEPROTECT', _tmp_raw, flags=re.IGNORECASE)
                _tmp_raw = re.sub(r'\bBLUE\s*FILTER\b', 'BLUEFILTER', _tmp_raw, flags=re.IGNORECASE)
                for _cw in ['PRO GRAY', 'PRO GREY', 'PRO BROWN', 'EXTRA-GRAY', 'EXTRA-GREY', 'EXTRA GRAY', 'EXTRA GREY', 'EXTRAGRAY', 'EXTRAGREY', 'GRAY', 'GREY', 'GRY', 'BROWN', 'BRN', 'GREEN', 'GRN', 'G15', 'G-15', 'PIONEER', 'PIONEEER', 'PIO', 'EMERALD', 'BURGUNDY', 'BURG', 'BRG', 'PINK', 'PNK', 'BLUE', 'BLU', 'PURPLE', 'PURP', 'PLUM', 'YELLOW', 'YEL', 'YLW', 'ROSE', 'ROS', 'ORANGE']:
                    _tmp_raw = re.sub(rf'\b{_cw}(?:\s*[-]?\s*[123ABC])?\b', '', _tmp_raw, flags=re.IGNORECASE)
                _tmp_raw = _tmp_raw.replace('BLUEGUARD', 'BlueGuard').replace('BLUEPROTECT', 'Blue Protect').replace('BLUEFILTER', 'Blue Filter')
                raw_vca_desc = re.sub(r'\s+', ' ', _tmp_raw).strip()
                
                all_tags = set(tags + extracted_coats + extracted_colors + color_search_tags)
                all_tags.discard("Clear")
                all_tags.discard("CLEAR")
                all_tags.discard("NONE")
                
                clean_desc = smart_casing(clean_desc, list(all_tags) + extracted_techs)
                raw_vca_desc = smart_casing(raw_vca_desc, list(all_tags) + extracted_techs)
                
                specs_list, sorted_dias, rollup_meta = aggregate_specs(group, is_fsv, extracted_seg_size)
                style_code = map_lens_style(sample_row)
                
                is_new = l_id not in sandbox_lenses
                if is_new:
                    giant_int = int(l_id, 16)
                    cand = giant_int % 100000
                    while cand in used_short_ids:
                        cand = (cand + 1) % 100000
                    used_short_ids.add(cand)
                    short_id_str = f"{cand:05d}"
                    
                    idx_float = safe_float(safe_idx)
                    idx_str = f"{idx_float:.4f}".rstrip('0')
                    if idx_str.endswith('.'): idx_str += "00"
                    elif len(idx_str.split('.')[1]) == 1: idx_str += "0"
                    
                    lens_entry = {
                        "Id": short_id_str,
                        "MFG": mfg,
                        "Style": style_code,
                        "Material": mat,
                        "Index": idx_str,
                        "Abbe": int(safe_float(abbe)),
                        "Raw Description": raw_vca_desc,
                        "Description": clean_desc,
                        "Brief Description": lms_brief,
                        "Long Description": lms_long,
                        "Colors": extracted_colors,
                        "Diameters": sorted_dias,
                        "Coatings": extracted_coats,
                        "FilterTags": sorted(list(all_tags), key=str.casefold),
                        "Specifications": {cls_upper: specs_list}
                    }
                    lens_entry.update(rollup_meta)
                    sandbox_lenses[l_id] = lens_entry
                    
                    # Stylized New Lens Log
                    ctx['log_lines'].append(f"[+] INDEXED [{l_id}] {raw_vca_desc} (Indexing base matrix)")
                else:
                    existing_lens = sandbox_lenses[l_id]
                    
                    old_colors = set(existing_lens["Colors"])
                    old_dias = set(existing_lens["Diameters"])
                    
                    existing_lens["Colors"] = sorted(list(set(existing_lens["Colors"] + extracted_colors)))
                    existing_lens["Diameters"] = sorted(list(set(existing_lens["Diameters"] + sorted_dias)))
                    existing_lens["Coatings"] = sorted(list(set(existing_lens["Coatings"] + extracted_coats)))
                    existing_lens["FilterTags"] = sorted(list(set(existing_lens["FilterTags"] + list(all_tags))), key=str.casefold)
                    
                    if cls_upper not in existing_lens["Specifications"]:
                        existing_lens["Specifications"][cls_upper] = specs_list
                    else:
                        existing_lens["Specifications"][cls_upper].extend(specs_list)
                    existing_lens.update(rollup_meta)
                    
                    # Calculate Stylized Deltas
                    new_colors = sorted(list(set(extracted_colors) - old_colors))
                    new_dias = sorted(list(set(sorted_dias) - old_dias))
                    
                    added_str = []
                    if new_colors:
                        c_noun = "colors" if len(new_colors) > 1 else "color"
                        added_str.append(f"Adding {', '.join(new_colors)} {c_noun}")
                    if new_dias:
                        d_str = ", ".join(str(d) for d in new_dias)
                        added_str.append(f"{d_str}mm blanks")
                        
                    if added_str:
                        delta_msg = f"({'; '.join(added_str)})"
                    else:
                        delta_msg = "(Merging new base curves & specs)"
                        
                    ctx['log_lines'].append(f"[~] MERGED  [{l_id}] {raw_vca_desc} {delta_msg}")
                    
                # Theatrical Throttle updates smoothly based on total_lenses
                draw_throttle(term_w, term_h, ctx, pct, f"Compiling: {file_name}", current_lens_processed, total_lenses)
                
        except Exception as e:
            ctx['log_lines'].append(f"[!] CRITICAL FAILURE parsing {file_name}: {e}")
            ctx['log_lines'].append("[!] Atomic abort triggered. No changes written to database.")
            ctx['log_lines'].append("=" * 50)
            ctx['log_lines'].append("[ PROCESS ABORTED ] Press [RETURN] to Continue...")
            ctx['log_lines'].append("=" * 50)
            draw_throttle(term_w, term_h, ctx, pct, "Aborted", current_lens_processed, total_lenses, is_done=True)
            return ctx['log_lines']

    # ----- ATOMIC COMMIT ----- #
    ctx['pace_min'] = 0.0
    ctx['pace_max'] = 0.0
    
    ctx['log_lines'].append("")
    ctx['log_lines'].append(f"[✓] Matrix Compilation Complete. Writing {len(sandbox_lenses)} parent lenses to disk...")
    draw_throttle(term_w, term_h, ctx, 100.0, "Atomic Commit", total_lenses, total_lenses)
    
    try:
        raw_json = json.dumps({"files": current_hashes, "lenses": sandbox_lenses}, indent=4)
        flat_json = re.sub(r'\[\n\s+([^\[\]\{\}]+?)\n\s+\]', lambda m: '[' + ' '.join(m.group(1).split()) + ']', raw_json)
        
        with open(DB_FILE, 'w') as f:
            f.write(flat_json)
            
        ctx['log_lines'].append(f"[✓] Atomic commit successful. master_lens_db.json is secured.")
    except Exception as e:
        ctx['log_lines'].append(f"[!] FATAL WRITE ERROR: {e}")

    ctx['log_lines'].append("")
    ctx['log_lines'].append("=" * 50)
    ctx['log_lines'].append("[ PROCESS COMPLETE ] Press [RETURN] to Continue...")
    ctx['log_lines'].append("=" * 50)

    draw_throttle(term_w, term_h, ctx, 100.0, "Database Mastered", total_lenses, total_lenses, is_done=True)
    return ctx['log_lines']
    
def vca_generate_html(ctx, term_w, term_h):
    global global_mode
    global_version = str(globals().get('VERSION', '4.0.0')).replace('v', '')
    
    draw_skeleton("STATIC SITE GENERATOR", "HTML DEPLOYMENT")
    
    if not os.path.exists(DB_FILE):
        draw_frame_line(f"{C_ALERT}Error: Master database not found.{RESET}", 6, align="center")
        draw_universal_footer() 
        global_mode = "MAIN MENU"; return
        
    ctx['log_lines'] = ["[~] Awaiting SSG deployment authorization..."]
    draw_throttle(term_w, term_h, ctx, 0.0, "Pending Auth...", 0, 1)
    
    ans = draw_z_modal("DEPLOYMENT AUTHORIZATION", "Type DEPLOY to generate web sandbox:")
    
    # Restores the outer double-line walls after the modal clears
    draw_skeleton("STATIC SITE GENERATOR", "HTML DEPLOYMENT")
    
    if ans != "DEPLOY": return

    try:
        ctx['log_lines'] = [f"[+] Opening Read-Only Buffer -> {DB_FILE}"]
        draw_throttle(term_w, term_h, ctx, 0.0, "Bootstrapping...", 0, 1)
        
        # Ensure direct output directories exist
        os.makedirs(HTML_DIR, exist_ok=True)
        os.makedirs(HTML_DATA_DIR, exist_ok=True)
        os.makedirs(HTML_DB_DIR, exist_ok=True)
        
        ctx['log_lines'].append("[+] Writing Web Assets (Tokyo Night Storm)...")
        
        # ----- DIRECT CSS WRITE ----- #
        css_content = """
:root {
    --bg-main: #24283b; --bg-table: #1f2335; --text-main: #c0caf5;
    --win-bg: #24283b; --win-highlight: #414868; --win-shadow: #1a1b26;
    --win-dark-shadow: #15161e; --win-title: #24283b; --win-title-fade: #1f2335;
    --win-text: #c0caf5; --win-title-text: #7aa2f7; --border-light: #414868;
    --border-dark: #1a1b26; --accent: #3d59a1; --row-even: #24283b; --row-odd: #1f2335;
    --col-desc: #c0caf5; --col-filt: #9ece6a; --col-coat: #e0af68; --col-mat: #7dcfff;
    --col-idx: #bb9af7; --col-diam: #c0caf5; --col-base: #e0af68; --col-tfc: #c0caf5;
    --col-tbc: #7aa2f7; --col-sag: #f7768e;
    
    --table-fs: 15px;
    --table-th-fs: 12px;
}

body { background-color: var(--bg-main); color: var(--text-main); font-weight: 500; margin: 0; padding: 20px; font-family: sans-serif; font-variant-numeric: tabular-nums; }

.top-bar { position: relative; display: flex; justify-content: space-between; align-items: flex-start; background-color: var(--win-title); border: 1px solid var(--border-light); border-bottom: 2px solid var(--border-dark); padding: 16px 24px; margin-bottom: 15px; border-radius: 6px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
.top-bar-left { display: flex; flex-direction: column; align-items: flex-start; gap: 8px; margin-top: 4px; }
.brand-title { font-size: 26px; font-weight: 900; color: var(--accent); letter-spacing: 1.5px; }
.brand-sub { font-size: 14px; font-weight: bold; color: var(--col-idx); letter-spacing: 1px; }
.top-bar-center { position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%); text-align: center; color: var(--win-title-text); font-weight: 800 !important; font-size: 28px; text-transform: uppercase; letter-spacing: 3px; white-space: nowrap; }

.top-bar-right { display: flex; flex-direction: column; gap: 10px; align-items: flex-end; }
.dropdown-row { display: flex; gap: 12px; align-items: center; }
.header-dropdown { background: var(--bg-table); color: var(--text-main); border: 1px solid var(--border-light); padding: 6px 8px; border-radius: 4px; font-weight: bold; cursor: pointer; outline: none; font-size: 14px; transition: border-color 0.2s; }
.header-dropdown:hover { border-color: var(--col-desc); }

/* SPA SEARCH & PILL ENGINE */
.stats-bar { background-color: var(--bg-table); padding: 20px 24px; border: 1px solid var(--border-light); border-radius: 6px; margin-bottom: 30px; display: flex; flex-direction: column; gap: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.15); }
.filter-row { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; justify-content: flex-start; width: 100%; margin-bottom: 4px; }
.pill-label { font-size: 14px; color: var(--col-desc); font-weight: bold; text-transform: uppercase; letter-spacing: 1px; width: 100px; text-align: right; margin-right: 10px; }

.mfg-pill, .stat-badge { padding: 5px 16px; border-radius: 50px; background: var(--bg-main); color: var(--text-main); font-weight: bold; border: 1px solid var(--border-light); font-size: 14px; cursor: pointer; user-select: none; text-decoration: none; transition: all 0.1s; }
.mfg-pill { padding: 8px 24px; border: 2px solid var(--border-light); font-size: 16px; }
.mfg-pill.active { background: var(--accent); border-color: var(--accent); color: #fff; box-shadow: 0 4px 8px rgba(0,0,0,0.3); }
.stat-badge:hover, .mfg-pill:hover { border-color: var(--col-desc); }
.stat-badge.active { background: var(--col-desc); color: var(--bg-main); border-color: var(--col-desc); }

.filter-row.row-type .stat-badge.active { background: var(--col-filt); border-color: var(--col-filt); color: var(--bg-main); }
.filter-row.row-mat .stat-badge.active { background: var(--col-mat); border-color: var(--col-mat); color: var(--bg-main); }
.filter-row.row-tech .stat-badge.active { background: var(--col-idx); border-color: var(--col-idx); color: var(--bg-main); }
.filter-row.row-color .stat-badge.active { background: var(--col-coat); border-color: var(--col-coat); color: var(--bg-main); }

.search-container { margin-top: 15px; border-top: 1px solid var(--border-dark); padding-top: 20px; width: 100%; display: flex; justify-content: center;}
.search-box { width: 80%; padding: 14px 24px; border-radius: 50px; border: 1px solid var(--border-light); background: var(--bg-main); color: var(--text-main); font-size: 16px; font-weight: bold; outline: none; text-align: center; }
.search-box:focus { border-color: var(--accent); box-shadow: 0 0 0 2px rgba(61, 89, 161, 0.3); }

.category-section { display: none; margin-bottom: 50px; }
.cat-title { color: var(--win-title-text); font-size: 22px; font-weight: bold; border-bottom: 2px solid var(--border-dark); padding-bottom: 8px; margin-bottom: 15px; text-transform: uppercase; letter-spacing: 1px; }

/* DATA GRID */
.table-container { border-radius: 12px; overflow: hidden; box-shadow: 0 8px 16px rgba(0, 0, 0, 0.4); border: 1px solid var(--border-dark); }
table.data-grid { width: 100%; border-collapse: collapse; background: var(--bg-table); table-layout: fixed; }
table.data-grid th, table.data-grid td { border: 1px solid var(--border-light); padding: 8px 10px; text-align: center; vertical-align: middle; }
table.data-grid th { font-weight: 800; text-transform: uppercase; font-size: var(--table-th-fs); color: var(--bg-main) !important; }
table.data-grid td { font-size: var(--table-fs); }
tr.row-even { background-color: var(--row-even); } tr.row-odd { background-color: var(--row-odd); }
tr.group-hover td { background-color: var(--win-highlight) !important; color: var(--bg-main) !important; cursor: pointer; }

.col-desc { color: var(--col-desc); text-align: left !important; padding-left: 14px !important; }
.col-filt { color: var(--col-filt); } .col-coat { color: var(--col-coat); }
.col-mat  { color: var(--col-mat); } .col-idx  { color: var(--col-idx); }
.col-diam { color: var(--col-diam); } .col-base { color: var(--col-base); }
.col-tfc  { color: var(--col-tfc); } .col-tbc  { color: var(--col-tbc); } .col-sag  { color: var(--col-sag); }
.empty-bullet { display: block; text-align: center; width: 100%; opacity: 0.5;}

th.bg-desc { background-color: var(--col-desc); width: 20%; }
th.bg-filt { background-color: var(--col-filt); width: 10%; }
th.bg-coat { background-color: var(--col-coat); width: 10%; }
th.bg-mat  { background-color: var(--col-mat); width: 8%; }
th.bg-idx  { background-color: var(--col-idx); width: 4.5%; }
th.bg-diam { background-color: var(--col-diam); width: 5.5%; }
th.bg-p1 { background-color: var(--col-base); width: 10.5%; }
th.bg-p2 { background-color: var(--col-tfc); width: 10.5%; }
th.bg-p3 { background-color: var(--col-tbc); width: 10.5%; }
th.bg-p4 { background-color: var(--col-sag); width: 10.5%; }
.header-divider { border: 0; height: 1px; background: var(--bg-main); opacity: 0.5; width: 85%; margin: 4px auto; }

/* LAYOUT ENGINE SWITCHES */
html[data-modal-layout="legacy"] .modern-box { display: none !important; }
html[data-modal-layout="legacy"] .dialog-box { display: flex; }
html[data-modal-layout="modern"] .dialog-box { display: none !important; }
html[data-modal-layout="modern"] .modern-box { display: flex; }
html[data-modal-layout="legacy"] .modal-overlay { background-color: transparent; }
html[data-modal-layout="modern"] .modal-overlay { background-color: rgba(0,0,0,0.75); }

.modal-overlay { display: flex; position: fixed; top: 0; left: 0; right: 0; bottom: 0; z-index: 9999; justify-content: center; align-items: center; }
.modal-overlay.hidden { display: none !important; }

/* LEGACY LMS MODAL STYLES */
.dialog-box { background-color: #d4d0c8; width: 830px; display: flex; flex-direction: column; padding: 2px; position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%) scale(1.2); z-index: 10001; }
.dialog-box * { font-family: 'Microsoft Sans Serif', 'MS Sans Serif', Tahoma, sans-serif; font-size: 11px; color: #000000; text-rendering: crispEdges; }
.dialog-box .outset-border { border-top: 1px solid #dfdfdf; border-left: 1px solid #dfdfdf; border-bottom: 1px solid #000000; border-right: 1px solid #000000; box-shadow: inset -1px -1px 0 #808080, inset 1px 1px 0 #ffffff; }
.dialog-box .inset-border { border-top: 1px solid #808080; border-left: 1px solid #808080; border-bottom: 1px solid #ffffff; border-right: 1px solid #ffffff; box-shadow: inset -1px -1px 0 #dfdfdf, inset 1px 1px 0 #000000; background-color: #ffffff; color: #000000 !important; }
.dialog-box .title-bar { background: linear-gradient(to right, #0A246A, #A6CAF0); padding: 2px 3px; display: flex; justify-content: space-between; align-items: center; font-weight: bold; }
.dialog-box .title-bar * { color: white; } 
.dialog-box .title-bar-left, .dialog-box .title-bar-right { display: flex; align-items: center; gap: 4px; }
.dialog-box .version-text { font-weight: normal; font-size: 10px; color: #000000; }
.dialog-box .faux-icon { height: 14px; background: white; color: black; border: 1px solid #ccc; font-size: 7px; padding: 1px 4px 0 4px; }
.dialog-box .title-bar-close { background: #d4d0c8; color: black; font-weight: bold; font-size: 10px; width: 16px; height: 14px; display: flex; justify-content: center; align-items: center; border-top: 1px solid #dfdfdf; border-left: 1px solid #dfdfdf; border-bottom: 1px solid #000000; border-right: 1px solid #000000; box-shadow: inset -1px -1px 0 #808080, inset 1px 1px 0 #ffffff; }

.dialog-box .tabs-container { margin-top: 8px; padding: 0 4px; position: relative; z-index: 10; }
.dialog-box .tab-buttons { display: flex; gap: 2px; margin-left: 2px; }
.dialog-box .tab { background: #d4d0c8; padding: 4px 12px; border-top: 1px solid #dfdfdf; border-left: 1px solid #dfdfdf; border-right: 1px solid #000000; border-bottom: 1px solid #dfdfdf; box-shadow: inset -1px 0 0 #808080, inset 1px 1px 0 #ffffff; cursor: pointer; position: relative; z-index: 1; }
.dialog-box .tab.active { padding-top: 6px; margin-top: -2px; border-bottom: 1px solid #d4d0c8; margin-bottom: -1px; padding-bottom: 2px; z-index: 11; }

.dialog-box .dialog-content-wrapper { height: 510px; border-top: 1px solid #ffffff; border-left: 1px solid #ffffff; border-bottom: 1px solid #404040; border-right: 1px solid #404040; box-shadow: inset -1px -1px 0 #808080; padding: 12px; position: relative; z-index: 5; display: flex; flex-direction: column; }
.dialog-box .tab-pane { display: none; height: 100%; flex-grow: 1;} 
.dialog-box .tab-pane.active { display: block; }
.dialog-box .grid-3-col { display: grid; grid-template-columns: 245px 235px 265px; gap: 16px; justify-content: center; }
.dialog-box .grid-3-col > div { display: flex; flex-direction: column; }
.dialog-box .grid-2-col { display: grid; grid-template-columns: 1fr 1fr; gap: 40px; padding: 10px 40px; box-sizing: border-box; }
.dialog-box .center-col { display: flex; flex-direction: column; align-items: center; padding-top: 20px; }

.dialog-box .form-row { display: flex; align-items: center; margin-bottom: 4px; }
.dialog-box .form-row label { width: 110px; flex-shrink: 0; }
.dialog-box .form-row input[type="text"], .dialog-box .form-row select { flex-grow: 1; height: 19px; padding: 1px 3px; background: #ffffff; outline: none; box-sizing: border-box; }
.dialog-box .fixed-width { flex-grow: 0 !important; }
.dialog-box .form-row input[readonly] { background: #d4d0c8; }

.dialog-box .classic-table { border-collapse: collapse; background: #ffffff; border: 1px solid #808080; }
.dialog-box .classic-table th { background: #d4d0c8; border-top: 1px solid #dfdfdf; border-left: 1px solid #dfdfdf; border-right: 1px solid #808080; border-bottom: 1px solid #808080; padding: 2px 4px; text-align: left; }
.dialog-box .classic-table td { border-right: 1px solid #d4d0c8; border-bottom: 1px solid #d4d0c8; padding: 1px 4px; height: 14px; }
.dialog-box .grid-lines td { border: 1px solid silver; }
.dialog-box .table-title { background: #d4d0c8; font-weight: bold; text-align: center !important; border-top: 1px solid #dfdfdf; border-left: 1px solid #dfdfdf; border-right: 1px solid #808080; border-bottom: 1px solid #808080; padding: 4px !important; }
.dialog-box fieldset { border-top: 1px solid #808080; border-left: 1px solid #808080; border-bottom: 1px solid #ffffff; border-right: 1px solid #ffffff; padding: 10px 8px; margin: 0 0 12px 0; }
.dialog-box legend { padding: 0 4px; margin-left: 4px; }
.dialog-box .win-btn { padding: 3px 12px; min-width: 75px; background: #d4d0c8; color: #000000; outline: none; }
.dialog-box .footer { display: flex; justify-content: space-between; align-items: center; padding: 10px; }

/* MODERN DASHBOARD STYLES (BENTO BOX) */
.modern-box { background-color: var(--win-bg); width: 850px; border-radius: 12px; padding: 24px; box-shadow: 0 10px 40px rgba(0,0,0,0.8); border: 1px solid var(--border-light); flex-direction: column; gap: 20px; position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); z-index: 10001;}
.modern-header { display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 1px solid var(--border-dark); padding-bottom: 15px; }
.modern-title { font-size: 26px; font-weight: bold; color: var(--win-title-text); margin: 0; letter-spacing: 0.5px; }
.modern-subtitle { font-size: 14px; color: var(--col-desc); opacity: 0.8; margin-top: 6px; }
.modern-close { background: none; border: none; color: var(--win-text); font-size: 24px; cursor: pointer; padding: 5px; opacity: 0.6; } .modern-close:hover { opacity: 1; color: var(--col-tfc); }

.bento-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 10px; }
.bento-card { background: var(--bg-table); border: 1px solid var(--border-light); border-top-width: 4px; border-radius: 8px; padding: 14px; box-shadow: 0 4px 8px rgba(0,0,0,0.2); display: flex; flex-direction: column; gap: 8px; }
.b-title { font-size: 12px; text-transform: uppercase; font-weight: 800; letter-spacing: 0.05em; margin-bottom: 4px; border-bottom: 1px solid var(--border-dark); padding-bottom: 6px; }
.b-row { display: flex; justify-content: space-between; align-items: center; font-size: 13px; }
.b-row span { opacity: 0.7; }
.b-row b { font-weight: bold; color: var(--text-main); }

.modern-grids { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.modern-table-wrap { background: var(--bg-table); border-radius: 8px; border: 1px solid var(--border-dark); overflow: hidden; }
.modern-table-wrap table { width: 100%; border-collapse: collapse; }
.modern-table-wrap th { padding: 8px 12px; font-size: 13px; color: var(--bg-main) !important; text-align: center; font-weight: bold; text-transform: uppercase; }
.modern-table-wrap td { padding: 8px 12px; border-bottom: 1px solid var(--border-dark); font-size: 15px; text-align: center; }
.modern-table-wrap tr:last-child td { border-bottom: none; }
"""
        with open(os.path.join(HTML_DATA_DIR, 'styles.css'), 'w', encoding='utf-8') as f:
            f.write(css_content.strip())
            
        # ----- DIRECT JS WRITE ----- #
        js_content = r"""
async function calculateHash(ascii) {
    const msgBuffer = new TextEncoder().encode(ascii);
    const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

function formatPower(val) {
    if (isNaN(val)) return '';
    if (Math.abs(val) === 0) return 'PL'; 
    return (val > 0 ? '+' : '') + val.toFixed(2);
}

function getRangeString(arr, isCyl) {
    if (arr.length === 0) return `<span class="empty-bullet">•</span>`;
    let minSph = Math.min(...arr.map(a => a.sph)); let maxSph = Math.max(...arr.map(a => a.sph));
    let isMinus = maxSph <= 0; let sphStr;
    if (minSph === maxSph) sphStr = formatPower(minSph);
    else sphStr = isMinus ? `${formatPower(maxSph)} to ${formatPower(minSph)}` : `${formatPower(minSph)} to ${formatPower(maxSph)}`;
    if (!isCyl) return sphStr;
    let minCyl = Math.min(...arr.map(a => a.cyl));
    return `${sphStr} to <span class="highlight-cyl">${minCyl.toFixed(2)} cyl</span>`;
}

document.addEventListener('DOMContentLoaded', async () => {
    
    const layoutSelect = document.getElementById('layout-select');
    const fontSizeSelect = document.getElementById('fontsize-select');

    if (layoutSelect) {
        let savedLayout = localStorage.getItem('ui-layout') || 'modern';
        document.documentElement.setAttribute('data-modal-layout', savedLayout);
        layoutSelect.value = savedLayout;
        layoutSelect.addEventListener('change', (e) => {
            document.documentElement.setAttribute('data-modal-layout', e.target.value);
            localStorage.setItem('ui-layout', e.target.value);
        });
    }
    
    if (fontSizeSelect) {
        let savedFs = localStorage.getItem('ui-fontsize') || '15';
        document.documentElement.style.setProperty('--table-fs', savedFs + 'px');
        document.documentElement.style.setProperty('--table-th-fs', (parseInt(savedFs) - 3) + 'px');
        fontSizeSelect.value = savedFs;
        fontSizeSelect.addEventListener('change', (e) => {
            let val = e.target.value;
            document.documentElement.style.setProperty('--table-fs', val + 'px');
            document.documentElement.style.setProperty('--table-th-fs', (parseInt(val) - 3) + 'px');
            localStorage.setItem('ui-fontsize', val);
        });
    }

    window.lensDatabase = [];
    let tamperDetected = false;

    if (typeof securityManifest !== 'undefined' && typeof window.dbPayload !== 'undefined') {
        const calculatedHash = await calculateHash(window.dbPayload);
        if (calculatedHash !== securityManifest.dbHash) {
            tamperDetected = true;
        } else {
            const binaryString = atob(window.dbPayload);
            const bytes = new Uint8Array(binaryString.length);
            for (let i = 0; i < binaryString.length; i++) bytes[i] = binaryString.charCodeAt(i);
            const jsonString = new TextDecoder('utf-8').decode(bytes);
            window.lensDatabase = JSON.parse(jsonString);
        }
    }

    if (tamperDetected) {
        document.body.innerHTML = `
            <div style="display:flex; flex-direction:column; justify-content:center; align-items:center; height:100vh; background-color:var(--bg-main); color:var(--col-sag); text-align:center;">
                <h1 style="font-size:48px; border-bottom:2px solid var(--col-sag); padding-bottom:10px; letter-spacing: 2px;">CRYPTOGRAPHIC MISMATCH</h1>
                <p style="font-size:20px; max-width:600px; color:var(--text-main); margin-top: 20px;">The signature for the Database Payload does not match the securely signed manifest.</p>
                <p style="font-size:16px; max-width:600px; color:var(--col-filt); margin-top:20px;">Please return to the VCA2HTML-TUI console and run the <b>(G)eneration Sequence</b> to completely rebuild the Vault.</p>
            </div>
        `;
        return;
    }

    buildPillFilters(window.lensDatabase);
    renderTable(window.lensDatabase);

    window.hoverGrp = function(gid) { document.querySelectorAll('.' + gid).forEach(el => el.classList.add('group-hover')); };
    window.leaveGrp = function(gid) { document.querySelectorAll('.' + gid).forEach(el => el.classList.remove('group-hover')); };

    function buildPillFilters(data) {
        let mfgSet = new Set();
        let colorSet = new Set();
        
        data.forEach(lens => { 
            if (lens.MFG) mfgSet.add(lens.MFG); 
            if (lens.Colors) lens.Colors.forEach(c => colorSet.add(c));
        });
        
        const mfgRow = document.getElementById('pill-row-mfg');
        if (mfgRow) {
            let mfgHtml = '';
            Array.from(mfgSet).sort().forEach(m => {
                mfgHtml += `<a href="#" class="mfg-pill" data-group="mfg" data-val="${m}">${m}</a>`;
            });
            mfgRow.innerHTML = mfgHtml;
        }

        const genPills = (id, label, arr, groupName) => {
            const row = document.getElementById(id);
            if (!row) return;
            let html = `<span class="pill-label">${label}:</span>`;
            html += `<a href="#" class="stat-badge tag-pill active" data-group="${groupName}" data-tag="all">All</a>`;
            
            arr.forEach(tag => {
                html += `<a href="#" class="stat-badge tag-pill" data-group="${groupName}" data-tag="${tag}">${tag}</a>`;
            });
            row.innerHTML = html;
        };

        genPills('pill-row-type', 'Type', ['FSV', 'SFSV', 'PAL', 'FT', 'TRI', 'Round', 'Exec', 'Occupational', 'Blend'], 'type');
        genPills('pill-row-mat', 'Material', ['CR-39', 'Polycarbonate', 'Trivex', '1.60', '1.67', '1.74'], 'mat');
        genPills('pill-row-tech', 'Tech', ['Blue Filter', 'Photochromic', 'Polarized', 'Short', 'Extra Thick'], 'tech');
        genPills('pill-row-coat', 'Coating', ['Hardcoated', 'Uncoated', 'A/R'], 'coat');
        
        // Smart Color Pills dynamically built from database
        genPills('pill-row-color', 'Color', Array.from(colorSet).sort(), 'color');
    }

    function renderTable(data) {
        const container = document.getElementById('table-container');
        window.activeViewData = data; 
        
        let categories = {
            'fsv': { title: 'Finished Single Vision', lenses: [] },
            'sfsv': { title: 'Semi-Finished Single Vision', lenses: [] },
            'pal': { title: 'Progressive Addition Lenses', lenses: [] },
            'ft': { title: 'Multi-Focal Lenses', lenses: [] },
            'other': { title: 'Other Lenses', lenses: [] }
        };

        data.forEach((lens, index) => {
            lens.originalIndex = index;
            let isFin = !!(lens.Specifications && lens.Specifications.FIN);
            let style = parseInt(lens.Style);
            if (isFin && style === 1) categories.fsv.lenses.push(lens);
            else if (!isFin && style === 1) categories.sfsv.lenses.push(lens);
            else if (style === 6) categories.pal.lenses.push(lens);
            else if ([2,3,4,5,8,9,10,11,12,15,16,17].includes(style)) categories.ft.lenses.push(lens);
            else categories.other.lenses.push(lens);
        });

        let html = '';
        for (const [catId, catData] of Object.entries(categories)) {
            if (catData.lenses.length === 0) continue;
            
            html += `<div class="category-section" data-cat="${catId}">`;
            html += `<h2 class="cat-title">${catData.title}</h2>`;
            html += `<div class="table-container"><table class="data-grid"><thead><tr>
                <th class="bg-desc">Description</th>
                <th class="bg-filt">Filter</th>
                <th class="bg-coat">Coating</th>
                <th class="bg-mat">Material</th>
                <th class="bg-idx">Index</th>
                <th class="bg-diam">Diameter</th>
                <th class="bg-p1">${catId === 'fsv' ? 'Minus Sph<hr class="header-divider">Base Curves' : 'Marked<hr class="header-divider">Base'}</th>
                <th class="bg-p2">${catId === 'fsv' ? 'Minus with Cylinder<hr class="header-divider">True Front Curve' : 'True Curve<hr class="header-divider">Front TC'}</th>
                <th class="bg-p3">${catId === 'fsv' ? 'Plus Sph<hr class="header-divider">True Back Curve' : 'True Curve<hr class="header-divider">Back TC'}</th>
                <th class="bg-p4">${catId === 'fsv' ? 'Plus with Cylinder<hr class="header-divider">SAG at 50mm' : 'SAG<hr class="header-divider">50mm'}</th>
            </tr></thead><tbody>`;
            
            catData.lenses.forEach((lens) => {
                let isFin = !!(lens.Specifications && lens.Specifications.FIN);
                let specArray = isFin ? lens.Specifications.FIN : lens.Specifications.SF;
                
                let rowData = [];
                if (isFin) {
                    let diamMap = {};
                    specArray.forEach(s => {
                        let diams = (s.Diameters && s.Diameters.length > 0) ? s.Diameters : ['N/A'];
                        diams.forEach(d => {
                            if (!diamMap[d]) diamMap[d] = [];
                            diamMap[d].push({ sph: parseFloat(s.SPH)||0, cyl: parseFloat(s.CYL)||0 });
                        });
                    });
                    
                    let sortedDiams = Object.keys(diamMap).sort((a,b) => parseFloat(a) - parseFloat(b));
                    sortedDiams.forEach(d => {
                        let pArr = diamMap[d];
                        let minSph = pArr.filter(p => p.sph <= 0 && p.cyl === 0);
                        let minCyl = pArr.filter(p => p.sph <= 0 && p.cyl < 0);
                        let pluSph = pArr.filter(p => p.sph > 0 && p.cyl === 0);
                        let pluCyl = pArr.filter(p => p.sph > 0 && p.cyl < 0);
                        rowData.push({
                            col1: d === 'N/A' ? '<span class="empty-bullet">•</span>' : d,
                            col2: getRangeString(minSph, false),
                            col3: getRangeString(minCyl, true),
                            col4: getRangeString(pluSph, false),
                            col5: getRangeString(pluCyl, true)
                        });
                    });
                } else {
                    let baseMap = {};
                    specArray.forEach(s => {
                        let b = parseFloat(s.BASE);
                        if(isNaN(b)) return;
                        let bStr = b.toFixed(2);
                        if (!baseMap[bStr]) {
                            baseMap[bStr] = { 
                                ftc: parseFloat(s.TRUE_FRONT || s['Front TC'])||0, 
                                btc: parseFloat(s.TRUE_BACK || s['Back TC'])||0, 
                                sag: parseFloat(s.SAG || s['SAG'])||0,
                                diams: new Set()
                            };
                        }
                        (s.Diameters || []).forEach(dia => baseMap[bStr].diams.add(dia));
                    });
                    let sortedBases = Object.keys(baseMap).sort((a,b) => parseFloat(a) - parseFloat(b));
                    sortedBases.forEach(bStr => {
                        let m = baseMap[bStr];
                        let dStr = Array.from(m.diams).sort((a,b)=>parseFloat(a)-parseFloat(b)).join(' / ') || '<span class="empty-bullet">•</span>';
                        rowData.push({
                            col1: dStr,
                            col2: parseFloat(bStr) > 0 ? `+${bStr}` : bStr,
                            col3: m.ftc === 0 ? '<span class="empty-bullet">•</span>' : m.ftc.toFixed(2),
                            col4: m.btc === 0 ? '<span class="empty-bullet">•</span>' : m.btc.toFixed(2),
                            col5: m.sag === 0 ? '<span class="empty-bullet">•</span>' : m.sag.toFixed(3)
                        });
                    });
                }
                
                if (rowData.length === 0) {
                    rowData.push({ col1: '<span class="empty-bullet">•</span>', col2: '<span class="empty-bullet">•</span>', col3: '<span class="empty-bullet">•</span>', col4: '<span class="empty-bullet">•</span>', col5: '<span class="empty-bullet">•</span>' });
                }

                let rowspan = rowData.length;
                let grpId = `grp-${lens.originalIndex}`;
                let rowClass = lens.originalIndex % 2 === 0 ? 'row-even' : 'row-odd';
                
                let desc = lens.Description || '';
                let colorHtml = '';
                if (lens.Colors && lens.Colors.length > 0) {
                    let visibleColors = lens.Colors.filter(c => c !== 'Clear');
                    if (visibleColors.length > 0) {
                        colorHtml = `<br><span style="color:var(--col-coat); font-style:italic; font-size:smaller;">(${visibleColors.join(', ')})</span>`;
                    }
                }
                desc = `${desc}${colorHtml}`;
                
                let filt = lens.Filter || '<span style="opacity:0.5;">None</span>';
                let coat = (lens.Coatings || []).join('<br>');
                if(!coat) coat = 'Uncoated';
                
                let searchIndex = [
                    lens.Id || "", 
                    lens.MFG || "", 
                    lens.Material || "", 
                    lens["Brief Description"] || "", 
                    lens["Long Description"] || "", 
                    lens.Description || "", 
                    catId
                ];
                if (lens.FilterTags) lens.FilterTags.forEach(t => searchIndex.push(t));
                let safeSearch = JSON.stringify(searchIndex.map(s => String(s))).replace(/'/g, "&#39;");
                
                html += `<tr class="${rowClass} ${grpId} lens-row" data-cat="${catId}" data-mfg="${lens.MFG}" data-search='${safeSearch}' onmouseenter="hoverGrp('${grpId}')" onmouseleave="leaveGrp('${grpId}')" onclick='openModal(${lens.originalIndex})'>`;
                html += `<td class="col-desc" rowspan="${rowspan}"><b>${desc}</b></td>`;
                html += `<td class="col-filt" rowspan="${rowspan}">${filt}</td>`;
                html += `<td class="col-coat" rowspan="${rowspan}">${coat}</td>`;
                html += `<td class="col-mat" rowspan="${rowspan}">${lens.Material || ''}</td>`;
                html += `<td class="col-idx" rowspan="${rowspan}">${lens.Index || ''}</td>`;
                
                html += `<td class="col-diam">${rowData[0].col1}</td>`;
                html += `<td class="col-base">${rowData[0].col2}</td>`;
                html += `<td class="col-tfc">${rowData[0].col3}</td>`;
                html += `<td class="col-tbc">${rowData[0].col4}</td>`;
                html += `<td class="col-sag">${rowData[0].col5}</td>`;
                html += `</tr>`;
                
                for(let i=1; i<rowspan; i++) {
                    html += `<tr class="${rowClass} ${grpId} lens-row" data-cat="${catId}" data-mfg="${lens.MFG}" data-search='${safeSearch}' onmouseenter="hoverGrp('${grpId}')" onmouseleave="leaveGrp('${grpId}')" onclick='openModal(${lens.originalIndex})'>`;
                    html += `<td class="col-diam">${rowData[i].col1}</td>`;
                    html += `<td class="col-base">${rowData[i].col2}</td>`;
                    html += `<td class="col-tfc">${rowData[i].col3}</td>`;
                    html += `<td class="col-tbc">${rowData[i].col4}</td>`;
                    html += `<td class="col-sag">${rowData[i].col5}</td>`;
                    html += `</tr>`;
                }
            });
            
            html += `</tbody></table></div></div>`;
        }
        
        container.innerHTML = html;
        applyFilters();
    }

    function applyFilters() {
        const btnAllLenses = document.getElementById('btn-all-lenses');
        const mfgBadges = document.querySelectorAll('.mfg-pill');
        const tagBadges = document.querySelectorAll('.tag-pill');
        const searchInput = document.getElementById('text-search-box');
        
        let activeMfg = 'all';
        let activeFilters = { type: 'all', mat: 'all', tech: 'all', coat: 'all', color: 'all' };
        
        function updateDOM() {
            let textQuery = searchInput ? searchInput.value.toLowerCase().trim() : '';
            let qFlat = textQuery.replace(/[^a-z0-9]/gi, '');
            const sections = document.querySelectorAll('.category-section');
            const rows = document.querySelectorAll('tr.lens-row');
            
            sections.forEach(sec => { sec.style.display = 'block'; });
            
            rows.forEach(r => {
                let searchData = [];
                try { searchData = JSON.parse(r.getAttribute('data-search') || "[]"); } catch(e) {}
                
                const mfgMatch = (activeMfg === 'all') || (r.getAttribute('data-mfg') === activeMfg);
                
                let textMatch = false;
                if (textQuery === '') {
                    textMatch = true;
                } else {
                    const idVal = searchData[0] ? searchData[0].toLowerCase() : '';
                    const mfg = searchData[1] ? searchData[1].toLowerCase() : '';
                    const desc = searchData[5] ? searchData[5].toLowerCase() : '';
                    
                    if (desc.includes(textQuery) || mfg.includes(textQuery) || idVal.includes(textQuery)) {
                        textMatch = true;
                    } else {
                        for (let t of searchData) {
                            let tLow = t.toLowerCase();
                            if (tLow === textQuery || tLow.replace(/[^a-z0-9]/gi, '') === qFlat) { textMatch = true; break; }
                            try {
                                let regex = new RegExp('\\b' + textQuery.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '\\b');
                                if (regex.test(tLow)) { textMatch = true; break; }
                            } catch(e) {}
                        }
                    }
                }
                
                let tagsMatch = true;
                for (const group in activeFilters) {
                    if (activeFilters[group] !== 'all') {
                        let targetFlat = activeFilters[group].replace(/[^a-z0-9]/gi, '').toLowerCase();
                        if (group === 'mat') {
                            if (!searchData.some(s => s.toLowerCase().includes(activeFilters[group].toLowerCase()))) tagsMatch = false;
                        } else {
                            if (!searchData.some(s => s.replace(/[^a-z0-9]/gi, '').toLowerCase() === targetFlat)) tagsMatch = false;
                        }
                    }
                }
                
                if (mfgMatch && textMatch && tagsMatch) {
                    r.style.display = '';
                } else {
                    r.style.display = 'none';
                }
            });
            
            sections.forEach(sec => {
                if (sec.style.display === 'block') {
                    const visibleRows = sec.querySelectorAll('tr.lens-row:not([style*="display: none"])');
                    if (visibleRows.length === 0) sec.style.display = 'none';
                }
            });
        }

        if(searchInput) searchInput.addEventListener('input', updateDOM);

        if(btnAllLenses) {
            btnAllLenses.addEventListener('click', (e) => {
                e.preventDefault();
                mfgBadges.forEach(b => b.classList.remove('active'));
                btnAllLenses.classList.add('active');
                activeMfg = 'all';
                
                tagBadges.forEach(tb => {
                    if (tb.getAttribute('data-tag') === 'all') tb.classList.add('active');
                    else tb.classList.remove('active');
                });
                for (let g in activeFilters) activeFilters[g] = 'all';
                if(searchInput) searchInput.value = '';
                updateDOM();
            });
        }

        mfgBadges.forEach(badge => {
            badge.addEventListener('click', (e) => {
                e.preventDefault();
                if (badge.classList.contains('active')) {
                    badge.classList.remove('active');
                    activeMfg = 'all';
                    if(btnAllLenses) btnAllLenses.classList.add('active');
                } else {
                    mfgBadges.forEach(b => b.classList.remove('active'));
                    if(btnAllLenses) btnAllLenses.classList.remove('active');
                    badge.classList.add('active');
                    activeMfg = badge.getAttribute('data-val');
                }
                updateDOM();
            });
        });
        
        tagBadges.forEach(badge => {
            badge.addEventListener('click', (e) => {
                e.preventDefault();
                const tag = badge.getAttribute('data-tag');
                const group = badge.getAttribute('data-group');
                
                if (tag === 'all') {
                    document.querySelectorAll(`.tag-pill[data-group="${group}"]`).forEach(b => b.classList.remove('active'));
                    badge.classList.add('active');
                    activeFilters[group] = 'all';
                } else {
                    if (badge.classList.contains('active')) {
                        badge.classList.remove('active');
                        activeFilters[group] = 'all';
                        document.querySelector(`.tag-pill[data-group="${group}"][data-tag="all"]`).classList.add('active');
                    } else {
                        document.querySelectorAll(`.tag-pill[data-group="${group}"]`).forEach(b => b.classList.remove('active'));
                        badge.classList.add('active');
                        activeFilters[group] = tag;
                    }
                }
                updateDOM();
            });
        });
        
        updateDOM();
    }

    window.switchTab = function(tabIndex) {
        for (let i = 1; i <= 3; i++) {
            let btn = document.getElementById('tab-btn-' + i); if(btn) btn.className = 'tab inactive';
            let content = document.getElementById('tab-content-' + i); if(content) content.classList.remove('active');
        }
        let selectedBtn = document.getElementById('tab-btn-' + tabIndex); if(selectedBtn) selectedBtn.className = 'tab active';
        let selectedContent = document.getElementById('tab-content-' + tabIndex); if(selectedContent) selectedContent.classList.add('active');
    };

    window.toggleProgressive = function() {
        const lensTypeCode = document.getElementById('lens-type-code');
        const progressiveTypeRow = document.getElementById('progressive-type-row');
        if (lensTypeCode && progressiveTypeRow) progressiveTypeRow.style.display = (lensTypeCode.value.includes('6.')) ? 'flex' : 'none';
    };

    window.openModal = function(dataIndex) {
        const lens = window.activeViewData[dataIndex];
        if (!lens) return;
        
        let isFin = !!(lens.Specifications && lens.Specifications.FIN);
        let specArray = isFin ? lens.Specifications.FIN : lens.Specifications.SF;
        let isProg = parseInt(lens.Style) === 6;

        let idDisplay = lens.Id || '00000';
        let webDesc = isFin ? '*' + lens.Description : lens.Description;
        let lensTypeStr = "Single Vision";
        if(isProg) lensTypeStr = "Progressive";
        else if([2,3,4,5,8,9,10,11,12,15,16].includes(parseInt(lens.Style))) lensTypeStr = "Multi-Focal";
        
        let rep = specArray[0] || {};
        
        let opcs = Object.values(rep['OPC'] || {});
        let opcRange = "N/A";
        let opcMin = ""; let opcMax = "";
        if(opcs.length > 0) {
            let sortedOpc = opcs.sort();
            opcMin = sortedOpc[0];
            opcMax = sortedOpc[sortedOpc.length - 1];
            opcRange = opcMin + " to " + opcMax;
        }

        let modTitle = document.getElementById('mod-modern-title'); if(modTitle) modTitle.innerText = webDesc;
        let modSub = document.getElementById('mod-modern-sub'); if(modSub) modSub.innerText = `${lens.MFG || 'Unknown'} | ID: ${idDisplay}`;
        
        let mBentoMfg = document.getElementById('mod-bento-mfg'); if(mBentoMfg) mBentoMfg.innerText = lens.MFG || 'Unknown';
        let mBentoMat = document.getElementById('mod-bento-mat'); if(mBentoMat) mBentoMat.innerText = lens.Material;
        let mBentoIdx = document.getElementById('mod-bento-idx'); if(mBentoIdx) mBentoIdx.innerText = lens.Index;
        let mBentoType = document.getElementById('mod-bento-type'); if(mBentoType) mBentoType.innerText = lensTypeStr;
        let mBentoSeg = document.getElementById('mod-bento-seg'); if(mBentoSeg) mBentoSeg.innerText = rep.SEGW || rep['Seg Width'] || 'N/A';
        let mBentoInset = document.getElementById('mod-bento-inset'); if(mBentoInset) mBentoInset.innerText = `${rep.INSET || rep['Inset'] || '0.0'} / ${rep.DROP || rep['Drop'] || '0.0'}`;
        let mBentoPrp = document.getElementById('mod-bento-prp'); if(mBentoPrp) mBentoPrp.innerText = `${rep.PRPOUT || rep['PRP Out'] || '0.0'} / ${rep.PRPUP || rep['PRP Up'] || '0.0'}`;
        let mBentoOpc = document.getElementById('mod-bento-opc'); if(mBentoOpc) mBentoOpc.innerText = opcRange;
        
        let mid = document.getElementById('mod-id'); if(mid) mid.value = idDisplay;
        let mmfg = document.getElementById('mod-mfg'); if(mmfg) mmfg.value = lens.MFG || '';
        let mbrief = document.getElementById('mod-brief'); if(mbrief) mbrief.value = lens['Brief Description'] || '';
        let mlong = document.getElementById('mod-long'); if(mlong) mlong.value = lens['Long Description'] || '';
        
        let selStyle = parseInt(lens.Style);
        let elType = document.getElementById('lens-type-code');
        if(elType && !isNaN(selStyle)) { 
            elType.selectedIndex = selStyle; 
            const progRow = document.getElementById('progressive-type-row');
            if(progRow) progRow.style.display = selStyle === 6 ? 'flex' : 'none';
        }
        
        let mseg = document.getElementById('mod-seg-width'); if(mseg) mseg.value = rep.SEGW || rep['Seg Width'] || '';
        let mmatn = document.getElementById('mod-mat-name'); if(mmatn) mmatn.value = lens.Material || '';
        let mmatc = document.getElementById('mod-mat-cat'); if(mmatc) mmatc.innerHTML = `<option>${lens.Material}</option>`;
        let midx = document.getElementById('mod-idx'); if(midx) midx.value = lens.Index || '';
        
        let mopcr = document.getElementById('mod-opc-right'); if(mopcr) mopcr.value = opcMin;
        let mopcl = document.getElementById('mod-opc-left'); if(mopcl) mopcl.value = opcMax;
        
        let mbowl = document.getElementById('mod-bowl-dia'); if(mbowl) mbowl.value = rep.BOWLD || rep['Bowl Dia'] || '0';
        
        const ctcDict = {
            'Plastic (CR-39)': '2.2', 'Polycarbonate': '1.5', 'Trivex': '1.5',
            'High-Index 1.60': '1.4', 'High-Index 1.60 (MR-8)': '1.4', 'High-Index 1.60 (MR-8+)': '1.4',
            'High-Index 1.67': '1.4', 'High-Index 1.67 (MR-7)': '1.4', 'High-Index 1.67 (MR-10)': '1.4',
            'High-Index 1.74': '1.4'
        };
        let mminct = document.getElementById('mod-min-ct'); 
        if(mminct) mminct.value = ctcDict[lens.Material] || '';

        let mSurfHead = document.getElementById('mod-modern-surf-thead');
        let mThickHead = document.getElementById('mod-modern-thick-thead');
        if(mSurfHead && mThickHead) {
            if(isFin) {
                mSurfHead.innerHTML = `<tr><th style="background:var(--col-base);">Minus Sph</th><th style="background:var(--col-tfc);">Minus Cyl</th><th style="background:var(--win-highlight);">Plus Sph</th><th style="background:var(--col-tbc);">Plus Cyl</th></tr>`;
                mThickHead.innerHTML = `<tr><th style="background:var(--col-diam);">Diameter</th><th style="background:var(--col-idx);">CT</th></tr>`;
            } else {
                mSurfHead.innerHTML = `<tr><th style="background:var(--col-base);">Base</th><th style="background:var(--col-tfc);">Front TC</th><th style="background:var(--win-highlight);">Asph</th><th style="background:var(--col-tbc);">Back TC</th></tr>`;
                mThickHead.innerHTML = `<tr><th style="background:var(--col-diam);">Diameter</th><th style="background:var(--col-base);">Base</th><th style="background:var(--col-idx);">CT</th></tr>`;
            }
        }

        let surfHtml = '', thickHtml = '', blankHtml = '', modernSurf = '', modernThick = '';

        if (isFin) {
            let diamMap = {};
            specArray.forEach(s => {
                let diams = (s.Diameters && s.Diameters.length > 0) ? s.Diameters : ['N/A'];
                diams.forEach(d => {
                    if (!diamMap[d]) diamMap[d] = [];
                    diamMap[d].push({ sph: parseFloat(s.SPH)||0, cyl: parseFloat(s.CYL)||0 });
                });
            });
            
            let sortedDiams = Object.keys(diamMap).sort((a,b) => parseFloat(a) - parseFloat(b));
            let dCount = 0;
            sortedDiams.forEach(d => {
                let pArr = diamMap[d];
                let minSph = getRangeString(pArr.filter(p => p.sph <= 0 && p.cyl === 0), false);
                let minCyl = getRangeString(pArr.filter(p => p.sph <= 0 && p.cyl < 0), true);
                let pluSph = getRangeString(pArr.filter(p => p.sph > 0 && p.cyl === 0), false);
                let pluCyl = getRangeString(pArr.filter(p => p.sph > 0 && p.cyl < 0), true);
                
                modernSurf += `<tr><td>${minSph}</td><td>${minCyl}</td><td>${pluSph}</td><td>${pluCyl}</td></tr>`;
                modernThick += `<tr><td>${d}</td><td>-</td></tr>`;
                
                if(dCount < 12) {
                    surfHtml += `<tr><td>&nbsp;</td><td></td><td></td><td></td></tr>`;
                    thickHtml += `<tr><td><span class="arrow-indicator" style="color: #cc0000; font-size: 9px;">&#9654;</span> ${d}</td><td>-</td><td>-</td></tr>`;
                    dCount++;
                }
            });
            
            for(let j=dCount; j<12; j++) {
                surfHtml += `<tr><td>&nbsp;</td><td></td><td></td><td></td></tr>`;
                thickHtml += `<tr><td>&nbsp;</td><td></td><td></td></tr>`;
            }
            
        } else {
            let uniqueCurves = new Map(); let uniqueDiams = new Map();
            let asphFactor = isProg ? '-0.50' : '.50';

            specArray.forEach(r => {
                let bRaw = parseFloat(r['BASE']);
                let b = isNaN(bRaw) ? '' : bRaw.toFixed(2);
                let ftc = parseFloat(r.TRUE_FRONT || r['Front TC']); ftc = isNaN(ftc) ? '' : ftc.toFixed(2);
                let btc = parseFloat(r.TRUE_BACK || r['Back TC']); btc = isNaN(btc) ? '' : btc.toFixed(2);
                let ct = parseFloat(r.CT || r['Center Thick']); ct = isNaN(ct) ? '' : ct.toFixed(2);
                
                if (b) {
                    if (!uniqueCurves.has(b)) uniqueCurves.set(b, {b, ftc, btc, asphFactor});
                    (r.Diameters || []).forEach(dia => {
                        let diamKey = `${dia}-${b}`;
                        if (!uniqueDiams.has(diamKey)) uniqueDiams.set(diamKey, {dia, b, ct, inset: r.INSET || r.Inset || '', drop: r.DROP || r.Drop || ''});
                    });
                }
            });

            let sortedCurves = Array.from(uniqueCurves.values()).sort((x,y) => parseFloat(x.b) - parseFloat(y.b));
            let sortedDiams = Array.from(uniqueDiams.values()).sort((x,y) => {
                if(parseFloat(x.dia) === parseFloat(y.dia)) return parseFloat(x.b) - parseFloat(y.b);
                return parseFloat(x.dia) - parseFloat(y.dia);
            });

            for(let j=0; j<12; j++) {
                if (j < sortedCurves.length) {
                    let c = sortedCurves[j];
                    surfHtml += `<tr><td>${c.b}</td><td>${c.ftc}</td><td>${c.asphFactor}</td><td>${c.btc}</td></tr>`;
                    modernSurf += `<tr><td>${c.b}</td><td>${c.ftc}</td><td>${c.asphFactor}</td><td>${c.btc}</td></tr>`;
                } else { surfHtml += `<tr><td>&nbsp;</td><td></td><td></td><td></td></tr>`; }
            }

            for(let j=0; j<12; j++) {
                if(j < sortedDiams.length) {
                    let d = sortedDiams[j];
                    thickHtml += `<tr><td><span class="arrow-indicator" style="color: #cc0000; font-size: 9px;">&#9654;</span> ${d.dia}</td><td>${d.b}</td><td>${d.ct !== 'NaN' ? d.ct : ''}</td></tr>`;
                    modernThick += `<tr><td>${d.dia}</td><td>${d.b}</td><td>${d.ct !== 'NaN' ? d.ct : ''}</td></tr>`;
                } else { thickHtml += `<tr><td>&nbsp;</td><td></td><td></td></tr>`; }
            }

            let printedDiamsForBlank = new Set(); let bCount = 0;
            sortedDiams.forEach(d => {
                if(!printedDiamsForBlank.has(d.dia) && bCount < 5) {
                    blankHtml += `<tr><td>${d.dia}</td><td>${d.inset !== 'NaN' ? parseFloat(d.inset).toFixed(2) : ''}</td><td>${d.drop !== 'NaN' ? parseFloat(d.drop).toFixed(2) : ''}</td><td>17.00</td></tr>`;
                    printedDiamsForBlank.add(d.dia); bCount++;
                }
            });
            for(let j=bCount; j<7; j++) blankHtml += `<tr><td>&nbsp;</td><td></td><td></td><td></td></tr>`;
        }
        
        let modSurfBody = document.getElementById('mod-surf-tbody'); if(modSurfBody) modSurfBody.innerHTML = surfHtml;
        let modThickBody = document.getElementById('mod-thick-tbody'); if(modThickBody) modThickBody.innerHTML = thickHtml;
        let modBlankBody = document.getElementById('mod-blank-tbody'); if(modBlankBody && !isFin) modBlankBody.innerHTML = blankHtml;
        let mModSurf = document.getElementById('mod-modern-surf'); if(mModSurf) mModSurf.innerHTML = modernSurf;
        let mModThick = document.getElementById('mod-modern-thick'); if(mModThick) mModThick.innerHTML = modernThick;

        let tabColorArr = Array.from(lens.Colors || []);
        if(tabColorArr.length === 0) tabColorArr.push('CLEAR');
        
        let rawCoatArr = Array.from(lens.Coatings || []);
        if(rawCoatArr.length === 0) rawCoatArr.push('UNCOATED');
        let modalCoats = [];
        rawCoatArr.forEach(c => {
            if(c.includes('/')) { modalCoats.push(...c.split('/').map(x => x.trim())); }
            else { modalCoats.push(c); }
        });
        modalCoats = Array.from(new Set(modalCoats));
        
        let colorsHtml = '', coatsHtml = '';
        
        for(let j=0; j<16; j++) {
            let cText = j < tabColorArr.length ? tabColorArr[j].toUpperCase() : '&nbsp;';
            colorsHtml += `<tr><td>${cText}</td><td>&nbsp;</td></tr>`;
            let coatText = j < modalCoats.length ? modalCoats[j].toUpperCase() : '&nbsp;';
            coatsHtml += `<tr><td>${coatText}</td><td>&nbsp;</td></tr>`;
        }
        let modColBody = document.getElementById('mod-col-tbody'); if(modColBody) modColBody.innerHTML = colorsHtml;
        let modCoatBody = document.getElementById('mod-coat-tbody'); if(modCoatBody) modCoatBody.innerHTML = coatsHtml;

        switchTab(1); 
        let modalOverlay = document.getElementById('tech-modal');
        if(modalOverlay) modalOverlay.classList.remove('hidden');
    };

    window.closeModal = function() { 
        const m = document.getElementById('tech-modal');
        if(m) m.classList.add('hidden'); 
    };

    const modalOverlay = document.getElementById('tech-modal');
    if(modalOverlay) {
        modalOverlay.addEventListener('click', (e) => {
            if(e.target === modalOverlay) closeModal();
        });
    }

});
"""
        with open(os.path.join(HTML_DATA_DIR, 'app.js'), 'w', encoding='utf-8') as f:
            f.write(js_content.strip())

        # ----- DIRECT HTML WRITE ----- #
        html_content = """
<!DOCTYPE html>
<html lang="en" data-modal-layout="modern">
<head>
    <meta charset="UTF-8">
    <title>VCA Vault Hub</title>
    <link rel="stylesheet" href="data/styles.css">
</head>
<body>
    <header class="top-bar">
        <div class="top-bar-left">
            <span class="brand-title">VCA2HTML-TUI</span>
            <span class="brand-sub">ENGINE v{{VERSION}}</span>
        </div>
        <div class="top-bar-center">
            MASTER LENS DATABASE
        </div>
        <div class="top-bar-right">
            <div class="dropdown-row">
                <span class="dd-icon" title="Font Size">󰚺</span>
                <select id="fontsize-select" class="header-dropdown" style="width: 100px;">
                    <option value="12">12px</option><option value="13">13px</option><option value="14">14px</option>
                    <option value="15">15px</option><option value="16">16px</option><option value="18">18px</option>
                    <option value="20">20px</option>
                </select>
                <span class="dd-icon" title="Modal Layout">󰒓</span>
                <select id="layout-select" class="header-dropdown" style="width: 120px;">
                    <option value="legacy">LMS Layout</option>
                    <option value="modern">Grid Layout</option>
                </select>
            </div>
        </div>
    </header>
    
    <div class="stats-bar" id="stats-container">
        <div style="display: flex; width: 100%; align-items: center; justify-content: flex-start; margin-bottom: 5px;">
            <a href="#" class="mfg-pill active" id="btn-all-lenses" style="padding: 10px 28px; font-size: 16px;" data-group="mfg" data-val="all">ALL LENSES</a>
        </div>
        <div class="filter-row" id="pill-row-mfg" style="justify-content: center; margin-bottom: 15px; border-bottom: 1px solid var(--border-dark); padding-bottom: 15px;"></div>
        <div class="filter-row row-type" id="pill-row-type"></div>
        <div class="filter-row row-mat" id="pill-row-mat"></div>
        <div class="filter-row row-tech" id="pill-row-tech"></div>
        <div class="filter-row row-color" id="pill-row-color"></div>
        <div class="filter-row row-coat" id="pill-row-coat"></div>
        
        <div class="search-container">
            <input type="text" id="text-search-box" class="search-box" placeholder="Search Tags, Description, ID...">
        </div>
    </div>
    
    <main id="table-container"></main>
    
    <div class="modal-overlay hidden" id="tech-modal">
        <div class="dialog-box outset-border">
            <div class="title-bar">
                <div class="title-bar-left"><div class="faux-icon">VLP</div><span class="title-text">Lens Blank Specifications</span></div>
                <div class="title-bar-right"><span class="version-text">v{{VERSION}}</span><button class="title-bar-close" onclick="closeModal()">X</button></div>
            </div>
            <div class="tabs-container">
                <div class="tab-buttons">
                    <div class="tab active" id="tab-btn-1" onclick="switchTab(1)">Surfacing Specs</div>
                    <div class="tab inactive" id="tab-btn-2" onclick="switchTab(2)">Colors and Coatings</div>
                    <div class="tab inactive" id="tab-btn-3" onclick="switchTab(3)">Thickness Chart</div>
                </div>
            </div>
            <div class="dialog-content-wrapper">
                <div id="tab-content-1" class="tab-pane active">
                    <div class="grid-3-col">
                        <div style="margin-top: 5px;">
                            <div class="form-row"><label>Unique ID Code</label><input type="text" id="mod-id" class="inset-border" readonly></div>
                            <div class="form-row"><label>Manufacturer</label><input type="text" id="mod-mfg" class="inset-border fixed-width" style="width: 100px;"></div>
                            <div class="form-row"><label>Brief Description</label><input type="text" id="mod-brief" class="inset-border fixed-width" style="width: 150px;"></div>
                            <div class="form-row"><label>Long Description</label><div style="position: relative; flex-grow: 1; height: 19px;"><input type="text" id="mod-long" class="inset-border" style="position: absolute; left: 0; top: 0; width: 275px; z-index: 10;"></div></div>
                            <div class="form-row"><label>Lens Type Code</label><select class="inset-border" id="lens-type-code" onchange="toggleProgressive()">
                                <option>0. None</option><option>1. Single Vision</option><option>2. Flat Top Bif</option><option>3. Round Bif</option><option>4. Exec Bif</option><option>5. Exec Bif</option><option>6. Progressive</option><option>7. Blend Seg</option><option>8. FT Dble Seg</option><option>9. Exec Dble Seg</option><option>10. FT Trif</option><option>11. Exec Trif</option><option>12. ED Trif</option><option>13. Other SV</option><option>14. Asph SV</option><option>15. Asph FT</option><option>16. Asph Rnd</option><option>17. Asph Ultex</option><option>18. Other Multi-focal</option>
                            </select></div>
                            <div class="form-row" id="progressive-type-row" style="display:none;"><label>Progressive Type</label><select class="inset-border"><option>Generic</option><option selected>Type 2</option></select></div>
                            <div class="form-row"><label>Seg Width</label><input type="text" id="mod-seg-width" class="inset-border fixed-width" style="width: 25px;"></div>
                            <div class="form-row"><label>Material Name</label><input type="text" id="mod-mat-name" class="inset-border"></div>
                            <div class="form-row"><label>Material Category</label><select class="inset-border" id="mod-mat-cat"></select></div>
                            <div class="form-row"><label>Material Index</label><input type="text" id="mod-idx" class="inset-border fixed-width" style="width: 65px;"></div>
                            <div class="form-row"><label>Rights and Lefts?</label><select class="inset-border fixed-width" id="mod-rl-sel" style="width: 65px;"></select></div>
                            <div class="form-row"><label>Vertical OC Position</label><select class="inset-border"><option selected>Automatic</option><option>MM Above</option><option>MM Below</option><option>Even with GC</option></select></div>
                            <div class="form-row"><label>Lenticular Field Size</label><input type="text" id="mod-bowl-dia" class="inset-border fixed-width" style="width: 25px;"></div>
                            <div class="form-row" style="margin-top: 36px;"><label>Minus Center Thick</label><input type="text" id="mod-min-ct" class="inset-border fixed-width" style="width: 65px;"></div>
                            <div class="form-row" style="margin-top: 14px;"><label style="line-height: 1.2; width: 110px;">True Curve<br>Reference Index if<br>not standard 1.530</label><input type="text" class="inset-border fixed-width" value="1.530" style="width: 65px;"></div>
                        </div>
                        <div>
                            <div style="display: flex; justify-content: flex-end; margin-bottom: 24px;">
                                <table style="border-collapse: collapse;"><tr><td style="text-align: left; padding-bottom: 4px; padding-right: 5px;">Preferred Supplier?</td><td style="padding-bottom: 4px;"><select class="inset-border" style="width: 45px;"><option selected>No</option><option>Yes</option></select></td></tr><tr><td style="text-align: left; padding-bottom: 4px; padding-right: 5px;">On-Line Locally?</td><td style="padding-bottom: 4px;"><select class="inset-border" style="width: 45px;"><option selected>No</option><option>Yes</option></select></td></tr><tr><td style="text-align: left; padding-bottom: 4px; padding-right: 5px;">On-Line Remotely?</td><td style="padding-bottom: 4px;"><select class="inset-border" style="width: 45px;"><option selected>No</option><option>Yes</option></select></td></tr></table>
                            </div>
                            <table class="classic-table grid-lines" style="width: 195px; margin: 22px auto 4px auto;"><thead><tr><th>Marked<br>Base</th><th>True<br>Curve</th><th>Asph<br>Factor</th><th>Minus<br>Back</th></tr></thead><tbody id="mod-surf-tbody"></tbody></table>
                            <div style="text-align: center; margin-top: 13px;"><div style="margin-bottom: 3px;">Product OPC Range</div><input type="text" id="mod-opc-right" class="inset-border fixed-width" style="width: 80px;"><span style="margin: 0 4px;">To</span><input type="text" id="mod-opc-left" class="inset-border fixed-width" style="width: 80px;"></div>
                        </div>
                        <div>
                            <table class="classic-table grid-lines" style="width: calc(100% - 40px); margin: 0 auto 12px auto;"><thead><tr><th>Blank<br>Size</th><th>Inset</th><th>Drop</th><th>Reading<br>Level</th></tr></thead><tbody id="mod-blank-tbody"></tbody></table>
                            <fieldset><legend>Custom Settings</legend><table style="width: 100%; border-collapse: collapse; margin-bottom: 8px;"><tr><td style="width: 135px; padding-bottom: 4px; text-align: left;">Fining Allowance:</td><td style="width: 35px; padding-bottom: 4px;"><input type="text" class="inset-border fixed-width" style="width: 30px;"></td><td style="padding-bottom: 4px; text-align: left;">&nbsp;&nbsp;mm</td></tr><tr><td style="padding-bottom: 4px; text-align: left;">Global Power Adjust</td><td style="padding-bottom: 4px;"><input type="text" class="inset-border fixed-width" style="width: 30px;"></td><td style="padding-bottom: 4px; text-align: left;">&nbsp;&nbsp;diopters</td></tr><tr><td style="padding-bottom: 4px; text-align: left;">Lens Flex Power Adjust</td><td style="padding-bottom: 4px;"><input type="text" class="inset-border fixed-width" style="width: 30px;"></td><td style="padding-bottom: 4px; text-align: left;">&nbsp;&nbsp;diopters</td></tr></table><div class="inset-border" style="background: #ece9d8; padding: 4px; margin-top: 4px; font-size: 10px; line-height: 1.3;">Note: Enter a special fining allowance only if this lens requires a different value than the .300 mm allowance currently specified for CR-39 in the Lab Setup Menu.</div></fieldset>
                            <div style="text-align: center; margin-top: 26px;"><button class="win-btn outset-border" style="width: 150px; padding: 4px 0;">Click Here to Set Prices</button></div>
                        </div>
                    </div>
                </div>
                <div id="tab-content-2" class="tab-pane"><div class="grid-2-col" style="height: calc(100% - 10px);"><div><table class="classic-table grid-lines" style="width: 100%; height: 100%;"><thead><tr><th style="width: 60%;">Factory Colors</th><th style="width: 40%;">Pair Price</th></tr></thead><tbody id="mod-col-tbody"></tbody></table></div><div><table class="classic-table grid-lines" style="width: 100%; height: 100%;"><thead><tr><th style="width: 60%;">Factory Coatings</th><th style="width: 40%;">Pair Price</th></tr></thead><tbody id="mod-coat-tbody"></tbody></table></div></div></div>
                <div id="tab-content-3" class="tab-pane"><div class="center-col" style="height: calc(100% - 10px);"><div style="width: 500px;"><table class="classic-table grid-lines" style="width: 100%;"><thead><tr><td colspan="3" class="table-title">Blank Thickness Table</td></tr><tr><th style="width: 30%;">Diameter</th><th style="width: 35%;">Base</th><th style="width: 35%;">Center Thickness</th></tr></thead><tbody id="mod-thick-tbody"></tbody></table><div style="text-align: center; margin-top: 15px; font-size: 11px; color: #808080;">Left click any center thickness value you want to change.</div></div></div></div>
            </div>
            <div class="footer"><button class="win-btn outset-border">Print This Form</button><div style="font-weight: bold;">Warning: Incorrect data in this form will cause calculations errors!</div><div><button class="win-btn outset-border" onclick="closeModal()">Cancel</button><button class="win-btn outset-border" onclick="closeModal()">Save</button></div></div>
        </div>

        <div class="modern-box">
            <div class="modern-header">
                <div>
                    <h2 class="modern-title" id="mod-modern-title">Lens Description</h2>
                    <div class="modern-subtitle" id="mod-modern-sub">MFG / ID</div>
                </div>
                <button class="modern-close" onclick="closeModal()">✖</button>
            </div>
            <div class="bento-grid">
                <div class="bento-card" style="border-top-color: var(--col-mat);">
                    <div class="b-title" style="color:var(--col-mat)">Identity</div>
                    <div class="b-row"><span>MFG:</span> <b id="mod-bento-mfg"></b></div>
                    <div class="b-row"><span>Material:</span> <b id="mod-bento-mat"></b></div>
                    <div class="b-row"><span>Index:</span> <b id="mod-bento-idx"></b></div>
                </div>
                <div class="bento-card" style="border-top-color: var(--col-idx);">
                    <div class="b-title" style="color:var(--col-idx)">Geometry</div>
                    <div class="b-row"><span>Type:</span> <b id="mod-bento-type"></b></div>
                    <div class="b-row"><span>Seg Width:</span> <b id="mod-bento-seg"></b></div>
                    <div class="b-row"><span>Inset / Drop:</span> <b id="mod-bento-inset"></b></div>
                </div>
                <div class="bento-card" style="border-top-color: var(--col-coat);">
                    <div class="b-title" style="color:var(--col-coat)">Lab Settings</div>
                    <div class="b-row"><span>True Curve Ref:</span> <b>1.530</b></div>
                    <div class="b-row"><span>PRP (Out/Up):</span> <b id="mod-bento-prp"></b></div>
                    <div class="b-row"><span>Fining Allowance:</span> <b>-</b></div>
                </div>
                <div class="bento-card" style="border-top-color: var(--col-filt);">
                    <div class="b-title" style="color:var(--col-filt)">OPC Codes</div>
                    <div class="b-row"><span>Range:</span> <b id="mod-bento-opc"></b></div>
                </div>
            </div>
            <div class="modern-grids">
                <div class="modern-table-wrap">
                    <table id="mod-modern-surf-table"><thead id="mod-modern-surf-thead"><tr><th style="background:var(--col-base);">Base</th><th style="background:var(--col-tfc);">Front TC</th><th style="background:var(--win-highlight);">Asph</th><th style="background:var(--col-tbc);">Back TC</th></tr></thead><tbody id="mod-modern-surf"></tbody></table>
                </div>
                <div class="modern-table-wrap">
                    <table id="mod-modern-thick-table"><thead id="mod-modern-thick-thead"><tr><th style="background:var(--col-diam);">Diameter</th><th style="background:var(--col-base);">Base</th><th style="background:var(--col-idx);">CT</th></tr></thead><tbody id="mod-modern-thick"></tbody></table>
                </div>
            </div>
        </div>
    </div>
    
    <script src="data/db/manifest.js"></script>
    <script src="data/db/database.js"></script>
    <script src="data/app.js"></script>
</body></html>
"""
        html_content = html_content.replace('{{VERSION}}', global_version)
        with open(os.path.join(HTML_DIR, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(html_content.strip())
            
        ctx['log_lines'].append("  -> Output written successfully. Templates completely bypassed.")

        # ----- PAYLOAD GENERATION & FILTER TAG SCRUB ----- #
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            db_data = json.load(f)
        
        lenses = db_data.get('lenses', {})
        if not lenses: return
            
        web_lenses = list(lenses.values())
        
        blue_terms = {"blue filter", "blueguard", "blue-guard", "blue protect", "clear blue filter", "cbf", "blue capture", "blue uv capture", "hev", "uv420"}
        tech_whitelist = {"photochromic", "photofusion", "q-change", "transitions", "liferx", "polarized", "nupolar", "uv", "uvri", "uv protect", "drivesafe"}

        ctx['log_lines'].append(f"[~] Formatting {len(web_lenses)} lenses for Web Delivery...")
        
        for lens_obj in web_lenses:
            raw_tags = lens_obj.get("FilterTags", [])
            pure_filters = []
            
            # Identify Blue variations and push them strictly to FilterTags (not pills)
            has_blue = any(b in tag.lower() for tag in raw_tags for b in blue_terms)
            if has_blue and "Blue Filter" not in lens_obj["FilterTags"]:
                lens_obj["FilterTags"].append("Blue Filter")
                
            for tag in raw_tags:
                t_low = tag.lower()
                if t_low in tech_whitelist:
                    pure_filters.append(tag)
            
            if has_blue:
                pure_filters.append("Blue Filter")
            
            if pure_filters:
                lens_obj["Filter"] = "<br>".join(sorted(list(set(pure_filters))))
            else:
                lens_obj["Filter"] = '<span style="opacity:0.5;">None</span>'
                
            # Safely handle the "NONE" edge case inside colors
            lens_colors = lens_obj.get("Colors", [])
            if "NONE" in lens_colors:
                lens_colors.remove("NONE")
                if "Clear" not in lens_colors: lens_colors.append("Clear")
            lens_obj["Colors"] = lens_colors
            
            # Inject empty ID safeguard
            if "Id" not in lens_obj:
                lens_obj["Id"] = "00000"

        # The Single Payload Engine
        ctx['log_lines'].append("[+] Base64 Encoding master database payload...")
        draw_throttle(term_w, term_h, ctx, 50.0, "Encoding Payload...", 1, 2)
        
        json_string = json.dumps(web_lenses, separators=(',', ':'))
        b64_bytes = base64.b64encode(json_string.encode('utf-8'))
        b64_string = b64_bytes.decode('utf-8')
        
        db_hash = hashlib.sha256(b64_bytes).hexdigest()
        
        db_filename = "database.js"
        db_path = os.path.join(HTML_DB_DIR, db_filename)
        with open(db_path, 'w', encoding='utf-8') as f:
            f.write(f'window.dbPayload = "{b64_string}";\n')
            
        ctx['log_lines'].append(f"  -> Payload [ {db_filename} ] written ({os.path.getsize(db_path) / (1024*1024):.2f} MB)")
        
        master_sig = "UNSIGNED"
        if os.path.exists(SIG_FILE):
            with open(SIG_FILE, 'r') as sf: master_sig = sf.read().strip()
                
        manifest_data = {
            "masterSignature": master_sig, 
            "compiled_at": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            "dbHash": db_hash
        }
        
        ctx['log_lines'].append("[!] Injecting HTML security manifest directly into Master Vault...")
        db_data['manifest'] = manifest_data
        
        if 'shards' in db_data: db_data.pop('shards', None)
        if '__security_manifest__' in db_data: db_data.pop('__security_manifest__', None)
        
        try: os.chmod(DB_FILE, stat.S_IWRITE)
        except: pass
        with open(DB_FILE, 'w', encoding='utf-8') as f: json.dump(db_data, f, indent=4)
        try: os.chmod(DB_FILE, stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)
        except: pass
        
        manifest_path = os.path.join(HTML_DB_DIR, 'manifest.js')
        with open(manifest_path, 'w', encoding='utf-8') as f:
            f.write(f"const securityManifest = {json.dumps(manifest_data, indent=4)};\n")
            
        ctx['log_lines'].append("[✓] SSG Payload cryptographically sealed.")
        
        draw_throttle(term_w, term_h, ctx, 100.0, "Deployment Complete", 2, 2, is_done=True)
        
        ctx['log_lines'].append("")
        ctx['log_lines'].append("=" * 50)
        ctx['log_lines'].append("[ PROCESS COMPLETE ] Press [RETURN] to Continue...")
        ctx['log_lines'].append("=" * 50)
        
    except Exception as e:
        ctx['log_lines'].append(f"[!] FATAL DEPLOYMENT ERROR: {e}")
        draw_throttle(term_w, term_h, ctx, 100.0, "ERROR", 2, 2, is_done=True)

# ----- Master Loop. Master Sword. ----- #

def bootloader(term_w, term_h):
    draw_skeleton("OPTICAL LENS SPECIFICATIONS ENGINE", "License & Disclaimer")
    
    start_row = 4
    
    # ----- Center the ASCII Art ----- #
    for i, line in enumerate(ascii_art):
        pad = max(1, (term_w - len(line)) // 2)
        sys.stdout.write(f"\033[{start_row + i};{pad}H{line}")
    
    # ----- Pad 85% for text ----- #
    text_w = int(term_w * 0.85)
    pad_left = max(1, (term_w - text_w) // 2)
    
    # ----- Rows to start text under ASCII ----- #
    row = start_row + len(ascii_art) + 2
    
    for line in textwrap.wrap(GLOBAL_LICENSE, width=text_w):
        sys.stdout.write(f"\033[{row};{pad_left}H{line}")
        row += 1
        
    row += 2 
    
    for line in textwrap.wrap(GLOBAL_DISCLAIMER, width=text_w):
        sys.stdout.write(f"\033[{row};{pad_left}H{line}") 
        row += 1
        
    row += 3
    prompt = "Press (Y) to Accept Terms and Continue, or any other key to quit."
    pad_prompt = max(1, (term_w - len(prompt)) // 2)
    sys.stdout.write(f"\033[{row};{pad_prompt}H{prompt}")

def main_menu(term_w, term_h):
    draw_skeleton("OPERATIONS CENTER", "Main Menu Active")
    sys.stdout.write("\033[4;5H(C)onvert Files")
    sys.stdout.write("\033[5;5H(A)dd to Vault")
    sys.stdout.write("\033[6;5H(G)enerate Database")
    sys.stdout.write("\033[7;5H(B)uild Web Application")
    sys.stdout.write("\033[8;5H(Q)uit Application")

def init_env():
    os.makedirs(IMPORT_DIR, exist_ok=True)
    os.makedirs(ORIGINALS_DIR, exist_ok=True)
    os.makedirs(VAULT_DIR, exist_ok=True)
    os.makedirs(PURGED_DIR, exist_ok=True)
    os.makedirs(CORRUPT_DIR, exist_ok=True)
    os.makedirs(TEMP_DIR, exist_ok=True)
    os.makedirs(HTML_DB_DIR, exist_ok=True)
    os.makedirs(HTML_FONT_DIR, exist_ok=True)

def master_loop():
    current_state = "BOOTLOADER"
    last_state = ""
    ctx = {}
    
    last_term_w, last_term_h = 0, 0
    force_redraw = True
    
    # ----- Alternate Screen / Hide Cursor ----- #
    sys.stdout.write("\033[?1049h\033[?25l\033[2J")
    
    try:
        while True:
            if not check_term_size():
                warn_term_size()
                force_redraw = True
                
            term_w, term_h = get_term_size()
            if term_w != last_term_w or term_h != last_term_h:
                force_redraw = True
                last_term_w, last_term_h = term_w, term_h
                sys.stdout.write("\033[2J")
                
            # Flawless transition screen wipe
            if current_state != last_state:
                sys.stdout.write("\033[2J\033[H")
                last_state = current_state
                force_redraw = True
                
            if force_redraw:
                sys.stdout.write("\033[H")
                
                if current_state == "BOOTLOADER":
                    bootloader(term_w, term_h)
                elif current_state == "MAIN_MENU":
                    main_menu(term_w, term_h)
                elif current_state == "FILE_MGR":
                    update_file_mgr_data(term_h, ctx) # ----- Resolves race condition ----- #
                    file_mgr(term_w, term_h, ctx)
                elif current_state == "PLAYBACK":
                    draw_playback(term_w, term_h, ctx)
                    
                sys.stdout.flush()
                force_redraw = False
                
            ch = getch_timeout(POLL_RATE)
            
            if ch is None:
                continue 
                
            force_redraw = True 
            
            if current_state == "BOOTLOADER":
                if ch.lower() == 'y':
                    init_env() # ----- Initialize on accept ----- #
                    current_state = "MAIN_MENU"
                else:
                    response = draw_z_modal("TERMS & CONDITIONS", "Press (Y) to agree or any key to quit.", False, bootloader, single_key=True)
                    if response and response.lower() == 'y':
                        init_env() # ----- Initialize on accept ----- #
                        current_state = "MAIN_MENU"
                    else:
                        return # Escapes to finally block
                        
            elif current_state == "MAIN_MENU":
                if ch.lower() == 'c':
                    ctx = {
                        'ldir': os.path.abspath(os.getcwd()),
                        'clip': [], 'lpage': 0, 'rpage': 0,
                        'user_input': "", 'warning_msg': "",
                        'action_cmd': "CONVERT",
                        'next_state': "PLAYBACK" 
                    }
                    current_state = "FILE_MGR"
                elif ch.lower() == 'a':
                    ctx = {
                        'ldir': IMPORT_DIR,
                        'locked_dir': IMPORT_DIR,
                        'clip': [], 'lpage': 0, 'rpage': 0,
                        'user_input': "", 'warning_msg': "",
                        'action_cmd': "ADD",
                        'next_state': "PLAYBACK"
                    }
                    current_state = "FILE_MGR"
                elif ch.lower() == 'g':
                    ctx = {
                        'pb_title': "Database Engine",
                        'pb_action': "( COMPILING JSON )",
                        'pb_frame': "ATOMIC MATRIX COMPILATION",
                        'pace_min': 0.01,  
                        'pace_max': 0.03,  
                        'log_lines': []
                    }
                    sys.stdout.write("\033[?25l")
                    vca_generate_db(ctx, term_w, term_h)
                    current_state = "PLAYBACK"
                elif ch.lower() == 'b':
                    ctx = {
                        'pb_title': "STATIC SITE GENERATOR",
                        'pb_frame': "HTML DEPLOYMENT",
                        'log_lines': []
                    }
                    sys.stdout.write("\033[?25l")
                    vca_generate_html(ctx, term_w, term_h)
                    current_state = "PLAYBACK"
                elif ch.lower() == 'q' or ch == 'ESC':
                    return 
                    
            elif current_state == "FILE_MGR":
                update_file_mgr_data(term_h, ctx)
                action = file_mgr_input(ch, ctx)
                if action == "EXIT":
                    current_state = "MAIN_MENU"
                elif action == "CONVERT":
                    ctx['pb_title'] = "Convert VCA"
                    ctx['pb_action'] = "File Review"
                    ctx['pb_frame'] = "Convert MFG VCA File for Sanitation"
                    ctx['pace_min'] = 0.8  
                    ctx['pace_max'] = 1.2  
                    vca_parse_data(ctx, term_w, term_h)
                    current_state = "PLAYBACK"
                elif action == "ADD":
                    ctx['pb_title'] = "Vault Gatekeeper"
                    ctx['pb_action'] = "( AUDITING )"
                    ctx['pb_frame'] = "ATOMIC BATCH CLEARANCE"
                    ctx['pace_min'] = 0.4  
                    ctx['pace_max'] = 0.8  
                    vca_add_data(ctx, term_w, term_h)
                    current_state = "PLAYBACK"
            
            elif current_state == "PLAYBACK":
                action = playback_input(ch, ctx, term_h)
                if action == "EXIT":
                    current_state = "MAIN_MENU"
                    
    finally:
        # ----- Close Alternate Screen / Restore Cursor ----- #
        sys.stdout.write("\033[?1049l\033[?25h\033[2J\033[H")
        sys.stdout.flush()

if __name__ == "__main__":
    master_loop()