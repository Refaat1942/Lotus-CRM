import tkinter as tk
from tkinter import messagebox
import pyodbc

def launch():
    conn = pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=LAPREFaat;'
        'DATABASE=DrAhmedCRM;'
        'Trusted_Connection=yes;'
    )
    cursor = conn.cursor()

    root = tk.Tk()
    root.title("➕ إضافة عميل")
    root.configure(bg="#e0f7fa")  # لون خلفية أفتح
    root.attributes("-fullscreen", True)

    tk.Label(root, text="➕ إضافة عميل جديد", font=("Tahoma", 26, "bold"),
             fg="#006064", bg="#e0f7fa").pack(pady=30)

    form = tk.Frame(root, bg="#e0f7fa")
    form.pack()

    fields = [
        "First Name", "Last Name", "Phone Number", "Region", "City", "District",
        "Area", "Street Name", "Building", "Floor", "Flat Number", "Landmark"
    ]
    entries = {}

    for i, field in enumerate(fields):
        row = i % 6
        col = i // 6
        tk.Label(form, text=field, font=("Tahoma", 14), bg="#e0f7fa", anchor="w").grid(row=row, column=col * 2, sticky="e", padx=(10, 2), pady=8)
        entry = tk.Entry(form, font=("Tahoma", 14), width=25)
        entry.grid(row=row, column=(col * 2) + 1, padx=(2, 20), pady=8)
        entries[field] = entry

    def save_customer():
        try:
            cursor.execute("""
                INSERT INTO Customers (
                    FirstName, LastName, PhoneNumber, Region, City, District,
                    Area, StreetName, Building, Floor, FlatNumber, Landmark
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, *[entries[f].get() for f in fields])
            conn.commit()
            messagebox.showinfo("✅ تم", "تم حفظ بيانات العميل بنجاح")
            for e in entries.values():
                e.delete(0, tk.END)
        except Exception as e:
            messagebox.showerror("❌ خطأ", f"حدث خطأ أثناء الحفظ:\n{e}")

    btn_frame = tk.Frame(root, bg="#e0f7fa")
    btn_frame.pack(pady=30)

    tk.Button(btn_frame, text="💾 حفظ العميل", font=("Tahoma", 14, "bold"),
              bg="#00796b", fg="white", padx=30, pady=10, command=save_customer).pack(side="left", padx=30)

    tk.Button(btn_frame, text="⬅️ رجوع", font=("Tahoma", 14, "bold"),
              bg="#d84315", fg="white", padx=30, pady=10, command=root.destroy).pack(side="left", padx=30)

    def close_fullscreen(event):
        root.attributes("-fullscreen", False)
    root.bind("<Escape>", close_fullscreen)

    root.mainloop()

if __name__ == "__main__":
    launch()
