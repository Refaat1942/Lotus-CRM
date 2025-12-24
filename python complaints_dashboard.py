# -*- coding: utf-8 -*-
#!/usr/bin/env python
import sys
import tkinter as tk
from tkinter import ttk, messagebox

# التعامل مع المكتبات المفقودة
try:
    from tkcalendar import DateEntry
except ImportError:
    tk.Tk().withdraw()
    messagebox.showerror("خطأ", "المكتبة tkcalendar غير مثبتة. الرجاء تشغيل:\npip install tkcalendar")
    sys.exit(1)

try:
    import pyodbc
except ImportError:
    tk.Tk().withdraw()
    messagebox.showerror("خطأ", "المكتبة pyodbc غير مثبتة. الرجاء تشغيل:\npip install pyodbc")
    sys.exit(1)

try:
    import matplotlib.pyplot as plt
    from matplotlib import rcParams
except ImportError:
    tk.Tk().withdraw()
    messagebox.showerror("خطأ", "المكتبة matplotlib غير مثبتة. الرجاء تشغيل:\npip install matplotlib")
    sys.exit(1)

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
except ImportError:
    tk.Tk().withdraw()
    messagebox.showerror("خطأ", "المكتبات arabic_reshaper و python-bidi غير مثبتة. الرجاء تشغيل:\npip install arabic_reshaper python-bidi")
    sys.exit(1)

from datetime import datetime

# ======== اتصال بقاعدة البيانات ========
try:
    conn = pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=LAPREFaat;'
        'DATABASE=DrAhmedCRM;'
        'Trusted_Connection=yes;'
    )
    cursor = conn.cursor()
except Exception as e:
    tk.Tk().withdraw()
    messagebox.showerror("❌ خطأ في الاتصال", f"فشل الاتصال بقاعدة البيانات:\n{e}")
    sys.exit(1)

# ======== مساعدة إعادة تشكيل العربي ========
def reshape(text):
    return get_display(arabic_reshaper.reshape(text))

# ======== جلب البيانات ========
def fetch_branches():
    cursor.execute("SELECT BranchCode, BranchName FROM Branches ORDER BY BranchName")
    return [f"{r.BranchCode} - {r.BranchName}" for r in cursor.fetchall()]

def fetch_statuses():
    cursor.execute("SELECT DISTINCT ComplaintStatus FROM Complaints")
    return [row[0] for row in cursor.fetchall()]

def fetch_dashboard_data(fd, td, bc, st):
    q = ["SELECT ComplaintStatus, COUNT(*) AS cnt FROM Complaints WHERE ComplaintDate BETWEEN ? AND ?"]
    params = [fd, td]
    if bc and bc != 'كل الفروع':
        q.append("AND BranchCode = ?"); params.append(bc)
    if st and st != 'كل الحالات':
        q.append("AND ComplaintStatus = ?"); params.append(st)
    q.append("GROUP BY ComplaintStatus")
    cursor.execute(' '.join(q), *params)
    return cursor.fetchall()

# ======== رسم المخطط ========
def draw_dashboard():
    fd = from_entry.get_date()
    td = to_entry.get_date()
    if fd > td:
        messagebox.showwarning('تنبيه', 'تأكد من ترتيب التواريخ')
        return
    bc = branch_var.get().split(' - ')[0] if branch_var.get() != 'كل الفروع' else None
    st = status_var.get()
    data = fetch_dashboard_data(fd, td, bc, st)
    if not data:
        messagebox.showinfo('معلومة', 'لا توجد بيانات للفلاتر المحددة')
        return
    labels = [reshape(r.ComplaintStatus) for r in data]
    sizes  = [r.cnt for r in data]
    rcParams['font.family'] = 'Arial'
    plt.figure(figsize=(8,6), facecolor='#fdfdfd')
    plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90,
            wedgeprops={'linewidth':2,'edgecolor':'white'})
    plt.setp(plt.gca().texts, color='#333333', fontsize=12)
    plt.title(reshape('توزيع حالات الشكاوى'), fontsize=16, color='#4A148C')
    plt.axis('equal')
    plt.tight_layout()
    plt.show()

# ======== بناء الواجهة ========
root = tk.Tk()
root.title('📊 Dashboard - حالات الشكاوى')
root.configure(bg='#ECEFF1')
root.geometry('650x350')

style = ttk.Style(root)
style.theme_use('clam')
style.configure('TFrame', background='#ECEFF1')
style.configure('TLabel', background='#ECEFF1', font=('Segoe UI',11))
style.configure('Header.TLabel', font=('Segoe UI',16,'bold'), foreground='#512DA8')
style.configure('Filter.TLabelframe', background='#FAFAFA', borderwidth=1, relief='solid')
style.configure('TButton', font=('Segoe UI',11,'bold'), background='#512DA8', foreground='white')
style.map('TButton', background=[('active','#673AB7')])
style.configure('TCombobox', font=('Segoe UI',11))

# عنوان
ttk.Label(root, text='📊 فلترة وعرض حالات الشكاوى', style='Header.TLabel').pack(pady=15)

# إطار الفلاتر
ff = ttk.Labelframe(root, text='فلترة البيانات', style='Filter.TLabelframe', padding=15)
ff.pack(fill='x', padx=20)

# التاريخ
ttk.Label(ff, text='من:').grid(row=0, column=0, padx=5, pady=5)
from_entry = DateEntry(ff, date_pattern='yyyy-MM-dd', width=12)
from_entry.grid(row=0, column=1, padx=5)

ttk.Label(ff, text='إلى:').grid(row=0, column=2, padx=5)
to_entry = DateEntry(ff, date_pattern='yyyy-MM-dd', width=12)
to_entry.grid(row=0, column=3, padx=5)

# الفرع
ttk.Label(ff, text='الفرع:').grid(row=1, column=0, sticky='e', padx=5, pady=5)
branch_var = tk.StringVar()
branch_list = ['كل الفروع'] + fetch_branches()
br_combo = ttk.Combobox(ff, textvariable=branch_var, values=branch_list, state='readonly', width=30)
br_combo.grid(row=1, column=1, columnspan=3, padx=5, pady=5, sticky='w')
br_combo.current(0)

# الحالة
ttk.Label(ff, text='الحالة:').grid(row=2, column=0, sticky='e', padx=5, pady=5)
status_var = tk.StringVar()
status_list = ['كل الحالات'] + fetch_statuses()
st_combo = ttk.Combobox(ff, textvariable=status_var, values=status_list, state='readonly', width=30)
st_combo.grid(row=2, column=1, columnspan=3, padx=5, pady=5, sticky='w')
st_combo.current(0)

# أزرار العرض والخروج
bf = ttk.Frame(root)
bf.pack(pady=20)

ttk.Button(bf, text='عرض Dashboard', command=draw_dashboard).grid(row=0, column=0, padx=10)
ttk.Button(bf, text='❌ خروج', command=root.destroy).grid(row=0, column=1, padx=10)

root.mainloop()
