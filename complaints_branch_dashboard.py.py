import tkinter as tk
from tkinter import messagebox
import pyodbc
import matplotlib.pyplot as plt
from matplotlib import rcParams
import arabic_reshaper
from bidi.algorithm import get_display

# الاتصال بقاعدة البيانات
conn = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=LAPREFaat;'
    'DATABASE=DrAhmedCRM;'
    'Trusted_Connection=yes;'
)
cursor = conn.cursor()

# تحويل النص العربي
def reshape_ar(text):
    return get_display(arabic_reshaper.reshape(text))

# جلب بيانات الشكاوى حسب الفروع
def fetch_branch_data():
    try:
        cursor.execute("""
            SELECT b.BranchName, COUNT(*) as Count
            FROM Complaints c
            LEFT JOIN Branches b ON c.BranchCode = b.BranchCode
            GROUP BY b.BranchName
        """)
        return cursor.fetchall()
    except Exception as e:
        messagebox.showerror("❌ خطأ", f"حدث خطأ:\n{e}")
        return []

# رسم Dashboard
def draw_branch_dashboard():
    data = fetch_branch_data()
    if not data:
        messagebox.showinfo("معلومة", "لا توجد بيانات لعرضها.")
        return

    branches = []
    counts = []

    for row in data:
        name = row.BranchName if row.BranchName else "غير محدد"
        branches.append(reshape_ar(name))
        counts.append(row.Count)

    rcParams['font.family'] = 'Arial'

    plt.figure(figsize=(12, 6))
    bars = plt.bar(branches, counts, color="#4CAF50", edgecolor="black")
    plt.title(reshape_ar("عدد الشكاوى حسب الفرع"), fontsize=18)
    plt.ylabel(reshape_ar("عدد الشكاوى"))
    plt.xticks(rotation=45, ha="right")
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.show()

# نافذة رئيسية بسيطة
root = tk.Tk()
root.title("📊 Dashboard - شكاوى الفروع")
root.geometry("420x250")
root.configure(bg="#EDE7F6")

tk.Label(root, text="📊 Dashboard - شكاوى حسب الفروع", font=("Arial", 18, "bold"), fg="#4A148C", bg="#EDE7F6").pack(pady=30)

show_btn = tk.Button(root, text="📈 عرض Dashboard", font=("Arial", 16), bg="#2196F3", fg="white", command=draw_branch_dashboard)
show_btn.pack(pady=20)

exit_btn = tk.Button(root, text="❌ خروج", font=("Arial", 14), bg="#f44336", fg="white", command=root.destroy)
exit_btn.pack(pady=10)

root.mainloop()
