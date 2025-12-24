import tkinter as tk
from tkinter import ttk, messagebox
import pyodbc
import pandas as pd

def open_knowledge_window():
    win = tk.Toplevel()
    win.title("قاعدة المعرفة الدوائية")
    win.attributes('-fullscreen', True)
    win.configure(bg="#e0f7fa")
    win.bind("<Escape>", lambda e: win.attributes('-fullscreen', False))

    # تحسين التبويبات لجعلها أكثر وضوحاً
    style = ttk.Style()
    style.configure('TNotebook', background="#e0f7fa")
    style.configure('TNotebook.Tab', font=('Cairo', 12, 'bold'), padding=[20, 5])
    
    tk.Label(win, text="💊 قاعدة المعرفة الدوائية", font=("Cairo", 22, "bold"),
             bg="#e0f7fa", fg="#004d40").pack(pady=20)

    notebook = ttk.Notebook(win)
    notebook.pack(fill="both", expand=True)

    # التبويب 1: بحث عام
    frame_search = tk.Frame(notebook, bg="#e0f7fa")
    frame_alternatives = tk.Frame(notebook, bg="#e0f7fa")
    frame_buttons_by_use = tk.Frame(notebook, bg="#fff8e1")
    notebook.add(frame_search, text="🔍 بحث عام")
    notebook.add(frame_alternatives, text="💊 البدايل")
    notebook.add(frame_buttons_by_use, text="📚 حسب الاستخدام")

    # تبويب 1 - بحث عام 
    search_entry = tk.Entry(frame_search, font=("Cairo", 14), width=40)
    search_entry.pack(pady=10)

    columns = ("ItemCode", "ItemName", "ActiveIngredient", "MedicalUse")
    tree = ttk.Treeview(frame_search, columns=columns, show="headings")
    tree.pack(pady=10, padx=20, fill="both", expand=True)

    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, anchor='center', width=250)

    def get_connection():
        return pyodbc.connect(
            r'DRIVER={ODBC Driver 17 for SQL Server};'
            r'SERVER=LAPREFaat;'
            r'DATABASE=DrAhmedCRM;'
            r'Trusted_Connection=yes;'
        )

    def fetch_data(keyword, treeview):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    CAST(ItemCode AS VARCHAR(50)), 
                    LTRIM(RTRIM(ItemName)), 
                    LTRIM(RTRIM(ActiveIngredient)), 
                    LTRIM(RTRIM(MedicalUse))
                FROM ProductKnowledge
                WHERE ItemCode LIKE ? OR ItemName LIKE ?
            """, (f"%{keyword}%", f"%{keyword}%"))
            rows = cursor.fetchall()
            treeview.delete(*treeview.get_children())
            for row in rows:
                clean_row = [str(col).strip("(),'") for col in row]
                treeview.insert("", "end", values=clean_row)
            conn.close()
        except Exception as e:
            messagebox.showerror("خطأ", str(e))

    search_entry.bind("<Return>", lambda event: fetch_data(search_entry.get(), tree))
    tk.Button(frame_search, text="بحث", font=("Cairo", 12), bg="#00796b", fg="white",
              command=lambda: fetch_data(search_entry.get(), tree)).pack()

    # تبويب 2 - بدائل 
    alt_search_frame = tk.Frame(frame_alternatives, bg="#e0f7fa")
    alt_search_frame.pack(pady=10)

    alt_entry = tk.Entry(alt_search_frame, font=("Cairo", 14), width=40)
    alt_entry.pack(pady=10)

    search_mode = tk.StringVar(value="name")
    tk.Radiobutton(alt_search_frame, text="بحث بالاسم", variable=search_mode, value="name",
                   font=("Cairo", 12), bg="#e0f7fa").pack(side="left", padx=10)
    tk.Radiobutton(alt_search_frame, text="بحث بالمادة الفعالة", variable=search_mode, value="active",
                   font=("Cairo", 12), bg="#e0f7fa").pack(side="left", padx=10)

    alt_tree = ttk.Treeview(frame_alternatives, columns=columns, show="headings")
    alt_tree.pack(pady=10, padx=20, fill="both", expand=True)
    for col in columns:
        alt_tree.heading(col, text=col)
        alt_tree.column(col, anchor='center', width=250)

    def fetch_alternatives():
        try:
            conn = get_connection()
            cursor = conn.cursor()

            if search_mode.get() == "name":
                keyword = alt_entry.get()
                cursor.execute("""
                    SELECT ActiveIngredient 
                    FROM ProductKnowledge 
                    WHERE ItemName LIKE ?
                """, (f"%{keyword}%",))
                result = cursor.fetchone()
                if result:
                    active = result[0].strip()
                    cursor.execute("""
                        SELECT 
                            CAST(ItemCode AS VARCHAR(50)), 
                            LTRIM(RTRIM(ItemName)), 
                            LTRIM(RTRIM(ActiveIngredient)), 
                            LTRIM(RTRIM(MedicalUse))
                        FROM ProductKnowledge
                        WHERE ActiveIngredient = ?
                    """, (active,))
            elif search_mode.get() == "active":
                ingr = alt_entry.get()
                cursor.execute("""
                    SELECT 
                        CAST(ItemCode AS VARCHAR(50)), 
                        LTRIM(RTRIM(ItemName)), 
                        LTRIM(RTRIM(ActiveIngredient)), 
                        LTRIM(RTRIM(MedicalUse))
                    FROM ProductKnowledge
                    WHERE ActiveIngredient LIKE ?
                """, (f"%{ingr}%",))

            rows = cursor.fetchall()
            alt_tree.delete(*alt_tree.get_children())
            for row in rows:
                clean_row = [str(col).strip("(),'") for col in row]
                alt_tree.insert("", "end", values=clean_row)
            conn.close()
        except Exception as e:
            messagebox.showerror("خطأ", str(e))

    tk.Button(frame_alternatives, text="إظهار البدايل", font=("Cairo", 12), bg="#00796b", fg="white", command=fetch_alternatives).pack()
    alt_entry.bind("<Return>", lambda e: fetch_alternatives())

    # تبويب 3 - زرائر حسب الاستخدام 
    def load_buttons_by_use():
        try:
            df = pd.read_excel("Product Knowledge.xlsx")
            uses = df["MedicalUse"].dropna().unique()
            uses = sorted(set(u.strip() for u in uses if u))

            # إنشاء إطار رئيسي للتمرير
            main_frame = tk.Frame(frame_buttons_by_use, bg="#fff8e1")
            main_frame.pack(fill="both", expand=True)

            # إنشاء كانفاس وشريط تمرير
            canvas = tk.Canvas(main_frame, bg="#fff8e1", highlightthickness=0)
            scrollbar = tk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
            scrollable_frame = tk.Frame(canvas, bg="#fff8e1")

            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(
                    scrollregion=canvas.bbox("all")
                )
            )

            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)

            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")

            # توزيع الأزرار على الصفوف والأعمدة
            num_columns = 6  
            for i, use in enumerate(uses):
                row = i // num_columns
                col = i % num_columns
                
                btn = tk.Button(
                    scrollable_frame, 
                    text=use, 
                    font=("Cairo", 11), 
                    bg="#aed581", 
                    width=20, 
                    height=2,
                    wraplength=150,  
                    command=lambda u=use: show_products_by_use(df, u)
                )
                btn.grid(
                    row=row, 
                    column=col, 
                    padx=10, 
                    pady=10, 
                    sticky="nsew"
                )
                
                # جعل الأزرار تتمدد لتعبئة المساحة
                scrollable_frame.grid_columnconfigure(col, weight=1)
                scrollable_frame.grid_rowconfigure(row, weight=1)

        except Exception as e:
            messagebox.showerror("خطأ", str(e))

    def show_products_by_use(df, use):
        products = df[df["MedicalUse"].str.strip() == use]
        window = tk.Toplevel()
        window.title(f"📋 المنتجات - {use}")
        window.geometry("900x600")
        
        tree = ttk.Treeview(window, columns=("ItemCode", "ItemName", "ActiveIngredient"), show="headings")
        tree.pack(fill="both", expand=True)

        for col in ("ItemCode", "ItemName", "ActiveIngredient"):
            tree.heading(col, text=col)
            tree.column(col, anchor="center", width=250)

        for _, row in products.iterrows():
            tree.insert("", "end", values=(row["ItemCode"], row["ItemName"], row["ActiveIngredient"]))

    fetch_data("", tree)
    load_buttons_by_use()
    
    # 🌟 التعديل السحري عشان القائمة الرئيسية تشوف الشاشة
    return win

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    open_knowledge_window()
    root.mainloop()