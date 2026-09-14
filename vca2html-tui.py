import os
import sys
import time
import stat
import textwrap

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
            
        time.sleep(0.1)

def getch_timeout(timeout=0.1):
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

def draw_z_modal(title, prompt, mask=False, bg_render_func=None):
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
            start_y, start_x = (term_h // 2) - 2, (term_w - box_w) // 2
            
            for i in range(5):
                row = start_y + i
                if i == 0: text = f"╔{'═'*(box_w-2)}╗"
                elif i == 1: text = f"║{title:^{box_w-2}}║"
                elif i == 2: text = f"║ {prompt:<{box_w-3}}║"
                elif i == 3: text = f"║ > {' ' * (box_w-5)}║"
                elif i == 4: text = f"╚{'═'*(box_w-2)}╝"
                sys.stdout.write(f"\033[{row};{start_x}H{text}")
            sys.stdout.flush()
            force_redraw = False
            
        box_w = max(50, len(prompt) + 10)
        cursor_x = ((term_w - box_w) // 2) + 4 + len(val)
        sys.stdout.write(f"\033[{(term_h // 2) + 1};{cursor_x}H\033[?25h")
        sys.stdout.flush()
        
        ch = getch_timeout(0.1)
        if ch is None: continue
        force_redraw = True
        
        if ch in ['\r', '\n']:
            sys.stdout.write("\033[?25l")
            return val
        elif ch == 'ESC':
            sys.stdout.write("\033[?25l")
            return None
        elif ch in ['BACKSPACE', '\x08', '\x7f', 'DEL']: val = val[:-1]
        elif len(ch) == 1 and ch.isprintable() and len(val) < box_w - 7: val += ch

def bootloader(term_w, term_h):
    draw_skeleton("VCA ENGINE BOOTLOADER", "Awaiting Authorization")
    ascii_art = [
        r"██╗   ██╗ ██████╗ █████╗   ██████╗ ██╗  ██╗████████╗███╗   ███╗██╗        ████████╗██╗   ██╗██╗",
        r"██║   ██║██╔════╝██╔══██╗ ╚════██╗ ██║  ██║╚══██╔══╝████╗ ████║██║        ╚══██╔══╝██║   ██║██║",
        r"██║   ██║██║     ███████║  █████╔╝ ███████║   ██║   ██╔████╔██║██║           ██║   ██║   ██║██║",
        r"╚██╗ ██╔╝██║     ██╔══██║ ██╔═══╝  ██╔══██║   ██║   ██║╚██╔╝██║██║           ██║   ██║   ██║██║",
        r" ╚████╔╝ ╚██████╗██║  ██║ ███████╗ ██║  ██║   ██║   ██║ ╚═╝ ██║███████╗      ██║   ╚██████╔╝██║",
        r"  ╚═══╝   ╚═════╝╚═╝  ╚═╝ ╚══════╝ ╚═╝  ╚═╝   ╚═╝   ╚═╝     ╚═╝╚══════╝      ╚═╝    ╚═════╝ ╚═╝"
    ]
    start_row = 4
    for i, line in enumerate(ascii_art):
        sys.stdout.write(f"\033[{start_row + i};{(term_w - len(line)) // 2}H{line}")
    
    text_w = int(term_w * 0.85)
    pad_left = (term_w - text_w) // 2
    row = start_row + len(ascii_art) + 2
    disclaimer = "This application was created to help optical lab technicians get lens technical specifications into legacy LMS systems. There is absolutely no support for this tool and I am not responsible for any invalid information, errors, or any data loss. This application comes as is and you must use at your own risk."
    
    for line in textwrap.wrap(disclaimer, width=text_w):
        sys.stdout.write(f"\033[{row};{pad_left}H{line}")
        row += 1
    sys.stdout.write(f"\033[{row + 2};{pad_left}HPress (Y) to Accept Terms and Continue.")

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
    draw_skeleton("VCA CONVERSION MODULE", "Processing Files")
    staged_count = len(ctx.get('clip', []))
    msg = f"Ready to parse {staged_count} files. Press (ESC) to return to Main Menu."
    sys.stdout.write(f"\033[4;5H{msg}")

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
                    update_file_mgr_data(term_h, ctx) # Resolves race condition!
                    file_mgr(term_w, term_h, ctx)
                elif current_state == "VCA_CONVERT":
                    vca_convert(term_w, term_h, ctx)
                    
                sys.stdout.flush()
                force_redraw = False
                
            ch = getch_timeout(0.1)
            
            if ch is None:
                continue 
                
            force_redraw = True 
            
            if current_state == "BOOTLOADER":
                if ch.lower() == 'y':
                    current_state = "MAIN_MENU"
                else:
                    response = draw_z_modal("TERMS & CONDITIONS", "Press (Y) to agree or any key to quit.", False, bootloader)
                    if response and response.lower() == 'y':
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
                    # ----- Transition into whatever you want. ----- #
                    current_state = ctx.get('next_state', 'MAIN_MENU')
            
            elif current_state == "VCA_CONVERT":
                if ch == 'ESC':
                    current_state = "MAIN_MENU"
                    
    finally:
        sys.stdout.write("\033[?25h\033[2J\033[H")
        sys.stdout.flush()

if __name__ == "__main__":
    master_loop()