import os

def update_server_name():
    old_server = "DESKTOP-8PMOIFI"
    new_server = "LAPREFaat"
    
    current_dir = os.getcwd()
    modified_files = []
    
    print(f"🔍 جاري البحث عن السيرفر القديم '{old_server}' في جميع المجلدات...\n")
    print("-" * 50)
    
    # os.walk بتخلي السكريبت يدخل جوه كل الفولدرات الفرعية
    for root, dirs, files in os.walk(current_dir):
        for filename in files:
            if filename.endswith(".py") and filename != "magic_script.py":
                filepath = os.path.join(root, filename)
                
                try:
                    with open(filepath, 'r', encoding='utf-8') as file:
                        content = file.read()
                    
                    if old_server in content:
                        new_content = content.replace(old_server, new_server)
                        
                        with open(filepath, 'w', encoding='utf-8') as file:
                            file.write(new_content)
                            
                        modified_files.append(filepath)
                        # طباعة اسم الملف بالمسار بتاعه
                        print(f"✅ تم التعديل في: {os.path.relpath(filepath, current_dir)}")
                except Exception as e:
                    print(f"❌ خطأ في ملف {filename}: {e}")
                    
    print("-" * 50)
    if modified_files:
        print(f"🎉 السحر اكتمل! تم تعديل {len(modified_files)} ملف بنجاح.")
    else:
        print("لم يتم العثور على أي ملفات تحتوي على اسم السيرفر القديم.")

if __name__ == "__main__":
    update_server_name()