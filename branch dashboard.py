# -*- coding: utf-8 -*-
#!/usr/bin/env python
import sys
import tkinter as tk
from tkinter import ttk, messagebox
# مكتبات التاريخ
try:
    from tkcalendar import DateEntry
except ImportError:
    tk.Tk().withdraw()
    messagebox.showerror("خطأ", "المكتبة tkcalendar غير مثبتة. الرجاء تشغيل:\npip install tkcalendar")
    sys.exit(1)
# اتصال بقاعدة البيانات
try:
    import pyodbc
except ImportError:
    tk.Tk().withdraw()
    messagebox.showerror("خطأ", "المكتبة pyodbc غير مثبتة. الرجاء تشغيل:\npip install pyodbc")
    sys.exit(1)
# matplotlib
try:
    import matplotlib.pyplot as plt
    from matplotlib import rcParams
except ImportError:
    tk.Tk().withdraw()
    messagebox.showerror("خطأ", "المكتبة matplotlib غير مثبتة. الرجاء تشغيل:\npip install matplotlib")
    sys.exit(1)
# عربى
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
except ImportError:
    tk.Tk().withdraw()
    messagebox.showerror("خطأ", "المكتبات arabic_reshaper و python-bidi غير مثبتة. الرجاء تشغيل:\npip install arabic_reshaper python-bidi")
    sys.exit(1)
from datetime import datetime

# ======== اتصال DB ========
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
    messagebox.showerror("خطأ في الاتصال", f"فشل الاتصال بقاعدة البيانات:\n{e}")
    sys.exit(1)

# ======== مساعدة النص العربي ========
def reshape(text):
    return get_display(arabic_reshaper.reshape(text))

# ======== جلب بيانات ========
def fetch_branches():
    cursor.execute("SELECT BranchCode, BranchName FROM Branches ORDER BY BranchName")
    return [f"{r.BranchCode} - {r.BranchName}" for r in cursor.fetchall()]

def fetch_statuses():
    cursor.execute("SELECT DISTINCT ComplaintStatus FROM Complaints")
    return [row[0] for row in cursor.fetchall()]

# جلب عدد الشكاوى حسب الفرع
# مع فلترة بالتاريخ والفرع والحالة

def fetch_branch_data(fd, td, br_code, status):
    parts = ["SELECT b.BranchName, COUNT(*) AS cnt FROM Complaints c",
             "LEFT JOIN Branches b ON c.BranchCode=b.BranchCode",
             "WHERE c.ComplaintDate BETWEEN ? AND ?"]
    params = [fd, td]
    if br_code and br_code!='كل الفروع':
        parts.append("AND c.BranchCode=?"); params.append(br_code)
    if status and status!='كل الحالات':
        parts.append("AND c.ComplaintStatus=?"); params.append(status)
    parts.append("GROUP BY b.BranchName")
    sql = ' '.join(parts)
    cursor.execute(sql, *params)
    return cursor.fetchall()

# ======== رسم الرسم البياني ========
def draw_dashboard():
    fd = from_entry.get_date(); td = to_entry.get_date()
    if fd>td:
        messagebox.showwarning('تنبيه','تأكد من ترتيب التواريخ')
        return
    br = branch_var.get().split(' - ')[0] if branch_var.get()!='كل الفروع' else None
    st = status_var.get()
    data = fetch_branch_data(fd, td, br, st)
    if not data:
        messagebox.showinfo('معلومة','لا توجد بيانات')
        return
    labels = [reshape(r.BranchName or 'غير محدد') for r in data]
    sizes  = [r.cnt for r in data]
    rcParams['font.family']='Arial'
    fig, ax = plt.subplots(figsize=(10,6), facecolor='#f9f9f9')
    bars = ax.bar(labels, sizes, color='#42A5F5', edgecolor='#ffffff', linewidth=1)
    ax.set_title(reshape('عدد الشكاوى حسب الفرع'), fontsize=16, color='#1E88E5')
    ax.set_ylabel(reshape('عدد الشكاوى'))
    ax.tick_params(axis='x', rotation=45)
    ax.grid(axis='y', linestyle='--', alpha=0.5)
    plt.tight_layout(); plt.show()

# ======== بناء الواجهة ========
root = tk.Tk()
root.title('📊 Dashboard - شكاوى الفروع')
root.configure(bg='#EEEEEE')
root.geometry('700x360')

style = ttk.Style(root)
style.theme_use('clam')
style.configure('TLabel',background='#EEEEEE',font=('Segoe UI',11))
style.configure('Header.TLabel',font=('Segoe UI',16,'bold'),foreground='#1E88E5')
style.configure('Filter.TLabelframe',background='#FFFFFF',borderwidth=1,relief='solid')
style.configure('TButton',font=('Segoe UI',11,'bold'),background='#1E88E5',foreground='white')
style.map('TButton',background=[('active','#1976D2')])
style.configure('TCombobox',font=('Segoe UI',11))

# عنوان
ttk.Label(root,text='📊 Dashboard - شكاوى الفروع',style='Header.TLabel').pack(pady=12)

# إطار الفلترة
ff = ttk.Labelframe(root,text='فلترة البيانات',style='Filter.TLabelframe',padding=12)
ff.pack(fill='x',padx=20)

# تواريخ
ttk.Label(ff,text='من:').grid(row=0,column=0,padx=5,pady=5)
from_entry=DateEntry(ff,date_pattern='yyyy-MM-dd',width=12)
from_entry.grid(row=0,column=1,padx=5)

ttk.Label(ff,text='إلى:').grid(row=0,column=2,padx=5)
to_entry=DateEntry(ff,date_pattern='yyyy-MM-dd',width=12)
to_entry.grid(row=0,column=3,padx=5)

# فرع
ttk.Label(ff,text='الفرع:').grid(row=1,column=0,sticky='e',padx=5,pady=5)
branch_var=tk.StringVar(); bl=['كل الفروع']+fetch_branches()
br_combo=ttk.Combobox(ff,textvariable=branch_var,values=bl,state='readonly',width=30)
br_combo.grid(row=1,column=1,columnspan=3,padx=5,pady=5,sticky='w'); br_combo.current(0)

# حالة
ttk.Label(ff,text='الحالة:').grid(row=2,column=0,sticky='e',padx=5,pady=5)
status_var=tk.StringVar(); sl=['كل الحالات']+fetch_statuses()
st_combo=ttk.Combobox(ff,textvariable=status_var,values=sl,state='readonly',width=30)
st_combo.grid(row=2,column=1,columnspan=3,padx=5,pady=5,sticky='w'); st_combo.current(0)

# أزرار
bf=ttk.Frame(root); bf.pack(pady=20)
ttk.Button(bf,text='عرض Dashboard',command=draw_dashboard).grid(row=0,column=0,padx=10)
ttk.Button(bf,text='❌ خروج',command=root.destroy).grid(row=0,column=1,padx=10)

root.mainloop()