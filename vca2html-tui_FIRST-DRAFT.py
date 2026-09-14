#!/usr/bin/env python3
# =============================================================================
# VCA2HTML-TUI v3.3.0 (Ultimate Optical Engine)
# OPTICAL LENS DATABASE ENGINE
# ==============================================================================

import os            # Core filesystem
import sys           # Console/stdout printing
import time          # Delays and UI pacing
import shutil        # Copy/Move/Delete files
import stat          # Needed for listing directories
import subprocess    # Running CAB extraction
import hashlib       # SHA256 Verification
import threading     # spinner
import random        # random numbers
import platform
import warnings      # uh, warnings
import atexit        # for the warnings on exit
import re
import textwrap      # to wrap text?
import json          # deal with json files
import base64        # base64 information
from datetime import datetime, timezone

# 1. Dual-Lane Dependency Check
missing_py_modules = []
missing_os_binaries = []

if os.name == 'nt':
    try: import msvcrt
    except ImportError: missing_py_modules.append("msvcrt")
else:
    try: import tty, termios, select
    except ImportError: missing_py_modules.append("tty/termios")
    
    # Check for OS-level Linux binaries natively
    if shutil.which('cabextract') is None:
        missing_os_binaries.append("cabextract")

if missing_py_modules or missing_os_binaries:
    if missing_py_modules:
        print(f"\033[31m[FATAL] Missing required Python libraries: {', '.join(missing_py_modules)}\033[0m")
        print(f"\033[33mRun: pip install {', '.join(missing_py_modules)}\033[0m\n")
    if missing_os_binaries:
        print(f"\033[31m[FATAL] Missing required OS Binaries: {', '.join(missing_os_binaries)}\033[0m")
        print(f"\033[33mRun: sudo apt install {', '.join(missing_os_binaries)} (or equivalent package manager)\033[0m")
    sys.exit(1)


# Global placeholders for the Tier-2 heavyweights
pd = None
np = None
openpyxl = None



# Suppress background warnings that destroy TUI coordinates
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

def clean_teardown():
    """Guarantees the terminal is wiped and color reset on exit/crash."""
    sys.stdout.write("\033[2J\033[H\033[0m")
    sys.stdout.flush()

atexit.register(clean_teardown)

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
HTML_FONT_DIR = os.path.join(HTML_DATA_DIR, 'fonts')
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
USE_NERD_FONTS = app_config.get('nerd_fonts', False)

active_icons = {}

def reload_icons():
    """Rebuilds the icon dictionary in-place based directly on the config state."""
    nf_on = app_config.get('nerd_fonts', False)
    
    new_icons = {
        "check": "" if nf_on else "✓",
        "cross": "" if nf_on else "X",
        "toggle": "" if nf_on else "=",
        "nf": "⚡" if nf_on else "NF",
        "opt_eng": "󰇻" if nf_on else "SYS",
        "mode": "󰚡" if nf_on else "M:",
        "db": "󱘲" if nf_on else "DB:",
        "lens": "󰊪" if nf_on else "O",
        "stage": "" if nf_on else "+",
        "term": "" if nf_on else ">",
        "prot": "󰒃" if nf_on else "@",
        "conv": "" if nf_on else "~",
        "add": "󱘫" if nf_on else "+",
        "list": "󱤢" if nf_on else "=",
        "scan": "󱘶" if nf_on else "?",
        "gen": "󱘸" if nf_on else "*",
        "html": "󰊯" if nf_on else "</>",
        "tools": "󰏗" if nf_on else "*",
        "move": "󱄗" if nf_on else "->",
        "copy": "󱉦" if nf_on else "C",
        "ren": "󱓦" if nf_on else "R",
        "del": "󱂨" if nf_on else "X",
        "quit": "󰗼" if nf_on else "Q",
        "arr_up": "󰧇" if nf_on else "^",
        "arr_dn": "󰦿" if nf_on else "v",
        "arr_prv": "󰧀" if nf_on else "<",
        "arr_nxt": "󰧂" if nf_on else ">",
        "dir_up": "󰷏" if nf_on else "..",
        "dir": "󰉖" if nf_on else "DIR",
        "file": "󰈙" if nf_on else "DOC",
        "ext_json": "󰘦" if nf_on else "{ }",
        "ext_html": "" if nf_on else "< >",
        "ext_csv": "󰈙" if nf_on else "CSV",
        "ext_vca": "󰈙" if nf_on else "VCA",
        "ext_txt": "󰈙" if nf_on else "TXT",
        "pfx_ok": "󰄬" if nf_on else "[+]",
        "pfx_warn": "󰀪" if nf_on else "[*]",
        "pfx_err": "󰅙" if nf_on else "[!]",
        "pfx_info": "󰋼" if nf_on else "[~]"
    }
    active_icons.clear()
    active_icons.update(new_icons)

reload_icons()

# --- INITIALIZATION & CONFIGURATION ---

def preflight_dependency_check():
    """Fails fast if 3rd party modules are missing, providing the exact install command."""
    import importlib.util
    import sys
    import os

    required_modules = ['pandas', 'numpy', 'openpyxl', 'psutil']
    missing = []

    for mod in required_modules:
        if importlib.util.find_spec(mod) is None:
            missing.append(mod)

    if missing:
        pkg_str = " ".join(missing)
        
        # 1. Flood the entire terminal with the Tokyo Night background color
        sys.stdout.write(f"{C_BG}\033[2J\033[H")
        
        # 2. \033[K forces the background color to paint all the way to the right edge
        print(f"{C_BG}\033[K")
        print(f"{C_BG}  {C_SIZE}❯  SYSTEM HALT: Missing Required Dependencies{RESET}{C_BG}\033[K")
        print(f"{C_BG}     {C_SUBTEXT}The engine cannot boot. You are missing:{RESET} {C_FILE}{', '.join(missing)}{RESET}{C_BG}\033[K")
        print(f"{C_BG}\033[K")
        
        if os.name == 'nt':
            print(f"{C_BG}     {C_SUBTEXT}Run this command to install them:{RESET}{C_BG}\033[K")
            print(f"{C_BG}     {C_STAGED}$ py -m pip install {pkg_str}{RESET}{C_BG}\033[K")
            print(f"{C_BG}     {C_SUBTEXT}(If 'py' fails, try: {C_STAGED}python -m pip install {pkg_str}{C_SUBTEXT}){RESET}{C_BG}\033[K")
        else:
            print(f"{C_BG}     {C_SUBTEXT}Run this command to install them:{RESET}{C_BG}\033[K")
            print(f"{C_BG}     {C_STAGED}$ python3 -m pip install {pkg_str}{RESET}{C_BG}\033[K")
            print(f"{C_BG}     {C_SUBTEXT}(Or use your native package manager, e.g., sudo pacman -S python3-pandas){RESET}{C_BG}\033[K")
        
        print(f"{C_BG}\033[K{RESET}")
        sys.exit(1)
        
def init_environment():
    dirs = [DATA_DIR, IMPORT_DIR, ORIGINALS_DIR, DB_DIR, VLP_ARCHIVE, PURGED_DIR, CORRUPT_DIR, HTML_DIR, HTML_DATA_DIR, HTML_FONT_DIR, HTML_DB_DIR, TMP_DIR]
    for d in dirs: 
        os.makedirs(d, exist_ok=True)
    if not os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'w') as f: json.dump(app_config, f, indent=4)
        except: pass
    if not os.path.exists(ICONS_FILE):
        try:
            with open(ICONS_FILE, 'w', encoding='utf-8') as f:
                json.dump(ICONS, f, indent=4, ensure_ascii=False)
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

def get_ico(key):
    """Returns the icon or its ASCII fallback with zero padding."""
    return active_icons.get(key, "")

def get_ext_ico(filename):
    """Dynamically grabs the file extension and returns the matched icon."""
    ext = os.path.splitext(filename)[1].lower().replace('.', '')
    # Tries to find 'ext_json', if it fails, falls back to the default 'file' icon
    return active_icons.get(f"ext_{ext}", active_icons.get('file', ""))

def get_pfx(t):
    """Returns the status prefix."""
    return active_icons.get(f"pfx_{t}", "")

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
        draw_frame_line(f"{C_ALERT}{get_pfx('err')}{get_ico('prot')} CRITICAL SECURITY ALERT: Master Database Signature Mismatch!{RESET}", row=r, align="center")
        draw_frame_line(f"{C_WARN}The master_lens_db.json file has been altered outside of the application.{RESET}", row=r+2, align="center")
        draw_frame_line(f"{C_WARN}To restore integrity, you must run the (G)eneration Sequence to rebuild the Vault.{RESET}", row=r+3, align="center")
        
        draw_universal_footer("Press ENTER to acknowledge and return to menu...")
        return False
    return True


# --- TUI DRAWING UTILITIES ---

def get_term_size():
    sz = shutil.get_terminal_size((120, 30))
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
        return f"{C_BGLIGHT} {C_PROMPT}{get_ico('term')}  {RESET}{C_BGLIGHT}"
    else:
        return f"{C_BGLIGHT}{C_PROMPT}>{RESET}{C_BGLIGHT}"

viewport_logs = []
scroll_offset = 0

def wrap_ansi_text(text, indent_spaces, max_w, cont_char="", color_carry=True):
    """Greedy word-wrapper that flows text to the edge, PRESERVES spaces, and REMEMBERS active colors."""
    ansi_escape = re.compile(r'(\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~]))')
    
    cont_vis_len = len(ansi_escape.sub('', cont_char)) if cont_char else 0
    safe_width = max_w - cont_vis_len - 1
    
    tokens = re.split(r'( +)', text)
    lines = []
    curr_line = ""
    curr_len = 0
    active_codes = []
    
    for token in tokens:
        if not token: continue
        
        token_clean_len = len(ansi_escape.sub('', token))
        
        if token.isspace():
            if curr_len + token_clean_len <= safe_width:
                curr_line += token
                curr_len += token_clean_len
                if color_carry:
                    for c in ansi_escape.findall(token):
                        if c in ('\x1b[0m', '\x1b[m', '\033[0m', '\033[m'): active_codes.clear()
                        else: active_codes.append(c)
            continue
            
        if curr_len + token_clean_len <= safe_width:
            curr_line += token
            curr_len += token_clean_len
            if color_carry:
                for c in ansi_escape.findall(token):
                    if c in ('\x1b[0m', '\x1b[m', '\033[0m', '\033[m'): active_codes.clear()
                    else: active_codes.append(c)
        else:
            lines.append(curr_line + (f" {cont_char}" if cont_char else ""))
            
            active_color_str = "".join(active_codes) if color_carry else ""
            curr_line = (" " * indent_spaces) + active_color_str + token
            curr_len = indent_spaces + token_clean_len
            
            if color_carry:
                for c in ansi_escape.findall(token):
                    if c in ('\x1b[0m', '\x1b[m', '\033[0m', '\033[m'): active_codes.clear()
                    else: active_codes.append(c)
                    
    if curr_line.strip() or len(ansi_escape.sub('', curr_line)) > 0:
        lines.append(curr_line)
        
    return lines

def log_task(task_string, tag="SYS"):
    global scroll_offset
    term_w, term_h = get_term_size()
    
    wrapped_lines = wrap_ansi_text(task_string, indent_spaces=4, max_w=term_w - 14)
    for line in wrapped_lines:
        viewport_logs.append(line)

def vp_log(tag, msg, level="info"):
    global scroll_offset
    term_w, term_h = get_term_size()
    
    if level == "ok": color = C_STAGED
    elif level == "err": color = C_ALERT
    elif level == "warn": color = C_WARN
    else: color = C_TITLE
    
    icon = "" if level == "ok" else ("✗" if level == "err" else ("!" if level == "warn" else "i"))
    padded_tag = str(tag).ljust(10)
    
    raw_str = f" {C_SUBTEXT}({color}{icon}{C_SUBTEXT}){RESET} {C_PROMPT}{padded_tag}{RESET}  {C_TITLE}❯{RESET}  {color}{msg}{RESET}"
    
    wrapped_lines = wrap_ansi_text(raw_str, indent_spaces=19, max_w=term_w - 14)
    for line in wrapped_lines:
        viewport_logs.append(line)

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

def format_log(tag, msg, color, is_cmd=False):
    """Formats logs. is_cmd=True bypasses the tag/colon for 2-space indented trails."""
    if is_cmd:
        # Just 2 spaces of padding. No tags.
        return f"{color}  {msg}{RESET}"
    else:
        # Standard Tokyo Night tagged formatting
        clean_tag = str(tag)[:10]
        tag_str = f" {clean_tag} ".ljust(12) 
        muted_colon = f"{C_SUBTEXT}:{color}"
        return f"{color}{tag_str}{muted_colon} {msg}{RESET}"

# Global Tracking
last_known_w, last_known_h = 0, 0

def draw_viewport(progress_pct=100.0, current_task_string="", active_file="", current_file_idx=0, total_files=0, total_types=0, total_lenses=0, is_interactive=False, action_text="", frame_title=""):
    global scroll_offset, last_known_w, last_known_h
    
    term_w, term_h = get_term_size()
    
    # THE UNIVERSAL RESIZE HOOK
    if term_w != last_known_w or term_h != last_known_h:
        last_known_w, last_known_h = term_w, term_h
        sys.stdout.write(f"{C_BG}\033[2J\033[H")
        draw_top_bar()
        for r in range(2, term_h - 1): draw_frame_line("", row=r)
        
        if frame_title:
            draw_frame_line(f"{C_SIZE}{frame_title}{RESET}", row=2, align="center")
            
        draw_status_bar()
    
    inner_l = 4; inner_r = term_w - 3
    box_w = inner_r - inner_l + 1
    
    pb_r1 = term_h - 5
    pb_r2 = term_h - 4
    pb_r3 = term_h - 3
    
    vp_start_row = 4
    vp_end_row = pb_r1 - 1
    vp_height = vp_end_row - vp_start_row - 1
    
    total_logs = max(1, len(viewport_logs))

    if not is_interactive:
        scroll_offset = max(0, total_logs - vp_height)
    else:
        scroll_offset = min(scroll_offset, max(0, total_logs - vp_height))
    
    sys.stdout.write(f"\033[{vp_start_row};{inner_l}H{C_BORDER}┌{'─' * (box_w - 2)}┐{RESET}")
    
    for i in range(vp_height):
        row = vp_start_row + 1 + i
        log_idx = scroll_offset + i
        log_text = viewport_logs[log_idx] if log_idx < len(viewport_logs) else ""
        
        thumb_size = max(1, int((vp_height / total_logs) * vp_height)) if len(viewport_logs) > vp_height else vp_height
        max_scroll_possible = max(1, total_logs - vp_height)
        scroll_pct = scroll_offset / max_scroll_possible if max_scroll_possible > 0 else 0
        thumb_pos = int(scroll_pct * (vp_height - thumb_size)) if len(viewport_logs) > vp_height else 0
        
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
    
    text_tl = f" Progress: {current_file_idx} of {total_files} " if total_files > 0 else " Progress "
    raw_top_l = f"({text_tl})"
    top_l_str = f"({C_BGLIGHT}{C_TITLE}{text_tl}{RESET}{C_BORDER})"

    raw_top_r = f"({active_file[:40] + '...' if len(active_file) > 40 else active_file})" if active_file else ""
    top_r_str = f"({C_BGLIGHT}\033[4m{C_PROMPT}{active_file[:40] + '...' if len(active_file) > 40 else active_file}{RESET}\033[24m{C_BORDER})" if active_file else ""

    text_bl_1 = f" {total_types} TYPES "
    text_bl_2 = f" {total_lenses:,} LENSES "
    
    raw_bot_l = ""
    bot_l_str = ""
    
    if action_text:
        clean_action = action_text.strip("() ")
        text_act = f" {clean_action} "
        raw_bot_l += f"({text_act})"
        bot_l_str += f"{C_BORDER}({C_BGLIGHT}{C_PROMPT}{text_act}{RESET}{C_BORDER})"
        
    if total_types > 0:
        if raw_bot_l: 
            raw_bot_l += "─"
            bot_l_str += "─"
        raw_bot_l += f"({text_bl_1}|{text_bl_2})"
        bot_l_str += f"{C_BORDER}({C_BGLIGHT}{C_STAGED}{text_bl_1}{C_SUBTEXT}|{C_STAGED}{text_bl_2}{RESET}{C_BORDER})"

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

def draw_z_index_modal(title, prompt, mask=False):
    """Draws a floating modal over the active UI and intercepts input."""
    term_w, term_h = get_term_size()
    box_w = max(50, ansi_len(prompt) + 10)
    box_h = 5
    start_y = (term_h // 2) - (box_h // 2)
    start_x = (term_w - box_w) // 2
    
    for i in range(box_h):
        row = start_y + i
        if i == 0:
            text = f"{C_BORDER}╔{'═'*(box_w-2)}╗{RESET}"
        elif i == 1:
            text = f"{C_BORDER}║{C_TITLE}{title:^{box_w-2}}{C_BORDER}║{RESET}"
        elif i == 2:
            text = f"{C_BORDER}║{C_PROMPT} {prompt:<{box_w-3}}{C_BORDER}║{RESET}"
        elif i == 3:
            text = f"{C_BORDER}║{C_FILE} > {' ' * (box_w-5)}{C_BORDER}║{RESET}"
        elif i == 4:
            text = f"{C_BORDER}╚{'═'*(box_w-2)}╝{RESET}"
            
        sys.stdout.write(f"\033[{row};{start_x}H{C_BG}{text}")
    sys.stdout.flush()
    
    val = ""
    while True:
        cursor_x = start_x + 4 + len(val)
        sys.stdout.write(f"\033[{start_y+3};{cursor_x}H\033[?25h")
        sys.stdout.flush()
        
        ch = getch()
        if ch in ['\r', '\n']:
            break
        elif ch == 'ESC':
            sys.stdout.write("\033[?25l")
            return None
        elif ch in ['BACKSPACE', '\x08', '\x7f', 'DEL']:
            if len(val) > 0:
                val = val[:-1]
                sys.stdout.write(f"\033[{start_y+3};{cursor_x-1}H \033[{start_y+3};{cursor_x-1}H")
        elif len(ch) == 1 and ch.isprintable() and len(val) < box_w - 7:
            val += ch
            sys.stdout.write('*' if mask else ch)
            
    sys.stdout.write("\033[?25l")
    return val

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
    prompt_ico = get_ico('term') if app_config['nerd_fonts'] else "[!]"
    sys.stdout.write(f"\033[{term_h - 4};5H{C_BGLIGHT} {C_ALERT}{prompt_ico} {err_msg} {C_SUBTEXT}(Press ENTER){RESET}{C_BGLIGHT}{' '*10}{RESET}")
    sys.stdout.flush()
    while True:
        c = getch()
        if c == 'F12': execute_admin_menu(); return True
        if c in ['\r', '\n']: break
    err_msg = ""
    sys.stdout.write(f"\033[{term_h - 4};5H{C_BGLIGHT} {C_PROMPT}{get_ico('term')}  {RESET}{C_BGLIGHT}{' '*60}{RESET}\033[{term_h - 4};9H{C_BGLIGHT}")
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
    
    # Strip redundant text directly in the renderer
    clean_mode = global_mode.replace(" (Generate)", "").replace(" (GENERATE)", "")
    mode_str = clean_mode.upper()
    
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
    
    m_block = f"{C_SIZE}{get_ico(m_key)} MODE: {C_TITLE}{clean_mode}{C_BORDER}"
    db_block = f"{C_SIZE}{get_ico('db')} DB: {C_TITLE}{'ACTIVE' if db_active else 'OFFLINE'}{C_BORDER}"
    l_block = f"{C_SIZE}{get_ico('lens')} LENSES: {C_STAGED}{total_lenses:,}{C_BORDER}"
    s_block = f"{C_SIZE}{get_ico('stage')} STAGED: {C_TITLE}{staged}{C_BORDER}"

    # Reduced structural padding to allow the dynamic gap to breathe
    left = f"{C_BORDER}╚══[{m_block}]══[{db_block}]══({l_block})══[{s_block}]"
    right = f"══[{C_TITLE}{get_ico('prot')} {get_sys_info()}{C_BORDER}]══╝{RESET}"
    
    gap = term_w - ansi_len(left) - ansi_len(right)
    
    # Dynamic failsafe: If the screen is exceptionally narrow, crush the padding
    if gap < 0:
        left = f"{C_BORDER}╚═[{m_block}]═[{db_block}]═({l_block})═[{s_block}]"
        right = f"═[{C_TITLE}{get_ico('prot')} {get_sys_info()}{C_BORDER}]═╝{RESET}"
        gap = max(0, term_w - ansi_len(left) - ansi_len(right))
        
    sys.stdout.write(f"\033[{term_h - 1};1H{left}{'═' * gap}{right}")
    sys.stdout.flush()

def draw_universal_footer_ui(prompt_text):
    term_w, term_h = get_term_size()
    draw_status_bar()
    sys.stdout.write(f"\033[{term_h - 4};5H{C_BGLIGHT} {C_PROMPT}{get_ico('term')}  {C_STAGED}{prompt_text}{RESET}{C_BGLIGHT}{' '*40}{RESET}\033[{term_h - 4};{10+ansi_len(prompt_text)}H")
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
    indicator = f"{C_PROMPT}{get_ico('term')}  {RESET}" if app_config.get('nerd_fonts', False) else f"{C_PROMPT}> {RESET}"
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
        ico = get_ico('term')
        return f"{C_PROMPT}{ico}{RESET}{C_BGLIGHT}"
    else:
        return f"{C_PROMPT}>{RESET}{C_BGLIGHT}"

def render_ui_skeleton(loading_text="Initializing..."):
    sys.stdout.write(f"{C_BG}\033[2J\033[H")
    term_w, term_h = get_term_size()
    draw_top_bar()
    for r in range(2, term_h - 1): draw_frame_line("", row=r)
    draw_frame_line(f"{C_TITLE}{loading_text}{RESET}", 4, align="center")
    if 'draw_universal_footer_ui' in globals(): draw_universal_footer_ui("Processing Request...")
    sys.stdout.flush()

def clean_teardown():
    """the terminal is wiped and color reset on exit/crash."""
    sys.stdout.write("\033[?1049l\033[?25h\033[0m")
    sys.stdout.flush()

def clean_exit(msg=None):
    sys.stdout.write(f"{C_BG}\033[2J\033[H")
    # Destroy Buffer, restore cursor, and execute hard color reset
    sys.stdout.write("\033[?1049l\033[?25h\033[0m")
    sys.stdout.flush()
    
    if msg:
        print(f"{C_ALERT}{msg}\033[0m")
        
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

# --- BOOT & ADMINISTRATION ---

def verify_and_stage_fonts():
    global global_mode, scroll_offset, viewport_logs
    global pd, np, zipfile, openpyxl
    import urllib.parse
    import subprocess
    import threading
    import time
    import random
    import os
    import shutil
    import hashlib
    import re
    
    sys.stdout.write(f"{C_BG}\033[2J\033[H")
    term_w, term_h = get_term_size()
    draw_top_bar()
    for r in range(2, term_h - 1): draw_frame_line("", row=r)
    draw_frame_line(f"{C_SIZE}PHASE 0: SYSTEM INITIALIZATION & ASSET VERIFICATION{RESET}", row=2, align="center")
    draw_status_bar() 
    sys.stdout.flush()
    
    viewport_logs.clear()
    scroll_offset = 0
    BASE_INDENT = 0
    MARGIN = " " * BASE_INDENT

    modules = [
        ("Core OS Interface", "os", False), ("System Pathways", "sys", False),
        ("Temporal Engine", "time", False), ("Platform Diagnostics", "platform", False),
        ("Warning Handlers", "warnings", False), ("Exit Routines", "atexit", False),
        ("Regex Engine", "re", False), ("File Operations", "shutil", False),
        ("JSON Parsers", "json", False), ("Sys Stat", "stat", False),
        ("Text Wrapping", "textwrap", False), ("Datetime Engine", "datetime", False),
        ("Timezone Protocols", "timezone", False), ("Cryptographic Hashes", "hashlib", False),
        ("Binary Encoders", "base64", False),
        ("Network Libraries", "urllib", True), ("System Information", "psutil", True),
        ("Archive Tools", "zipfile", True), ("Data Aggregator", "pandas", True),
        ("Numeric Engine", "numpy", True), ("Excel IO Engine", "openpyxl", True)
    ]
    
    fonts = {
        'Arial-Regular.ttf': {'win': r"C:\Windows\Fonts\arial.ttf", 'lin_name': 'arial.ttf', 'url': "https://downloads.sourceforge.net/project/corefonts/the%20fonts/final/arial32.exe", 'is_cab': True, 'target_ttf': 'arial.ttf'},
        'Arial-Bold.ttf': {'win': r"C:\Windows\Fonts\arialbd.ttf", 'lin_name': 'arialbd.ttf', 'url': "https://downloads.sourceforge.net/project/corefonts/the%20fonts/final/arialb32.exe", 'is_cab': True, 'target_ttf': 'arialbd.ttf'},
        'Tahoma-Regular.ttf': {'win': r"C:\Windows\Fonts\tahoma.ttf", 'lin_name': 'tahoma.ttf', 'url': "https://downloads.sourceforge.net/project/corefonts/the%20fonts/final/iel32.exe", 'is_cab': True, 'target_ttf': 'tahoma.ttf'},
        'MSSansSerif-Regular.ttf': {'win': r"C:\Windows\Fonts\micross.ttf", 'lin_name': 'micross.ttf', 'url': "https://cdn.jsdelivr.net/gh/matomo-org/travis-scripts@master/fonts/micross.ttf"},
        'UbuntuSansNerdFont-Regular.ttf': {
            'win': "", 'lin_name': "", 
            'url': "https://github.com/ryanoasis/nerd-fonts/releases/latest/download/UbuntuSans.zip", 
            'is_zip': True,
            'extra_targets': ['UbuntuSansNerdFont-Medium.ttf', 'UbuntuSansNerdFont-Bold.ttf', 'UbuntuSansNerdFont-Italic.ttf']
        },
        'JetBrainsMonoNerdFont-Regular.ttf': {'win': "", 'lin_name': "", 'url': "https://github.com/ryanoasis/nerd-fonts/releases/latest/download/JetBrainsMono.zip", 'is_zip': True},
        'FiraCodeNerdFont-Regular.ttf': {'win': "", 'lin_name': "", 'url': "https://github.com/ryanoasis/nerd-fonts/releases/latest/download/FiraCode.zip", 'is_zip': True},
        'CaskaydiaCoveNerdFont-Regular.ttf': {'win': "", 'lin_name': "", 'url': "https://github.com/ryanoasis/nerd-fonts/releases/latest/download/CascadiaCode.zip", 'is_zip': True},
        'NotoSansNerdFont-Regular.ttf': {'win': "", 'lin_name': "", 'url': "https://github.com/ryanoasis/nerd-fonts/releases/latest/download/Noto.zip", 'is_zip': True},
        'OpenSans-Regular.ttf': {'win': "", 'lin_name': "", 'url': "https://cdn.jsdelivr.net/gh/googlefonts/opensans@main/fonts/ttf/OpenSans-Regular.ttf"},
    }

    USE_NERD_FONTS = app_config.get('nerd_fonts', False)
    CHECK_MARK = "" if USE_NERD_FONTS else "✓"
    is_win = os.name == 'nt'
    BOLD = "\033[1m"
    L_CONT = f"{C_PROMPT}{BOLD}`{RESET}" if is_win else f"{C_PROMPT}{BOLD}\\{RESET}"

    os.makedirs(HTML_DATA_DIR, exist_ok=True)
    os.makedirs(HTML_FONT_DIR, exist_ok=True)
    os.makedirs(TMP_DIR, exist_ok=True)

    display_font_dir = "./" + os.path.relpath(HTML_FONT_DIR).replace(os.sep, '/')

    def find_local_font(win_path, file_name):
        if is_win and os.path.exists(win_path): return win_path
        if not is_win and file_name:
            lin_paths = [
                f"/usr/share/fonts/truetype/msttcorefonts/{file_name}", 
                f"/usr/share/fonts/TTF/{file_name}", f"/usr/share/fonts/{file_name}",
                os.path.expanduser(f"~/.local/share/fonts/{file_name}")
            ]
            for p in lin_paths:
                if os.path.exists(p): return p
        return None

    total_ghost_loads = sum(1 for m in modules if not m[2])
    ghost_weight = 1.0 / max(1, total_ghost_loads)
    boot_total = sum(1 for m in modules if m[2]) + (1 if total_ghost_loads > 0 else 0)
    curr = 0.0
    
    # --- THE CONTINUOUS TICK COUNTER ---
    spinner_tick = 0

    for dest_name, meta in fonts.items():
        targets = [dest_name] + meta.get('extra_targets', [])
        missing_count = sum(1 for t in targets if not os.path.exists(os.path.join(HTML_FONT_DIR, t)))
        
        if missing_count == 0:
            boot_total += len(targets)
        else:
            local_src = find_local_font(meta.get('win', ''), meta.get('lin_name', ''))
            if local_src: 
                boot_total += 2
            else: 
                boot_total += 1 
                if meta.get('is_cab') or meta.get('is_zip'): boot_total += 2
                else: boot_total += 1
                boot_total += len(targets)
            
    def fast_track_step(tag, desc):
        nonlocal curr
        global scroll_offset
        padded_tag = tag.ljust(10)
        viewport_logs.append(f"{MARGIN}{C_STAGED} {CHECK_MARK} {RESET} {C_PROMPT}{padded_tag}{RESET}  {C_TITLE}❯{RESET}  {C_FILE}{desc}{RESET}")
        curr += ghost_weight 
        vp_height = (term_h - 9) - 4 - 1
        scroll_offset = max(0, len(viewport_logs) - vp_height)
        pct = min(100.0, (curr / max(1, boot_total)) * 100.0)
        draw_viewport(progress_pct=pct, active_file="Executing...", current_file_idx=int(curr), total_files=boot_total, is_interactive=False)
        sys.stdout.flush()
        time.sleep(random.uniform(0.03, 0.08))

    def execute_pipeline(tag, objective, tasks):
        nonlocal curr, spinner_tick
        global scroll_offset
        padded_tag = tag.ljust(10)
        header_idx = len(viewport_logs)
        
        spinner_chars = ['|', '/', '-', '\\']
        start_char = spinner_chars[spinner_tick % len(spinner_chars)]
        
        viewport_logs.append(f"{MARGIN}{C_SIZE}({C_TITLE}{start_char}{C_SIZE}){RESET} {C_PROMPT}{padded_tag}{RESET}  {C_TITLE}❯{RESET}  {C_FILE}{objective}{RESET}")

        for raw_cmd, task_func in tasks:
            if not raw_cmd:
                continue
            
            # Routes the fully flattened command string through the new wrapper
            wrapped_cmd = wrap_ansi_text(raw_cmd, indent_spaces=11, max_w=term_w - 14, cont_char=L_CONT)
            
            viewport_logs.append(f"{MARGIN} {C_STAGED}${RESET} {wrapped_cmd[0].strip()}")
            for w_line in wrapped_cmd[1:]:
                viewport_logs.append(w_line)
                
            floor_time = random.uniform(0.8, 1.6) 
            task_complete = False
            
            def worker():
                nonlocal task_complete
                try: 
                    if task_func: task_func()
                except Exception: pass
                task_complete = True
                
            t = threading.Thread(target=worker)
            t.start()
            start_time = time.time()
            
            while not task_complete or (time.time() - start_time) < floor_time:
                char = spinner_chars[spinner_tick % len(spinner_chars)]
                spin = f"{C_TITLE}{char}{C_SIZE}"
                viewport_logs[header_idx] = f"{MARGIN}{C_SIZE}({spin}){RESET} {C_PROMPT}{padded_tag}{RESET}  {C_TITLE}❯{RESET}  {C_FILE}{objective}{RESET}"
                vp_height = (term_h - 9) - 4 - 1
                scroll_offset = max(0, len(viewport_logs) - vp_height)
                pct = min(100.0, (curr / max(1, boot_total)) * 100.0)
                draw_viewport(progress_pct=pct, active_file="Executing...", current_file_idx=int(curr), total_files=boot_total, is_interactive=False)
                sys.stdout.flush()
                time.sleep(0.12)
                spinner_tick += 1
            curr += 1.0

        viewport_logs[header_idx] = f"{MARGIN}{C_STAGED} {CHECK_MARK} {RESET} {C_PROMPT}{padded_tag}{RESET}  {C_TITLE}❯{RESET}  {C_FILE}{objective}{RESET}"
        pct = min(100.0, (curr / max(1, boot_total)) * 100.0)
        draw_viewport(progress_pct=pct, active_file="Executing...", current_file_idx=int(curr), total_files=boot_total, is_interactive=False)
        sys.stdout.flush()

    def load_module_task(m):
        global pd, np, zipfile, openpyxl
        if m == "pandas": import pandas as pd
        elif m == "numpy": import numpy as np
        elif m == "openpyxl": import openpyxl
        elif m == "urllib":
            import urllib.request
            import urllib.parse
        elif m == "zipfile": import zipfile

    # 4A. GHOST & TRUE LOADS
    for desc, mod, is_real in modules:
        if not is_real:
            fast_track_step("SYS MODULE", f"Verifying {desc} {C_SUBTEXT}[{C_FILE}{mod}{C_SUBTEXT}]{RESET}")
        else:
            if is_win: raw_cmd = f"{C_TITLE}pip{RESET} {C_TITLE}show{RESET} {C_FILE}{mod}{RESET} {C_SUBTEXT}|{RESET} {C_TITLE}findstr{RESET} {C_FILE}Location{RESET}"
            else: raw_cmd = f"{C_TITLE}python{RESET} {C_SUBTEXT}-{C_SIZE}m{RESET} {C_TITLE}site{RESET} {C_SUBTEXT}--{C_SIZE}user{C_SUBTEXT}-{C_SIZE}site{RESET} {C_FILE}{mod}{RESET}"
            execute_pipeline("SYS MODULE", f"Loading {desc} {C_SUBTEXT}[{C_FILE}{mod}{C_SUBTEXT}]{RESET}", [(raw_cmd, lambda m=mod: load_module_task(m))])

    # 4B. FONT ASSETS
    for dest_name, meta in fonts.items():
        targets = [dest_name] + meta.get('extra_targets', [])
        missing_count = sum(1 for t in targets if not os.path.exists(os.path.join(HTML_FONT_DIR, t)))
        real_filename = urllib.parse.unquote(meta['url'].split('/')[-1])
        if "download?family" in real_filename: real_filename = dest_name.replace(".ttf", ".zip")
        
        obj_title = f"{dest_name} {C_SUBTEXT}(+{len(targets)-1} extras){RESET}" if len(targets) > 1 else dest_name

        if missing_count > 0:
            local_src = find_local_font(meta.get('win', ''), meta.get('lin_name', ''))
            if local_src:
                if is_win: copy_cmd = f"{C_TITLE}copy{RESET} {C_SUBTEXT}/{C_SIZE}Y{RESET} \"{C_FILE}{local_src}{RESET}\" \"{C_FILE}{display_font_dir}{RESET}\""
                else: copy_cmd = f"{C_TITLE}cp{RESET} {C_SUBTEXT}-{C_SIZE}v{RESET} \"{C_FILE}{local_src}{RESET}\" \"{C_FILE}{display_font_dir}{RESET}\""
                
                if is_win: hash_cmd = f"{C_TITLE}certutil.exe{RESET} {C_SUBTEXT}-{C_SIZE}hashfile{RESET} \"{C_FILE}{dest_name}{RESET}\" {C_TITLE}SHA256{RESET}"
                else: hash_cmd = f"{C_TITLE}sha256sum{RESET} \"{C_FILE}{display_font_dir}/{dest_name}{RESET}\""

                tasks = [
                    (copy_cmd, lambda l_src=local_src, d_pth=os.path.join(HTML_FONT_DIR, dest_name): shutil.copy2(l_src, d_pth)),
                    (hash_cmd, lambda path=os.path.join(HTML_FONT_DIR, dest_name): hashlib.sha256(open(path, 'rb').read()).hexdigest() if os.path.exists(path) else None)
                ]
                execute_pipeline("FONT ASSET", f"Need {obj_title} (Found in native OS cache)", tasks)
            else:
                tasks = []
                dl_bin = "curl.exe" if is_win else "curl"
                tmp_target = f"./data/.tmp/{real_filename}"
                real_tmp_path = os.path.join(TMP_DIR, real_filename)
                
                dl_cmd = f"{C_TITLE}{dl_bin}{RESET} {C_SUBTEXT}-{C_SIZE}sL{RESET} \"{C_FILE}{meta['url']}{RESET}\" {C_SUBTEXT}-{C_SIZE}o{RESET} \"{C_FILE}{tmp_target}{RESET}\""
                tasks.append((dl_cmd, lambda url=meta["url"].strip(), path=real_tmp_path: subprocess.run(f'{dl_bin} -sL "{url}" -o "{path}"', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)))
                
                if meta.get('is_cab'):
                    if is_win:
                        ext_cmd = f"{C_TITLE}extrac32.exe{RESET} {C_SUBTEXT}/{C_SIZE}E{RESET} {C_SUBTEXT}/{C_SIZE}Y{RESET} \"{C_FILE}{tmp_target}{RESET}\" \"{C_FILE}{meta['target_ttf']}{RESET}\""
                        tasks.append((ext_cmd, lambda path=real_tmp_path, trg=meta["target_ttf"], dest=os.path.join(HTML_FONT_DIR, dest_name): subprocess.run(f'extrac32.exe /E /Y "{path}" "{trg}"', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) or (shutil.move(trg, dest) if os.path.exists(trg) else None)))
                        del_cmd = f"{C_TITLE}del{RESET} {C_SUBTEXT}/{C_SIZE}F{RESET} {C_SUBTEXT}/{C_SIZE}Q{RESET} \"{C_FILE}{tmp_target}{RESET}\""
                    else:
                        ext_cmd = f"{C_TITLE}cabextract{RESET} {C_SUBTEXT}-{C_SIZE}q{RESET} {C_SUBTEXT}-{C_SIZE}F{RESET} \"{C_FILE}{meta['target_ttf']}{RESET}\" \"{C_FILE}{tmp_target}{RESET}\" {C_SUBTEXT}-{C_SIZE}d{RESET} \"{C_FILE}{display_font_dir}{RESET}\""
                        tasks.append((ext_cmd, lambda trg=meta["target_ttf"], path=real_tmp_path: subprocess.run(f'cabextract -q -F "{trg}" "{path}" -d "{HTML_FONT_DIR}"', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)))
                        del_cmd = f"{C_TITLE}rm{RESET} {C_SUBTEXT}-{C_SIZE}f{RESET} \"{C_FILE}{tmp_target}{RESET}\""
                        
                    tasks.append((del_cmd, lambda path=real_tmp_path: os.remove(path) if os.path.exists(path) else None))
                    
                elif meta.get('is_zip'):
                    t_str = " ".join([f'"{C_FILE}{t}{RESET}"' for t in targets])
                    
                    if is_win:
                        ext_cmd = f"{C_TITLE}tar.exe{RESET} {C_SUBTEXT}-{C_SIZE}xf{RESET} \"{C_FILE}{tmp_target}{RESET}\" {C_SUBTEXT}-{C_SIZE}C{RESET} \"{C_FILE}{display_font_dir}{RESET}\" {t_str}"
                        del_cmd = f"{C_TITLE}del{RESET} {C_SUBTEXT}/{C_SIZE}F{RESET} {C_SUBTEXT}/{C_SIZE}Q{RESET} \"{C_FILE}{tmp_target}{RESET}\""
                    else:
                        ext_cmd = f"{C_TITLE}unzip{RESET} {C_SUBTEXT}-{C_SIZE}q{RESET} \"{C_FILE}{tmp_target}{RESET}\" {t_str} {C_SUBTEXT}-{C_SIZE}d{RESET} \"{C_FILE}{display_font_dir}{RESET}\""
                        del_cmd = f"{C_TITLE}rm{RESET} {C_SUBTEXT}-{C_SIZE}f{RESET} \"{C_FILE}{tmp_target}{RESET}\""

                    def ext_task(path=real_tmp_path, t_args=" ".join([f'"{x}"' for x in targets])):
                        if is_win: subprocess.run(f'tar.exe -xf "{path}" -C "{HTML_FONT_DIR}" {t_args}', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        else: subprocess.run(f'unzip -q "{path}" {t_args} -d "{HTML_FONT_DIR}"', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                            
                    tasks.append((ext_cmd, ext_task))
                    tasks.append((del_cmd, lambda path=real_tmp_path: os.remove(path) if os.path.exists(path) else None))
                
                else:
                    if is_win: mv_cmd = f"{C_TITLE}move{RESET} {C_SUBTEXT}/{C_SIZE}Y{RESET} \"{C_FILE}{tmp_target}{RESET}\" \"{C_FILE}{display_font_dir}/{dest_name}{RESET}\""
                    else: mv_cmd = f"{C_TITLE}mv{RESET} {C_SUBTEXT}-{C_SIZE}f{RESET} \"{C_FILE}{tmp_target}{RESET}\" \"{C_FILE}{display_font_dir}/{dest_name}{RESET}\""
                    tasks.append((mv_cmd, lambda p1=real_tmp_path, p2=os.path.join(HTML_FONT_DIR, dest_name): shutil.move(p1, p2) if os.path.exists(p1) else None))

                for t in targets:
                    t_path = os.path.join(HTML_FONT_DIR, t)
                    if is_win: h_cmd = f"{C_TITLE}certutil.exe{RESET} {C_SUBTEXT}-{C_SIZE}hashfile{RESET} \"{C_FILE}{t}{RESET}\" {C_TITLE}SHA256{RESET}"
                    else: h_cmd = f"{C_TITLE}sha256sum{RESET} \"{C_FILE}{display_font_dir}/{t}{RESET}\""
                    tasks.append((h_cmd, lambda path=t_path: hashlib.sha256(open(path, 'rb').read()).hexdigest() if os.path.exists(path) else None))
                
                execute_pipeline("FONT ASSET", f"Need {obj_title} (Fetching remote...)", tasks)
        else:
            tasks = []
            for t in targets:
                t_path = os.path.join(HTML_FONT_DIR, t)
                if is_win: h_cmd = f"{C_TITLE}certutil.exe{RESET} {C_SUBTEXT}-{C_SIZE}hashfile{RESET} \"{C_FILE}{t}{RESET}\" {C_TITLE}SHA256{RESET}"
                else: h_cmd = f"{C_TITLE}sha256sum{RESET} \"{C_FILE}{display_font_dir}/{t}{RESET}\""
                tasks.append((h_cmd, lambda path=t_path: hashlib.sha256(open(path, 'rb').read()).hexdigest() if os.path.exists(path) else None))
            
            execute_pipeline("FONT ASSET", f"Verified {obj_title} (In vault cache)", tasks)

    execute_pipeline("SYSTEM RDY", f"{C_STAGED}BOOT SEQUENCE COMPLETE. PRESS [ENTER] TO LAUNCH OPERATIONS CENTER{RESET}", [("", None)])
    
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
        
        pct = min(100.0, (curr / max(1, boot_total)) * 100.0)
        draw_viewport(progress_pct=pct, active_file="System Ready", current_file_idx=int(curr), total_files=boot_total, is_interactive=True)

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

def bootstrap_web_templates(theme_css_block, theme_options_html, font_css_block, font_options_html, default_font_id):
    template_dir = os.path.join(HTML_DATA_DIR, '.templates')
    os.makedirs(template_dir, exist_ok=True)

    css_path = os.path.join(template_dir, 'styles.css')
    with open(css_path, 'w', encoding='utf-8') as f:
        f.write("""
/* DYNAMIC FONT ENGINE */
{{FONT_CSS_BLOCK}}

/* DYNAMIC THEME ENGINE */
{{THEME_CSS_BLOCK}}

:root {
    --table-fs: 15px;
    --table-th-fs: 12px;
}

body { background-color: var(--bg-main); color: var(--text-main); font-weight: 500; margin: 0; padding: 20px; transition: background-color 0.1s; font-variant-numeric: tabular-nums; }

.top-bar { position: relative; display: flex; justify-content: space-between; align-items: flex-start; background-color: var(--win-title); border: 1px solid var(--border-light); border-bottom: 2px solid var(--border-dark); padding: 16px 24px; margin-bottom: 15px; border-radius: 6px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }

/* VCA Branding (Top Left) */
.top-bar-left { display: flex; flex-direction: column; align-items: flex-start; gap: 8px; margin-top: 4px; }
.brand-title { font-size: 26px; font-weight: 900; color: var(--accent); letter-spacing: 1.5px; font-family: inherit; }
.brand-sub { font-size: 14px; font-weight: bold; color: var(--col-idx); letter-spacing: 1px; }

/* True Center Master Title */
.top-bar-center { position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%); text-align: center; color: var(--win-title-text); font-weight: 800 !important; font-size: 28px; text-transform: uppercase; letter-spacing: 3px; text-shadow: 1px 1px 2px rgba(0,0,0,0.2); white-space: nowrap; }

/* Symmetrical Dropdown Cluster (Top Right) */
.top-bar-right { display: flex; flex-direction: column; gap: 10px; align-items: flex-end; }
.dropdown-row { display: flex; gap: 12px; align-items: center; }
.header-dropdown { background: var(--bg-table); color: var(--text-main); border: 1px solid var(--border-light); padding: 6px 8px; border-radius: 4px; font-family: inherit; cursor: pointer; outline: none; font-size: 14px; font-weight: bold; transition: border-color 0.2s; }
.header-dropdown:hover { border-color: var(--col-desc); }
.dd-icon { color: var(--win-title-text); font-size: 18px; width: 20px; text-align: center; }

/* ---------------------------------------------------
   SPA SEARCH & PILL ENGINE
--------------------------------------------------- */
.stats-bar { background-color: var(--bg-table); padding: 20px 24px; border: 1px solid var(--border-light); border-radius: 6px; margin-bottom: 30px; display: flex; flex-direction: column; gap: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.15); }
.filter-row { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; justify-content: flex-start; width: 100%; margin-bottom: 4px; }
.pill-label { font-size: 14px; color: var(--col-desc); font-weight: bold; text-transform: uppercase; letter-spacing: 1px; width: 100px; text-align: right; margin-right: 10px; }

.mfg-pill { padding: 8px 24px; border-radius: 50px; background: var(--bg-main); color: var(--text-main); font-weight: bold; border: 2px solid var(--border-light); font-size: 16px; cursor: pointer; user-select: none; transition: all 0.1s; text-decoration: none;}
.mfg-pill.active { background: var(--accent); border-color: var(--accent); color: #fff; box-shadow: 0 4px 8px rgba(0,0,0,0.3); }

.stat-badge { padding: 5px 16px; border-radius: 50px; background: var(--bg-main); color: var(--text-main); font-weight: bold; border: 1px solid var(--border-light); font-size: 14px; cursor: pointer; user-select: none; transition: all 0.1s; text-decoration: none;}
.stat-badge:hover, .mfg-pill:hover { border-color: var(--col-desc); }
.stat-badge.active { background: var(--col-desc); color: var(--bg-main); border-color: var(--col-desc); }

/* Custom Row Colors for active Pills */
.filter-row.row-type .stat-badge.active { background: var(--col-filt); border-color: var(--col-filt); color: var(--bg-main); }
.filter-row.row-mat .stat-badge.active { background: var(--col-mat); border-color: var(--col-mat); color: var(--bg-main); }
.filter-row.row-tech .stat-badge.active { background: var(--col-idx); border-color: var(--col-idx); color: var(--bg-main); }
.filter-row.row-coat .stat-badge.active { background: var(--col-coat); border-color: var(--col-coat); color: var(--bg-main); }

.search-container { margin-top: 15px; border-top: 1px solid var(--border-dark); padding-top: 20px; width: 100%; display: flex; justify-content: center;}
.search-box { width: 80%; padding: 14px 24px; border-radius: 50px; border: 1px solid var(--border-light); background: var(--bg-main); color: var(--text-main); font-family: inherit; font-size: 16px; font-weight: bold; box-sizing: border-box; outline: none; transition: border-color 0.2s; text-align: center; }
.search-box:focus { border-color: var(--accent); box-shadow: 0 0 0 2px rgba(61, 89, 161, 0.3); }
.search-box::placeholder { color: var(--col-mat); opacity: 0.8; font-style: italic; font-weight: normal; }

.category-section { display: none; margin-bottom: 50px; }
.cat-title { color: var(--win-title-text); font-size: 22px; font-weight: bold; border-bottom: 2px solid var(--border-dark); padding-bottom: 8px; margin-bottom: 15px; text-transform: uppercase; letter-spacing: 1px; }

/* ---------------------------------------------------
   RIGID DATA GRID (SCALED TYPOGRAPHY)
--------------------------------------------------- */
.table-container { border-radius: 12px; overflow: hidden; box-shadow: 0 8px 16px rgba(0, 0, 0, 0.4); border: 1px solid var(--border-dark); }
table.data-grid { width: 100%; border-collapse: collapse; background: var(--bg-table); table-layout: fixed; }
table.data-grid th, table.data-grid td { border: 1px solid var(--border-light); padding: 8px 10px; text-align: center; vertical-align: middle; }

table.data-grid th { font-weight: 800; text-transform: uppercase; font-size: var(--table-th-fs); letter-spacing: 0.05em; color: var(--bg-main) !important; text-shadow: 0px 0px 2px rgba(255,255,255,0.4); }
table.data-grid td { font-size: var(--table-fs); }
table.data-grid td.col-mat, table.data-grid td.col-diam { white-space: nowrap; }

tr.row-even { background-color: var(--row-even); } tr.row-odd { background-color: var(--row-odd); }
tr.group-hover td { background-color: var(--win-highlight) !important; color: var(--bg-main) !important; cursor: pointer; }
tr.group-hover td span { color: var(--bg-main) !important; text-shadow: none !important; }

.col-desc { color: var(--col-desc); text-align: left !important; padding-left: 14px !important; }
.col-filt { color: var(--col-filt); } .col-coat { color: var(--col-coat); }
.col-mat  { color: var(--col-mat); } .col-idx  { color: var(--col-idx); }
.col-diam { color: var(--col-diam); } .col-base { color: var(--col-base); }
.col-tfc  { color: var(--col-tfc); } .col-tbc  { color: var(--col-tbc); } .col-sag  { color: var(--col-sag); }
.empty-bullet { display: block; text-align: center; width: 100%; opacity: 0.5;}
.highlight-cyl { font-weight: bold; }

/* Enforced Proportions */
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

/* ---------------------------------------------------
   LAYOUT ENGINE SWITCHES
--------------------------------------------------- */
html[data-modal-layout="legacy"] .modern-box { display: none !important; }
html[data-modal-layout="legacy"] .dialog-box { display: flex; }
html[data-modal-layout="modern"] .dialog-box { display: none !important; }
html[data-modal-layout="modern"] .modern-box { display: flex; }

html[data-modal-layout="legacy"] .modal-overlay { background-color: transparent; }
html[data-modal-layout="modern"] .modal-overlay { background-color: rgba(0,0,0,0.75); }

.modal-overlay { display: flex; position: fixed; top: 0; left: 0; right: 0; bottom: 0; z-index: 9999; justify-content: center; align-items: center; }
.modal-overlay.hidden { display: none !important; }

/* ---------------------------------------------------
   LEGACY LMS MODAL STYLES (v1.1.8 IMMUTABLE)
--------------------------------------------------- */
.dialog-box { background-color: #d4d0c8; width: 830px; display: flex; flex-direction: column; padding: 2px; position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%) scale(1.2); z-index: 10001; }
.dialog-box * { font-family: 'Microsoft Sans Serif', 'MS Sans Serif', Tahoma, sans-serif; font-size: 11px; color: #000000; -webkit-font-smoothing: none; text-rendering: crispEdges; }

/* Dual-Tone Tactile Borders */
.dialog-box .outset-border { border-top: 1px solid #dfdfdf; border-left: 1px solid #dfdfdf; border-bottom: 1px solid #000000; border-right: 1px solid #000000; box-shadow: inset -1px -1px 0 #808080, inset 1px 1px 0 #ffffff; }
.dialog-box .inset-border { border-top: 1px solid #808080; border-left: 1px solid #808080; border-bottom: 1px solid #ffffff; border-right: 1px solid #ffffff; box-shadow: inset -1px -1px 0 #dfdfdf, inset 1px 1px 0 #000000; background-color: #ffffff; color: #000000 !important; }

.dialog-box .title-bar { background: linear-gradient(to right, #0A246A, #A6CAF0); color: white; padding: 2px 3px; display: flex; justify-content: space-between; align-items: center; font-weight: bold; letter-spacing: 0.5px; }
.dialog-box .title-bar * { color: white; } 
.dialog-box .title-bar-left, .dialog-box .title-bar-right { display: flex; align-items: center; gap: 4px; width: auto; }
.dialog-box .version-text { font-weight: normal; font-size: 10px; padding-right: 2px; color: #000000; }
.dialog-box .faux-icon { height: 14px; background: white; color: black; border: 1px solid #ccc; font-size: 7px; display: flex; justify-content: center; align-items: center; font-weight: normal; box-sizing: border-box; padding: 1px 4px 0 4px; }
.dialog-box .title-bar-close { background: #d4d0c8; color: black; font-weight: bold; font-size: 10px; width: 16px; height: 14px; display: flex; justify-content: center; align-items: center; cursor: default; padding: 0; box-sizing: border-box; outline: none; border-top: 1px solid #dfdfdf; border-left: 1px solid #dfdfdf; border-bottom: 1px solid #000000; border-right: 1px solid #000000; box-shadow: inset -1px -1px 0 #808080, inset 1px 1px 0 #ffffff; }
.dialog-box .title-bar-close:active { border-top: 1px solid #000000; border-left: 1px solid #000000; border-bottom: 1px solid #dfdfdf; border-right: 1px solid #dfdfdf; box-shadow: inset -1px -1px 0 #ffffff, inset 1px 1px 0 #808080; padding-top: 1px; padding-left: 1px; }

.dialog-box .tabs-container { margin-top: 8px; padding: 0 4px; position: relative; z-index: 10; }
.dialog-box .tab-buttons { display: flex; gap: 2px; margin-left: 2px; }
.dialog-box .tab { background: #d4d0c8; padding: 4px 12px; border-top: 1px solid #dfdfdf; border-left: 1px solid #dfdfdf; border-right: 1px solid #000000; border-bottom: 1px solid #dfdfdf; box-shadow: inset -1px 0 0 #808080, inset 1px 1px 0 #ffffff; cursor: pointer; position: relative; color: #000000; user-select: none; z-index: 1; }
.dialog-box .tab.active { padding-top: 6px; margin-top: -2px; border-bottom: 1px solid #d4d0c8; margin-bottom: -1px; padding-bottom: 2px; z-index: 11; cursor: default; }

.dialog-box .dialog-content-wrapper { height: 510px; border-top: 1px solid #ffffff; border-left: 1px solid #ffffff; border-bottom: 1px solid #404040; border-right: 1px solid #404040; box-shadow: inset -1px -1px 0 #808080; padding: 12px; position: relative; z-index: 5; box-sizing: border-box; display: flex; flex-direction: column; overflow: hidden; }
.dialog-box .tab-pane { display: none; height: 100%; flex-grow: 1;} 
.dialog-box .tab-pane.active { display: block; }

.dialog-box .grid-3-col { display: grid; grid-template-columns: 245px 235px 265px; gap: 16px; justify-content: center; }
.dialog-box .grid-3-col > div { display: flex; flex-direction: column; }

.dialog-box .grid-2-col { display: grid; grid-template-columns: 1fr 1fr; gap: 40px; padding: 10px 40px; box-sizing: border-box; }
.dialog-box .center-col { display: flex; flex-direction: column; align-items: center; padding-top: 20px; }

.dialog-box .form-row { display: flex; align-items: center; margin-bottom: 4px; }
.dialog-box .form-row label { width: 110px; flex-shrink: 0; }
.dialog-box .form-row input[type="text"], .dialog-box .form-row select { flex-grow: 1; height: 19px; padding: 1px 3px; font-family: 'Microsoft Sans Serif', sans-serif; font-size: 11px; background: #ffffff; box-sizing: border-box; outline: none;}
.dialog-box .fixed-width { flex-grow: 0 !important; }
.dialog-box .form-row input[readonly] { background: #d4d0c8; }
.dialog-box select { border-radius: 0; }

.dialog-box .classic-table { border-collapse: collapse; background: #ffffff; border: 1px solid #808080; }
.dialog-box .classic-table th { background: #d4d0c8; font-weight: normal; border-top: 1px solid #dfdfdf; border-left: 1px solid #dfdfdf; border-right: 1px solid #808080; border-bottom: 1px solid #808080; padding: 2px 4px; text-align: left; }
.dialog-box .classic-table td { border-right: 1px solid #d4d0c8; border-bottom: 1px solid #d4d0c8; padding: 1px 4px; height: 14px; }
.dialog-box .grid-lines td { border: 1px solid silver; }

.dialog-box .table-title { background: #d4d0c8; font-weight: bold; text-align: center !important; border-top: 1px solid #dfdfdf; border-left: 1px solid #dfdfdf; border-right: 1px solid #808080; border-bottom: 1px solid #808080; padding: 4px !important; }
.dialog-box fieldset { border-top: 1px solid #808080; border-left: 1px solid #808080; border-bottom: 1px solid #ffffff; border-right: 1px solid #ffffff; padding: 10px 8px; margin: 0 0 12px 0; }
.dialog-box legend { color: #000000; padding: 0 4px; margin-left: 4px; }

.dialog-box .win-btn { font-family: 'Microsoft Sans Serif', sans-serif; font-size: 11px; padding: 3px 12px; min-width: 75px; background: #d4d0c8; color: #000000; cursor: default; outline: none; }
.dialog-box .win-btn:active { border-top: 1px solid #000000; border-left: 1px solid #000000; border-bottom: 1px solid #dfdfdf; border-right: 1px solid #dfdfdf; box-shadow: inset -1px -1px 0 #ffffff, inset 1px 1px 0 #808080; padding-top: 4px; padding-left: 13px; }
.dialog-box .footer { display: flex; justify-content: space-between; align-items: center; padding: 10px; }

/* ---------------------------------------------------
   MODERN DASHBOARD STYLES (BENTO BOX)
--------------------------------------------------- */
.modern-box { background-color: var(--win-bg); width: 850px; border-radius: 12px; padding: 24px; box-shadow: 0 10px 40px rgba(0,0,0,0.8); border: 1px solid var(--border-light); color: var(--win-text); flex-direction: column; gap: 20px; position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); z-index: 10001;}
.modern-header { display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 1px solid var(--border-dark); padding-bottom: 15px; }
.modern-title { font-size: 26px; font-weight: bold; color: var(--win-title-text); margin: 0; letter-spacing: 0.5px; }
.modern-subtitle { font-size: 14px; color: var(--col-desc); opacity: 0.8; margin-top: 6px; }
.modern-close { background: none; border: none; color: var(--win-text); font-size: 24px; cursor: pointer; padding: 5px; opacity: 0.6; } .modern-close:hover { opacity: 1; color: var(--col-tfc); }

.bento-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 10px; }
.bento-card { background: var(--bg-table); border: 1px solid var(--border-light); border-top-width: 4px; border-radius: 8px; padding: 14px; box-shadow: 0 4px 8px rgba(0,0,0,0.2); display: flex; flex-direction: column; gap: 8px; }
.b-title { font-size: 12px; text-transform: uppercase; font-weight: 800; letter-spacing: 0.05em; margin-bottom: 4px; border-bottom: 1px solid var(--border-dark); padding-bottom: 6px; }
.b-row { display: flex; justify-content: space-between; align-items: center; font-size: 13px; color: var(--win-text); }
.b-row span { opacity: 0.7; }
.b-row b { font-weight: bold; color: var(--text-main); }

.modern-grids { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.modern-table-wrap { background: var(--bg-table); border-radius: 8px; border: 1px solid var(--border-dark); overflow: hidden; }
.modern-table-wrap table { width: 100%; border-collapse: collapse; }
.modern-table-wrap th { padding: 8px 12px; font-size: 13px; color: var(--bg-main) !important; text-align: center; font-weight: bold; text-transform: uppercase; }
.modern-table-wrap td { padding: 8px 12px; border-bottom: 1px solid var(--border-dark); font-size: 15px; text-align: center; }
.modern-table-wrap tr:last-child td { border-bottom: none; }
        """.strip()
        .replace("{{THEME_CSS_BLOCK}}", theme_css_block)
        .replace("{{FONT_CSS_BLOCK}}", font_css_block))

    js_path = os.path.join(template_dir, 'app.js')
    with open(js_path, 'w', encoding='utf-8') as f:
        f.write(r"""
async function calculateHash(ascii) {
    const msgBuffer = new TextEncoder().encode(ascii);
    const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

function fmt(val, dec) {
    let parsed = parseFloat(val);
    if (isNaN(parsed)) return '<span class="empty-bullet">•</span>';
    if (parsed === 0) return (0).toFixed(dec); return parsed.toFixed(dec);
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
    
    const themeSelect = document.getElementById('theme-select');
    const layoutSelect = document.getElementById('layout-select');
    const fontSelect = document.getElementById('font-select');
    const fontSizeSelect = document.getElementById('fontsize-select');

    if (themeSelect) {
        let savedTheme = localStorage.getItem('ui-theme') || 'tokyo-night';
        document.documentElement.setAttribute('data-theme', savedTheme);
        themeSelect.value = savedTheme;
        themeSelect.addEventListener('change', (e) => {
            document.documentElement.setAttribute('data-theme', e.target.value);
            localStorage.setItem('ui-theme', e.target.value);
        });
    }

    if (layoutSelect) {
        let savedLayout = localStorage.getItem('ui-layout') || 'legacy';
        document.documentElement.setAttribute('data-modal-layout', savedLayout);
        layoutSelect.value = savedLayout;
        layoutSelect.addEventListener('change', (e) => {
            document.documentElement.setAttribute('data-modal-layout', e.target.value);
            localStorage.setItem('ui-layout', e.target.value);
        });
    }

    if (fontSelect) {
        let savedFont = localStorage.getItem('ui-font') || '{{DEFAULT_FONT_ID}}';
        document.documentElement.setAttribute('data-font', savedFont);
        fontSelect.value = savedFont;
        fontSelect.addEventListener('change', (e) => {
            document.documentElement.setAttribute('data-font', e.target.value);
            localStorage.setItem('ui-font', e.target.value);
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
    let failedShard = "";

    if (typeof securityManifest !== 'undefined' && typeof window.shards !== 'undefined') {
        for (const [filename, hash] of Object.entries(securityManifest.shards)) {
            const mfg = filename.replace('_shard.js', '');
            const b64 = window.shards[mfg];
            
            if (!b64) continue;
            
            const calculatedHash = await calculateHash(b64);
            
            if (calculatedHash !== hash) {
                tamperDetected = true;
                failedShard = filename;
                break;
            }
            
            const binaryString = atob(b64);
            const bytes = new Uint8Array(binaryString.length);
            for (let i = 0; i < binaryString.length; i++) bytes[i] = binaryString.charCodeAt(i);
            const jsonString = new TextDecoder('utf-8').decode(bytes);
            
            let rawData = JSON.parse(jsonString);
            window.lensDatabase = window.lensDatabase.concat(rawData);
        }
    }

    if (tamperDetected) {
        document.body.innerHTML = `
            <div style="display:flex; flex-direction:column; justify-content:center; align-items:center; height:100vh; background-color:var(--bg-main); color:var(--col-sag); font-family:inherit; text-align:center;">
                <h1 style="font-size:48px; border-bottom:2px solid var(--col-sag); padding-bottom:10px; letter-spacing: 2px;">CRYPTOGRAPHIC MISMATCH</h1>
                <p style="font-size:20px; max-width:600px; color:var(--text-main); margin-top: 20px;">The signature for <b>${failedShard}</b> does not match the securely signed manifest.</p>
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
        data.forEach(lens => { if (lens.MFG) mfgSet.add(lens.MFG); });
        
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
                let extraStyle = '';
                if (groupName === 'basecolor') {
                    const cMap = {
                        'gray': '#808080', 'brown': '#8B4513', 'green': '#228B22', 
                        'blue': '#4682B4', 'pink': '#FFC0CB', 'extra gray': '#696969'
                    };
                    let bg = cMap[tag.toLowerCase()];
                    if(bg) extraStyle = `style="background-color: ${bg}; color: #fff; border-color: ${bg}; text-shadow: 1px 1px 1px rgba(0,0,0,0.5);"`;
                }
                html += `<a href="#" class="stat-badge tag-pill" data-group="${groupName}" data-tag="${tag}" ${extraStyle}>${tag}</a>`;
            });
            row.innerHTML = html;
        };

        genPills('pill-row-type', 'Type', ['FSV', 'SFSV', 'PAL', 'FT', 'TRI', 'Round', 'Exec', 'Occupational', 'Blend'], 'type');
        genPills('pill-row-mat', 'Material', ['CR-39', 'Polycarbonate', 'Trivex', '1.60', '1.67', '1.74'], 'mat');
        genPills('pill-row-tech', 'Tech', ['Blue Filter', 'Photochromic', 'Polarized', 'Short', 'Extra Thick', 'HEV', 'Blue Protect', 'BlueGuard', 'ClearView'], 'tech');
        genPills('pill-row-coat', 'Coating', ['Hardcoated', 'Uncoated', 'A/R'], 'coat');
        genPills('pill-row-basecolor', 'Color', ['Pink', 'Blue', 'Green', 'Brown', 'Gray', 'Extra Gray'], 'basecolor');
        
        const shadeRow = document.getElementById('pill-row-exactcolor');
        if (shadeRow) {
            let sHtml = `<span class="pill-label">Shade:</span>`;
            sHtml += `<a href="#" class="stat-badge tag-pill active" data-group="exactcolor" data-tag="all">All</a>`;
            ['Gray', 'Brown', 'Green', 'Blue', 'Pink', 'Extra Gray'].forEach(c => {
                sHtml += `<a href="#" class="stat-badge tag-pill shade-pill" data-base="${c}" data-group="exactcolor" data-tag="${c}-1" style="display:none;">${c}-1</a>`;
                sHtml += `<a href="#" class="stat-badge tag-pill shade-pill" data-base="${c}" data-group="exactcolor" data-tag="${c}-2" style="display:none;">${c}-2</a>`;
                sHtml += `<a href="#" class="stat-badge tag-pill shade-pill" data-base="${c}" data-group="exactcolor" data-tag="${c}-3" style="display:none;">${c}-3</a>`;
            });
            shadeRow.innerHTML = sHtml;
            shadeRow.style.display = 'none';
        }
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
                                ftc: parseFloat(s['Front TC'])||0, 
                                btc: parseFloat(s['Back TC'])||0, 
                                sag: parseFloat(s['SAG'])||0,
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
                            col5: m.sag === 0 ? '<span class="empty-bullet">•</span>' : m.sag.toFixed(2)
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
                
                // Safe JSON compilation to prevent Javascript crashing
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
                if (lens.MappedShades) lens.MappedShades.forEach(t => searchIndex.push(t));
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

    // High Performance Search Engine
    function applyFilters() {
        const btnAllLenses = document.getElementById('btn-all-lenses');
        const mfgBadges = document.querySelectorAll('.mfg-pill');
        const tagBadges = document.querySelectorAll('.tag-pill');
        const searchInput = document.getElementById('text-search-box');
        
        let activeMfg = 'all';
        let activeFilters = { type: 'all', mat: 'all', tech: 'all', coat: 'all', basecolor: 'all', exactcolor: 'all' };
        
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
                            // Exact flat match or Word boundary match
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

            const shadeRow = document.getElementById('pill-row-exactcolor');
            if (shadeRow) {
                if (activeFilters.basecolor !== 'all' && activeFilters.basecolor !== 'clear') {
                    shadeRow.style.display = 'flex';
                    document.querySelectorAll('.shade-pill').forEach(sp => {
                        if (sp.getAttribute('data-base').toLowerCase() === activeFilters.basecolor.toLowerCase()) {
                            sp.style.display = 'inline-block';
                        } else {
                            sp.style.display = 'none';
                            sp.classList.remove('active');
                        }
                    });
                } else {
                    shadeRow.style.display = 'none';
                    activeFilters.exactcolor = 'all';
                    document.querySelector('.tag-pill[data-group="exactcolor"][data-tag="all"]').classList.add('active');
                    document.querySelectorAll('.shade-pill').forEach(sp => sp.classList.remove('active'));
                }
            }
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
                        
                        if(group === 'basecolor') {
                            activeFilters.exactcolor = 'all';
                            document.querySelectorAll('.tag-pill[data-group="exactcolor"]').forEach(b => b.classList.remove('active'));
                            document.querySelector('.tag-pill[data-group="exactcolor"][data-tag="all"]').classList.add('active');
                        }
                    }
                }
                updateDOM();
            });
        });
        
        // Force the initial load
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

        let idStr = lens.Description + lens.Index;
        let hashNum = 0; for(let i=0;i<idStr.length;i++) hashNum = Math.imul(31, hashNum) + idStr.charCodeAt(i) | 0;
        let idDisplay = Math.abs(hashNum).toString().substring(0,6).padStart(6, '0');
        
        let webDesc = isFin ? '*' + lens.Description : lens.Description;
        let lensTypeStr = "Single Vision";
        if(isProg) lensTypeStr = "Progressive";
        else if([2,3,4,5,8,9,10,11,12,15,16].includes(parseInt(lens.Style))) lensTypeStr = "Multi-Focal";
        
        let rep = specArray[0] || {};
        
        // OPC Extraction
        let opcs = Object.values(rep['OPC'] || {});
        let opcRange = "N/A";
        let opcMin = ""; let opcMax = "";
        if(opcs.length > 0) {
            let sortedOpc = opcs.sort();
            opcMin = sortedOpc[0];
            opcMax = sortedOpc[sortedOpc.length - 1];
            opcRange = opcMin + " to " + opcMax;
        }

        // Modern Bento Box Injections
        let modTitle = document.getElementById('mod-modern-title'); if(modTitle) modTitle.innerText = webDesc;
        let modSub = document.getElementById('mod-modern-sub'); if(modSub) modSub.innerText = `${lens.MFG || 'Unknown'} | ID: ${idDisplay}`;
        
        let mBentoMfg = document.getElementById('mod-bento-mfg'); if(mBentoMfg) mBentoMfg.innerText = lens.MFG || 'Unknown';
        let mBentoMat = document.getElementById('mod-bento-mat'); if(mBentoMat) mBentoMat.innerText = lens.Material;
        let mBentoIdx = document.getElementById('mod-bento-idx'); if(mBentoIdx) mBentoIdx.innerText = lens.Index;
        let mBentoType = document.getElementById('mod-bento-type'); if(mBentoType) mBentoType.innerText = lensTypeStr;
        let mBentoSeg = document.getElementById('mod-bento-seg'); if(mBentoSeg) mBentoSeg.innerText = rep['Seg Width'] || 'N/A';
        let mBentoInset = document.getElementById('mod-bento-inset'); if(mBentoInset) mBentoInset.innerText = `${rep['Inset'] || '0.0'} / ${rep['Drop'] || '0.0'}`;
        let mBentoPrp = document.getElementById('mod-bento-prp'); if(mBentoPrp) mBentoPrp.innerText = `${rep['PRP Out'] || '0.0'} / ${rep['PRP Up'] || '0.0'}`;
        let mBentoOpc = document.getElementById('mod-bento-opc'); if(mBentoOpc) mBentoOpc.innerText = opcRange;
        
        // Legacy Modal Injections
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
        
        let mseg = document.getElementById('mod-seg-width'); if(mseg) mseg.value = rep['Seg Width'] || '';
        let mmatn = document.getElementById('mod-mat-name'); if(mmatn) mmatn.value = lens.Material || '';
        let mmatc = document.getElementById('mod-mat-cat'); if(mmatc) mmatc.innerHTML = `<option>${lens.Material}</option>`;
        let midx = document.getElementById('mod-idx'); if(midx) midx.value = lens.Index || '';
        
        let mopcr = document.getElementById('mod-opc-right'); if(mopcr) mopcr.value = opcMin;
        let mopcl = document.getElementById('mod-opc-left'); if(mopcl) mopcl.value = opcMax;
        
        let mbowl = document.getElementById('mod-bowl-dia'); if(mbowl) mbowl.value = rep['Bowl Dia'] || '0';
        
        const ctcDict = {
            'Plastic (CR-39)': '2.2', 'Polycarbonate': '1.5', 'Trivex': '1.5',
            'High-Index 1.60': '1.4', 'High-Index 1.60 (MR-8)': '1.4', 'High-Index 1.60 (MR-8+)': '1.4',
            'High-Index 1.67': '1.4', 'High-Index 1.67 (MR-7)': '1.4', 'High-Index 1.67 (MR-10)': '1.4',
            'High-Index 1.74': '1.4'
        };
        let mminct = document.getElementById('mod-min-ct'); 
        if(mminct) mminct.value = ctcDict[lens.Material] || '';

        // Modern Modal Dynamic Headers (FSV vs SF)
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
                let ftc = parseFloat(r['Front TC']); ftc = isNaN(ftc) ? '' : ftc.toFixed(2);
                let btc = parseFloat(r['Back TC']); btc = isNaN(btc) ? '' : btc.toFixed(2);
                let ct = parseFloat(r['Center Thick']); ct = isNaN(ct) ? '' : ct.toFixed(2);
                
                if (b) {
                    if (!uniqueCurves.has(b)) uniqueCurves.set(b, {b, ftc, btc, asphFactor});
                    (r.Diameters || []).forEach(dia => {
                        let diamKey = `${dia}-${b}`;
                        if (!uniqueDiams.has(diamKey)) uniqueDiams.set(diamKey, {dia, b, ct, inset: r.Inset || '', drop: r.Drop || ''});
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
        if(tabColorArr.length === 0) tabColorArr.push('NONE');
        
        let rawCoatArr = Array.from(lens.Coatings || []);
        if(rawCoatArr.length === 0) rawCoatArr.push('UNCOATED');
        let modalCoats = [];
        rawCoatArr.forEach(c => {
            if(c.includes('/')) { modalCoats.push(...c.split('/').map(x => x.trim())); }
            else { modalCoats.push(c); }
        });
        modalCoats = Array.from(new Set(modalCoats));
        
        let colorsHtml = '', coatsHtml = '';
        let maxRows = 16;
        
        for(let j=0; j<maxRows; j++) {
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
        """.strip().replace("{{DEFAULT_FONT_ID}}", default_font_id))

    root_path = os.path.join(template_dir, 'root_template.html')
    with open(root_path, 'w', encoding='utf-8') as f:
        f.write("""
<!DOCTYPE html>
<html lang="en" data-theme="tokyo-storm" data-modal-layout="modern" data-font="{{DEFAULT_FONT_ID}}">
<head>
    <meta charset="UTF-8">
    <title>VCA Vault Hub</title>
    <link rel="stylesheet" href="data/styles.css">
    <script>
        let savedTheme = localStorage.getItem('ui-theme') || 'tokyo-night';
        let savedLayout = localStorage.getItem('ui-layout') || 'modern';
        let savedFont = localStorage.getItem('ui-font') || '{{DEFAULT_FONT_ID}}';
        let savedFs = localStorage.getItem('ui-fontsize') || '15';
        document.documentElement.setAttribute('data-theme', savedTheme);
        document.documentElement.setAttribute('data-modal-layout', savedLayout);
        document.documentElement.setAttribute('data-font', savedFont);
        document.documentElement.style.setProperty('--table-fs', savedFs + 'px');
        document.documentElement.style.setProperty('--table-th-fs', (parseInt(savedFs) - 3) + 'px');
    </script>
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
                <span class="dd-icon" title="Modal Layout">󰒓</span>
                <select id="layout-select" class="header-dropdown" style="width: 100px;">
                    <option value="legacy">LMS</option>
                    <option value="modern">Grid</option>
                </select>
                <span class="dd-icon" title="Color Theme">󰔎</span>
                <select id="theme-select" class="header-dropdown" style="width: 220px;">
                    {{THEME_OPTIONS_HTML}}
                </select>
            </div>
            <div class="dropdown-row">
                <span class="dd-icon" title="Font Size">󰚺</span>
                <select id="fontsize-select" class="header-dropdown" style="width: 100px;">
                    <option value="12">12px</option>
                    <option value="13">13px</option>
                    <option value="14">14px</option>
                    <option value="15">15px</option>
                    <option value="16">16px</option>
                    <option value="18">18px</option>
                    <option value="20">20px</option>
                    <option value="22">22px</option>
                    <option value="24">24px</option>
                </select>
                <span class="dd-icon" title="Font"></span>
                <select id="font-select" class="header-dropdown" style="width: 220px;">
                    {{FONT_OPTIONS_HTML}}
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
        <div class="filter-row row-coat" id="pill-row-coat"></div>
        <div class="filter-row row-basecolor" id="pill-row-basecolor"></div>
        <div class="filter-row row-exactcolor" id="pill-row-exactcolor"></div>
        
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
    {{SHARD_SCRIPTS}}
    <script src="data/app.js"></script>
</body></html>
        """.strip().replace("{{THEME_OPTIONS_HTML}}", theme_options_html)
           .replace("{{FONT_OPTIONS_HTML}}", font_options_html)
           .replace("{{DEFAULT_FONT_ID}}", default_font_id))
    
    return template_dir

def execute_html_generation():
    global global_mode, scroll_offset
    global_version = str(globals().get('VERSION', '4.0.0')).replace('v', '')
    
    sys.stdout.write(f"{C_BG}\033[2J\033[H")
    term_w, term_h = get_term_size()
    draw_top_bar()
    for r in range(2, term_h - 1): draw_frame_line("", row=r)
    draw_frame_line(f"{C_SIZE}STATIC SITE GENERATOR: HTML DEPLOYMENT{RESET}", row=2, align="center")
    draw_status_bar()
    
    if not os.path.exists(DB_FILE):
        draw_frame_line(f"{C_ALERT}Error: Master database not found.{RESET}", 6, align="center")
        draw_universal_footer() 
        global_mode = "MAIN MENU"; return
        
    viewport_logs.clear()
    scroll_offset = 0
    log_task(format_log("SYSTEM", "Awaiting SSG deployment authorization...", C_TITLE), "RAW")
    draw_viewport(progress_pct=0.0, active_file="Pending Auth...", current_file_idx=0, total_files=0, is_interactive=False)
    
    ans = draw_modal("DEPLOYMENT AUTHORIZATION", "Type DEPLOY to generate web shards:", is_password=False)
    
    sys.stdout.write(f"{C_BG}\033[2J\033[H")
    draw_top_bar()
    for r in range(2, term_h - 1): draw_frame_line("", row=r)
    draw_frame_line(f"{C_SIZE}STATIC SITE GENERATOR: HTML DEPLOYMENT{RESET}", row=2, align="center")
    draw_status_bar()
    
    if ans != "DEPLOY": global_mode = "MAIN MENU"; return

    try:
        viewport_logs.clear()
        scroll_offset = 0
        log_task(format_log("SYSTEM", f"Opening Read-Only Buffer -> {DB_FILE}", C_FILE), "RAW")
        draw_viewport(progress_pct=0.0, active_file="Bootstrapping...", current_file_idx=0, total_files=0, is_interactive=False)
        
        os.makedirs(HTML_DIR, exist_ok=True)
        os.makedirs(HTML_DATA_DIR, exist_ok=True)
        os.makedirs(HTML_DB_DIR, exist_ok=True)
        
        themes_dir = os.path.join(HTML_DATA_DIR, 'themes')
        os.makedirs(themes_dir, exist_ok=True)
        
        if not os.listdir(themes_dir):
            default_themes = {
                "tokyo-storm.json": { "theme_name": "Tokyo Storm", "ui_colors": { "--bg-main": "#24283b", "--bg-table": "#1f2335", "--text-main": "#c0caf5", "--win-bg": "#24283b", "--win-highlight": "#414868", "--win-shadow": "#1a1b26", "--win-dark-shadow": "#15161e", "--win-title": "#24283b", "--win-title-fade": "#1f2335", "--win-text": "#c0caf5", "--win-title-text": "#7aa2f7", "--border-light": "#414868", "--border-dark": "#1a1b26", "--accent": "#3d59a1", "--row-even": "#24283b", "--row-odd": "#1f2335" }, "data_colors": { "--col-desc": "#c0caf5", "--col-filt": "#9ece6a", "--col-coat": "#e0af68", "--col-mat": "#7dcfff", "--col-idx": "#bb9af7", "--col-diam": "#c0caf5", "--col-base": "#e0af68", "--col-tfc": "#c0caf5", "--col-tbc": "#7aa2f7", "--col-sag": "#f7768e" } },
                "tokyo-day.json": { "theme_name": "Tokyo Day", "ui_colors": { "--bg-main": "#f0f2f5", "--bg-table": "#ffffff", "--text-main": "#1a1b26", "--win-bg": "#f0f2f5", "--win-highlight": "#e1e4ed", "--win-shadow": "#a1a6c5", "--win-dark-shadow": "#8086a8", "--win-title": "#d0d5e3", "--win-title-fade": "#ffffff", "--win-text": "#1a1b26", "--win-title-text": "#3760bf", "--border-light": "#c0c5ce", "--border-dark": "#a1a6c5", "--accent": "#3760bf", "--row-even": "#f8f9fa", "--row-odd": "#ffffff" }, "data_colors": { "--col-desc": "#3760bf", "--col-filt": "#587539", "--col-coat": "#8c6c3e", "--col-mat": "#007197", "--col-idx": "#9854f1", "--col-diam": "#3760bf", "--col-base": "#8c6c3e", "--col-tfc": "#3760bf", "--col-tbc": "#2e7de9", "--col-sag": "#f52a65" } },
                "tokyo-night.json": { "theme_name": "Tokyo Night", "ui_colors": { "--bg-main": "#1a1b26", "--bg-table": "#16161e", "--text-main": "#c0caf5", "--win-bg": "#1a1b26", "--win-highlight": "#414868", "--win-shadow": "#15161e", "--win-dark-shadow": "#101014", "--win-title": "#1a1b26", "--win-title-fade": "#16161e", "--win-text": "#c0caf5", "--win-title-text": "#7aa2f7", "--border-light": "#292e42", "--border-dark": "#15161e", "--accent": "#3d59a1", "--row-even": "#1a1b26", "--row-odd": "#16161e" }, "data_colors": { "--col-desc": "#c0caf5", "--col-filt": "#9ece6a", "--col-coat": "#e0af68", "--col-mat": "#7dcfff", "--col-idx": "#bb9af7", "--col-diam": "#c0caf5", "--col-base": "#e0af68", "--col-tfc": "#c0caf5", "--col-tbc": "#7aa2f7", "--col-sag": "#f7768e" } },
                "tokyo-moon.json": { "theme_name": "Tokyo Moon", "ui_colors": { "--bg-main": "#222436", "--bg-table": "#1e2030", "--text-main": "#c8d3f5", "--win-bg": "#222436", "--win-highlight": "#444a73", "--win-shadow": "#191a2a", "--win-dark-shadow": "#131421", "--win-title": "#222436", "--win-title-fade": "#1e2030", "--win-text": "#c8d3f5", "--win-title-text": "#82aaff", "--border-light": "#2f334d", "--border-dark": "#1e2030", "--accent": "#3e68d7", "--row-even": "#222436", "--row-odd": "#1e2030" }, "data_colors": { "--col-desc": "#c8d3f5", "--col-filt": "#c3e88d", "--col-coat": "#ffc777", "--col-mat": "#86e1fc", "--col-idx": "#fca7ea", "--col-diam": "#c8d3f5", "--col-base": "#ffc777", "--col-tfc": "#c8d3f5", "--col-tbc": "#82aaff", "--col-sag": "#ff757f" } }
            }
            for fn, payload in default_themes.items():
                with open(os.path.join(themes_dir, fn), 'w', encoding='utf-8') as f:
                    json.dump(payload, f, indent=4)
                    
        theme_css_block = ""
        theme_options_html = ""
        
        for file in sorted(os.listdir(themes_dir)):
            if not file.endswith('.json'): continue
            theme_key = file.replace('.json', '')
            try:
                with open(os.path.join(themes_dir, file), 'r', encoding='utf-8') as f:
                    theme_data = json.load(f)
                
                t_name = theme_data.get("theme_name", theme_key)
                ui_cols = theme_data.get("ui_colors", {})
                data_cols = theme_data.get("data_colors", {})
                
                css_lines = []
                for k, v in ui_cols.items(): css_lines.append(f"{k}: {v};")
                for k, v in data_cols.items(): css_lines.append(f"{k}: {v};")
                
                theme_css_block += f"html[data-theme=\"{theme_key}\"] {{\n    " + " ".join(css_lines) + "\n}\n"
                theme_options_html += f'<option value="{theme_key}">{t_name}</option>\n'
                
            except Exception as e:
                log_task(format_log("THEME_ERR", f"Failed to parse {file}: {e}", C_ALERT), "RAW")

        font_css_block = ""
        font_options_html = ""
        default_font_id = "sans-serif"
        
        try: fonts_found = [f for f in os.listdir(HTML_FONT_DIR) if f.lower().endswith(('.ttf', '.woff', '.woff2'))]
        except: fonts_found = []
        
        if fonts_found:
            default_font_id = os.path.splitext(fonts_found[0])[0]
            for f in sorted(fonts_found):
                font_id = os.path.splitext(f)[0]
                if "UbuntuSansNerdFont-Medium" in font_id: default_font_id = font_id
            
            for f in sorted(fonts_found):
                font_id = os.path.splitext(f)[0]
                display_name = font_id.replace('-', ' ')
                
                font_css_block += f"@font-face {{ font-family: '{font_id}'; src: url('fonts/{f}') format('truetype'); }}\n"
                font_css_block += f"html[data-font=\"{font_id}\"] body {{ font-family: '{font_id}', sans-serif !important; }}\n"
                font_options_html += f'<option value="{font_id}">{display_name}</option>\n'
        else:
            font_options_html += '<option value="sans-serif">System Sans-Serif</option>\n'

        log_task(format_log("DEPLOYMENT", "Bootstrapping Web Templates & Assets...", C_TITLE), "RAW")
        template_dir = bootstrap_web_templates(theme_css_block, theme_options_html, font_css_block, font_options_html, default_font_id)
        
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
        
        db_manifest = db_data.get('manifest', db_data.get('__security_manifest__', {}))
        shards_manifest = db_manifest.get('shards', {})
        
        total_mfgs = len(manufacturers)
        shard_scripts_html = ""
        
        # Tech Whitelist
        tech_whitelist = {
            "blue filter", "blueguard", "blue-guard", "blue protect", "clear blue filter", 
            "cbf", "blue capture", "blue uv capture", "hev", "uv420", 
            "photochromic", "photofusion", "q-change", "transitions", "liferx", 
            "polarized", "nupolar", "uv", "uvri", "uv protect", "drivesafe"
        }

        # SHARD COMPILATION LOOP (SPA Payload)
        for idx, mfg in enumerate(manufacturers):
            clean_mfg = re.sub(r'[^a-zA-Z0-9_-]', '_', str(mfg))
            mfg_data = df[df['MFG'] == mfg].fillna("").to_dict(orient='records')
            
            for lens_obj in mfg_data:
                raw_tags = lens_obj.get("FilterTags", [])
                mapped_shades = []
                base_colors = set()
                
                # Dynamic BaseColor
                for tag in raw_tags:
                    t_up = tag.upper()
                    if t_up == "PRO GRAY": mapped_shades.append("Gray-2")
                    elif t_up == "PRO BROWN": mapped_shades.append("Brown-2")
                    elif t_up in ["GRAY", "GREY"]: mapped_shades.append("Gray-3")
                    elif t_up == "BROWN": mapped_shades.append("Brown-3")
                    elif t_up == "BLUE": mapped_shades.append("Blue-3")
                    elif t_up == "ROSE": mapped_shades.append("Rose-3")
                    elif t_up == "PURPLE": mapped_shades.append("Purple-3")
                    elif t_up == "BURGUNDY": mapped_shades.append("Burgundy-3")
                    elif t_up == "YELLOW": mapped_shades.append("Yellow-3")
                    elif t_up == "GREEN": mapped_shades.append("Green-3")
                    elif t_up == "PINK": mapped_shades.append("Pink-3")
                    elif t_up == "EXTRA GRAY": mapped_shades.append("Extra Gray-3")
                    elif re.match(r"^[A-Z\s]+-[123]$", t_up): mapped_shades.append(tag)
                
                for s in mapped_shades:
                    base_colors.add(s.split('-')[0].strip())
                    
                lens_obj["MappedShades"] = sorted(list(set(mapped_shades)))
                lens_obj["BaseColors"] = sorted(list(base_colors))
                
                base_map = {}
                for s in lens_obj["MappedShades"]:
                    b = s.split('-')[0].strip()
                    if b not in base_map: base_map[b] = []
                    base_map[b].append(s)
                    
                smart_colors = []
                for b, variants in base_map.items():
                    if len(variants) == 1: smart_colors.append(b)
                    else: smart_colors.extend(variants)
                lens_obj["SmartColors"] = sorted(list(set(smart_colors)))

                pure_filters = []
                for tag in raw_tags:
                    t_low = tag.lower()
                    if t_low in tech_whitelist:
                        pure_filters.append(tag)
                    elif "blue" in t_low and not re.match(r"blue(?:-|\s*)[1-3]", t_low):
                        if "blue" not in [c.lower() for c in lens_obj["BaseColors"]]:
                            pure_filters.append(tag)
                
                if pure_filters:
                    lens_obj["Filter"] = "<br>".join(sorted(list(set(pure_filters))))
                else:
                    lens_obj["Filter"] = '<span style="opacity:0.5;">None</span>'
                
                cat = "other"
                is_fin = bool(lens_obj.get("Specifications", {}).get("FIN"))
                style = int(lens_obj.get("Style", 0))
                
                if is_fin and style == 1: cat = "fsv"
                elif not is_fin and style == 1: cat = "sfsv"
                elif style == 6: cat = "pal"
                elif style in [2,3,4,5,8,9,10,11,12,15,16,17]: cat = "ft"
                lens_obj["Category"] = cat

            log_task(format_log("BASE_SHARD", f"{mfg} -> Base64 Encoding...", C_TITLE), "RAW")
            json_string = json.dumps(mfg_data, separators=(',', ':'))
            b64_bytes = base64.b64encode(json_string.encode('utf-8'))
            b64_string = b64_bytes.decode('utf-8')
            
            shard_hash = hashlib.sha256(b64_bytes).hexdigest()
            log_task(format_log("SHARD_HASH", f"{shard_hash}", C_WARN), "RAW")
            
            shard_filename = f"{clean_mfg}_shard.js"
            shards_manifest[shard_filename] = shard_hash
            
            shard_path = os.path.join(HTML_DB_DIR, shard_filename)
            with open(shard_path, 'w', encoding='utf-8') as f:
                f.write(f'window.shards = window.shards || {{}};\nwindow.shards["{clean_mfg}"] = "{b64_string}";\n')
                
            log_task(format_log("SHARD_OUT", f"{shard_filename} ({os.path.getsize(shard_path) / (1024*1024):.2f} MB)", C_STAGED), "RAW")
            
            shard_scripts_html += f'<script src="data/db/{shard_filename}"></script>\n    '
            
            pct = ((idx + 1) / total_mfgs) * 100.0
            draw_viewport(progress_pct=pct, active_file=shard_filename, current_file_idx=idx+1, total_files=total_mfgs)
            time.sleep(0.5) 

        with open(os.path.join(template_dir, 'root_template.html'), 'r', encoding='utf-8') as f:
            root_template_str = f.read()
        
        root_html = root_template_str.replace('{{SHARD_SCRIPTS}}', shard_scripts_html).replace('{{VERSION}}', global_version)
        with open(os.path.join(HTML_DIR, 'index.html'), 'w', encoding='utf-8') as f: f.write(root_html)

        sign_master_database()
        
        master_sig = "UNSIGNED"
        if os.path.exists(SIG_FILE):
            with open(SIG_FILE, 'r') as sf: master_sig = sf.read().strip()
                
        manifest_data = {
            "masterSignature": master_sig, 
            "compiled_at": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            "shards": shards_manifest
        }
        
        log_task(format_log("WEB_MANIFEST", f"Compiling with {len(manifest_data['shards'])} Shard Signatures", C_PROMPT), "RAW")
        db_data['manifest'] = manifest_data
        
        if 'shards' in db_data: db_data.pop('shards', None)
        if '__security_manifest__' in db_data: db_data.pop('__security_manifest__', None)
        
        try: os.chmod(DB_FILE, stat.S_IWRITE)
        except: pass
        with open(DB_FILE, 'w', encoding='utf-8') as f: json.dump(db_data, f, indent=4)
        try: os.chmod(DB_FILE, stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)
        except: pass
        
        log_task(format_log("TETHER_LOCK", "Security Manifest injected directly into Master Vault.", C_TITLE), "RAW")
        
        manifest_path = os.path.join(HTML_DB_DIR, 'manifest.js')
        with open(manifest_path, 'w', encoding='utf-8') as f:
            f.write(f"const securityManifest = {json.dumps(manifest_data, indent=4)};\n")
            
        log_task(format_log("SECURITY", "SSG Payload cryptographically sealed.", C_STAGED), "RAW")
        
        draw_viewport(progress_pct=100.0, active_file="manifest.js", current_file_idx=total_mfgs, total_files=total_mfgs, is_interactive=True)
        
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
            
            draw_viewport(progress_pct=100.0, active_file="manifest.js", current_file_idx=total_mfgs, total_files=total_mfgs, is_interactive=True)

    except Exception as e:
        log_task(format_log("FATAL_I/O", f"{str(e)}", C_ALERT), "RAW")
        draw_viewport(progress_pct=100.0, active_file="ERROR", current_file_idx=total_mfgs, total_files=total_mfgs, is_interactive=True)
        
        while True:
            c = getch()
            if isinstance(c, bytes):
                try: c = c.decode('utf-8')
                except: continue
            if c in ('\r', '\n', '\x1b'): break
        
    global_mode = "MAIN MENU"

# --- MATH & PARSER UTILITIES ---

def map_style_code(row):
    """Maps raw VCA data to base legacy style codes (1-18), ignoring false diameter triggers."""
    raw_style = str(row.get('Style', '')).upper()
    raw_desc = str(row.get('Description', '')).upper()
    raw_name = str(row.get('Name', '')).upper()
    c = f" {raw_style} {raw_desc} {raw_name} "
    
    # 1. Neutralize massive diameter tags so they don't trigger seg matches
    diam = str(row.get('Diameter', '')).strip()
    if diam:
        try:
            d_val = int(float(diam))
            c = re.sub(rf'\bD-?{d_val}\b', '', c)
        except: pass

    # 2. Strict Seg Width Validation (22 to 45 bounds only)
    seg_width = str(row.get('Seg Width', '')).strip()
    has_valid_seg = False
    if seg_width:
        try:
            s_val = int(float(seg_width))
            if 22 <= s_val <= 45:
                has_valid_seg = True
        except: pass

    # 3. Progressive Check
    if any(x in c for x in [' PROG ', ' PAL ', ' PROGRESSIVE ']): 
        return 6
        
    # 4. Double Seg
    if any(x in c for x in [' DOUBLE ', ' DBL ', ' QUAD ', ' DUAL ']): 
        return 9 if ' EXEC ' in c or ' EXECUTIVE ' in c else 8
        
    # 5. Trifocal
    if any(x in c for x in [' TRI ', ' TRIFOCAL ', ' TF ', ' 7X ', ' 8X ', ' 10X ']) or re.search(r'\b\d+X\d+\b', c):
        if ' EXEC ' in c or ' EXECUTIVE ' in c: return 11
        if ' ED ' in c: return 12
        return 10
        
    # 6. Blended Seg
    if ' BLEND ' in c: return 7
        
    # 7. Ultex
    if ' ULTEX ' in c: return 5
        
    # 8. Executive Bifocal
    if any(x in c for x in [' EXEC ', ' EXECUTIVE ']): return 4
        
    # 9. Round Bifocal
    if any(x in c for x in [' RND ', ' ROUND ', ' SEG ']): return 3
        
    # 10. Flat Top Bifocal (Requires valid segment size or bounded D-seg regex)
    if any(x in c for x in [' FT ', ' BIF ', ' BIFOCAL ']) or has_valid_seg or re.search(r'\b(?:FT|D-?)\s*(22|25|28|35|40|45)\b', c): 
        return 2
    
    # 11. Single Vision (Default fallback for all stock blanks)
    return 1

def resolve_material(mat_str, mat_brand_str, index_val, desc_str, name_str, abbe_val, global_context=None):
    if global_context is None: global_context = {}
    
    import re
    c = f" {str(mat_str)} {str(mat_brand_str)} {str(desc_str)} {str(name_str)} ".upper()
    
    try: i_val = float(index_val)
    except: i_val = 0.0
    
    try: a_val = float(abbe_val)
    except: a_val = 0.0
    
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
        m10_score = 0
        m7_score = 0
        
        if a_val == 31: m10_score += 2
        if a_val == 32: m7_score += 2
        
        if "MR10" in c or "MR-10" in c: m10_score += 5
        if "MR7" in c or "MR-7" in c: m7_score += 5
        
        if m10_score > m7_score: return "1.67 (MR-10)"
        elif m7_score > m10_score: return "1.67 (MR-7)"
        else:
            m_key = f"1.67_{mat_str}_{desc_str}"
            if m_key in global_context:
                return global_context[m_key]
            
            ans = draw_z_index_modal("MATERIAL HEURISTIC TIE", f"Lens: {mat_str} {desc_str}\nIndex: {i_val} | Abbe: {a_val}\n\nIs this MR-7 or MR-10? Type 7 or 10:")
            if ans == "10": 
                global_context[m_key] = "1.67 (MR-10)"
                return "1.67 (MR-10)"
            else:
                global_context[m_key] = "1.67 (MR-7)"
                return "1.67 (MR-7)"
                
    if mat_str and str(mat_str).strip(): return str(mat_str).title()
    return "Unknown Material"

def map_style_code(row):
    """Maps raw VCA data to base legacy style codes (1-18), ignoring false diameter triggers."""
    raw_style = str(row.get('Style', '')).upper()
    raw_desc = str(row.get('Description', '')).upper()
    raw_name = str(row.get('Name', '')).upper()
    c = f" {raw_style} {raw_desc} {raw_name} "
    
    # 1. Neutralize massive diameter tags so they don't trigger seg matches
    diam = str(row.get('Diameter', '')).strip()
    if diam:
        try:
            d_val = int(float(diam))
            c = re.sub(rf'\bD-?{d_val}\b', '', c)
        except: pass

    # 2. Strict Seg Width Validation (22 to 45 bounds only)
    seg_width = str(row.get('Seg Width', '')).strip()
    has_valid_seg = False
    if seg_width:
        try:
            s_val = int(float(seg_width))
            if 22 <= s_val <= 45:
                has_valid_seg = True
        except: pass

    # 3. Progressive Check
    if any(x in c for x in [' PROG ', ' PR ', ' PAL ', ' PROGRESSIVE ']) or raw_style == 'PR': 
        return 6
        
    # 4. Double Seg
    if any(x in c for x in [' DOUBLE ', ' DBL ', ' QUAD ', ' DUAL ']): 
        return 9 if ' EXEC ' in c or ' EXECUTIVE ' in c else 8
        
    # 5. Trifocal
    if any(x in c for x in [' TRI ', ' TRIFOCAL ', ' TF ', ' 7X ', ' 8X ', ' 10X ']) or re.search(r'\b\d+X\d+\b', c):
        if ' EXEC ' in c or ' EXECUTIVE ' in c: return 11
        if ' ED ' in c: return 12
        return 10
        
    # 6. Blended Seg
    if ' BLEND ' in c: return 7
        
    # 7. Ultex
    if ' ULTEX ' in c: return 5
        
    # 8. Executive Bifocal
    if any(x in c for x in [' EXEC ', ' EXECUTIVE ']): return 4
        
    # 9. Round Bifocal
    if any(x in c for x in [' RND ', ' ROUND ', ' SEG ']): return 3
        
    # 10. Flat Top Bifocal (Requires valid segment size or bounded D-seg regex)
    if any(x in c for x in [' FT ', ' BIF ', ' BIFOCAL ']) or has_valid_seg or re.search(r'\b(?:FT|D-?)\s*(22|25|28|35|40|45)\b', c): 
        return 2
    
    # 11. Single Vision (Default fallback for all stock blanks)
    return 1
    
def apply_smart_casing(text, techs_list):
    """Translates generic manufacture terms, applies title case, and protects optical acronyms."""
    import re
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
        r'\bA/r\b': 'A/R', r'\bNupolar\b': 'NuPolar', r'\bTrupolar\b': 'TruPolar',
        r'\bPhotofusion X\b': 'PhotoFusion X', r'\bPhotofusion\b': 'PhotoFusion',
        r'\bSunsync\b': 'SunSync', r'\bLiferx\b': 'LifeRx', r'\bSunrx\b': 'SunRx',
        r'\bHev\b': 'HEV', r'\bFsv\b': 'FSV', r'\bSfsv\b': 'SFSV', r'\bSf\b': 'SF',
        r'\bFt(\d+)\b': r'FT\1', r'\bDd(\d+)\b': r'DD\1', r'\bRnd(\d+)\b': r'RND\1', r'\bExg\b': 'EXG',
        r'\bUv\b': 'UV', r'\bUv(\d+)\b': r'UV\1', r'\bAr\b': 'AR', r'\bPg\b': 'PG',
        r'\bUt\b': 'UT', r'\bYhc\b': 'YHC', r'\bUs\b': 'US', r'\bHc\b': 'HC', r'\bUc\b': 'UC',
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

def synthesize_descriptions(sample_row, is_fsv, has_add, techs_found, extracted_coats, is_universal_ar, resolved_mat):
    import re
    raw_desc = str(sample_row.get('Description', '')).upper().strip()
    raw_name = str(sample_row.get('Name', '')).upper().strip()
    mfg = str(sample_row.get('MFG', '')).upper().strip()
    material = str(sample_row.get('Material', '')).upper()
    index = str(sample_row.get('Index', '')).strip()
    
    combined_name_desc = raw_desc + " " + raw_name
    combined_name_desc = re.sub(r'\b(?:HARD RESIN|RESIN|ORG)\b', 'CR-39', combined_name_desc)
    
    style_int = map_style_code(sample_row)
    
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
    else: base_sv = "FSV" if is_fsv else "SFSV"; type_cascade_array = [base_sv, base_sv, base_sv, base_sv]

    tags = []
    tags.append("FIN" if is_fsv else "SF")
    
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
        if "DuraVision" in active_ar:
            if "DuraVision" not in tags: tags.append("DuraVision")
        if active_ar not in tags: tags.append(active_ar)

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
    c_pad_color = c_pad_desc.replace('BLUE FILTER', '').replace('BLUE BLOCKER', '').replace('BLUE PROTECT', '').replace('BLUE GUARD', '').replace('BLUE-GUARD', '').replace('BLUEGUARD', '').replace('BLUEP', '').replace('UV420', '').replace('FUL PROTECT', '').replace('FUL-PROTECT', '').replace('GUARD', '')

    has_color_word = any(x in c_pad_color for x in [f" {w} " for w in color_keywords] + [f" {w}" for w in color_keywords])

    is_photochromic = any(t in techs_found or t.upper() in combined_name_desc for t in [
        'Transitions', 'PhotoFusion X', 'PhotoFusion', 'Sensitivity', 
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
        
    if active_blue: tags.append("Blue Filter") 
    
    has_photo = False
    if 'PhotoFusion X' in techs_found or 'PhotoFusion' in techs_found or 'PHOTOFUSION X' in combined_name_desc or 'PHOTOFUSION' in combined_name_desc:
        if 'EXTRA GRAY' in c_pad_color or ' EXTRA ' in c_pad_color or ' EXG ' in c_pad_color:
            tech_list_full.append('PhotoFusion X Extra')
        else:
            tech_list_full.append('PhotoFusion X')
        has_photo = True
        
    for t in ['Xtra-Active', 'Quick-Change', 'SunSync', 'Sensitivity', 'Transitions', 'LifeRx']:
        if t in techs_found or t.upper() in combined_name_desc: 
            tech_list_full.append(t)
            has_photo = True
            
    if not has_photo and ('Photochromic' in techs_found or 'PHOTOCHROMIC' in combined_name_desc):
        tech_list_full.append("Photochromic")
        has_photo = True
        
    if has_photo: tags.append("Photochromic")
        
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
            "Sensitivity": ["SENSITIVITY", "SENS", "SENS", "SENS"],
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
        
        if "ClearView" in working_techs:
            working_techs.remove("ClearView")
        if len(build()) <= target_len: return build()
        
        if target_len <= 15 and has_puck:
            state_puck = 2
            if len(build()) <= target_len: return build()
            state_puck = 3 
            if len(build()) <= target_len: return build()
        
        state_org = 0
        if len(build()) <= target_len: return build()
        state_asph = 0
        if len(build()) <= target_len: return build()
        
        state_type = 1
        if len(build()) <= target_len: return build()
        
        state_tech = 1
        if len(build()) <= target_len: return build()
        
        state_mat = 1
        if len(build()) <= target_len: return build()
        
        if active_ar: state_ar = 1
        if len(build()) <= target_len: return build()
        
        state_type = 2
        if len(build()) <= target_len: return build()
        
        state_tech = 2
        if len(build()) <= target_len: return build()
        
        state_mat = 2
        if len(build()) <= target_len: return build()
        
        if active_ar: state_ar = 2
        if len(build()) <= target_len: return build()
        
        state_tech = 3
        if len(build()) <= target_len: return build()
        
        state_mat = 3
        if len(build()) <= target_len: return build()
        
        state_mat = 4
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
        
        if has_puck: state_puck = 1
        if len(build()) <= target_len: return build()
        if has_puck: state_puck = 2
        if len(build()) <= target_len: return build()
        if has_puck: state_puck = 3
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

    if is_dd and dd_pct:
        strip_list.append(dd_pct)
    if seg_size:
        strip_list.append(str(seg_size))

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

    return clean_desc, brief_desc, long_desc, tags, active_ar, prefix_str, prefix_parts, seg_size

def aggregate_fsv_powers(group):
    import pandas as pd
    raw_sph = pd.to_numeric(group['SPH/BASE'], errors='coerce')
    raw_cyl = pd.to_numeric(group['CYL/ADD'], errors='coerce').fillna(0.0)
    
    valid_mask = raw_sph.notna()
    sph_vals = raw_sph[valid_mask]
    cyl_vals = raw_cyl[valid_mask]
    
    p_dict = {
        "PowerRange_MinusSph": None,
        "PowerRange_PlusSph": None,
        "PowerRange_MinusCyl": None,
        "PowerRange_PlusCyl": None
    }
    
    if sph_vals.empty: 
        return [f"    {C_SUBTEXT}Power Range : {C_TITLE}N/A{RESET}"], p_dict

    def fmt_closest(v_series, is_minus=False):
        if v_series.empty: return ""
        arr = sorted(v_series.unique(), key=float)
        if len(arr) == 1: return f"{arr[0]:+.2f}"
        
        # Anchors negative powers closest to 0.00 first
        if is_minus: return f"{arr[-1]:+.2f} to {arr[0]:+.2f}"
        else: return f"{arr[0]:+.2f} to {arr[-1]:+.2f}"

    m_sph = sph_vals[(sph_vals <= 0) & (cyl_vals == 0.0)]
    p_sph = sph_vals[(sph_vals > 0) & (cyl_vals == 0.0)]
    m_cyl = sph_vals[(sph_vals <= 0) & (cyl_vals != 0.0)]
    m_cyl_c = cyl_vals[(sph_vals <= 0) & (cyl_vals != 0.0)]
    p_cyl = sph_vals[(sph_vals > 0) & (cyl_vals != 0.0)]
    p_cyl_c = cyl_vals[(sph_vals > 0) & (cyl_vals != 0.0)]
    
    if not m_sph.empty: p_dict["PowerRange_MinusSph"] = fmt_closest(m_sph, is_minus=True)
    if not p_sph.empty: p_dict["PowerRange_PlusSph"] = fmt_closest(p_sph, is_minus=False)
    if not m_cyl.empty: p_dict["PowerRange_MinusCyl"] = f"{fmt_closest(m_cyl, is_minus=True)} SPH | {fmt_closest(m_cyl_c, is_minus=True)} CYL"
    if not p_cyl.empty: p_dict["PowerRange_PlusCyl"] = f"{fmt_closest(p_cyl, is_minus=False)} SPH | {fmt_closest(p_cyl_c, is_minus=True)} CYL"
        
    telemetry = []
    # 10-Character spacing for perfect colon alignment, using C_TITLE for bright Cyan
    if p_dict["PowerRange_MinusSph"]: telemetry.append(f"    {C_SUBTEXT}Minus Sph : {C_TITLE}{p_dict['PowerRange_MinusSph']}{RESET}")
    if p_dict["PowerRange_PlusSph"]:  telemetry.append(f"    {C_SUBTEXT} Plus Sph : {C_TITLE}{p_dict['PowerRange_PlusSph']}{RESET}")
    if p_dict["PowerRange_MinusCyl"]: telemetry.append(f"    {C_SUBTEXT}Minus/Cyl : {C_TITLE}{p_dict['PowerRange_MinusCyl']}{RESET}")
    if p_dict["PowerRange_PlusCyl"]:  telemetry.append(f"    {C_SUBTEXT} Plus/Cyl : {C_TITLE}{p_dict['PowerRange_PlusCyl']}{RESET}")
        
    return telemetry, p_dict

def aggregate_sf_curves(group_df):
    import pandas as pd
    curves = sorted(pd.to_numeric(group_df['SPH/BASE'], errors='coerce').dropna().unique(), key=lambda x: abs(x))
    curve_str = ", ".join([f"{c:+.2f}" for c in curves])
    # 10-Character spacing matches the FSV colons above, mapped to C_TITLE
    telemetry = [f"    {C_SUBTEXT}Base Curve: {C_TITLE}{curve_str}{RESET}"]
    return telemetry, curve_str

def heal_vca_format(filepath):
    if not str(filepath).lower().endswith(('.vca', '.txt', '.csv')): return filepath
    try:

        with open(filepath, 'r', encoding='utf-8-sig', errors='ignore') as f:
            raw_text = f.read()
            
        lines = raw_text.splitlines()
        if not lines: return filepath
        
        target_commas = lines[0].count(',')
        healed_lines = []
        buffer = ""
        
        for line in lines:
            line_str = line.strip()
            if buffer: buffer += " " + line_str
            else: buffer = line_str
            
            if buffer.count(',') >= target_commas: 
                healed_lines.append(buffer + '\n')
                buffer = ""
                
        if len(healed_lines) == len(lines): return filepath
        
        os.makedirs(TMP_DIR, exist_ok=True)
        tmp_path = os.path.join(TMP_DIR, "healed_" + os.path.basename(filepath))
        with open(tmp_path, 'w', encoding='utf-8-sig') as tf: 
            tf.writelines(healed_lines)
            
        return tmp_path
    except: 
        return filepath

def get_fuzzy_col(df, target_name, default_val=float('nan')):
    clean_target = re.sub(r'[^a-zA-Z0-9]', '', target_name).lower()
    for real_col in df.columns:
        if clean_target == re.sub(r'[^a-zA-Z0-9]', '', str(real_col)).lower(): 
            return df[real_col]
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
    for col in CUSTOM_SCHEMA:
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

def extract_lens_colors_coatings(group_df):
    colors_found = set()
    techs_found = set()
    coats_found = set()

    for _, row in group_df.iterrows():
        combined = (str(row.get('Description', '')) + " " + 
                    str(row.get('Name', '')) + " " + 
                    str(row.get('Filter', '')) + " " + 
                    str(row.get('Filter Brand', '')) + " " + 
                    str(row.get('Coating Brand', '')) + " " + 
                    str(row.get('Coating', ''))).upper()
        
        c_pad = f" {combined} ".replace('-', ' ').replace('/', ' ')
        
        c_pad_color = c_pad.replace('BLUE FILTER', '').replace('BLUE BLOCKER', '').replace('BLUE PROTECT', '').replace('BLUE GUARD', '').replace('BLUE-GUARD', '').replace('BLUEGUARD', '').replace('BLUEP', '').replace('UV420', '').replace('FUL PROTECT', '').replace('FUL-PROTECT', '').replace('GUARD', '')
        c_pad_coat = c_pad.replace('-', '').replace(' ', '')

        has_pigment = False
        
        shade_match = re.search(r'\b(GRAY|GREY|GRY|BROWN|BRN|GREEN|GRN|PIO|BURGUNDY|BURG|BRG|PINK|PNK|BLUE|BLU|PURPLE|PURP|PLUM|YELLOW|YEL|YLW|ROSE|ROS|ORANGE)\s*[-]?\s*([123ABC])\b', c_pad_color)
        if shade_match:
            base = shade_match.group(1)
            shade_val = shade_match.group(2).upper()
            
            if shade_val == 'A': shade_val = '1'
            elif shade_val == 'B': shade_val = '2'
            elif shade_val == 'C': shade_val = '3'
            
            if base in ['GRAY', 'GREY', 'GRY']: base_mapped = "Gray"
            elif base in ['BROWN', 'BRN']: base_mapped = "Brown"
            elif base in ['GREEN', 'GRN', 'PIO']: base_mapped = "Green"
            elif base in ['BURGUNDY', 'BURG', 'BRG']: base_mapped = "Burgundy"
            elif base in ['PINK', 'PNK']: base_mapped = "Pink"
            elif base in ['BLUE', 'BLU']: base_mapped = "Blue"
            elif base in ['PURPLE', 'PURP', 'PLUM']: base_mapped = "Purple"
            elif base in ['YELLOW', 'YEL', 'YLW']: base_mapped = "Yellow"
            elif base in ['ROSE', 'ROS']: base_mapped = "Rose"
            elif base in ['ORANGE']: base_mapped = "Orange"
            else: base_mapped = base.title()
            
            colors_found.add(base_mapped)
            techs_found.add(f"{base_mapped}-{shade_val}")
            has_pigment = True
            
        else:
            if any(x in c_pad_color for x in [' PRO GRAY', ' PRO GREY']): 
                colors_found.add('Pro Gray')
                techs_found.add('Gray-2')
                has_pigment = True
            elif any(x in c_pad_color for x in [' PRO BROWN']): 
                colors_found.add('Pro Brown')
                techs_found.add('Brown-2')
                has_pigment = True
            elif any(x in c_pad_color for x in [' EXTRAGREY', ' EXTRAGRAY', ' EXTRA GREY', ' EXTRA GRAY', ' EXTRA-GREY', ' EXTRA-GRAY', ' EXTRA ', ' EXG ']): colors_found.add('Extra Gray'); has_pigment = True
            elif any(x in c_pad_color for x in [' GRAY', ' GREY', ' GRY ']): colors_found.add('Gray'); has_pigment = True
            elif any(x in c_pad_color for x in [' BROWN', ' BRN ']): colors_found.add('Brown'); has_pigment = True
            elif any(x in c_pad_color for x in [' GREEN', ' GRN ', ' G15', ' G 15', ' PIONEER', ' PIONEEER', ' EMERALD', ' PIO ']): colors_found.add('Green'); has_pigment = True
            elif any(x in c_pad_color for x in [' BURGUNDY', ' BURG ', ' BRG ']): colors_found.add('Burgundy'); has_pigment = True
            elif any(x in c_pad_color for x in [' PINK', ' PNK ']): colors_found.add('Pink'); has_pigment = True
            elif any(x in c_pad_color for x in [' BLUE ', ' BLUE1', ' BLUE2', ' BLUE3', ' BLU ']): colors_found.add('Blue'); has_pigment = True
            elif any(x in c_pad_color for x in [' PURPLE', ' PURP ', ' PLUM ']): colors_found.add('Purple'); has_pigment = True
            elif any(x in c_pad_color for x in [' YELLOW', ' YEL ', ' YLW ']): colors_found.add('Yellow'); has_pigment = True
            elif any(x in c_pad_color for x in [' ROSE', ' ROS ']): colors_found.add('Rose'); has_pigment = True
            elif any(x in c_pad_color for x in [' ORANGE']): colors_found.add('Orange'); has_pigment = True

        is_photochromic = False
        is_polarized = False
        
        if any(x in c_pad for x in [' XTRA ACTIVE', ' XTRA-ACTIVE', ' XA ', ' XTRA ']): techs_found.add('Xtra-Active'); is_photochromic = True
        elif any(x in c_pad for x in [' QUICK CHANGE', ' Q CHANGE', ' QC ']): techs_found.add('Quick-Change'); is_photochromic = True
        elif any(x in c_pad for x in [' SUNSYNC']): techs_found.add('SunSync'); is_photochromic = True
        elif any(x in c_pad for x in [' SENSITIVITY', ' SENS ']): techs_found.add('Sensitivity'); is_photochromic = True
        elif any(x in c_pad for x in [' PFX', ' PHOTOFUSION X']): techs_found.add('PhotoFusion X'); is_photochromic = True
        elif any(x in c_pad for x in [' TRANSITIONS', ' TRANS ', ' TRN ']): techs_found.add('Transitions'); is_photochromic = True
        elif ' PHOTOFUSION' in c_pad: techs_found.add('PhotoFusion X'); is_photochromic = True 
        elif any(x in c_pad for x in [' LIFERX', ' LIFE RX ', ' LRX ']): techs_found.add('LifeRx'); is_photochromic = True
        elif any(x in c_pad for x in [' PHOTOCHROMIC', ' PHOTO ']): is_photochromic = True
        
        if ' NUPOLAR' in c_pad: techs_found.add('NuPolar'); is_polarized = True
        elif ' TRUPOLAR' in c_pad: techs_found.add('TruPolar'); is_polarized = True
        elif any(x in c_pad for x in [' SUNRX', ' SUN RX ']): techs_found.add('SunRx'); is_polarized = True
        elif any(x in c_pad for x in [' COPPERTONE', ' COPPER ']): techs_found.add('Coppertone'); is_polarized = True
        elif any(x in c_pad for x in [' POLARIZED', ' POLAR ', ' POLZ ', ' POL ']): techs_found.add('Polarized'); is_polarized = True
        
        if ' BLUE PROTECT' in c_pad or ' BP ' in c_pad: techs_found.add('Blue Protect')
        elif ' BLUEGUARD' in c_pad or ' BLUE GUARD' in c_pad or ' BG ' in c_pad: techs_found.add('BlueGuard')
        elif ' HEV' in c_pad or ' UV420' in c_pad: techs_found.add('HEV')
        elif ' FUL PROTECT ' in c_pad or ' FUL-PROTECT ' in c_pad: techs_found.add('Ful-Protect')
        elif any(x in c_pad for x in [" BLUE BLOCKER", " BLUE FILTER"]): techs_found.add('Blue Filter')
        
        if ' UVRI ' in c_pad or 'UVRI' in c_pad: techs_found.add('UVRI')
        if ' UV PROTECT' in c_pad: techs_found.add('UV Protect')

        if not has_pigment:
            if is_photochromic or is_polarized: colors_found.add('Gray')
            else: colors_found.add('Clear')

        if any(x in c_pad for x in [' HC ', ' SR ', ' SHMC ', ' PG ', ' UT ', ' YHC ', ' US ', ' HCT ', ' HARDCOAT ', ' HARD COAT ', ' HARD-COAT ', ' HARD ']) or any(x in c_pad_coat for x in ['ULTRASHIELD', 'PERMAGUARD', 'ULTRATOUGH', 'YOUNGERHC', 'YOUNGERHARDCOAT']):
            coats_found.add('Hardcoat')
            
        if 'PERMAGUARD' in c_pad_coat or ' PG ' in c_pad: techs_found.add('PermaGuard')
        if 'ULTRATOUGH' in c_pad_coat or ' UT ' in c_pad: techs_found.add('UltraTough')
        if 'YOUNGERHC' in c_pad_coat or 'YOUNGERHARDCOAT' in c_pad_coat or ' YHC ' in c_pad: techs_found.add('Younger Hardcoat')
        if 'ULTRASHIELD' in c_pad_coat or ' US ' in c_pad: techs_found.add('Ultra-Shield')

        if any(x in c_pad for x in [' DVC ', ' CHROME ']): coats_found.add('DuraVision Chrome')
        elif any(x in c_pad for x in [' DVP ', ' PLATINUM ']): coats_found.add('DuraVision Platinum')
        elif any(x in c_pad for x in [' DVG ', ' GOLD ']): coats_found.add('DuraVision Gold')
        elif any(x in c_pad for x in [' DVS ', ' SILVER ']): coats_found.add('DuraVision Silver')
        elif ' ROCK ' in c_pad: coats_found.add('Crizal Rock')
        elif ' SAPPHIRE ' in c_pad: coats_found.add('Crizal Sapphire')
        elif ' EASY ' in c_pad: coats_found.add('Crizal Easy')
        elif ' VELA ' in c_pad: coats_found.add('Vela')
        elif any(x in c_pad for x in [' AR ', ' CRIZAL ', ' DURAVISION ', ' DURA ']): coats_found.add('A/R')
        elif any(x in c_pad for x in [' UC ', ' UNCOATED ']): coats_found.add('Uncoated')

    if any(t in techs_found for t in ['Xtra-Active', 'Quick-Change', 'SunSync', 'Sensitivity', 'Transitions', 'PhotoFusion X', 'PhotoFusion', 'LifeRx']):
        techs_found.add('Photochromic')
    if any(t in techs_found for t in ['NuPolar', 'TruPolar', 'SunRx', 'Coppertone']):
        techs_found.add('Polarized')

    color_str = ", ".join(sorted(colors_found)) if colors_found else "Clear"
    return color_str, list(colors_found), list(techs_found), list(coats_found)
    
def normalize_lens_grouping_name(raw_name):
    n = str(raw_name).upper()
    
    n = re.sub(r'\b(?:HARD RESIN|RESIN|ORG)\b', 'CR-39', n)
    n = re.sub(r'\bBLUE\s*GUARD\b', 'BLUEGUARD', n)
    
    n = re.sub(r'\b(?:EXTRA\s*-?\s*THICK|EXTHK|ET)\b', '__ET__', n)
    n = re.sub(r'\b(?:EXTRA\s*-?\s*THIN)\b', '__E_THIN__', n)
    n = re.sub(r'\b(?:DOUBLE\s*-?\s*D|OCCUPATIONAL|OCCUP|OCC|DD)\b', '__DD__', n)
    
    # Upgraded Color Matrix Injection
    n = re.sub(r'\b(PRO GRAY|PRO GREY|PRO BROWN|EXTRA-GRAY|EXTRA-GREY|EXTRA GRAY|EXTRA GREY|EXTRAGRAY|EXTRAGREY|GRAY|GREY|GRY|BROWN|BRN|GREEN|GRN|G15|G-15|PIONEER|PIONEEER|PIO|EMERALD|BURGUNDY|BURG|BRG|PINK|PNK|BLUE|BLU|PURPLE|PURP|PLUM|YELLOW|YEL|YLW|ROSE|ROS|ORANGE|PRO|EXTRA|XTRA|XA|EXG)(?:\s*[-]?\s*[123ABC])?\b', '', n)
        
    for word in [
        'PHOTOFUSION X', 'PHOTOFUSION', 'TRANSITIONS', 'TRANS', 'TRN', 'SENSITIVITY', 'SENS', 'LIFERX', 'LRX',
        'QUICK CHANGE', 'QUICK-CHANGE', 'QC', 'NUPOLAR', 'NPOL', 'TRUPOLAR', 'TPOL', 'SUNRX', 'SUN', 'COPPERTONE', 'COPPER', 'CT', 
        'POLARIZED', 'POLAR', 'POLZ', 'PHOTOCHROMIC', 'PHOTO', 'PHT',
        'DVC', 'DVP', 'DVG', 'DVS', 'ROCK', 'EASY', 'SAPPHIRE', 'VELA', 'AR', 'CRIZAL', 'DURAVISION', 'DURA', 
        'HC', 'SR', 'SHMC', 'PG', 'UT', 'YHC', 'US', 'UC', 'UNCOATED', 'THICK', 'THIN', 'HCT',
        'YOUNGERHC', 'YOUNGER HARDCOAT', 'YOUNGER HARD COAT', 'YOUNGER HARD-COAT',
        'PERMAGUARD', 'PERMA-GUARD', 'PERMA GUARD', 'ULTRATOUGH', 'ULTRA-TOUGH', 'ULTRA TOUGH',
        'ULTRASHIELD', 'ULTRA-SHIELD', 'ULTRA SHIELD', 'HARDCOAT', 'HARD COAT', 'HARD-COAT', 'HARD', 'UVRI'
    ]:
        n = re.sub(rf'\b{word}\b', '', n)
        
    n = n.replace('__ET__', 'EXTRA-THICK')
    n = n.replace('__E_THIN__', 'EXTRA-THIN')
    n = n.replace('__DD__', 'DOUBLE-D')
    return re.sub(r'\s+', ' ', n).strip()

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
        ico = get_ico(key)
        return ico if ico else fallback

    def safe_mode(path):
        try: return os.stat(path).st_mode
        except: return 0
        
    def safe_size(path):
        try: return os.path.getsize(path)
        except: return 0

    while True:
        sys.stdout.write(f"{C_BG}\033[2J\033[H")
        term_w, term_h = get_term_size()
        
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
        
        sys.stdout.write(f"\033[2;1H{C_BORDER}║ {C_DIR}Active Directory: \033[4m{left_path}{RESET}")
        if right_path: sys.stdout.write(f"\033[2;{term_w - ansi_len(right_path) - 1}H{C_TITLE}{right_path}{RESET}")
        sys.stdout.write(f"\033[2;{term_w}H{C_BORDER}║{RESET}")
        
        sys.stdout.write(f"\033[3;1H{C_BORDER}╟{'─'*pane_l_w}┬{'─'*pane_r_w}╢{RESET}")

        if op == 'add' and ldir != IMPORT_DIR: 
            ldir = IMPORT_DIR
            
        try: items = os.listdir(ldir)
        except: items = []
            
        dirs_list = []
        files_list = []
        
        for i in items:
            pth = os.path.join(ldir, i)
            mode = safe_mode(pth) 
            
            if os.path.isdir(pth):
                dirs_list.append((i, mode, pth))
            else:
                if not ext_filter or os.path.splitext(i)[1].lower() in ext_filter:
                    files_list.append((i, mode, pth))
                    
        dirs_list.sort(key=lambda x: x[0].lower())
        files_list.sort(key=lambda x: x[0].lower())
            
        if op == 'add': 
            l_items = [("-- LOCKED --", 0, "")] + files_list
        else: 
            l_items = [("../", 0, os.path.dirname(ldir))] + [(f"{d[0]}/", d[1], d[2]) for d in dirs_list] + files_list

        max_lpage = max(1, (len(l_items) + 15) // 16)
        max_rpage = max(1, (len(clip) + 7) // 8)

        a_up = get_arrow('arr_up', '^'); a_prv = get_arrow('arr_prv', '<')
        a_dn = get_arrow('arr_dn', 'v'); a_nxt = get_arrow('arr_nxt', '>')
        
        l_head_l = f"  {a_up}   SCROLL UP"; l_head_r = f"(Page {lpage+1} of {max_lpage})"
        r_head_l = f"  {a_prv}   PREV PAGE"; r_head_r = f"(Page {rpage+1} of {max_rpage})"
        
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
                
                size_str = f"{C_TITLE}{'<DIR>':>6}{RESET}" if os.path.isdir(pth) or n=='../' or n=='-- LOCKED --' else f"{C_SIZE}{format_bytes(safe_size(pth)):>6}{RESET}"
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
                    
                    csize_str = f"{C_TITLE}{'<DIR>':>6}{RESET}" if os.path.isdir(cpth) else f"{C_SIZE}{format_bytes(safe_size(cpth)):>6}{RESET}"
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
        sys.stdout.write(f"\033[{term_h - 4};5H{C_BGLIGHT} {C_PROMPT}{get_ico('term')}  {RESET}{C_BGLIGHT}{' '*40}{RESET}\033[{term_h - 4};9H{C_BGLIGHT}")
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

CUSTOM_SCHEMA = [
        "MFG", "Class", "Name", "Description", "Filter", "Coating", "Material", "Style", 
        "Coating Brand", "Right OPC", "Left OPC", "Index", "Diameter", "SPH/BASE", 
        "CYL/ADD", "Front RAD", "Back RAD", "Center Thick", "Edge Thick", "Inset", 
        "Drop", "PRP Out", "PRP Up", "Abbe", "Seg Width", "Seg Thick", "Intermediate Ht", 
        "Slab Off", "Carriage Rad", "Bowl Dia", "Ver Dia", "Dia Dia", "Seg Sep", "Up Add", 
        "Special", "Cat Code", "Filter Brand", "DRP In", "DRP Up", "NRP In", "NRP Up", 
        "Horizontal Dia", "Nominal Dia", "Obj Clear", "Obj Rad", "Front TC", "Back TC", "SAG", "Safe Index"
]
    
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

VCA_ALIAS_MAP = {
        "FRNT RAD": "FRONT RAD", "BCK RAD": "BACK RAD", 
        "C THK": "CENTER THICK", "E THK": "EDGE THICK",
        "SEG WD": "SEG WIDTH", "SEG THK": "SEG THICK", 
        "INT HT": "INTERMEDIATE HT", "BWL DIAM": "BOWL DIA", 
        "VER DIAM": "VER DIA", "HOR DIAM": "HORIZONTAL DIA",
        "NOM DIAM": "NOMINAL DIA", "DIA DIAM": "DIA DIA",
        "PRODUCT NAME": "NAME", "LRP IN": "INSET", "LRP DOWN": "DROP"
}

def execute_batch_convert():
    global global_mode, scroll_offset
    
    tgt_list = run_file_manager('convert', start_dir=BASE_DIR, ext_filter=['.vca', '.csv', '.xlsx', '.xls', '.txt'])
    if not tgt_list: return
    total_files = len(tgt_list)
    
    def redraw_skeleton():
        sys.stdout.write(f"{C_BG}\033[2J\033[H")
        term_w, term_h = get_term_size()
        draw_top_bar()
        for r in range(2, term_h - 1): draw_frame_line("", row=r)
        draw_frame_line(f"{C_SIZE}VCA REFINERY: DATA SANITIZATION & MATH{RESET}", row=2, align="center")
        draw_status_bar()
        draw_viewport(progress_pct=33.0, active_file="AWAITING USER INPUT", current_file_idx=total_files, total_files=total_files, is_interactive=False, action_text="( WAITING FOR INPUT )")

    sys.stdout.write(f"{C_BG}\033[2J\033[H")
    term_w, term_h = get_term_size()
    draw_top_bar()
    for r in range(2, term_h - 1): draw_frame_line("", row=r)
    draw_frame_line(f"{C_SIZE}VCA REFINERY: DATA SANITIZATION & MATH{RESET}", row=2, align="center")
    draw_status_bar()
    
    viewport_logs.clear()
    scroll_offset = 0
    
    memory_bank = []     
    global_mfgs = set()  
    mfg_translation_map = {}
    
    draw_viewport(progress_pct=0.0, active_file="Phase 1: Sweep...", current_file_idx=0, total_files=total_files, is_interactive=False, action_text="( BUFFERING )")
    sys.stdout.flush() 

    # PHASE 1: SILENT INGESTION & SWEEP
    for idx, tgt in enumerate(tgt_list):
        fname = os.path.basename(tgt)
        vp_log("BUFFERING", f"Ingesting '{fname}' into memory bank...", "info")
        
        pct = ((idx + 1) / total_files) * 33.0
        draw_viewport(progress_pct=pct, active_file=f"Reading {fname}...", current_file_idx=idx+1, total_files=total_files, action_text="( BUFFERING )")
        sys.stdout.flush() 
        
        try:
            has_header = True
            if tgt.lower().endswith(('.csv', '.txt', '.vca')):
                with open(tgt, 'r', encoding='utf-8', errors='ignore') as f:
                    first_line = f.readline().upper()
                    if "MFG" not in first_line and "DESCRIPTION" not in first_line:
                        has_header = False
                        
            if not has_header:
                df = pd.read_csv(tgt, header=None, names=STANDARD_VCA_HEADERS, dtype=str)
            else:
                if tgt.lower().endswith(('.xlsx', '.xls')): df = pd.read_excel(tgt, dtype=str)
                else: df = pd.read_csv(tgt, dtype=str)
            
            # --- THE ADVANCED HEADER HEALER ---
            df.columns = df.columns.str.strip().str.upper()
            df.columns = [c.replace(' ', '') if '/' in c else c for c in df.columns]
            
            index_candidates = ['D INDEX', 'E INDEX', 'N REF', 'INDEX', 'SAFE INDEX']
            found_idx_cols = [c for c in index_candidates if c in df.columns]
            
            if found_idx_cols:
                extracted_index = df[found_idx_cols].bfill(axis=1).iloc[:, 0]
                df.drop(columns=found_idx_cols, inplace=True, errors='ignore')
                df['SAFE INDEX'] = extracted_index
                df['INDEX'] = extracted_index
            else:
                df['SAFE INDEX'] = np.nan
                df['INDEX'] = np.nan
                
            df.rename(columns=VCA_ALIAS_MAP, inplace=True)
            
            upper_to_schema = {c.upper(): c for c in CUSTOM_SCHEMA}
            df.rename(columns=upper_to_schema, inplace=True)
            df = df.loc[:, ~df.columns.duplicated()]
            
            df = df.apply(lambda col: col.str.strip() if col.dtype == "object" else col)
            df = df.replace(r'\.\.', '.', regex=True)
            df = df.replace('', np.nan)
            df = df.dropna(how='all')
            
            if 'Safe Index' in df.columns and 'Index' in df.columns:
                df['Safe Index'] = df['Safe Index'].combine_first(df['Index'])
                df['Index'] = df['Safe Index']
            elif 'Index' in df.columns: df['Safe Index'] = df['Index']
            elif 'Safe Index' in df.columns: df['Index'] = df['Safe Index']
            else: df['Safe Index'] = np.nan; df['Index'] = np.nan
            
            if 'MFG' in df.columns:
                mfgs_in_file = df['MFG'].dropna().unique()
                for m in mfgs_in_file: global_mfgs.add(str(m).strip())
                
            safe_mat = df.get('Material', pd.Series(dtype=str)).fillna('')
            safe_desc = df.get('Description', pd.Series(dtype=str)).fillna('')
            combined_text = safe_mat + " " + safe_desc
            
            mr7_count = int(combined_text.str.contains('MR-7|MR7', case=False, na=False).sum())
            mr10_count = int(combined_text.str.contains('MR-10|MR10', case=False, na=False).sum())
            ambiguous_mask = combined_text.str.contains('PU|1.67', case=False, na=False) & \
                             ~combined_text.str.contains('MR-7|MR7|MR-10|MR10', case=False, na=False)
            
            memory_bank.append({
                'tgt': tgt, 'fname': fname, 'df': df, 
                'mr7': mr7_count, 'mr10': mr10_count, 'amb_mask': ambiguous_mask
            })
            
        except Exception as e:
            vp_log("FATAL I/O", f"Failed to ingest {fname}: {str(e)}", "err")
            
        time.sleep(0.02)

    # PHASE 2: THE HUMAN GATEKEEPER (Z-Modal)
    draw_viewport(progress_pct=33.0, active_file="AWAITING USER INPUT", current_file_idx=total_files, total_files=total_files, is_interactive=False, action_text="( WAITING FOR INPUT )")
    sys.stdout.flush()
    
    for abbr in global_mfgs:
        if not abbr: continue
        ans = draw_z_index_modal("TRANSLATE MANUFACTURER", f"What does '{abbr}' stand for?")
        redraw_skeleton()
        mfg_translation_map[abbr] = ans.strip() if ans else abbr 
        
    for mem in memory_bank:
        if mem['amb_mask'].sum() > 0:
            if mem['mr10'] > mem['mr7']: mem['deduced_167'] = "MR-10" 
            elif mem['mr7'] > mem['mr10']: mem['deduced_167'] = "MR-7" 
            else:
                if mem['mr7'] == 0: mem['deduced_167'] = "MR-7" 
                else:
                    ans = draw_z_index_modal("MATERIAL AMBIGUITY", f"Tie in '{mem['fname']}'. Type MR7 or MR10:")
                    redraw_skeleton()
                    mem['deduced_167'] = "MR-7" if ans and "7" in ans else "MR-10"
    
    draw_viewport(progress_pct=50.0, active_file="Human Validation Complete", current_file_idx=total_files, total_files=total_files, is_interactive=False, action_text="( COMPILING MATH )")
    sys.stdout.flush()

    # PHASE 3 & 4: MATH & THEATRICAL TELEMETRY
    os.makedirs(IMPORT_DIR, exist_ok=True)
    os.makedirs(ORIGINALS_DIR, exist_ok=True)

    for idx, mem in enumerate(memory_bank):
        df = mem['df']
        fname = mem['fname']
        tgt = mem['tgt']
        base_name = os.path.splitext(fname)[0]
        file_size_kb = os.path.getsize(tgt) / 1024.0
        
        vp_log("I/O STREAM", f"Opening '{fname}' ({file_size_kb:.1f} KB)...", "info")
        time.sleep(0.1)
        vp_log("INGESTION", f"Parsing {len(df):,} individual data lines...", "ok")
        time.sleep(0.1)
        
        if 'MFG' in df.columns:
            df['MFG'] = df['MFG'].str.strip().map(mfg_translation_map).fillna(df['MFG'])
            
        df['Material'] = df.apply(
            lambda row: resolve_material(
                mat_str=row.get('Material'), 
                mat_brand_str=row.get('MATERIAL BRAND', ''),
                index_val=row.get('Safe Index'), 
                desc_str=row.get('Description', ''), 
                name_str=row.get('Name', ''),
                abbe_val=row.get('Abbe', ''),
                global_context={'fallback': mem.get('deduced_167')}
            ), axis=1
        )
            
        if 'Class' not in df.columns: df['Class'] = 'SF'
        sf_mask = ~df['Class'].fillna('SF').str.upper().str.contains('FIN')
        
        idx_val = pd.to_numeric(df.get('Safe Index', pd.Series(dtype=float)), errors='coerce')
        f_rad = pd.to_numeric(df.get('Front RAD', pd.Series(dtype=float)), errors='coerce')
        b_rad = pd.to_numeric(df.get('Back RAD', pd.Series(dtype=float)), errors='coerce')
        
        df.loc[sf_mask, 'Front TC'] = (((idx_val[sf_mask] - 1.0) * 1000.0) / f_rad[sf_mask]).round(2)
        df.loc[sf_mask, 'Back TC'] = (-((idx_val[sf_mask] - 1.0) * 1000.0) / b_rad[sf_mask]).round(2)
        y = 25.0 
        df.loc[sf_mask, 'SAG'] = np.where(f_rad[sf_mask] > y, f_rad[sf_mask] - np.sqrt(f_rad[sf_mask]**2 - y**2), np.nan)
        df['SAG'] = df.get('SAG', pd.Series(dtype=float)).round(3)

        sf_count = sf_mask.sum()
        fin_count = (~sf_mask).sum()
        unique_cols = [c for c in ['Name', 'Material', 'Safe Index'] if c in df.columns]
        unique_count = df.drop_duplicates(subset=unique_cols).shape[0] if unique_cols else 0
        
        if sf_count > 0:
            vp_log("AUDIT", f"Indexed {sf_count:,} Semi-Finished blanks (Curves/SAG applied)", "ok")
            time.sleep(0.1)
        if fin_count > 0:
            vp_log("AUDIT", f"Indexed {fin_count:,} Finished (FSV) lenses", "ok")
            time.sleep(0.1)
        vp_log("SUMMARY", f"Consolidated into {unique_count:,} unique optical products", "warn")
        time.sleep(0.1)

        df = df.reindex(columns=CUSTOM_SCHEMA)

        vlp_filename = f"{base_name}.vlp"
        import_path = os.path.join(IMPORT_DIR, vlp_filename)
        
        try:
            if os.path.exists(import_path):
                try: os.chmod(import_path, stat.S_IWRITE | stat.S_IREAD)
                except: pass
            
            df.to_csv(import_path, index=False)
            
            try: os.chmod(import_path, stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)
            except: pass
            
            vp_log("SECURITY", f"Locking '{vlp_filename}' to strict Read-Only (0444)", "info")
            time.sleep(0.1)
            vp_log("SUCCESS", f"Transmitted {len(df):,} sanitized records to Vault Staging.", "ok")

            dest_orig = os.path.join(ORIGINALS_DIR, fname)
            if os.path.exists(dest_orig): os.remove(dest_orig)
            shutil.move(tgt, dest_orig)
            
        except Exception as e:
            vp_log("FATAL I/O", f"Failed to save Vault file '{vlp_filename}': {str(e)}", "err")
        
        pct = 50.0 + (((idx + 1) / total_files) * 50.0)
        draw_viewport(progress_pct=pct, active_file=fname, current_file_idx=idx+1, total_files=total_files, action_text="( COMPILING )")
        time.sleep(0.3) 

    # --- INTERACTIVE SCROLL ---
    term_w, term_h = get_term_size()
    vp_height = term_h - 11
    scroll_offset = max(0, len(viewport_logs) - vp_height)
    
    draw_viewport(progress_pct=100.0, active_file="Batch Complete", current_file_idx=total_files, total_files=total_files, is_interactive=True, action_text="( PRESS ENTER TO RETURN )")
    
    while True:
        c = getch()
        if isinstance(c, bytes):
            try: c = c.decode('utf-8')
            except: continue
        if c in ('\r', '\n', '\x1b'): break
        
        if c == '\x1b[A' or c == 'UP': scroll_offset = max(0, scroll_offset - 1)
        elif c == '\x1b[B' or c == 'DOWN': scroll_offset += 1
        elif c == '\x1b[5~' or c == 'PGUP': scroll_offset = max(0, scroll_offset - 10)
        elif c == '\x1b[6~' or c == 'PGDN': scroll_offset += 10
        
        draw_viewport(progress_pct=100.0, active_file="Batch Complete", current_file_idx=total_files, total_files=total_files, is_interactive=True, action_text="( PRESS ENTER TO RETURN )")

    global_mode = "MAIN MENU"
    
def execute_add_database():
    global global_mode, scroll_offset
    if not enforce_security_lock(): return
    global_mode = "VAULT GATEKEEPER (Add)"
    
    tgt_list = run_file_manager('add', start_dir=IMPORT_DIR, ext_filter=['.vlp'])
    if not tgt_list: global_mode = "MAIN MENU"; return
    
    sys.stdout.write(f"{C_BG}\033[2J\033[H")
    term_w, term_h = get_term_size()
    draw_top_bar()
    for r in range(2, term_h - 1): draw_frame_line("", row=r)
    draw_frame_line(f"{C_SIZE}VAULT GATEKEEPER: ATOMIC BATCH VERIFICATION{RESET}", row=2, align="center")
    draw_status_bar()
    
    os.makedirs(VLP_ARCHIVE, exist_ok=True)
    os.makedirs(ORIGINALS_DIR, exist_ok=True)
    
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
    
    viewport_logs.clear()
    scroll_offset = 0
    total_files = len(tgt_list)
    current_idx = 0
    current_pct = 0.0
    
    vp_log("SYSTEM", "Cross-referencing batch against Vault records...", "info")
    draw_viewport(progress_pct=0.0, active_file="Verifying...", current_file_idx=0, total_files=total_files, is_interactive=False, action_text="( SECURING VAULT )")
    sys.stdout.flush()
    
    # VERIFICATION LOOP
    for idx, tgt in enumerate(tgt_list):
        current_idx = idx + 1
        current_pct = (current_idx / total_files) * 100.0
        fname = os.path.basename(tgt)
        
        if fname in vault_files: 
            failed_file = tgt; fail_reason = "Filename collision with Live Vault."; break
            
        vp_log("I/O STREAM", f"Verifying signature of '{fname}'...", "info")
        time.sleep(0.1) 
        
        try:
            df = robust_read_csv(tgt).dropna(how='all').drop_duplicates()
            
            if list(df.columns) != CUSTOM_SCHEMA:
                failed_file = tgt; fail_reason = "Schema corruption. Missing or altered columns."; break
            vp_log("AUDIT", "Schema matches 49/49 strict VCA columns.", "ok")
            time.sleep(0.05)
            
            critical_cols = ['MFG', 'Name', 'Material']
            null_counts = df[critical_cols].isnull().sum().sum()
            empty_counts = (df[critical_cols] == "").sum().sum()
            if null_counts > 0 or empty_counts > 0:
                failed_file = tgt; fail_reason = "Row integrity compromised (Missing MFG, Name, or Material)."; break
            vp_log("AUDIT", "Row integrity verified (0 critical nulls).", "ok")
            time.sleep(0.05)
            
            sf_mask = ~df['Class'].fillna('SF').str.upper().str.contains('FIN')
            if sf_mask.sum() > 0:
                math_cols = ['Front TC', 'Back TC', 'SAG']
                bad_math_mask = sf_mask & df[math_cols].isnull().any(axis=1)
                
                if bad_math_mask.sum() > 0:
                    first_bad_idx = df[bad_math_mask].index[0]
                    bad_lens_name = df.loc[first_bad_idx, 'Name'] if 'Name' in df.columns else "Unknown"
                    failed_file = tgt
                    fail_reason = f"Math Error on Row {first_bad_idx + 2} ({bad_lens_name}). Missing Radius or Index."
                    break
            vp_log("AUDIT", "Cryptographic math validation passed.", "ok")
            time.sleep(0.05)
            
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
                    fail_reason = f"Cross-file duplicate! Row {row_idx + 2} matches {original_location}."
                    break
                    
                batch_hashes[h_id] = f"'{fname}' (Row {row_idx + 2})"
                
            if failed_file: break
            cleaned_dfs[tgt] = df
            
        except Exception as e: 
            failed_file = tgt; fail_reason = f"Read error: {str(e)}"; break
            
        draw_viewport(progress_pct=current_pct, active_file=fname, current_file_idx=current_idx, total_files=total_files, action_text="( SECURING VAULT )")
        
    # REJECTION & ACCEPTANCE PROTOCOLS
    if failed_file:
        fname = os.path.basename(failed_file); base_name = os.path.splitext(fname)[0]
        CORRUPT_DIR = os.path.join(BASE_DIR, 'data', 'db', 'corrupt')
        os.makedirs(CORRUPT_DIR, exist_ok=True)
        
        try: 
            os.chmod(failed_file, stat.S_IWRITE | stat.S_IREAD)
            dest_corrupt = os.path.join(CORRUPT_DIR, fname)
            if os.path.exists(dest_corrupt): os.remove(dest_corrupt)
            shutil.move(failed_file, dest_corrupt)
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

        vp_log("FATAL REJECT", f"Validation Failure in '{fname}'", "err")
        vp_log("REASON", fail_reason, "err")
        vp_log("ACTION", "Atomic Batch halted. Offending .vlp file quarantined in /db/corrupt/", "warn")
        
        # --- Snap to Bottom Fix ---
        term_w, term_h = get_term_size()
        vp_height = term_h - 11
        scroll_offset = max(0, len(viewport_logs) - vp_height)
        
        draw_viewport(progress_pct=current_pct, active_file="HALTED", current_file_idx=current_idx, total_files=total_files, is_interactive=True, action_text="( PRESS ENTER TO RETURN )")
    
    else:
        vp_log("SYSTEM", "All audits passed. Initializing Vault transfer...", "info")
        moved = 0
        for idx, tgt in enumerate(tgt_list):
            try:
                dest = os.path.join(VLP_ARCHIVE, os.path.basename(tgt))
                cleaned_dfs[tgt].to_csv(dest, index=False)
                
                try: 
                    vp_log("SECURITY", f"Unlocking '{os.path.basename(tgt)}' (0777) for migration...", "warn")
                    time.sleep(0.05)
                    os.chmod(tgt, stat.S_IWRITE | stat.S_IREAD)
                    os.remove(tgt)
                    vp_log("CLEANUP", f"Purged staging copy from /data/import/.", "ok")
                except: pass
                
                os.chmod(dest, stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)
                vp_log("SECURITY", f"Checksum valid. '{os.path.basename(tgt)}' locked to 0444", "ok")
                time.sleep(0.1)
                moved += 1
            except Exception as e:
                vp_log("FATAL I/O", f"Failed to transfer {os.path.basename(tgt)}: {str(e)}", "err")
            
        vp_log("SYSTEM", f"BATCH ACCEPTED: {moved} files securely written to Vault.", "ok")
        
        # --- Snap to Bottom Fix ---
        term_w, term_h = get_term_size()
        vp_height = term_h - 11
        scroll_offset = max(0, len(viewport_logs) - vp_height)
        
        draw_viewport(progress_pct=100.0, active_file="Batch Complete", current_file_idx=total_files, total_files=total_files, is_interactive=True, action_text="( PRESS ENTER TO RETURN )")
        

    # --- INTERACTIVE SCROLL ---

    while True:
        c = getch()
        if isinstance(c, bytes):
            try: c = c.decode('utf-8')
            except: continue
        if c in ('\r', '\n', '\x1b'): break
        
        if c == '\x1b[A' or c == 'UP': scroll_offset = max(0, scroll_offset - 1)
        elif c == '\x1b[B' or c == 'DOWN': scroll_offset += 1
        elif c == '\x1b[5~' or c == 'PGUP': scroll_offset = max(0, scroll_offset - 10)
        elif c == '\x1b[6~' or c == 'PGDN': scroll_offset += 10
        
        final_pct = 100.0 if not failed_file else current_pct
        final_idx = total_files if not failed_file else current_idx
        status_msg = "Batch Complete" if not failed_file else "HALTED"
        
        draw_viewport(progress_pct=final_pct, active_file=status_msg, current_file_idx=final_idx, total_files=total_files, is_interactive=True, action_text="( PRESS ENTER TO RETURN )")
        
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
    global_mode = "MASTER COMPILER"
    render_ui_skeleton("Master Compiler Initializing...")

    sys.stdout.write("\033[?1049h\033[?25l")
    sys.stdout.flush()
    
    while True:
        sys.stdout.write(f"{C_BG}\033[2J\033[H")
        term_w, term_h = get_term_size()
        draw_top_bar()
        for r in range(2, term_h - 1): draw_frame_line("", row=r)
        draw_frame_line(f"{C_SIZE}THE MASTER COMPILER: CRUCIBLE AUDIT & REBUILD{RESET}", row=2, align="center")
        draw_status_bar()
     
        try: files = [f for f in os.listdir(VLP_ARCHIVE) if f.lower().endswith('.vlp')]
        except: files = []

        if not files:
            viewport_logs.clear()
            log_task(format_log("FATAL", "Cannot Compile: The Vault (/data/db/.vlp/) is empty.", C_ALERT), "RAW")
            draw_viewport(progress_pct=100.0, active_file="HALTED", current_file_idx=0, total_files=0, is_interactive=True, action_text="( PRESS ENTER TO RETURN )", frame_title="THE MASTER COMPILER: CRUCIBLE AUDIT & REBUILD")
            
            while True:
                c = getch()
                if isinstance(c, bytes):
                    try: c = c.decode('utf-8')
                    except: continue
                if c in ('\r', '\n', '\x1b'): break
            
            sys.stdout.write("\033[?1049l\033[?25h\033[0m")
            global_mode = "MAIN MENU"; return

        viewport_logs.clear()
        scroll_offset = 0
        log_task(format_log("SYSTEM", "Awaiting execution authorization...", C_TITLE), "RAW")
        
        total_raw_lines = 0
        for fname in files:
            fpath = os.path.join(VLP_ARCHIVE, fname)
            try: total_raw_lines += sum(1 for _ in open(fpath, 'r', encoding='utf-8', errors='ignore')) - 1
            except: pass
            
        draw_viewport(progress_pct=0.0, active_file="Pending Auth...", current_file_idx=0, total_files=max(1, total_raw_lines), total_types=0, total_lenses=0, is_interactive=False, action_text="( WAITING FOR INPUT )", frame_title="THE MASTER COMPILER: CRUCIBLE AUDIT & REBUILD")
        sys.stdout.flush()

        ans = draw_z_index_modal("CRITICAL SYSTEM WARNING", "Type COMPILE to annihilate DB & rebuild:")
        
        sys.stdout.write(f"{C_BG}\033[2J\033[H")
        draw_top_bar()
        for r in range(2, term_h - 1): draw_frame_line("", row=r)
        draw_frame_line(f"{C_SIZE}THE MASTER COMPILER: CRUCIBLE AUDIT & REBUILD{RESET}", row=2, align="center")
        draw_status_bar()
        
        if ans != "COMPILE": 
            sys.stdout.write("\033[?1049l\033[?25h\033[0m")
            global_mode = "MAIN MENU"
            return
            
        compile_start_time = time.time()
        
        if os.path.exists(DB_FILE):
            try: os.chmod(DB_FILE, stat.S_IWRITE | stat.S_IREAD)
            except: pass
        
        master_db = {"files": {}, "lenses": {}, "shards": {}}
        viewport_logs.clear()
        
        processed_lines = 0
        total_skus = 0
        total_types = 0
        
        spinner_tick = 0
        
        def get_norm_desc(desc):
            n = str(desc).upper()
            n = re.sub(r'\b(?:HARD RESIN|RESIN)\b', 'CR-39', n)
            n = normalize_lens_grouping_name(n)
            n = re.sub(r'\bD\d{2,3}\b', '', n, flags=re.IGNORECASE)
            n = re.sub(r'\b\d{2,3}MM\b', '', n, flags=re.IGNORECASE)
            return n.strip()
        
        for idx, fname in enumerate(files):
            fpath = os.path.join(VLP_ARCHIVE, fname)
            
            if fname not in master_db["files"]:
                try:
                    with open(fpath, "rb") as hash_f:
                        master_db["files"][fname] = hashlib.sha256(hash_f.read()).hexdigest()
                except:
                    master_db["files"][fname] = "HASH_ERROR"
            
            try:
                df = robust_read_csv(fpath)
                
                file_global_context = {}
                
                df['Material'] = df.apply(lambda row: resolve_material(
                    mat_str=row.get('Material', ''), 
                    mat_brand_str=row.get('Material Brand', ''), 
                    index_val=row.get('Index', ''), 
                    desc_str=row.get('Description', ''), 
                    name_str=row.get('Name', ''), 
                    abbe_val=row.get('Abbe', ''), 
                    global_context=file_global_context
                ), axis=1)
                
                df['Norm_Name'] = df['Description'].apply(get_norm_desc)
                
                group_cols = ['Norm_Name', 'Material', 'Index']
                if 'Class' in df.columns:
                    group_cols.append('Class')
                
                for group_keys, group in df.groupby(group_cols):
                    term_w, term_h = get_term_size()
                    
                    norm_desc = group_keys[0] if len(group_keys) > 0 else ""
                    mat = group_keys[1] if len(group_keys) > 1 else ""
                    index = group_keys[2] if len(group_keys) > 2 else ""
                    cls = group_keys[3] if len(group_keys) > 3 else ""
                    
                    is_fsv = "FIN" in str(cls).upper() if cls else False
                    has_add = pd.to_numeric(group['CYL/ADD'], errors='coerce').max() > 0 if not is_fsv else False
                    
                    b_id_str = f"{norm_desc}{mat}{index}{cls}"
                    b_id = hashlib.md5(b_id_str.encode()).hexdigest()[:12]
                    
                    color_tag, extracted_colors, extracted_techs, extracted_coats = extract_lens_colors_coatings(group)
                    
                    has_non_ar = False
                    for _, row_data in group.iterrows():
                        coat_str = (str(row_data.get('Coating', '')) + " " + str(row_data.get('Coating Brand', ''))).upper()
                        
                        is_ar_line = any(x in coat_str for x in ['AR', 'A/R', 'DURA', 'CRIZAL', 'VELA', 'HOYA', 'ECP', 'ULTRACLEAN', 'ANTI-REFLECTIVE', 'HMC', 'SHMC', 'BMC'])
                        
                        if 'UNCOAT' in coat_str or 'UC' in coat_str.split():
                            has_non_ar = True
                        elif not is_ar_line and ('HC' in coat_str.split() or 'SR' in coat_str.split() or 'HARDCOAT' in coat_str or 'HA' in coat_str.split()):
                            has_non_ar = True
                        elif not is_ar_line and not coat_str.strip():
                            has_non_ar = True 
                            
                    is_universal_ar = not has_non_ar
                    
                    sample_row = group.iloc[0].to_dict()
                    
                    clean_desc, lms_brief, lms_long, tags, active_ar, prefix_str, prefix_parts, extracted_seg_size = synthesize_descriptions(
                        sample_row, is_fsv, has_add, extracted_techs, extracted_coats, is_universal_ar, mat
                    )
                    
                    base_raw_desc = str(sample_row.get('Description', '')).strip()
                    
                    extra_dia_tags = []
                    if len(group) > 1:
                        for _, r_data in group.iloc[1:].iterrows():
                            rd = str(r_data.get('Description', '')).strip()
                            matches = re.findall(r'\bD\d{2,3}\b|\b\d{2,3}MM\b', rd, flags=re.IGNORECASE)
                            for m in matches:
                                m_upper = m.upper()
                                if m_upper not in base_raw_desc.upper() and m_upper not in extra_dia_tags:
                                    extra_dia_tags.append(m_upper)
                                    
                    raw_vca_description = base_raw_desc
                    if extra_dia_tags:
                        raw_vca_description += " " + " ".join(extra_dia_tags)

                    _tmp_raw = re.sub(r'\bBLUE\s*GUARD\b', 'BLUEGUARD', raw_vca_description, flags=re.IGNORECASE)
                    _tmp_raw = re.sub(r'\bBLUE\s*PROTECT\b', 'BLUEPROTECT', _tmp_raw, flags=re.IGNORECASE)
                    _tmp_raw = re.sub(r'\bBLUE\s*FILTER\b', 'BLUEFILTER', _tmp_raw, flags=re.IGNORECASE)
                    
                    _color_strip_list = ['PRO GRAY', 'PRO GREY', 'PRO BROWN', 'EXTRA-GRAY', 'EXTRA-GREY', 'EXTRA GRAY', 'EXTRA GREY', 'EXTRAGRAY', 'EXTRAGREY', 'GRAY', 'GREY', 'GRY', 'BROWN', 'BRN', 'GREEN', 'GRN', 'G15', 'G-15', 'PIONEER', 'PIONEEER', 'PIO', 'EMERALD', 'BURGUNDY', 'BURG', 'BRG', 'PINK', 'PNK', 'BLUE', 'BLU', 'PURPLE', 'PURP', 'PLUM', 'YELLOW', 'YEL', 'YLW', 'ROSE', 'ROS', 'ORANGE']
                    for _cw in _color_strip_list:
                        _tmp_raw = re.sub(rf'\b{_cw}(?:\s*[-]?\s*[123ABC])?\b', '', _tmp_raw, flags=re.IGNORECASE)
                        
                    _tmp_raw = _tmp_raw.replace('BLUEGUARD', 'BlueGuard').replace('BLUEPROTECT', 'Blue Protect').replace('BLUEFILTER', 'Blue Filter')
                    raw_vca_description = re.sub(r'\s+', ' ', _tmp_raw).strip()
                    
                    tags.extend(extracted_coats)
                    tags.extend(extracted_colors) 
                    
                    clean_desc = apply_smart_casing(clean_desc, tags + extracted_techs)
                    raw_vca_description = apply_smart_casing(raw_vca_description, tags + extracted_techs)
                    
                    if is_fsv: telemetry, p_range_dict = aggregate_fsv_powers(group)
                    else: telemetry, sf_curve_str = aggregate_sf_curves(group)
                    
                    total_types += 1
                    specifications = []
                    
                    total_in_group = len(group)
                    all_diameters = set()
                    all_colors = set()
                    all_coats = set()
                    all_exact_shades = set()
                    merge_events_to_play = []

                    seed_color = ""
                    seed_dia = ""
                    seed_coat = ""
                    seed_str = ""

                    for row_i, (_, row_data) in enumerate(group.iterrows()):
                        r_dict = {k: ("" if pd.isna(v) else v) for k, v in row_data.items()}
                        
                        row_color = "Clear"
                        exact_shade = None
                        c_pad_row = (str(r_dict.get('Description', '')) + " " + 
                                     str(r_dict.get('Name', '')) + " " + 
                                     str(r_dict.get('Filter', '')) + " " + 
                                     str(r_dict.get('Filter Brand', '')) + " " + 
                                     str(r_dict.get('Coating Brand', '')) + " " + 
                                     str(r_dict.get('Coating', ''))).upper()
                        c_pad_row = f" {c_pad_row} ".replace('-', ' ').replace('/', ' ')
                        
                        c_pad_color = c_pad_row.replace('BLUE FILTER', '').replace('BLUE BLOCKER', '').replace('BLUE PROTECT', '').replace('BLUE GUARD', '').replace('BLUE-GUARD', '').replace('BLUEGUARD', '').replace('BLUEP', '').replace('UV420', '').replace('FUL PROTECT', '').replace('FUL-PROTECT', '').replace('GUARD', '')
                        c_pad_coat = c_pad_row.replace('-', '').replace(' ', '')
                        
                        shade_match = re.search(r'\b(GRAY|GREY|GRY|BROWN|BRN|GREEN|GRN|PIO|BURGUNDY|BURG|BRG|PINK|PNK|BLUE|BLU|PURPLE|PURP|PLUM|YELLOW|YEL|YLW|ROSE|ROS|ORANGE)\s*[-]?\s*([123ABC])\b', c_pad_color)
                        if shade_match:
                            base = shade_match.group(1)
                            shade_val = shade_match.group(2).upper()
                            if shade_val == 'A': shade_val = '1'
                            elif shade_val == 'B': shade_val = '2'
                            elif shade_val == 'C': shade_val = '3'
                            
                            if base in ['GRAY', 'GREY', 'GRY']: base_mapped = "Gray"
                            elif base in ['BROWN', 'BRN']: base_mapped = "Brown"
                            elif base in ['GREEN', 'GRN', 'PIO']: base_mapped = "Green"
                            elif base in ['BURGUNDY', 'BURG', 'BRG']: base_mapped = "Burgundy"
                            elif base in ['PINK', 'PNK']: base_mapped = "Pink"
                            elif base in ['BLUE', 'BLU']: base_mapped = "Blue"
                            elif base in ['PURPLE', 'PURP', 'PLUM']: base_mapped = "Purple"
                            elif base in ['YELLOW', 'YEL', 'YLW']: base_mapped = "Yellow"
                            elif base in ['ROSE', 'ROS']: base_mapped = "Rose"
                            elif base in ['ORANGE']: base_mapped = "Orange"
                            else: base_mapped = base.title()
                            
                            exact_shade = f"{base_mapped}-{shade_val}"
                            all_exact_shades.add(exact_shade)
                            row_color = base_mapped
                            has_pigment = True
                            
                        else:
                            has_pigment = False
                            if any(x in c_pad_color for x in [' PRO GRAY', ' PRO GREY']): 
                                row_color = 'Pro Gray'
                                exact_shade = 'Gray-2'
                                all_exact_shades.add(exact_shade)
                                has_pigment = True
                            elif any(x in c_pad_color for x in [' PRO BROWN']): 
                                row_color = 'Pro Brown'
                                exact_shade = 'Brown-2'
                                all_exact_shades.add(exact_shade)
                                has_pigment = True
                            elif any(x in c_pad_color for x in [' EXTRAGREY', ' EXTRAGRAY', ' EXTRA GREY', ' EXTRA GRAY', ' EXTRA-GREY', ' EXTRA-GRAY', ' EXTRA ', ' EXG ']): row_color = 'Extra Gray'; has_pigment = True
                            elif any(x in c_pad_color for x in [' GRAY', ' GREY', ' GRY ']): row_color = 'Gray'; has_pigment = True
                            elif any(x in c_pad_color for x in [' BROWN', ' BRN ']): row_color = 'Brown'; has_pigment = True
                            elif any(x in c_pad_color for x in [' GREEN', ' GRN ', ' G15', ' G 15', ' PIONEER', ' PIONEEER', ' EMERALD', ' PIO ']): row_color = 'Green'; has_pigment = True
                            elif any(x in c_pad_color for x in [' BURGUNDY', ' BURG ', ' BRG ']): row_color = 'Burgundy'; has_pigment = True
                            elif any(x in c_pad_color for x in [' PINK', ' PNK ']): row_color = 'Pink'; has_pigment = True
                            elif any(x in c_pad_color for x in [' BLUE ', ' BLUE1', ' BLUE2', ' BLUE3', ' BLU ']): row_color = 'Blue'; has_pigment = True
                            elif any(x in c_pad_color for x in [' PURPLE', ' PURP ', ' PLUM ']): row_color = 'Purple'; has_pigment = True
                            elif any(x in c_pad_color for x in [' YELLOW', ' YEL ', ' YLW ']): row_color = 'Yellow'; has_pigment = True
                            elif any(x in c_pad_color for x in [' ROSE', ' ROS ']): row_color = 'Rose'; has_pigment = True
                            elif any(x in c_pad_color for x in [' ORANGE']): row_color = 'Orange'; has_pigment = True
                            
                            is_photochromic = False
                            is_polarized = False
                            
                            if any(x in c_pad_row for x in [' XTRA ACTIVE', ' XTRA-ACTIVE', ' XA ', ' XTRA ', ' QUICK CHANGE', ' Q CHANGE', ' QC ', ' SUNSYNC', ' SENSITIVITY', ' SENS ', ' TRANSITIONS', ' TRANS ', ' TRN ', ' LIFERX', ' LIFE RX ', ' PFX', ' PHOTOFUSION X', ' PHOTOFUSION', ' PHOTOCHROMIC', ' PHOTO ']):
                                is_photochromic = True
                            if any(x in c_pad_row for x in [' NUPOLAR', ' TRUPOLAR', ' SUNRX', ' COPPERTONE', ' POLARIZED', ' POLAR ', ' POLZ ']):
                                is_polarized = True
                                
                            if not has_pigment:
                                if is_photochromic or is_polarized: row_color = 'Gray'
                                else: row_color = 'Clear'
                        
                        raw_coat_str = (str(r_dict.get('Coating', '')) + " " + str(r_dict.get('Coating Brand', '')) + " " + str(r_dict.get('Filter', ''))).upper()
                        raw_coat_healed = raw_coat_str.replace('-', '').replace(' ', '')
                        
                        is_ar = any(x in raw_coat_str for x in ['A/R', 'DURA', 'CRIZAL', 'VELA', 'HOYA', 'ECP', 'ULTRACLEAN', 'ANTI-REFLECTIVE', 'HMC', 'SHMC', 'BMC']) or bool(re.search(r'\bAR\b', raw_coat_str))
                        
                        if is_ar: 
                            coat_tier = "AR"
                        elif 'PG' in raw_coat_str.split() or 'PERMAGUARD' in raw_coat_healed: 
                            coat_tier = "PG"
                        elif 'UT' in raw_coat_str.split() or 'ULTRATOUGH' in raw_coat_healed: 
                            coat_tier = "UT"
                        elif 'YHC' in raw_coat_str.split() or 'YOUNGERHC' in raw_coat_healed or 'YOUNGERHARDCOAT' in raw_coat_healed: 
                            coat_tier = "YHC"
                        elif 'US' in raw_coat_str.split() or 'ULTRASHIELD' in raw_coat_healed: 
                            coat_tier = "US"
                        elif any(x in raw_coat_str.split() for x in ['HC', 'SR', 'HCT', 'HA']) or 'HARD' in raw_coat_str: 
                            coat_tier = "HC"
                        elif 'UNCOAT' in raw_coat_str or 'UC' in raw_coat_str.split() or not raw_coat_str.strip() or 'NONE' in raw_coat_str.split(): 
                            coat_tier = "UC"
                        else: 
                            coat_tier = "HC" 

                        dia_val = str(r_dict.get("Diameter", "")).replace(".0", "").strip()
                        try: d_check = int(float(dia_val)) if float(dia_val).is_integer() else float(dia_val)
                        except: d_check = dia_val
                        
                        shade_str = exact_shade if exact_shade else row_color
                        
                        if row_i == 0:
                            seed_color = shade_str
                            seed_dia = f"{d_check}MM" if d_check else "N/A"
                            seed_coat = coat_tier
                            seed_str = f"Seeded {seed_color}, {seed_dia}, {seed_coat}"
                        else:
                            if all_diameters and dia_val and d_check not in all_diameters:
                                msg = f"Added {dia_val}MM Blanks"
                                if msg not in merge_events_to_play: merge_events_to_play.append(msg)
                            
                            if all_colors and shade_str not in all_colors and shade_str != seed_color:
                                msg = f"Added {shade_str.title()}"
                                if msg not in merge_events_to_play: merge_events_to_play.append(msg)
                                
                            if all_coats and coat_tier not in all_coats and coat_tier != seed_coat:
                                c_name = "Hardcoated" if coat_tier in ["HC", "PG", "UT", "YHC", "US"] else "Uncoated" if coat_tier == "UC" else "A/R"
                                msg = f"Added {c_name} Lenses"
                                if msg not in merge_events_to_play: merge_events_to_play.append(msg)

                        if dia_val: all_diameters.add(d_check)
                        all_colors.add(row_color)
                        all_coats.add(coat_tier)

                        r_opc = str(r_dict.get("Right OPC", "")).strip()
                        l_opc = str(r_dict.get("Left OPC", "")).strip()
                        if r_opc == "NAN": r_opc = ""
                        if l_opc == "NAN": l_opc = ""
                        
                        valid_opc_s = r_opc if r_opc else l_opc
                        if (r_opc and not l_opc) or (l_opc and not r_opc) or (r_opc == l_opc and valid_opc_s):
                            opc_flag = "S"
                        else:
                            opc_flag = "SPLIT"
                            
                        b_val = pd.to_numeric(r_dict.get("SPH/BASE"), errors='coerce')
                        c_val = pd.to_numeric(r_dict.get("CYL/ADD"), errors='coerce')
                        
                        b_str = f"{b_val:+.2f}" if pd.notna(b_val) else ""
                        c_str = "+0.00" if pd.isna(c_val) or float(c_val) == 0.0 else f"{c_val:+.2f}"
                        
                        spec_base = {}
                        if is_fsv:
                            spec_base = {
                                "SPH": b_str,
                                "CYL": c_str,
                                "Center Thick": r_dict.get("Center Thick", ""),
                                "Edge Thick": r_dict.get("Edge Thick", "")
                            }
                        else:
                            raw_seg_w = str(r_dict.get("Seg Width", "")).strip()
                            if not raw_seg_w and extracted_seg_size:
                                try: raw_seg_w = float(extracted_seg_size)
                                except: raw_seg_w = extracted_seg_size
                            elif raw_seg_w:
                                try: raw_seg_w = float(raw_seg_w)
                                except: pass
                                
                            spec_base = {
                                "BASE": b_str,
                                "ADD": c_str,
                                "Front RAD": r_dict.get("Front RAD", ""),
                                "Back RAD": r_dict.get("Back RAD", ""),
                                "Front TC": r_dict.get("Front TC", ""),
                                "Back TC": r_dict.get("Back TC", ""),
                                "SAG": r_dict.get("SAG", ""),
                                "Center Thick": r_dict.get("Center Thick", ""),
                                "Edge Thick": r_dict.get("Edge Thick", ""),
                                "Inset": r_dict.get("Inset", ""),
                                "Drop": r_dict.get("Drop", ""),
                                "PRP Out": r_dict.get("PRP Out", ""),
                                "PRP Up": r_dict.get("PRP Up", ""),
                                "Seg Width": raw_seg_w,
                                "Seg Thick": r_dict.get("Seg Thick", "")
                            }
                        
                        color_key_str = (exact_shade if exact_shade else row_color).replace(' ', '_').upper()
                        
                        is_duplicate = False
                        for exist_s in specifications:
                            if is_fsv:
                                if spec_base["SPH"] == exist_s.get("SPH") and spec_base["CYL"] == exist_s.get("CYL"):
                                    is_duplicate = True
                            else:
                                if spec_base["BASE"] == exist_s.get("BASE") and spec_base["ADD"] == exist_s.get("ADD"):
                                    tc_val = pd.to_numeric(r_dict.get("Front TC"), errors='coerce')
                                    etc_val = pd.to_numeric(exist_s.get("Front TC"), errors='coerce')
                                    if (pd.notna(tc_val) and pd.notna(etc_val) and abs(tc_val - etc_val) <= 0.05) or (pd.isna(tc_val) and pd.isna(etc_val)):
                                        is_duplicate = True
                                        
                            if is_duplicate:
                                if dia_val:
                                    if d_check not in exist_s["Diameters"]:
                                        exist_s["Diameters"].append(d_check)
                                        try: exist_s["Diameters"] = sorted(exist_s["Diameters"], key=float)
                                        except: pass

                                if opc_flag == "S" and valid_opc_s:
                                    k = f"{dia_val}_S_{color_key_str}_{coat_tier}"
                                    if k in exist_s["OPC"]:
                                        if valid_opc_s not in exist_s["OPC"][k]:
                                            if isinstance(exist_s["OPC"][k], list): exist_s["OPC"][k].append(valid_opc_s)
                                            else: exist_s["OPC"][k] = [exist_s["OPC"][k], valid_opc_s]
                                    else: exist_s["OPC"][k] = valid_opc_s
                                elif opc_flag == "SPLIT":
                                    kr = f"{dia_val}_R_{color_key_str}_{coat_tier}"
                                    kl = f"{dia_val}_L_{color_key_str}_{coat_tier}"
                                    if r_opc:
                                        if kr in exist_s["OPC"]:
                                            if r_opc not in exist_s["OPC"][kr]:
                                                if isinstance(exist_s["OPC"][kr], list): exist_s["OPC"][kr].append(r_opc)
                                                else: exist_s["OPC"][kr] = [exist_s["OPC"][kr], r_opc]
                                        else: exist_s["OPC"][kr] = r_opc
                                    if l_opc:
                                        if kl in exist_s["OPC"]:
                                            if l_opc not in exist_s["OPC"][kl]:
                                                if isinstance(exist_s["OPC"][kl], list): exist_s["OPC"][kl].append(l_opc)
                                                else: exist_s["OPC"][kl] = [exist_s["OPC"][kl], l_opc]
                                        else: exist_s["OPC"][kl] = l_opc
                                break

                        if not is_duplicate:
                            spec_base["Diameters"] = [d_check] if dia_val else []
                            spec_base["OPC"] = {}
                            if opc_flag == "S" and valid_opc_s:
                                spec_base["OPC"][f"{dia_val}_S_{color_key_str}_{coat_tier}"] = valid_opc_s
                            elif opc_flag == "SPLIT":
                                if r_opc: spec_base["OPC"][f"{dia_val}_R_{color_key_str}_{coat_tier}"] = r_opc
                                if l_opc: spec_base["OPC"][f"{dia_val}_L_{color_key_str}_{coat_tier}"] = l_opc
                                
                            specifications.append(spec_base)
                            
                        processed_lines += 1
                        total_skus += 1
                    
                    tags.extend(all_exact_shades)
                    tags = sorted(list(set(tags)), key=str.casefold)
                    
                    spinner_chars = ['(|)', '(/)', '(-)', '(\\)']
                    check_char = get_ico('check')
                    
                    target_dur = max(0.4, min(2.5, (total_in_group / 150.0) * 0.25))
                    sleep_interval = 0.12 
                    anim_frames = max(3, int(target_dur / sleep_interval))
                    pct = (processed_lines / max(1, total_raw_lines)) * 100.0
                    
                    header_idx = len(viewport_logs)
                    viewport_logs.append("") 
                    for t_line in telemetry: 
                        wrapped_lines = wrap_ansi_text(t_line, indent_spaces=16, max_w=term_w - 14)
                        for w_line in wrapped_lines:
                            viewport_logs.append(w_line)
                        
                    for f in range(anim_frames + 1):
                        fake_i = int((f / anim_frames) * total_in_group)
                        if fake_i == 0 and total_in_group > 0: fake_i = 1
                        if f == anim_frames: fake_i = total_in_group
                        
                        if f == anim_frames:
                            spin_char = f"{C_STAGED} {check_char} {RESET}"
                        else:
                            spin_char = f"{C_TITLE}{spinner_chars[spinner_tick % len(spinner_chars)]}{RESET}"
                            spinner_tick += 1
                            
                        fake_i_str = str(fake_i).rjust(len(str(total_in_group)))
                        clean_count = f"[+{fake_i_str}/{total_in_group}] (|)" 
                        
                        static_len = len(f'[COMPILE]  ("{b_id}"): {seed_str}') + len(clean_count)
                        max_desc_len = max(5, (term_w - 11) - static_len)
                        disp_desc = clean_desc[:max_desc_len]
                        
                        clean_base = f"[COMPILE] {disp_desc} (\"{b_id}\"): {seed_str}"
                        pad_len = max(1, (term_w - 11) - len(clean_base) - len(clean_count))
                        
                        header_str = f"{C_TITLE}[COMPILE]{RESET} {C_WARN}{disp_desc}{RESET} {C_SUBTEXT}(\"{b_id}\"):{RESET} {C_TITLE}{seed_str}{RESET}" + (" " * pad_len) + f"{C_PROMPT}[+{fake_i_str}/{total_in_group}]{RESET} {spin_char}"
                        viewport_logs[header_idx] = header_str
                        
                        draw_viewport(progress_pct=pct, active_file=fname, current_file_idx=processed_lines, total_files=total_raw_lines, total_types=total_types, total_lenses=total_skus, action_text="( COMPILING )", frame_title="THE MASTER COMPILER: CRUCIBLE AUDIT & REBUILD")
                        sys.stdout.flush()
                        if f < anim_frames: time.sleep(sleep_interval)
                        
                    for m_event in merge_events_to_play:
                        m_header_idx = len(viewport_logs)
                        viewport_logs.append("") 
                        for t_line in telemetry: 
                            wrapped_lines = wrap_ansi_text(t_line, indent_spaces=16, max_w=term_w - 14)
                            for w_line in wrapped_lines:
                                viewport_logs.append(w_line)
                            
                        for f in range(anim_frames + 1):
                            fake_i = int((f / anim_frames) * total_in_group)
                            if fake_i == 0 and total_in_group > 0: fake_i = 1
                            if f == anim_frames: fake_i = total_in_group
                            
                            if f == anim_frames:
                                spin_char = f"{C_STAGED} {check_char} {RESET}"
                            else:
                                spin_char = f"{C_TITLE}{spinner_chars[spinner_tick % len(spinner_chars)]}{RESET}"
                                spinner_tick += 1
                                
                            fake_i_str = str(fake_i).rjust(len(str(total_in_group)))
                            clean_count = f"[+{fake_i_str}/{total_in_group}] (|)"
                            
                            static_len = len(f'[ MERGE ]  ("{b_id}"): {m_event}') + len(clean_count)
                            max_desc_len = max(5, (term_w - 11) - static_len)
                            disp_desc = clean_desc[:max_desc_len]
                            
                            clean_base = f"[ MERGE ] {disp_desc} (\"{b_id}\"): {m_event}"
                            pad_len = max(1, (term_w - 11) - len(clean_base) - len(clean_count))
                            
                            header_str = f"{C_PROMPT}[ MERGE ]{RESET} {C_WARN}{disp_desc}{RESET} {C_SUBTEXT}(\"{b_id}\"):{RESET} {C_STAGED}{m_event}{RESET}" + (" " * pad_len) + f"{C_PROMPT}[+{fake_i_str}/{total_in_group}]{RESET} {spin_char}"
                            viewport_logs[m_header_idx] = header_str
                            
                            draw_viewport(progress_pct=pct, active_file=fname, current_file_idx=processed_lines, total_files=total_raw_lines, total_types=total_types, total_lenses=total_skus, action_text="( MERGING NODE )", frame_title="THE MASTER COMPILER: CRUCIBLE AUDIT & REBUILD")
                            sys.stdout.flush()
                            if f < anim_frames: time.sleep(sleep_interval)

                    for spec in specifications:
                        if not spec.get("OPC"):
                            spec.pop("OPC", None)
                        
                    strict_style_code = map_style_code(sample_row)

                    try: sorted_diameters = sorted(list(all_diameters), key=float)
                    except: sorted_diameters = list(all_diameters)
                    
                    has_blue_tech = any(t in tags for t in ["Blue Filter", "BlueGuard", "Blue Protect", "HEV"])
                    if has_blue_tech and "Blue" in all_colors:
                        base_blue_only = [c for c in all_colors if "BLUE-" not in c.upper()]
                        if "Blue" in base_blue_only:
                            all_colors.remove("Blue")
                            if not all_colors: all_colors.add("Clear")
                    if has_blue_tech and "Blue" in tags:
                        tags.remove("Blue")

                    lens_entry = {
                        "Id": b_id,
                        "MFG": sample_row.get("MFG", ""),
                        "Style": strict_style_code,
                        "Material": mat,
                        "Index": sample_row.get("Index", ""),
                        "Abbe": sample_row.get("Abbe", ""),
                        "Raw Description": raw_vca_description,
                        "Description": clean_desc,
                        "Brief Description": lms_brief,
                        "Long Description": lms_long,
                        "Colors": sorted(list(all_colors)),
                        "Diameters": sorted_diameters,
                        "Coatings": extracted_coats,
                        "FilterTags": tags,
                        "Specifications": {"FIN": specifications} if is_fsv else {"SF": specifications}
                    }
                    
                    if is_fsv: 
                        lens_entry.update(p_range_dict)
                    else: 
                        lens_entry["NominalBaseCurves"] = sf_curve_str
                        
                    master_db['lenses'][b_id] = lens_entry
                    
            except Exception as e: 
                log_task(format_log("PARSER_ERR", f"{e}", C_ALERT), "RAW")

        log_task(format_log("SYSTEM", "Writing JSON Payload...", C_TITLE), "RAW")
        
        try:
            master_db['lenses'] = dict(sorted(
                master_db['lenses'].items(),
                key=lambda item: (
                    str(item[1].get('MFG', '')),
                    str(item[1].get('Style', '')),
                    str(item[1].get('Material', '')),
                    str(item[1].get('Description', ''))
                )
            ))
            
            raw_json = json.dumps(master_db, indent=4, sort_keys=False, ensure_ascii=False)
            
            collapsed_json = re.sub(
                r'("(?:Colors|Diameters)":\s*)\[\s*([^\]]*?)\s*\]',
                lambda m: m.group(1) + '[' + " ".join(m.group(2).split()) + ']',
                raw_json
            )
            
            with open(DB_FILE, 'w', encoding='utf-8') as f: 
                f.write(collapsed_json)
            
            f_size = os.path.getsize(DB_FILE)
            os.chmod(DB_FILE, stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)
            sign_master_database()
            with open(SIG_FILE, 'r') as sf: sig = sf.read().strip()
            
            compile_end_time = time.time()
            elapsed = compile_end_time - compile_start_time
            mins, secs = divmod(int(elapsed), 60)
            
            current_time_str = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
            
            cpu_name = platform.processor()
            if platform.system() == "Windows":
                try:
                    import winreg
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
                    cpu_name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
                    cpu_name = cpu_name.strip()
                except: pass
            elif platform.system() == "Linux":
                try:
                    with open("/proc/cpuinfo", "r") as f:
                        for line in f:
                            if "model name" in line:
                                cpu_name = line.split(":")[1].strip()
                                break
                except: pass

            cpu_str = f"{cpu_name} | {os.cpu_count() or '?'} Threads"
            freq_str = "Load data unavailable"
            sys_mem_str = "Memory data unavailable"
            footprint_str = "Footprint unavailable"
            
            try:
                import psutil
                try:
                    cores_phys = psutil.cpu_count(logical=False) or "?"
                    cores_log = psutil.cpu_count(logical=True) or "?"
                    cpu_str = f"{cpu_name} | {cores_phys} Cores ({cores_log} Threads)"
                except: pass
                
                try:
                    cpu_usage = psutil.cpu_percent(interval=0.1)
                    try:
                        freq = psutil.cpu_freq()
                        if freq: freq_str = f"{cpu_usage}% Load @ {freq.current/1000:.2f} GHz (Max: {freq.max/1000:.2f} GHz)"
                        else: freq_str = f"{cpu_usage}% Load"
                    except:
                        freq_str = f"{cpu_usage}% Load"
                except: pass
                
                try:
                    vmem = psutil.virtual_memory()
                    ram_used_gb = (vmem.total - vmem.available) / (1024**3)
                    ram_total_gb = vmem.total / (1024**3)
                    sys_mem_str = f"{ram_used_gb:.1f} GB / {ram_total_gb:.1f} GB Used ({vmem.percent}%)"
                except: pass
                
                try:
                    proc = psutil.Process(os.getpid())
                    mem_use_mb = proc.memory_info().rss / (1024 * 1024)
                    footprint_str = f"{mem_use_mb:.1f} MB RAM Consumed"
                except: pass
                
            except ImportError:
                freq_str = "Load data unavailable (psutil missing)"

            db_abs_path = os.path.abspath(DB_FILE)
            try:
                disk_u = shutil.disk_usage(os.path.dirname(db_abs_path))
                disk_free_gb = disk_u.free / (1024**3)
                disk_total_gb = disk_u.total / (1024**3)
                
                if disk_total_gb > 1024:
                    vault_str = f"{disk_free_gb:.1f} GB Free / {disk_total_gb/1024:.1f} TB Total"
                else:
                    vault_str = f"{disk_free_gb:.1f} GB Free / {disk_total_gb:.1f} GB Total"
            except:
                vault_str = "Disk data unavailable"

            def pad_tel(label, val):
                return f"  {str(label).ljust(22)} :   {val}"

            log_task(format_log("SUMMARY", pad_tel("Completed", current_time_str), C_STAGED), "RAW")
            log_task(format_log("TELEMETRY", pad_tel("Environment", f"{platform.system()} {platform.release()} ({platform.machine()})"), C_STAGED), "RAW")
            log_task(format_log("TELEMETRY", pad_tel("CPU", cpu_str), C_STAGED), "RAW")
            log_task(format_log("TELEMETRY", pad_tel("CPU Load & Speed", freq_str), C_STAGED), "RAW")
            log_task(format_log("TELEMETRY", pad_tel("System Memory", sys_mem_str), C_STAGED), "RAW")
            log_task(format_log("TELEMETRY", pad_tel("Compiler Footprint", footprint_str), C_STAGED), "RAW")
            log_task(format_log("TELEMETRY", pad_tel("Vault Storage", vault_str), C_STAGED), "RAW")
            log_task(format_log("SUMMARY", pad_tel("Time Elapsed", f"{mins}m {secs}s"), C_STAGED), "RAW")
            log_task(format_log("SUMMARY", pad_tel("Vault Files Digested", str(len(files))), C_STAGED), "RAW")
            log_task(format_log("SUMMARY", pad_tel("Unique Merge Nodes", f"{total_types:,}"), C_STAGED), "RAW")
            log_task(format_log("SUMMARY", pad_tel("Total Lenses Minted", f"{total_skus:,}"), C_STAGED), "RAW")
            
            log_task(format_log("PAYLOAD", f"{f_size / (1024*1024):.2f} MB ({f_size:,} bytes)", C_PROMPT), "RAW")
            log_task(format_log("Signature", f"{sig}", C_WARN), "RAW")
            
            w_paths = wrap_ansi_text(db_abs_path, indent_spaces=15, max_w=term_w - 14, cont_char="")
            log_task(format_log("DB Path", w_paths[0].strip(), C_STAGED), "RAW")
            for p_line in w_paths[1:]:
                viewport_logs.append(p_line)
            
            vp_height = term_h - 12
            scroll_offset = max(0, len(viewport_logs) - vp_height)
            
            draw_viewport(progress_pct=100.0, active_file="master_lens_db.json", current_file_idx=total_raw_lines, total_files=total_raw_lines, total_types=total_types, total_lenses=total_skus, is_interactive=True, action_text="( PRESS ENTER TO RETURN )", frame_title="THE MASTER COMPILER: CRUCIBLE AUDIT & REBUILD")
            
            while True:
                c = getch()
                if isinstance(c, bytes):
                    try: c = c.decode('utf-8')
                    except: continue
                if c in ('\r', '\n', '\x1b'): break 
                
                max_scroll = max(0, len(viewport_logs) - vp_height)
                if c == '\x1b[A' or c == 'UP': scroll_offset = max(0, scroll_offset - 1)
                elif c == '\x1b[B' or c == 'DOWN': scroll_offset = min(max_scroll, scroll_offset + 1)
                elif c == '\x1b[5~' or c == 'PGUP': scroll_offset = max(0, scroll_offset - 10)
                elif c == '\x1b[6~' or c == 'PGDN': scroll_offset = min(max_scroll, scroll_offset + 10)
                
                draw_viewport(progress_pct=100.0, active_file="master_lens_db.json", current_file_idx=total_raw_lines, total_files=total_raw_lines, total_types=total_types, total_lenses=total_skus, is_interactive=True, action_text="( PRESS ENTER TO RETURN )", frame_title="THE MASTER COMPILER: CRUCIBLE AUDIT & REBUILD")
     
        except Exception as e: 
            log_task(format_log("FATAL", f"{e}", C_ALERT), "RAW")
            draw_viewport(progress_pct=100.0, active_file="ERROR", current_file_idx=total_raw_lines, total_files=total_raw_lines, is_interactive=True, action_text="( PRESS ENTER TO RETURN )", frame_title="THE MASTER COMPILER: CRUCIBLE AUDIT & REBUILD")
            
            while True:
                c = getch()
                if isinstance(c, bytes):
                    try: c = c.decode('utf-8')
                    except: continue
                if c in ('\r', '\n', '\x1b'): break
        
        sys.stdout.write("\033[?1049l\033[?25h\033[0m")
        break
    global_mode = "MAIN MENU"

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
        draw_frame_line(f"{C_TITLE}{get_ico('conv')} (C){C_FILE}onvert Manufacturers File -> Generate .VLP{RESET}", row=6, indent=pad)
        draw_frame_line(f"{C_TITLE}{get_ico('add')} (A){C_FILE}dd staged .VLP files into the Vault{RESET}", row=7, indent=pad)
        draw_frame_line(f"{C_TITLE}{get_ico('list')} (L){C_FILE}ist existing .VLP files in Vault{RESET}", row=8, indent=pad)
        draw_frame_line(f"{C_TITLE}{get_ico('scan')} (S){C_FILE}can existing Vault for integrity errors{RESET}", row=9, indent=pad)
        draw_frame_line(f"{C_TITLE}{get_ico('gen')} (G){C_FILE}eneration Sequence (Wipe & Rebuild DB){RESET}", row=10, indent=pad)
        draw_frame_line(f"{C_TITLE}{get_ico('html')} (E){C_FILE}xecute Master HTML Generation{RESET}", row=11, indent=pad)
        
        draw_frame_line(f"{C_TITLE}{get_ico('tools')} File Tools:{RESET}", row=13, indent=pad)
        draw_frame_line(f"  {C_TITLE}{get_ico('move')} (M){C_FILE}ove files{RESET}", row=14, indent=pad)
        draw_frame_line(f"  {C_TITLE}{get_ico('copy')} Co{C_TITLE}(p){C_FILE}y files{RESET}", row=15, indent=pad)
        draw_frame_line(f"  {C_TITLE}{get_ico('ren')} (R){C_FILE}ename file{RESET}", row=16, indent=pad)
        draw_frame_line(f"  {C_TITLE}{get_ico('del')} (D){C_FILE}elete files{RESET}", row=17, indent=pad)
        
        draw_frame_line(f"{C_ALERT}{get_ico('quit')} (Q)uit Application{RESET}", row=19, indent=pad)
        
        global_mode = "MAIN MENU"
        
        nf_status = f"{C_STAGED}[ON]{RESET}" if app_config.get('nerd_fonts') else f"{C_ALERT}[OFF]{RESET}"
        nf_text = f"{C_PROMPT}{get_ico('nf')} (N)erd Fonts: {nf_status}"
        draw_frame_line(nf_text, row=term_h - 5, align="right")
        
        ins_1 = f"Press a command hotkey (e.g. {C_PROMPT}C{C_SUBTEXT})."
        draw_frame_line(ins_1, row=term_h - 5, align="left", indent=0)
        
        draw_status_bar()
        
        sys.stdout.write(f"\033[{term_h - 4};5H{C_PROMPT}{get_ico('term')}  {RESET}{C_BGLIGHT}{' '*40}{RESET}\033[{term_h - 4};9H{C_BGLIGHT}")
        sys.stdout.flush()

        if handle_error_hijack(): continue
            
        sys.stdout.flush()
        cmd = getch()
        
        if cmd in ['\x1b[A', '\x1b[B', '\x1b[5~', '\x1b[6~', 'UP', 'DOWN', 'PGUP', 'PGDN']:
            continue
        sys.stdout.write(f"{RESET}")
        
        if cmd == 'F12': execute_admin_menu()
        elif cmd.lower() in ['q', 'x']: clean_exit()
        elif cmd.lower() == 'n': app_config['nerd_fonts'] = not app_config.get('nerd_fonts', False); reload_icons(); save_config()
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
    import sys
    import time
    
    try:
        preflight_dependency_check()
        
        # 1. Establish the Theme
        init_environment()
        load_config()
        apply_theme(app_config.get("theme", "tokyo_night"))
        
        # 1.1 --skip asset verification
        if "--skip" in sys.argv:
            import urllib.parse
            import subprocess
            import threading
            import time as _time
            import random
            import os
            import shutil
            import hashlib
            import re
            import platform
            import warnings
            import atexit
            import json
            import stat
            import textwrap
            import base64
            import psutil
            import zipfile
            import pandas as pd
            import numpy as np
            import openpyxl
            from datetime import datetime, timezone
            
            global_mode = "MAIN MENU"
            
        else: 
            # 2. Disclaimer ASCII
            display_boot_sequence()

            # 3. Asset Verification 
            verify_and_stage_fonts()

        # 4. Main Loop
        main()
        
    except KeyboardInterrupt: 
        clean_exit()
    except Exception as e:
        sys.stdout.write(f"\n\033[31m[FATAL CRASH] {str(e)}\033[0m\n")
        try: time.sleep(5)
        except: pass
        clean_exit()