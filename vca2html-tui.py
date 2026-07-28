#!/usr/bin/env python3
# ==============================================================================
# VCA2HTML-TUI v3.3.0 (Ultimate Optical Engine)
# OPTICAL LENS DATABASE ENGINE
# ==============================================================================

import os
import sys
import time
import shutil
import re
import textwrap
import platform
import warnings
import atexit
import json
import stat
import hashlib
import base64
import zipfile
import urllib.request as urllib
from datetime import datetime, timezone

# Global placeholders for the Tier-2 heavyweights
pd = None
np = None
openpyxl = None

# Suppress background warnings that destroy TUI coordinates
#warnings.filterwarnings("ignore", category=FutureWarning)
#warnings.filterwarnings("ignore", category=DeprecationWarning)

#def clean_teardown():
#    """Guarantees the terminal is wiped and color reset on exit/crash."""
#    sys.stdout.write("\033[2J\033[H\033[0m")
#    sys.stdout.flush()

#atexit.register(clean_teardown)

# --- DEPENDENCY CHECK ---
missing_modules = []
try: 
    import pandas as pd
except ImportError: 
    missing_modules.append("pandas")
try: 
    import numpy as np
except ImportError: 
    missing_modules.append("numpy")
try:
    import openpyxl
except ImportError:
    missing_modules.append("openpyxl")

if os.name == 'nt':
    try: 
        import msvcrt
    except ImportError: 
        missing_modules.append("msvcrt")
else:
    try: 
        import tty, termios, select
    except ImportError: 
        missing_modules.append("tty/termios")

if missing_modules:
    print(f"\033[31m[FATAL] Missing required libraries: {', '.join(missing_modules)}\033[0m")
    print(f"\033[33mRun: pip install {', '.join(missing_modules)}\033[0m")
    sys.exit(1)

# Directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DB_DIR = os.path.join(DATA_DIR, 'db')
CONFIG_FILE = os.path.join(DB_DIR, '.config')
IMPORT_DIR = os.path.join(DATA_DIR, 'import')
ORIGINALS_DIR = os.path.join(DATA_DIR, 'originals')
VLP_ARCHIVE = os.path.join(DB_DIR, '.vlp')
PURGED_DIR = os.path.join(DB_DIR, 'purged')        
CORRUPT_DIR = os.path.join(DB_DIR, 'corrupt')      
HTML_DIR = os.path.join(DATA_DIR, 'HTML')
HTML_DATA_DIR = os.path.join(HTML_DIR, 'data')
HTML_DB_DIR = os.path.join(HTML_DATA_DIR, 'db')
TMP_DIR = os.path.join(DATA_DIR, '.tmp')
DB_FILE = os.path.join(DB_DIR, 'master_lens_db.json')
ICONS_FILE = os.path.join(DB_DIR, '.icons')
SIG_FILE = os.path.join(DB_DIR, '.sig')

app_config = {
    "nerd_fonts": False,
    "theme": "tokyo_night",  # Default fallback
    "admin_enabled": True,   
    "sys_auth": "c94bec1f5512d6508e50fcd325635357b3c25e90f07ac5635801dd536486bb84"
}

# Ghost-load the config file before the UI ever draws
if os.path.exists(CONFIG_FILE):
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            app_config.update(json.load(f))
    except Exception:
        pass # If config is corrupted or empty, we silently fall back to defaults

THEME_MATRIX = {
    "tokyo_night": {
        "bg": "26;27;38", "bglight": "33;35;55", "border": "65;72;104",
        "prompt": "187;154;247", "title": "122;162;247", "dir": "122;162;247",
        "file": "192;202;245", "size": "224;175;104", "staged": "158;206;106",
        "alert": "247;118;142", "subtext": "86;95;137"
    },
    "tokyo_night_storm": {
        "bg": "36;40;59", "bglight": "41;46;66", "border": "65;72;104",
        "prompt": "187;154;247", "title": "122;162;247", "dir": "122;162;247",
        "file": "192;202;245", "size": "224;175;104", "staged": "158;206;106",
        "alert": "247;118;142", "subtext": "86;95;137"
    },
    "tokyo_night_moon": {
        "bg": "34;36;54", "bglight": "45;63;118", "border": "68;74;115",
        "prompt": "192;153;255", "title": "134;225;252", "dir": "130;170;255",
        "file": "200;211;245", "size": "255;199;119", "staged": "195;232;141",
        "alert": "255;117;127", "subtext": "68;74;115"
    },
    "tokyo_day": { 
        "bg": "225;226;231", "bglight": "203;205;214", "border": "140;143;161",
        "prompt": "152;84;241", "title": "55;96;191", "dir": "46;125;233",
        "file": "55;96;191", "size": "143;94;21", "staged": "51;99;92",
        "alert": "198;83;101", "subtext": "140;143;161"
    }
}

ascii_art = [
    r"██╗   ██╗ ██████╗ █████╗   ██████╗ ██╗  ██╗████████╗███╗   ███╗██╗        ████████╗██╗   ██╗██╗",
    r"██║   ██║██╔════╝██╔══██╗ ╚════██╗ ██║  ██║╚══██╔══╝████╗ ████║██║        ╚══██╔══╝██║   ██║██║",
    r"██║   ██║██║     ███████║  █████╔╝ ███████║   ██║   ██╔████╔██║██║           ██║   ██║   ██║██║",
    r"╚██╗ ██╔╝██║     ██╔══██║ ██╔═══╝  ██╔══██║   ██║   ██║╚██╔╝██║██║           ██║   ██║   ██║██║",
    r" ╚████╔╝ ╚██████╗██║  ██║ ███████╗ ██║  ██║   ██║   ██║ ╚═╝ ██║███████╗      ██║   ╚██████╔╝██║",
    r"  ╚═══╝   ╚═════╝╚═╝  ╚═╝ ╚══════╝ ╚═╝  ╚═╝   ╚═╝   ╚═╝     ╚═╝╚══════╝      ╚═╝    ╚═════╝ ╚═╝"
]

def apply_theme(theme_name="tokyo_night"):
    global C_BG, C_BGLIGHT, C_BORDER, C_PROMPT, C_TITLE, C_DIR, STRIKE, UNSTRIKE
    global C_FILE, C_SIZE, C_STAGED, C_SUCCESS, C_ALERT, C_WARN, C_SUBTEXT, RESET, PB_COLORS
    
    t = THEME_MATRIX.get(theme_name, THEME_MATRIX["tokyo_night"]) # Hardcode fallback
    
    C_BG = f"\033[48;2;{t['bg']}m"
    C_BGLIGHT = f"\033[48;2;{t['bglight']}m"
    C_BORDER = f"\033[38;2;{t['border']}m" + C_BG
    C_PROMPT = f"\033[38;2;{t['prompt']}m" + C_BG
    C_TITLE = f"\033[38;2;{t['title']}m" + C_BG
    C_DIR = f"\033[38;2;{t['dir']}m" + C_BG
    C_FILE = f"\033[38;2;{t['file']}m" + C_BG
    C_SIZE = f"\033[38;2;{t['size']}m" + C_BG
    C_STAGED = f"\033[38;2;{t['staged']}m" + C_BG
    C_SUCCESS = f"\033[38;2;{t['staged']}m" + C_BG
    C_ALERT = f"\033[38;2;{t['alert']}m" + C_BG
    C_WARN = f"\033[38;2;{t['size']}m" + C_BG
    C_SUBTEXT = f"\033[38;2;{t['subtext']}m" + C_BG
    RESET = "\033[0m" + C_BG 
    STRIKE = "\033[9m"
    UNSTRIKE = "\033[29m"
    
    PB_COLORS = [C_ALERT, C_WARN, C_WARN, C_STAGED, C_TITLE, C_DIR, C_PROMPT] * 2

apply_theme(app_config.get("theme", "tokyo_night"))

VERSION = "v5.4.20"
global_mode = "BOOT SEQUENCE"
err_msg = ""
viewport_logs = []
viewport_offset = 0
MATH_INDEX = 1.530

GLOBAL_LICENSE = "Copyright © 2026 Daniel Casada. This program is free software; You can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation. This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE."
GLOBAL_DISCLAIMER = "This application was created to help optical lab technicians get lens technical specifications into legacy LMS systems. This tool tries to take industry \"standard VCA files\", parse them properly, then format them into a human readable format. It is not affiliated with National Optronics™ (DAC Vision™) or any proprietary LMS manufacturer. There is absolutely no support for this tool and I am not responsible for any invalid information, errors, or any data loss. This application comes as is and you must use at your own risk."

VALID_EXTENSIONS = ['.vca', '.csv', '.xlsx', '.xls', '.txt']
DEFAULT_ICONS = {
    "opt_eng": {"char": "󰇻", "pad": 2}, "mode": {"char": "󰚡", "pad": 1},
    "db": {"char": "󱘲", "pad": 1}, "lens": {"char": "󰊪", "pad": 2},
    "stage": {"char": "", "pad": 1}, "conv": {"char": "", "pad": 1},
    "add": {"char": "󱘫", "pad": 1}, "list": {"char": "󱤢", "pad": 1},
    "scan": {"char": "󱘶", "pad": 1}, "gen": {"char": "󱘸", "pad": 1},
    "html": {"char": "󰊯", "pad": 1}, "tools": {"char": "󰏗", "pad": 1},
    "move": {"char": "󱄗", "pad": 1}, "copy": {"char": "󱉦", "pad": 1},
    "ren": {"char": "󱓦", "pad": 1}, "del": {"char": "󱂨", "pad": 1},
    "quit": {"char": "󰗼", "pad": 1}, "nf": {"char": "⚡", "pad": 0},
    "arr_up": {"char": "󰧇", "pad": 1}, "arr_dn": {"char": "󰦿", "pad": 1},
    "arr_prv": {"char": "󰧀", "pad": 1}, "arr_nxt": {"char": "󰧂", "pad": 1},
    "dir_up": {"char": "󰷏", "pad": 1}, "dir": {"char": "󰉖", "pad": 1},
    "file": {"char": "󰈙", "pad": 1}, "term": {"char": "", "pad": 1},
    "prot": {"char": "󰒃", "pad": 1}, "ext_json": {"char": "󰘦", "pad": 1},
    "ext_html": {"char": "", "pad": 1}, "ext_csv": {"char": "󰈙", "pad": 1},
    "ext_vca": {"char": "󰈙", "pad": 1}, "ext_txt": {"char": "󰈙", "pad": 1}
}

active_icons = DEFAULT_ICONS.copy()

# --- INITIALIZATION & CONFIGURATION ---

def init_environment():
    dirs = [DATA_DIR, IMPORT_DIR, ORIGINALS_DIR, DB_DIR, VLP_ARCHIVE, PURGED_DIR, CORRUPT_DIR, HTML_DIR, HTML_DATA_DIR, HTML_DB_DIR, TMP_DIR]
    for d in dirs: 
        os.makedirs(d, exist_ok=True)
    if not os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'w') as f: json.dump(app_config, f, indent=4)
        except: pass
    if not os.path.exists(ICONS_FILE):
        try:
            with open(ICONS_FILE, 'w', encoding='utf-8') as f:
                json.dump(DEFAULT_ICONS, f, indent=4, ensure_ascii=False)
        except: pass

def load_config():
    global app_config
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
                # Safely update the dictionary so we don't overwrite new default keys
                for k, v in loaded.items():
                    app_config[k] = v
        except Exception: 
            pass

def save_config():
    try:
        # Ensure the hidden directory exists before saving
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(app_config, f, indent=4)
    except Exception: 
        pass

def get_ico(key, pad=True):
    if not app_config['nerd_fonts']: return ""
    icon_data = active_icons.get(key, {})
    if isinstance(icon_data, str): return icon_data + (" " if pad else "")
    return icon_data.get("char", "") + (" " * icon_data.get("pad", 0) if pad else "")

def get_ext_ico(filename, pad=True):
    if not app_config['nerd_fonts']: return ""
    ext = os.path.splitext(filename)[1].lower().replace('.', '')
    icon_data = active_icons.get(f"ext_{ext}", active_icons.get('file', {}))
    if isinstance(icon_data, str): return icon_data + (" " if pad else "")
    return icon_data.get("char", " ") + (" " * icon_data.get("pad", 0) if pad else "")

def get_pfx(t):
    if app_config['nerd_fonts']: return {'ok': '󰄬 ', 'warn': '󰀪 ', 'err': '󰅙 ', 'info': '󰋼 '}.get(t, '')
    return {'ok': '[+] ', 'warn': '[*] ', 'err': '[!] ', 'info': '[~] '}.get(t, '')

def get_sys_info():
    try: user = os.getlogin()
    except: 
        import getpass; user = getpass.getuser()
    return f"{user}@{platform.node()}"

def is_protected(pth):
    abs_pth = os.path.abspath(pth)
    protected = [
        os.path.abspath(__file__), os.path.abspath(BASE_DIR), os.path.abspath(DATA_DIR), 
        os.path.abspath(IMPORT_DIR), os.path.abspath(ORIGINALS_DIR), os.path.abspath(DB_DIR),
        os.path.abspath(VLP_ARCHIVE), os.path.abspath(PURGED_DIR), os.path.abspath(CORRUPT_DIR), 
        os.path.abspath(HTML_DIR), os.path.abspath(HTML_DATA_DIR), os.path.abspath(TMP_DIR), 
        os.path.abspath(DB_FILE), os.path.abspath(CONFIG_FILE), os.path.abspath(ICONS_FILE), 
        os.path.abspath(SIG_FILE)
    ]
    return abs_pth in protected


# --- CRYPTOGRAPHIC SECURITY ENGINE ---

def check_master_signature():
    if not os.path.exists(DB_FILE): return True 
    if not os.path.exists(SIG_FILE): return False
    try:
        with open(DB_FILE, 'rb') as f: db_data = f.read()
        live_hash = hashlib.sha256(db_data).hexdigest()
        with open(SIG_FILE, 'r') as f: sig_hash = f.read().strip()
        return live_hash == sig_hash
    except: return False

def sign_master_database():
    if not os.path.exists(DB_FILE): return
    try:
        with open(DB_FILE, 'rb') as f: db_data = f.read()
        sig_hash = hashlib.sha256(db_data).hexdigest()
        if os.path.exists(SIG_FILE): os.chmod(SIG_FILE, stat.S_IWRITE | stat.S_IREAD)
        with open(SIG_FILE, 'w') as f: f.write(sig_hash)
        os.chmod(SIG_FILE, stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)
    except: pass

def enforce_security_lock():
    if not check_master_signature():
        sys.stdout.write(f"{C_BG}\033[2J\033[H")
        term_w, term_h = get_term_size()
        draw_top_bar()
        for r in range(2, term_h - 1): draw_frame_line("", row=r)
         
        r = term_h // 2 - 2
        draw_frame_line(f"{C_ALERT}{get_pfx('err')}{get_ico('prot', pad=False)} CRITICAL SECURITY ALERT: Master Database Signature Mismatch!{RESET}", row=r, align="center")
        draw_frame_line(f"{C_WARN}The master_lens_db.json file has been altered outside of the application.{RESET}", row=r+2, align="center")
        draw_frame_line(f"{C_WARN}To restore integrity, you must run the (G)eneration Sequence to rebuild the Vault.{RESET}", row=r+3, align="center")
        
        draw_universal_footer("Press ENTER to acknowledge and return to menu...")
        return False
    return True


# --- TUI DRAWING UTILITIES ---

def get_term_size():
    sz = shutil.get_terminal_size((120, 30))
    # Enforce minimum canvas bounds to prevent string-math collapse
    return max(120, sz.columns), max(30, sz.lines)

def ansi_len(text): 
    return len(re.sub(r'\033\[[0-9;]*m', '', text))

def format_bytes(size):
    if size < 1024: return f"{int(size)}B"
    size /= 1024.0
    if size < 1024: return f"{int(size)}K" if size.is_integer() else f"{size:.1f}K".replace('.0K', 'K')
    size /= 1024.0
    if size < 1024: return f"{int(size)}M" if size.is_integer() else f"{size:.1f}M".replace('.0M', 'M')
    size /= 1024.0
    return f"{int(size)}G" if size.is_integer() else f"{size:.1f}G".replace('.0G', 'G')

def get_prompt_indicator():
    """Returns the globally themed input indicator."""
    if app_config.get('nerd_fonts', False):
        return f"{C_BGLIGHT} {C_PROMPT}{get_ico('term', pad=False)}  {RESET}{C_BGLIGHT}"
    else:
        return f"{C_BGLIGHT}{C_PROMPT}>{RESET}{C_BGLIGHT}"

# Make sure these are declared globally near the top of your script
viewport_logs = []
scroll_offset = 0

def log_task(task_msg, status="INFO"):
    """
    Appends formatted strings to the viewport matrix.
    Status triggers semantic coloring and specific indentations.
    """
    global viewport_logs
    if status == "INFO": viewport_logs.append(f"{C_TITLE}{task_msg}{RESET}")
    elif status == "OK": viewport_logs.append(f"{C_STAGED}{task_msg}{RESET}")
    elif status == "ERR": viewport_logs.append(f"{C_ALERT}{task_msg}{RESET}")
    elif status == "WARN": viewport_logs.append(f"{C_WARN}{task_msg}{RESET}")
    elif status == "STAGED": viewport_logs.append(f"{C_PROMPT}{task_msg}{RESET}")
    elif status == "TITLE": viewport_logs.append(f"{C_TITLE}Unlocking vault file: {C_FILE}{task_msg}{RESET}")
    elif status == "PROMPT": viewport_logs.append(f"{C_PROMPT}Ingesting Lens Type: {C_STAGED}{task_msg}{RESET}")
    elif status == "RAW": viewport_logs.append(f"{task_msg}{RESET}") # Used for pre-formatted indented data
    else: viewport_logs.append(f"{C_SUBTEXT}{task_msg}{RESET}")

def get_bucket_telemetry(group_df, class_type):
    """
    Takes a Pandas DataFrame group and returns formatted telemetry strings.
    Analyzes Base Curves for SF, and exact rx ranges for FIN.
    """
    telemetry = []
    if class_type == 'SF':
        curves = sorted(group_df['Front RAD'].dropna().unique())
        curve_str = ", ".join([f"{c:.2f}" for c in curves])
        telemetry.append(f"{C_BORDER}{' '*45}-> {C_SUBTEXT}Curves: {C_TITLE}{curve_str}")
    else:
        min_sph_df = group_df[pd.to_numeric(group_df['SPH/BASE'], errors='coerce') <= 0]
        plus_sph_df = group_df[pd.to_numeric(group_df['SPH/BASE'], errors='coerce') > 0]

        if not min_sph_df.empty:
            m_min_sph = min_sph_df['SPH/BASE'].astype(float).min()
            m_max_sph = min_sph_df['SPH/BASE'].astype(float).max()
            m_min_cyl = min_sph_df['CYL/ADD'].astype(float).min()
            telemetry.append(f"{C_BORDER}{' '*45}-> {C_SUBTEXT}Minus Powers: {C_WARN}{m_max_sph:+.2f} to {m_min_sph:+.2f} SPH  |  up to {m_min_cyl:+.2f} CYL")

        if not plus_sph_df.empty:
            p_min_sph = plus_sph_df['SPH/BASE'].astype(float).min()
            p_max_sph = plus_sph_df['SPH/BASE'].astype(float).max()
            p_min_cyl = plus_sph_df['CYL/ADD'].astype(float).min()
            telemetry.append(f"{C_BORDER}{' '*45}-> {C_SUBTEXT}Plus Powers:  {C_STAGED}{p_min_sph:+.2f} to {p_max_sph:+.2f} SPH  |  up to {p_min_cyl:+.2f} CYL")
            
    return telemetry

def format_log(label, data, color=C_TITLE):
    """Aligns labels to 14 characters for the Matrix Dashboard aesthetic."""
    return f"{C_SUBTEXT}{label:>14} : {color}{data}{RESET}"

def draw_viewport(progress_pct=100.0, current_task_string="", active_file="", current_file_idx=0, total_files=0, total_types=0, total_lenses=0, is_interactive=False):
    global scroll_offset
    import re
    term_w, term_h = get_term_size()
    
    # UI ZONING
    inner_l = 4; inner_r = term_w - 3
    box_w = inner_r - inner_l + 1
    
    pb_r1 = term_h - 5
    pb_r2 = term_h - 4
    pb_r3 = term_h - 3
    
    vp_start_row = 4
    vp_end_row = pb_r1 - 1
    vp_height = vp_end_row - vp_start_row - 1
    
    # WORD-WRAP: Multi-Line Spilling with Indentation
    max_log_len = box_w - 6 
    wrapped_logs = []
    
    for log in viewport_logs:
        clean_text = re.sub(r'\x1B\[[0-9;]*[mK]', '', log)
        if len(clean_text) <= max_log_len:
            wrapped_logs.append(log)
        else:
            color_match = re.match(r'^(\x1B\[[0-9;]*[mK])+?', log)
            base_color = color_match.group(0) if color_match else ""
            
            first_chunk = clean_text[:max_log_len]
            wrapped_logs.append(f"{base_color}{first_chunk}{RESET}")
            
            remaining = clean_text[max_log_len:]
            indent = "    ↳ "
            indent_len = len(indent)
            chunk_size = max_log_len - indent_len
            
            for i in range(0, len(remaining), chunk_size):
                chunk = remaining[i:i + chunk_size]
                wrapped_logs.append(f"{base_color}{indent}{chunk}{RESET}")

    total_logs = max(1, len(wrapped_logs))

    # AUTO-SCROLL LOGIC
    if not is_interactive:
        scroll_offset = max(0, len(wrapped_logs) - vp_height)
    else:
        scroll_offset = min(scroll_offset, max(0, len(wrapped_logs) - vp_height))
    
    # DRAW VIEWPORT MATRIX
    sys.stdout.write(f"\033[{vp_start_row};{inner_l}H{C_BORDER}┌{'─' * (box_w - 2)}┐{RESET}")
    for i in range(vp_height):
        row = vp_start_row + 1 + i
        log_idx = scroll_offset + i
        log_text = wrapped_logs[log_idx] if log_idx < len(wrapped_logs) else ""
        
        thumb_size = max(1, int((vp_height / total_logs) * vp_height)) if len(wrapped_logs) > vp_height else vp_height
        max_scroll_possible = max(1, total_logs - vp_height)
        scroll_pct = scroll_offset / max_scroll_possible if max_scroll_possible > 0 else 0
        thumb_pos = int(scroll_pct * (vp_height - thumb_size)) if len(wrapped_logs) > vp_height else 0
        
        s_char = "█" if thumb_pos <= i < thumb_pos + thumb_size else "│"
        s_color = C_TITLE if s_char == "█" else C_SUBTEXT
        
        sys.stdout.write(f"\033[{row};{inner_l}H{C_BORDER}│ {RESET}")
        
        raw_len = 0
        if log_text:
            clean_text = re.sub(r'\x1B\[[0-9;]*[mK]', '', log_text)
            raw_len = len(clean_text)
            sys.stdout.write(f"\033[{row};{inner_l + 2}H{log_text}")
        
        space_to_fill = (inner_r - 1) - (inner_l + 2) - raw_len
        if space_to_fill > 0: 
            sys.stdout.write(" " * space_to_fill)
            
        sys.stdout.write(f"\033[{row};{inner_r - 1}H{s_color}{s_char}{RESET}")
        sys.stdout.write(f"\033[{row};{inner_r}H{C_BORDER}│{RESET}")
        
    sys.stdout.write(f"\033[{vp_end_row};{inner_l}H{C_BORDER}└{'─' * (box_w - 2)}┘{RESET}")
    
    # DRAW PROGRESS BAR & INTERACTIVE OVERWRITE
    text_tl = f" Progress: {current_file_idx} of {total_files} " if total_files > 0 else " Progress "
    raw_top_l = f"({text_tl})"
    top_l_str = f"({C_BGLIGHT}{C_TITLE}{text_tl}{RESET}{C_BORDER})"

    raw_top_r = f"({active_file[:40] + '...' if len(active_file) > 40 else active_file})" if active_file else ""
    top_r_str = f"({C_BGLIGHT}\033[4m{C_PROMPT}{active_file[:40] + '...' if len(active_file) > 40 else active_file}{RESET}\033[24m{C_BORDER})" if active_file else ""

    text_bl_1 = f" {total_types} TYPES "
    text_bl_2 = f" {total_lenses:,} LENSES "
    raw_bot_l = f"({text_bl_1}|{text_bl_2})" if total_types > 0 else ""
    bot_l_str = f"({C_BGLIGHT}{C_STAGED}{text_bl_1}{C_SUBTEXT}|{C_STAGED}{text_bl_2}{RESET}{C_BORDER})" if total_types > 0 else ""

# DRAW PROGRESS BAR (Always draw hashes, never erase)
    pb_inner_w = box_w - 4
    bar_str = ""
    
    text_br = f" {progress_pct:5.1f}% "
    raw_br = f"({text_br})"
    br_str = f"({C_BGLIGHT}{C_SIZE}{text_br}{RESET}{C_BORDER})"
    
    filled = int(pb_inner_w * (progress_pct / 100.0))
    for b in range(pb_inner_w):
        if b < filled:
            ratio = b / max(1, pb_inner_w)
            if ratio < 0.2: c = C_ALERT
            elif ratio < 0.4: c = C_WARN
            elif ratio < 0.6: c = C_STAGED
            elif ratio < 0.8: c = C_TITLE
            else: c = C_PROMPT
            bar_str += f"{c}#{RESET}"
        else: bar_str += " "

    r1_len = max(0, box_w - 6 - len(raw_top_l) - len(raw_top_r))
    sys.stdout.write(f"\033[{pb_r1};{inner_l}H{C_BORDER}┌──{top_l_str}{C_BORDER}{'─' * r1_len}{top_r_str}──┐{RESET}")
            
    sys.stdout.write(f"\033[{pb_r2};{inner_l}H{C_BORDER}│ {bar_str} {C_BORDER}│{RESET}")
    
    r3_len = max(0, box_w - 6 - len(raw_bot_l) - len(raw_br))
    sys.stdout.write(f"\033[{pb_r3};{inner_l}H{C_BORDER}└──{bot_l_str}{C_BORDER}{'─' * r3_len}{br_str}──┘{RESET}")
    
    sys.stdout.write(f"\033[{term_h};1H")
    sys.stdout.flush()

def getch():
    if os.name == 'nt':
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
            if arr == b'S': return 'DEL'
            if arr == b'\x86': return 'F12'
            return 'ARROWS'
        return ch.decode('utf-8', errors='ignore')
    else:
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            if ch == '\x1b':
                dr, _, _ = select.select([sys.stdin], [], [], 0.01)
                if dr:
                    ch2 = sys.stdin.read(1)
                    if ch2 == '[':
                        ch3 = sys.stdin.read(1)
                        if ch3 == 'A': return 'UP'
                        if ch3 == 'B': return 'DOWN'
                        if ch3 == 'C': return 'RIGHT'
                        if ch3 == 'D': return 'LEFT'
                        if ch3 == '5': sys.stdin.read(1); return 'PGUP'
                        if ch3 == '6': sys.stdin.read(1); return 'PGDN'
                        if ch3 == '3': sys.stdin.read(1); return 'DEL'
                        if ch3 == '2':
                            if sys.stdin.read(1) == '4':
                                sys.stdin.read(1)
                                return 'F12'
                    return 'ARROWS'
                else: return 'ESC'
        finally: termios.tcsetattr(fd, termios.TCSADRAIN, old)
        return ch

def live_input(prompt, hotkeys=False, default_text=""):
    sys.stdout.write(prompt); sys.stdout.flush()
    buf = default_text
    if buf: sys.stdout.write(f"{C_FILE}{buf}{RESET}"); sys.stdout.flush()
        
    first_key = True
    while True:
        c = getch()
        if c == 'ESC': return "ABORT"
        if c == 'F12': execute_admin_menu(); return "REFRESH"
        if c in ('UP', 'DOWN', 'LEFT', 'RIGHT', 'PGUP', 'PGDN', 'DEL') and hotkeys: return c
        if c == '\r' or c == '\n': return buf.strip()
         
        if first_key and c not in ('\x08', '\x7f', '\r', '\n') and c.isprintable():
            sys.stdout.write('\b \b' * len(buf))
            buf = c
            sys.stdout.write(f"{C_FILE}{c}{RESET}"); sys.stdout.flush()
            first_key = False
            continue
            
        first_key = False
        if c == '\x08' or c == '\x7f':
            if len(buf) > 0:
                buf = buf[:-1]
                sys.stdout.write('\b \b'); sys.stdout.flush()
        elif c == '\x03': clean_exit()
        elif c not in ('UP', 'DOWN', 'LEFT', 'RIGHT', 'PGUP', 'PGDN', 'DEL', 'ARROWS', 'ESC', 'F12'):
            if c.isalnum() or c in " .-_&/\\:\\()":
                buf += c
                sys.stdout.write(f"{C_FILE}{c}{RESET}"); sys.stdout.flush()

def handle_error_hijack():
    global err_msg
    if not err_msg: return False
    term_w, term_h = get_term_size()
    prompt_ico = get_ico('term', pad=False) if app_config['nerd_fonts'] else "[!]"
    sys.stdout.write(f"\033[{term_h - 4};5H{C_BGLIGHT} {C_ALERT}{prompt_ico} {err_msg} {C_SUBTEXT}(Press ENTER){RESET}{C_BGLIGHT}{' '*10}{RESET}")
    sys.stdout.flush()
    while True:
        c = getch()
        if c == 'F12': execute_admin_menu(); return True
        if c in ['\r', '\n']: break
    err_msg = ""
    sys.stdout.write(f"\033[{term_h - 4};5H{C_BGLIGHT} {C_PROMPT}{get_ico('term', pad=False)}  {RESET}{C_BGLIGHT}{' '*60}{RESET}\033[{term_h - 4};9H{C_BGLIGHT}")
    sys.stdout.flush()
    return True

def draw_top_bar():
    term_w, term_h = get_term_size()
    title = f"{C_TITLE}[Optical Lens Specifications Engine]{C_BORDER}"
    
    # Highlight the version string so it pops
    ver = f"{C_PROMPT}({VERSION}){C_BORDER}"
    
    left_str = f"{C_BORDER}╔══{title}"
    
    # Add 4 '═' characters AFTER {ver} to push it back towards the center
    right_str = f"══{ver}════╗{RESET}"
    
    # Calculate the exact number of ═ needed to bridge the gap
    gap = term_w - ansi_len(left_str) - ansi_len(right_str)
    
    sys.stdout.write(f"\033[1;1H{left_str}{'═' * max(0, gap)}{right_str}")
    sys.stdout.flush()

def draw_status_bar():
    term_w, term_h = get_term_size()
    db_active = os.path.exists(DB_FILE)
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f: total_lenses = len(json.load(f).get('lenses', {}))
    except: total_lenses = 0
    staged = len([f for f in os.listdir(IMPORT_DIR) if f.lower().endswith('.vlp')]) if os.path.exists(IMPORT_DIR) else 0
    
    mode_str = global_mode.upper()
    if "MENU" in mode_str: m_key = "mode"
    elif "AUDIT" in mode_str or "QUESTION" in mode_str or "CONVERT" in mode_str: m_key = "conv"
    elif "GATEKEEPER" in mode_str or "ADD" in mode_str: m_key = "add"
    elif "INVENTORY" in mode_str or "LIST" in mode_str: m_key = "list"
    elif "DIAGNOSTICS" in mode_str or "SCAN" in mode_str: m_key = "scan"
    elif "COMPILER" in mode_str and "HTML" not in mode_str: m_key = "gen"
    elif "HTML" in mode_str: m_key = "html"
    elif "MOVE" in mode_str: m_key = "move"
    elif "COPY" in mode_str: m_key = "copy"
    elif "RENAME" in mode_str: m_key = "ren"
    elif "DELETE" in mode_str: m_key = "del"
    else: m_key = "mode"
    
    m_block = f"{C_SIZE}{get_ico(m_key)}MODE: {C_TITLE}{global_mode}{C_BORDER}"
    db_block = f"{C_SIZE}{get_ico('db')}DB: {C_TITLE}{'ACTIVE' if db_active else 'OFFLINE'}{C_BORDER}"
    l_block = f"{C_SIZE}{get_ico('lens')}LENSES: {C_STAGED}{total_lenses}{C_BORDER}"
    s_block = f"{C_SIZE}{get_ico('stage')}STAGED: {C_TITLE}{staged}{C_BORDER}"

    left = f"{C_BORDER}╚════[{m_block}]════[{db_block}]══({l_block})════[{s_block}]"
    right = f"═══[{C_TITLE}{get_ico('prot')}{get_sys_info()}{C_BORDER}]════╝{RESET}"
    
    gap = max(0, term_w - ansi_len(left) - ansi_len(right))
    sys.stdout.write(f"\033[{term_h - 1};1H{left}{'═' * gap}{right}")
    sys.stdout.flush()

def draw_universal_footer_ui(prompt_text):
    term_w, term_h = get_term_size()
    draw_status_bar()
    sys.stdout.write(f"\033[{term_h - 4};5H{C_BGLIGHT} {C_PROMPT}{get_ico('term', pad=False)}  {C_STAGED}{prompt_text}{RESET}{C_BGLIGHT}{' '*40}{RESET}\033[{term_h - 4};{10+ansi_len(prompt_text)}H")
    sys.stdout.flush()

def draw_universal_footer(prompt_text="Press ENTER to return..."):
    draw_universal_footer_ui(prompt_text)
    while True:
        cmd = getch()
        if cmd == 'F12': execute_admin_menu(); draw_universal_footer_ui(prompt_text)
        elif cmd in ['\r', '\n']: break

def draw_frame_line(text, row=2, align="left", color=None, indent=0):
    if color is None: color = C_SUBTEXT
    term_w, term_h = get_term_size()
    
    # Modern Double-Line Walls
    sys.stdout.write(f"\033[{row};1H{C_BORDER}║ {RESET}")
    
    if text:
        clean_len = ansi_len(text)
        if align == "left":
            sys.stdout.write(f"\033[{row};{3 + indent}H{color}{text}{RESET}")
        elif align == "center":
            pad = (term_w - clean_len) // 2
            sys.stdout.write(f"\033[{row};{pad}H{color}{text}{RESET}")
        elif align == "right":
            pad = term_w - clean_len - 2
            sys.stdout.write(f"\033[{row};{pad}H{color}{text}{RESET}")
            
    sys.stdout.write(f"\033[{row};{term_w}H{C_BORDER}║{RESET}")

def draw_borderless_line(text, row, align="center"):
    term_w, _ = get_term_size()
    if align == "center": padding = max(0, term_w - ansi_len(text)) // 2; content = (" " * padding) + text
    else: content = text
    sys.stdout.write(f"\033[{row};1H{content}")

def draw_context_helpers(line1, line2="", offset=5):
    term_w, term_h = get_term_size()
    start_row = term_h - offset
    
    # Route the legacy helper text directly through our modern double-line wall engine
    draw_frame_line(line1, row=start_row, align="center")
    
    if line2:
        draw_frame_line(line2, row=start_row + 1, align="center")

def draw_modal(title, prompt_text, is_password=False, is_y_n=False):
    """Draws a floating, single-line modal strictly in the center of the terminal."""
    term_w, term_h = get_term_size()
    
    # Dynamically scale box width
    box_w = max(44, len(title) + 8, len(prompt_text) + 8)
    start_col = (term_w - box_w) // 2
    start_row = (term_h // 2) - 3

    # Opaque background using {C_BG} to prevent viewport bleed
    indicator = f"{C_PROMPT}{get_ico('term', pad=False)}  {RESET}" if app_config.get('nerd_fonts', False) else f"{C_PROMPT}> {RESET}"
    ind_len = 3 if app_config.get('nerd_fonts', False) else 2

    sys.stdout.write(f"\033[{start_row};{start_col}H{C_BORDER}┌{'─' * (box_w - 2)}┐{RESET}")
    sys.stdout.write(f"\033[{start_row + 1};{start_col}H{C_BORDER}│{C_BG}{C_TITLE}{title.center(box_w - 2)}{RESET}{C_BORDER}│{RESET}")
    sys.stdout.write(f"\033[{start_row + 2};{start_col}H{C_BORDER}│{C_BG} {C_ALERT if not is_password else C_WARN}{prompt_text:<{box_w - 4}}{RESET}{C_BORDER} │{RESET}")
    sys.stdout.write(f"\033[{start_row + 3};{start_col}H{C_BORDER}│{C_BG} {indicator}{' ' * (box_w - 4 - ind_len)}{RESET}{C_BORDER} │{RESET}")
    sys.stdout.write(f"\033[{start_row + 4};{start_col}H{C_BORDER}└{'─' * (box_w - 2)}┘{RESET}")
    sys.stdout.flush()

    input_str = ""
    input_col = start_col + 2 + ind_len
    
    while True:
        sys.stdout.write(f"\033[{start_row + 3};{input_col}H{C_BG}{' ' * (box_w - 4 - ind_len)}")
        display_str = ("*" * len(input_str)) if is_password else input_str
        sys.stdout.write(f"\033[{start_row + 3};{input_col}H{C_STAGED}{display_str}{RESET}")
        sys.stdout.write(f"\033[{start_row + 3};{input_col + len(input_str)}H")
        sys.stdout.flush()

        c = getch()
        if isinstance(c, bytes):
            try: c = c.decode('utf-8')
            except: continue
        if not isinstance(c, str): continue
        
        # --- NEW Y/N INTERCEPT ---
        if is_y_n:
            if c.upper() == 'Y': return 'Y'
            return None # Any other key instantly aborts
        # -------------------------

        if c in ('\r', '\n'): return input_str
        elif c == '\x1b': return None 
        elif c in ('\x08', '\x7f'): input_str = input_str[:-1]
        elif len(input_str) < box_w - 6 - ind_len and c.isprintable(): input_str += c

def get_prompt_indicator():
    if app_config.get('nerd_fonts', False):
        ico = get_ico('term', pad=False)
        return f"{C_BGLIGHT} {C_PROMPT}{ico}  {RESET}{C_BGLIGHT}"
    else:
        return f"{C_BGLIGHT}{C_PROMPT}>{RESET}{C_BGLIGHT}"

def render_ui_skeleton(loading_text="Initializing..."):
    sys.stdout.write(f"{C_BG}\033[2J\033[H")
    term_w, term_h = get_term_size()
    draw_top_bar()
    for r in range(2, term_h - 1): draw_frame_line("", row=r)
    draw_frame_line(f"{C_TITLE}{loading_text}{RESET}", 4, align="center")
    if 'draw_universal_footer_ui' in globals(): draw_universal_footer_ui("Processing Request...")
    sys.stdout.flush()

def clean_exit(msg=None):
    sys.stdout.write(f"{C_BG}\033[2J\033[H{RESET}")
    # Destroy Alternate Buffer
    sys.stdout.write("\033[?1049l")
    sys.stdout.flush()
    
    if msg:
        print(f"{C_ALERT}{msg}{RESET}")
        
    sys.exit(0)

def eza_perms(st_mode):
    c = ""
    for x in stat.filemode(st_mode):
        if x == 'd': c += f"{C_DIR}{x}"
        elif x == 'r': c += f"{C_STAGED}{x}"
        elif x == 'w': c += f"{C_SIZE}{x}"
        elif x == 'x': c += f"{C_ALERT}{x}"
        else: c += f"{C_SUBTEXT}{x}"
    return c + RESET

def get_alpha_id(i):
    res = ""
    while i >= 0:
        res = chr(65 + (i % 26)) + res
        i = i // 26 - 1
    return res


# --- BOOT & ADMINISTRATION ---

def verify_and_stage_fonts():
    global global_mode, scroll_offset
    # Bring the Tier 2 heavy lifters into global scope
    global pd, urllib, zipfile
    
    # 1. STANDARDIZED SKELETON SETUP
    sys.stdout.write(f"{C_BG}\033[2J\033[H")
    term_w, term_h = get_term_size()
    draw_top_bar()
    for r in range(2, term_h - 1): draw_frame_line("", row=r)
    draw_frame_line(f"{C_SIZE}PHASE 0: SYSTEM INITIALIZATION & ASSET VERIFICATION{RESET}", row=2, align="center")
    
    draw_universal_footer_ui(f"{C_SUBTEXT}Igniting Matrix Engine...{RESET}") # THE FLOOR SEAL (NO LOCK)
    
    viewport_logs.clear()
    scroll_offset = 0

    # 2. THE SMOKE & MIRRORS MATRIX
    modules = [
        ("Core OS Interface", "os", False), ("System Pathways", "sys", False),
        ("Temporal Engine", "time", False), ("Platform Diagnostics", "platform", False),
        ("Warning Handlers", "warnings", False), ("Exit Routines", "atexit", False),
        ("Regex Engine", "re", False), ("File Operations", "shutil", False),
        ("JSON Parsers", "json", False), ("Sys Stat", "stat", False),
        ("Text Wrapping", "textwrap", False), ("Datetime Engine", "datetime", False),
        ("Timezone Protocols", "timezone", False), ("Cryptographic Hashes", "hashlib", False),
        ("Binary Encoders", "base64", False), ("Network Libraries", "urllib", False), 
        ("Archive Tools", "zipfile", False), ("Pandas DataFrames", "pandas", True)
    ]
    
    fonts = {
        'MSSansSerif-Regular.ttf': {'win': r"C:\Windows\Fonts\micross.ttf", 'lin_name': 'micross.ttf', 'url': "https://cdn.jsdelivr.net/gh/matomo-org/travis-scripts@master/fonts/micross.ttf", 'is_zip': False},
        'Arial-Regular.ttf': {'win': r"C:\Windows\Fonts\arial.ttf", 'lin_name': 'arial.ttf', 'url': "https://cdn.jsdelivr.net/gh/matomo-org/travis-scripts@master/fonts/arial.ttf", 'is_zip': False},
        'Arial-Bold.ttf': {'win': r"C:\Windows\Fonts\arialbd.ttf", 'lin_name': 'arialbd.ttf', 'url': "https://cdn.jsdelivr.net/gh/matomo-org/travis-scripts@master/fonts/arialbd.ttf", 'is_zip': False},
        'Tahoma-Regular.ttf': {'win': r"C:\Windows\Fonts\tahoma.ttf", 'lin_name': 'tahoma.ttf', 'url': "https://cdn.jsdelivr.net/gh/matomo-org/travis-scripts@master/fonts/tahoma.ttf", 'is_zip': False},
        'UbuntuSansNerdFont-Regular.ttf': {'win': "", 'lin_name': "", 'url': "https://github.com/ryanoasis/nerd-fonts/releases/latest/download/UbuntuSans.zip", 'is_zip': True},
        'JetBrainsMonoNerdFont-Regular.ttf': {'win': "", 'lin_name': "", 'url': "https://github.com/ryanoasis/nerd-fonts/releases/latest/download/JetBrainsMono.zip", 'is_zip': True},
        'FiraCodeNerdFont-Medium.ttf': {'win': "", 'lin_name': "", 'url': "https://github.com/ryanoasis/nerd-fonts/releases/latest/download/FiraCode.zip", 'is_zip': True},
        'CaskaydiaCoveNerdFont-Regular.ttf': {'win': "", 'lin_name': "", 'url': "https://github.com/ryanoasis/nerd-fonts/releases/latest/download/CascadiaCode.zip", 'is_zip': True},
        'NotoSansNerdFont-Regular.ttf': {'win': "", 'lin_name': "", 'url': "https://github.com/ryanoasis/nerd-fonts/releases/latest/download/Noto.zip", 'is_zip': True},
        'OpenSans-Regular.ttf': {'win': "", 'lin_name': "", 'url': "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/opensans/static/OpenSans-Regular.ttf", 'is_zip': False},
    }

    # Weighting the progress bar: Modules = 1 tick, Fonts = 4 ticks each (because they take longer)
    total_tasks = len(modules) + (len(fonts) * 4)
    curr = 0

    # THE CINEMATIC MACRO
    def matrix_step(log_msg, status="SYSTEM", color=C_SUBTEXT, inc=1, delay=0.15):
        nonlocal curr
        curr += inc
        pct = min(100.0, (curr / total_tasks) * 100.0)
        log_task(format_log(status, log_msg, color), "RAW")
        draw_viewport(progress_pct=pct, active_file="Initializing...", current_file_idx=curr, total_files=total_tasks, is_interactive=False)
        time.sleep(delay)

    matrix_step("INITIALIZING CORE MODULES...", "SYSTEM", C_TITLE, inc=0, delay=0.6)
    
    # 4. EXECUTING THE MATRIX LOADS
    for desc, mod, is_real in modules:
        matrix_step(f"Allocating memory buffer for {desc} [{mod}]...", "SYSTEM", C_SUBTEXT, inc=0, delay=0.08)
        
    # Ensure pd escapes the local function scope
    global pd

    # 4. EXECUTING THE MATRIX LOADS
    for desc, mod, is_real in modules:
        matrix_step(f"Allocating memory buffer for {desc} [{mod}]...", "SYSTEM", C_SUBTEXT, inc=0, delay=0.08)
        
        if is_real:
            if mod == "pandas": 
                import pandas as pd
                matrix_step(f"Physical library '{mod}' loaded into RAM.", "MOUNT", C_PROMPT, inc=0, delay=0.4)
            # If you ever add numpy or openpyxl back to the matrix, you'd do it here:
            # elif mod == "numpy": import numpy as np
        
        # We still delay on the Ghost Loads so it looks like it's doing heavy lifting
        matrix_step(f"Module '{mod}' successfully mounted and verified.", "SUCCESS", C_STAGED, inc=1, delay=0.1)
        
        matrix_step(f"Module '{mod}' successfully mounted and verified.", "SUCCESS", C_STAGED, inc=1, delay=0.1)

    # 5. ASSET SCANNING & EXTRACTION
    matrix_step("INITIALIZING TYPOGRAPHY ENGINE...", "SYSTEM", C_TITLE, inc=0, delay=0.8)
    
    os.makedirs(HTML_DATA_DIR, exist_ok=True)
    os.makedirs(TMP_DIR, exist_ok=True)
    is_win = os.name == 'nt'
    
    def find_local_font(win_path, file_name):
        if is_win and os.path.exists(win_path): return win_path
        if not is_win and file_name:
            lin_paths = [
                f"/usr/share/fonts/truetype/msttcorefonts/{file_name}", f"/usr/share/fonts/truetype/msttcorefonts/{file_name.lower()}",
                f"/usr/share/fonts/TTF/{file_name}", f"/usr/share/fonts/{file_name}",
                os.path.expanduser(f"~/.local/share/fonts/{file_name}"), os.path.expanduser(f"~/.fonts/{file_name}")
            ]
            for p in lin_paths:
                if os.path.exists(p): return p
        return None

    for dest_name, meta in fonts.items():
        dest_path = os.path.join(HTML_DATA_DIR, dest_name)
        matrix_step(f"Evaluating dependency: {dest_name}", "SCAN", C_SUBTEXT, inc=1, delay=0.3)
        
        if not os.path.exists(dest_path):
            local_src = find_local_font(meta['win'], meta.get('lin_name', ''))
            if local_src:
                matrix_step(f"Discovered native OS asset at: {local_src}", "LOCAL", C_DIR, inc=1, delay=0.4)
                matrix_step(f"Copying {dest_name} to HTML/data vault...", "MOUNT", C_PROMPT, inc=1, delay=0.3)
                try:
                    shutil.copy2(local_src, dest_path)
                    matrix_step(f"Asset {dest_name} integrated flawlessly.", "SUCCESS", C_STAGED, inc=1, delay=0.2)
                except Exception as e:
                    matrix_step(f"Mount error: {e}", "FAILED", C_ALERT, inc=1, delay=0.5)
            else:
                matrix_step(f"Asset missing locally. Preparing network fetch...", "WARN", C_WARN, inc=1, delay=0.5)
                matrix_step(f"Opening secure HTTP tunnel to: {meta['url'].split('/')[2]}", "NETWORK", C_DIR, inc=0, delay=0.6)
                
                try:
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                        'Accept': '*/*'
                    }
                    req = urllib.Request(meta['url'].strip(), headers=headers)
                    
                    if meta.get('is_zip'):
                        zip_path = os.path.join(TMP_DIR, 'temp_font.zip')
                        matrix_step(f"Downloading binary payload from {meta['url']}...", "DOWNLOAD", C_FILE, inc=1, delay=1.0)
                        with urllib.urlopen(req) as response, open(zip_path, 'wb') as out_file: shutil.copyfileobj(response, out_file)
                        
                        matrix_step(f"Payload received. Unzipping temp_font.zip...", "EXTRACT", C_PROMPT, inc=1, delay=0.6)
                        with zipfile.ZipFile(zip_path, 'r') as z:
                            target_file = next((f for f in z.namelist() if f.endswith(dest_name)), None)
                            if target_file:
                                matrix_step(f"Located {target_file} inside archive. Extracting to {dest_path}...", "EXTRACT", C_PROMPT, inc=0, delay=0.5)
                                with z.open(target_file) as zf, open(dest_path, 'wb') as f: shutil.copyfileobj(zf, f)
                            else:
                                matrix_step(f"Could not find {dest_name} in archive!", "FAILED", C_ALERT, inc=0, delay=0.5)
                                
                        matrix_step(f"Purging temporary archive temp_font.zip...", "CLEANUP", C_SUBTEXT, inc=0, delay=0.4)
                        os.remove(zip_path)
                    else:
                        matrix_step(f"Downloading raw asset from {meta['url']}...", "DOWNLOAD", C_FILE, inc=2, delay=1.0)
                        with urllib.urlopen(req) as response, open(dest_path, 'wb') as out_file: shutil.copyfileobj(response, out_file)
                            
                    matrix_step(f"Asset {dest_name} successfully staged.", "SUCCESS", C_STAGED, inc=1, delay=0.2)
                except Exception as e:
                    matrix_step(f"Network fetch failed: {e}", "FAILED", C_ALERT, inc=2, delay=1.5)
        else:
            matrix_step(f"Verified existing cached asset: {dest_name}", "VERIFIED", C_STAGED, inc=3, delay=0.15)
            
    # 6. UNIVERSAL THEATRICAL LOCK
    matrix_step(f"System Ready. {C_PROMPT}Press ENTER to boot Operations Center...{RESET}", "SYSTEM", C_STAGED, inc=0, delay=0)
    
    draw_viewport(progress_pct=100.0, active_file="System Ready", current_file_idx=total_tasks, total_files=total_tasks, is_interactive=True)
    
    while True:
        c = getch()
        if isinstance(c, bytes):
            try: c = c.decode('utf-8')
            except: continue
        if c in ('\r', '\n', '\x1b'): break
        
        vp_height = (term_h - 9) - 4 - 1
        max_scroll = max(0, len(viewport_logs) - vp_height)
        
        if c == '\x1b[A' or c == 'UP': scroll_offset = max(0, scroll_offset - 1)
        elif c == '\x1b[B' or c == 'DOWN': scroll_offset = min(max_scroll, scroll_offset + 1)
        elif c == '\x1b[5~' or c == 'PGUP': scroll_offset = max(0, scroll_offset - 10)
        elif c == '\x1b[6~' or c == 'PGDN': scroll_offset = min(max_scroll, scroll_offset + 10)
        
        draw_viewport(progress_pct=100.0, active_file="System Ready", current_file_idx=total_tasks, total_files=total_tasks, is_interactive=True)

def display_boot_sequence():
    global global_mode
    import textwrap
    
    # Engage Alternate Screen Buffer
    sys.stdout.write("\033[?1049h\033[H")
    sys.stdout.write(f"{C_BG}\033[2J\033[H") 
    
    term_w, term_h = get_term_size()
    draw_top_bar() 
    
    # Paint the Walls
    for r in range(2, term_h - 1): 
        draw_frame_line("", row=r)
    
    # Center the ASCII Art (Dropped exactly 2 lines lower)
    start_row = 4
    for i, line in enumerate(ascii_art):
        pad = (term_w - ansi_len(line)) // 2
        sys.stdout.write(f"\033[{start_row + i};{pad}H{C_TITLE}{line}{RESET}")
    
    # Setup Text Block Margin
    text_w = int(term_w * 0.85)
    pad_left = (term_w - text_w) // 2
    row = start_row + len(ascii_art) + 2
    
    for line in textwrap.wrap(GLOBAL_LICENSE, width=text_w):
        sys.stdout.write(f"\033[{row};{pad_left}H{C_SUCCESS}{line}{RESET}")
        row += 1
        
    row += 1
    for line in textwrap.wrap(GLOBAL_DISCLAIMER, width=text_w):
        sys.stdout.write(f"\033[{row};{pad_left}H{C_PROMPT}{line}{RESET}")
        row += 1

    row += 2
    sys.stdout.write(f"\033[{row};{pad_left}H{C_SUBTEXT}Press {C_PROMPT}(Y){C_SUBTEXT} to Accept Terms and Continue.{RESET}")
    
    draw_status_bar()
    sys.stdout.flush()
    
    # Capture keystroke and normalize bytes (Fixes dual-boot OS differences)
    c = getch()
    if isinstance(c, bytes): c = c.decode('utf-8', errors='ignore')
    if isinstance(c, str) and c.lower() == 'y': 
        return
    
    # Warning Modal
    box_w = 64
    start_col = (term_w - box_w) // 2
    modal_row = (term_h // 2) - 3

    sys.stdout.write(f"\033[{modal_row};{start_col}H{C_BORDER}┌{'─' * (box_w - 2)}┐{RESET}")
    sys.stdout.write(f"\033[{modal_row + 1};{start_col}H{C_BORDER}│{C_TITLE}{'TERMS & CONDITIONS':^{box_w - 2}}{C_BORDER}│{RESET}")
    prompt_txt = "You must press (Y) to agree or any other key to quit."
    sys.stdout.write(f"\033[{modal_row + 2};{start_col}H{C_BORDER}│ {C_ALERT}{prompt_txt:<{box_w - 4}}{C_BORDER} │{RESET}")
    sys.stdout.write(f"\033[{modal_row + 3};{start_col}H{C_BORDER}│{' ' * (box_w - 2)}│{RESET}")
    sys.stdout.write(f"\033[{modal_row + 4};{start_col}H{C_BORDER}└{'─' * (box_w - 2)}┘{RESET}")
    sys.stdout.flush()
    
    c2 = getch()
    if isinstance(c2, bytes): c2 = c2.decode('utf-8', errors='ignore')
    if isinstance(c2, str) and c2.lower() == 'y': 
        return
    
    clean_exit("User did not accept terms. Exiting Application.")

def execute_admin_menu():
    global global_mode
    prev_mode = global_mode
    global_mode = "SYSTEM CONFIGURATION"
    
    while True:
        term_w, term_h = get_term_size()
        sys.stdout.write(f"{C_BG}\033[2J\033[H")
        draw_top_bar()
        
        # Paint the empty walls for the whole screen
        for r in range(2, term_h - 1): 
            draw_frame_line("", row=r)
            
        start_row = 4
        margin_left = 6
        
        sys.stdout.write(f"\033[{start_row};{margin_left}H{C_TITLE}SYSTEM ADMINISTRATION{RESET}")
        sys.stdout.write(f"\033[{start_row + 1};{margin_left}H{C_BORDER}{'═' * 45}{RESET}")
        
        active_theme = app_config.get('theme', 'tokyo_night')
        nf_str = f"{C_STAGED}ON{RESET}" if app_config.get('nerd_fonts') else f"{C_ALERT}OFF{RESET}"
        
        # --- THEME MATRIX (Options 1-4) ---
        themes = ['tokyo_night', 'tokyo_night_storm', 'tokyo_night_moon', 'tokyo_day']
        row = start_row + 3
        
        for i, th in enumerate(themes):
            is_active = " (ACTIVE)" if th == active_theme else ""
            c = C_PROMPT if is_active else C_SUBTEXT
            sys.stdout.write(f"\033[{row};{margin_left}H{c}[{i+1}] {th}{is_active}{RESET}")
            row += 1
            
        row += 2
        
        # --- SYSTEM TOGGLES (Options 5-6) ---
        sys.stdout.write(f"\033[{row};{margin_left}H{C_SUBTEXT}[5] Typography Engine: {nf_str}{RESET}")
        row += 1
        sys.stdout.write(f"\033[{row};{margin_left}H{C_SUBTEXT}[6] Reset Master Passkey{RESET}")
        row += 3
        
        sys.stdout.write(f"\033[{row};{margin_left}H{C_WARN}[ESC / Q] Return to System{RESET}")
        
        draw_status_bar()
        sys.stdout.flush()
        
        c = getch()
        if not isinstance(c, str): continue
        c = c.lower()
        
        # Explicit trap for Escape (\x1b) and Q
        if c == '\x1b' or c == 'q':
            break
        elif c == '1':
            app_config['theme'] = 'tokyo_night'; save_config(); apply_theme('tokyo_night')
        elif c == '2':
            app_config['theme'] = 'tokyo_night_storm'; save_config(); apply_theme('tokyo_night_storm')
        elif c == '3':
            app_config['theme'] = 'tokyo_night_moon'; save_config(); apply_theme('tokyo_night_moon')
        elif c == '4':
            app_config['theme'] = 'tokyo_day'; save_config(); apply_theme('tokyo_day')
        elif c == '5':
            app_config['nerd_fonts'] = not app_config.get('nerd_fonts', False); save_config()
            
    global_mode = prev_mode

#--- HTML COMPILER & SHARD ENGINE ---

def bootstrap_web_templates():
    template_dir = os.path.join(HTML_DATA_DIR, '.templates')
    os.makedirs(template_dir, exist_ok=True)

    css_path = os.path.join(template_dir, 'styles.css')
    with open(css_path, 'w', encoding='utf-8') as f:
        f.write("""
@font-face { font-family: 'Ubuntu Sans Nerd'; src: url('UbuntuSansNerdFont-Medium.ttf') format('truetype'); font-weight: 500; }
@font-face { font-family: 'MS Sans Serif Local'; src: local('MS Sans Serif'), local('Microsoft Sans Serif'), url('MSSansSerif-Regular.ttf') format('truetype'); }
@font-face { font-family: 'Arial Local'; src: local('Arial'), url('Arial-Regular.ttf') format('truetype'); }
@font-face { font-family: 'Arial Bold Local'; src: local('Arial Bold'), url('Arial-Bold.ttf') format('truetype'); font-weight: bold; }
@font-face { font-family: 'Tahoma Local'; src: local('Tahoma'), url('Tahoma-Regular.ttf') format('truetype'); }

:root, .modern-mode {
    --bg-main: #24283b; --bg-table: #1f2335; --text-main: #c0caf5; --win-bg: #24283b; --win-highlight: #414868; --win-shadow: #1a1b26;
    --win-dark-shadow: #15161e; --win-title: #24283b; --win-title-fade: #1f2335; --win-text: #c0caf5; --win-title-text: #7aa2f7;
    --border-light: #414868; --border-dark: #1a1b26; --accent: #3d59a1; --row-even: #24283b; --row-odd: #1f2335;
    --col-desc: #c0caf5; --col-filt: #9ece6a; --col-coat: #e0af68; --col-mat: #7dcfff; 
    --col-idx: #bb9af7; --col-diam: #c0caf5; --col-base: #e0af68; --col-tfc: #c0caf5; --col-tbc: #7aa2f7; --col-sag: #f7768e;
}
.classic-mode {
    --bg-main: #e1e2e7; --bg-table: #d0d5e3; --text-main: #3760bf; --win-bg: #d4d0c8; --win-highlight: #ffffff; --win-shadow: #808080;
    --win-dark-shadow: #404040; --win-title: #e1e2e7; --win-title-fade: #d0d5e3; --win-text: #000000; --win-title-text: #3760bf;
    --border-light: #b4b5b9; --border-dark: #a1a6c5; --accent: #b7c1e3; --row-even: #e1e2e7; --row-odd: #d0d5e3;
    --col-desc: #3760bf; --col-filt: #587539; --col-coat: #8c6c3e; --col-mat: #007197; 
    --col-idx: #9854f1; --col-diam: #3760bf; --col-base: #8c6c3e; --col-tfc: #3760bf; --col-tbc: #2e7de9; --col-sag: #f52a65;
}

body { background-color: var(--bg-main); color: var(--text-main); font-family: 'Ubuntu Sans Nerd', sans-serif; font-weight: 500; margin: 0; padding: 20px; transition: background-color 0.1s; font-variant-numeric: tabular-nums; }

.top-bar { display: flex; justify-content: space-between; align-items: center; background-color: var(--win-title); border: 1px solid var(--border-light); border-bottom: 2px solid var(--border-dark); padding: 12px 24px; margin-bottom: 20px; border-radius: 6px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
.classic-mode .top-bar { box-shadow: none; border-bottom: 2px solid var(--border-dark); }

.top-bar-left, .top-bar-right { width: 260px; display: flex; align-items: center; }
.top-bar-right { justify-content: flex-end; gap: 8px; }
.top-bar-center { flex-grow: 1; text-align: center; color: var(--win-title-text); font-family: 'Ubuntu Sans Nerd', sans-serif !important; font-weight: 700 !important; font-size: 26px; text-transform: uppercase; letter-spacing: 2px; text-shadow: 1px 1px 2px rgba(0,0,0,0.2); }

.nav-toggle { color: var(--win-title-text); text-decoration: none; font-size: 18px; font-weight: bold; opacity: 0.9; transition: opacity 0.2s; }
.nav-toggle:hover { opacity: 1; text-decoration: underline; }

.theme-switch { position: relative; display: inline-block; width: 50px; height: 26px; margin: 0 8px; }
.theme-switch input { opacity: 0; width: 0; height: 0; }
.slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: var(--win-dark-shadow); transition: .4s; border-radius: 26px; border: 1px solid var(--border-light); }
.slider:before { position: absolute; content: ""; height: 18px; width: 18px; left: 3px; bottom: 3px; background-color: var(--text-main); transition: .4s; border-radius: 50%; }
input:checked + .slider { background-color: #7aa2f7; }
input:checked + .slider:before { transform: translateX(24px); background-color: #15161e; }
.classic-mode input:checked + .slider { background-color: #3760bf; }
.classic-mode input:checked + .slider:before { background-color: #ffffff; }

.theme-label { color: var(--win-title-text); font-size: 20px; opacity: 0.9; }

.mfg-list { list-style-type: none; padding-left: 20px; } 
.mfg-list li { margin: 16px 0; font-size: 24px; font-weight: bold; }
.mfg-list a { color: var(--text-main); text-decoration: none; padding: 6px 12px; border-radius: 6px; transition: background 0.2s; } 
.mfg-list a:hover { color: var(--col-desc); background: var(--win-highlight); }

.table-container { border-radius: 12px; overflow: hidden; box-shadow: 0 8px 16px rgba(0, 0, 0, 0.4); border: 1px solid var(--border-dark); }
table.data-grid { width: 100%; border-collapse: collapse; background: var(--bg-table); }
table.data-grid th, table.data-grid td { border: 1px solid var(--border-light); padding: 6px 10px; text-align: center; vertical-align: middle; }
table.data-grid th { font-weight: 700; text-transform: uppercase; font-size: 0.9em; letter-spacing: 0.05em; }

table.data-grid td.col-mat, table.data-grid td.col-diam { white-space: nowrap; }

tr.row-even { background-color: var(--row-even); } tr.row-odd { background-color: var(--row-odd); }
tr.group-hover td { background-color: var(--accent) !important; cursor: pointer; }

.col-desc { color: var(--col-desc); text-align: left !important; padding-left: 14px !important; }
.col-filt { color: var(--col-filt); } .col-coat { color: var(--col-coat); }
.col-mat  { color: var(--col-mat); } .col-idx  { color: var(--col-idx); }
.col-diam { color: var(--col-diam); } .col-base { color: var(--col-base); }
.col-tfc  { color: var(--col-tfc); } .col-tbc  { color: var(--col-tbc); } .col-sag  { color: var(--col-sag); }
.empty-bullet { display: block; text-align: center; width: 100%; }
.highlight-cyl { color: var(--col-idx); font-weight: bold; }

th.bg-desc { background-color: var(--col-desc); color: var(--bg-main); }
th.bg-filt { background-color: var(--col-filt); color: var(--bg-main); }
th.bg-coat { background-color: var(--col-coat); color: var(--bg-main); }
th.bg-mat  { background-color: var(--col-mat); color: var(--bg-main); }
th.bg-idx  { background-color: var(--col-idx); color: var(--bg-main); }
th.bg-diam { background-color: var(--col-diam); color: var(--bg-main); }
th.bg-base { background-color: var(--col-base); color: var(--bg-main); }
th.bg-tfc  { background-color: var(--col-tfc); color: var(--bg-main); }
th.bg-tbc  { background-color: var(--col-tbc); color: var(--bg-main); }
th.bg-sag  { background-color: var(--col-sag); color: var(--bg-main); }
.header-divider { border: 0; height: 1px; background: var(--bg-main); opacity: 0.5; width: 85%; margin: 4px auto; }

.modal-overlay { display: flex; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background-color: rgba(0,0,0,0.6); z-index: 9999; justify-content: center; align-items: center; }
.modal-overlay.hidden { display: none !important; }
.dialog-box { background-color: var(--win-bg); width: 870px; display: flex; flex-direction: column; padding: 2px; transform: scale(1.1); transform-origin: center; }
.modern-mode .dialog-box { display: none; }
.dialog-box * { font-family: 'MS Sans Serif Local', 'Tahoma Local', 'Arial Local', 'MS Sans Serif', 'Tahoma', 'Arial', sans-serif; font-size: 11px; color: var(--win-text); -webkit-font-smoothing: none; text-rendering: crispEdges; }
.outset-border { border-top: 1px solid var(--win-highlight); border-left: 1px solid var(--win-highlight); border-bottom: 1px solid var(--win-dark-shadow); border-right: 1px solid var(--win-dark-shadow); box-shadow: inset -1px -1px 0 var(--win-shadow), inset 1px 1px 0 var(--win-bg); }
.inset-border { border-top: 1px solid var(--win-dark-shadow); border-left: 1px solid var(--win-dark-shadow); border-bottom: 1px solid var(--win-highlight); border-right: 1px solid var(--win-highlight); box-shadow: inset 1px 1px 0 var(--win-shadow), inset -1px -1px 0 var(--win-bg); background-color: var(--win-highlight); }
.title-bar { background: linear-gradient(to right, var(--win-title), var(--win-title-fade)); color: white; padding: 2px 3px; display: flex; justify-content: space-between; align-items: center; font-weight: bold; letter-spacing: 0.5px; }
.classic-mode .title-bar { background: linear-gradient(to right, #0A246A, #A6CAF0); }
.title-bar * { color: white; } .title-bar-left, .title-bar-right { display: flex; align-items: center; gap: 4px; width: auto; }
.version-text { font-weight: normal; font-size: 10px; padding-right: 2px; }
.faux-icon { height: 14px; background: white; color: black; border: 1px solid #ccc; font-size: 7px; display: flex; justify-content: center; align-items: center; font-weight: normal; box-sizing: border-box; padding: 1px 4px 0 4px; }
.title-bar-close { background: var(--win-bg); color: black; font-weight: bold; font-size: 10px; border-top: 1px solid var(--win-highlight); border-left: 1px solid var(--win-highlight); border-bottom: 1px solid var(--win-dark-shadow); border-right: 1px solid var(--win-dark-shadow); width: 16px; height: 14px; display: flex; justify-content: center; align-items: center; cursor: default; padding: 0; box-sizing: border-box; outline: none; }
.title-bar-close:active { border-top: 1px solid var(--win-dark-shadow); border-left: 1px solid var(--win-dark-shadow); border-bottom: 1px solid var(--win-highlight); border-right: 1px solid var(--win-highlight); padding-top: 1px; padding-left: 1px; }

/* RE-ENGINEERED FLEXBOX MODAL */
.tabs-container { margin-top: 8px; padding: 0 4px; position: relative; z-index: 10; }
.tab-buttons { display: flex; gap: 2px; margin-left: 2px; }
.tab { background: var(--win-bg); padding: 4px 12px; border-top: 1px solid var(--win-highlight); border-left: 1px solid var(--win-highlight); border-right: 1px solid var(--win-dark-shadow); border-bottom: 1px solid var(--win-highlight); cursor: pointer; position: relative; user-select: none; z-index: 1; }
.tab.active { padding-top: 6px; margin-top: -2px; border-bottom: 1px solid var(--win-bg); margin-bottom: -1px; padding-bottom: 2px; z-index: 11; cursor: default; }

.dialog-content-wrapper { height: 510px; border-top: 1px solid var(--win-highlight); border-left: 1px solid var(--win-highlight); border-bottom: 1px solid var(--win-dark-shadow); border-right: 1px solid var(--win-dark-shadow); box-shadow: inset -1px -1px 0 var(--win-shadow); padding: 12px; position: relative; z-index: 5; box-sizing: border-box; display: flex; flex-direction: column;}
.tab-pane { display: none; height: 100%; flex-grow: 1;} .tab-pane.active { display: block; }
.grid-3-col { display: grid; grid-template-columns: 275px 235px 285px; gap: 16px; justify-content: center; height: 100%; }

/* TOP-DOWN FLEX STACKING FOR THE MODAL COLUMNS */
.col-flex { display: flex; flex-direction: column; height: 100%; justify-content: flex-start; gap: 12px; }
.col-center { display: flex; justify-content: center; align-items: center; }

.grid-2-col { display: grid; grid-template-columns: 1fr 1fr; gap: 40px; padding: 10px 40px; box-sizing: border-box; }
.center-col { display: flex; flex-direction: column; align-items: center; padding-top: 20px; }
.form-row { display: flex; align-items: center; margin-bottom: 4px; height: 19px; min-height: 19px; }
.form-row label { width: 135px; flex-shrink: 0; }
.form-row input[type="text"], .form-row select { flex-grow: 1; height: 19px !important; min-height: 19px !important; padding: 1px 3px; box-sizing: border-box; background: var(--win-highlight); color: var(--win-text);}
.form-row select { height: 21px !important; min-height: 21px !important; border-radius: 0; }
.fixed-width { flex-grow: 0 !important; } .uniform-dropdown-width { width: 125px !important; flex-grow: 0 !important; }
.form-row input[readonly] { background-color: var(--win-bg); }
.classic-table { border-collapse: collapse; background: var(--win-highlight); border: 1px solid var(--win-shadow); }
.classic-table th { background: var(--win-bg); font-weight: normal; border-top: 1px solid var(--win-highlight); border-left: 1px solid var(--win-highlight); border-right: 1px solid var(--win-shadow); border-bottom: 1px solid var(--win-shadow); padding: 2px 4px; text-align: left; }
.classic-table td { border-right: 1px solid var(--win-bg); border-bottom: 1px solid var(--win-bg); padding: 1px 4px; height: 15px; color: var(--win-text); background: var(--win-highlight); }
.grid-lines td { border: 1px solid silver; }
.table-title { background: var(--win-bg); font-weight: bold; text-align: center !important; border-top: 1px solid var(--win-highlight); border-left: 1px solid var(--win-highlight); border-right: 1px solid var(--win-shadow); border-bottom: 1px solid var(--win-shadow); padding: 4px !important; }
fieldset { border-top: 1px solid var(--win-shadow); border-left: 1px solid var(--win-shadow); border-bottom: 1px solid var(--win-highlight); border-right: 1px solid var(--win-highlight); padding: 10px 8px 10px 8px; margin: 0; }
legend { padding: 0 4px; margin-left: 4px; }
.win-btn { padding: 3px 12px; min-width: 75px; background: var(--win-bg); cursor: default; }
.win-btn:active { border-top: 1px solid var(--win-dark-shadow); border-left: 1px solid var(--win-dark-shadow); border-bottom: 1px solid var(--win-highlight); border-right: 1px solid var(--win-highlight); box-shadow: inset 1px 1px 0 var(--win-shadow), inset -1px -1px 0 var(--win-bg); padding-top: 4px; padding-left: 13px; }
.footer { display: flex; justify-content: space-between; align-items: center; padding: 10px; }

.modern-box { display: none; background-color: var(--win-bg); width: 800px; border-radius: 12px; padding: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.8); border: 1px solid var(--border-light); font-family: 'Ubuntu Sans Nerd', sans-serif; color: var(--win-text); }
.classic-mode .modern-box { display: none; } .modern-mode .modern-box { display: flex; flex-direction: column; gap: 20px; }
.modern-header { display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 1px solid var(--border-dark); padding-bottom: 15px; }
.modern-title { font-size: 24px; font-weight: bold; color: var(--win-title-text); margin: 0; }
.modern-subtitle { font-size: 14px; color: var(--col-desc); opacity: 0.8; margin-top: 4px; }
.modern-close { background: none; border: none; color: var(--win-text); font-size: 20px; cursor: pointer; padding: 5px; opacity: 0.6; } .modern-close:hover { opacity: 1; color: var(--col-tfc); }
.modern-cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; }
.mod-card { background: var(--bg-table); border: 1px solid var(--border-dark); border-radius: 8px; padding: 12px; }
.mod-card-label { font-size: 12px; text-transform: uppercase; color: var(--col-mat); font-weight: bold; letter-spacing: 0.05em; margin-bottom: 5px; }
.mod-card-val { font-size: 16px; color: var(--text-main); }
.modern-grids { display: grid; grid-template-columns: 3fr 2fr; gap: 20px; }
.modern-table-wrap { background: var(--bg-table); border-radius: 8px; border: 1px solid var(--border-dark); overflow: hidden; }
.modern-table-wrap table { width: 100%; border-collapse: collapse; }
.modern-table-wrap th { background: var(--win-highlight); padding: 8px 12px; font-size: 12px; color: var(--win-text); text-align: left; font-weight: bold; }
.modern-table-wrap td { padding: 8px 12px; border-bottom: 1px solid var(--border-dark); font-size: 14px; }
.modern-table-wrap tr:last-child td { border-bottom: none; }
        """.strip())

    js_path = os.path.join(template_dir, 'app.js')
    with open(js_path, 'w', encoding='utf-8') as f:
        f.write(r"""
async function pureSHA256(ascii) {
    function rightRotate(value, amount) { return (value >>> amount) | (value << (32 - amount)); };
    var mathPow = Math.pow; var maxWord = mathPow(2, 32); var lengthProperty = 'length'
    var i, j; var result = ''; var words = []; var asciiBitLength = ascii[lengthProperty]*8;
    var hash = [], k = []; var primeCounter = k[lengthProperty];
    var isComposite = {};
    for (var candidate = 2; primeCounter < 64; candidate++) {
        if (!isComposite[candidate]) {
            for (i = 0; i < 313; i += candidate) isComposite[i] = candidate;
            hash[primeCounter] = (mathPow(candidate, .5)*maxWord)|0; k[primeCounter++] = (mathPow(candidate, 1/3)*maxWord)|0;
        }
    }
    ascii += '\x80';
    while (ascii[lengthProperty]%64 - 56) ascii += '\x00';
    for (i = 0; i < ascii[lengthProperty]; i++) {
        j = ascii.charCodeAt(i);
        if (j>>8) return;
        words[i>>2] |= j << ((3 - i)%4)*8;
    }
    words[words[lengthProperty]] = ((asciiBitLength/maxWord)|0); words[words[lengthProperty]] = (asciiBitLength)
    for (j = 0; j < words[lengthProperty];) {
        var w = words.slice(j, j += 16); var oldHash = hash; hash = hash.slice(0, 8);
        for (i = 0; i < 64; i++) {
            var w15 = w[i - 15], w2 = w[i - 2]; var a = hash[0], e = hash[4];
            var temp1 = hash[7] + (rightRotate(e, 6) ^ rightRotate(e, 11) ^ rightRotate(e, 25)) + ((e&hash[5])^((~e)&hash[6])) + k[i] + (w[i] = (i < 16) ? w[i] : (w[i - 16] + (rightRotate(w15, 7) ^ rightRotate(w15, 18) ^ (w15>>>3)) + w[i - 7] + (rightRotate(w2, 17) ^ rightRotate(w2, 19) ^ (w2>>>10)))|0);
            var temp2 = (rightRotate(a, 2) ^ rightRotate(a, 13) ^ rightRotate(a, 22)) + ((a&hash[1])^(a&hash[2])^(hash[1]&hash[2]));
            hash = [(temp1 + temp2)|0].concat(hash); hash[4] = (hash[4] + temp1)|0;
        }
        for (i = 0; i < 8; i++) hash[i] = (hash[i] + oldHash[i])|0;
    }
    for (i = 0; i < 8; i++) {
        for (j = 3; j + 1; j--) {
            var b = (hash[i]>>(j*8))&255; result += ((b < 16) ? 0 : '') + b.toString(16);
        }
    }
    return result;
}

function fmt(val, dec) {
    let parsed = parseFloat(val);
    if (isNaN(parsed)) return '<span class="empty-bullet">•</span>';
    if (parsed === 0) return (0).toFixed(dec); return parsed.toFixed(dec);
}

// FORMAT POWER LOGIC UPDATE: PL and DASH
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
    else sphStr = isMinus ? `${formatPower(maxSph)} - ${formatPower(minSph)}` : `${formatPower(minSph)} - ${formatPower(maxSph)}`;
    if (!isCyl) return sphStr;
    let minCyl = Math.min(...arr.map(a => a.cyl));
    return `${sphStr}; <span class="highlight-cyl">${minCyl.toFixed(2)} cyl</span>`;
}

document.addEventListener('DOMContentLoaded', async () => {
    const toggleCb = document.getElementById('theme-toggle-cb');
    if (toggleCb) {
        if(localStorage.getItem('ui-theme') === 'classic') {
            document.documentElement.className = 'classic-mode';
            toggleCb.checked = false;
        } else {
            toggleCb.checked = true;
        }
        toggleCb.addEventListener('change', (e) => {
            const isClassic = !e.target.checked;
            document.documentElement.className = isClassic ? 'classic-mode' : 'modern-mode';
            localStorage.setItem('ui-theme', isClassic ? 'classic' : 'modern');
        });
    }

    if (typeof CURRENT_MFG !== 'undefined' && typeof encodedShard !== 'undefined') {
        const hashHex = await pureSHA256(encodedShard);
        if (securityManifest.shards[CURRENT_MFG + '_shard.js'] === hashHex) {
            const binaryString = atob(encodedShard);
            const bytes = new Uint8Array(binaryString.length);
            for (let i = 0; i < binaryString.length; i++) bytes[i] = binaryString.charCodeAt(i);
            const jsonString = new TextDecoder('utf-8').decode(bytes);
            
            let rawData = JSON.parse(jsonString);
            
            rawData.sort((a, b) => {
                let getWeight = (desc) => {
                    if (desc.startsWith('FSV')) return 1;
                    if (desc.startsWith('SFSV')) return 2;
                    if (desc.includes('PAL')) return 3;
                    if (desc.includes('BIFOCAL')) {
                        let m = desc.match(/FT(\d+)/);
                        return 4 + (m ? (parseInt(m[1])/1000) : 0);
                    }
                    if (desc.includes('TRIFOCAL')) {
                        let m = desc.match(/(\d+)x/);
                        return 5 + (m ? (parseInt(m[1])/1000) : 0);
                    }
                    return 6;
                };
                let descA = String(a.Description || a.Name || '').toUpperCase();
                let descB = String(b.Description || b.Name || '').toUpperCase();
                let wA = getWeight(descA);
                let wB = getWeight(descB);
                if (wA !== wB) return wA - wB;
                return descA.localeCompare(descB);
            });
            window.lensDatabase = rawData;
            renderTable(window.lensDatabase);
        } else {
            document.getElementById('table-container').innerHTML = `<h2 style="color: #ff757f; text-align: center;">󰅙 TAMPER ALERT: Signature invalid for ${CURRENT_MFG}. Execution Halted.</h2>`;
        }
    }

    window.hoverGrp = function(gid) { document.querySelectorAll('.' + gid).forEach(el => el.classList.add('group-hover')); };
    window.leaveGrp = function(gid) { document.querySelectorAll('.' + gid).forEach(el => el.classList.remove('group-hover')); };

    function renderTable(data) {
        const container = document.getElementById('table-container');
        window.activeViewData = [];
        
        let html = `<div class="table-container"><table class="data-grid"><thead><tr>
            <th class="bg-desc" style="text-align: left; padding-left: 14px;">Description</th>
            <th class="bg-filt">Filter</th>
            <th class="bg-coat">Coating</th>
            <th class="bg-mat">Material</th>
            <th class="bg-idx">Index</th>
            <th class="bg-diam">Diameter</th>
            <th class="bg-base">Minus Sph<hr class="header-divider">Base Curves</th>
            <th class="bg-tfc">Minus with Cylinder<hr class="header-divider">True Front Curve</th>
            <th class="bg-tbc">Plus Sph<hr class="header-divider">True Back Curve</th>
            <th class="bg-sag">Plus with Cylinder<hr class="header-divider">SAG at 50mm</th>
        </tr></thead><tbody>`;
        
        let buckets = {};
        
        data.forEach(lens => {
            let cleanDesc = (lens['Description'] || lens['Name'] || '').trim();
            let cleanFilt = (lens['Filter'] || '').trim();
            
            let colorRegex = /\b(EXG3|XTR|Extra\s*Active|Extra\s*Gr[ae]y|PGY3|Pro\s*Gr[ae]y|PBN3|Pro\s*Brown|PIO3|Pioneer|BRG[1-3]?|BURG|BURGUNDY|GRY[1-3]?|GRAY|GREY|BRN[1-3]?|BROWN|G-15|GRN[1-3]?|GREEN|BLU[1-3]?|BLUE|YEL[1-3]?|YLW|YELLOW|PNK[1-3]?|ROS[1-3]?|ROSE|PINK|PUR[1-3]?|PRP[1-3]?|PLUM|PURPLE)\b/ig;
            let colors = [];
            let hasExtra = false;
            
            let extColor = (match) => {
                let c = match.toUpperCase();
                if (c.match(/EXG3|XTR|EXTRA\s*ACTIVE/)) { hasExtra = true; return ''; }
                if (c.match(/EXTRA\s*GR[AE]Y/)) { colors.push('Extra Gray'); return ''; }
                if (c.match(/PGY3|PRO\s*GR[AE]Y/)) { colors.push('Gray'); return ''; }
                if (c.match(/PBN3|PRO\s*BROWN/)) { colors.push('Brown'); return ''; }
                if (c.match(/^PIO|PIONEER/)) { colors.push('G-15'); return ''; }
                if (c.match(/BRG|BURG/)) { colors.push('Burgundy'); return ''; }
                if (c.match(/^GRY|GRAY|GREY/)) { colors.push('Gray'); return ''; }
                if (c.match(/^BRN|BROWN/)) { colors.push('Brown'); return ''; }
                if (c === 'G-15') { colors.push('G-15'); return ''; }
                if (c.match(/^GRN|GREEN/)) { colors.push('Green'); return ''; }
                if (c.match(/^BLU|BLUE/)) { colors.push('Blue'); return ''; }
                if (c.match(/^YEL|YLW|YELLOW/)) { colors.push('Yellow'); return ''; }
                if (c.match(/^PNK|ROS|PINK/)) { colors.push('Pink'); return ''; }
                if (c.match(/^PUR|PRP|PLUM/)) { colors.push('Purple'); return ''; }
                return '';
            };

            cleanDesc = cleanDesc.replace(colorRegex, extColor).replace(/\s{2,}/g, ' ').trim();
            cleanFilt = cleanFilt.replace(colorRegex, extColor).replace(/\s{2,}/g, ' ').trim();
            
            if (hasExtra && colors.length === 0) colors.push('Extra Gray');
            let isPhoto = /PhotoFusion|Transition|Photochromic|Quick-Change|Sensitivity|LifeRx/i.test(cleanDesc);
            if (isPhoto && colors.length === 0 && !hasExtra) colors.push('Gray');
            if (hasExtra) colors = colors.map(col => col.startsWith('Extra') ? col : `Extra ${col}`);
            
            lens['_extractedColors'] = colors;
            lens['_cleanFilt'] = cleanFilt || '';
            
            let baseCoat = (lens['Coating'] || 'Uncoated').trim();
            let routeCoat = baseCoat;
            if (['UC', 'SR', 'UNCOATED', 'HC', 'HARD COAT'].includes(baseCoat.toUpperCase())) routeCoat = 'Standard (UC/SR)';
            else if (baseCoat.toUpperCase().includes('AR') || baseCoat.toUpperCase().includes('A/R') || baseCoat.toUpperCase().includes('HMC')) routeCoat = `Premium (${baseCoat})`;

            const key = `${cleanDesc}:::${lens['_cleanFilt']}:::${routeCoat}:::${lens['Material'] || ''}:::${lens['Index'] || ''}:::${lens['Class'] || ''}`;
            if(!buckets[key]) buckets[key] = [];
            buckets[key].push({...lens});
        });

        let groupIndex = 0;
        for (const [key, bucketData] of Object.entries(buckets)) {
            const parts = key.split(':::');
            const baseDesc = parts[0]; const baseFiltRaw = parts[1]; const routeCoat = parts[2];
            const mat = parts[3]; let rawIdx = parseFloat(parts[4]);
            const idx = isNaN(rawIdx) ? parts[4] : rawIdx.toFixed(3);
            const lensClass = parts[5];
            let folded = [];
            
            if (lensClass === 'FIN') {
                let diamBuckets = {};
                bucketData.forEach(r => {
                    let d = String(r['Diameter']||'').replace(/mm/ig,'').trim();
                    if(!diamBuckets[d]) diamBuckets[d] = [];
                    diamBuckets[d].push({ sph: parseFloat(r['SPH/BASE']) || 0, cyl: parseFloat(r['CYL/ADD']) || 0, row: r });
                });
                for (const [d, powers] of Object.entries(diamBuckets)) {
                    let minusSph = powers.filter(p => p.sph <= 0 && p.cyl === 0); let minusCyl = powers.filter(p => p.sph <= 0 && p.cyl < 0);
                    let plusSph  = powers.filter(p => p.sph > 0 && p.cyl === 0);  let plusCyl  = powers.filter(p => p.sph > 0 && p.cyl < 0);
                    folded.push({
                        ...powers[0].row,
                        'Diameter': d ? d : '<span class="empty-bullet">•</span>',
                        'Base': getRangeString(minusSph, false), 'Front TC': getRangeString(minusCyl, true),
                        'Back TC': getRangeString(plusSph, false), 'SAG': getRangeString(plusCyl, true)
                    });
                }
            } else {
                bucketData.forEach(row => {
                    let merged = false;
                    for(let f of folded) {
                        let fDiam = String(f['Diameter']||'').replace(/mm/ig,'').trim();
                        let rDiam = String(row['Diameter']||'').replace(/mm/ig,'').trim();
                        
                        if(parseFloat(f['SPH/BASE']) === parseFloat(row['SPH/BASE']) &&
                           parseFloat(f['Front TC']) === parseFloat(row['Front TC']) &&
                           parseFloat(f['SAG']) === parseFloat(row['SAG'])) {
                            if (fDiam === rDiam || fDiam.includes(rDiam)) { merged = true; break; }
                            else { f['Diameter'] = `${f['Diameter']} / ${rDiam}`; merged = true; break; }
                        }
                    }
                    if(!merged) {
                        let newRow = {...row};
                        newRow['Diameter'] = String(newRow['Diameter']||'').replace(/mm/ig,'').trim();
                        folded.push(newRow);
                    }
                });
                folded.sort((a, b) => parseFloat(a['SPH/BASE']) - parseFloat(b['SPH/BASE']));
                folded.forEach(f => {
                    let d = f['Diameter'];
                    f['Diameter'] = d ? d.split('/').map(x => x.trim()).join(' / ') : '<span class="empty-bullet">•</span>';
                    f['BaseOut'] = fmt(f['SPH/BASE'], 2); f['FtcOut'] = fmt(f['Front TC'], 2);
                    f['BtcOut'] = fmt(f['Back TC'], 2); f['SagOut'] = fmt(f['SAG'], 2);
                });
            }

            let allColors = new Set();
            bucketData.forEach(r => { if(r._extractedColors) r._extractedColors.forEach(c => allColors.add(c)); });
            let colorArr = Array.from(allColors).sort((a,b) => {
                let weight = { 'Gray': 1, 'Brown': 2, 'G-15': 3, 'Green': 4 };
                let wA = weight[a] || 5; let wB = weight[b] || 5;
                if(wA !== wB) return wA - wB;
                return a.localeCompare(b);
            });
            
            let colorStr = '';
            if (colorArr.length > 0) {
                let chunks = [];
                for(let i=0; i<colorArr.length; i+=3) chunks.push(colorArr.slice(i, i+3).join(', '));
                colorStr = chunks.join('<br>');
            }
            
            let cleanBaseFilt = baseFiltRaw;
            if(/none/i.test(cleanBaseFilt)) cleanBaseFilt = cleanBaseFilt.replace(/none/ig, '').trim();
            
            let finalFilter = cleanBaseFilt;
            if(colorStr) finalFilter = cleanBaseFilt ? `${cleanBaseFilt}<br><span style="color:var(--col-coat); font-style:italic;">${colorStr}</span>` : `<span style="color:var(--col-coat); font-style:italic;">${colorStr}</span>`;
            if(!finalFilter || finalFilter === '/' || finalFilter === '') finalFilter = 'Clear';

            let coatArr = Array.from(new Set(bucketData.map(r => r['Coating'] || 'Uncoated')));
            let finalCoat = routeCoat.includes('Standard') ? coatArr.join(' / ') : coatArr[0];

            const rowspan = folded.length;
            const rowClass = groupIndex % 2 === 0 ? 'row-even' : 'row-odd';
            const grpId = `grp-${groupIndex}`;
            let masterBucketObject = { bucket: bucketData, finalDesc: baseDesc, finalFilt: finalFilter, coat: finalCoat, mat: mat, idx: idx, isFin: lensClass === 'FIN', coatArr: coatArr, tabColorArr: colorArr };
            
            folded.forEach((row, i) => {
                window.activeViewData.push({ repRow: row, master: masterBucketObject });
                const dataIndex = window.activeViewData.length - 1;
                html += `<tr class="${rowClass} ${grpId}" onmouseenter="hoverGrp('${grpId}')" onmouseleave="leaveGrp('${grpId}')" onclick='openModal(${dataIndex})'>`;
                
                if (i === 0) {
                    html += `<td class="col-desc" rowspan="${rowspan}"><b>${baseDesc}</b></td>`;
                    html += `<td class="col-filt" rowspan="${rowspan}">${finalFilter}</td>`;
                    html += `<td class="col-coat" rowspan="${rowspan}">${finalCoat}</td>`;
                    html += `<td class="col-mat" rowspan="${rowspan}">${mat}</td>`;
                    html += `<td class="col-idx" rowspan="${rowspan}">${idx}</td>`;
                }
                
                html += `<td class="col-diam">${row['Diameter']}</td>`;
                html += `<td class="col-base">${lensClass === 'FIN' ? row['Base'] : row['BaseOut']}</td>`;
                html += `<td class="col-tfc">${lensClass === 'FIN' ? row['Front TC'] : row['FtcOut']}</td>`;
                html += `<td class="col-tbc">${lensClass === 'FIN' ? row['Back TC'] : row['BtcOut']}</td>`;
                html += `<td class="col-sag">${lensClass === 'FIN' ? row['SAG'] : row['SagOut']}</td>`;
                html += `</tr>`;
            });
            groupIndex++;
        }
        container.innerHTML = html + `</tbody></table></div>`;
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
        const lensTypeCode = document.getElementById('mod-type-code');
        const progressiveTypeRow = document.getElementById('progressive-type-row');
        if (lensTypeCode && progressiveTypeRow) progressiveTypeRow.style.visibility = (lensTypeCode.value.includes('6.')) ? 'visible' : 'hidden';
    };

    // DYNAMIC LMS STRING GENERATOR 
    function generateLmsNames(rep, master) {
        let isFin = rep['Class'] === 'FIN';
        let ast = isFin ? '*' : '';
        let style = parseInt(rep['Style']);
        
        let s_type = '';
        if ([10,11,12,15].includes(style)) {
            let sw = rep['Seg Width'] ? rep['Seg Width'].toString().replace('.0','') : '';
            let ih = rep['Intermediate Ht'] ? rep['Intermediate Ht'].toString().replace('.0','') : '';
            if(sw && ih) s_type = `TRI ${ih}x${sw}`;
            else {
                let m = (rep['Description']||'').match(/(\d{1,2}x\d{2})/i);
                s_type = m ? `TRI ${m[1].toLowerCase()}` : 'TRI';
            }
        } else if ([2,3,4,5,8,9,16].includes(style)) {
            let sw = rep['Seg Width'] ? rep['Seg Width'].toString().replace('.0','') : '';
            if(sw) s_type = `FT${sw}`;
            else {
                let m = (rep['Description']||'').match(/FT(\d{2})/i);
                s_type = m ? `FT${m[1]}` : 'BIFOCAL';
            }
        } else if (style === 6) {
            s_type = ''; // Stripping "PAL" explicitly per request
        } else {
            s_type = isFin ? 'FSV' : 'SFSV';
        }

        let rawText = ((rep['Description']||'') + ' ' + (rep['Name']||'') + ' ' + (master.finalFilt||'')).toUpperCase();
        let s_brand = '';
        if (style === 6) {
            let b_clean = rawText.replace(/\b(FIN|SF|PAL|PROG|PROGRESSIVE|POLY|CR-39|TRIVEX|1\.\d{2}|AS|ASPHERIC|POLARIZED|POL|PHOT|PHT|PHOTOFUSION|TRANSITIONS?|LIFERX|BLUEGUARD|BG|HEV)\b/gi, '').trim();
            b_clean = b_clean.replace(/[^A-Z0-9\s-]/g, '').replace(/\s{2,}/g, ' ').trim();
            s_brand = b_clean.split(' ').slice(0, 2).join(' ');
        }

        let s_mat = '';
        let mat = rep['Material'] || '';
        let idx = rep['Index'] || '';
        if (mat.includes('CR-39')) s_mat = 'CR-39';
        else if (mat.includes('Poly')) s_mat = 'POLY';
        else if (mat.includes('Trivex')) s_mat = 'TRIVEX';
        else if (idx) s_mat = parseFloat(idx).toFixed(2); // Keeps 1.67 intact

        let has_as = /\b(AS|ASPHERIC)\b/.test(rawText);
        let has_pol = /\b(POL|POLARIZED|NUPOLAR|TRUPOLAR)\b/.test(rawText);
        let has_pht = /\b(PHOT|PHT|PHOTOFUSION|TRANSITIONS?|LIFERX)\b/.test(rawText);
        let has_bg = /\b(BG|BLUEGUARD)\b/.test(rawText);

        // -- BRIEF DESCRIPTION ASSEMBLY (Max 15) --
        function buildBrief(brandStr, incPHT, incBG, incPOL, incAS) {
            let parts = [];
            if (s_type) parts.push(s_type);
            if (brandStr) parts.push(brandStr);
            if (s_mat) parts.push(s_mat);
            if (incAS && has_as) parts.push('AS');
            if (incPOL && has_pol) parts.push('POL');
            if (incBG && has_bg) parts.push('BG');
            if (incPHT && has_pht) parts.push('PHT');
            return ast + parts.join(' ').replace(/\s{2,}/g, ' ');
        }

        let briefDesc = "";
        let curBrand = s_brand;
        let pht = true, bg = true, pol = true, as = true;
        
        let testStr = buildBrief(curBrand, pht, bg, pol, as);
        if (testStr.length <= 15) {
            briefDesc = testStr;
        } else {
            // Crush the brand from the right side
            while (curBrand.length > 0 && buildBrief(curBrand, pht, bg, pol, as).length > 15) {
                curBrand = curBrand.slice(0, -1).trim();
            }
            if (buildBrief(curBrand, pht, bg, pol, as).length <= 15) {
                briefDesc = buildBrief(curBrand, pht, bg, pol, as);
            } else {
                // If brand is totally gone and it's STILL > 15 chars, execute smart drop
                pht = false;
                if (buildBrief('', pht, bg, pol, as).length <= 15) briefDesc = buildBrief('', pht, bg, pol, as);
                else {
                    bg = false;
                    if (buildBrief('', pht, bg, pol, as).length <= 15) briefDesc = buildBrief('', pht, bg, pol, as);
                    else {
                        pol = false;
                        if (buildBrief('', pht, bg, pol, as).length <= 15) briefDesc = buildBrief('', pht, bg, pol, as);
                        else {
                            as = false; // Emergency drop
                            briefDesc = buildBrief('', pht, bg, pol, as).substring(0,15);
                        }
                    }
                }
            }
        }

        // -- LONG DESCRIPTION ASSEMBLY (Max 32) --
        let expandedPht = "";
        if (has_pht) {
            let pMatch = rawText.match(/\b(PHOTOFUSION(?:\s*X)?|TRANSITIONS?(?:\s*\w+)?|LIFERX)\b/);
            expandedPht = pMatch ? pMatch[1] : "PHOTOCHROMIC";
        }
        let expandedPol = "";
        if (has_pol) {
            if (/\bNUPOLAR\b/.test(rawText)) expandedPol = "NUPOLAR";
            else if (/\bTRUPOLAR\b/.test(rawText)) expandedPol = "TRUPOLAR";
            else expandedPol = "POL"; 
        }
        
        function buildLong(brandStr) {
            let parts = [];
            if (s_type) parts.push(s_type);
            if (brandStr) parts.push(brandStr);
            if (s_mat) parts.push(s_mat);
            if (has_as) parts.push('AS');
            if (expandedPol) parts.push(expandedPol);
            if (has_bg) parts.push('BLUEGUARD');
            if (expandedPht) parts.push(expandedPht);
            return ast + parts.join(' ').replace(/\s{2,}/g, ' ');
        }

        let longDesc = "";
        let curLongBrand = s_brand;
        if (buildLong(curLongBrand).length <= 32) {
            longDesc = buildLong(curLongBrand);
        } else {
            // Crush the brand if 32 is somehow breached
            while (curLongBrand.length > 0 && buildLong(curLongBrand).length > 32) {
                curLongBrand = curLongBrand.slice(0, -1).trim();
            }
            longDesc = buildLong(curLongBrand).substring(0, 32);
        }

        return { brief: briefDesc, long: longDesc };
    }

    window.openModal = function(dataIndex) {
        const viewItem = window.activeViewData[dataIndex];
        if (!viewItem) return;
        
        const rep = viewItem.master.bucket[0];
        const isProg = parseInt(rep['Style']) === 6;

        let idStr = rep['Description'] + rep['Index'];
        let hashNum = 0; for(let i=0;i<idStr.length;i++) hashNum = Math.imul(31, hashNum) + idStr.charCodeAt(i) | 0;
        let idDisplay = Math.abs(hashNum).toString().substring(0,6).padStart(6, '0');
        
        // Generate the strict LMS strings dynamically!
        let lmsData = generateLmsNames(rep, viewItem.master);
        let modalLongDesc = lmsData.long;
        let modalBriefDesc = lmsData.brief; 

        // Preserve original descriptive view for the header
        let webDesc = viewItem.master.isFin ? '*' + viewItem.master.finalDesc : viewItem.master.finalDesc;

        let lensTypeStr = "Single Vision";
        if(isProg) lensTypeStr = "Progressive";
        else if([2,3,4,5,8,9,10,11,12,15,16].includes(parseInt(rep['Style']))) lensTypeStr = "Multi-Focal";

        let modTitle = document.getElementById('mod-modern-title'); if(modTitle) modTitle.innerText = webDesc;
        let modSub = document.getElementById('mod-modern-sub'); if(modSub) modSub.innerText = `${rep['MFG'] || 'Unknown'} | ID: ${idDisplay}`;
        let modFilt = document.getElementById('mod-modern-filt'); if(modFilt) modFilt.innerHTML = `${viewItem.master.finalFilt} / ${viewItem.master.coat}`;
        let modMat = document.getElementById('mod-modern-mat'); if(modMat) modMat.innerText = `${viewItem.master.mat} / ${viewItem.master.idx}`;
        let modType = document.getElementById('mod-modern-type'); if(modType) modType.innerText = `${lensTypeStr} ${rep['Seg Width'] ? '(Seg: '+rep['Seg Width']+')' : ''}`;
        
        let mid = document.getElementById('mod-id'); if(mid) mid.value = idDisplay;
        let mmfg = document.getElementById('mod-mfg'); if(mmfg) mmfg.value = rep['MFG'] || '';
        
        // Inject the LMS formatted strings into inputs
        let mbrief = document.getElementById('mod-brief'); if(mbrief) mbrief.value = modalBriefDesc;
        let mlong = document.getElementById('mod-long'); if(mlong) mlong.value = modalLongDesc;
        
        let selStyle = parseInt(rep['Style']);
        let elType = document.getElementById('mod-type-code');
        if(elType && !isNaN(selStyle)) { elType.selectedIndex = selStyle; toggleProgressive(); }
        
        let mseg = document.getElementById('mod-seg-width'); if(mseg) mseg.value = rep['Seg Width'] || '';
        let mmatn = document.getElementById('mod-mat-name'); if(mmatn) mmatn.value = rep['Material Brand'] || rep['Material'] || '';
        let mmatc = document.getElementById('mod-mat-cat'); if(mmatc) mmatc.innerHTML = `<option>${rep['Material']}</option>`;
        let midx = document.getElementById('mod-idx'); if(midx) midx.value = rep['Index'] || '';
        
        let mopcr = document.getElementById('mod-opc-right'); if(mopcr) mopcr.value = rep['Right OPC'] || '';
        let mopcl = document.getElementById('mod-opc-left'); if(mopcl) mopcl.value = rep['Left OPC'] || '';
        let needsLeft = (rep['Left OPC'] && rep['Left OPC'] !== rep['Right OPC']) ? 'Yes' : 'No';
        let mrlsel = document.getElementById('mod-rl-sel'); if(mrlsel) mrlsel.innerHTML = `<option>${needsLeft}</option>`;
        
        let mbowl = document.getElementById('mod-bowl-dia'); if(mbowl) mbowl.value = rep['Bowl Dia'] || '0';
        
        const ctcDict = {
            'Plastic (CR-39)': '2.2', 'Polycarbonate': '1.5', 'Trivex': '1.5',
            'High-Index 1.60': '1.4', 'High-Index 1.60 (MR-8)': '1.4', 'High-Index 1.60 (MR-8+)': '1.4',
            'High-Index 1.67': '1.4', 'High-Index 1.67 (MR-7)': '1.4', 'High-Index 1.67 (MR-10)': '1.4',
            'High-Index 1.74': '1.4'
        };
        let mminct = document.getElementById('mod-min-ct'); 
        if(mminct) mminct.value = ctcDict[rep['Material']] || '';

        let asphFactor = isProg ? '-0.50' : '0.00';
        let surfHtml = '', thickHtml = '', blankHtml = '', modernSurf = '', modernThick = '';
        let uniqueCurves = new Map(); let uniqueDiams = new Map();

        viewItem.master.bucket.forEach(r => {
            let bRaw = parseFloat(r['SPH/BASE']); let b = fmt(bRaw, 2);
            let ftc = fmt(r['Front TC'], 2); let btc = fmt(r['Back TC'], 2);
            let ct = fmt(r['Center Thick'], 2); let dia = String(r['Diameter']).replace(/mm/ig, '').trim();
            let inset = fmt(r['Inset'], 2); let drop = fmt(r['Drop'], 2);

            if (!isNaN(bRaw)) {
                let curveKey = `${b}`; 
                if (!uniqueCurves.has(curveKey)) uniqueCurves.set(curveKey, {b, ftc, btc, asphFactor});
                let diamKey = `${dia}-${b}`;
                if (dia && !uniqueDiams.has(diamKey)) uniqueDiams.set(diamKey, {dia, b, ct, inset, drop});
            }
        });

        let sortedCurves = Array.from(uniqueCurves.values()).sort((x,y) => parseFloat(x.b) - parseFloat(y.b));
        let sortedDiams = Array.from(uniqueDiams.values()).sort((x,y) => {
            if(parseFloat(x.dia) === parseFloat(y.dia)) return parseFloat(x.b) - parseFloat(y.b);
            return parseFloat(x.dia) - parseFloat(y.dia);
        });

        for(let j=0; j<12; j++) {
            if (viewItem.master.isFin) {
                surfHtml += `<tr><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td></tr>`;
            } else if (j < sortedCurves.length) {
                let c = sortedCurves[j];
                surfHtml += `<tr><td>${c.b}</td><td>${c.ftc}</td><td>${c.asphFactor}</td><td>${c.btc}</td></tr>`;
                modernSurf += `<tr><td>${c.b}</td><td>${c.ftc}</td><td>${c.asphFactor}</td><td>${c.btc}</td></tr>`;
            } else { surfHtml += `<tr><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td></tr>`; }
        }

        for(let j=0; j<22; j++) {
            if(j < sortedDiams.length) {
                let d = sortedDiams[j];
                thickHtml += `<tr><td>&nbsp;&nbsp; ${d.dia}</td><td>${d.b}</td><td>${d.ct !== 'NaN' ? d.ct : ''}</td></tr>`;
                modernThick += `<tr><td>${d.dia}</td><td>${d.b}</td><td>${d.ct !== 'NaN' ? d.ct : ''}</td></tr>`;
            } else { thickHtml += `<tr><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td></tr>`; }
        }

        let printedDiamsForBlank = new Set(); let bCount = 0;
        sortedDiams.forEach(d => {
            if(!printedDiamsForBlank.has(d.dia) && bCount < 5) {
                blankHtml += `<tr><td>${d.dia}</td><td>${d.inset !== 'NaN' ? d.inset : ''}</td><td>${d.drop !== 'NaN' ? d.drop : ''}</td><td>${d.drop !== 'NaN' ? d.drop : ''}</td></tr>`;
                printedDiamsForBlank.add(d.dia); bCount++;
            }
        });
        for(let j=bCount; j<5; j++) blankHtml += `<tr><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td></tr>`;
        
        let modSurfBody = document.getElementById('mod-surf-tbody'); if(modSurfBody) modSurfBody.innerHTML = surfHtml;
        let modThickBody = document.getElementById('mod-thick-tbody'); if(modThickBody) modThickBody.innerHTML = thickHtml;
        let modBlankBody = document.getElementById('mod-blank-tbody'); if(modBlankBody) modBlankBody.innerHTML = blankHtml;
        let mModSurf = document.getElementById('mod-modern-surf'); if(mModSurf) mModSurf.innerHTML = modernSurf;
        let mModThick = document.getElementById('mod-modern-thick'); if(mModThick) mModThick.innerHTML = modernThick;

        let tabColorArr = viewItem.master.tabColorArr;
        if(tabColorArr.length === 0) tabColorArr.push('Clear');
        
        let rawCoatArr = viewItem.master.coatArr;
        let modalCoats = [];
        rawCoatArr.forEach(c => {
            if(c.includes('/')) { modalCoats.push(...c.split('/').map(x => x.trim())); }
            else { modalCoats.push(c); }
        });
        modalCoats = Array.from(new Set(modalCoats));
        
        let colorsHtml = '', coatsHtml = '';
        let maxRows = Math.max(25, tabColorArr.length, modalCoats.length);
        
        for(let j=0; j<maxRows; j++) {
            let cText = j < tabColorArr.length ? tabColorArr[j] : '&nbsp;';
            colorsHtml += `<tr><td>${cText}</td><td>&nbsp;</td></tr>`;
            let coatText = j < modalCoats.length ? modalCoats[j] : '&nbsp;';
            coatsHtml += `<tr><td>${coatText}</td><td>&nbsp;</td></tr>`;
        }
        let modColBody = document.getElementById('mod-col-tbody'); if(modColBody) modColBody.innerHTML = colorsHtml;
        let modCoatBody = document.getElementById('mod-coat-tbody'); if(modCoatBody) modCoatBody.innerHTML = coatsHtml;

        switchTab(1); 
        let modalOverlay = document.getElementById('tech-modal');
        if(modalOverlay) modalOverlay.classList.remove('hidden');
    };

    window.closeModal = function() { document.getElementById('tech-modal').classList.add('hidden'); };
    const modalOverlay = document.getElementById('tech-modal');
    if(modalOverlay) modalOverlay.addEventListener('click', (e) => {
        if(e.target === modalOverlay) closeModal();
    });
});
            """.strip())

    root_path = os.path.join(template_dir, 'root_template.html')
    with open(root_path, 'w', encoding='utf-8') as f:
        f.write("""
<!DOCTYPE html>
<html lang="en" class="modern-mode">
<head>
    <meta charset="UTF-8">
    <title>VCA Vault Hub</title>
    <link rel="stylesheet" href="data/styles.css">
    <script>if(localStorage.getItem('ui-theme') === 'classic') document.documentElement.className = 'classic-mode';</script>
</head>
<body>
    <header class="top-bar">
        <div class="top-bar-left"><span class="theme-label" style="font-family: 'Ubuntu Sans Nerd', sans-serif;">VCA2HTML-TUI v4.0.0</span></div>
        <div class="top-bar-center">MASTER LENS DATABASE BY MANUFACTURERS</div>
        <div class="top-bar-right">
            <span class="theme-label" style="font-size: 18px;">󰖨</span>
            <label class="theme-switch">
                <input type="checkbox" id="theme-toggle-cb" checked>
                <span class="slider"></span>
            </label>
            <span class="theme-label" style="font-size: 18px;">󰖔</span>
        </div>
    </header>
    <main class="hub-container">
        <h2>Manufacturer Vaults</h2>
        <ul class="mfg-list">{{MFG_LIST}}</ul>
    </main>
    <script src="data/app.js"></script>
</body></html>
        """.strip())

    mfg_path = os.path.join(template_dir, 'mfg_template.html')
    with open(mfg_path, 'w', encoding='utf-8') as f:
        f.write("""
<!DOCTYPE html>
<html lang="en" class="modern-mode">
<head>
    <meta charset="UTF-8">
    <title>{{CURRENT_MFG}} Data Grid</title>
    <link rel="stylesheet" href="../data/styles.css">
    <script>if(localStorage.getItem('ui-theme') === 'classic') document.documentElement.className = 'classic-mode';</script>
</head>
<body>
    <header class="top-bar">
        <div class="top-bar-left"><a href="../index.html" class="nav-toggle" style="font-family: 'Ubuntu Sans Nerd', sans-serif;">󰎹 « Back to Vault</a></div>
        <div class="top-bar-center">MASTER DATABASE FOR {{CURRENT_MFG}}</div>
        <div class="top-bar-right">
            <span class="theme-label" style="font-size: 18px;">󰖨</span>
            <label class="theme-switch">
                <input type="checkbox" id="theme-toggle-cb" checked>
                <span class="slider"></span>
            </label>
            <span class="theme-label" style="font-size: 18px;">󰖔</span>
        </div>
    </header>
    <main id="table-container"></main>
    
    <div class="modal-overlay hidden" id="tech-modal">
        <div class="dialog-box outset-border">
            <div class="title-bar">
                <div class="title-bar-left"><div class="faux-icon">VLP</div><span class="title-text">Lens Blank Specifications</span></div>
                <div class="title-bar-right"><span class="version-text">v4.0.0</span><button class="title-bar-close" onclick="closeModal()">X</button></div>
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
                        <div class="col-flex">
                            <div style="margin-top: 5px;">
                                <div class="form-row"><label>Unique ID Code</label><input type="text" id="mod-id" class="inset-border fixed-width" style="width: 75px;" readonly></div>
                                <div class="form-row"><label>Manufacturer</label><input type="text" id="mod-mfg" class="inset-border fixed-width" style="width: 90px;"></div>
                                <div class="form-row"><label>Brief Description</label><input type="text" id="mod-brief" class="inset-border fixed-width" style="width: 150px;"></div>
                                <div class="form-row"><label>Long Description</label><div style="position: relative; flex-grow: 1; height: 19px;"><input type="text" id="mod-long" class="inset-border" style="position: absolute; left: 0; top: 0; width: 250px; z-index: 10;"></div></div>
                                <div class="form-row"><label>Lens Type Code</label><select class="inset-border uniform-dropdown-width" id="mod-type-code" onchange="toggleProgressive()">
                                    <option>0. None</option><option>1. Single Vision</option><option>2. Flat Top Bif</option><option>3. Round Bif</option><option>4. Exec Bif</option><option>5. Exec Bif</option><option>6. Progressive</option><option>7. Blend Seg</option><option>8. FT Dble Seg</option><option>9. Exec Dble Seg</option><option>10. FT Trif</option><option>11. Exec Trif</option><option>12. ED Trif</option><option>13. Other SV</option><option>14. Asph SV</option><option>15. Asph FT</option><option>16. Asph Rnd</option><option>17. Asph Ultex</option><option>18. Other Multi-focal</option>
                                </select></div>
                                <div class="form-row" id="progressive-type-row" style="visibility:hidden;"><label>Progressive Type</label><select class="inset-border uniform-dropdown-width"><option>Generic</option><option>Type 1</option><option selected>Type 2</option></select></div>
                                <div class="form-row"><label>Seg Width</label><input type="text" id="mod-seg-width" class="inset-border fixed-width" style="width: 32px;"></div>
                                <div class="form-row"><label>Material Name</label><input type="text" id="mod-mat-name" class="inset-border uniform-dropdown-width"></div>
                                <div class="form-row"><label>Material Category</label><select class="inset-border uniform-dropdown-width" id="mod-mat-cat"></select></div>
                                <div class="form-row"><label>Material Index</label><input type="text" id="mod-idx" class="inset-border fixed-width" style="width: 65px;"></div>
                                <div class="form-row"><label>Rights and Lefts?</label><select class="inset-border fixed-width" id="mod-rl-sel" style="width: 65px;"></select></div>
                                <div class="form-row"><label>Vertical OC Position</label><select class="inset-border uniform-dropdown-width"><option selected>Automatic</option><option>MM Above</option><option>MM Below</option><option>Even with GC</option></select></div>
                                <div class="form-row"><label>Lenticular Field Size</label><input type="text" id="mod-bowl-dia" class="inset-border fixed-width" style="width: 32px;"></div>
                            </div>
                            <div>
                                <div class="form-row"><label>Minus Center Thick</label><input type="text" id="mod-min-ct" class="inset-border fixed-width" style="width: 65px;"></div>
                                <div class="form-row" style="align-items: flex-start; margin-bottom: 0;"><label style="line-height: normal; width: 135px;">True Curve<br>Reference Index if<br>not standard 1.530</label><input type="text" class="inset-border fixed-width" value="1.530" style="width: 65px; margin-top: 14px;"></div>
                            </div>
                        </div>
                        <div class="col-flex">
                            <div style="display: flex; justify-content: flex-end;">
                                <table style="border-collapse: collapse;"><tr><td style="text-align: left; padding-bottom: 4px; padding-right: 5px;">Preferred Supplier?</td><td style="padding-bottom: 4px;"><select class="inset-border" style="width: 45px;"><option selected>No</option><option>Yes</option></select></td></tr><tr><td style="text-align: left; padding-bottom: 4px; padding-right: 5px;">On-Line Locally?</td><td style="padding-bottom: 4px;"><select class="inset-border" style="width: 45px;"><option selected>No</option><option>Yes</option></select></td></tr><tr><td style="text-align: left; padding-bottom: 4px; padding-right: 5px;">On-Line Remotely?</td><td style="padding-bottom: 4px;"><select class="inset-border" style="width: 45px;"><option selected>No</option><option>Yes</option></select></td></tr></table>
                            </div>
                            <div class="col-center" style="flex-grow: 0;">
                                <table class="classic-table grid-lines" style="width: 220px;"><thead><tr><th>Marked<br>Base</th><th>True<br>Curve</th><th>Asph<br>Factor</th><th>Minus<br>Back</th></tr></thead><tbody id="mod-surf-tbody"></tbody></table>
                            </div>
                            <div style="text-align: center;"><div style="margin-bottom: 3px;">Product OPC Range</div><input type="text" id="mod-opc-right" class="inset-border fixed-width" style="width: 80px;"><span style="margin: 0 4px;">To</span><input type="text" id="mod-opc-left" class="inset-border fixed-width" style="width: 80px;"></div>
                        </div>
                        <div class="col-flex">
                            <div>
                                <table class="classic-table grid-lines" style="width: calc(100% - 40px); margin: 0 auto 12px auto;"><thead><tr><th>Blank<br>Size</th><th>Inset</th><th>Drop</th><th>Reading<br>Level</th></tr></thead><tbody id="mod-blank-tbody"></tbody></table>
                                <fieldset style="padding-bottom: 10px;"><legend>Custom Settings</legend><table style="width: 100%; border-collapse: collapse; margin-bottom: 8px;"><tr><td style="width: 135px; padding-bottom: 4px; text-align: left;">Fining Allowance:</td><td style="width: 35px; padding-bottom: 4px;"><input type="text" class="inset-border fixed-width" style="width: 30px;"></td><td style="padding-bottom: 4px; text-align: left;">&nbsp;&nbsp;mm</td></tr><tr><td style="padding-bottom: 4px; text-align: left;">Global Power Adjust</td><td style="padding-bottom: 4px;"><input type="text" class="inset-border fixed-width" style="width: 30px;"></td><td style="padding-bottom: 4px; text-align: left;">&nbsp;&nbsp;diopters</td></tr><tr><td style="padding-bottom: 4px; text-align: left;">Lens Flex Power Adjust</td><td style="padding-bottom: 4px;"><input type="text" class="inset-border fixed-width" style="width: 30px;"></td><td style="padding-bottom: 4px; text-align: left;">&nbsp;&nbsp;diopters</td></tr></table><div class="inset-border" style="background: var(--win-bg); padding: 4px; margin-top: 4px; line-height: 1.3;">Note: Enter a special fining allowance only if this lens requires a different value than the .300 mm allowance currently specified for CR-39 in the Lab Setup Menu.</div></fieldset>
                            </div>
                            <div style="text-align: center;"><button class="win-btn outset-border" style="width: 185px; padding: 4px 0;">Click Here to Set Prices</button></div>
                        </div>
                    </div>
                </div>
                <div id="tab-content-2" class="tab-pane"><div style="height: calc(100% - 10px);" class="grid-2-col"><div><table class="classic-table grid-lines" style="width: 100%;"><thead><tr><th style="width: 60%;">Factory Colors</th><th style="width: 40%;">Pair Price</th></tr></thead><tbody id="mod-col-tbody"></tbody></table></div><div><table class="classic-table grid-lines" style="width: 100%;"><thead><tr><th style="width: 60%;">Factory Coatings</th><th style="width: 40%;">Pair Price</th></tr></thead><tbody id="mod-coat-tbody"></tbody></table></div></div></div>
                <div id="tab-content-3" class="tab-pane"><div style="height: calc(100% - 10px);" class="center-col"><div style="width: 500px;"><table class="classic-table grid-lines" style="width: 100%;"><thead><tr><td colspan="3" class="table-title">Blank Thickness Table</td></tr><tr><th style="width: 30%;">Diameter</th><th style="width: 35%;">Base</th><th style="width: 35%;">Center Thickness</th></tr></thead><tbody id="mod-thick-tbody"></tbody></table><div style="text-align: center; margin-top: 15px; color: var(--win-shadow);">Left click any center thickness value you want to change.</div></div></div></div>
            </div>
            <div class="footer"><button class="win-btn outset-border">Print This Form</button><div style="font-weight: bold;">Warning: Incorrect data in this form will cause calculations errors!</div><div style="display: flex; gap: 15px;"><button class="win-btn outset-border" onclick="closeModal()">Cancel</button><button class="win-btn outset-border" onclick="closeModal()">Save</button></div></div>
        </div>

        <div class="modern-box">
            <div class="modern-header">
                <div>
                    <h2 class="modern-title" id="mod-modern-title">Lens Description</h2>
                    <div class="modern-subtitle" id="mod-modern-sub">MFG / ID</div>
                </div>
                <button class="modern-close" onclick="closeModal()">✖</button>
            </div>
            <div class="modern-cards">
                <div class="mod-card"><div class="mod-card-label">Filter & Coating</div><div class="mod-card-val" id="mod-modern-filt">Clear / HC</div></div>
                <div class="mod-card"><div class="mod-card-label">Material & Index</div><div class="mod-card-val" id="mod-modern-mat">Poly / 1.590</div></div>
                <div class="mod-card"><div class="mod-card-label">Lens Type</div><div class="mod-card-val" id="mod-modern-type">Single Vision</div></div>
            </div>
            <div class="modern-grids">
                <div class="modern-table-wrap">
                    <table><thead><tr><th>Base</th><th>Front TC</th><th>Asph Factor</th><th>Back TC</th></tr></thead><tbody id="mod-modern-surf"></tbody></table>
                </div>
                <div class="modern-table-wrap">
                    <table><thead><tr><th>Diameter</th><th>Base</th><th>CT</th></tr></thead><tbody id="mod-modern-thick"></tbody></table>
                </div>
            </div>
        </div>
    </div>
    
    <script src="../data/db/security_manifest.js"></script>
    <script src="../data/db/{{CURRENT_MFG}}_shard.js"></script>
    <script>const CURRENT_MFG = "{{CURRENT_MFG}}";</script>
    <script src="../data/app.js"></script>
</body></html>
        """.strip())
    
    return template_dir

def execute_html_generation():
    global global_mode, scroll_offset
    from datetime import datetime, timezone
    import shutil
    import re
    import base64
    import hashlib
    import json
    import stat
    import pandas as pd
    
    # 1. STANDARDIZED SKELETON SETUP
    sys.stdout.write(f"{C_BG}\033[2J\033[H")
    term_w, term_h = get_term_size()
    draw_top_bar()
    for r in range(2, term_h - 1): draw_frame_line("", row=r)
    draw_frame_line(f"{C_SIZE}STATIC SITE GENERATOR: HTML DEPLOYMENT{RESET}", row=2, align="center")
    
    draw_universal_footer() # THE FLOOR SEAL
    
    if not os.path.exists(DB_FILE):
        draw_frame_line(f"{C_ALERT}Error: Master database not found.{RESET}", 6, align="center")
        getch()
        global_mode = "MAIN MENU"; return
        
    # 2. INITIALIZE VIEWPORT
    viewport_logs.clear()
    scroll_offset = 0
    log_task(format_log("SYSTEM", "Awaiting SSG deployment authorization...", C_TITLE), "RAW")
    draw_viewport(progress_pct=0.0, active_file="Pending Auth...", current_file_idx=0, total_files=0, is_interactive=False)
    
    ans = draw_modal("DEPLOYMENT AUTHORIZATION", "Type DEPLOY to generate web shards:", is_password=False)
    
    # Repaint Skeleton after Modal
    sys.stdout.write(f"{C_BG}\033[2J\033[H")
    draw_top_bar()
    for r in range(2, term_h - 1): draw_frame_line("", row=r)
    draw_frame_line(f"{C_SIZE}STATIC SITE GENERATOR: HTML DEPLOYMENT{RESET}", row=2, align="center")
    draw_universal_footer()
    
    if ans != "DEPLOY": global_mode = "MAIN MENU"; return

    try:
        viewport_logs.clear()
        scroll_offset = 0
        log_task(format_log("SYSTEM", f"Opening Read-Only Buffer -> {DB_FILE}", C_FILE), "RAW")
        draw_viewport(progress_pct=0.0, active_file="Bootstrapping...", current_file_idx=0, total_files=0, is_interactive=False)
        
        os.makedirs(HTML_DIR, exist_ok=True)
        os.makedirs(HTML_DATA_DIR, exist_ok=True)
        os.makedirs(HTML_DB_DIR, exist_ok=True)
        
        log_task(format_log("DEPLOYMENT", "Bootstrapping Web Templates & Assets...", C_TITLE), "RAW")
        template_dir = bootstrap_web_templates()
        
        # ASSET ROUTING (Leaving existing fonts in /HTML/data/ alone)
        for item in ['styles.css', 'app.js']:
            src_path = os.path.join(template_dir, item)
            dest_path = os.path.join(HTML_DATA_DIR, item)
            if os.path.exists(src_path):
                shutil.copy2(src_path, dest_path)
                log_task(format_log("ROUTED", f"Asset '{item}' -> HTML/data/", C_FILE), "RAW")

        with open(DB_FILE, 'r', encoding='utf-8') as f:
            db_data = json.load(f)
        
        lenses = db_data.get('lenses', {})
        if not lenses: return
            
        df = pd.DataFrame.from_dict(lenses, orient='index')
        manufacturers = sorted(df['MFG'].dropna().unique())
        
        if 'shards' not in db_data: db_data['shards'] = {}
        total_mfgs = len(manufacturers)
        
        with open(os.path.join(template_dir, 'mfg_template.html'), 'r', encoding='utf-8') as f:
            mfg_template_str = f.read()

        root_list_html = ""

        # SHARD COMPILATION LOOP
        for idx, mfg in enumerate(manufacturers):
            clean_mfg = re.sub(r'[^a-zA-Z0-9_-]', '_', str(mfg))
            mfg_data = df[df['MFG'] == mfg].fillna("").to_dict(orient='records')
            
            log_task(format_log("BASE_SHARD", f"{mfg} -> Base64 Encoding...", C_TITLE), "RAW")
            
            json_string = json.dumps(mfg_data, separators=(',', ':'))
            b64_bytes = base64.b64encode(json_string.encode('utf-8'))
            b64_string = b64_bytes.decode('utf-8')
            
            shard_hash = hashlib.sha256(b64_bytes).hexdigest()
            log_task(format_log("SHARD_HASH", f"{shard_hash}", C_WARN), "RAW")
            
            shard_filename = f"{clean_mfg}_shard.js"
            db_data['shards'][shard_filename] = shard_hash
            
            shard_path = os.path.join(HTML_DB_DIR, shard_filename)
            with open(shard_path, 'w', encoding='utf-8') as f:
                f.write(f'const encodedShard = "{b64_string}";\n')
                
            log_task(format_log("SHARD_OUT", f"{shard_filename} ({os.path.getsize(shard_path) / (1024*1024):.2f} MB)", C_STAGED), "RAW")
                
            mfg_dir = os.path.join(HTML_DIR, clean_mfg)
            os.makedirs(mfg_dir, exist_ok=True)
            
            mfg_html = mfg_template_str.replace('{{CURRENT_MFG}}', clean_mfg)
            with open(os.path.join(mfg_dir, 'index.html'), 'w', encoding='utf-8') as f: f.write(mfg_html)
                
            root_list_html += f'<li><a href="{clean_mfg}/index.html">󰉖  {mfg}</a></li>\n'
            
            pct = ((idx + 1) / total_mfgs) * 100.0
            draw_viewport(progress_pct=pct, active_file=shard_filename, current_file_idx=idx+1, total_files=total_mfgs)
            time.sleep(0.5) 

        with open(os.path.join(template_dir, 'root_template.html'), 'r', encoding='utf-8') as f:
            root_template_str = f.read()
        
        root_html = root_template_str.replace('{{MFG_LIST}}', root_list_html)
        with open(os.path.join(HTML_DIR, 'index.html'), 'w', encoding='utf-8') as f: f.write(root_html)

        sign_master_database()
        
        master_sig = "UNSIGNED"
        if os.path.exists(SIG_FILE):
            with open(SIG_FILE, 'r') as sf: master_sig = sf.read().strip()
                
        # TIMEZONE & DIRECT MANIFEST INJECTION
        manifest_data = {
            "masterSignature": master_sig, 
            "compiled_at": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            "shards": {k: v for k, v in db_data['shards'].items() if k.endswith('_shard.js')}
        }
        
        log_task(format_log("WEB_MANIFEST", f"Compiling with {len(manifest_data['shards'])} Shard Signatures", C_PROMPT), "RAW")
        db_data['__security_manifest__'] = manifest_data
        
        try: os.chmod(DB_FILE, stat.S_IWRITE)
        except: pass
        with open(DB_FILE, 'w', encoding='utf-8') as f: json.dump(db_data, f, indent=4)
        try: os.chmod(DB_FILE, stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)
        except: pass
        
        log_task(format_log("TETHER_LOCK", "Security Manifest injected directly into Master Vault.", C_TITLE), "RAW")
        
        manifest_path = os.path.join(HTML_DB_DIR, 'security_manifest.js')
        with open(manifest_path, 'w', encoding='utf-8') as f:
            f.write(f"const securityManifest = {json.dumps(manifest_data, indent=4)};\n")
            
        log_task(format_log("SECURITY", "SSG Payload cryptographically sealed.", C_STAGED), "RAW")
        
        # FIXED INTERACTIVE SCROLL LOOP
        draw_viewport(progress_pct=100.0, active_file="security_manifest.js", current_file_idx=total_mfgs, total_files=total_mfgs, is_interactive=True)
        
        while True:
            c = getch()
            if isinstance(c, bytes):
                try: c = c.decode('utf-8')
                except: continue
            if c in ('\r', '\n', '\x1b'): break
            
            vp_height = (term_h - 9) - 4 - 1
            max_scroll = max(0, len(viewport_logs) - vp_height)
            
            if c == '\x1b[A' or c == 'UP': scroll_offset = max(0, scroll_offset - 1)
            elif c == '\x1b[B' or c == 'DOWN': scroll_offset = min(max_scroll, scroll_offset + 1)
            elif c == '\x1b[5~' or c == 'PGUP': scroll_offset = max(0, scroll_offset - 10)
            elif c == '\x1b[6~' or c == 'PGDN': scroll_offset = min(max_scroll, scroll_offset + 10)
            
            draw_viewport(progress_pct=100.0, active_file="security_manifest.js", current_file_idx=total_mfgs, total_files=total_mfgs, is_interactive=True)

    except Exception as e:
        log_task(format_log("FATAL_I/O", f"{str(e)}", C_ALERT), "RAW")
        draw_viewport(progress_pct=100.0, active_file="ERROR", current_file_idx=total_mfgs, total_files=total_mfgs, is_interactive=True)
        getch()
        
    global_mode = "MAIN MENU"

# --- MATH & PARSER UTILITIES ---

VLP_SCHEMA = [
    'MFG', 'Class', 'Name', 'Description', 'Filter', 'Coating', 'Material', 'Style', 
    'Coating Brand', 'Right OPC', 'Left OPC', 'Index', 'Diameter', 'SPH/BASE', 'CYL/ADD', 'Front RAD', 
    'Back RAD', 'Center Thick', 'Edge Thick', 'Inset', 'Drop', 'PRP Out', 
    'PRP Up', 'Abbe', 'Seg Width', 'Seg Thick', 'Intermediate Ht', 'Slab Off', 
    'Carriage Rad', 'Bowl Dia', 'Ver Dia', 'Dia Dia', 'Seg Sep', 'Up Add', 
    'Special', 'Cat Code', 'Filter Brand', 'DRP In', 'DRP Up', 'NRP In', 
    'NRP Up', 'Horizontal Dia', 'Nominal Dia', 'Obj Clear', 'Obj Rad', 
    'Front TC', 'Back TC', 'SAG'
]

def map_style_code(style_val, desc_val):
    v = str(style_val).upper(); d = str(desc_val).upper()
    if 'PROG' in v or 'PR ' in v or v == 'PR': return 6
    if 'FTT' in v or 'TRI' in v or 'TF' in v: return 15
    if 'FT' in v or 'BIF' in v or 'BI FT' in v: return 2
    if 'EXEC' in v: return 9
    if 'SV' in v or 'SINGLE' in v or v == '': 
        if 'AS' in d or 'ASP' in d or 'ASPHERIC' in d or 'AS' in v or 'ASP' in v: return 14
        return 1
    return 0

def resolve_material(mat_code, idx, desc, brand, explicit_mr_map=None, global_context=None):
    mat = str(mat_code).upper().strip()
    desc_upper = str(desc).upper()
    brand_upper = str(brand).upper()
    
    if mat in ['TR', 'PNX'] or 'TRIVEX' in mat or 'TRIVEX' in desc_upper: return 'Trivex'
    if mat == 'PL': return 'Plastic (CR-39)'
    if mat == 'PY': return 'Polycarbonate'
    if mat == 'PM' or (pd.notna(idx) and 1.54 <= float(idx) <= 1.56): return 'Mid-Index (1.56)'
    
    if mat == 'PH':
        if pd.notna(idx) and 1.590 <= float(idx) <= 1.610:
            if any(x in desc_upper for x in ['ULTRAFLEX', 'ULTRA FLEX', 'ULTRA-FLEX']) or any(x in brand_upper for x in ['ULTRAFLEX', 'ULTRA FLEX', 'ULTRA-FLEX']): 
                return 'High-Index 1.60 (MR-8+)'
            return 'High-Index 1.60 (MR-8)'
        return 'High-Index 1.60'
        
    if mat == 'PU':
        if pd.notna(idx):
            idx_val = float(idx)
            if idx_val >= 1.73: return 'High-Index 1.74'
            if 1.660 <= idx_val <= 1.70:
                if 'MR-7' in desc_upper or 'MR7' in desc_upper: return 'High-Index 1.67 (MR-7)'
                if 'MR-10' in desc_upper or 'MR10' in desc_upper: return 'High-Index 1.67 (MR-10)'
                if global_context:
                    c7 = global_context.get('7', 0)
                    c10 = global_context.get('10', 0)
                    fb = global_context.get('fallback')
                    if c7 > 0 or c10 > 0:
                        return 'High-Index 1.67 (MR-7)' if c7 < c10 else 'High-Index 1.67 (MR-10)'
                    elif fb:
                        return f"High-Index 1.67 ({fb})"
                return 'High-Index 1.67 (MR-7)'
        return 'High-Index (Polyurethane)'
    return mat_code

def heal_vca_format(filepath):
    if not str(filepath).lower().endswith(('.vca', '.txt')): return filepath
    try:
        with open(filepath, 'r', encoding='utf-8-sig') as f: lines = f.readlines()
        if not lines: return filepath
        target_commas = lines[0].count(',')
        healed_lines = []; buffer = ""
        for line in lines:
            line_str = line.strip('\n\r')
            if buffer: buffer += " " + line_str
            else: buffer = line_str
            if buffer.count(',') >= target_commas: 
                healed_lines.append(buffer + '\n'); buffer = ""
        if len(healed_lines) == len(lines): return filepath
        tmp_path = os.path.join(TMP_DIR, "healed_" + os.path.basename(filepath))
        with open(tmp_path, 'w', encoding='utf-8-sig') as tf: tf.writelines(healed_lines)
        return tmp_path
    except: return filepath

def get_fuzzy_col(df, target_name, default_val=np.nan):
    clean_target = re.sub(r'[^a-zA-Z0-9]', '', target_name).lower()
    for real_col in df.columns:
        if clean_target == re.sub(r'[^a-zA-Z0-9]', '', str(real_col)).lower(): return df[real_col]
    return pd.Series(default_val, index=df.index)

def robust_read_csv(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    if ext in ['.xlsx', '.xls']:
        try: return pd.read_excel(filepath)
        except Exception as e: raise RuntimeError(f"Excel read error. Ensure 'openpyxl' is installed via pip. Details: {e}")

    target_path = heal_vca_format(filepath)
    encodings = ['utf-8-sig', 'utf-8', 'cp1252', 'latin1', 'iso-8859-1']
    
    for enc in encodings:
        try: return pd.read_csv(target_path, encoding=enc, skip_blank_lines=True, on_bad_lines='skip', low_memory=False)
        except UnicodeDecodeError: continue
        except Exception: pass
            
    if target_path != filepath:
        for enc in encodings:
            try: return pd.read_csv(filepath, encoding=enc, skip_blank_lines=True, on_bad_lines='skip', low_memory=False)
            except: continue
                
    raise RuntimeError(f"Unable to parse {os.path.basename(filepath)}. Unsupported format or encoding.")

def generate_hash_id(row_dict):
    raw_components = []
    for col in VLP_SCHEMA:
        val = str(row_dict.get(col, '')).strip().lower()
        if val in ('nan', 'none', 'null', '<na>'): val = ''
        if val.endswith('.0'): val = val[:-2]
        raw_components.append(val)
    raw_string = "_".join(raw_components)
    return hashlib.md5(raw_string.encode()).hexdigest()[:12]

def calculate_curves(df):
    NUM = 530.0; h = 25.0
    is_fin = df['Class'] == 'FIN'
    v_f = (~is_fin) & (df['Front RAD'] > 0)
    v_b = (~is_fin) & (df['Back RAD'] > 0)
    v_s = (~is_fin) & (df['Front RAD'] >= h)
    
    calc_ftc = np.where(df['SPH/BASE'] == 0, 0.00, np.where(v_f, NUM / df['Front RAD'], np.nan)).round(2)
    df['Front TC'] = np.where(pd.to_numeric(df['Front TC'], errors='coerce').notna() & (df['Front TC'] != 0), df['Front TC'], calc_ftc)
    
    calc_btc = np.where(v_b, -NUM / df['Back RAD'], np.nan).round(2)
    df['Back TC'] = np.where(pd.to_numeric(df['Back TC'], errors='coerce').notna() & (df['Back TC'] != 0), df['Back TC'], calc_btc)
    
    calc_sag = np.where(df['SPH/BASE'] == 0, 0.00, np.where(v_s, df['Front RAD'] - np.sqrt(df['Front RAD']**2 - h**2), np.nan)).round(2)
    df['SAG'] = np.where(pd.to_numeric(df['SAG'], errors='coerce').notna() & (df['SAG'] != 0), df['SAG'], calc_sag)
    
    return df

def parse_vlp_attributes(desc, raw_name, style_val, class_val, filt_val, coat_val, seg_val, int_val, mat, idx):
    d_str = str(desc).strip()
    f_str = str(filt_val).strip() if str(filt_val).lower() not in ['nan', 'none', ''] else ""
    
    d_str = re.sub(r'(?<!\d)(1\.[4-9])(?!\d)', r'\g<1>0', d_str)
    
    # 1. Protect BlueGuard & Blue Filter
    if re.search(r'(?i)\b(Blue\s*Guard|Blue-Guard)\b', d_str):
        d_str = re.sub(r'(?i)\b(Blue\s*Guard|Blue-Guard)\b', 'BlueGuard', d_str)
        if 'HEV' not in f_str.upper(): f_str = (f_str + " HEV").strip()
        
    if re.search(r'(?i)\b(Clear\s*Blue\s*Filter|Blue\s*Filter|Blue-Filter)\b', d_str):
        d_str = re.sub(r'(?i)\b(Clear\s*Blue\s*Filter|Blue\s*Filter|Blue-Filter)\b', 'Blue Filter', d_str)
        if 'HEV' not in f_str.upper(): f_str = (f_str + " HEV").strip()

    # 2. Extract standard filters
    filt_match = re.search(r'(?i)\b(UV420|UVRI|Blue\s*Blocker)\b', d_str)
    if filt_match:
        f_str = (f_str + " " + filt_match.group(1)).strip()

    # 3. Aggressive Noise Vacuum
    scrub_regex = r'(?i)\b(HA|HARD\s*RESIN|COATED|UNCOATED|PHOT\s*GRY|PHOT\s*BRN|PHOT|POLR|POL)\b'
    d_str = re.sub(scrub_regex, '', d_str)
    f_str = re.sub(scrub_regex, '', f_str)
    
    d_str = re.sub(r'(?i)\bQ-Change|Q Change\b', 'Quick-Change', d_str)
    d_str = re.sub(r'(?i)(?<!\.)(?<!MR-)(?<!MR)\b[D]?\d{2,3}(?:/\d{2,3})?(?:mm)?\b', '', d_str)
    
    # 4. Smart Coating Formatter
    coat = str(coat_val).strip() if str(coat_val).lower() not in ['nan', 'none', ''] else ""
    found_coats = re.findall(r'(?i)\b(SHMC|HMC|HC|AR|A/R|UNCOATED|SR)\b', d_str)
    if found_coats:
        unique_coats = list(dict.fromkeys([c.upper().replace('A/R', 'AR') for c in found_coats]))
        if 'UNCOATED' in unique_coats and len(unique_coats) > 1: unique_coats.remove('UNCOATED')
        coat_str = " / ".join(unique_coats)
        if not coat or coat.upper() == "UNCOATED": coat = coat_str
        
    if not coat: coat = "Uncoated"
    coat = re.sub(r'(?i)\bSR\s+AR\b', 'SR / AR', coat)
    
    d_str = re.sub(r'(?i)\b(SHMC|HMC|HC|AR|A/R|UNCOATED|SR)\b', '', d_str)
    f_str = re.sub(r'(?i)\b(SHMC|HMC|HC|AR|A/R|UNCOATED|SR)\b', '', f_str)
    
    # 5. Strict Lens Type Nomenclature (Now with Explicit DB Overrides)
    is_fin = str(class_val).strip().upper() == 'FIN'
    
    # Fallback regexes, negative lookbehind to avoid index numbers (e.g. 1.50 -> 50)
    tri_match = re.search(r'(?i)\b(\d{1,2}x\d{2})\b', str(desc))
    seg_match = re.search(r'(?i)(?<!\.)\b(?:FT|Flat\s*Top|Round|Blend|-)?\s*(\d{2})\b', str(desc))

    sw = str(seg_val).replace('.0', '').strip() if pd.notna(seg_val) and str(seg_val).lower() not in ['nan', 'none', ''] else None
    ih = str(int_val).replace('.0', '').strip() if pd.notna(int_val) and str(int_val).lower() not in ['nan', 'none', ''] else None

    d_str = re.sub(r'(?i)\b(BIFOCAL|TRIFOCAL|FLAT\s*TOP|TRI|FT|ROUND|BLEND|-)\b', '', d_str)
    d_str = re.sub(r'(?i)\b(\d{1,2}x\d{2})\b', '', d_str)
    d_str = re.sub(r'(?i)(?<!\.)\b(\d{2})\b', '', d_str)

    prefix = ""
    if style_val in [10, 11, 12, 15]:
        p_base = "FIN" if is_fin else "SF"
        if ih and sw: prefix = f"{p_base} TRIFOCAL {ih}x{sw}"
        elif tri_match: prefix = f"{p_base} TRIFOCAL {tri_match.group(1).lower()}"
        else: prefix = f"{p_base} TRIFOCAL"
    elif style_val in [2, 3, 4, 5, 8, 9, 16]:
        p_base = "FIN" if is_fin else "SF"
        if sw: prefix = f"{p_base} BIFOCAL FT{sw}"
        elif seg_match: prefix = f"{p_base} BIFOCAL FT{seg_match.group(1)}"
        else: prefix = f"{p_base} BIFOCAL"
    elif style_val == 6: prefix = "FIN PAL" if is_fin else "SF PAL"
    elif style_val in [1, 13, 14]: prefix = "FSV" if is_fin else "SFSV"
    else: prefix = "FSV" if is_fin else "SF"
    
    d_str = re.sub(r'(?i)\b(SV|FSV|SF|SFSV|PROG|PAL|SEMI-FINISHED|FINISHED|SFFT|FIN)\b', '', d_str)
    d_str = re.sub(r'\s{2,}', ' ', d_str).strip()
    f_str = re.sub(r'\s{2,}', ' ', f_str).strip()
    
    long_desc = f"{prefix} {d_str}".strip()

    # 6. SHORT DESCRIPTION GENERATOR
    ast = "*" if is_fin else ""
    
    if style_val in [10, 11, 12, 15]: s_type = f"TRI {ih}x{sw}" if (ih and sw) else (f"TRI {tri_match.group(1).lower()}" if tri_match else "TRI")
    elif style_val in [2, 3, 4, 5, 8, 9, 16]: s_type = f"FT{sw}" if sw else (f"FT{seg_match.group(1)}" if seg_match else "BIFOCAL")
    elif style_val == 6: s_type = "PAL"
    else: s_type = "FSV" if is_fin else "SFSV"

    s_brand = ""
    if style_val == 6:
        b_src = str(raw_name) if str(raw_name).strip() else str(desc)
        b_clean = re.sub(r'(?i)\b(PAL|PROG|PROGRESSIVE|POLY|CR-39|TRIVEX|POLARIZED|POL|PHOT|TRANS|TRANSITIONS|PHOTOFUSION|1\.\d{2})\b', '', b_src)
        b_clean = re.sub(r'(?i)\b(EXG3|XTR|Extra\s*Active|PGY3|Pro\s*Gr[ae]y|PBN3|Pro\s*Brown|PIO3|Pioneer|BRG[1-3]?|BURG|BURGUNDY|GRY[1-3]?|GRAY|GREY|BRN[1-3]?|BROWN|G-15|GRN[1-3]?|GREEN|BLU[1-3]?|BLUE|YEL[1-3]?|YLW|YELLOW|PNK[1-3]?|ROS[1-3]?|ROSE|PINK|PUR[1-3]?|PRP[1-3]?|PLUM|PURPLE)\b', '', b_clean)
        b_clean = re.sub(r'[^a-zA-Z0-9\s-]', '', b_clean).strip()
        s_brand = " ".join(b_clean.split()[:2]).upper()

    s_mat = ""
    if mat == 'Plastic (CR-39)': s_mat = "CR-39"
    elif mat == 'Polycarbonate': s_mat = "POLY"
    elif mat == 'Trivex': s_mat = "TRIVEX"
    elif pd.notna(idx): s_mat = f"{float(idx):.2f}"
    
    s_tags = []
    if 'POL' in str(desc).upper(): s_tags.append("POLR")
    if re.search(r'(?i)\b(PHOT|PhotoFusion|Transition|LifeRx|Quick-Change|Sensitivity)\b', str(desc) + " " + str(filt_val)): s_tags.append("PHOT")
    
    short_parts = [f"{ast}{s_type}"]
    if s_brand: short_parts.append(s_brand)
    if s_mat: short_parts.append(s_mat)
    short_parts.extend(s_tags)
    short_desc = " ".join(short_parts).replace("  ", " ").strip()
    
    return long_desc, short_desc, f_str, coat

# --- FILE MANAGER ---

def run_file_manager(op, start_dir=BASE_DIR, ext_filter=None):
    global global_mode, err_msg
    op_name = {'mv': 'MOVE', 'cp': 'COPY', 'rm': 'DELETE', 're': 'RENAME', 'convert': 'SELECT', 'add': 'MERGE'}.get(op, 'MOVE')
    global_mode = f"{op_name} (Selection)"
    ldir = start_dir; clip = []; lpage = 0; rpage = 0; phase = 1
    
    def handle_selection(idx, l_items):
        global err_msg
        if idx < 0 or idx >= len(l_items): return
        n, p, pth = l_items[idx]
        if n in ('../', '-- LOCKED --'): return
        if is_protected(pth):
            err_msg = f"PROTECTED: Access to '{n}' is denied."
            return
        if not any(c[2] == pth for c in clip):
            if op == 're': clip.clear() 
            clip.append((n, p, pth))

    def get_arrow(key, fallback):
        ico = get_ico(key, pad=False)
        return ico if ico else fallback

    while True:
        sys.stdout.write(f"{C_BG}\033[2J\033[H")
        term_w, term_h = get_term_size()
        
        # Calculate exactly how wide the inner panes are, accounting for the 3 vertical lines
        pane_l_w = (term_w - 3) // 2
        pane_r_w = term_w - 3 - pane_l_w
        center_col = pane_l_w + 2
        
        draw_top_bar()
        home = os.path.expanduser('~')
        if not home.endswith(os.sep): home += os.path.sep
        ldir_abs = os.path.abspath(ldir)
        if not ldir_abs.endswith(os.sep): ldir_abs += os.path.sep
        
        if ldir_abs.startswith(home):
            left_path = "~" + os.sep + os.path.relpath(ldir_abs, home)
            if not left_path.endswith(os.sep) and left_path != f"~{os.sep}": left_path += os.path.sep
            right_path = home
        else:
            left_path = ldir_abs
            right_path = ""
        
        # Row 2: Directory Info
        sys.stdout.write(f"\033[2;1H{C_BORDER}║ {C_DIR}Active Directory: \033[4m{left_path}{RESET}")
        if right_path: sys.stdout.write(f"\033[2;{term_w - ansi_len(right_path) - 1}H{C_TITLE}{right_path}{RESET}")
        sys.stdout.write(f"\033[2;{term_w}H{C_BORDER}║{RESET}")
        
        # Row 3: The Hybrid Attached Ceiling
        sys.stdout.write(f"\033[3;1H{C_BORDER}╟{'─'*pane_l_w}┬{'─'*pane_r_w}╢{RESET}")

        try: items = os.listdir(ldir)
        except: items = []
        if op == 'add' and ldir != IMPORT_DIR: ldir = IMPORT_DIR; items = os.listdir(ldir)
            
        dirs = sorted([(i, os.stat(os.path.join(ldir, i)).st_mode, os.path.join(ldir, i)) for i in items if os.path.isdir(os.path.join(ldir, i))])
        if ext_filter: files = sorted([(i, os.stat(os.path.join(ldir, i)).st_mode, os.path.join(ldir, i)) for i in items if not os.path.isdir(os.path.join(ldir, i)) and os.path.splitext(i)[1].lower() in ext_filter])
        else: files = sorted([(i, os.stat(os.path.join(ldir, i)).st_mode, os.path.join(ldir, i)) for i in items if not os.path.isdir(os.path.join(ldir, i))])
            
        if op == 'add': l_items = [("-- LOCKED --", 0, "")] + [(f[0], f[1], f[2]) for f in files]
        else: l_items = [("../", 0, os.path.dirname(ldir))] + [(f"{d[0]}/", d[1], d[2]) for d in dirs] + [(f[0], f[1], f[2]) for f in files]

        max_lpage = max(1, (len(l_items) + 15) // 16)
        max_rpage = max(1, (len(clip) + 7) // 8)

        a_up = get_arrow('arr_up', '^'); a_prv = get_arrow('arr_prv', '<')
        a_dn = get_arrow('arr_dn', 'v'); a_nxt = get_arrow('arr_nxt', '>')
        
        l_head_l = f"  {a_up}   SCROLL UP"; l_head_r = f"(Page {lpage+1} of {max_lpage})"
        r_head_l = f"  {a_prv}   PREV PAGE"; r_head_r = f"(Page {rpage+1} of {max_rpage})"
        
        # Row 4: Column Headers
        sys.stdout.write(f"\033[4;1H{C_BORDER}║{RESET} {C_PROMPT}{l_head_l}{RESET}")
        sys.stdout.write(f"\033[4;{center_col - ansi_len(l_head_r) - 1}H{C_SIZE}{l_head_r}{RESET}")
        sys.stdout.write(f"\033[4;{center_col}H{C_BORDER}│{RESET} {C_PROMPT}{r_head_l}{RESET}")
        sys.stdout.write(f"\033[4;{term_w - ansi_len(r_head_r) - 1}H{C_SIZE}{r_head_r}{RESET}\033[4;{term_w}H{C_BORDER}║{RESET}")

        for i in range(16):
            row_idx = 5 + i
            idx = lpage * 16 + i
            sys.stdout.write(f"\033[{row_idx};1H{C_BORDER}║{RESET} ")
            
            if idx < len(l_items):
                n, p_mode, pth = l_items[idx]
                is_sel = any(c[2] == pth for c in clip)
                n_prefix = f"{C_PROMPT}[{idx:02d}]{RESET}" if n != "-- LOCKED --" else f"{C_PROMPT}[00]{RESET}"
                
                if n == '../': ico = get_ico('dir_up')
                elif os.path.isdir(pth): ico = get_ico('dir')
                elif n == "-- LOCKED --": ico = ""
                else: ico = get_ext_ico(n)
                
                size_str = f"{C_TITLE}{'<DIR>':>6}{RESET}" if os.path.isdir(pth) or n=='../' or n=='-- LOCKED --' else f"{C_SIZE}{format_bytes(os.path.getsize(pth)):>6}{RESET}"
                perms_str = f"{C_DIR}d{C_STAGED}r{C_SIZE}w{C_ALERT}x{C_STAGED}r{C_SIZE}w{C_ALERT}x{C_STAGED}r{C_SIZE}w{C_ALERT}x{RESET}" if n in ('../', '-- LOCKED --') else (eza_perms(p_mode) if p_mode else "drwxrwxrwx")
                
                max_n_len = pane_l_w - 3 - 4 - ansi_len(ico) - 1 - 6 - 1 - 10
                n_disp = n if ansi_len(n) <= max_n_len else n[:max_n_len]

                if n == "-- LOCKED --": 
                    name_part = f"{n_prefix} {C_ALERT}{n_disp}{RESET}"
                    perms_part = perms_str
                elif is_sel: 
                    name_part = f"{n_prefix} {ico}{C_ALERT}{STRIKE}{n_disp}{UNSTRIKE}{RESET}"
                    perms_part = f"{STRIKE}{C_SUBTEXT}{re.sub(r'\\033\\[[0-9;]*m', '', perms_str)}{UNSTRIKE}{RESET}"
                else:
                    c_itm = C_DIR if os.path.isdir(pth) or n=='../' else C_FILE
                    name_part = f"{n_prefix} {ico}{c_itm}{n_disp}{RESET}"
                    perms_part = perms_str
                    
                spacing = max(1, pane_l_w - 2 - 4 - ansi_len(ico) - ansi_len(n_disp) - 1 - 6 - 1 - 10)
                sys.stdout.write(f"{name_part}{' '*spacing} {size_str} {perms_part}")

            sys.stdout.write(f"\033[{row_idx};{pane_l_w + 1}H {C_BORDER}│{RESET} ")
            
            r_idx = rpage * 8 + (i // 2)
            if r_idx < len(clip):
                cn, cp_mode, cpth = clip[r_idx]
                if i % 2 == 0:
                    c_prefix = f"{C_PROMPT}[{get_alpha_id(r_idx):>2}]{RESET}"
                    cico = get_ico('dir') if os.path.isdir(cpth) else get_ext_ico(cn)
                    csize_str = f"{C_TITLE}{'<DIR>':>6}{RESET}" if os.path.isdir(cpth) else f"{C_SIZE}{format_bytes(os.path.getsize(cpth)):>6}{RESET}"
                    cperms_str = eza_perms(cp_mode) if cp_mode else "drwxrwxrwx"
                    
                    max_cn_len = pane_r_w - 3 - 4 - ansi_len(cico) - 1 - 6 - 1 - 10
                    cn_disp = cn if ansi_len(cn) <= max_cn_len else cn[:max_cn_len]
                    
                    cname_part = f"{c_prefix} {cico}{C_STAGED}{cn_disp}{RESET}"
                    cspace = max(1, pane_r_w - 2 - 4 - ansi_len(cico) - ansi_len(cn_disp) - 1 - 6 - 1 - 10)
                    sys.stdout.write(f"{cname_part}{' '*cspace} {csize_str} {cperms_str}")
                else:
                    disp_cpth = os.path.dirname(cpth) + os.sep
                    sys.stdout.write(f"    {C_TITLE}\u2514\u2500\u2500 {disp_cpth[:pane_r_w - 10]}{RESET}")
            sys.stdout.write(f"\033[{row_idx};{term_w}H{C_BORDER}║{RESET}")

        l_foot_l = f"  {a_dn}   SCROLL DOWN"; r_foot_l = f"  {a_nxt}   NEXT PAGE"
        sys.stdout.write(f"\033[21;1H{C_BORDER}║{RESET} {C_PROMPT}{l_foot_l}{RESET}")
        sys.stdout.write(f"\033[21;{center_col - ansi_len(l_head_r) - 1}H{C_SIZE}{l_head_r}{RESET}")
        sys.stdout.write(f"\033[21;{center_col}H{C_BORDER}│{RESET} {C_PROMPT}{r_foot_l}{RESET}")
        sys.stdout.write(f"\033[21;{term_w - ansi_len(r_head_r) - 1}H{C_SIZE}{r_head_r}{RESET}\033[21;{term_w}H{C_BORDER}║{RESET}")
        
        # Row 22: The Hybrid Attached Floor
        sys.stdout.write(f"\033[22;1H{C_BORDER}╟{'─'*pane_l_w}┴{'─'*pane_r_w}╢{RESET}")
        
        for r in range(23, term_h - 1): draw_frame_line("", row=r)
        
        if phase == 1:
            draw_context_helpers(
                f"Input {C_PROMPT}NUMBER{C_SUBTEXT} of File to Select.    Input {C_PROMPT}/NUMBER{C_SUBTEXT} to Select Directories.",
                f"Press {C_PROMPT}ENTER{C_SUBTEXT} to Execute Once Populated. Press {C_PROMPT}ESC{C_SUBTEXT} to Abort.", offset=6
            )
        draw_status_bar()
        
        # Position the blinking cursor safely within the inner wall structure
        sys.stdout.write(f"\033[{term_h - 4};5H{C_BGLIGHT} {C_PROMPT}{get_ico('term', pad=False)}  {RESET}{C_BGLIGHT}{' '*40}{RESET}\033[{term_h - 4};9H{C_BGLIGHT}")
        sys.stdout.flush()

        if handle_error_hijack(): continue
        
        if phase == 1:
            cmd = live_input("", hotkeys=True)
            if cmd == "REFRESH": continue
            if cmd: cmd = cmd.lower()
            
            sys.stdout.write(f"{RESET}")
            if cmd == "abort": return None
            elif cmd == 'up': lpage = (lpage - 1 + max_lpage) % max_lpage
            elif cmd == 'down': lpage = (lpage + 1) % max_lpage
            elif cmd == 'pgup': lpage = max(0, lpage - 5)
            elif cmd == 'pgdn': lpage = min(max_lpage - 1, lpage + 5)
            elif cmd == 'left': rpage = (rpage - 1 + max_rpage) % max_rpage
            elif cmd == 'right': rpage = (rpage + 1) % max_rpage
            elif (cmd == 'select' or cmd == '') and clip: phase = 2
            elif cmd.startswith('/') and cmd[1:].isdigit():
                idx = int(cmd[1:])
                if 0 <= idx < len(l_items):
                    if not os.path.isdir(l_items[idx][2]): err_msg = f"'{l_items[idx][0]}' is not a directory. Only use / when selecting whole directories."
                    else: handle_selection(idx, l_items)
            elif cmd.isdigit() and 0 <= int(cmd) < len(l_items):
                idx = int(cmd)
                n, p, pth = l_items[idx]
                if os.path.isdir(pth): ldir = pth; lpage = 0
                else: handle_selection(idx, l_items)
            elif cmd.isalpha():
                val = 0
                for char in cmd.upper(): val = val * 26 + (ord(char) - 64)
                idx = val - 1
                if 0 <= idx < len(clip): clip.pop(idx)
        else:
            if op in ('convert', 'add'): return [c[2] for c in clip]
            elif op == 'rm':
                prompt = f"Delete {len(dirs_to_del)} dir(s) and {sub_f} files? Type YES:" if dirs_to_del else f"Delete {len(files_to_del)} files? Type YES:"
                ans = draw_modal("DESTRUCTIVE ACTION", prompt, is_password=False)
                if ans == "YES":
                    for _, _, pth in clip:
                        try: 
                            if os.path.isdir(pth): shutil.rmtree(pth)
                            else: os.chmod(pth, stat.S_IWRITE | stat.S_IREAD); os.remove(pth)
                        except Exception as e: err_msg = f"DELETE Error: {e}"
                else: err_msg = "Deletion aborted."
                return None
            elif op == 'mv':
                dest = draw_modal("MOVE FILES", "Type Destination Directory:", is_password=False)
                if not dest: return None # Escaped out
                for _, _, pth in clip:
                    try: shutil.move(pth, dest)
                    except Exception as e: err_msg = f"MOVE Error: {e}"
                return None
            elif op == 'cp':
                dest = draw_modal("COPY FILES", "Type Destination Directory:", is_password=False)
                if not dest: return None
                for _, _, pth in clip:
                    try: 
                        if os.path.isdir(pth): shutil.copytree(pth, os.path.join(dest, os.path.basename(pth)))
                        else: shutil.copy2(pth, dest)
                    except Exception as e: err_msg = f"COPY Error: {e}"
                return None
            elif op == 're':
                old_name, _, pth = clip[0]
                new_name = draw_modal("RENAME FILE", f"New name for '{old_name}':", is_password=False)
                if not new_name: return None
                try: os.rename(pth, os.path.join(os.path.dirname(pth), new_name))
                except Exception as e: err_msg = f"RENAME Error: {e}"
                return None

# --- CORE ETL OPERATIONS ---

def execute_batch_convert():
    global global_mode, scroll_offset
    import shutil
    import stat
    import pandas as pd
    
    # 1. FILE SELECTION
    tgt_list = run_file_manager('convert', start_dir=BASE_DIR, ext_filter=['.vca', '.csv', '.xlsx', '.xls', '.txt'])
    if not tgt_list: return
    
    # 2. STANDARDIZED SKELETON SETUP
    sys.stdout.write(f"{C_BG}\033[2J\033[H")
    term_w, term_h = get_term_size()
    draw_top_bar()
    for r in range(2, term_h - 1): draw_frame_line("", row=r)
    draw_frame_line(f"{C_SIZE}VCA REFINERY: DATA SANITIZATION & MATH{RESET}", row=2, align="center")
    
    draw_universal_footer() # THE FLOOR SEAL
    
    # 3. INITIALIZE VIEWPORT
    viewport_logs.clear()
    scroll_offset = 0
    total_files = len(tgt_list)
    
    # Define the absolute VCA Schema for Headerless injections
    STANDARD_VCA_HEADERS = [
        "MFG", "Class", "Description", "Material", "Material Brand", "Product Name", 
        "Style", "Filter", "Coating", "Coating Brand", "Right OPC", "Left OPC", 
        "Diameter", "Sph / Base", "Cyl / Add", "Frnt Rad", "Bck Rad", "C Thk", 
        "E Thk", "LRP In", "LRP Down", "d Index", "N Ref", "e Index", "Abbe", 
        "Density", "PRP Out", "PRP Up", "Seg Wd", "Seg Thk", "Int Ht", "Slab", 
        "Car Rad", "Bwl Diam", "Ver Diam", "Dia Diam", "Seg Sep", "Up Add", 
        "Special", "Cat Code", "Filter Brand", "DRP In", "DRP Up", "NRP In", 
        "NRP Up", "Hor Diam", "Nom Diam", "Obj Clear", "Obj Rad"
    ]
    
    draw_viewport(progress_pct=0.0, active_file="Initializing Refinery...", current_file_idx=0, total_files=total_files, is_interactive=False)
    
    # 4. CONVERSION LOOP
    for idx, tgt in enumerate(tgt_list):
        fname = os.path.basename(tgt)
        base_name = os.path.splitext(fname)[0]
        log_task(format_log("I/O", f"Processing {fname}...", C_FILE), "RAW")
        
        try:
            # --- HEADERLESS AUTO-HEAL SNIFFER ---
            has_header = True
            if tgt.lower().endswith(('.csv', '.txt', '.vca')):
                with open(tgt, 'r', encoding='utf-8', errors='ignore') as f:
                    first_line = f.readline().upper()
                    # If it doesn't have standard VCA header terminology, it's naked.
                    if "MFG" not in first_line and "DESCRIPTION" not in first_line:
                        has_header = False
                        
            if not has_header:
                log_task(format_log("AUTO-HEAL", f"Headerless file detected. Injecting VCA Schema.", C_WARN), "RAW")
                df = pd.read_csv(tgt, header=None, names=STANDARD_VCA_HEADERS, dtype=str)
            else:
                # If Excel or standard CSV, read normally
                if tgt.lower().endswith(('.xlsx', '.xls')): df = pd.read_excel(tgt, dtype=str)
                else: df = pd.read_csv(tgt, dtype=str)
            
            # Drop purely empty rows
            df = df.dropna(how='all')
            
            # --- INVERSE DEDUCTION LOGIC (MR-7 vs MR-10) ---
            # Search the file for 1.67 material clues
            mat_col = 'Material' if 'Material' in df.columns else 'Description'
            
            # Count explicit occurrences
            mr7_count = df[mat_col].str.contains('MR-7|MR7', case=False, na=False).sum()
            mr10_count = df[mat_col].str.contains('MR-10|MR10', case=False, na=False).sum()
            
            # Identify ambiguous 1.67s (e.g. marked as PU or just 1.67)
            ambiguous_mask = df[mat_col].str.contains('PU|1.67', case=False, na=False) & \
                             ~df[mat_col].str.contains('MR-7|MR7|MR-10|MR10', case=False, na=False)
                             
            if ambiguous_mask.sum() > 0:
                deduced_material = ""
                
                # Inverse Deduction
                if mr7_count > mr10_count: 
                    deduced_material = "MR-10"
                    log_task(format_log("INFERENCE", f"MR-7 scored {mr7_count}. Ambiguous materials assigned to MR-10.", C_PROMPT), "RAW")
                elif mr10_count > mr7_count:
                    deduced_material = "MR-7"
                    log_task(format_log("INFERENCE", f"MR-10 scored {mr10_count}. Ambiguous materials assigned to MR-7.", C_PROMPT), "RAW")
                else:
                    # Dead Tie or 0/0. Human Fallback Required.
                    log_task(format_log("AMBIGUITY", f"1.67 Scoring tied. Requesting Human Fallback.", C_ALERT), "RAW")
                    ans = draw_modal("AMBIGUITY DETECTED", f"File '{fname}' has unknown 1.67 materials. Type MR7 or MR10:", is_password=False)
                    
                    # RE-DRAW SKELETON AFTER MODAL
                    sys.stdout.write(f"{C_BG}\033[2J\033[H")
                    draw_top_bar()
                    for r in range(2, term_h - 1): draw_frame_line("", row=r)
                    draw_frame_line(f"{C_SIZE}VCA REFINERY: DATA SANITIZATION & MATH{RESET}", row=2, align="center")
                    draw_universal_footer() # Seal it again
                    
                    deduced_material = "MR-7" if "7" in ans else "MR-10"
                    log_task(format_log("HUMAN_INPUT", f"Forced ambiguity resolution to {deduced_material}", C_STAGED), "RAW")
                
                # Apply the deduced material to the ambiguous rows
                df.loc[ambiguous_mask, mat_col] = df.loc[ambiguous_mask, mat_col] + f" ({deduced_material})"

            # --- OPTICAL MATH & SAG CALCULATION PLACEHOLDER ---
            # (Insert your specific True Curve and SAG calculation logic here)
            # log_task(format_log("CALCULATING", f"Processing Base True Curves...", C_TITLE), "RAW")
            # df['True Front Curve (1.53)'] = ...
            # df['True Back Curve (1.53)'] = ...
            # df['SAG at 50mm'] = ...

            # 5. DISPLACEMENT & OUTPUT
            # Write the clean .vlp file to the Staging/Import Directory
            vlp_filename = f"{base_name}.vlp"
            import_path = os.path.join(IMPORT_DIR, vlp_filename)
            
            df.to_csv(import_path, index=False)
            
            # Lock the .vlp file to Read-Only so users don't accidentally edit the clean file
            try: os.chmod(import_path, stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)
            except: pass
            
            # Move the dirty original to the Originals vault
            try:
                dest_orig = os.path.join(ORIGINALS_DIR, fname)
                if os.path.exists(dest_orig):
                    os.remove(dest_orig) # Replace if re-running
                shutil.move(tgt, dest_orig)
                log_task(format_log("DISPLACED", f"Original routed to /originals/", C_STAGED), "RAW")
            except Exception as e:
                log_task(format_log("WARNING", f"Could not move original: {str(e)}", C_WARN), "RAW")
                
            log_task(format_log("SUCCESS", f"Purified -> {vlp_filename}", C_STAGED), "RAW")
            
        except Exception as e:
            log_task(format_log("FATAL_I/O", f"Failed to convert {fname}: {str(e)}", C_ALERT), "RAW")
            
        pct = ((idx + 1) / total_files) * 100.0
        draw_viewport(progress_pct=pct, active_file=fname, current_file_idx=idx+1, total_files=total_files)
        time.sleep(0.1) # Smooth telemetry pacing
        
    # 6. FIXED INTERACTIVE SCROLL LOOP
    draw_viewport(progress_pct=100.0, active_file="Batch Complete", current_file_idx=total_files, total_files=total_files, is_interactive=True)
    
    while True:
        c = getch()
        if isinstance(c, bytes):
            try: c = c.decode('utf-8')
            except: continue
        if c in ('\r', '\n', '\x1b'): break
        
        vp_height = (term_h - 9) - 4 - 1
        max_scroll = max(0, len(viewport_logs) - vp_height)
        
        if c == '\x1b[A' or c == 'UP': scroll_offset = max(0, scroll_offset - 1)
        elif c == '\x1b[B' or c == 'DOWN': scroll_offset = min(max_scroll, scroll_offset + 1)
        elif c == '\x1b[5~' or c == 'PGUP': scroll_offset = max(0, scroll_offset - 10)
        elif c == '\x1b[6~' or c == 'PGDN': scroll_offset = min(max_scroll, scroll_offset + 10)
        
        draw_viewport(progress_pct=100.0, active_file="Batch Complete", current_file_idx=total_files, total_files=total_files, is_interactive=True)

    global_mode = "MAIN MENU"
    
def execute_add_database():
    global global_mode, scroll_offset
    if not enforce_security_lock(): return
    global_mode = "VAULT GATEKEEPER (Add)"
    
    tgt_list = run_file_manager('add', start_dir=IMPORT_DIR, ext_filter=['.vlp'])
    if not tgt_list: global_mode = "MAIN MENU"; return
    
    # 1. STANDARDIZED SKELETON SETUP
    sys.stdout.write(f"{C_BG}\033[2J\033[H")
    term_w, term_h = get_term_size()
    draw_top_bar()
    for r in range(2, term_h - 1): draw_frame_line("", row=r)
    draw_frame_line(f"{C_SIZE}VAULT GATEKEEPER: ATOMIC BATCH VERIFICATION{RESET}", row=2, align="center")
    
    draw_universal_footer() # THE FLOOR SEAL
    
    vault_hashes = set()
    vault_files = [f for f in os.listdir(VLP_ARCHIVE) if f.lower().endswith('.vlp')]
    for vf in vault_files:
        try:
            df = robust_read_csv(os.path.join(VLP_ARCHIVE, vf)).dropna(how='all')
            for _, row_data in df.iterrows(): vault_hashes.add(generate_hash_id(row_data.to_dict()))
        except: pass
            
    batch_hashes = {} 
    cleaned_dfs = {}
    failed_file = None; fail_reason = ""
    
    # 2. INITIALIZE VIEWPORT
    viewport_logs.clear()
    scroll_offset = 0
    total_files = len(tgt_list)
    
    log_task(format_log("SYSTEM", "Cross-referencing batch against Vault records..."), "RAW")
    draw_viewport(progress_pct=0.0, active_file="Verifying...", current_file_idx=0, total_files=total_files, is_interactive=False)
    
    # 3. VERIFICATION LOOP
    for idx, tgt in enumerate(tgt_list):
        fname = os.path.basename(tgt)
        if fname in vault_files: 
            failed_file = tgt; fail_reason = "Filename collision."; break
            
        log_task(format_log("I/O", f"Reading absolute path -> {tgt}", C_FILE), "RAW")
        
        try:
            # Drop purely empty rows and exact Intra-file duplicates silently
            df = robust_read_csv(tgt).dropna(how='all').drop_duplicates()
            
            for row_idx, row_data in df.iterrows():
                row_dict = row_data.to_dict()
                h_id = generate_hash_id(row_dict)
                
                if h_id in vault_hashes:
                    failed_file = tgt
                    failed_lens = row_dict.get('Description', row_dict.get('Name', 'Unknown Lens'))
                    fail_reason = f"Master Vault collision on Row {row_idx + 2}. Lens: {failed_lens}"
                    break
                    
                if h_id in batch_hashes: 
                    failed_file = tgt
                    failed_lens = row_dict.get('Description', row_dict.get('Name', 'Unknown Lens'))
                    original_location = batch_hashes[h_id]
                    fail_reason = f"Cross-file duplicate! Row {row_idx + 2} matches data already seen in {original_location}. Lens: {failed_lens}"
                    break
                    
                batch_hashes[h_id] = f"'{fname}' (Row {row_idx + 2})"
                
            if failed_file: break
            cleaned_dfs[tgt] = df
            
        except Exception as e: 
            failed_file = tgt; fail_reason = f"Read error: {str(e)}"; break
            
    # 4. REJECTION PROTOCOL
    if failed_file:
        fname = os.path.basename(failed_file); base_name = os.path.splitext(fname)[0]
        try: os.chmod(failed_file, stat.S_IWRITE | stat.S_IREAD); os.remove(failed_file)
        except: pass
            
        if os.path.exists(ORIGINALS_DIR):
            for orig in os.listdir(ORIGINALS_DIR):
                if orig.startswith(base_name) and not orig.startswith("(BAD-COPY)_"):
                    try: 
                        new_path = os.path.join(ORIGINALS_DIR, f"(BAD-COPY)_{orig}")
                        os.chmod(os.path.join(ORIGINALS_DIR, orig), stat.S_IWRITE | stat.S_IREAD)
                        shutil.move(os.path.join(ORIGINALS_DIR, orig), new_path)
                    except: pass
                    break

        log_task(format_log("FATAL", f"Validation Failure in '{fname}'", C_ALERT), "RAW")
        log_task(format_log("REASON", fail_reason, C_ALERT), "RAW")
        log_task(format_log("ACTION", "Offending .vlp file deleted from Staging.", C_WARN), "RAW")
        
        draw_viewport(progress_pct=100.0, active_file="HALTED", current_file_idx=total_files, total_files=total_files, is_interactive=True)
    
    # 5. ACCEPTANCE PROTOCOL
    else:
        moved = 0
        for idx, tgt in enumerate(tgt_list):
            try:
                dest = os.path.join(VLP_ARCHIVE, os.path.basename(tgt))
                cleaned_dfs[tgt].to_csv(dest, index=False)
                try: os.remove(tgt)
                except: pass
                os.chmod(dest, stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)
                log_task(format_log("SECURITY", f"{os.path.basename(tgt)} scrubbed and locked to 0444", C_STAGED), "RAW")
                moved += 1
            except: pass
            
            pct = ((idx + 1) / total_files) * 100.0
            draw_viewport(progress_pct=pct, active_file=os.path.basename(tgt), current_file_idx=idx+1, total_files=total_files)
            time.sleep(0.05)
            
        log_task(format_log("SYSTEM", f"BATCH ACCEPTED: {moved} files securely written to Vault.", C_STAGED), "RAW")
        draw_viewport(progress_pct=100.0, active_file="Complete", current_file_idx=total_files, total_files=total_files, is_interactive=True)
        
    # 6. FIXED INTERACTIVE SCROLL LOOP
    while True:
        c = getch()
        if isinstance(c, bytes):
            try: c = c.decode('utf-8')
            except: continue
        if c in ('\r', '\n', '\x1b'): break
        
        vp_height = (term_h - 9) - 4 - 1
        max_scroll = max(0, len(viewport_logs) - vp_height)
        
        if c == '\x1b[A' or c == 'UP': scroll_offset = max(0, scroll_offset - 1)
        elif c == '\x1b[B' or c == 'DOWN': scroll_offset = min(max_scroll, scroll_offset + 1)
        elif c == '\x1b[5~' or c == 'PGUP': scroll_offset = max(0, scroll_offset - 10)
        elif c == '\x1b[6~' or c == 'PGDN': scroll_offset = min(max_scroll, scroll_offset + 10)
        
        draw_viewport(progress_pct=100.0, active_file="Complete" if not failed_file else "HALTED", current_file_idx=total_files, total_files=total_files, is_interactive=True)
        
    global_mode = "MAIN MENU"

def execute_list_database():
    global global_mode
    global_mode = "VAULT INVENTORY"
    render_ui_skeleton("Loading Vault Inventory...")
    while True:
        sys.stdout.write(f"{C_BG}\033[2J\033[H")
        term_w, term_h = get_term_size()
        draw_top_bar()
        for r in range(2, term_h - 1): draw_frame_line("", row=r)
    
        draw_frame_line(f"{C_SIZE}VAULT INVENTORY: ARCHIVED .VLP FILES{RESET}", row=2, align="center")
        draw_frame_line(f"{C_TITLE}{get_pfx('info')}INITIALIZING INVENTORY...{RESET}", row=5, indent=2)
        draw_universal_footer_ui("Processing... Please wait.")
        
        try: files = sorted([f for f in os.listdir(VLP_ARCHIVE) if f.lower().endswith('.vlp')])
        except: files = []
        
        draw_frame_line(" "*50, row=5, indent=2)
  
        r = 5
        if not files: draw_frame_line(f"{C_ALERT}{get_pfx('warn')}The Vault is currently empty.{RESET}", row=r, indent=2)
        else:
            for fname in files:
                if r > term_h - 6:
                    draw_frame_line(f"{C_TITLE}...and {len(files) - (r-5)} more files.{RESET}", row=r, indent=2); break
                size = format_bytes(os.path.getsize(os.path.join(VLP_ARCHIVE, fname)))
                draw_frame_line(f"{get_ext_ico(fname)}{C_STAGED}{fname[:40]:<45} {C_SIZE}{size:>6}{RESET}", row=r, indent=4)
                r += 1
                
        draw_universal_footer()
        break
    global_mode = "MAIN MENU"

def execute_scan_database():
    global global_mode
    if not enforce_security_lock(): return
    global_mode = "VAULT DIAGNOSTICS"
    render_ui_skeleton("Initializing Diagnostics...")
    while True:
        sys.stdout.write(f"{C_BG}\033[2J\033[H")
        term_w, term_h = get_term_size()
        draw_top_bar()
        for r in range(2, term_h - 1): draw_frame_line("", row=r)
        
        draw_frame_line(f"{C_SIZE}VAULT DIAGNOSTICS: INTEGRITY SCAN{RESET}", row=2, align="center")
        draw_universal_footer_ui("Processing... Please wait.")
        
        try: files = [f for f in os.listdir(VLP_ARCHIVE) if f.lower().endswith('.vlp')]
        except: files = []
        
        viewport_logs.clear()
        total_files = len(files)
        issues = 0
        
        for idx, fname in enumerate(files):
            try:
                df = robust_read_csv(os.path.join(VLP_ARCHIVE, fname))
                if df.empty or get_fuzzy_col(df, 'MFG', default_val=None) is None: raise ValueError("Invalid schema")
                log_task(f"{fname} Scanned -> Clean", "OK")
            except Exception as e:
                log_task(f"Corruption Detected: {fname} -> {e}", "ERR")
                issues += 1
                
            pct = ((idx + 1) / total_files) * 100.0 if total_files > 0 else 100.0
            draw_viewport(progress_pct=pct, active_file=fname, current_file_idx=idx+1, total_files=total_files)
                
        if issues == 0: log_task("Vault Integrity Confirmed. No structural errors found.", "OK")
        else: log_task(f"Scan complete. Found {issues} corrupted files. Recommend Manual Purge.", "WARN")
            
        draw_viewport(progress_pct=100.0, active_file="Scan Complete", current_file_idx=total_files, total_files=total_files)
        draw_universal_footer()
        break
    global_mode = "MAIN MENU"

def execute_generate_database():
    global global_mode, scroll_offset
    global_mode = "MASTER COMPILER (Generate)"
    render_ui_skeleton("Master Compiler Initializing...")
    while True:
        sys.stdout.write(f"{C_BG}\033[2J\033[H")
        term_w, term_h = get_term_size()
        draw_top_bar()
        for r in range(2, term_h - 1): draw_frame_line("", row=r)
        draw_frame_line(f"{C_SIZE}THE MASTER COMPILER: CRUCIBLE AUDIT & REBUILD{RESET}", row=2, align="center")
     
        try: files = [f for f in os.listdir(VLP_ARCHIVE) if f.lower().endswith('.vlp')]
        except: files = []

        if not files:
            draw_frame_line(f"{C_ALERT}{get_pfx('err')}Cannot Compile: The Vault (/data/db/.vlp/) is empty.{RESET}", row=5, indent=2)
            draw_universal_footer()
            global_mode = "MAIN MENU"; return

        # 1. Cinematic Start: Draw empty viewport behind the modal
        viewport_logs.clear()
        scroll_offset = 0
        log_task(format_log("SYSTEM", "Awaiting execution authorization...", C_TITLE), "RAW")
        draw_viewport(progress_pct=0.0, active_file="Pending Auth...", current_file_idx=0, total_files=len(files), total_types=0, total_lenses=0, is_interactive=False)

        # 2. Float the Modal
        ans = draw_modal("CRITICAL SYSTEM WARNING", "Type COMPILE to annihilate DB & rebuild:", is_password=False)
        if ans != "COMPILE": global_mode = "MAIN MENU"; return
        
        if os.path.exists(DB_FILE):
            try: os.chmod(DB_FILE, stat.S_IWRITE | stat.S_IREAD)
            except: pass
        
        master_db = {"files": {}, "lenses": {}, "shards": {}}; vault_hashes = set()
        viewport_logs.clear()
        total_files = len(files)
        total_skus = 0
        total_types = 0
        
        for idx, fname in enumerate(files):
            fpath = os.path.join(VLP_ARCHIVE, fname)
            file_valid = True
            local_lenses = {}
            
            log_task(format_log("VAULT_FILE", f"{fpath}", C_FILE), "RAW")
            
            try:
                df = robust_read_csv(fpath)
                
                # --- UNIVERSAL BUCKET PROFILER ---
                for (name, mat, index), group in df.groupby(['Name', 'Material', 'Index']):
                    extras = str(group['Coating'].iloc[0]) if 'Coating' in group.columns else ""
                    c_type = str(group['Class'].iloc[0])
                    
                    # Generate Bucket ID
                    b_id_str = f"{name}{mat}{index}{c_type}"
                    b_id = hashlib.md5(b_id_str.encode()).hexdigest()[:12]
                    
                    log_task(format_log("MERGE_NODE", f"{name} ({mat}, {index}) {extras}", C_STAGED), "RAW")
                    log_task(format_log("NODE_ID", f"{b_id} -> Minted {len(group)} SKUs", C_PROMPT), "RAW")
                    
                    # Call the telemetry math
                    telemetry = get_bucket_telemetry(group, c_type)
                    for t in telemetry: log_task(t, "RAW")
                        
                    total_types += 1
                    
                    pct = ((idx + 1) / total_files) * 100.0
                    draw_viewport(progress_pct=pct, active_file=fname, current_file_idx=idx+1, total_files=total_files, total_types=total_types, total_lenses=total_skus)
                    time.sleep(0.04)

                for _, row_data in df.iterrows():
                    h_id = generate_hash_id(row_data.to_dict())
                    if h_id in vault_hashes or h_id in local_lenses: 
                        file_valid = False; break
                    local_lenses[h_id] = row_data.to_dict()
                    total_skus += 1
                    
            except Exception as e: 
                file_valid = False
                log_task(format_log("PARSER_ERR", f"{e}", C_ALERT), "RAW")
                
            if file_valid:
                for hid, ldata in local_lenses.items(): 
                    master_db['lenses'][hid] = ldata
                    vault_hashes.add(hid)
                master_db['files'][fname] = len(local_lenses)
            else:
                try:
                    os.chmod(fpath, stat.S_IWRITE | stat.S_IREAD)
                    shutil.move(fpath, os.path.join(CORRUPT_DIR, fname))
                    log_task(format_log("SECURITY", f"{fname} BANISHED -> Hash Collision", C_ALERT), "RAW")
                except: pass
                
        log_task(format_log("SYSTEM", "Writing JSON Payload..."), "RAW")
        
        try:
            with open(DB_FILE, 'w', encoding='utf-8') as f: 
                json.dump(master_db, f, indent=4, sort_keys=True, ensure_ascii=False)
            
            # File Size Telemetry
            f_size = os.path.getsize(DB_FILE)
            log_task(format_log("PAYLOAD_SIZE", f"{f_size / (1024*1024):.2f} MB ({f_size:,} bytes)", C_PROMPT), "RAW")
            
            os.chmod(DB_FILE, stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)
            sign_master_database()
            
            # Signature Telemetry
            with open(SIG_FILE, 'r') as sf: sig = sf.read().strip()
            log_task(format_log("DB_PUB_ID", f"{sig}", C_WARN), "RAW")
            log_task(format_log("SEAL_LOG", f"Signature appended to master_lens_db.sig", C_STAGED), "RAW")
            
            draw_viewport(progress_pct=100.0, active_file="master_lens_db.json", current_file_idx=total_files, total_files=total_files, total_types=total_types, total_lenses=total_skus, is_interactive=True)
            
            while True:
                c = getch()
                if isinstance(c, bytes):
                    try: c = c.decode('utf-8')
                    except: continue
                if c in ('\r', '\n', '\x1b'): break 
                elif c == '\x1b[A' or c == 'UP': scroll_offset = min(len(viewport_logs) - ((term_h - 6) - 4), scroll_offset + 1)
                elif c == '\x1b[B' or c == 'DOWN': scroll_offset = max(0, scroll_offset - 1)
                elif c == '\x1b[5~' or c == 'PGUP': scroll_offset = min(len(viewport_logs) - ((term_h - 6) - 4), scroll_offset + 10)
                elif c == '\x1b[6~' or c == 'PGDN': scroll_offset = max(0, scroll_offset - 10)
                
                draw_viewport(progress_pct=100.0, active_file="master_lens_db.json", current_file_idx=total_files, total_files=total_files, total_types=total_types, total_lenses=total_skus, is_interactive=True)
     
        except Exception as e: 
            log_task(format_log("FATAL", f"{e}", C_ALERT), "RAW")
            draw_viewport(progress_pct=100.0, active_file="ERROR", current_file_idx=total_files, total_files=total_files, is_interactive=True)
            getch()
        
        break
    global_mode = "MAIN MENU"

def verify_and_stage_fonts():
    global global_mode, scroll_offset
    # Bring the Tier 2 heavy lifters into global scope
    global pd, urllib, zipfile
    
    # 1. STANDARDIZED SKELETON SETUP
    sys.stdout.write(f"{C_BG}\033[2J\033[H")
    term_w, term_h = get_term_size()
    draw_top_bar()
    for r in range(2, term_h - 1): draw_frame_line("", row=r)
    draw_frame_line(f"{C_SIZE}PHASE 0: SYSTEM INITIALIZATION & ASSET VERIFICATION{RESET}", row=2, align="center")
    
    draw_status_bar() # Draw the bottom mode bar
    sys.stdout.flush()
    
    viewport_logs.clear()
    scroll_offset = 0

    # 2. THE SMOKE & MIRRORS MATRIX
    modules = [
        ("Core OS Interface", "os", False), ("System Pathways", "sys", False),
        ("Temporal Engine", "time", False), ("Platform Diagnostics", "platform", False),
        ("Warning Handlers", "warnings", False), ("Exit Routines", "atexit", False),
        ("Regex Engine", "re", False), ("File Operations", "shutil", False),
        ("JSON Parsers", "json", False), ("Sys Stat", "stat", False),
        ("Text Wrapping", "textwrap", False), ("Datetime Engine", "datetime", False),
        ("Timezone Protocols", "timezone", False), ("Cryptographic Hashes", "hashlib", False),
        ("Binary Encoders", "base64", False), ("Network Libraries", "urllib", True), 
        ("Archive Tools", "zipfile", True), ("Pandas DataFrames", "pandas", True)
    ]
    
    fonts = {
        'Arial-Regular.ttf': {'win': r"C:\Windows\Fonts\arial.ttf", 'lin_name': 'arial.ttf', 'url': "https://cdn.jsdelivr.net/gh/matomo-org/travis-scripts@master/fonts/arial.ttf", 'is_zip': False},
        'Arial-Bold.ttf': {'win': r"C:\Windows\Fonts\arialbd.ttf", 'lin_name': 'arialbd.ttf', 'url': "https://cdn.jsdelivr.net/gh/matomo-org/travis-scripts@master/fonts/arialbd.ttf", 'is_zip': False},
        'Tahoma-Regular.ttf': {'win': r"C:\Windows\Fonts\tahoma.ttf", 'lin_name': 'tahoma.ttf', 'url': "https://cdn.jsdelivr.net/gh/matomo-org/travis-scripts@master/fonts/tahoma.ttf", 'is_zip': False},
        'MSSansSerif-Regular.ttf': {'win': r"C:\Windows\Fonts\micross.ttf", 'lin_name': 'micross.ttf', 'url': "https://cdn.jsdelivr.net/gh/matomo-org/travis-scripts@master/fonts/micross.ttf", 'is_zip': False},
        'UbuntuSansNerdFont-Regular.ttf': {'win': "", 'lin_name': "", 'url': "https://github.com/ryanoasis/nerd-fonts/releases/latest/download/UbuntuSans.zip", 'is_zip': True},
        'JetBrainsMonoNerdFont-Regular.ttf': {'win': "", 'lin_name': "", 'url': "https://github.com/ryanoasis/nerd-fonts/releases/latest/download/JetBrainsMono.zip", 'is_zip': True},
        'FiraCodeNerdFont-Medium.ttf': {'win': "", 'lin_name': "", 'url': "https://github.com/ryanoasis/nerd-fonts/releases/latest/download/FiraCode.zip", 'is_zip': True},
        'CaskaydiaCoveNerdFont-Regular.ttf': {'win': "", 'lin_name': "", 'url': "https://github.com/ryanoasis/nerd-fonts/releases/latest/download/CascadiaCode.zip", 'is_zip': True},
        'NotoSansNerdFont-Regular.ttf': {'win': "", 'lin_name': "", 'url': "https://github.com/ryanoasis/nerd-fonts/releases/latest/download/Noto.zip", 'is_zip': True},
        'OpenSans-Regular.ttf': {'win': "", 'lin_name': "", 'url': "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/opensans/static/OpenSans-Regular.ttf", 'is_zip': False},
    }

    total_tasks = len(modules) + (len(fonts) * 4)
    curr = 0

    # THE CINEMATIC MACRO
    def matrix_step(log_msg, status="SYSTEM", color=C_SUBTEXT, inc=1, delay=0.15):
        nonlocal curr
        curr += inc
        pct = min(100.0, (curr / max(1, total_tasks)) * 100.0)
        log_task(format_log(status, log_msg, color), "RAW")
        draw_viewport(progress_pct=pct, active_file="Initializing...", current_file_idx=curr, total_files=total_tasks, is_interactive=False)
        time.sleep(delay)

    matrix_step("INITIALIZING CORE MODULES...", "SYSTEM", C_TITLE, inc=0, delay=0.6)
    
    # 4. EXECUTING THE MATRIX LOADS
    for desc, mod, is_real in modules:
        matrix_step(f"Allocating memory buffer for {desc} [{mod}]...", "SYSTEM", C_SUBTEXT, inc=0, delay=0.08)
        
        if is_real:
            if mod == "pandas": import pandas as pd
            elif mod == "urllib": import urllib.request as urllib
            elif mod == "zipfile": import zipfile
            matrix_step(f"Physical library '{mod}' loaded into RAM.", "MOUNT", C_PROMPT, inc=0, delay=0.2)
        
        matrix_step(f"Module '{mod}' successfully mounted and verified.", "SUCCESS", C_STAGED, inc=1, delay=0.1)

    # 5. ASSET SCANNING & EXTRACTION
    matrix_step("INITIALIZING TYPOGRAPHY ENGINE...", "SYSTEM", C_TITLE, inc=0, delay=0.8)
    
    os.makedirs(HTML_DATA_DIR, exist_ok=True)
    os.makedirs(TMP_DIR, exist_ok=True)
    is_win = os.name == 'nt'
    
    def find_local_font(win_path, file_name):
        if is_win and os.path.exists(win_path): return win_path
        if not is_win and file_name:
            lin_paths = [
                f"/usr/share/fonts/truetype/msttcorefonts/{file_name}", f"/usr/share/fonts/truetype/msttcorefonts/{file_name.lower()}",
                f"/usr/share/fonts/TTF/{file_name}", f"/usr/share/fonts/{file_name}",
                os.path.expanduser(f"~/.local/share/fonts/{file_name}"), os.path.expanduser(f"~/.fonts/{file_name}")
            ]
            for p in lin_paths:
                if os.path.exists(p): return p
        return None

    for dest_name, meta in fonts.items():
        dest_path = os.path.join(HTML_DATA_DIR, dest_name)
        matrix_step(f"Evaluating dependency: {dest_name}", "SCAN", C_SUBTEXT, inc=1, delay=0.3)
        
        if not os.path.exists(dest_path):
            local_src = find_local_font(meta['win'], meta.get('lin_name', ''))
            if local_src:
                matrix_step(f"Discovered native OS asset at: {local_src}", "LOCAL", C_DIR, inc=1, delay=0.4)
                matrix_step(f"Copying {dest_name} to HTML/data vault...", "MOUNT", C_PROMPT, inc=1, delay=0.3)
                try:
                    shutil.copy2(local_src, dest_path)
                    matrix_step(f"Asset {dest_name} integrated flawlessly.", "SUCCESS", C_STAGED, inc=1, delay=0.2)
                except Exception as e:
                    matrix_step(f"Mount error: {e}", "FAILED", C_ALERT, inc=1, delay=0.5)
            else:
                matrix_step(f"Asset missing locally. Preparing network fetch...", "WARN", C_WARN, inc=1, delay=0.5)
                matrix_step(f"Opening secure HTTP tunnel to: {meta['url'].split('/')[2]}", "NETWORK", C_DIR, inc=0, delay=0.6)
                
                try:
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                        'Accept': '*/*'
                    }
                    req = urllib.Request(meta['url'].strip(), headers=headers)
                    
                    if meta.get('is_zip'):
                        zip_path = os.path.join(TMP_DIR, 'temp_font.zip')
                        matrix_step(f"Downloading binary payload from {meta['url']}...", "DOWNLOAD", C_FILE, inc=1, delay=1.0)
                        with urllib.urlopen(req) as response, open(zip_path, 'wb') as out_file: shutil.copyfileobj(response, out_file)
                        
                        matrix_step(f"Payload received. Unzipping temp_font.zip...", "EXTRACT", C_PROMPT, inc=1, delay=0.6)
                        with zipfile.ZipFile(zip_path, 'r') as z:
                            target_file = next((f for f in z.namelist() if f.endswith(dest_name)), None)
                            if target_file:
                                matrix_step(f"Located {target_file} inside archive. Extracting to {dest_path}...", "EXTRACT", C_PROMPT, inc=0, delay=0.5)
                                with z.open(target_file) as zf, open(dest_path, 'wb') as f: shutil.copyfileobj(zf, f)
                            else:
                                matrix_step(f"Could not find {dest_name} in archive!", "FAILED", C_ALERT, inc=0, delay=0.5)
                                
                        matrix_step(f"Purging temporary archive temp_font.zip...", "CLEANUP", C_SUBTEXT, inc=0, delay=0.4)
                        os.remove(zip_path)
                    else:
                        matrix_step(f"Downloading raw asset from {meta['url']}...", "DOWNLOAD", C_FILE, inc=2, delay=1.0)
                        with urllib.urlopen(req) as response, open(dest_path, 'wb') as out_file: shutil.copyfileobj(response, out_file)
                            
                    matrix_step(f"Asset {dest_name} successfully staged.", "SUCCESS", C_STAGED, inc=1, delay=0.2)
                except Exception as e:
                    matrix_step(f"Network fetch failed: {e}", "FAILED", C_ALERT, inc=2, delay=1.5)
        else:
            matrix_step(f"Verified existing cached asset: {dest_name}", "VERIFIED", C_STAGED, inc=3, delay=0.15)
            
    # 6. THE INTERNAL VIEWPORT LOCK
    # Push the final instruction directly into the viewport as the last log entry!
    matrix_step(f"{C_PROMPT}>>> BOOT SEQUENCE COMPLETE. PRESS [ENTER] TO LAUNCH OPERATIONS CENTER <<<{RESET}", "READY", C_STAGED, inc=0, delay=0)
    
    # Render it one last time and engage the scroll loop
    draw_viewport(progress_pct=100.0, active_file="System Ready", current_file_idx=total_tasks, total_files=total_tasks, is_interactive=True)
    
    while True:
        c = getch()
        if isinstance(c, bytes):
            try: c = c.decode('utf-8')
            except: continue
        if c in ('\r', '\n', '\x1b'): break
        
        vp_height = (term_h - 9) - 4 - 1
        max_scroll = max(0, len(viewport_logs) - vp_height)
        
        if c == '\x1b[A' or c == 'UP': scroll_offset = max(0, scroll_offset - 1)
        elif c == '\x1b[B' or c == 'DOWN': scroll_offset = min(max_scroll, scroll_offset + 1)
        elif c == '\x1b[5~' or c == 'PGUP': scroll_offset = max(0, scroll_offset - 10)
        elif c == '\x1b[6~' or c == 'PGDN': scroll_offset = min(max_scroll, scroll_offset + 10)
        
        draw_viewport(progress_pct=100.0, active_file="System Ready", current_file_idx=total_tasks, total_files=total_tasks, is_interactive=True)

# --- APPLICATION ENTRY ---

def main():
    global global_mode

    while True:
        sys.stdout.write(f"{C_BG}\033[2J\033[H")
        term_w, term_h = get_term_size()
        draw_top_bar()
        
        for i in range(2, term_h - 1): draw_frame_line("", row=i)
        
        draw_frame_line(f"{C_SIZE}OPTICAL LENS SPECIFICATIONS ENGINE: OPERATIONS CENTER{RESET}", row=2, align="center")
        
        pad = 15
        draw_frame_line(f"{C_TITLE}{get_ico('conv')}(C){C_FILE}onvert Manufacturers File -> Generate .VLP{RESET}", row=6, indent=pad)
        draw_frame_line(f"{C_TITLE}{get_ico('add')}(A){C_FILE}dd staged .VLP files into the Vault{RESET}", row=7, indent=pad)
        draw_frame_line(f"{C_TITLE}{get_ico('list')}(L){C_FILE}ist existing .VLP files in Vault{RESET}", row=8, indent=pad)
        draw_frame_line(f"{C_TITLE}{get_ico('scan')}(S){C_FILE}can existing Vault for integrity errors{RESET}", row=9, indent=pad)
        draw_frame_line(f"{C_TITLE}{get_ico('gen')}(G){C_FILE}eneration Sequence (Wipe & Rebuild DB){RESET}", row=10, indent=pad)
        draw_frame_line(f"{C_TITLE}{get_ico('html')}(E){C_FILE}xecute Master HTML Generation{RESET}", row=11, indent=pad)
        
        draw_frame_line(f"{C_TITLE}{get_ico('tools')}File Tools:{RESET}", row=13, indent=pad)
        draw_frame_line(f"  {C_TITLE}{get_ico('move')}(M){C_FILE}ove files{RESET}", row=14, indent=pad)
        draw_frame_line(f"  {C_TITLE}{get_ico('copy')}Co{C_TITLE}(p){C_FILE}y files{RESET}", row=15, indent=pad)
        draw_frame_line(f"  {C_TITLE}{get_ico('ren')}(R){C_FILE}ename file{RESET}", row=16, indent=pad)
        draw_frame_line(f"  {C_TITLE}{get_ico('del')}(D){C_FILE}elete files{RESET}", row=17, indent=pad)
        
        draw_frame_line(f"{C_ALERT}{get_ico('quit')}(Q)uit Application{RESET}", row=19, indent=pad)
        
        global_mode = "MAIN MENU"
        
        nf_status = f"{C_STAGED}[ON]{RESET}" if app_config.get('nerd_fonts') else f"{C_ALERT}[OFF]{RESET}"
        nf_text = f"{C_PROMPT}{get_ico('nf')}(N)erd Fonts: {nf_status}"
        draw_frame_line(nf_text, row=term_h - 5, align="right")
        
        ins_1 = f"Press a command hotkey (e.g. {C_PROMPT}C{C_SUBTEXT})."
        draw_frame_line(ins_1, row=term_h - 5, align="left", indent=4)
        
        draw_status_bar()
        
        sys.stdout.write(f"\033[{term_h - 4};5H{C_BGLIGHT} {C_PROMPT}{get_ico('term', pad=False)}  {RESET}{C_BGLIGHT}{' '*40}{RESET}\033[{term_h - 4};9H{C_BGLIGHT}")
        sys.stdout.flush()

        if handle_error_hijack(): continue
            
        sys.stdout.flush()
        cmd = getch()
        
        if cmd in ['\x1b[A', '\x1b[B', '\x1b[5~', '\x1b[6~', 'UP', 'DOWN', 'PGUP', 'PGDN']:
            continue
        sys.stdout.write(f"{RESET}")
        
        if cmd == 'F12': execute_admin_menu()
        elif cmd.lower() in ['q', 'x']: clean_exit()
        elif cmd.lower() == 'n': app_config['nerd_fonts'] = not app_config.get('nerd_fonts', False); save_config()
        # Look closely below: we decoupled the file manager from the router!
        elif cmd.lower() == 'c': execute_batch_convert() 
        elif cmd.lower() == 'a': execute_add_database()
        elif cmd.lower() == 'l': execute_list_database()
        elif cmd.lower() == 's': execute_scan_database()
        elif cmd.lower() == 'g': execute_generate_database()
        elif cmd.lower() == 'e': execute_html_generation()
        
        elif cmd.lower() == 'm': run_file_manager('mv', start_dir=BASE_DIR)
        elif cmd.lower() == 'p': run_file_manager('cp', start_dir=BASE_DIR)
        elif cmd.lower() == 'd': run_file_manager('rm', start_dir=BASE_DIR)
        elif cmd.lower() == 'r': run_file_manager('re', start_dir=BASE_DIR)

if __name__ == "__main__":
    try: 
        # 1. Establish the Color Palette
        init_environment()
        load_config()
        apply_theme(app_config.get("theme", "tokyo_night"))
        
        # 2. The Consent Wall (Handles the Y check and Modal internally)
        display_boot_sequence()

        # 3. Assets (Phase 0 ignites instantly upon returning from the Consent Wall)      
        verify_and_stage_fonts()
        
        # 4. The Grand Reveal & Main Loop
        # (The Final Lock is handled safely inside verify_and_stage_fonts)
        main()
        
    except KeyboardInterrupt: 
        clean_exit()
    except Exception as e:
        sys.stdout.write(f"\n\033[31m[FATAL CRASH] {str(e)}\033[0m\n")
        time.sleep(5) 
        clean_exit()
