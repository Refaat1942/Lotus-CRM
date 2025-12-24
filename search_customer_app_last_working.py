import tkinter as tk
from tkinter import ttk
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
    root.title("🔍 البحث عن عميل وأوردراته")
    root.configure(bg="#e0f7fa")
    root.attributes("-fullscreen", True)

    phone_var = tk.StringVar()

    # ========= Header =========
    tk.Label(root, text="🔍 البحث عن عميل وأوردراته", font=("Tahoma", 24, "bold"),
             fg="#004d40", bg="#e0f7fa").pack(pady=20)

    search_frame = tk.Frame(root, bg="#e0f7fa")
    search_frame.pack()

    tk.Label(search_frame, text="رقم العميل:", font=("Tahoma", 14), bg="#e0f7fa").grid(row=0, column=0, padx=5)
    phone_entry = tk.Entry(search_frame, textvariable=phone_var, font=("Tahoma", 14), width=25)
    phone_entry.grid(row=0, column=1, padx=5)
    phone_entry.bind("<Return>", lambda event: search())  # ← ده بيربط زر Enter بدالة البحث

    


    customer_info_label = tk.Label(root, text="", font=("Tahoma", 14), fg="blue", bg="#e0f7fa")
    customer_info_label.pack(pady=10)

    # Scrollable Frame for Orders
    container = tk.Frame(root, bg="#e0f7fa")
    container.pack(fill="both", expand=True, padx=20, pady=20)

    canvas = tk.Canvas(container, bg="#e0f7fa", highlightthickness=0)
    scrollbar = tk.Scrollbar(container, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas, bg="#e0f7fa")

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")


    def search():
        for widget in scrollable_frame.winfo_children():
            widget.destroy()

        phone = phone_var.get().strip()
        cursor.execute("SELECT CustomerID, FirstName, LastName, Region, City FROM Customers WHERE PhoneNumber = ?", phone)
        row = cursor.fetchone()
        if not row:
            customer_info_label.config(text="❌ لم يتم العثور على عميل")
            return

        customer_id = row.CustomerID
        customer_info_label.config(
            text=f"{row.FirstName} {row.LastName} - {row.Region}, {row.City}"
        )

        cursor.execute("SELECT OrderID, OrderDate FROM Orders WHERE CustomerID = ? ORDER BY OrderDate DESC", customer_id)
        orders = cursor.fetchall()

        for order in orders:
            lf = tk.LabelFrame(scrollable_frame, text=f"أوردر رقم: {order.OrderID} | التاريخ: {order.OrderDate.date()}",
                               padx=5, pady=5, font=("Tahoma", 12))
            lf.pack(fill="x", padx=5, pady=5)

            tree = ttk.Treeview(lf, columns=("Product", "Qty", "Unit", "Price", "Total"),
                                show="headings", height=4)
            tree.pack(fill="x")
            for col, name in zip(tree["columns"], ["المنتج", "الكمية", "الوحدة", "سعر الوحدة", "الإجمالي"]):
                tree.heading(col, text=name)
                tree.column(col, anchor="center")

            cursor.execute("SELECT ProductName, Quantity, Unit, UnitPrice, Total FROM OrderItems WHERE OrderID = ?", order.OrderID)
            for item in cursor.fetchall():
                tree.insert("", "end", values=(
                    item.ProductName, item.Quantity, item.Unit, f"{item.UnitPrice:.2f}", f"{item.Total:.2f}"
                ))

    tk.Button(search_frame, text="🔍 بحث", font=("Tahoma", 14), command=search).grid(row=0, column=2, padx=5)

    def close_fullscreen(event):
        root.attributes("-fullscreen", False)
    root.bind("<Escape>", close_fullscreen)

    root.mainloop()

if __name__ == "__main__":
    launch()