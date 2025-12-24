import tkinter as tk
from tkinter import messagebox
import pyodbc
import matplotlib.pyplot as plt

# الاتصال بقاعدة البيانات
try:
    conn = pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=LAPREFaat;'
        'DATABASE=DrAhmedCRM;'
        'Trusted_Connection=yes;'
    )
    cursor = conn.cursor()
except Exception as e:
    messagebox.showerror("❌ خطأ الاتصال", f"فشل الاتصال بقاعدة البيانات:\n{e}")
    exit()

# جلب بيانات الشكاوى
def fetch_dashboard_data():
    try:
        cursor.execute("""
            SELECT ComplaintStatus, COUNT(*) as Count
            FROM Complaints
            GROUP BY ComplaintStatus
        """)
        data = cursor.fetchall()
        return data
    except Exception as e:
        messagebox.showerror("❌ خطأ", f"فشل في جلب بيانات الشكاوى:\n{e}")
        return []

# رسم الـ Dashboard
def draw_dashboard():
    data = fetch_dashboard_data()
    if not data:
        return

    statuses = []
    counts = []

    for row in data:
        statuses.append(row.ComplaintStatus)
        counts.append(row.Count)

    plt.figure(figsize=(7, 7))
    plt.pie(counts, labels=statuses, autopct='%1.1f%%', startangle=140, wedgeprops={'edgecolor': 'black'})
    plt.title('توزيع حالات الشكاوى', fontdict={'fontsize': 20})
    plt.axis('equal')  # يخلي الرسمه مدورة مضبوط
    plt.show()

# نافذة رئيسية صغيرة للـ Dashboard
root = tk.Tk()
root.title("📊 Dashboard - حالات الشكاوى")
root.geometry("300x200")
root.configure(bg="#EDE7F6")

tk.Label(root, text="📊 عرض Dashboard لحالات الشكاوى", font=("Arial", 16, "bold"), fg="#4A148C", bg="#EDE7F6").pack(pady=30)

show_btn = tk.Button(root, text="📈 عرض Dashboard", font=("Arial", 14), bg="#4CAF50", fg="white", command=draw_dashboard)
show_btn.pack(pady=20)

def close_app(event=None):
    root.destroy()

root.bind("<Escape>", close_app)

exit_btn = tk.Button(root, text="❌ خروج", font=("Arial", 12), bg="#f44336", fg="white", command=close_app)
exit_btn.pack(pady=10)

root.mainloop()
