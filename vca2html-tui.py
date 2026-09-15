import os
import sys
import time
import stat
import textwrap
import pandas as pd
import numpy as np
import difflib
import re

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
    "diam": "DIAMETER", "material": "MATCODE"
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
        
        title = "[ TERMINAL TOO SMALL ]"
        dim = f"Current: {term_w}x{term_h}  |  Required: 100x30"
        msg = "Please maximize or resize your window to continue."
        start_y = term_h // 2 - 1
        
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

def draw_skeleton(title, subtitle=""):
    term_w, term_h = get_term_size()
    sys.stdout.write(f"\033[1;1H╔══[{title}]{'═'*(term_w - len(title) - 6)}╗")
    for r in range(2, term_h):
        sys.stdout.write(f"\033[{r};1H║\033[{r};{term_w}H║")
    sys.stdout.write(f"\033[{term_h};1H╚══[{subtitle}]{'═'*(term_w - len(subtitle) - 6)}╝")

# ----- UI UPDATERS ----- #

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
    
    # Safety bounds check after changing directories or resizing window
    if ctx['lpage'] >= ctx['max_lpage']: ctx['lpage'] = max(0, ctx['max_lpage'] - 1)
    if ctx['rpage'] >= ctx['max_rpage']: ctx['rpage'] = max(0, ctx['max_rpage'] - 1)

# ----- DRAWING UTILITES ----- #

def draw_viewport(term_w, term_h, ctx, progress_pct, active_file, current_idx, total_files, is_interactive=False, title="Convert VCA", action_text="", frame_title=""):
    draw_skeleton(title, "Data Sanitization & Math Engine")
    
    log_lines = ctx.get('log_lines', [])
    inner_l = 4
    inner_r = term_w - 3
    box_w = inner_r - inner_l + 1
    
    # ----- Progress Bar Rows ----- #
    pb_r1 = term_h - 5
    pb_r2 = term_h - 4
    pb_r3 = term_h - 3
    
    # ----- Viewport Rows ------ #
    vp_start_row = 5
    vp_end_row = pb_r1 - 1
    vp_height = vp_end_row - vp_start_row - 1
    total_logs = max(1, len(log_lines))
    
    # ----- Scrolling ----- #
    if not is_interactive:
        offset = max(0, total_logs - vp_height)
        ctx['scroll_offset'] = offset
    else:
        offset = ctx.get('scroll_offset', 0)
        
    # ----- Frame Title ----- #
    if frame_title:
        pad_title = max(1, (term_w - len(frame_title)) // 2)
        sys.stdout.write(f"\033[4;{inner_l}H{' ' * box_w}")
        sys.stdout.write(f"\033[4;{pad_title}H{frame_title}")
        
    sys.stdout.write(f"\033[{vp_start_row};{inner_l}H┌{'─' * (box_w - 2)}┐")
    
    for i in range(vp_height):
        row = vp_start_row + 1 + i
        log_idx = offset + i
        
        # ----- "Scrollbar" ----- #
        thumb_size = max(1, int((vp_height / total_logs) * vp_height)) if len(log_lines) > vp_height else vp_height
        max_scroll = max(1, total_logs - vp_height)
        scroll_pct = offset / max_scroll if max_scroll > 0 else 0
        thumb_pos = int(scroll_pct * (vp_height - thumb_size)) if len(log_lines) > vp_height else 0
        s_char = "█" if thumb_pos <= i < thumb_pos + thumb_size else "│"
        
        sys.stdout.write(f"\033[{row};{inner_l}H│ ")
        
        if log_idx < len(log_lines):
            line = log_lines[log_idx]
            display_line = line[:(box_w - 4)]
            sys.stdout.write(f"\033[{row};{inner_l + 2}H{display_line}")
            space_to_fill = (box_w - 4) - len(display_line)
            if space_to_fill > 0: sys.stdout.write(" " * space_to_fill)
        else:
            sys.stdout.write(" " * (box_w - 4))
            
        sys.stdout.write(f"\033[{row};{inner_r - 1}H{s_char}")
        sys.stdout.write(f"\033[{row};{inner_r}H│")
        
    sys.stdout.write(f"\033[{vp_end_row};{inner_l}H└{'─' * (box_w - 2)}┘")
    
    # ----- Progress Bar ----- #
    text_tl = f" Progress: {current_idx} of {total_files} " if total_files > 0 else " Progress "
    top_r_str = f"({active_file[:40] + '...' if len(active_file) > 40 else active_file})" if active_file else ""
    
    pb_inner_w = box_w - 4
    filled = int(pb_inner_w * (progress_pct / 100.0))
    bar_str = ("#" * filled) + (" " * (pb_inner_w - filled))
    text_br = f" {progress_pct:5.1f}% "
    
    r1_len = max(0, box_w - 6 - len(text_tl) - 2 - len(top_r_str))
    sys.stdout.write(f"\033[{pb_r1};{inner_l}H┌──({text_tl}){'─' * r1_len}{top_r_str}──┐")
    sys.stdout.write(f"\033[{pb_r2};{inner_l}H│ {bar_str} │")
    
    r3_len = max(0, box_w - 6 - len(text_br) - 2 - len(action_text))
    sys.stdout.write(f"\033[{pb_r3};{inner_l}H└──{action_text}{'─' * r3_len}({text_br})──┘")
    
    sys.stdout.write(f"\033[{term_h};1H")
    sys.stdout.flush()

def draw_z_modal(title, prompt, mask=False, bg_render_func=None, single_key=False):
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
            if bg_render_func: bg_render_func(term_w, term_h) 
            
            box_w = max(50, len(prompt) + 10)
            box_h = 4 if single_key else 5
            start_y, start_x = (term_h // 2) - (box_h // 2), (term_w - box_w) // 2
            
            for i in range(box_h):
                row = start_y + i
                if i == 0: text = f"╔{'═'*(box_w-2)}╗"
                elif i == 1: text = f"║{title:^{box_w-2}}║"
                elif i == 2: text = f"║ {prompt:<{box_w-3}}║"
                elif i == 3 and not single_key: text = f"║ > {' ' * (box_w-5)}║"
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
    sys.stdout.write("\033[5;5H(Q)uit Application")

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
            
            content = f"{prefix} {fmt_start}{n[:name_max]}{fmt_end}"
            pad = pane_l_w - 4 - len(prefix) - len(n[:name_max]) - len(perms)
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
            
            pad1 = pane_r_w - 4 - len(prefix) - len(n[:name_max]) - len(perms)
            sys.stdout.write(f"\033[{row_idx};{center_col + 2}H{prefix} {n[:name_max]}{' ' * max(0, pad1)} {perms}")
            tree_prefix = "    └─ "
            sys.stdout.write(f"\033[{row_idx + 1};{center_col + 2}H{tree_prefix}{os.path.dirname(pth)[:pane_r_w - 4 - len(tree_prefix)]}")

    # ----- Draw Command Bar ----- #
    sys.stdout.write(f"\033[{term_h - 6};5H{' ' * (term_w - 6)}")
    sys.stdout.write(f"\033[{term_h - 6};5HSelect Files by Index Number.")
    sys.stdout.write(f"\033[{term_h - 5};5H{' ' * (term_w - 6)}")
    sys.stdout.write(f"\033[{term_h - 5};5HInput \033[4mEXEC\033[24m to Finish Selection.")
    sys.stdout.write(f"\033[{term_h - 3};5H{' ' * (term_w - 6)}")
    if ctx['warning_msg']: sys.stdout.write(f"\033[{term_h - 3};5H{ctx['warning_msg']}")
        
    sys.stdout.write(f"\033[{term_h - 2};5H{' ' * (term_w - 6)}")
    sys.stdout.write(f"\033[{term_h - 2};5H> {ctx['user_input']}")
    
    cursor_col = 7 + len(ctx['user_input']) 
    sys.stdout.write(f"\033[{term_h - 2};{cursor_col}H\033[?25h")

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
    """Pandas ingestion funnel with fuzzy matching, frame throttling, and dynamic headers."""
    ctx['log_lines'] = []
    files_to_process = ctx.get('clip', [])
    total_files = len(files_to_process)
    
    import time
    last_draw_time = 0
    frame_rate = 0.05 # Redraw capped at 20 FPS
    
    draw_viewport(term_w, term_h, ctx, 0.0, "Starting batch...", 0, total_files, is_interactive=False, title="Convert VCA", action_text="( COMPILING )", frame_title="VCA REFINERY: DATA SANITIZATION")
    
    for idx, (name, pth) in enumerate(files_to_process):
        current_idx = idx + 1
        pct = (current_idx / max(1, total_files)) * 100.0
        
        # Throttle check for Start of file
        current_time = time.time()
        if current_time - last_draw_time > frame_rate or current_idx == total_files:
            draw_viewport(term_w, term_h, ctx, pct, f"Parsing: {name}", current_idx, total_files, is_interactive=False, title="Convert VCA", action_text="( COMPILING )", frame_title="VCA REFINERY: DATA SANITIZATION")
            last_draw_time = current_time
        
        ctx['log_lines'].append(f"╔══ [ TARGET FILE: {name} ]")
        dest_pth = os.path.join(IMPORT_DIR, name)
        
        try:
            # ----- Does it have a header? ----- #
            with open(pth, 'r', errors='ignore') as f:
                first_line = f.readline().upper()
                
            if "MFG" not in first_line and "DESCRIPTION" not in first_line:
                df = pd.read_csv(pth, header=None, dtype=str, on_bad_lines='skip', engine='python')
                df.columns = CUSTOM_SCHEMA[:df.shape[1]]
                ctx['log_lines'].append("║ [!] Ghost file detected: Forced master schema overlay.")
            else:
                df = pd.read_csv(pth, dtype=str, on_bad_lines='skip', engine='python')
                
                # ----- Fuzzy Matcher ----- #
                mapped_columns = {}
                target_keys = list(SCHEMA_LOOKUP.keys())
                
                for col in df.columns:
                    scrubbed = re.sub(r'[^a-zA-Z0-9]', '', str(col)).lower()

                    if scrubbed in SCHEMA_ALIAS:
                        mapped_columns[col] = SCHEMA_ALIAS[scrubbed]
                    # ----- match ----- #
                    elif scrubbed in SCHEMA_LOOKUP:
                        mapped_columns[col] = SCHEMA_LOOKUP[scrubbed]
                    # ----- typo ----- #
                    else:
                        matches = difflib.get_close_matches(scrubbed, target_keys, n=1, cutoff=0.85)
                        if matches:
                            mapped_columns[col] = SCHEMA_LOOKUP[matches[0]]
                        else:
                            mapped_columns[col] = col # ----- Leave it alone ----- #
                            
                df.rename(columns=mapped_columns, inplace=True)

            # ----- Drops proprietary manufacturer math and enforces 53-column layout ----- #
            df = df.reindex(columns=CUSTOM_SCHEMA)
            df = df.replace(r'^\s*$', np.nan, regex=True)
            
            # ----- Cascade logic for Safe Index: NINDEX -> DINDEX -> EINDEX -> default 1.530 ----- #
            n_idx = pd.to_numeric(df['NINDEX'], errors='coerce')
            d_idx = pd.to_numeric(df['DINDEX'], errors='coerce')
            e_idx = pd.to_numeric(df['EINDEX'], errors='coerce')
            df['SAFE_INDEX'] = n_idx.combine_first(d_idx).combine_first(e_idx).fillna(1.530)
            
            # ----- Convert Radii to Numeric. Zeros become NaN to prevent division-by-zero ----- #
            rad_f = pd.to_numeric(df['RADIUSF'], errors='coerce').replace(0.0, np.nan)
            rad_b = pd.to_numeric(df['RADIUSB'], errors='coerce').replace(0.0, np.nan)
            safe_idx_val = pd.to_numeric(df['SAFE_INDEX'], errors='coerce')
            
            # ----- Calculate True Front and True Back Curves using 1.530 standard tooling index ----- #
            df['TRUE_FRONT'] = (((safe_idx_val - 1.0) * 1000.0) / rad_f).round(2)
            df['TRUE_BACK'] = (-((safe_idx_val - 1.0) * 1000.0) / rad_b).round(2)
            
            # ----- Calculate SAG at 50mm (half-chord y = 25.0) ----- #
            y = 25.0
            df['SAG'] = np.where(rad_f > y, rad_f - np.sqrt(rad_f**2 - y**2), np.nan)
            df['SAG'] = df['SAG'].round(3)
            
            # ---- Failsafe convert invalid math results back to 0.00 ----- #
            df[['TRUE_FRONT', 'TRUE_BACK', 'SAG']] = df[['TRUE_FRONT', 'TRUE_BACK', 'SAG']].fillna(0.00)
            
            # ----- Clean dataframe back to strings so Pandas doesn't strip trailing zeros when saving ----- #
            df = df.fillna("")
            
            # ---- Temporary Output ----- #
            df.to_csv(dest_pth, index=False)
            
            ctx['log_lines'].append(f"║ {len(df):,} Rows Ingested & Schema Locked")
            ctx['log_lines'].append(f"║ Math Engine: Safe Index, True Curves, and SAG Applied")
            ctx['log_lines'].append(f"║ [ STAGED TO: {dest_pth} ]")
            
        except Exception as e:
            ctx['log_lines'].append(f"║ [ ERROR PROCESSING FILE: {e} ]")
            
        ctx['log_lines'].append(f"╚{'═'*40}")
        ctx['log_lines'].append("") 
        
        # ----- check for EOF ----- #
        current_time = time.time()
        if current_time - last_draw_time > frame_rate or current_idx == total_files:
            draw_viewport(term_w, term_h, ctx, pct, f"Finished: {name}", current_idx, total_files, is_interactive=False, title="Convert VCA", action_text="( COMPILING )", frame_title="VCA REFINERY: DATA SANITIZATION")
            last_draw_time = current_time
        
    return ctx['log_lines']

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
        if cmd.upper() == "EXEC":
            sys.stdout.write("\033[?25l")
            return "EXEC"
        elif cmd.isdigit():
            idx = int(cmd)
            if 0 <= idx < len(ctx['l_items']):
                n, pth = ctx['l_items'][idx]
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

# ----- Master Loop. Master Sword. ----- #

def init_env():
    os.makedirs('./data/import', exist_ok=True)
    os.makedirs('./data/db/.vault', exist_ok=True)

def master_loop():
    current_state = "BOOTLOADER"
    last_state = ""
    ctx = {}
    
    last_term_w, last_term_h = 0, 0
    force_redraw = True
    
    sys.stdout.write("\033[?25l\033[2J")
    
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
                elif current_state == "VCA_CONVERT":
                    vca_convert(term_w, term_h, ctx)
                    
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
                        sys.exit(0)
                        
            elif current_state == "MAIN_MENU":
                if ch.lower() == 'c':
                    # ----- File Manager -> VCA_CONVERT ----- #
                    ctx = {
                        'ldir': os.path.abspath(os.getcwd()),
                        'clip': [],
                        'lpage': 0, 'rpage': 0,
                        'user_input': "", 'warning_msg': "",
                        'next_state': "VCA_CONVERT" 
                    }
                    current_state = "FILE_MGR"
                elif ch.lower() == 'q' or ch == 'ESC':
                    sys.exit(0)
                    
            elif current_state == "FILE_MGR":
                # ----- Ensure data is updated before checking keystrokes ----- #
                update_file_mgr_data(term_h, ctx)
                action = file_mgr_input(ch, ctx)
                if action == "EXIT":
                    current_state = "MAIN_MENU"
                elif action == "EXEC":
                    # -----Pass terminal dimensions ----- #
                    vca_parse_data(ctx, term_w, term_h)
                    current_state = ctx.get('next_state', 'MAIN_MENU')
            
            elif current_state == "VCA_CONVERT":
                action = vca_convert_input(ch, ctx, term_h)
                if action == "EXIT":
                    current_state = "MAIN_MENU"
                    
    finally:
        sys.stdout.write("\033[?25h\033[2J\033[H")
        sys.stdout.flush()

if __name__ == "__main__":
    master_loop()