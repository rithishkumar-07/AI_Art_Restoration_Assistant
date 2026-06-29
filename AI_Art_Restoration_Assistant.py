import cv2
import math
import numpy as np
import os
import time
import threading
import sqlite3
import hashlib
import secrets
import csv
import tkinter as tk
import sys
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk, ImageDraw

# ══════════════════════════════════════════════
#  COLOUR PALETTE — Premium Dark
# ══════════════════════════════════════════════
BG_MAIN   = "#1a1a2e"
BG_CARD   = "#16213e"
BG_PANEL  = "#0f3460"
BTN_PUR   = "#9b59b6"
BTN_HOV   = "#8e44ad"
BTN_SAVE  = "#27ae60"
BTN_SAVE2 = "#1e8449"
ACCENT    = "#bb86fc"
TEXT_W    = "#f0f0f0"
TEXT_M    = "#aaaaaa"
TEXT_D    = "#555555"
BORDER    = "#2a2a4a"
PROG_BG   = "#2a2a4a"
PROG_FG   = "#9b59b6"
ERR_RED   = "#e74c3c"
GOLD      = "#f1c40f"

# ══════════════════════════════════════════════
#  PASSWORD HASHING  (salted SHA-256)
# ══════════════════════════════════════════════
def hash_pw(password, salt=None):
    """Hash a password with a random per-user salt.
       Stored as 'salt$hash' so no DB schema change is needed."""
    if salt is None:
        salt = secrets.token_hex(16)
    pw_hash = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}${pw_hash}"

def verify_pw(password, stored):
    """Verify a password against a 'salt$hash' string."""
    try:
        salt, pw_hash = stored.split("$", 1)
    except (ValueError, AttributeError):
        return False
    return hashlib.sha256((salt + password).encode()).hexdigest() == pw_hash

# ══════════════════════════════════════════════
#  DATABASE SETUP
# ══════════════════════════════════════════════
DB_PATH = "art_restoration.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Users table
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT    UNIQUE NOT NULL,
            password TEXT    NOT NULL,
            email    TEXT,
            created  TEXT    DEFAULT (datetime('now'))
        )
    """)
    # Restoration history table
    c.execute("""
        CREATE TABLE IF NOT EXISTS restoration_log (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            username     TEXT,
            filename     TEXT,
            file_size_kb REAL,
            width        INTEGER,
            height       INTEGER,
            quality_score INTEGER,
            restored_at  TEXT DEFAULT (datetime('now'))
        )
    """)
    # Seed admin user if not exists
    pw = hash_pw("admin123")
    c.execute("INSERT OR IGNORE INTO users (username,password,email) VALUES (?,?,?)",
              ("admin", pw, "admin@artrestore.com"))
    conn.commit()
    conn.close()

def db_register(username, password, email):
    try:
        conn = sqlite3.connect(DB_PATH)
        pw   = hash_pw(password)
        conn.execute("INSERT INTO users (username,password,email) VALUES (?,?,?)",
                     (username, pw, email))
        conn.commit()
        conn.close()
        return True, "Registration successful!"
    except sqlite3.IntegrityError:
        return False, "Username already exists."

def db_login(username, password):
    conn = sqlite3.connect(DB_PATH)
    row  = conn.execute(
        "SELECT password FROM users WHERE username=?",
        (username,)).fetchone()
    conn.close()
    if row is None:
        return False
    return verify_pw(password, row[0])

def db_log_restoration(username, filename, size_kb, w, h, score):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        INSERT INTO restoration_log
        (username, filename, file_size_kb, width, height, quality_score)
        VALUES (?,?,?,?,?,?)
    """, (username, filename, size_kb, w, h, score))
    conn.commit()
    conn.close()

def db_fetch_history(username):
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("""
        SELECT filename, file_size_kb, width, height, quality_score, restored_at
        FROM restoration_log WHERE username=?
        ORDER BY id DESC LIMIT 50
    """, (username,)).fetchall()
    conn.close()
    return rows

def db_search_history(username, keyword):
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("""
        SELECT filename, file_size_kb, width, height, quality_score, restored_at
        FROM restoration_log
        WHERE username=? AND filename LIKE ?
        ORDER BY id DESC
    """, (username, f"%{keyword}%")).fetchall()
    conn.close()
    return rows

def db_delete_log(username):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM restoration_log WHERE username=?", (username,))
    conn.commit()
    conn.close()

def db_get_stats(username):
    conn = sqlite3.connect(DB_PATH)

    total = conn.execute(
        "SELECT COUNT(*) FROM restoration_log WHERE username=?",
        (username,)
    ).fetchone()[0]

    avg_score = conn.execute(
        "SELECT AVG(quality_score) FROM restoration_log WHERE username=?",
        (username,)
    ).fetchone()[0]

    best_score = conn.execute(
        "SELECT MAX(quality_score) FROM restoration_log WHERE username=?",
        (username,)
    ).fetchone()[0]

    conn.close()

    return (
        total,
        round(avg_score or 0, 1),
        best_score or 0
    )

# ══════════════════════════════════════════════
#  APPLICATION STATE
# ══════════════════════════════════════════════
restored_image_path = None
current_user        = None

init_db()

# ──────────────────────────────────────────────
#  HELPERS
# ──────────────────────────────────────────────
def make_placeholder(label_text="No Image"):
    img = Image.new("RGB", (300, 210), color=BG_CARD)
    d   = ImageDraw.Draw(img)
    for x in range(0, 300, 12):
        d.rectangle([x,   0, x+6,   1], fill=BORDER)
        d.rectangle([x, 208, x+6, 209], fill=BORDER)
    for y in range(0, 210, 12):
        d.rectangle([  0, y,   1, y+6], fill=BORDER)
        d.rectangle([298, y, 299, y+6], fill=BORDER)
    d.text((150, 95),  label_text,      fill="#666680", anchor="mm")
    d.text((150, 115), "Upload to begin", fill="#444460", anchor="mm")
    return ImageTk.PhotoImage(img)

def display_in_label(lbl, path, size=(300, 210)):
    img    = Image.open(path)
    img.thumbnail(size, Image.LANCZOS)
    framed = Image.new("RGB", (img.width+4, img.height+4), BTN_PUR)
    framed.paste(img, (2, 2))
    photo  = ImageTk.PhotoImage(framed)
    lbl.config(image=photo, bg=BG_CARD)
    lbl.image = photo

def compute_quality_score(original, restored):
    mse = np.mean((original.astype(float) - restored.astype(float))**2)
    if mse == 0:
        return 100
    psnr  = 10 * math.log10(255**2 / mse)
    return min(100, max(0, int(psnr * 2.5)))

# ══════════════════════════════════════════════════════════
#  LOGIN WINDOW
# ══════════════════════════════════════════════════════════
def open_login_window():
    global current_user

    login_win = tk.Tk()
    login_win.title("AI Art Restoration — Login")
    login_win.geometry("420x480")
    login_win.resizable(False, False)
    login_win.configure(bg=BG_MAIN)

    # Title
    tk.Label(login_win, text="🎨 AI Art Restoration Assistant",
             font=("Courier", 16, "bold"), bg=BG_MAIN, fg=ACCENT).pack(pady=(28,4))
    tk.Label(login_win, text="VSB ENGINEERING COLLEGE, KARUR",
             font=("Courier", 9), bg=BG_MAIN, fg=TEXT_D).pack()
    tk.Frame(login_win, bg=BTN_PUR, height=2).pack(fill="x", padx=50, pady=12)

    # Tab bar
    tab_frame = tk.Frame(login_win, bg=BG_MAIN)
    tab_frame.pack()

    form_frame = tk.Frame(login_win, bg=BG_CARD, padx=30, pady=20)
    form_frame.pack(fill="x", padx=40, pady=8)

    msg_lbl = tk.Label(login_win, text="", font=("Courier", 9),
                       bg=BG_MAIN, fg=ERR_RED)
    msg_lbl.pack()

    # ── shared entry fields ────────────────────
    def clear_form():
        for w in form_frame.winfo_children():
            w.destroy()

    def show_login_form():
        clear_form()
        tab_login.config(bg=BTN_PUR, fg=TEXT_W)
        tab_reg.config(bg=BG_CARD, fg=TEXT_M)
        msg_lbl.config(text="")

        tk.Label(form_frame, text="Username", font=("Courier", 10),
                 bg=BG_CARD, fg=TEXT_M).pack(anchor="w")
        u_var = tk.StringVar()
        tk.Entry(form_frame, textvariable=u_var, font=("Courier", 11),
                 bg=BG_PANEL, fg=TEXT_W, insertbackground=TEXT_W,
                 relief="flat", bd=4).pack(fill="x", pady=(2,10))

        tk.Label(form_frame, text="Password", font=("Courier", 10),
                 bg=BG_CARD, fg=TEXT_M).pack(anchor="w")
        p_var = tk.StringVar()
        tk.Entry(form_frame, textvariable=p_var, show="●",
                 font=("Courier", 11), bg=BG_PANEL, fg=TEXT_W,
                 insertbackground=TEXT_W, relief="flat", bd=4).pack(fill="x", pady=(2,14))

        def do_login():
            global current_user
            u = u_var.get().strip()
            p = p_var.get().strip()
            if not u or not p:
                msg_lbl.config(text="⚠  Please fill all fields.", fg=GOLD)
                return
            if db_login(u, p):
                current_user = u
                login_win.destroy()
            else:
                msg_lbl.config(text="✗  Invalid username or password.", fg=ERR_RED)

        tk.Button(form_frame, text="  Login  ", command=do_login,
                  font=("Courier", 12, "bold"), bg=BTN_PUR, fg=TEXT_W,
                  activebackground=BTN_HOV, relief="flat", bd=0,
                  padx=20, pady=8, cursor="hand2").pack()

        form_frame.bind("<Return>", lambda e: do_login())

    def show_register_form():
        clear_form()
        tab_login.config(bg=BG_CARD, fg=TEXT_M)
        tab_reg.config(bg=BTN_PUR, fg=TEXT_W)
        msg_lbl.config(text="")

        fields = {}
        for label, key, show in [
            ("Username", "user", ""),
            ("Email",    "email",""),
            ("Password", "pw",   "●"),
            ("Confirm Password", "pw2","●"),
        ]:
            tk.Label(form_frame, text=label, font=("Courier", 9),
                     bg=BG_CARD, fg=TEXT_M).pack(anchor="w")
            v = tk.StringVar()
            tk.Entry(form_frame, textvariable=v, show=show,
                     font=("Courier", 10), bg=BG_PANEL, fg=TEXT_W,
                     insertbackground=TEXT_W, relief="flat", bd=3
                     ).pack(fill="x", pady=(2, 6))
            fields[key] = v

        def do_register():
            u  = fields["user"].get().strip()
            em = fields["email"].get().strip()
            p  = fields["pw"].get().strip()
            p2 = fields["pw2"].get().strip()
            if not u or not p:
                msg_lbl.config(text="⚠  Username & password required.", fg=GOLD)
                return
            if p != p2:
                msg_lbl.config(text="✗  Passwords do not match.", fg=ERR_RED)
                return
            if len(p) < 6:
                msg_lbl.config(text="⚠  Password min 6 characters.", fg=GOLD)
                return
            ok, txt = db_register(u, p, em)
            if ok:
                msg_lbl.config(text="✔  Registered! Please login.", fg=BTN_SAVE)
                show_login_form()
            else:
                msg_lbl.config(text=f"✗  {txt}", fg=ERR_RED)

        tk.Button(form_frame, text="  Register  ", command=do_register,
                  font=("Courier", 11, "bold"), bg=BTN_SAVE, fg=TEXT_W,
                  activebackground=BTN_SAVE2, relief="flat", bd=0,
                  padx=20, pady=7, cursor="hand2").pack(pady=(4,0))

    # Tab buttons
    tab_login = tk.Button(tab_frame, text="  Login  ",
                          command=show_login_form,
                          font=("Courier", 10, "bold"), relief="flat",
                          bd=0, padx=18, pady=6, cursor="hand2",
                          bg=BTN_PUR, fg=TEXT_W)
    tab_login.grid(row=0, column=0)
    tab_reg   = tk.Button(tab_frame, text="  Register  ",
                          command=show_register_form,
                          font=("Courier", 10, "bold"), relief="flat",
                          bd=0, padx=18, pady=6, cursor="hand2",
                          bg=BG_CARD, fg=TEXT_M)
    tab_reg.grid(row=0, column=1)

    show_login_form()

    login_win.mainloop()
    return current_user

# Run login first
logged_in_user = open_login_window()
if not logged_in_user:
    sys.exit()

# ══════════════════════════════════════════════════════════
#  MAIN APPLICATION WINDOW
# ══════════════════════════════════════════════════════════
root = tk.Tk()
root.title(f"AI Art Restoration Assistant v3.0  —  {logged_in_user}")
root.geometry("1080x860")
root.minsize(860, 720)
root.configure(bg=BG_MAIN)
root.bind("<Control-o>", lambda e: restore_image())

# ── Progress helpers (must be defined before UI builds) ──
def set_progress(pct):
    fill_w = int(540 * pct / 100)
    prog_canvas.coords("fill", 0, 0, fill_w, 14)
    prog_canvas.itemconfig("pct_txt",
        text=f"{int(pct)}%",
        fill=ACCENT if pct > 0 else TEXT_D)
    root.update_idletasks()

def animate_to(target, start, steps=35, delay=16):
    inc = (target - start) / steps
    def step(i=0, cur=float(start)):
        if i <= steps:
            set_progress(min(cur, target))
            root.after(delay, step, i+1, cur+inc)
    step()

# ── Title Canvas ──────────────────────────────
t_canvas = tk.Canvas(root, bg=BG_MAIN, highlightthickness=0, height=66)
t_canvas.pack(fill="x", pady=(12, 4))

def redraw_title(e=None):
    t_canvas.delete("all")
    W  = t_canvas.winfo_width() or 1060
    cx = W // 2
    t_canvas.create_text(cx+2, 26, anchor="center",
        text="AI ART RESTORATION ASSISTANT",
        font=("Courier", 20, "bold"), fill="#3a006a")
    t_canvas.create_text(cx, 25, anchor="center",
        text="AI ART RESTORATION ASSISTANT",
        font=("Courier", 20, "bold"), fill=ACCENT)
    t_canvas.create_text(cx, 46, anchor="center",
        text="──  OpenCV  |  Image Processing  |  Heritage Science  ──",
        font=("Courier", 9), fill=TEXT_D)
    t_canvas.create_text(cx, 60, anchor="center",
        text=f"VSB ENGINEERING COLLEGE, KARUR   |   Logged in as: {logged_in_user}",
        font=("Courier", 8), fill=BTN_PUR)

t_canvas.bind("<Configure>", redraw_title)
root.after(80, redraw_title)

tk.Frame(root, bg=BTN_PUR, height=2).pack(fill="x", padx=60, pady=(0, 8))

# ── Button Row ────────────────────────────────
btn_row = tk.Frame(root, bg=BG_MAIN)
btn_row.pack(pady=(2, 4))

def make_btn(parent, text, cmd, col, bg=BTN_PUR, fg=TEXT_W, hov=BTN_HOV):
    b = tk.Button(parent, text=text, command=cmd,
                  font=("Courier", 10, "bold"),
                  bg=bg, fg=fg,
                  activebackground=hov, activeforeground=TEXT_W,
                  relief="flat", bd=0, padx=16, pady=8, cursor="hand2")
    b.grid(row=0, column=col, padx=5)
    b.bind("<Enter>", lambda e: b.config(bg=hov))
    b.bind("<Leave>", lambda e: b.config(bg=bg))
    return b

upload_btn = make_btn(btn_row, "  ⬆  Upload & Restore  (Ctrl+O)",
                      lambda: restore_image(), 0)
save_btn   = make_btn(btn_row, "  💾  Save Image",
                      lambda: save_image(), 1,
                      bg=BG_CARD, fg=TEXT_D, hov=BTN_SAVE2)
hist_btn   = make_btn(btn_row, "  📋  History",
                      lambda: open_history_window(), 2,
                      bg="#333355", fg=TEXT_W, hov="#444477")
about_btn  = make_btn(btn_row, "  ℹ  About",
                      lambda: show_about(), 3,
                      bg="#333355", fg=TEXT_W, hov="#444477")
logout_btn = make_btn(btn_row, "  ⏻  Logout",
                      lambda: do_logout(), 4,
                      bg=ERR_RED, fg=TEXT_W, hov="#c0392b")

# ── Status & Progress ─────────────────────────
status_lbl = tk.Label(root, text="Status:  Waiting for artwork …",
                      font=("Courier", 10), bg=BG_MAIN, fg=TEXT_M)
status_lbl.pack()

pf = tk.Frame(root, bg=BG_MAIN)
pf.pack(pady=(5, 3))
prog_canvas = tk.Canvas(pf, width=560, height=14,
    bg=PROG_BG, highlightthickness=1, highlightbackground=BORDER)
prog_canvas.pack()
prog_canvas.create_rectangle(0, 0, 0, 14, fill=PROG_FG, outline="", tags="fill")
prog_canvas.create_text(280, 7, text="0%",
    fill=TEXT_D, font=("Courier", 8, "bold"), tags="pct_txt")

info_lbl = tk.Label(root, text="", font=("Courier", 9),
                    bg=BG_MAIN, fg=ACCENT)
info_lbl.pack(pady=(0, 5))

tk.Frame(root, bg=BORDER, height=1).pack(fill="x", padx=40)

# ── Main Content (Comparison card + Quick Stats) ──
content = tk.Frame(root, bg=BG_MAIN)
content.pack(fill="both", expand=True, padx=20, pady=8)
content.columnconfigure(0, weight=3)
content.columnconfigure(1, weight=1)
content.rowconfigure(0, weight=1)

# Comparison card
outer_card = tk.Frame(content, bg=BORDER, bd=1)
outer_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
card = tk.Frame(outer_card, bg=BG_CARD)
card.pack(fill="both", expand=True)

hdr = tk.Frame(card, bg=BG_PANEL)
hdr.pack(fill="x")
hdr.columnconfigure(0, weight=1)
hdr.columnconfigure(2, weight=1)
tk.Label(hdr, text="   Original Artwork",
    font=("Courier", 11, "bold"), bg=BG_PANEL, fg=ACCENT, pady=8, anchor="w"
).grid(row=0, column=0, sticky="ew")
tk.Frame(hdr, bg=BORDER, width=1).grid(row=0, column=1, sticky="ns")
tk.Label(hdr, text="   Restored Artwork",
    font=("Courier", 11, "bold"), bg=BG_PANEL, fg=ACCENT, pady=8, anchor="w"
).grid(row=0, column=2, sticky="ew")
tk.Frame(card, bg=BORDER, height=1).pack(fill="x")

img_row = tk.Frame(card, bg=BG_CARD)
img_row.pack(fill="both", expand=True)
img_row.columnconfigure(0, weight=1)
img_row.columnconfigure(1, weight=1)

left_p = tk.Frame(img_row, bg=BG_CARD)
left_p.grid(row=0, column=0, padx=16, pady=10, sticky="n")
tk.Frame(img_row, bg=BORDER, width=1).grid(row=0, column=1, sticky="nse", pady=8)
right_p = tk.Frame(img_row, bg=BG_CARD)
right_p.grid(row=0, column=2, padx=16, pady=10, sticky="n")

ph1 = make_placeholder("Original")
orig_lbl = tk.Label(left_p, image=ph1, bg=BG_CARD, bd=0)
orig_lbl.image = ph1
orig_lbl.pack()

ph2 = make_placeholder("Restored")
rest_lbl = tk.Label(right_p, image=ph2, bg=BG_CARD, bd=0)
rest_lbl.image = ph2
rest_lbl.pack()

tk.Frame(card, bg=BORDER, height=1).pack(fill="x")

# Stage checkmarks
chk_row = tk.Frame(card, bg=BG_CARD)
chk_row.pack(fill="x", padx=20, pady=8)
chk_row.columnconfigure(0, weight=1)
chk_row.columnconfigure(1, weight=1)
chk_row.columnconfigure(2, weight=1)
chk_lbls = []
for i, txt in enumerate(["✦  Noise Reduction",
                          "✦  Detail Enhancement",
                          "✦  Quality Improvement"]):
    lbl = tk.Label(chk_row, text=txt,
        font=("Courier", 10, "bold"), bg=BG_CARD, fg=TEXT_D, pady=4)
    lbl.grid(row=0, column=i, sticky="ew")
    chk_lbls.append(lbl)

# ── Right panel: Quick Stats (
right_panel = tk.Frame(content, bg=BG_CARD)
right_panel.grid(row=0, column=1, sticky="nsew")

tk.Label(right_panel, text="  Dashboard",
    font=("Courier", 10, "bold"), bg=BG_PANEL, fg=ACCENT, pady=8, anchor="w"
).pack(fill="x")
tk.Frame(right_panel, bg=BORDER, height=1).pack(fill="x")

def make_stat(parent, label, var_text, color=ACCENT):
    f = tk.Frame(parent, bg=BG_CARD)
    f.pack(fill="x", padx=10, pady=6)
    tk.Label(f, text=label, font=("Courier", 8), bg=BG_CARD, fg=TEXT_D
             ).pack(anchor="w")
    lbl = tk.Label(f, text=var_text, font=("Courier", 13, "bold"),
                   bg=BG_CARD, fg=color)
    lbl.pack(anchor="w")
    return lbl

total_lbl  = make_stat(right_panel, "Total Restored", "0", ACCENT)
score_lbl  = make_stat(right_panel, "Last Quality Score", "— %", BTN_SAVE)
size_lbl   = make_stat(right_panel, "Last File Size", "— KB", TEXT_M)
dim_lbl    = make_stat(right_panel, "Last Dimensions", "—", TEXT_M)
user_lbl   = make_stat(right_panel, "Logged in as", logged_in_user, BTN_PUR)

avg_lbl  = make_stat(right_panel, "Average Score", "0 %", GOLD)
best_lbl = make_stat(right_panel, "Best Score",    "0 %", BTN_SAVE)

total, avg_score, best_score = db_get_stats(logged_in_user)

total_lbl.config(text=str(total))
avg_lbl.config(text=f"{avg_score}%")
best_lbl.config(text=f"{best_score}%")

tk.Frame(right_panel, bg=BORDER, height=1).pack(fill="x", pady=6)

# Recent 5 in right panel
tk.Label(right_panel, text="  Recent",
    font=("Courier", 9, "bold"), bg=BG_CARD, fg=TEXT_M
).pack(anchor="w", padx=10)
recent_box = tk.Listbox(right_panel, bg=BG_CARD, fg=TEXT_M,
    selectbackground=BTN_PUR, font=("Courier", 8),
    bd=0, highlightthickness=0, relief="flat", height=7)
recent_box.pack(fill="x", padx=6, pady=4)

# ── Footer ────────────────────────────────────
tk.Frame(root, bg=BTN_PUR, height=2).pack(fill="x", padx=60, pady=(6, 0))
tk.Label(root,
    text="  AI Art Restoration v3.0  │  VSB ENGINEERING COLLEGE, KARUR  "
         "│  Python + OpenCV + SQLite + Tkinter  │  Mini-Project Submission  ",
    font=("Courier", 8), bg=BG_MAIN, fg=TEXT_D
).pack(pady=(3, 6))

# ══════════════════════════════════════════════
#  CORE FUNCTIONS
# ══════════════════════════════════════════════

def restore_image():
    """Upload image and run the 3-stage restoration pipeline on a background thread
       so the UI never freezes."""
    path = filedialog.askopenfilename(
        title="Select Artwork",
        filetypes=[("Image Files", "*.jpg *.jpeg *.png *.bmp *.tiff")])
    if not path:
        return

    for lbl in chk_lbls:
        lbl.config(fg=TEXT_D)
    upload_btn.config(state="disabled", bg="#444444", fg=TEXT_D)
    save_btn.config(bg=BG_CARD, fg=TEXT_D)
    info_lbl.config(text="")
    set_progress(0)

    try:
        status_lbl.config(text="Status:  Loading image …", fg=TEXT_M)
        display_in_label(orig_lbl, path)
    except Exception as exc:
        status_lbl.config(text=f"Error: {exc}", fg=ERR_RED)
        upload_btn.config(state="normal", bg=BTN_PUR, fg=TEXT_W)
        messagebox.showerror("Error", str(exc))
        return

    threading.Thread(target=_restore_worker, args=(path,), daemon=True).start()

def _restore_worker(path):
    """Background thread: all the slow OpenCV / DB work happens here.
       Never touch Tkinter widgets directly from this function —
       always hand off to the main thread via root.after(0, ...)."""
    global restored_image_path
    try:
        img_bgr = cv2.imread(path)
        if img_bgr is None:
            raise Exception("Invalid image file selected")
        file_size = round(os.path.getsize(path) / 1024, 1)
        h, w      = img_bgr.shape[:2]

        # Stage 1 — Noise Reduction
        root.after(0, lambda: status_lbl.config(
            text="Stage 1 / 3  │  Noise Reduction …", fg=ACCENT))
        denoised = cv2.fastNlMeansDenoisingColored(img_bgr, None, 10, 10, 7, 21)
        root.after(0, lambda: (animate_to(33, 0), chk_lbls[0].config(fg=ACCENT)))

        # Stage 2 — Detail Enhancement
        root.after(0, lambda: status_lbl.config(
            text="Stage 2 / 3  │  Detail Enhancement …", fg=ACCENT))
        kernel    = np.array([[0,-1,0],[-1,5,-1],[0,-1,0]])
        sharpened = cv2.filter2D(denoised, -1, kernel)
        root.after(0, lambda: (animate_to(66, 33), chk_lbls[1].config(fg=ACCENT)))

        # Stage 3 — CLAHE Quality
        root.after(0, lambda: status_lbl.config(
            text="Stage 3 / 3  │  Quality Improvement …", fg=ACCENT))
        lab        = cv2.cvtColor(sharpened, cv2.COLOR_BGR2LAB)
        l_ch, a, b = cv2.split(lab)
        clahe      = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        restored   = cv2.cvtColor(
            cv2.merge([clahe.apply(l_ch), a, b]), cv2.COLOR_LAB2BGR)
        root.after(0, lambda: (animate_to(100, 66), chk_lbls[2].config(fg=ACCENT)))

        restored_image_path = f"restored_{int(time.time())}.jpg"
        cv2.imwrite(restored_image_path, restored)

        score = compute_quality_score(img_bgr, restored)

        # Save to DB — own sqlite3 connection
        # per call, so it's safe to run from a background thread.
        db_log_restoration(logged_in_user,
                           os.path.basename(path), file_size, w, h, score)

        root.after(0, lambda: _restore_finish(path, file_size, w, h, score))

    except Exception as exc:
        root.after(0, lambda: _restore_error(exc))

def _restore_finish(path, file_size, w, h, score):
    """Main-thread only: paint final results once background work is done."""
    display_in_label(rest_lbl, restored_image_path)

    # Update dashboard
    total, avg_score, best_score = db_get_stats(logged_in_user)
    total_lbl.config(text=str(total))
    avg_lbl.config(text=f"{avg_score}%")
    best_lbl.config(text=f"{best_score}%")

    score_lbl.config(text=f"{score} %",
        fg=BTN_SAVE if score >= 70 else GOLD)
    size_lbl.config(text=f"{file_size} KB")
    dim_lbl.config(text=f"{w} × {h}")

    fname = os.path.basename(path)
    recent_box.insert(0, f"  {fname[:18]}  {score}%")
    if recent_box.size() > 7:
        recent_box.delete(tk.END)

    info_lbl.config(
        text=(f"File : {fname}    Size : {file_size} KB    "
              f"Dimensions : {w}×{h} px    Quality Score : {score} %"),
        fg=ACCENT)

    status_lbl.config(text="  ✔  Restoration Complete — Ready to Save",
                      fg=BTN_SAVE)
    upload_btn.config(state="normal", bg=BTN_PUR, fg=TEXT_W)
    save_btn.config(bg=BTN_SAVE, fg=TEXT_W)
    save_btn.bind("<Enter>", lambda e: save_btn.config(bg=BTN_SAVE2))
    save_btn.bind("<Leave>", lambda e: save_btn.config(bg=BTN_SAVE))

    messagebox.showinfo("Restoration Complete",
        f"Artwork restored successfully!\n\n"
        f"  ✓  Noise Reduction\n"
        f"  ✓  Detail Enhancement\n"
        f"  ✓  Quality Improvement\n\n"
        f"Quality Score  : {score} %\n"
        f"Dimensions     : {w} × {h} px\n"
        f"File Size      : {file_size} KB")

def _restore_error(exc):
    """Main-thread only: surface an error raised on the background thread."""
    status_lbl.config(text=f"Error: {exc}", fg=ERR_RED)
    upload_btn.config(state="normal", bg=BTN_PUR, fg=TEXT_W)
    messagebox.showerror("Error", str(exc))

def save_image():
    if not restored_image_path or not os.path.exists(restored_image_path):
        messagebox.showwarning("No Image", "Restore an image first.")
        return
    sp = filedialog.asksaveasfilename(
        defaultextension=".jpg",
        filetypes=[("JPEG", "*.jpg"), ("PNG", "*.png")])
    if sp:
        cv2.imwrite(sp, cv2.imread(restored_image_path))
        messagebox.showinfo("Saved", f"Saved successfully!\n{sp}")

def open_history_window():
    hw = tk.Toplevel(root)
    hw.title("Restoration History")
    hw.geometry("780x500")
    hw.configure(bg=BG_MAIN)

    tk.Label(hw, text="  Restoration History",
             font=("Courier", 13, "bold"), bg=BG_PANEL, fg=ACCENT, pady=10
             ).pack(fill="x")
    tk.Frame(hw, bg=BORDER, height=1).pack(fill="x")
    # Search bar
    sf = tk.Frame(hw, bg=BG_MAIN)
    sf.pack(fill="x", padx=20, pady=8)
    tk.Label(sf, text="Search:", font=("Courier", 10),
             bg=BG_MAIN, fg=TEXT_M).pack(side="left")
    search_var = tk.StringVar()
    tk.Entry(sf, textvariable=search_var, font=("Courier", 10),
             bg=BG_PANEL, fg=TEXT_W, insertbackground=TEXT_W,
             relief="flat", bd=4, width=30).pack(side="left", padx=8)

    # Table
    cols = ("Filename", "Size (KB)", "Width", "Height", "Score %", "Date")
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Dark.Treeview",
        background=BG_CARD, foreground=TEXT_W,
        fieldbackground=BG_CARD, rowheight=26)
    style.configure("Dark.Treeview.Heading",
        background=BG_PANEL, foreground=ACCENT,
        font=("Courier", 9, "bold"))
    style.map("Dark.Treeview", background=[("selected", BTN_PUR)])

    tree_f = tk.Frame(hw, bg=BG_MAIN)
    tree_f.pack(fill="both", expand=True, padx=20, pady=4)
    tree = ttk.Treeview(tree_f, columns=cols, show="headings",
                        style="Dark.Treeview")
    for col in cols:
        tree.heading(col, text=col)
        tree.column(col, width=115, anchor="center")
    tree.column("Filename", width=200, anchor="w")

    sb = ttk.Scrollbar(tree_f, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=sb.set)
    tree.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y")

    def load_rows(rows):
        tree.delete(*tree.get_children())
        for r in rows:
            fname, sz, w, h, sc, dt = r
            dt_short = dt[:16] if dt else ""
            tree.insert("", tk.END, values=(fname, sz, w, h, f"{sc}%", dt_short))

    def refresh():
        load_rows(db_fetch_history(logged_in_user))

    def export_csv():
        rows = db_fetch_history(logged_in_user)
        if not rows:
            messagebox.showwarning("No Data", "No history available.")
            return
        save_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv")])
        if not save_path:
            return
        with open(save_path, "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["Filename", "Size KB", "Width", "Height", "Score", "Date"])
            writer.writerows(rows)
        messagebox.showinfo("Success", "History exported successfully!")

    def do_search(*_):
        kw = search_var.get().strip()
        if kw:
            load_rows(db_search_history(logged_in_user, kw))
        else:
            refresh()

    search_var.trace_add("write", do_search)
    refresh()

    # Bottom buttons
    bf = tk.Frame(hw, bg=BG_MAIN)
    bf.pack(pady=8)
    tk.Button(bf, text="  ↺  Refresh  ", command=refresh,
              font=("Courier", 10, "bold"), bg=BTN_PUR, fg=TEXT_W,
              relief="flat", bd=0, padx=12, pady=6, cursor="hand2"
              ).grid(row=0, column=0, padx=6)

    def clear_all():
        if messagebox.askyesno("Confirm", "Delete all your history?"):
            db_delete_log(logged_in_user)
            refresh()

    tk.Button(bf, text="  🗑  Clear All  ", command=clear_all,
              font=("Courier", 10, "bold"), bg=ERR_RED, fg=TEXT_W,
              relief="flat", bd=0, padx=12, pady=6, cursor="hand2"
              ).grid(row=0, column=1, padx=6)

    tk.Button(bf, text="  📄 Export CSV  ", command=export_csv,
              font=("Courier", 10, "bold"), bg=BTN_SAVE, fg=TEXT_W,
              relief="flat", bd=0, padx=12, pady=6, cursor="hand2"
              ).grid(row=0, column=2, padx=6)

def show_about():
    messagebox.showinfo("About",
        "AI Art Restoration Assistant  v3.0\n"
        "────────────────────────────────────\n"
        "VSB ENGINEERING COLLEGE, KARUR\n"
        "Stack :\n"
        "  Python  •  OpenCV  •  Pillow\n"
        "  Tkinter  •  SQLite3\n\n"
        "Pipeline :\n"
        "  Stage 1 — fastNlMeansDenoisingColored\n"
        "  Stage 2 — Laplacian Sharpening Filter\n"
        "  Stage 3 — CLAHE Colour Enhancement\n\n"
        "Keyboard : Ctrl+O → Upload & Restore")

def do_logout():
    if messagebox.askyesno("Logout", "Logout and close the application?"):
        root.destroy()

# ══════════════════════════════════════════════
root.mainloop()