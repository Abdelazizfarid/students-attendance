import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import os
import random
import string
import qrcode
from fpdf import FPDF
import tempfile
from tkinter import filedialog
# from datetime import datetime  # Removed due to naming conflict
from PIL import Image, ImageTk
import subprocess
import datetime
import requests


#pyinstaller --onedir --windowed application.py

# Get the directory where the script is running
app_dir = os.path.dirname(os.path.abspath(__file__))

# Define the database file path in the same directory
db_path = os.path.join(app_dir, 'students.db')

# Splash screen duration (in milliseconds)
SPLASH_DURATION = 3000

# Database setup
def create_database():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create centers table
    cursor.execute('''CREATE TABLE IF NOT EXISTS centers (
                        id INTEGER PRIMARY KEY,
                        name TEXT UNIQUE NOT NULL,
                        created_date TEXT)''')

    # Check if students table exists and has the old schema
    cursor.execute("PRAGMA table_info(students)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'center_name' in columns and 'center_id' not in columns:
        # Migration needed: old schema detected
        print("Migrating database schema...")
        
        # Get existing data
        cursor.execute("SELECT * FROM students")
        existing_students = cursor.fetchall()
        
        # Get existing attendance data
        cursor.execute("SELECT * FROM attendance")
        existing_attendance = cursor.fetchall()
        
        # Drop old students table
        cursor.execute("DROP TABLE IF EXISTS students")
        
        # Create new students table with proper schema
        cursor.execute('''CREATE TABLE students (
                            id INTEGER PRIMARY KEY,
                            name TEXT,
                            mobile TEXT,
                            center_id INTEGER,
                            learning_type TEXT,
                            parent_mobile TEXT,
                            barcode TEXT UNIQUE,
                            grade TEXT,
                            FOREIGN KEY(center_id) REFERENCES centers(id))''')
        
        # Migrate data
        for student in existing_students:
            student_id, name, mobile, center_name, learning_type, parent_mobile, barcode, grade = student
            
            # Create center if it doesn't exist
            cursor.execute("INSERT OR IGNORE INTO centers (name, created_date) VALUES (?, ?)",
                         (center_name, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            
            # Get center_id
            cursor.execute("SELECT id FROM centers WHERE name = ?", (center_name,))
            center_id = cursor.fetchone()[0]
            
            # Insert student with new schema
            cursor.execute('''INSERT INTO students (id, name, mobile, center_id, learning_type, parent_mobile, barcode, grade)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                         (student_id, name, mobile, center_id, learning_type, parent_mobile, barcode, grade))
        
        # Recreate attendance table and restore data
        cursor.execute("DROP TABLE IF EXISTS attendance")
        cursor.execute('''CREATE TABLE attendance (
                            id INTEGER PRIMARY KEY,
                            student_id INTEGER,
                            date TEXT,
                            marks INTEGER,
                            FOREIGN KEY(student_id) REFERENCES students(id))''')
        
        # Restore attendance data
        for attendance in existing_attendance:
            cursor.execute("INSERT INTO attendance VALUES (?, ?, ?, ?)", attendance)
        
        print("Database migration completed!")
    
    else:
        # Create students table with new schema if it doesn't exist
        cursor.execute('''CREATE TABLE IF NOT EXISTS students (
                            id INTEGER PRIMARY KEY,
                            name TEXT,
                            mobile TEXT,
                            center_id INTEGER,
                            learning_type TEXT,
                            parent_mobile TEXT,
                            barcode TEXT UNIQUE,
                            grade TEXT,
                            FOREIGN KEY(center_id) REFERENCES centers(id))''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS attendance (
                        id INTEGER PRIMARY KEY,
                        student_id INTEGER,
                        date TEXT,
                        marks INTEGER,
                        FOREIGN KEY(student_id) REFERENCES students(id))''')
    conn.commit()
    conn.close()

class SplashScreen(tk.Toplevel):
    def __init__(self, parent):
        tk.Toplevel.__init__(self, parent)
        self.title("شاشة البداية")
        self.attributes("-fullscreen", True)  # Open the splash screen in full screen
        self.configure(bg="white")  # Set background color to white

        # Get screen dimensions
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        # Add company name, creator name, and mobile number in black bold text
        self.company_name = tk.Label(self, text="ALFARID", fg="black", bg="white", font=("Helvetica", 50, "bold"))  # Black text, bold
        self.creator_name = tk.Label(self, text="Created by: Shreif Farid", fg="black", bg="white", font=("Helvetica", 20, "bold"))  # Black text, bold
        self.mobile_number = tk.Label(self, text="Mobile: 01116788750", fg="black", bg="white", font=("Helvetica", 20, "bold"))  # Black text, bold

        # Place the labels in the middle of the screen
        self.company_name.place(x=screen_width//2 - 150, y=screen_height//2 - 100)
        self.creator_name.place(x=screen_width//2 - 150, y=screen_height//2)
        self.mobile_number.place(x=screen_width//2 - 150, y=screen_height//2 + 50)

        # Close the splash screen after SPLASH_DURATION milliseconds
        self.after(2000, self.destroy)  # Replace 5000 with your desired duration in milliseconds

class StudentManagementApp:
    def __init__(self, root):
        self.root = root
        self.root.title("نظام إدارة الطلاب")

        # Set application window size
        width = int(self.root.winfo_screenwidth() / 2) + 200
        height = int(self.root.winfo_screenheight() / 2) + 300

        # Calculate the position to center the window on the screen
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        position_x = (screen_width // 2) - (width // 2)
        position_y = (screen_height // 2) - (height // 2)

        # Set the geometry of the window to the calculated position
        self.root.geometry(f"{width}x{height}+{position_x}+{position_y}")

        # Apply a modern theme
        style = ttk.Style()
        style.theme_use('clam')

        # Customize colors and fonts
        style.configure('TLabel', font=('Helvetica', 12), background='#f0f0f0')
        style.configure('TButton', font=('Helvetica', 12), background='#007acc', foreground='#ffffff')
        style.configure('TEntry', font=('Helvetica', 12))
        style.configure('Treeview', font=('Helvetica', 10), background='#ffffff', fieldbackground='#ffffff', foreground='#000000')
        style.configure('Treeview.Heading', font=('Helvetica', 12, 'bold'))

        # Set padding and margins for widgets
        self.padx = 10
        self.pady = 5

        self.create_widgets()

        # Global binding for Ctrl+V
        self.root.bind_all("<Control-v>", self.paste_clipboard)

    def create_widgets(self):
        # Notebook to switch between pages
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=self.padx, pady=self.pady)

        # Page 1: Student Management
        self.student_frame = ttk.Frame(self.notebook, padding=(10, 10))
        self.notebook.add(self.student_frame, text="إدارة الطلاب")

        # Page 2: Center Management
        self.center_frame = ttk.Frame(self.notebook, padding=(10, 10))
        self.notebook.add(self.center_frame, text="إدارة السنتر")

        # Filter frame for searchable dropdowns
        filter_frame = ttk.Frame(self.student_frame, padding=(10, 10))
        filter_frame.pack(fill="x")

        # Center Name Filter (اسم السنتر)
        ttk.Label(filter_frame, text="اسم السنتر:").grid(row=0, column=0, padx=self.padx, pady=self.pady, sticky="E")
        self.center_name_filter = ttk.Combobox(filter_frame, state="normal")
        self.center_name_filter.grid(row=0, column=1, padx=self.padx, pady=self.pady)

        # Student Type Filter (نوع الطالب)
        ttk.Label(filter_frame, text="نوع الطالب:").grid(row=0, column=2, padx=self.padx, pady=self.pady, sticky="E")
        self.student_type_filter = ttk.Combobox(filter_frame, state="normal")
        self.student_type_filter.grid(row=0, column=3, padx=self.padx, pady=self.pady)

        # Grade Filter (الصف)
        ttk.Label(filter_frame, text="الصف:").grid(row=0, column=4, padx=self.padx, pady=self.pady, sticky="E")
        self.grade_filter = ttk.Combobox(filter_frame, state="normal")
        self.grade_filter.grid(row=0, column=5, padx=self.padx, pady=self.pady)

        # Clear Filters Button
        ttk.Button(filter_frame, text="مسح الفلاتر", command=self.clear_all_filters).grid(row=0, column=6, padx=self.padx, pady=self.pady)

        # Frame for displaying records in a table
        self.table_frame = ttk.Frame(self.student_frame, padding=(10, 10))
        self.table_frame.pack(fill="both", expand=True)

        # Add scrollbars
        self.student_tree_scroll_y = ttk.Scrollbar(self.table_frame, orient="vertical")
        self.student_tree_scroll_x = ttk.Scrollbar(self.table_frame, orient="horizontal")

        self.tree = ttk.Treeview(self.table_frame, columns=("ID", "الاسم", "رقم الجوال", "اسم السنتر", "نوع الطالب", "رقم جوال ولي الامر", "الرمز الشريطي", "الصف"), show='headings',
                                yscrollcommand=self.student_tree_scroll_y.set, xscrollcommand=self.student_tree_scroll_x.set)

        self.student_tree_scroll_y.config(command=self.tree.yview)
        self.student_tree_scroll_x.config(command=self.tree.xview)

        self.student_tree_scroll_y.pack(side="right", fill="y")
        self.student_tree_scroll_x.pack(side="bottom", fill="x")

        self.tree.heading("ID", text="الرقم", anchor="center")
        self.tree.heading("الاسم", text="الاسم", anchor="center")
        self.tree.heading("رقم الجوال", text="رقم الجوال", anchor="center")
        self.tree.heading("اسم السنتر", text="اسم السنتر", anchor="center")
        self.tree.heading("نوع الطالب", text="نوع الطالب", anchor="center")
        self.tree.heading("رقم جوال ولي الامر", text="رقم جوال ولي الامر", anchor="center")
        self.tree.heading("الرمز الشريطي", text="الرمز الشريطي", anchor="center")
        self.tree.heading("الصف", text="الصف", anchor="center")

        self.tree.column("ID", anchor="center")
        self.tree.column("الاسم", anchor="center")
        self.tree.column("رقم الجوال", anchor="center")
        self.tree.column("اسم السنتر", anchor="center")
        self.tree.column("نوع الطالب", anchor="center")
        self.tree.column("رقم جوال ولي الامر", anchor="center")
        self.tree.column("الرمز الشريطي", anchor="center")
        self.tree.column("الصف", anchor="center")
        self.tree.pack(fill="both", expand=True)

        # Load students only (filters will be loaded later)
        self.load_center_names()
        self.load_students()

        # Bind the treeview selection event to a method
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        # Add, Update, Delete buttons
        btn_frame = ttk.Frame(self.table_frame, padding=(10, 10))
        btn_frame.pack(fill="x")

        ttk.Button(btn_frame, text="إضافة جديد", command=self.show_add_view).pack(side="left", padx=self.padx)
        self.update_button = ttk.Button(btn_frame, text="تحديث المحدد", command=self.update_student)
        self.update_button.pack(side="left", padx=self.padx)
        self.delete_button = ttk.Button(btn_frame, text="حذف المحدد", command=self.delete_student)
        self.delete_button.pack(side="left", padx=self.padx)

        # Frame for adding/updating a student
        self.add_frame = ttk.Frame(self.student_frame, padding=(10, 10))
        self.add_frame.pack(fill="x", pady=10)

        # Initialize StringVar variables
        self.student_name_var = tk.StringVar()
        self.student_mobile_var = tk.StringVar()
        self.student_center_name = tk.StringVar()
        self.student_learning_type = tk.StringVar(value="علمي")  # Set default value
        self.parent_mobile_var = tk.StringVar()
        self.barcode_var = tk.StringVar()
        self.student_grade_var = tk.StringVar()  # Added "Grade" variable

        ttk.Label(self.add_frame, text="الاسم:").grid(row=0, column=0, padx=self.padx, pady=self.pady, sticky="E")
        ttk.Entry(self.add_frame, textvariable=self.student_name_var).grid(row=0, column=1, padx=self.padx, pady=self.pady)

        ttk.Label(self.add_frame, text="رقم الجوال:").grid(row=1, column=0, padx=self.padx, pady=self.pady, sticky="E")
        ttk.Entry(self.add_frame, textvariable=self.student_mobile_var).grid(row=1, column=1, padx=self.padx, pady=self.pady)

        ttk.Label(self.add_frame, text="اسم السنتر:").grid(row=2, column=0, padx=self.padx, pady=self.pady, sticky="E")
        self.student_center_dropdown = ttk.Combobox(self.add_frame, textvariable=self.student_center_name, state="readonly")
        self.student_center_dropdown.grid(row=2, column=1, padx=self.padx, pady=self.pady)

        ttk.Label(self.add_frame, text="نوع الطالب:").grid(row=3, column=0, padx=self.padx, pady=self.pady, sticky="E")
        self.student_type_dropdown = ttk.Combobox(self.add_frame, textvariable=self.student_learning_type, state="readonly", values=["علمي", "ادبي"])
        self.student_type_dropdown.grid(row=3, column=1, padx=self.padx, pady=self.pady)

        ttk.Label(self.add_frame, text="رقم جوال ولي الامر:").grid(row=4, column=0, padx=self.padx, pady=self.pady, sticky="E")
        ttk.Entry(self.add_frame, textvariable=self.parent_mobile_var).grid(row=4, column=1, padx=self.padx, pady=self.pady)

        ttk.Label(self.add_frame, text="الرمز الشريطي:").grid(row=5, column=0, padx=self.padx, pady=self.pady, sticky="E")
        self.barcode_entry = ttk.Entry(self.add_frame, textvariable=self.barcode_var)
        self.barcode_entry.grid(row=5, column=1, padx=self.padx, pady=self.pady)
        # Bind barcode validation
        self.barcode_entry.bind("<KeyRelease>", self.validate_barcode_realtime)

        ttk.Label(self.add_frame, text="الصف:").grid(row=6, column=0, padx=self.padx, pady=self.pady, sticky="E")  # Added "Grade" field
        ttk.Entry(self.add_frame, textvariable=self.student_grade_var).grid(row=6, column=1, padx=self.padx, pady=self.pady)  # Added "Grade" field entry

        # Generate Barcode Button
        ttk.Button(self.add_frame, text="توليد الرمز", command=self.generate_barcode).grid(row=7, column=0, pady=10)

        self.save_button = ttk.Button(self.add_frame, text="حفظ الطالب", command=self.add_student)
        self.save_button.grid(row=7, column=1, pady=10)
        self.save_button.grid_remove()  # Hide initially

        # Generate QR Code Button
        ttk.Button(self.add_frame, text="توليد رمز الاستجابة السريعة", command=self.generate_qr_code).grid(row=8, columnspan=2, pady=10)

        # Create centers management interface
        self.create_centers_management()

        # Page 3: Attendance Management
        self.attendance_frame = ttk.Frame(self.notebook, padding=(10, 10))
        self.notebook.add(self.attendance_frame, text="إدارة الحضور")

        # Filter frame for attendance
        attendance_filter_frame = ttk.Frame(self.attendance_frame, padding=(10, 10))
        attendance_filter_frame.pack(fill="x")

        # Center Name Filter for Attendance
        ttk.Label(attendance_filter_frame, text="اسم السنتر:").grid(row=0, column=0, padx=self.padx, pady=self.pady, sticky="E")
        self.attendance_center_filter = ttk.Combobox(attendance_filter_frame, state="normal")
        self.attendance_center_filter.grid(row=0, column=1, padx=self.padx, pady=self.pady)

        # Student Type Filter for Attendance
        ttk.Label(attendance_filter_frame, text="نوع الطالب:").grid(row=0, column=2, padx=self.padx, pady=self.pady, sticky="E")
        self.attendance_type_filter = ttk.Combobox(attendance_filter_frame, state="normal")
        self.attendance_type_filter.grid(row=0, column=3, padx=self.padx, pady=self.pady)

        # Today's attendance checkbox
        self.today_only_var = tk.BooleanVar()
        self.today_only_var.set(True)  # Default to checked (show today's attendance)
        ttk.Checkbutton(attendance_filter_frame, text="حضور اليوم", variable=self.today_only_var, 
                       command=self.apply_attendance_filters).grid(row=0, column=4, padx=self.padx, pady=self.pady)

        # Clear Attendance Filters Button
        ttk.Button(attendance_filter_frame, text="مسح الفلاتر", command=self.clear_attendance_filters).grid(row=0, column=5, padx=self.padx, pady=self.pady)

        # Barcode search frame
        barcode_frame = ttk.Frame(self.attendance_frame, padding=(10, 10))
        barcode_frame.pack(fill="x")

        # Search form for Barcode
        ttk.Label(barcode_frame, text="مسح الرمز الشريطي:").grid(row=0, column=0, padx=self.padx, pady=self.pady, sticky="E")
        self.search_barcode_var = tk.StringVar()
        self.search_entry = ttk.Entry(barcode_frame, textvariable=self.search_barcode_var)
        self.search_entry.grid(row=0, column=1, padx=self.padx, pady=self.pady)
        # Bind Enter key to add_attendance function
        self.search_entry.bind("<Return>", lambda event: self.add_attendance())
        # Bind KeyRelease to auto-confirm after 1 second delay
        self.search_entry.bind("<KeyRelease>", self.on_attendance_barcode_change)

        ttk.Button(barcode_frame, text="تأكيد", command=self.add_attendance).grid(row=0, column=2, padx=self.padx, pady=self.pady)

        # Treeview frame for attendance
        attendance_tree_frame = ttk.Frame(self.attendance_frame, padding=(10, 10))
        attendance_tree_frame.pack(fill="both", expand=True)

        # Add scrollbars for attendance treeview
        self.attendance_tree_scroll_y = ttk.Scrollbar(attendance_tree_frame, orient="vertical")
        self.attendance_tree_scroll_x = ttk.Scrollbar(attendance_tree_frame, orient="horizontal")

        # For the attendance Treeview
        self.attendance_tree = ttk.Treeview(attendance_tree_frame, columns=("ID", "الاسم", "رقم الجوال", "اسم السنتر", "نوع الطالب", "رقم جوال ولي الامر", "الصف", "التاريخ", "الدرجات"), show='headings',
                                            yscrollcommand=self.attendance_tree_scroll_y.set, xscrollcommand=self.attendance_tree_scroll_x.set)

        self.attendance_tree_scroll_y.config(command=self.attendance_tree.yview)
        self.attendance_tree_scroll_x.config(command=self.attendance_tree.xview)

        self.attendance_tree_scroll_y.pack(side="right", fill="y")
        self.attendance_tree_scroll_x.pack(side="bottom", fill="x")

        self.attendance_tree.heading("الاسم", text="الاسم", anchor="center")
        self.attendance_tree.heading("رقم الجوال", text="رقم الجوال", anchor="center")
        self.attendance_tree.heading("اسم السنتر", text="اسم السنتر", anchor="center")
        self.attendance_tree.heading("نوع الطالب", text="نوع الطالب", anchor="center")
        self.attendance_tree.heading("رقم جوال ولي الامر", text="رقم جوال ولي الامر", anchor="center")
        self.attendance_tree.heading("الصف", text="الصف", anchor="center")  # Added "Grade" column in attendance
        self.attendance_tree.heading("التاريخ", text="التاريخ", anchor="center")
        self.attendance_tree.heading("الدرجات", text="الدرجات", anchor="center")

        self.attendance_tree.column("الاسم", anchor="center")
        self.attendance_tree.column("رقم الجوال", anchor="center")
        self.attendance_tree.column("اسم السنتر", anchor="center")
        self.attendance_tree.column("نوع الطالب", anchor="center")
        self.attendance_tree.column("رقم جوال ولي الامر", anchor="center")
        self.attendance_tree.column("الصف", anchor="center")  # Added "Grade" column in attendance
        self.attendance_tree.column("التاريخ", anchor="center")
        self.attendance_tree.column("الدرجات", anchor="center", width=100)

        self.attendance_tree.pack(fill="both", expand=True)

        # Bind double-click for editing marks
        self.attendance_tree.bind("<Double-1>", self.edit_marks)

        # Button frame for attendance
        attendance_btn_frame = ttk.Frame(self.attendance_frame, padding=(10, 10))
        attendance_btn_frame.pack(fill="x")

        # Add delete button for attendance
        ttk.Button(attendance_btn_frame, text="حذف المحدد", command=self.delete_attendance).pack(side="left", padx=self.padx)

        # Statistics frame for attendance
        stats_frame = ttk.Frame(self.attendance_frame, padding=(10, 10))
        stats_frame.pack(fill="x")

        # Total students label
        self.total_students_var = tk.StringVar(value="اجمالي عدد الطلاب: 0")
        self.total_students_label = ttk.Label(stats_frame, textvariable=self.total_students_var, font=("Helvetica", 12, "bold"))
        self.total_students_label.pack(side="left", padx=self.padx)

        # Present students label
        self.present_students_var = tk.StringVar(value="عدد الطلاب الحاضرين اليوم: 0")
        self.present_students_label = ttk.Label(stats_frame, textvariable=self.present_students_var, font=("Helvetica", 12, "bold"))
        self.present_students_label.pack(side="left", padx=self.padx)

        # Load attendance data from the database
        self.load_attendance()
        self.update_attendance_statistics()

        # Page 4: Reporting
        self.reporting_frame = ttk.Frame(self.notebook, padding=(10, 10))
        self.notebook.add(self.reporting_frame, text="التقارير")

        # Filter frame for reporting
        reporting_filter_frame = ttk.Frame(self.reporting_frame, padding=(10, 10))
        reporting_filter_frame.pack(fill="x")

        # Center Name Filter for Reporting
        ttk.Label(reporting_filter_frame, text="اسم السنتر:").grid(row=0, column=0, padx=self.padx, pady=self.pady, sticky="E")
        self.reporting_center_filter = ttk.Combobox(reporting_filter_frame, state="normal")
        self.reporting_center_filter.grid(row=0, column=1, padx=self.padx, pady=self.pady)

        # Student Type Filter for Reporting
        ttk.Label(reporting_filter_frame, text="نوع الطالب:").grid(row=0, column=2, padx=self.padx, pady=self.pady, sticky="E")
        self.reporting_type_filter = ttk.Combobox(reporting_filter_frame, state="normal")
        self.reporting_type_filter.grid(row=0, column=3, padx=self.padx, pady=self.pady)

        # Apply Filter Button for Reporting
        ttk.Button(reporting_filter_frame, text="تصفية", command=self.apply_reporting_filters).grid(row=0, column=4, padx=self.padx, pady=self.pady)

        # Barcode and month search frame
        search_frame = ttk.Frame(self.reporting_frame, padding=(10, 10))
        search_frame.pack(fill="x")

        # Search form for Barcode in Reporting tab
        ttk.Label(search_frame, text="مسح الرمز الشريطي:").grid(row=0, column=0, padx=self.padx, pady=self.pady, sticky="E")
        self.report_barcode_var = tk.StringVar()
        self.report_entry = ttk.Entry(search_frame, textvariable=self.report_barcode_var)
        self.report_entry.grid(row=0, column=1, padx=self.padx, pady=self.pady)
        # Bind Enter key to filter_by_barcode function
        self.report_entry.bind("<Return>", lambda event: self.filter_by_barcode())
        # Bind KeyRelease to auto-confirm after 1 second delay
        self.report_entry.bind("<KeyRelease>", self.on_reporting_barcode_change)

        ttk.Button(search_frame, text="تأكيد", command=self.filter_by_barcode).grid(row=0, column=2, padx=self.padx, pady=self.pady)

        # Month filter
        ttk.Label(search_frame, text="التصفية حسب الشهر (MM-YYYY):").grid(row=0, column=3, padx=self.padx, pady=self.pady, sticky="E")
        self.month_filter_var = tk.StringVar()
        self.month_filter_entry = ttk.Entry(search_frame, textvariable=self.month_filter_var)
        self.month_filter_entry.grid(row=0, column=4, padx=self.padx, pady=self.pady)

        # Treeview frame for reporting
        reporting_tree_frame = ttk.Frame(self.reporting_frame, padding=(10, 10))
        reporting_tree_frame.pack(fill="both", expand=True)

        # Add scrollbars for reporting treeview
        self.reporting_tree_scroll_y = ttk.Scrollbar(reporting_tree_frame, orient="vertical")
        self.reporting_tree_scroll_x = ttk.Scrollbar(reporting_tree_frame, orient="horizontal")

        self.reporting_tree = ttk.Treeview(reporting_tree_frame, columns=("الاسم", "رقم الجوال", "اسم السنتر", "نوع الطالب", "رقم جوال ولي الامر", "الصف", "التاريخ", "الدرجات"), show='headings',
                                           yscrollcommand=self.reporting_tree_scroll_y.set, xscrollcommand=self.reporting_tree_scroll_x.set)

        self.reporting_tree_scroll_y.config(command=self.reporting_tree.yview)
        self.reporting_tree_scroll_x.config(command=self.reporting_tree.xview)

        self.reporting_tree_scroll_y.pack(side="right", fill="y")
        self.reporting_tree_scroll_x.pack(side="bottom", fill="x")

        self.reporting_tree.heading("الاسم", text="الاسم", anchor="center")
        self.reporting_tree.heading("رقم الجوال", text="رقم الجوال", anchor="center")
        self.reporting_tree.heading("اسم السنتر", text="اسم السنتر", anchor="center")
        self.reporting_tree.heading("نوع الطالب", text="نوع الطالب", anchor="center")
        self.reporting_tree.heading("رقم جوال ولي الامر", text="رقم جوال ولي الامر", anchor="center")
        self.reporting_tree.heading("الصف", text="الصف", anchor="center")  # Added "Grade" column in reporting
        self.reporting_tree.heading("التاريخ", text="التاريخ", anchor="center")
        self.reporting_tree.heading("الدرجات", text="الدرجات", anchor="center")

        self.reporting_tree.column("الاسم", anchor="center")
        self.reporting_tree.column("رقم الجوال", anchor="center")
        self.reporting_tree.column("اسم السنتر", anchor="center")
        self.reporting_tree.column("نوع الطالب", anchor="center")
        self.reporting_tree.column("رقم جوال ولي الامر", anchor="center")
        self.reporting_tree.column("الصف", anchor="center")  # Added "Grade" column in reporting
        self.reporting_tree.column("التاريخ", anchor="center")
        self.reporting_tree.column("الدرجات", anchor="center", width=100)

        self.reporting_tree.pack(fill="both", expand=True)

        # Counter frame
        counter_frame = ttk.Frame(self.reporting_frame, padding=(10, 10))
        counter_frame.pack(fill="x")

        # Counter Label
        self.result_count_var = tk.StringVar(value="النتائج: 0")
        self.result_count_label = ttk.Label(counter_frame, textvariable=self.result_count_var)
        self.result_count_label.pack(side="left", padx=self.padx)

        # Footer: Display name and phone number in the application
        self.footer_frame = ttk.Frame(self.root, padding=(10, 10))
        self.footer_frame.pack(fill="x", side="bottom")
        ttk.Label(self.footer_frame, text="المهندس شريف فريد", font=("Helvetica", 12, "bold")).pack(side="left", padx=10)
        ttk.Label(self.footer_frame, text="01116788750", font=("Helvetica", 12, "bold")).pack(side="left", padx=10)

        # Now load all filters after all widgets are created
        self.load_filters()

    def load_filters(self):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Load distinct values for Center Name (اسم السنتر)
        cursor.execute("SELECT name FROM centers ORDER BY name")
        center_names = [row[0] for row in cursor.fetchall()]
        self.center_name_filter['values'] = center_names

        # Load distinct values for Student Type (نوع الطالب)
        student_types = ["علمي", "ادبي"]
        self.student_type_filter['values'] = student_types

        # Load distinct values for Grade (الصف)
        cursor.execute("SELECT DISTINCT grade FROM students")
        grades = [row[0] for row in cursor.fetchall()]
        self.grade_filter['values'] = grades

        # Load attendance filters
        self.attendance_center_filter['values'] = center_names
        self.attendance_type_filter['values'] = student_types

        # Load reporting filters
        self.reporting_center_filter['values'] = center_names
        self.reporting_type_filter['values'] = student_types

        # Bind change events to filters for automatic filtering
        self.center_name_filter.bind("<<ComboboxSelected>>", lambda e: self.apply_filters())
        self.student_type_filter.bind("<<ComboboxSelected>>", lambda e: self.apply_filters())
        self.grade_filter.bind("<<ComboboxSelected>>", lambda e: self.apply_filters())
        
        # Bind attendance filter change events
        self.attendance_center_filter.bind("<<ComboboxSelected>>", lambda e: self.apply_attendance_filters())
        self.attendance_type_filter.bind("<<ComboboxSelected>>", lambda e: self.apply_attendance_filters())
        
        # Add clear filter functionality
        self.center_name_filter.bind("<KeyRelease>", self.on_filter_change)
        self.student_type_filter.bind("<KeyRelease>", self.on_filter_change)
        self.grade_filter.bind("<KeyRelease>", self.on_filter_change)

        conn.close()

    def paste_clipboard(self, event):
        """Handle the Ctrl+V paste event for specific entry widgets."""
        try:
            clipboard_text = self.root.clipboard_get()  # Get the text from the clipboard
            focused_widget = self.root.focus_get()

            # Check if the focused widget is a text entry widget (like tk.Entry or ttk.Entry)
            if isinstance(focused_widget, (tk.Entry, ttk.Entry)):
                # Prevent the default Ctrl+V behavior for this event to avoid duplication
                event.widget.delete(0, tk.END)  # Clear the entry field before inserting

                # Insert clipboard content at the current cursor position
                focused_widget.insert(tk.INSERT, clipboard_text)

                return 'break'  # Prevent any further handling of the event
        except tk.TclError:
            pass  # Handle cases where clipboard is empty or no text is available

    def apply_filters(self):
        self.load_students()
        
    def on_filter_change(self, event=None):
        """Handle filter changes for real-time filtering"""
        # Clear the filter if user types something
        widget = event.widget
        if hasattr(widget, 'get') and widget.get() == "":
            self.apply_filters()
            
    def clear_all_filters(self):
        """Clear all filters and show all students"""
        self.center_name_filter.set("")
        self.student_type_filter.set("")
        self.grade_filter.set("")
        self.apply_filters()
        
    def clear_attendance_filters(self):
        """Clear all attendance filters and show all attendance"""
        self.attendance_center_filter.set("")
        self.attendance_type_filter.set("")
        self.today_only_var.set(True)
        self.apply_attendance_filters()

    def load_students(self):
        # Clear the existing data
        for item in self.tree.get_children():
            self.tree.delete(item)

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Join with centers table to get center names
        query = """SELECT students.id, students.name, students.mobile, centers.name as center_name,
                          students.learning_type, students.parent_mobile, students.barcode, students.grade
                   FROM students
                   LEFT JOIN centers ON students.center_id = centers.id"""
        parameters = []

        # Apply filters if any filter is selected
        if self.center_name_filter.get():
            query += " WHERE centers.name = ?"
            parameters.append(self.center_name_filter.get())

        if self.student_type_filter.get():
            if "WHERE" in query:
                query += " AND learning_type = ?"
            else:
                query += " WHERE learning_type = ?"
            parameters.append(self.student_type_filter.get())

        if self.grade_filter.get():
            if "WHERE" in query:
                query += " AND grade = ?"
            else:
                query += " WHERE grade = ?"
            parameters.append(self.grade_filter.get())

        cursor.execute(query, parameters)
        rows = cursor.fetchall()

        for row in rows:
            self.tree.insert("", tk.END, values=row)
        
        conn.close()


    def apply_attendance_filters(self):
        self.load_attendance()
        self.update_attendance_statistics()

    def load_attendance(self):
        # Clear the existing data
        for item in self.attendance_tree.get_children():
            self.attendance_tree.delete(item)

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Base query with join
        query = '''SELECT attendance.id, students.name, students.mobile, centers.name as center_name,
                          students.learning_type, students.parent_mobile, students.grade, attendance.date, attendance.marks
                   FROM attendance
                   JOIN students ON attendance.student_id = students.id
                   LEFT JOIN centers ON students.center_id = centers.id'''
        parameters = []

        # Apply filters if any filter is selected
        conditions = []
        
        # Check if "today only" is selected
        if hasattr(self, 'today_only_var') and self.today_only_var.get():
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            conditions.append("attendance.date = ?")
            parameters.append(today)
        
        if self.attendance_center_filter.get():
            conditions.append("centers.name = ?")
            parameters.append(self.attendance_center_filter.get())

        if self.attendance_type_filter.get():
            conditions.append("students.learning_type = ?")
            parameters.append(self.attendance_type_filter.get())

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY attendance.id DESC"

        cursor.execute(query, parameters)

        rows = cursor.fetchall()
        for row in rows:
            # Insert the id (row[0]) but hide it in the treeview
            self.attendance_tree.insert("", tk.END, values=row)

        conn.close()

    def update_attendance_statistics(self):
        """Calculate and update attendance statistics based on current filters"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get current filter values
        center_filter = self.attendance_center_filter.get() if hasattr(self, 'attendance_center_filter') else ""
        type_filter = self.attendance_type_filter.get() if hasattr(self, 'attendance_type_filter') else ""

        # Build base query for total students (filtered by current selections)
        total_query = """SELECT COUNT(DISTINCT students.id)
                        FROM students
                        LEFT JOIN centers ON students.center_id = centers.id"""
        total_parameters = []

        # Apply filters for total students count
        conditions = []
        if center_filter:
            conditions.append("centers.name = ?")
            total_parameters.append(center_filter)

        if type_filter:
            conditions.append("students.learning_type = ?")
            total_parameters.append(type_filter)

        if conditions:
            total_query += " WHERE " + " AND ".join(conditions)

        cursor.execute(total_query, total_parameters)
        total_students = cursor.fetchone()[0]

        # Build query for present students (attendance today) with same filters
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        present_query = """SELECT COUNT(DISTINCT students.id)
                          FROM attendance
                          JOIN students ON attendance.student_id = students.id
                          LEFT JOIN centers ON students.center_id = centers.id
                          WHERE attendance.date = ?"""
        present_parameters = [today]

        # Apply same filters for present students
        if center_filter:
            present_query += " AND centers.name = ?"
            present_parameters.append(center_filter)

        if type_filter:
            present_query += " AND students.learning_type = ?"
            present_parameters.append(type_filter)

        cursor.execute(present_query, present_parameters)
        present_students = cursor.fetchone()[0]

        # Get total unfiltered count for comparison if filters are applied
        total_unfiltered = 0
        if center_filter or type_filter:
            cursor.execute("SELECT COUNT(DISTINCT students.id) FROM students")
            total_unfiltered = cursor.fetchone()[0]

        conn.close()

        # Update the labels with filtered counts
        if center_filter or type_filter:
            self.total_students_var.set(f"اجمالي عدد الطلاب (مفلتر): {total_students} / {total_unfiltered}")
        else:
            self.total_students_var.set(f"اجمالي عدد الطلاب: {total_students}")
        self.present_students_var.set(f"عدد الطلاب الحاضرين اليوم: {present_students}")

    def add_attendance(self):
        barcode = self.search_barcode_var.get()
        if not barcode:
            messagebox.showwarning("خطأ", "يرجى إدخال الرمز الشريطي.")
            return

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''SELECT students.id, students.name, students.mobile, centers.name as center_name, 
                                 students.learning_type, students.parent_mobile, students.grade 
                          FROM students 
                          LEFT JOIN centers ON students.center_id = centers.id 
                          WHERE students.barcode = ?''', (barcode,))
        student = cursor.fetchone()

        if student:
            student_id = student[0]
            name = student[1]
            mobile = student[2]
            center_name = student[3]
            learning_type = student[4]
            parent_mobile = student[5]
            grade = student[6]
            current_date = datetime.datetime.now().strftime("%Y-%m-%d")

            # Insert the attendance record into the database
            cursor.execute('''INSERT INTO attendance (student_id, date, marks)
                            VALUES (?, ?, ?)''', (student_id, current_date, ""))

            conn.commit()

            # Retrieve the attendance ID after insertion
            attendance_id = cursor.lastrowid

            # Add the data to the Treeview (make sure to include the hidden ID column)
            self.attendance_tree.insert("", 0, values=(attendance_id, name, mobile, center_name, learning_type, parent_mobile, grade, current_date, ""))  # Added 'attendance_id'
            messagebox.showinfo("نجاح", f"تم تسجيل الحضور للطالب {name}.")
            # Update statistics after adding attendance
            self.update_attendance_statistics()
            # Clear the barcode field for next scan
            self.search_barcode_var.set("")
        else:
            messagebox.showwarning("خطأ", "لم يتم العثور على طالب بالرمز الشريطي المدخل.")

        conn.close()

    def auto_confirm_attendance(self, barcode):
        """Auto-confirm attendance after 1 second delay if barcode exists"""
        if not barcode.strip():
            return

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM students WHERE barcode = ?", (barcode,))
        student = cursor.fetchone()
        conn.close()

        if student:
            # Barcode exists, auto-confirm attendance
            self.add_attendance()
        # If barcode doesn't exist, do nothing (user can continue typing or press enter)

    def auto_confirm_reporting(self, barcode):
        """Auto-confirm reporting filter after 1 second delay if barcode exists"""
        if not barcode.strip():
            return

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM students WHERE barcode = ?", (barcode,))
        student = cursor.fetchone()
        conn.close()

        if student:
            # Barcode exists, auto-filter reports
            self.filter_by_barcode()
        # If barcode doesn't exist, do nothing (user can continue typing or press enter)

    def on_attendance_barcode_change(self, event=None):
        """Handle barcode entry changes in attendance screen - instant auto-confirm"""
        # Get current barcode value
        barcode = self.search_barcode_var.get().strip()

        # Only auto-confirm if barcode is not empty and has reasonable length
        if barcode and len(barcode) >= 3:  # Minimum 3 characters to avoid premature confirmation
            self.auto_confirm_attendance(barcode)

    def on_reporting_barcode_change(self, event=None):
        """Handle barcode entry changes in reporting screen - instant auto-confirm"""
        # Get current barcode value
        barcode = self.report_barcode_var.get().strip()

        # Only auto-confirm if barcode is not empty and has reasonable length
        if barcode and len(barcode) >= 3:  # Minimum 3 characters to avoid premature confirmation
            self.auto_confirm_reporting(barcode)

    def apply_reporting_filters(self):
        """Apply filters to the reporting view"""
        self.filter_by_barcode()

    def filter_by_barcode(self):
        barcode = self.report_barcode_var.get()
        month_filter = self.month_filter_var.get()

        if not barcode:
            messagebox.showwarning("خطأ", "يرجى إدخال الرمز الشريطي.")
            return

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Build dynamic query with filters
        query = '''SELECT students.name, students.mobile, centers.name as center_name, students.learning_type, students.parent_mobile, students.grade, attendance.date, attendance.marks
                   FROM attendance
                   JOIN students ON attendance.student_id = students.id
                   LEFT JOIN centers ON students.center_id = centers.id'''
        parameters = []

        # Add WHERE conditions
        conditions = ["students.barcode = ?"]
        parameters.append(barcode)

        if month_filter:
            conditions.append("strftime('%m-%Y', attendance.date) = ?")
            parameters.append(month_filter)

        if self.reporting_center_filter.get():
            conditions.append("centers.name = ?")
            parameters.append(self.reporting_center_filter.get())

        if self.reporting_type_filter.get():
            conditions.append("students.learning_type = ?")
            parameters.append(self.reporting_type_filter.get())

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY attendance.id DESC"

        cursor.execute(query, parameters)

        rows = cursor.fetchall()

        # Clear the existing data in the reporting treeview
        for item in self.reporting_tree.get_children():
            self.reporting_tree.delete(item)

        # Insert the results into the Treeview
        for row in rows:
            self.reporting_tree.insert("", tk.END, values=row)

        conn.close()

        # Update result counter
        self.result_count_var.set(f"النتائج: {len(rows)}")

    def on_tree_select(self, event):
        if self.tree.selection():
            selected_item = self.tree.selection()[0]
            selected_student = self.tree.item(selected_item, 'values')
            self.student_name_var.set(selected_student[1])
            self.student_mobile_var.set(selected_student[2])
            self.student_center_name.set(selected_student[3])
            self.student_learning_type.set(selected_student[4])
            self.parent_mobile_var.set(selected_student[5])
            self.barcode_var.set(selected_student[6])
            self.student_grade_var.set(selected_student[7])  # Set 'Grade' field
            self.save_button.grid_remove()  # Hide the Save button

    def show_add_view(self):
        # Clear the form fields for a new entry
        self.student_name_var.set("")
        self.student_mobile_var.set("")
        self.student_center_name.set("")
        self.student_learning_type.set("علمي")  # Set default student type
        self.parent_mobile_var.set("")
        self.barcode_var.set("")
        self.student_grade_var.set("")  # Clear 'Grade' field
        # Show Save button and keep Update button visible
        self.save_button.grid()

    def generate_barcode(self):
        # Generate a random 10-character alphanumeric barcode
        barcode = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        self.barcode_var.set(barcode)

    def generate_qr_code(self):
        barcode = self.barcode_var.get()
        mobile = self.student_mobile_var.get()

        if barcode and mobile:
            # Generate QR code
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(barcode)
            qr.make(fit=True)
            img = qr.make_image(fill='black', back_color='white')

            # Save QR code to a temporary file
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
                img.save(tmp_file, "PNG")
                tmp_file_path = tmp_file.name

            # Ask the user where to save the PDF
            pdf_output_path = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf")],
                title="حفظ ملف PDF"
            )

            if pdf_output_path:
                # Create a PDF instance
                pdf = FPDF()
                pdf.add_page()

                # Use default Arial font
                pdf.set_font('Arial', 'B', 12)

                # Add the QR code image
                pdf.image(tmp_file_path, x=60, y=60, w=90, h=90)  # Adjust image position and size

                # Add the mobile number and barcode to the PDF
                pdf.set_xy(10, 160)
                pdf.cell(190, 10, f"Mobile: {mobile}", 0, 1, 'C')
                pdf.cell(190, 10, f"Bacrode : {barcode}", 0, 1, 'C')

                # Output the PDF to the specified file path
                pdf.output(pdf_output_path)

                # Clean up the temporary QR code image file
                os.remove(tmp_file_path)

                # Show a success message
                messagebox.showinfo("نجاح", f"تم حفظ رمز الاستجابة السريعة في {pdf_output_path}")
            else:
                # Clean up the temporary file if the user cancels the save dialog
                os.remove(tmp_file_path)
        else:
            # Show a warning if no barcode or mobile number is provided
            messagebox.showwarning("خطأ", "لا يوجد رمز شريطي أو رقم جوال لتوليد رمز الاستجابة السريعة.")

    def validate_barcode_realtime(self, event=None):
        """Real-time validation of barcode uniqueness"""
        barcode = self.barcode_var.get().strip()
        if barcode and len(barcode) >= 3:  # Start checking after 3 characters
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check if we're updating (exclude current student if editing)
            if hasattr(self, 'tree') and self.tree.selection():
                # We're editing - exclude current student
                selected_item = self.tree.selection()[0]
                student_id = self.tree.item(selected_item)['values'][0]
                cursor.execute("SELECT id FROM students WHERE barcode = ? AND id != ?", (barcode, student_id))
            else:
                # We're adding new student
                cursor.execute("SELECT id FROM students WHERE barcode = ?", (barcode,))
            
            existing_student = cursor.fetchone()
            conn.close()
            
            if existing_student:
                # Change background color to indicate duplicate
                self.barcode_entry.configure(background='#ffcccc')  # Light red
            else:
                # Reset to normal background
                self.barcode_entry.configure(background='white')

    def create_centers_management(self):
        """Create the centers management interface"""
        # Initialize center form variables
        self.center_name_var = tk.StringVar()

        # Frame for displaying centers in a table
        self.centers_table_frame = ttk.Frame(self.center_frame, padding=(10, 10))
        self.centers_table_frame.pack(fill="both", expand=True)

        # Add scrollbars
        self.centers_tree_scroll_y = ttk.Scrollbar(self.centers_table_frame, orient="vertical")
        self.centers_tree_scroll_x = ttk.Scrollbar(self.centers_table_frame, orient="horizontal")

        self.centers_tree = ttk.Treeview(self.centers_table_frame, columns=("ID", "الاسم", "تاريخ الإنشاء"), show='headings',
                                        yscrollcommand=self.centers_tree_scroll_y.set, xscrollcommand=self.centers_tree_scroll_x.set)

        self.centers_tree_scroll_y.config(command=self.centers_tree.yview)
        self.centers_tree_scroll_x.config(command=self.centers_tree.xview)

        self.centers_tree_scroll_y.pack(side="right", fill="y")
        self.centers_tree_scroll_x.pack(side="bottom", fill="x")

        self.centers_tree.heading("ID", text="الرقم", anchor="center")
        self.centers_tree.heading("الاسم", text="الاسم", anchor="center")
        self.centers_tree.heading("تاريخ الإنشاء", text="تاريخ الإنشاء", anchor="center")

        self.centers_tree.column("ID", anchor="center", width=80)
        self.centers_tree.column("الاسم", anchor="center", width=200)
        self.centers_tree.column("تاريخ الإنشاء", anchor="center", width=150)
        self.centers_tree.pack(fill="both", expand=True)

        # Load centers data
        self.load_centers()
        self.load_center_names()

        # Bind treeview selection event
        self.centers_tree.bind("<<TreeviewSelect>>", self.on_center_select)

        # Add, Update, Delete buttons
        btn_frame = ttk.Frame(self.centers_table_frame, padding=(10, 10))
        btn_frame.pack(fill="x")

        ttk.Button(btn_frame, text="إضافة جديد", command=self.show_add_center_view).pack(side="left", padx=self.padx)
        self.update_center_button = ttk.Button(btn_frame, text="تحديث المحدد", command=self.update_center)
        self.update_center_button.pack(side="left", padx=self.padx)
        self.delete_center_button = ttk.Button(btn_frame, text="حذف المحدد", command=self.delete_center)
        self.delete_center_button.pack(side="left", padx=self.padx)

        # Frame for adding/updating a center
        self.center_add_frame = ttk.Frame(self.center_frame, padding=(10, 10))
        self.center_add_frame.pack(fill="x", pady=10)

        ttk.Label(self.center_add_frame, text="اسم السنتر:").grid(row=0, column=0, padx=self.padx, pady=self.pady, sticky="E")
        ttk.Entry(self.center_add_frame, textvariable=self.center_name_var).grid(row=0, column=1, padx=self.padx, pady=self.pady)

        self.save_center_button = ttk.Button(self.center_add_frame, text="حفظ السنتر", command=self.add_center)
        self.save_center_button.grid(row=1, column=1, pady=10)
        self.save_center_button.grid_remove()  # Hide initially

    def load_centers(self):
        """Load centers from database and display in treeview"""
        # Clear existing data
        for item in self.centers_tree.get_children():
            self.centers_tree.delete(item)

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT id, name, created_date FROM centers ORDER BY id DESC")
        rows = cursor.fetchall()

        for row in rows:
            self.centers_tree.insert("", tk.END, values=row)

        conn.close()

    def load_center_names(self):
        """Load center names for dropdowns"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT id, name FROM centers ORDER BY name")
        centers = cursor.fetchall()
        conn.close()

        # Store centers as (id, name) tuples for easy lookup
        self.centers_list = centers
        self.center_names = [center[1] for center in centers]

        # Update center dropdown in student management if it exists
        if hasattr(self, 'student_center_dropdown'):
            self.student_center_dropdown['values'] = self.center_names

    def on_center_select(self, event):
        """Handle center selection in treeview"""
        if self.centers_tree.selection():
            selected_item = self.centers_tree.selection()[0]
            selected_center = self.centers_tree.item(selected_item, 'values')
            self.center_name_var.set(selected_center[1])
            self.save_center_button.grid_remove()  # Hide save button

    def show_add_center_view(self):
        """Clear form for adding new center"""
        self.center_name_var.set("")
        self.save_center_button.grid()  # Show save button

    def add_center(self):
        """Add new center to database"""
        center_name = self.center_name_var.get().strip()

        if not center_name:
            messagebox.showwarning("خطأ", "يرجى إدخال اسم السنتر.")
            return

        if messagebox.askyesno("تأكيد", "هل أنت متأكد من أنك تريد حفظ هذا السنتر؟"):
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()

                current_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute("INSERT INTO centers (name, created_date) VALUES (?, ?)",
                             (center_name, current_date))

                conn.commit()
                conn.close()

                self.load_centers()
                self.load_center_names()  # Refresh dropdowns
                messagebox.showinfo("نجاح", "تم إضافة السنتر بنجاح!")
                self.show_add_center_view()

            except sqlite3.IntegrityError:
                messagebox.showerror("خطأ", "اسم السنتر موجود بالفعل.")
            except sqlite3.Error as e:
                messagebox.showerror("خطأ في قاعدة البيانات", f"حدث خطأ أثناء إضافة السنتر: {e}")

    def update_center(self):
        """Update selected center"""
        selected_item = self.centers_tree.selection()
        if selected_item:
            if messagebox.askyesno("تأكيد", "هل أنت متأكد من أنك تريد تحديث هذا السنتر؟"):
                center_id = self.centers_tree.item(selected_item)['values'][0]
                center_name = self.center_name_var.get().strip()

                if not center_name:
                    messagebox.showwarning("خطأ", "يرجى إدخال اسم السنتر.")
                    return

                try:
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    cursor.execute("UPDATE centers SET name=? WHERE id=?",
                                 (center_name, center_id))
                    conn.commit()
                    conn.close()

                    self.load_centers()
                    self.load_center_names()  # Refresh dropdowns
                    messagebox.showinfo("نجاح", "تم تحديث السنتر بنجاح!")

                except sqlite3.IntegrityError:
                    messagebox.showerror("خطأ", "اسم السنتر موجود بالفعل.")
                except sqlite3.Error as e:
                    messagebox.showerror("خطأ في قاعدة البيانات", f"حدث خطأ أثناء تحديث السنتر: {e}")
        else:
            messagebox.showwarning("تحديد سنتر", "يرجى تحديد سنتر لتحديثه.")

    def delete_center(self):
        """Delete selected center and associated records"""
        selected_item = self.centers_tree.selection()
        if selected_item:
            if messagebox.askyesno("تأكيد", "هل أنت متأكد من أنك تريد حذف هذا السنتر؟\nسيتم حذف جميع السجلات المرتبطة بهذا السنتر."):
                center_id = self.centers_tree.item(selected_item)['values'][0]

                try:
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()

                    # Get all student IDs for this center
                    cursor.execute("SELECT id FROM students WHERE center_id=?", (center_id,))
                    student_ids = [row[0] for row in cursor.fetchall()]

                    # Delete attendance records for these students
                    if student_ids:
                        cursor.execute(f"DELETE FROM attendance WHERE student_id IN ({','.join('?' * len(student_ids))})",
                                     student_ids)

                    # Delete students
                    cursor.execute("DELETE FROM students WHERE center_id=?", (center_id,))

                    # Delete center
                    cursor.execute("DELETE FROM centers WHERE id=?", (center_id,))

                    conn.commit()
                    conn.close()

                    self.load_centers()
                    self.load_center_names()  # Refresh dropdowns
                    self.load_students()  # Refresh student list
                    self.load_attendance()  # Refresh attendance list
                    messagebox.showinfo("نجاح", "تم حذف السنتر وجميع السجلات المرتبطة بنجاح!")

                except sqlite3.Error as e:
                    messagebox.showerror("خطأ في قاعدة البيانات", f"حدث خطأ أثناء حذف السنتر: {e}")
        else:
            messagebox.showwarning("تحديد سنتر", "يرجى تحديد سنتر لحذفه.")

    def add_student(self):
        # Ensure that all fields are filled
        if not all([self.student_name_var.get(), self.student_mobile_var.get(), self.student_center_name.get(),
                    self.student_learning_type.get(), self.parent_mobile_var.get(), self.barcode_var.get(), self.student_grade_var.get()]):  # Added 'student_grade_var'
            messagebox.showwarning("خطأ", "يرجى ملء جميع الحقول.")
            return

        # Validate student type
        learning_type = self.student_learning_type.get()
        if learning_type not in ["علمي", "ادبي"]:
            messagebox.showwarning("خطأ", "يرجى اختيار نوع طالب صحيح (علمي أو ادبي).")
            return

        # Validate barcode uniqueness first
        barcode = self.barcode_var.get().strip()
        if barcode:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM students WHERE barcode = ?", (barcode,))
            existing_student = cursor.fetchone()
            conn.close()
            
            if existing_student:
                messagebox.showerror("خطأ", "الرمز الشريطي موجود بالفعل. يرجى استخدام رمز شريطي مختلف.")
                return

        # Ask for confirmation before saving
        if messagebox.askyesno("تأكيد", "هل أنت متأكد من أنك تريد حفظ هذا الطالب؟"):
            name = self.student_name_var.get()
            mobile = self.student_mobile_var.get()
            center_name = self.student_center_name.get()
            learning_type = self.student_learning_type.get()
            parent_mobile = self.parent_mobile_var.get()
            grade = self.student_grade_var.get()  # Added 'grade'

            # Get center_id from center_name
            center_id = None
            if center_name and hasattr(self, 'centers_list'):
                for cid, cname in self.centers_list:
                    if cname == center_name:
                        center_id = cid
                        break

            if not center_id:
                messagebox.showwarning("خطأ", "يرجى اختيار سنتر صحيح.")
                return

            # Connect to the database and insert the new student
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()

                # Insert query with center_id instead of center_name
                cursor.execute('''INSERT INTO students (name, mobile, center_id, learning_type, parent_mobile, barcode, grade)
                                VALUES (?, ?, ?, ?, ?, ?, ?)''',  # Updated to use center_id
                            (name, mobile, center_id, learning_type, parent_mobile, barcode, grade))

                conn.commit()
                conn.close()

                # Reload the table to show the new student
                self.load_students()
                self.load_filters()  # Refresh the dropdown lists
                messagebox.showinfo("نجاح", "تم إضافة الطالب بنجاح!")
                self.show_add_view()  # Reset the form fields
            except sqlite3.IntegrityError as e:
                if "barcode" in str(e).lower():
                    messagebox.showerror("خطأ", "الرمز الشريطي موجود بالفعل. يرجى استخدام رمز شريطي مختلف.")
                else:
                    messagebox.showerror("خطأ في قاعدة البيانات", f"حدث خطأ أثناء إضافة الطالب: {e}")
            except sqlite3.Error as e:
                messagebox.showerror("خطأ في قاعدة البيانات", f"حدث خطأ أثناء إضافة الطالب: {e}")

    def update_student(self):
        selected_item = self.tree.selection()
        if selected_item:
            # Validate barcode uniqueness first (exclude current student)
            student_id = self.tree.item(selected_item)['values'][0]
            barcode = self.barcode_var.get().strip()
            if barcode:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM students WHERE barcode = ? AND id != ?", (barcode, student_id))
                existing_student = cursor.fetchone()
                conn.close()
                
                if existing_student:
                    messagebox.showerror("خطأ", "الرمز الشريطي موجود بالفعل. يرجى استخدام رمز شريطي مختلف.")
                    return

            if messagebox.askyesno("تأكيد", "هل أنت متأكد من أنك تريد تحديث هذا الطالب؟"):
                name = self.student_name_var.get()
                mobile = self.student_mobile_var.get()
                center_name = self.student_center_name.get()
                learning_type = self.student_learning_type.get()
                parent_mobile = self.parent_mobile_var.get()
                grade = self.student_grade_var.get()  # Added 'grade'

                # Validate student type
                if learning_type not in ["علمي", "ادبي"]:
                    messagebox.showwarning("خطأ", "يرجى اختيار نوع طالب صحيح (علمي أو ادبي).")
                    return

                # Get center_id from center_name
                center_id = None
                if center_name and hasattr(self, 'centers_list'):
                    for cid, cname in self.centers_list:
                        if cname == center_name:
                            center_id = cid
                            break

                if not center_id:
                    messagebox.showwarning("خطأ", "يرجى اختيار سنتر صحيح.")
                    return

                try:
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    cursor.execute('''UPDATE students SET name=?, mobile=?, center_id=?, learning_type=?, parent_mobile=?, barcode=?, grade=?
                        WHERE id=?''',  # Updated to use center_id
                                   (name, mobile, center_id, learning_type, parent_mobile, barcode, grade, student_id))
                    conn.commit()
                    conn.close()

                    self.load_students()  # Reload the table to show updated student
                    self.load_filters()  # Refresh the dropdown lists
                    messagebox.showinfo("نجاح", "تم تحديث الطالب بنجاح!")
                    self.show_add_view()  # Reset the form
                except sqlite3.IntegrityError as e:
                    if "barcode" in str(e).lower():
                        messagebox.showerror("خطأ", "الرمز الشريطي موجود بالفعل. يرجى استخدام رمز شريطي مختلف.")
                    else:
                        messagebox.showerror("خطأ في قاعدة البيانات", f"حدث خطأ أثناء تحديث الطالب: {e}")
                except sqlite3.Error as e:
                    messagebox.showerror("خطأ في قاعدة البيانات", f"حدث خطأ أثناء تحديث الطالب: {e}")
        else:
            messagebox.showwarning("تحديد طالب", "يرجى تحديد طالب لتحديثه.")

    def delete_student(self):
        selected_item = self.tree.selection()
        if selected_item:
            if messagebox.askyesno("تأكيد", "هل أنت متأكد من أنك تريد حذف هذا الطالب؟"):
                student_id = self.tree.item(selected_item)['values'][0]
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM students WHERE id=?", (student_id,))
                conn.commit()
                conn.close()

                self.load_students()  # Reload the table to remove the deleted student
                self.load_filters()  # Refresh the dropdown lists
                messagebox.showinfo("نجاح", "تم حذف الطالب بنجاح!")
        else:
            messagebox.showwarning("تحديد طالب", "يرجى تحديد طالب لحذفه.")

    def edit_marks(self, event):
        # Get the region clicked (to ensure it's the 'Marks' column)
        region = self.attendance_tree.identify("region", event.x, event.y)
        if region == "cell":
            # Get the selected item
            row_id = self.attendance_tree.identify_row(event.y)
            column = self.attendance_tree.identify_column(event.x)

            if column == '#9':  # Marks column is now the 9th column (index starts from 1)
                x, y, width, height = self.attendance_tree.bbox(row_id, column)
                # Create an Entry widget
                entry = ttk.Entry(self.attendance_tree)
                entry.place(x=x, y=y, width=width, height=height)

                # Prepopulate with existing value (if any)
                existing_value = self.attendance_tree.set(row_id, column)
                entry.insert(0, existing_value)

                # Focus and bind the entry to remove it after editing
                entry.focus()
                entry.bind("<Return>", lambda e: self.save_marks(entry, row_id, column))
                entry.bind("<FocusOut>", lambda e: entry.destroy())

    def save_marks(self, entry, row_id, column):
        new_value = entry.get()
        self.attendance_tree.set(row_id, column, new_value)

        # Retrieve the attendance ID to identify the correct record in the database
        attendance_id = self.attendance_tree.item(row_id)['values'][0]  # Use the attendance ID

        # Update the database with the new marks value
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''UPDATE attendance
                        SET marks=?
                        WHERE id=?''', (new_value, attendance_id))  # Update based on attendance ID
        conn.commit()
        conn.close()

        entry.destroy()  # Remove the entry widget after editing

    def delete_attendance(self):
        selected_item = self.attendance_tree.selection()
        if selected_item:
            if messagebox.askyesno("تأكيد", "هل أنت متأكد من أنك تريد حذف هذا السجل؟"):
                # Get the selected row details, with the id being the first value
                attendance_id = self.attendance_tree.item(selected_item)['values'][0]  # The 'id' is in the first column

                # Delete from the database using the attendance id
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute('''DELETE FROM attendance WHERE id = ?''', (attendance_id,))
                conn.commit()
                conn.close()

                # Remove from the Treeview
                self.attendance_tree.delete(selected_item)
                messagebox.showinfo("نجاح", "تم حذف سجل الحضور بنجاح!")
                # Update statistics after deleting attendance
                self.update_attendance_statistics()
        else:
            messagebox.showwarning("تحديد سجل", "يرجى تحديد سجل لحذفه.")


def get_serial_number():
    # Run the command to get the serial number
    command = "wmic bios get serialnumber"
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    
    # Extract the serial number by skipping empty lines
    output_lines = [line.strip() for line in result.stdout.strip().splitlines() if line.strip()]
    if len(output_lines) > 1:
        return output_lines[1]  # The serial number is usually in the second line
    return None


APP_START_DATE = datetime.date(2025, 8, 25)


def get_current_date_from_api():
    url = "https://timeapi.io/api/Time/current/zone"
    params = {"timeZone": "Europe/Amsterdam"}
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # Check for HTTP request errors
        data = response.json()
        return datetime.date(data["year"], data["month"], data["day"])
    except requests.exceptions.RequestException as e:
        messagebox.showerror("Error", f"Could not fetch current date: {e}")
        return None




# def check_authorization():
#     today = get_current_date_from_api()
#     if not today:
#         return False  # Exit if the API call fails
#     delta = today - APP_START_DATE
    
#     if delta.days > 20:
#         messagebox.showerror("Unauthorized", "Expired.")
#         return False
#     else:
#         remaining_days = 20 - delta.days
#         messagebox.showinfo("Authorization Status", f"Remaining days: {remaining_days}")
#         return True

def check_authorization():
    serial_number = get_serial_number()
    #HQTCHV2
    #5CG5501MQC
    if serial_number == "HQTCHV2":
        return True
    else:
        messagebox.showerror("Unauthorized", "You are not authorized to use this application.")
        return False

if __name__ == "__main__":
    # First, check authorization
    if check_authorization():
        create_database()  # Ensure the database is created before starting the app
        root = tk.Tk()
        
        # Show the splash screen
        splash = SplashScreen(root)
        root.withdraw()  # Hide the main window during the splash screen
        splash.update()

        # Wait until the splash screen is closed
        splash.wait_window()

        root.deiconify()  # Show the main window after the splash screen is closed
        app = StudentManagementApp(root)
        root.mainloop()