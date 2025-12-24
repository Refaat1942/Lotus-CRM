# Admin Panel - نسخة المالك
# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pyodbc
import hashlib
import pandas as pd
import subprocess 

# ✅ صلاحيات المستخدم الحالي
current_permissions = {}

# الاتصال بقاعدة البيانات
def get_connection():
    return pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=LAPREFaat;'
        'DATABASE=DrAhmedCRM;'
        'Trusted_Connection=yes;'
    )

# تشفير الباسورد
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# تسجيل الدخول
def show_login():
    login = tk.Tk()
    login.title("لوحة دخول المشرف")
    login.geometry("600x400")
    login.configure(bg="#00796b")

    tk.Label(login, text="🔐 تسجيل دخول المشرفين", font=("Tahoma", 24, "bold"), bg="#00796b", fg="white").pack(pady=30)

    frame = tk.Frame(login, bg="#004d40")
    frame.pack(pady=20)

    tk.Label(frame, text="👤 اسم المستخدم:", font=("Tahoma", 16), bg="#004d40", fg="white").grid(row=0, column=0, pady=10, padx=10, sticky="e")
    username_entry = tk.Entry(frame, font=("Tahoma", 16))
    username_entry.grid(row=0, column=1, pady=10, padx=10)

    tk.Label(frame, text="🔒 كلمة المرور:", font=("Tahoma", 16), bg="#004d40", fg="white").grid(row=1, column=0, pady=10, padx=10, sticky="e")
    password_entry = tk.Entry(frame, font=("Tahoma", 16), show="*")
    password_entry.grid(row=1, column=1, pady=10, padx=10)

    def attempt_login():
        username = username_entry.get().strip()
        password = password_entry.get().strip()

        if not username or not password:
            messagebox.showwarning("⚠️", "يرجى إدخال اسم المستخدم وكلمة المرور")
            return

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT PasswordHash FROM AdminUsers WHERE Username = ?", username)
            row = cursor.fetchone()

            if row and hash_password(password) == row.PasswordHash:
                cursor.execute("SELECT ID FROM AdminUsers WHERE Username = ?", username)
                user_id = cursor.fetchone()[0]

                cursor.execute("SELECT * FROM UserPermissions WHERE UserID = ?", user_id)
                permissions = cursor.fetchone()

                if not permissions:
                    messagebox.showerror("🚫", "لا توجد صلاحيات معرفة لهذا المستخدم.")
                    return

                global current_permissions
                current_permissions = {
                    "CanViewReports": permissions[1],
                    "CanEditFunctions": permissions[2],
                    "CanManageUsers": permissions[3],
                    "CanExportExcel": permissions[4],
                }

                login.destroy()
                show_dashboard()
            else:
                messagebox.showerror("❌", "اسم المستخدم أو كلمة المرور غير صحيحة")

        except Exception as e:
            messagebox.showerror("❌ خطأ", str(e))

    tk.Button(login, text="➡️ دخول", font=("Tahoma", 16), bg="#004d40", fg="white", width=20, command=attempt_login).pack(pady=20)

    login.mainloop()
# ===== لوحة التحكم =====
def show_dashboard():
    root = tk.Tk()
    root.title("لوحة التحكم الإدارية")
    root.attributes('-fullscreen', True)
    root.configure(bg="#e0f7fa")

    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True)

    # ========== إدارة الوظائف ==========
    frame_functions = tk.Frame(notebook, bg="#e0f7fa")

    func_tree = ttk.Treeview(frame_functions, columns=("ID", "الوظيفة", "المسار", "مفعل", "لون"), show="headings")
    func_tree.pack(fill="both", expand=True, padx=10, pady=10)

    for col in ("ID", "الوظيفة", "المسار", "مفعل", "لون"):
        func_tree.heading(col, text=col)
        func_tree.column(col, anchor="center")

    def load_functions():
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT ID, FunctionName, ScriptPath, IsEnabled, ColorHex FROM SystemFunctions")
        rows = cursor.fetchall()
        func_tree.delete(*func_tree.get_children())
        for row in rows:
            func_tree.insert("", "end", values=(
                row.ID, row.FunctionName, row.ScriptPath,
                "✅" if row.IsEnabled else "❌", row.ColorHex
            ))

    def toggle_function():
        selected = func_tree.selection()
        if not selected:
            messagebox.showwarning("⚠️", "اختر وظيفة أولاً")
            return
        item = func_tree.item(selected[0])
        function_id = item['values'][0]
        current_status = item['values'][3] == "✅"
        new_status = 0 if current_status else 1
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE SystemFunctions SET IsEnabled = ? WHERE ID = ?", new_status, function_id)
        conn.commit()
        load_functions()

    tk.Button(frame_functions, text="🔁 تفعيل / تعطيل", font=("Tahoma", 12), bg="#2196F3", fg="white", command=toggle_function).pack(pady=10)

    if current_permissions.get("CanEditFunctions"):
        notebook.add(frame_functions, text="🧩 إدارة الزرائر")
    # ========== إدارة المستخدمين ==========
    frame_users = tk.Frame(notebook, bg="#f1f8e9")

    tk.Label(frame_users, text="👤 اسم المستخدم", bg="#f1f8e9", font=("Tahoma", 12)).pack(pady=5)
    username_entry = tk.Entry(frame_users, font=("Tahoma", 12))
    username_entry.pack(pady=5)

    tk.Label(frame_users, text="🔒 كلمة المرور", bg="#f1f8e9", font=("Tahoma", 12)).pack(pady=5)
    password_entry = tk.Entry(frame_users, font=("Tahoma", 12), show="*")
    password_entry.pack(pady=5)

    def add_user():
        username = username_entry.get().strip()
        password = password_entry.get().strip()
        if not username or not password:
            messagebox.showwarning("⚠️", "يرجى إدخال اسم المستخدم وكلمة المرور")
            return

        hashed = hash_password(password)
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO AdminUsers (Username, PasswordHash) OUTPUT INSERTED.ID VALUES (?, ?)", username, hashed)
        new_user_id = cursor.fetchone()[0]
        cursor.execute("INSERT INTO UserPermissions (UserID, CanViewReports, CanEditFunctions, CanManageUsers, CanExportExcel) VALUES (?, 1, 0, 0, 1)", new_user_id)
        conn.commit()
        username_entry.delete(0, tk.END)
        password_entry.delete(0, tk.END)
        load_users()

    tk.Button(frame_users, text="➕ إضافة مستخدم", font=("Tahoma", 12), bg="#4CAF50", fg="white", command=add_user).pack(pady=10)

    users_tree = ttk.Treeview(frame_users, columns=("ID", "Username"), show="headings")
    users_tree.pack(fill="both", expand=True, padx=10, pady=10)
    users_tree.heading("ID", text="ID")
    users_tree.heading("Username", text="اسم المستخدم")

    def load_users():
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT ID, Username FROM AdminUsers")
        users_tree.delete(*users_tree.get_children())
        for row in cursor.fetchall():
            users_tree.insert("", "end", values=(row.ID, row.Username))

    def delete_user():
        selected = users_tree.selection()
        if not selected:
            messagebox.showwarning("⚠️", "اختر مستخدمًا أولاً")
            return
        item = users_tree.item(selected[0])
        user_id = item['values'][0]
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM AdminUsers WHERE ID = ?", user_id)
        cursor.execute("DELETE FROM UserPermissions WHERE UserID = ?", user_id)
        conn.commit()
        load_users()

    tk.Button(frame_users, text="🗑 حذف مستخدم", font=("Tahoma", 12), bg="#f44336", fg="white", command=delete_user).pack(pady=10)
    tk.Button(frame_users, text="🛡 تعديل صلاحيات المستخدمين", font=("Tahoma", 12), bg="#6a1b9a", fg="white",
              command=lambda: subprocess.Popen(["python", "permissions_editor.py"])).pack(pady=10)

    if current_permissions.get("CanManageUsers"):
        notebook.add(frame_users, text="👥 إدارة المستخدمين")

    # ========== التقارير ==========
    frame_reports = tk.Frame(notebook, bg="#e1f5fe")

    report_options = ["تقرير العملاء", "تقرير الشكاوى", "تقرير الأوردرات"]
    selected_report = tk.StringVar()
    selected_report.set(report_options[0])

    tk.Label(frame_reports, text="اختر التقرير:", bg="#e1f5fe", font=("Tahoma", 13, "bold")).pack(pady=10)
    report_menu = ttk.Combobox(frame_reports, values=report_options, textvariable=selected_report, font=("Tahoma", 12), width=30)
    report_menu.pack(pady=5)

    report_frame = tk.Frame(frame_reports)
    report_frame.pack(fill="both", expand=True, padx=10, pady=10)

    report_tree = ttk.Treeview(report_frame)
    report_tree.pack(side="left", fill="both", expand=True)

    scrollbar = ttk.Scrollbar(report_frame, orient="vertical", command=report_tree.yview)
    scrollbar.pack(side="right", fill="y")
    report_tree.configure(yscrollcommand=scrollbar.set)

    def load_report():
        report_tree.delete(*report_tree.get_children())
        conn = get_connection()
        cursor = conn.cursor()
        if selected_report.get() == "تقرير العملاء":
            cursor.execute("SELECT FirstName, LastName, PhoneNumber, City, Region FROM Customers")
            columns = ["الاسم الأول", "الاسم الأخير", "رقم الهاتف", "المدينة", "المنطقة"]
            rows = cursor.fetchall()
        elif selected_report.get() == "تقرير الشكاوى":
            cursor.execute("SELECT ComplaintID, PhoneNumber, ComplaintText, ComplaintStatus, ComplaintDate FROM Complaints")
            columns = ["رقم الشكوى", "هاتف العميل", "محتوى الشكوى", "حالة الشكوى", "تاريخ الشكوى"]
            rows = [(r[0], r[1], r[2], r[3], str(r[4].date()) if r[4] else "") for r in cursor.fetchall()]
        elif selected_report.get() == "تقرير الأوردرات":
            cursor.execute("""SELECT o.OrderID, o.CustomerID, o.OrderDate, i.ProductName, i.Quantity, i.UnitPrice
                              FROM Orders o JOIN OrderItems i ON o.OrderID = i.OrderID""")
            columns = ["رقم الأوردر", "رقم العميل", "تاريخ الأوردر", "المنتج", "الكمية", "السعر"]
            rows = [(r[0], r[1], str(r[2].date()), r[3], r[4], r[5]) for r in cursor.fetchall()]
        else:
            return

        report_tree["columns"] = columns
        report_tree["show"] = "headings"

        for col in columns:
            report_tree.heading(col, text=col)
            report_tree.column(col, anchor="center", width=150)

        for row in rows:
            clean = [str(cell).strip("(),'") for cell in row]
            report_tree.insert("", "end", values=clean)

    def export_to_excel():
        if not report_tree.get_children():
            messagebox.showwarning("⚠️", "لا توجد بيانات للتصدير")
            return
        data = [report_tree.item(item)["values"] for item in report_tree.get_children()]
        df = pd.DataFrame(data, columns=report_tree["columns"])
        file_path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx")])
        if file_path:
            df.to_excel(file_path, index=False)
            messagebox.showinfo("✅", "تم حفظ التقرير بنجاح")

    tk.Button(frame_reports, text="📋 عرض التقرير", font=("Tahoma", 12), bg="#0288d1", fg="white", command=load_report).pack(pady=5)

    if current_permissions.get("CanExportExcel"):
        tk.Button(frame_reports, text="📥 تصدير إلى Excel", font=("Tahoma", 12), bg="#43a047", fg="white", command=export_to_excel).pack(pady=5)

    if current_permissions.get("CanViewReports"):
        notebook.add(frame_reports, text="📊 التقارير")

    load_functions()
    load_users()

    root.bind("<Escape>", lambda e: root.attributes("-fullscreen", False))
    
    # (تم حذف تبويب صلاحيات الوظائف بناءً على طلب المستخدم)

    
    # ========== صلاحيات الزرائر للمستخدمين مع فلترة بالفروع ========== #
    frame_button_permissions = tk.Frame(notebook, bg="#fffde7")

    branch_label = tk.Label(frame_button_permissions, text="اختر الفرع:", font=("Tahoma", 12), bg="#fffde7")
    branch_label.pack(pady=(10, 2))

    branch_var = tk.StringVar()
    branch_combo = ttk.Combobox(frame_button_permissions, textvariable=branch_var, font=("Tahoma", 12), state="readonly")
    branch_combo.pack(pady=5)

    btn_perm_tree = ttk.Treeview(frame_button_permissions, columns=("UserID", "Username", "FunctionID", "FunctionName", "مسموح"), show="headings")
    btn_perm_tree.pack(fill="both", expand=True, padx=10, pady=10)

    for col in btn_perm_tree["columns"]:
        btn_perm_tree.heading(col, text=col)
        btn_perm_tree.column(col, anchor="center", width=120)

    def load_branches():
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT BranchCode FROM Branches")
        branches = ["الكل"] + [row[0] for row in cursor.fetchall()]
        branch_combo["values"] = branches
        branch_combo.set("الكل")

    def load_button_permissions():
        conn = get_connection()
        cursor = conn.cursor()

        selected_branch = branch_var.get()
        if selected_branch and selected_branch != "الكل":
            cursor.execute("""
                SELECT u.ID, u.Username, f.ID, f.FunctionName,
                       ISNULL(a.IsVisible, 0)
                FROM AdminUsers u
                JOIN Branches b ON u.Username = b.BranchCode
                CROSS JOIN SystemFunctions f
                LEFT JOIN UserFunctionAccess a ON a.UserID = u.ID AND a.FunctionID = f.ID
                WHERE f.IsEnabled = 1 AND b.BranchCode = ?
            """, selected_branch)
        else:
            cursor.execute("""
                SELECT u.ID, u.Username, f.ID, f.FunctionName,
                       ISNULL(a.IsVisible, 0)
                FROM AdminUsers u
                CROSS JOIN SystemFunctions f
                LEFT JOIN UserFunctionAccess a ON a.UserID = u.ID AND a.FunctionID = f.ID
                WHERE f.IsEnabled = 1
            """)

        btn_perm_tree.delete(*btn_perm_tree.get_children())
        for row in cursor.fetchall():
            btn_perm_tree.insert("", "end", values=(
                row[0], row[1], row[2], row[3], "✅" if row[4] else "❌"
            ))

    def toggle_button_permission():
        selected = btn_perm_tree.selection()
        if not selected:
            messagebox.showwarning("⚠️", "اختر صلاحية أولاً")
            return
        item = btn_perm_tree.item(selected[0])
        user_id = item['values'][0]
        function_id = item['values'][2]
        current_val = item['values'][4]
        new_val = 0 if current_val == "✅" else 1

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM UserFunctionAccess WHERE UserID = ? AND FunctionID = ?", user_id, function_id)
        exists = cursor.fetchone()[0]
        if exists:
            cursor.execute("UPDATE UserFunctionAccess SET IsVisible = ? WHERE UserID = ? AND FunctionID = ?", new_val, user_id, function_id)
        else:
            cursor.execute("INSERT INTO UserFunctionAccess (UserID, FunctionID, IsVisible) VALUES (?, ?, ?)", user_id, function_id, new_val)
        conn.commit()
        load_button_permissions()

    branch_combo.bind("<<ComboboxSelected>>", lambda e: load_button_permissions())

    tk.Button(frame_button_permissions, text="🔁 تبديل السماح/الإخفاء", font=("Tahoma", 12), bg="#ff9800", fg="white", command=toggle_button_permission).pack(pady=10)
    notebook.add(frame_button_permissions, text="🛠 صلاحيات الزرائر")
    load_branches()
    load_button_permissions()

    root.mainloop()
if __name__ == "__main__":
    show_login()
