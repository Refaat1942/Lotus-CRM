# -*- coding: utf-8 -*-
#!/usr/bin/env python

import tkinter as tk
from tkinter import ttk, messagebox
import pyodbc
from datetime import datetime
import argparse
import sys


def connect_db():
    """
    اتصال بقاعدة DrAhmedCRM عبر ODBC.
    عدّل نص الاتصال لبيئتك إذا لزم.
    """
    try:
        conn = pyodbc.connect(
            'DRIVER={ODBC Driver 17 for SQL Server};'
            'SERVER=LAPREFaat;'
            'DATABASE=DrAhmedCRM;'
            'Trusted_Connection=yes;'
        )
        return conn, conn.cursor()
    except Exception as e:
        tk.Tk().withdraw()
        messagebox.showerror("خطأ اتصال DB", str(e))
        sys.exit(1)

class ComplaintDetailsApp:
    # 🌟 التعديل هنا: إضافة parent عشان نمنع فتح mainloop جديد
    def __init__(self, complaint_id, parent=None):
        self.complaint_id = complaint_id
        self.conn, self.cursor = connect_db()
        self.employee_names = self._fetch_employee_names()
        self.data = self._fetch_complaint_data()

        # إنشاء الواجهة بناءً على طريقة الاستدعاء
        if parent:
            self.root = tk.Toplevel(parent)
        else:
            self.root = tk.Tk()
            self._setup_style() # الستايل يتحمل بس لو برنامج منفصل

        self.root.title(f"🔍 تفاصيل الشكوى #{complaint_id}")
        self.root.configure(bg="#F3E5F5")
        self.build_gui()
        
        # لو شغالة لوحدها بس نعمل mainloop
        if not parent:
            self.root.mainloop()

    def _setup_style(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TLabelframe", background="#FFFFFF", borderwidth=1, relief="solid")
        style.configure("TLabelframe.Label", font=("Segoe UI", 14, "bold"), foreground="#6A1B9A")
        style.configure("TLabel", background="#FFFFFF", font=("Segoe UI", 12))
        style.configure("TButton", font=("Segoe UI", 12, "bold"))
        style.configure("TCombobox", font=("Segoe UI", 12))
        style.configure("Treeview.Heading", font=("Segoe UI", 12, "bold"), background="#CE93D8", foreground="white")
        style.configure("Treeview", font=("Segoe UI", 11), rowheight=24)

    def _fetch_employee_names(self):
        """جلب أسماء الموظفين لتعبئة الـ Combobox"""
        self.cursor.execute("SELECT EmployeeName FROM Employees WHERE EmployeeName IS NOT NULL ORDER BY EmployeeName")
        return [row[0] for row in self.cursor.fetchall()]

    def _fetch_complaint_data(self):
        """
        جلب بيانات الشكوى الأساسية وسجل التحديثات من جدول ComplaintDetails
        ويتضمن الآن عمود OnlineChannel
        """
        # بيانات الشكوى الرئيسية مع OnlineChannel
        self.cursor.execute("""
            SELECT ComplaintText, ComplaintDate, ComplaintStatus,
                   BranchCode, CreatedByName, OnlineChannel
            FROM Complaints
            WHERE ComplaintID = ?
        """, self.complaint_id)
        row = self.cursor.fetchone()
        if not row:
            tk.messagebox.showerror("خطأ", f"لم أجد شكوى بالمعرّف {self.complaint_id}")
            sys.exit(1)

        original, dt, status, branch_code, creator, online_ch = row
        original = original.strip()

        # اسم الفرع
        self.cursor.execute("SELECT BranchName FROM Branches WHERE BranchCode = ?", branch_code)
        br = self.cursor.fetchone()
        branch = br[0] if br else branch_code

        # سجل التحديثات
        self.cursor.execute("""
            SELECT DetailDate, Modifier, DetailText
            FROM ComplaintDetails
            WHERE ComplaintID = ?
            ORDER BY DetailDate
        """, self.complaint_id)
        history = [
            {'date': d.strftime('%Y-%m-%d'), 'modifier': m, 'text': txt}
            for d, m, txt in self.cursor.fetchall()
        ]

        return {
            'original': original,
            'date': dt.strftime('%Y-%m-%d %H:%M'),
            'status': status,
            'branch': branch,
            'creator': creator,
            'online_channel': online_ch or '—',
            'history': history
        }

    def build_gui(self):
        # --- نص الشكوى الأصلية ---
        f1 = ttk.LabelFrame(self.root, text="نص الشكوى الأصلية", padding=10)
        f1.pack(fill="x", padx=20, pady=(20, 10))
        t1 = tk.Text(f1, wrap="word", height=5, font=("Segoe UI", 11), bd=0)
        t1.insert("1.0", self.data['original'])
        t1.configure(state="disabled", bg="#FFFFFF")
        t1.pack(fill="both", expand=True)

        # --- معلومات الشكوى ---
        f2 = ttk.LabelFrame(self.root, text="معلومات الشكوى", padding=10)
        f2.pack(fill="x", padx=20, pady=10)
        labels = ["التاريخ والوقت", "المدخل", "الحالة", "الفرع", "القناة الإلكترونية"]
        values = [
            self.data['date'], self.data['creator'], self.data['status'],
            self.data['branch'], self.data['online_channel']
        ]
        for i, (lab, val) in enumerate(zip(labels, values)):
            ttk.Label(f2, text=f"{lab}:").grid(row=i, column=0, sticky="e", padx=5, pady=4)
            ttk.Label(f2, text=val).grid(row=i, column=1, sticky="w", padx=5, pady=4)

        # --- إضافة تحديث جديد ---
        f3 = ttk.LabelFrame(self.root, text="إضافة تحديث للشكوى", padding=10)
        f3.pack(fill="x", padx=20, pady=10)
        ttk.Label(f3, text="اسم المدخل:").grid(row=0, column=0, sticky="e", padx=5, pady=4)
        self.modifier_var = tk.StringVar(value=self.data['creator'])
        ttk.Combobox(f3, textvariable=self.modifier_var, values=self.employee_names,
                     state="readonly", width=30).grid(row=0, column=1, sticky="w", padx=5, pady=4)

        ttk.Label(f3, text="نص التحديث:").grid(row=1, column=0, sticky="ne", padx=5, pady=4)
        self.update_txt = tk.Text(f3, wrap="word", height=4, font=("Segoe UI", 11), bd=1, relief="solid")
        self.update_txt.grid(row=1, column=1, padx=5, pady=4, sticky="we")
        f3.columnconfigure(1, weight=1)

        # --- سجل التحديثات ---
        f4 = ttk.LabelFrame(self.root, text="سجل التحديثات", padding=10)
        f4.pack(fill="both", expand=True, padx=20, pady=(10, 20))
        cols = ("التاريخ", "المدخل", "نص التحديث")
        self.hist_tree = ttk.Treeview(f4, columns=cols, show="headings", height=6)
        for c in cols:
            self.hist_tree.heading(c, text=c)
            self.hist_tree.column(c, anchor="w")
        for e in self.data['history']:
            self.hist_tree.insert('', 'end', values=(e['date'], e['modifier'], e['text']))
        self.hist_tree.pack(fill="both", expand=True, side="left")
        ttk.Scrollbar(f4, command=self.hist_tree.yview).pack(side="right", fill="y")
        self.hist_tree.configure(yscrollcommand=lambda f, s: s)

        # --- الأزرار ---
        btns = tk.Frame(self.root, bg="#F3E5F5")
        btns.pack(pady=(0, 20))
        ttk.Button(btns, text="💾 حفظ التحديث", command=self.save_update).pack(side="left", padx=10)
        ttk.Button(btns, text="🔒 إغلاق",     command=self.root.destroy).pack(side="left", padx=10)

    def save_update(self):
        txt = self.update_txt.get("1.0", "end").strip()
        mod = self.modifier_var.get().strip()
        if not txt or not mod:
            messagebox.showwarning("تنبيه", "أكمل اسم المدخل ونص التحديث")
            return

        try:
            self.cursor.execute(
                "INSERT INTO ComplaintDetails (ComplaintID, Modifier, DetailText) VALUES (?, ?, ?)",
                self.complaint_id, mod, txt
            )
            self.conn.commit()

            ts = datetime.now().strftime('%Y-%m-%d')
            self.hist_tree.insert('', 'end', values=(ts, mod, txt))
            self.update_txt.delete("1.0", "end")
            messagebox.showinfo("تم", "تم حفظ التحديث بنجاح")
        except Exception as e:
            messagebox.showerror("خطأ أثناء الحفظ", str(e))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="عرض تفاصيل شكوى وإضافة تحديثات")
    parser.add_argument("complaint_id", type=int, help="رقم الشكوى")
    args = parser.parse_args()
    ComplaintDetailsApp(args.complaint_id)