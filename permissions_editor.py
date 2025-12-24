import tkinter as tk
from tkinter import ttk, messagebox
import pyodbc

# الاتصال بقاعدة البيانات
def get_connection():
    return pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=LAPREFaat;'
        'DATABASE=DrAhmedCRM;'
        'Trusted_Connection=yes;'
    )

def load_users_permissions(tree):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT A.ID, A.Username, 
               ISNULL(P.CanViewReports, 0),
               ISNULL(P.CanEditFunctions, 0),
               ISNULL(P.CanManageUsers, 0),
               ISNULL(P.CanExportExcel, 0)
        FROM AdminUsers A
        LEFT JOIN UserPermissions P ON A.ID = P.UserID
        GROUP BY A.ID, A.Username, P.CanViewReports, P.CanEditFunctions, P.CanManageUsers, P.CanExportExcel
    """
    cursor.execute(query)
    rows = cursor.fetchall()

    tree.delete(*tree.get_children())
    for row in rows:
        uid = int(row[0])
        uname = row[1]
        values = [uid, uname]
        for perm in row[2:]:
            values.append("✅" if perm else "❌")
        tree.insert("", "end", values=values)

def update_permissions(tree):
    conn = get_connection()
    cursor = conn.cursor()

    for item in tree.get_children():
        values = tree.item(item)["values"]
        user_id = int(values[0])
        perms = [1 if val == "✅" else 0 for val in values[2:]]

        cursor.execute("SELECT COUNT(*) FROM UserPermissions WHERE UserID = ?", user_id)
        exists = cursor.fetchone()[0]

        if exists:
            cursor.execute("""
                UPDATE UserPermissions 
                SET CanViewReports = ?, CanEditFunctions = ?, 
                    CanManageUsers = ?, CanExportExcel = ?
                WHERE UserID = ?
            """, *perms, user_id)
        else:
            cursor.execute("""
                INSERT INTO UserPermissions (UserID, CanViewReports, CanEditFunctions, CanManageUsers, CanExportExcel)
                VALUES (?, ?, ?, ?, ?)
            """, user_id, *perms)

    conn.commit()
    messagebox.showinfo("✅", "تم تحديث الصلاحيات بنجاح ✅")

def toggle_checkbox(event, tree):
    region = tree.identify("region", event.x, event.y)
    if region == "cell":
        col = tree.identify_column(event.x)
        row_id = tree.identify_row(event.y)
        if col in ("#3", "#4", "#5", "#6"):
            col_index = int(col[1:]) - 1
            values = list(tree.item(row_id)["values"])
            values[col_index] = "❌" if values[col_index] == "✅" else "✅"
            tree.item(row_id, values=values)

def launch_permissions_editor():
    root = tk.Tk()
    root.title("🛡 إدارة صلاحيات المستخدمين")
    root.geometry("950x550")
    root.configure(bg="#e8f5e9")

    style = ttk.Style()
    style.configure("Treeview", font=("Tahoma", 12), rowheight=32)
    style.configure("Treeview.Heading", font=("Tahoma", 13, "bold"))

    tk.Label(root, text="🛡 صلاحيات المستخدمين", font=("Tahoma", 16, "bold"), bg="#e8f5e9", fg="#2e7d32").pack(pady=10)

    columns = ("ID", "اسم المستخدم", "عرض تقارير", "زرائر", "مستخدمين", "Excel")

    tree = ttk.Treeview(root, columns=columns, show="headings")
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, anchor="center", width=140)
    tree.pack(fill="both", expand=True, padx=10, pady=10)

    tree.bind("<Button-1>", lambda e: toggle_checkbox(e, tree))

    tk.Button(root, text="💾 حفظ التعديلات", font=("Tahoma", 12), bg="#43a047", fg="white",
              command=lambda: update_permissions(tree)).pack(pady=10)

    load_users_permissions(tree)
    root.mainloop()

if __name__ == "__main__":
    launch_permissions_editor()
