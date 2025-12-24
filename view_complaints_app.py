# -*- coding: utf-8 -*-
#!/usr/bin/env python
import sys
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pyodbc
from datetime import datetime
from tkcalendar import DateEntry
import pandas as pd
from complaint_details import ComplaintDetailsApp

class ComplaintManagementSystem:
    def __init__(self):
        self.connect_db()
        self.load_employee_names()
        self.build_gui()

    def connect_db(self):
        try:
            self.conn = pyodbc.connect(
                'DRIVER={ODBC Driver 17 for SQL Server};'
                'SERVER=LAPREFaat;'
                'DATABASE=DrAhmedCRM;'
                'Trusted_Connection=yes;'
            )
            self.cursor = self.conn.cursor()
        except Exception as e:
            tk.Tk().withdraw()
            messagebox.showerror("خطأ في الاتصال", f"فشل الاتصال بقاعدة البيانات:\n{e}")
            sys.exit(1)

    def load_employee_names(self):
        try:
            self.cursor.execute("SELECT EmployeeName FROM Employees WHERE EmployeeName IS NOT NULL")
            self.employee_names = [row[0] for row in self.cursor.fetchall()]
        except Exception:
            self.employee_names = []

    def build_gui(self):
        self.root = tk.Tk()
        self.root.title("إدارة وعرض الشكاوى")
        self.root.state('zoomed')
        self.root.configure(bg="#F3E5F5")

        # زر الخروج
        tk.Button(self.root, text="❌ خروج", bg="#D32F2F", fg="white",
                  font=("Helvetica",12,"bold"), command=self.root.destroy).place(x=10, y=10)

        self.create_header()
        self.create_filters()
        self.create_table()
        self.search_complaints()
        self.root.mainloop()

    def create_header(self):
        frame = tk.Frame(self.root, bg="#F3E5F5", pady=10)
        frame.pack(fill="x")
        tk.Label(frame, text="📋 إدارة وعرض الشكاوى", font=("Helvetica",28,"bold"),
                 fg="#6A1B9A", bg="#F3E5F5").pack(side="left", padx=20)

    def create_filters(self):
        container = tk.Frame(self.root, bg="#F3E5F5")
        container.pack(fill="x", padx=20)
        canvas = tk.Canvas(container, bg="#F3E5F5", height=60, highlightthickness=0)
        h_scroll = tk.Scrollbar(container, orient="horizontal", command=canvas.xview)
        canvas.configure(xscrollcommand=h_scroll.set)
        h_scroll.pack(side="bottom", fill="x")
        canvas.pack(side="top", fill="x", expand=True)
        f = tk.Frame(canvas, bg="#F3E5F5", pady=10)
        canvas.create_window((0,0), window=f, anchor="nw")
        f.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        lbl = ("Helvetica",14)
        wd  = ("Helvetica",12)

        # حالة الشكوى
        tk.Label(f, text="الحالة:", font=lbl, bg="#F3E5F5").grid(row=0, column=0, sticky="e")
        self.status_var = tk.StringVar(value="الكل")
        ttk.Combobox(f, textvariable=self.status_var,
                     values=["الكل","مفتوحة","جاري الحل","مغلقة"],
                     font=wd, width=12).grid(row=0, column=1, padx=5)

        # رقم الهاتف
        tk.Label(f, text="رقم الهاتف:", font=lbl, bg="#F3E5F5").grid(row=0, column=2, sticky="e")
        self.phone_var = tk.StringVar()
        tk.Entry(f, textvariable=self.phone_var, font=wd, width=12).grid(row=0, column=3, padx=5)

        # من تاريخ
        tk.Label(f, text="من تاريخ:", font=lbl, bg="#F3E5F5").grid(row=0, column=4, sticky="e")
        self.start_date = DateEntry(f, font=wd, width=12)
        self.start_date.grid(row=0, column=5, padx=5)

        # إلى تاريخ
        tk.Label(f, text="إلى تاريخ:", font=lbl, bg="#F3E5F5").grid(row=0, column=6, sticky="e")
        self.end_date = DateEntry(f, font=wd, width=12)
        self.end_date.grid(row=0, column=7, padx=5)

        # مدخل الشكوى
        tk.Label(f, text="مدخل:", font=lbl, bg="#F3E5F5").grid(row=0, column=8, sticky="e")
        self.creator_var = tk.StringVar()
        ttk.Combobox(f, textvariable=self.creator_var,
                     values=self.employee_names,
                     font=wd, width=12).grid(row=0, column=9, padx=5)

        # الشيفت
        tk.Label(f, text="الشيفت:", font=lbl, bg="#F3E5F5").grid(row=0, column=10, sticky="e")
        self.shift_var = tk.StringVar(value="الكل")
        ttk.Combobox(f, textvariable=self.shift_var,
                     values=["الكل","Night","Morning","After"],
                     font=wd, width=12).grid(row=0, column=11, padx=5)

        # أزرار البحث والتفاصيل
        tk.Button(f, text="🔍 بحث", bg="#1976D2", fg="white",
                  font=("Helvetica",12,"bold"), command=self.search_complaints)\
          .grid(row=0, column=12, padx=5)
        tk.Button(f, text="تفاصيل", bg="#FF8F00", fg="white",
                  font=("Helvetica",12,"bold"), command=self.open_details)\
          .grid(row=0, column=13, padx=5)

        # تحديث الحالة
        tk.Label(f, text="تحديث الحالة:", font=lbl, bg="#F3E5F5")\
          .grid(row=0, column=14, sticky="e", padx=5)
        self.status_update_var = tk.StringVar(value="مفتوحة")
        ttk.Combobox(f, textvariable=self.status_update_var,
                     values=["مفتوحة","جاري الحل","مغلقة"],
                     font=wd, width=12).grid(row=0, column=15, padx=5)
        tk.Button(f, text="💾 حفظ الحالة", bg="#00897B", fg="white",
                  font=("Helvetica",12,"bold"), command=self.save_status)\
          .grid(row=0, column=16, padx=5)

        # تصدير إلى Excel
        tk.Button(f, text="📥 تصدير إلى Excel", bg="#3949AB", fg="white",
                  font=("Helvetica",12,"bold"), command=self.export_to_excel)\
          .grid(row=0, column=17, padx=5)

    def create_table(self):
        style = ttk.Style(self.root)
        style.theme_use('clam')
        style.configure("Treeview", font=("Helvetica",12), rowheight=28,
                        background="#FFFFFF", fieldbackground="#FFFFFF")
        style.configure("Treeview.Heading", font=("Helvetica",14,"bold"),
                        background="#CE93D8", foreground="white")
        style.map('Treeview', background=[('selected','#B39DDB')])

        cols = (
            "ID",
            "رقم العميل",
            "اسم العميل",
            "نوع الشكوى",
            "التاريخ",
            "الحالة",
            "الفرع",
            "اسم المدخل",
            "الشيفت"
        )
        self.tree = ttk.Treeview(self.root, columns=cols, show="headings")
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, anchor="center")
        self.tree.tag_configure('odd', background='#F3E5F5')
        self.tree.tag_configure('even', background='#FFFFFF')
        self.tree.tag_configure('alert', background='#FFF176')

        vsb = tk.Scrollbar(self.root, orient="vertical", command=self.tree.yview)
        hsb = tk.Scrollbar(self.root, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        self.tree.pack(fill="both", expand=True, padx=20, pady=(0,20))
        self.tree.bind("<Double-1>", lambda e: self.open_details())

    def search_complaints(self):
        fd = self.start_date.get_date()
        td = self.end_date.get_date()

        # الآن ننضم إلى Customers عبر تطابق رقم الهاتف وننشئ اسم العميل من FirstName + LastName
        q = (
            "SELECT "
            "c.ComplaintID, "
            "c.PhoneNumber, "
            "ISNULL(cust.FirstName,'') + ' ' + ISNULL(cust.LastName,'') AS CustomerName, "
            "c.ComplaintType, "
            "c.ComplaintDate, "
            "c.ComplaintStatus, "
            "b.BranchName, "
            "c.CreatedByName, "
            "c.Shift "
            "FROM Complaints c "
            "LEFT JOIN Branches b ON c.BranchCode = b.BranchCode "
            "LEFT JOIN Customers cust ON c.PhoneNumber = cust.PhoneNumber "
            "WHERE CAST(c.ComplaintDate AS DATE) BETWEEN ? AND ?"
        )
        params = [fd, td]

        if self.status_var.get() != "الكل":
            q += " AND c.ComplaintStatus = ?"; params.append(self.status_var.get())
        if self.phone_var.get().strip():
            q += " AND c.PhoneNumber LIKE ?"; params.append(f"%{self.phone_var.get()}%")
        if self.creator_var.get().strip():
            q += " AND c.CreatedByName LIKE ?"; params.append(f"%{self.creator_var.get()}%")
        if self.shift_var.get() != "الكل":
            q += " AND c.Shift = ?"; params.append(self.shift_var.get())

        self.cursor.execute(q, params)
        rows = self.cursor.fetchall()

        self.tree.delete(*self.tree.get_children())
        now = datetime.now()
        for i, r in enumerate(rows):
            tag = 'even' if i % 2 == 0 else 'odd'
            if r.ComplaintStatus == 'مفتوحة' and (now - r.ComplaintDate).days >= 1:
                tag = 'alert'
            dt_str = r.ComplaintDate.strftime('%Y-%m-%d %H:%M')
            self.tree.insert('', 'end',
                values=(
                    r.ComplaintID,
                    r.PhoneNumber,
                    r.CustomerName,
                    r.ComplaintType,
                    dt_str,
                    r.ComplaintStatus,
                    r.BranchName,
                    r.CreatedByName,
                    r.Shift
                ),
                tags=(tag,)
            )

    def open_details(self):
        sel = self.tree.selection()
        if not sel:
            return messagebox.showwarning("اختيار", "اختر شكوى أولاً")
        cid = self.tree.item(sel[0])['values'][0]
        # 🌟 التعديل هنا: تمرير الشاشة الحالية كـ parent
        ComplaintDetailsApp(cid, parent=self.root)

    def save_status(self):
        sel = self.tree.selection()
        if not sel:
            return messagebox.showwarning("اختيار", "اختر شكوى لتحديث الحالة")
        cid = self.tree.item(sel[0])['values'][0]
        new = self.status_update_var.get()
        try:
            self.cursor.execute(
                "UPDATE Complaints SET ComplaintStatus = ?, LastModified = GETDATE() WHERE ComplaintID = ?",
                new, cid
            )
            self.conn.commit()
            messagebox.showinfo("تم", "تم تحديث الحالة")
            self.search_complaints()
        except Exception as e:
            messagebox.showerror("خطأ", "فشل التحديث:\n" + str(e))

    def export_to_excel(self):
        cols = self.tree['columns']
        data = [self.tree.item(i)['values'] for i in self.tree.get_children()]
        df = pd.DataFrame(data, columns=cols)
        file = filedialog.asksaveasfilename(defaultextension='.xlsx',
                                            filetypes=[('Excel','*.xlsx')])
        if file:
            df.to_excel(file, index=False)
            messagebox.showinfo('✅', 'تم تصدير البيانات إلى Excel بنجاح')

if __name__ == '__main__':
    try:
        ComplaintManagementSystem()
    except Exception as ex:
        import traceback
        traceback.print_exc()
        tk.Tk().withdraw()
        messagebox.showerror("Error", str(ex))