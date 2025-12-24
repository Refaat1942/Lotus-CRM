# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import messagebox
import os, pyodbc, hashlib, subprocess, sys
from knowledge_app import open_knowledge_window

# ─────────────────────────────────────────────────────────────────────────────
# Globals
logged_in_username = None
root = None
main = None

# ─────────────────────────────────────────────────────────────────────────────
def get_connection():
    return pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=LAPREFaat;'
        'DATABASE=DrAhmedCRM;'
        'Trusted_Connection=yes;'
    )

def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def fade_in(win, step=0.05, delay=20):
    win.attributes('-alpha', 0.0)
    def _inc():
        a = win.attributes('-alpha')
        if a < 1.0:
            a = min(a + step, 1.0)
            win.attributes('-alpha', a)
            win.after(delay, _inc)
    _inc()

# ─────────────────────────────────────────────────────────────────────────────
def run_script(path):
    # استخدام subprocess يضمن تشغيل الملفات حتى لو الويندوز مش متعرف على مسار البايثون
    try:
        full_path = os.path.join(os.getcwd(), path.strip())
        subprocess.Popen([sys.executable, full_path])
    except Exception as e:
        messagebox.showerror("خطأ", f"تعذر تشغيل الملف:\n{e}")

def make_cmd(fn, *args):
    def _():
        global main
        try:
            # لو الزرار بيفتح سكريبت خارجي (برنامج منفصل)
            if fn.__name__ == 'run_script':
                fn(*args)
            else:
                # لو الزرار بيفتح شاشة داخلية (زي قاعدة المعرفة)
                main.withdraw()
                child = fn(*args) if args else fn()

                if isinstance(child, tk.Toplevel) or isinstance(child, tk.Tk):
                    fade_in(child)
                    child.bind("<Escape>", lambda e: (
                        child.destroy(),
                        main.deiconify(),
                        main.attributes('-fullscreen', True)
                    ))
                    child.protocol("WM_DELETE_WINDOW", lambda: (
                        child.destroy(),
                        main.deiconify(),
                        main.attributes('-fullscreen', True)
                    ))
                    child.focus_set()
                else:
                    main.deiconify()
                    main.attributes('-fullscreen', True)
        except Exception as e:
            messagebox.showerror("خطأ", str(e))
            main.deiconify()
    return _

# ─────────────────────────────────────────────────────────────────────────────
def show_login():
    global root
    root = tk.Tk()
    root.title("MG Management Studio – Login")
    root.configure(bg="#eceff1")
    root.attributes('-fullscreen', True)
    root.resizable(False, False)
    fade_in(root)

    card = tk.Frame(root, bg="white", bd=2, relief="ridge")
    card.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.3, relheight=0.4)

    tk.Label(
        card, text="MG Management Studio",
        font=("Segoe UI", 28, "bold"),
        bg="white", fg="#2C3E50"
    ).pack(pady=(20,15))

    tk.Label(
        card, text="Username", font=("Segoe UI",12,"bold"),
        bg="white", fg="#34495E"
    ).pack(anchor="w", padx=30)
    user_entry = tk.Entry(card, font=("Segoe UI",12))
    user_entry.pack(fill="x", padx=30, pady=(0,10))

    tk.Label(
        card, text="Password", font=("Segoe UI",12,"bold"),
        bg="white", fg="#34495E"
    ).pack(anchor="w", padx=30)
    pass_entry = tk.Entry(card, font=("Segoe UI",12), show="*")
    pass_entry.pack(fill="x", padx=30, pady=(0,20))

    tk.Label(
        card, text="Have a great day! 😊",
        font=("Segoe UI",10),
        bg="white", fg="#27ae60"
    ).pack(side="bottom", pady=(0,10))

    def attempt_login():
        global logged_in_username
        u = user_entry.get().strip()
        p = pass_entry.get()
        if not u or not p:
            messagebox.showwarning("Warning", "Please enter both username and password.")
            return
        try:
            cur = get_connection().cursor()
            cur.execute("SELECT PasswordHash FROM AdminUsers WHERE Username = ?", u)
            row = cur.fetchone()
            if row and hash_password(p) == row[0]:
                logged_in_username = u
                root.withdraw()
                show_main()
            else:
                messagebox.showerror("Error", "Invalid credentials.")
                pass_entry.delete(0, tk.END)
                user_entry.focus_set()
        except Exception as e:
            messagebox.showerror("Error", f"Database error:\n{e}")

    btn_frame = tk.Frame(card, bg="white")
    btn_frame.pack()
    login_btn = tk.Button(
        btn_frame, text="😊 Login", font=("Segoe UI",12,"bold"),
        bg="#3498DB", fg="white", activebackground="#5DADE2",
        width=12, relief="flat", command=attempt_login
    )
    login_btn.pack(side="left", padx=(20,10))

    exit_btn = tk.Button(
        btn_frame, text="🚪 Exit", font=("Segoe UI",12,"bold"),
        bg="#7F8C8D", fg="white", activebackground="#95A5A6",
        width=10, relief="flat", command=root.destroy
    )
    exit_btn.pack(side="left", padx=(10,20))

    root.bind("<Return>", lambda e: attempt_login())
    root.bind("<Escape>", lambda e: root.destroy())
    user_entry.focus_set()
    root.mainloop()

# ─────────────────────────────────────────────────────────────────────────────
def get_enabled_functions():
    global logged_in_username
    try:
        cur = get_connection().cursor()
        cur.execute("""
            SELECT sf.FunctionName, sf.ScriptPath, sf.IsFunction, sf.ColorHex
              FROM SystemFunctions sf
              JOIN UserFunctionAccess ufa ON sf.ID = ufa.FunctionID
              JOIN AdminUsers au ON ufa.UserID = au.ID
             WHERE sf.IsEnabled = 1
               AND ufa.IsVisible = 1
               AND au.Username = ?
        """, logged_in_username)
        return cur.fetchall()
    except:
        return []

# ─────────────────────────────────────────────────────────────────────────────
def show_main():
    global main
    main = tk.Toplevel(root)
    main.title("MG Management Studio – Main Menu")
    main.configure(bg="#ecf0f1")
    main.attributes('-fullscreen', True)
    main.resizable(False, False)
    fade_in(main)

    hdr = tk.Frame(main, bg="#2C3E50", height=60)
    hdr.pack(fill="x")
    tk.Label(
        hdr, text="MG Management Studio",
        font=("Segoe UI",24,"bold"),
        bg="#2C3E50", fg="white"
    ).pack(side="left", padx=20, pady=10)
    tk.Label(
        hdr, text=f"Welcome, {logged_in_username}! 😊",
        font=("Segoe UI",12),
        bg="#2C3E50", fg="white"
    ).pack(side="right", padx=20, pady=10)

    funcs = get_enabled_functions()

    # ⛔ إزالة Stock Management و Inventory تماماً من القائمة
    forbidden = ["stock", "inventory"]
    funcs = [
        f for f in funcs
        if all(word.lower() not in f[0].lower() for word in forbidden)
    ]

    cols = 4
    rows = max((len(funcs)+cols-1)//cols, 1)

    container = tk.Frame(main, bg="#ecf0f1")
    container.pack(expand=True, fill="both", padx=20, pady=20)

    for r in range(rows):
        container.grid_rowconfigure(r, weight=1)
    for c in range(cols):
        container.grid_columnconfigure(c, weight=1)

    for idx, (name, script, is_func, color) in enumerate(funcs):
        r, c = divmod(idx, cols)
        cmd = make_cmd(open_knowledge_window) if is_func else make_cmd(run_script, script)
        btn = tk.Button(
            container, text=name,
            font=("Segoe UI",16,"bold"),
            bg=color or "#3498DB", fg="white",
            relief="flat", command=cmd
        )
        btn.grid(row=r, column=c, sticky="nsew", padx=15, pady=15)

    foot = tk.Frame(main, bg="#ecf0f1", height=60)
    foot.pack(fill="x", side="bottom")
    exit_btn = tk.Button(
        foot, text="🚪 Exit System",
        font=("Segoe UI",12,"bold"),
        bg="#E74C3C", fg="white", activebackground="#EC7063",
        relief="flat", command=main.destroy
    )
    exit_btn.pack(pady=15)
    main.bind("<Escape>", lambda e: main.destroy())

# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    show_login()