import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from decimal import Decimal
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
    root.title("🧾 إنشاء أوردر")
    root.configure(bg="#e0f7fa")
    root.attributes("-fullscreen", True)

    customer_id_var = tk.StringVar()
    product_var = tk.StringVar()
    total_var = tk.DoubleVar(value=0.0)
    rows = []
    def calculate_total():
        total = sum(r["total_var"].get() for r in rows)
        total_var.set(round(total, 2))
        total_label.config(text=f"{total:.2f} ج.م")

    # دالة السعر بالتعديل
    def fetch_price(name, unit):
        cursor.execute("SELECT Price, SmallUnit FROM ProductUnits WHERE ItemName = ? AND AllUnit = ?", name, unit)
        row = cursor.fetchone()
        if row:
            return Decimal(row[0]), 1
        return Decimal(0), 1    
            
                
     

     
    tk.Label(root, text="🧾 إنشاء أوردر", font=("Tahoma", 26, "bold"), fg="#00695c", bg="#e0f7fa").pack(pady=20)

    top = tk.Frame(root, bg="#e0f7fa")
    top.pack()
    tk.Label(top, text="رقم العميل:", font=("Tahoma", 14), bg="#e0f7fa").grid(row=0, column=0, padx=5)
    tk.Entry(top, textvariable=customer_id_var, font=("Tahoma", 14), width=20).grid(row=0, column=1, padx=5)

    customer_label = tk.Label(root, text="", font=("Tahoma", 12), fg="blue", bg="#e0f7fa")
    customer_label.pack()

    def fetch_customer():
        phone = customer_id_var.get().strip()
        cursor.execute("SELECT FirstName, LastName, City, Region, CustomerID FROM Customers WHERE PhoneNumber = ?", phone)
        row = cursor.fetchone()
        if row:
            customer_label.config(text=f"{row.FirstName} {row.LastName} - {row.Region}, {row.City}")
            show_previous_orders(row.CustomerID)
        else:
            customer_label.config(text="❌ لم يتم العثور على عميل")

    tk.Button(top, text="🔍 بحث", font=("Tahoma", 14), command=fetch_customer).grid(row=0, column=2, padx=5)
    add_frame = tk.Frame(root, bg="#e0f7fa")
    add_frame.pack(pady=10)



    product_entry = tk.Entry(add_frame, textvariable=product_var, font=("Tahoma", 14), width=40)
    product_entry.pack(side="left", padx=10)

    suggestion_box = tk.Listbox(root, font=("Tahoma", 12), height=5, width=50, bg="white")
    suggestion_box.place_forget()

    def show_suggestions(event):
        text = product_var.get().strip()
        suggestion_box.delete(0, tk.END)
        if not text:
            suggestion_box.place_forget()
            return
        cursor.execute("SELECT DISTINCT ItemName FROM ProductUnits WHERE ItemName LIKE ?", f"%{text}%")
        results = [row[0] for row in cursor.fetchall()]
        if results:
            for r in results:
                suggestion_box.insert(tk.END, r)
            x = product_entry.winfo_rootx() - root.winfo_rootx()
            y = product_entry.winfo_rooty() - root.winfo_rooty() + product_entry.winfo_height()
            suggestion_box.place(x=x, y=y)
            suggestion_box.lift()
        else:
            suggestion_box.place_forget()

    def select_suggestion(event):
        if suggestion_box.curselection():
            selected = suggestion_box.get(suggestion_box.curselection())
            product_var.set(selected)
            suggestion_box.place_forget()
            product_entry.icursor(tk.END)

    product_entry.bind("<KeyRelease>", show_suggestions)
    product_entry.bind("<Down>", lambda e: suggestion_box.focus_set())
    suggestion_box.bind("<Return>", select_suggestion)
    suggestion_box.bind("<Double-Button-1>", select_suggestion)
    products_frame = tk.Frame(root, bg="#e0f7fa")
    products_frame.pack(pady=10)

    headers = ["المنتج", "الوحدة", "الكمية", "سعر الوحدة", "الإجمالي", "حذف"]
    for i, h in enumerate(headers):
        tk.Label(products_frame, text=h, font=("Tahoma", 12, "bold"), bg="#b2ebf2", width=15).grid(row=0, column=i)
    def fetch_units(name):
        cursor.execute("SELECT DISTINCT AllUnit FROM ProductUnits WHERE ItemName = ?", name)
        return [row[0] for row in cursor.fetchall()]

    def add_row():
        name = product_var.get().strip()
        if not name:
            return
        index = len(rows) + 1
        unit_var = tk.StringVar()
        qty_var = tk.StringVar(value="1")
        price_var = tk.StringVar(value="0.00")
        total_row_var = tk.DoubleVar(value=0.0)

        row_widgets = {}
        row_widgets["name"] = tk.Label(products_frame, text=name, font=("Tahoma", 12), anchor="w", bg="#e0f7fa")
        row_widgets["name"].grid(row=index, column=0, padx=5, sticky="w")

        row_widgets["unit"] = ttk.Combobox(products_frame, textvariable=unit_var, width=10)
        row_widgets["unit"]["values"] = fetch_units(name)
        if row_widgets["unit"]["values"]:
            unit_var.set(row_widgets["unit"]["values"][0])
        row_widgets["unit"].grid(row=index, column=1)

        row_widgets["qty"] = tk.Entry(products_frame, textvariable=qty_var, width=5)
        row_widgets["qty"].grid(row=index, column=2)

        row_widgets["price"] = tk.Label(products_frame, textvariable=price_var, width=10, bg="#e0f7fa")
        row_widgets["price"].grid(row=index, column=3)

        row_widgets["total"] = tk.Label(products_frame, textvariable=total_row_var, width=10, bg="#e0f7fa")
        row_widgets["total"].grid(row=index, column=4)

        def update_price(event=None):
            unit = unit_var.get()
            qty = qty_var.get()
            if unit and qty.isdigit():
                price, small = fetch_price(name, unit)
                price_var.set(f"{price:.2f}")
                total = price * Decimal(qty)
                total_row_var.set(round(total, 2))
                calculate_total()

        row_widgets["unit"].bind("<<ComboboxSelected>>", update_price)
        row_widgets["qty"].bind("<KeyRelease>", update_price)
        update_price()

        def delete_row():
            for widget in row_widgets.values():
                widget.grid_forget()
            rows.remove(row)
            calculate_total()

        row_widgets["delete"] = tk.Button(products_frame, text="🗑", font=("Tahoma", 10), command=delete_row)
        row_widgets["delete"].grid(row=index, column=5)

        row = {
            "product_name": name,
            "unit_var": unit_var,
            "qty_var": qty_var,
            "price_var": price_var,
            "total_var": total_row_var,
            "widgets": row_widgets
        }
        rows.append(row)
        product_var.set("")
    bottom = tk.Frame(root, bg="#e0f7fa")
    bottom.pack(pady=20)

    tk.Label(bottom, text="الإجمالي:", font=("Tahoma", 14), bg="#e0f7fa").pack(side="left")
    total_label = tk.Label(bottom, text="0.00 ج.م", font=("Tahoma", 16, "bold"), fg="green", bg="#e0f7fa")
    total_label.pack(side="left", padx=10)

    tk.Button(bottom, text="✅ حفظ الأوردر", font=("Tahoma", 14),
              bg="#388e3c", fg="white", command=lambda: save_order()).pack(side="left", padx=20)
    tk.Button(add_frame, text="➕ أضف المنتج", font=("Tahoma", 16, "bold"), bg="#00796b", fg="white", command=add_row).pack(side="left", padx=10)

    def save_order():
        phone = customer_id_var.get().strip()
        cursor.execute("SELECT CustomerID FROM Customers WHERE PhoneNumber = ?", phone)
        row = cursor.fetchone()
        if not row:
            messagebox.showerror("❌", "العميل غير موجود")
            return
        customer_id = row[0]
        now = datetime.now()

        cursor.execute("INSERT INTO Orders (CustomerID, OrderDate, Notes) VALUES (?, ?, '')", customer_id, now)
        conn.commit()
        cursor.execute("SELECT @@IDENTITY")
        order_id = int(cursor.fetchone()[0])

        for r in rows:
            cursor.execute("""
                INSERT INTO OrderItems (OrderID, ProductName, Quantity, Unit, UnitPrice, Total)
                VALUES (?, ?, ?, ?, ?, ?)
            """, order_id, r["product_name"],
                 float(r["qty_var"].get()), r["unit_var"].get(),
                 float(r["price_var"].get()), float(r["total_var"].get()))
        conn.commit()
        messagebox.showinfo("✅", "تم حفظ الأوردر بنجاح.")
        reset_all()
    def reset_all():
        customer_id_var.set("")
        product_var.set("")
        for r in rows:
            for w in r["widgets"].values():
                w.grid_forget()
        rows.clear()
        total_var.set(0.0)
        customer_label.config(text="")
        for widget in orders_frame.winfo_children():
            widget.destroy()
    orders_frame = tk.Frame(root, bg="#e0f7fa")
    orders_frame.pack(fill="both", expand=True, padx=20, pady=20)

    def show_previous_orders(customer_id):
        for widget in orders_frame.winfo_children():
            widget.destroy()
        cursor.execute("SELECT OrderID, OrderDate FROM Orders WHERE CustomerID = ? ORDER BY OrderDate DESC", customer_id)
        orders = cursor.fetchall()
        for order in orders:
            lf = tk.LabelFrame(orders_frame, text=f"أوردر رقم: {order.OrderID} | تاريخ: {order.OrderDate.date()}",
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
    def close_fullscreen(event):
        root.attributes("-fullscreen", False)

    root.bind("<Escape>", close_fullscreen)
    root.mainloop()

if __name__ == "__main__":
    launch()
