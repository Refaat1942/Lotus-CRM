# -*- coding: utf-8 -*-
"""
complaints_app.py

Tkinter GUI for recording new complaints to SQL Server and
sending notification emails via Microsoft Graph (MSAL client-credential flow).

Run this script from a console or via a .bat wrapper with PAUSE
so you can see any errors before the window closes.
"""

import sys
import traceback
import os
import tkinter as tk
from tkinter import messagebox, ttk
import pyodbc
from datetime import datetime
import msal
import requests

# ──────────────── Azure AD values from environment ────────────────
TENANT_ID     = os.getenv("AZURE_TENANT_ID", "")
CLIENT_ID     = os.getenv("AZURE_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET", "")
FROM_ADDRESS  = os.getenv("NOTIFICATION_EMAIL", "")
# ──────────────────────────────────────────────────────────────────

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPE     = ["https://graph.microsoft.com/.default"]


def graph_send_email(from_addr, to_addrs, cc_addrs, subject, body):
    """Acquire token and send an email via Microsoft Graph."""
    app = msal.ConfidentialClientApplication(
        client_id=CLIENT_ID,
        authority=AUTHORITY,
        client_credential=CLIENT_SECRET
    )
    token = app.acquire_token_for_client(scopes=SCOPE)
    if "access_token" not in token:
        raise RuntimeError("Authentication failed:\n" + token.get("error_description","<no details>"))

    payload = {
        "message": {
            "subject": subject,
            "body": {"contentType": "Text", "content": body},
            "toRecipients":   [{"emailAddress": {"address": addr}} for addr in to_addrs],
            "ccRecipients":   [{"emailAddress": {"address": addr}} for addr in cc_addrs],
        },
        "saveToSentItems": "true"
    }

    url = f"https://graph.microsoft.com/v1.0/users/{from_addr}/sendMail"
    resp = requests.post(
        url,
        headers={
            "Authorization": "Bearer " + token["access_token"],
            "Content-Type":  "application/json"
        },
        json=payload
    )
    if not resp.ok:
        raise RuntimeError(f"Graph sendMail failed: {resp.status_code} – {resp.text}")


def send_notification(branch_code, details):
    """Look up branch manager / area / sales emails and send notification."""
    cursor.execute("""
        SELECT BranchManagerEmail, AreaManagerEmail, SalesManagerEmail
          FROM dbo.Branches
         WHERE BranchCode = ?
    """, (branch_code,))
    mgr, area, sales = cursor.fetchone()

    subject = f"New complaint at branch {branch_code}"
    body    = (
        f"A new complaint was logged at branch {branch_code}:\n\n"
        f"{details}\n\n"
        f"Time: {datetime.now():%Y-%m-%d %H:%M}"
    )

    graph_send_email(FROM_ADDRESS, [mgr], [area, sales], subject, body)


def main():
    # ─── Connect to SQL Server ──────────────────────────────────────
    try:
        global conn, cursor
        conn = pyodbc.connect(
            'DRIVER={ODBC Driver 17 for SQL Server};'
            'SERVER=LAPREFaat;DATABASE=DrAhmedCRM;'
            'Trusted_Connection=yes;'
        )
        cursor = conn.cursor()
    except Exception as e:
        tk.Tk().withdraw()
        messagebox.showerror("Database Error", f"Cannot connect to database:\n{e}")
        return

    # ─── Helper to fetch customer by phone ─────────────────────────
    def fetch_customer_info(event=None):
        phone = phone_var.get().strip()
        if not phone:
            customer_info_label.config(text="Enter phone number", fg="orange")
            return
        try:
            cursor.execute(
                "SELECT FirstName, LastName FROM dbo.Customers WHERE PhoneNumber = ?",
                phone
            )
            row = cursor.fetchone()
            if row:
                customer_info_label.config(text=f"{row.FirstName} {row.LastName}", fg="green")
            else:
                customer_info_label.config(text="Customer not found", fg="red")
        except Exception as e:
            customer_info_label.config(text=f"Error: {e}", fg="red")

    def load_online_channels():
        return ["Instashop", "Talabat", "Chefaa", "Website", "Lotus Pharmacies App"]

    # ─── Build the GUI ─────────────────────────────────────────────
    root = tk.Tk()
    root.title("📝 تسجيل شكوى جديدة")
    root.attributes('-fullscreen', True)
    root.configure(bg='#EDE7F6')

    tk.Label(
        root,
        text="📝 تسجيل شكوى جديدة",
        font=("Arial", 26, "bold"),
        fg="#4A148C",
        bg='#EDE7F6'
    ).pack(pady=20)

    customer_info_label = tk.Label(root, text="", font=("Arial", 14), bg='#EDE7F6')
    customer_info_label.pack(pady=5)

    frm = tk.Frame(root, bg='#EDE7F6')
    frm.pack(pady=10)

    # Fetch employees and branches
    cursor.execute("SELECT EmployeeCode, EmployeeName FROM dbo.Employees")
    employees = [f"{r.EmployeeCode} - {r.EmployeeName}" for r in cursor.fetchall()]

    cursor.execute("SELECT BranchCode, BranchName FROM dbo.Branches")
    branches = [f"{r.BranchCode} - {r.BranchName}" for r in cursor.fetchall()]

    sel_emp    = tk.StringVar()
    sel_br     = tk.StringVar()
    phone_var  = tk.StringVar()
    type_var   = tk.StringVar()
    online_var = tk.StringVar()

    # Employee dropdown
    tk.Label(frm, text="الموظف:", font=("Arial", 16), bg='#EDE7F6')\
      .grid(row=0, column=0, sticky='e', padx=10, pady=8)
    ttk.Combobox(frm, textvariable=sel_emp, values=employees,
                 font=("Arial", 16), width=40, state='readonly')\
      .grid(row=0, column=1)

    # Branch dropdown
    tk.Label(frm, text="الفرع:", font=("Arial", 16), bg='#EDE7F6')\
      .grid(row=1, column=0, sticky='e', padx=10, pady=8)
    ttk.Combobox(frm, textvariable=sel_br, values=branches,
                 font=("Arial", 16), width=40, state='readonly')\
      .grid(row=1, column=1)

    # Phone + search
    tk.Label(frm, text="رقم العميل:", font=("Arial", 16), bg='#EDE7F6')\
      .grid(row=2, column=0, sticky='e', padx=10, pady=8)
    phone_entry = tk.Entry(frm, textvariable=phone_var, font=("Arial", 16), width=30)
    phone_entry.grid(row=2, column=1)
    phone_entry.bind("<Return>", fetch_customer_info)
    tk.Button(frm, text="🔍 بحث", font=("Arial", 12),
              bg="#2196F3", fg="white", command=fetch_customer_info)\
      .grid(row=2, column=2, padx=5)

    # Complaint type
    tk.Label(frm, text="نوع الشكوى:", font=("Arial", 16), bg='#EDE7F6')\
      .grid(row=3, column=0, sticky='e', padx=10, pady=8)
    types = [
        "تأخير", "منتج خاطئ", "معاملة سيئة", "أخرى",
        "نقص ادويه", "بديل غير مناسب", "مشكلة اون لاين"
    ]
    cmb_type = ttk.Combobox(frm, textvariable=type_var, values=types,
                             font=("Arial", 16), width=28, state='readonly')
    cmb_type.grid(row=3, column=1)
    cmb_type.current(0)

    # Online channel (shown only if type is "مشكلة اون لاين")
    online_lbl = tk.Label(frm, text="القناة الإلكترونية:", font=("Arial", 16), bg='#EDE7F6')
    online_cmb = ttk.Combobox(frm, textvariable=online_var, values=[],
                              font=("Arial", 16), width=28, state='readonly')
    online_lbl.grid(row=4, column=0, sticky='e', padx=10, pady=8)
    online_cmb.grid(row=4, column=1)
    online_lbl.grid_remove()
    online_cmb.grid_remove()

    def on_type_change(event=None):
        if type_var.get() == "مشكلة اون لاين":
            online_cmb['values'] = load_online_channels()
            online_cmb.current(0)
            online_lbl.grid()
            online_cmb.grid()
        else:
            online_lbl.grid_remove()
            online_cmb.grid_remove()

    cmb_type.bind("<<ComboboxSelected>>", on_type_change)

    # Complaint text
    tk.Label(frm, text="الشكوى:", font=("Arial", 16), bg='#EDE7F6')\
      .grid(row=5, column=0, sticky='ne', padx=10, pady=8)
    txt_area = tk.Text(frm, font=("Arial", 14), height=5, width=40)
    txt_area.grid(row=5, column=1, pady=8)

    # Save & send handler
    def save_complaint():
        if not sel_emp.get() or not sel_br.get():
            messagebox.showwarning("تنبيه", "يرجى اختيار الموظف والفرع")
            return

        phone = phone_var.get().strip()
        text  = txt_area.get("1.0", tk.END).strip()
        ctype = type_var.get()
        channel = online_var.get() if ctype == "مشكلة اون لاين" else None

        if not phone or not text:
            messagebox.showwarning("تنبيه", "يرجى إدخال رقم العميل ونص الشكوى")
            return

        emp_code, emp_name = sel_emp.get().split(" - ", 1)
        br_code            = sel_br.get().split(" - ", 1)[0]
        now = datetime.now()
        shift = "Night" if now.hour < 8 else "Morning" if now.hour < 16 else "After"

        try:
            if channel:
                sql = (
                    "INSERT INTO Complaints "
                    "(PhoneNumber,ComplaintType,OnlineChannel,ComplaintText,"
                    "ComplaintDate,ComplaintStatus,CreatedByCode,CreatedByName,"
                    "BranchCode,Shift) VALUES (?,?,?,?,?,?,?,?,?,?)"
                )
                params = (phone, ctype, channel, text, now, "مفتوحة",
                          emp_code, emp_name, br_code, shift)
            else:
                sql = (
                    "INSERT INTO Complaints "
                    "(PhoneNumber,ComplaintType,ComplaintText,"
                    "ComplaintDate,ComplaintStatus,CreatedByCode,CreatedByName,"
                    "BranchCode,Shift) VALUES (?,?,?,?,?,?,?,?,?)"
                )
                params = (phone, ctype, text, now, "مفتوحة",
                          emp_code, emp_name, br_code, shift)

            cursor.execute(sql, params)
            conn.commit()

            try:
                details = (
                    f"Employee: {emp_code} – {emp_name}\n"
                    f"Phone   : {phone}\n"
                    f"Type    : {ctype}\n"
                    f"Branch  : {br_code}\n"
                    f"Shift   : {shift}\n\n"
                    f"Text:\n{text}"
                )
                send_notification(br_code, details)
            except Exception as mail_err:
                messagebox.showwarning("Email failed", str(mail_err))

            messagebox.showinfo("نجاح", "تم حفظ الشكوى بنجاح")
            root.destroy()
        except Exception as e:
            conn.rollback()
            messagebox.showerror("خطأ", str(e))

    # Styled save button
    tk.Button(
        root,
        text="💾 حفظ الشكوى",
        font=("Arial", 16, "bold"),
        bg="#4CAF50",
        fg="white",
        activebackground="#45A049",
        relief="flat",
        padx=20,
        pady=10,
        command=save_complaint
    ).pack(pady=20)

    # Styled exit button
    tk.Button(
        root,
        text="❌ خروج",
        font=("Arial", 14, "bold"),
        bg="#f44336",
        fg="white",
        activebackground="#e53935",
        relief="flat",
        padx=15,
        pady=8,
        command=root.destroy
    ).place(x=20, y=20)

    root.bind("<Escape>", lambda e: root.destroy())
    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        tk.Tk().withdraw()
        messagebox.showerror("Fatal Error", "An unexpected error occurred.")
        input("Press Enter to exit…")