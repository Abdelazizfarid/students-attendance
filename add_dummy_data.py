import sqlite3
import os
import random
import string
import datetime

# Get the directory where the script is running
app_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(app_dir, 'students.db')

# Arabic names for students
arabic_names = [
    "أحمد محمد", "فاطمة علي", "علي حسن", "مريم أحمد", "محمد عبدالله",
    "خديجة محمد", "عبدالله علي", "عائشة محمد", "حسن علي", "زينب أحمد",
    "يوسف محمد", "نور الهدى", "إبراهيم علي", "رنا محمد", "عمر أحمد",
    "سارة محمد", "عبدالرحمن علي", "ليلى محمد", "محمد حسن", "فاطمة علي",
    "أحمد علي", "مريم محمد", "علي أحمد", "خديجة علي", "محمد حسن",
    "عائشة علي", "حسن محمد", "زينب علي", "يوسف علي", "نور الهدى محمد",
    "إبراهيم محمد", "رنا علي", "عمر محمد", "سارة علي", "عبدالرحمن محمد",
    "ليلى علي", "محمد أحمد", "فاطمة محمد", "أحمد حسن", "مريم علي",
    "علي محمد", "خديجة أحمد", "محمد علي", "عائشة أحمد", "حسن علي",
    "زينب محمد", "يوسف أحمد", "نور الهدى علي", "إبراهيم أحمد", "رنا محمد"
]

# Center names
centers = [
    "مركز النور التعليمي", "معهد الإبداع", "أكاديمية التميز", "مركز المعرفة",
    "معهد النجاح", "أكاديمية التفوق", "مركز التعلم الذكي", "معهد التطوير"
]

# Learning types (already defined in the app)
learning_types = ["علمي", "ادبي"]

# Grades
grades = ["الصف الأول", "الصف الثاني", "الصف الثالث", "الصف الرابع", "الصف الخامس", "الصف السادس"]

def generate_mobile():
    """Generate a realistic Egyptian mobile number"""
    prefixes = ["010", "011", "012", "015"]
    prefix = random.choice(prefixes)
    number = ''.join(random.choices(string.digits, k=8))
    return f"{prefix}{number}"

def generate_barcode():
    """Generate a unique 10-character barcode"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

def add_dummy_data():
    """Add 50 dummy student records"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # First, ensure we have centers
        print("Checking/creating centers...")
        for center_name in centers:
            cursor.execute("INSERT OR IGNORE INTO centers (name, created_date) VALUES (?, ?)",
                         (center_name, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        
        # Get center IDs
        cursor.execute("SELECT id FROM centers")
        center_ids = [row[0] for row in cursor.fetchall()]
        
        if not center_ids:
            print("Error: No centers found. Please create centers first.")
            return
        
        print(f"Found {len(center_ids)} centers")
        
        # Check if students table exists
        cursor.execute("PRAGMA table_info(students)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if not columns:
            print("Error: Students table not found. Please run the main application first.")
            return
        
        # Generate and insert 50 students
        print("Adding 50 dummy students...")
        
        for i in range(50):
            # Generate unique data
            name = random.choice(arabic_names)
            mobile = generate_mobile()
            center_id = random.choice(center_ids)
            learning_type = random.choice(learning_types)
            parent_mobile = generate_mobile()
            barcode = generate_barcode()
            grade = random.choice(grades)
            
            # Insert student
            cursor.execute('''INSERT INTO students (name, mobile, center_id, learning_type, parent_mobile, barcode, grade)
                            VALUES (?, ?, ?, ?, ?, ?, ?)''',
                         (name, mobile, center_id, learning_type, parent_mobile, barcode, grade))
            
            if (i + 1) % 10 == 0:
                print(f"Added {i + 1} students...")
        
        # Commit changes
        conn.commit()
        print(f"Successfully added 50 dummy students!")
        
        # Show summary
        cursor.execute("SELECT COUNT(*) FROM students")
        total_students = cursor.fetchone()[0]
        print(f"Total students in database: {total_students}")
        
        # Show distribution by learning type
        cursor.execute("SELECT learning_type, COUNT(*) FROM students GROUP BY learning_type")
        type_distribution = cursor.fetchall()
        print("\nDistribution by learning type:")
        for learning_type, count in type_distribution:
            print(f"  {learning_type}: {count} students")
        
        # Show distribution by center
        cursor.execute("""
            SELECT centers.name, COUNT(*) 
            FROM students 
            JOIN centers ON students.center_id = centers.id 
            GROUP BY centers.name
        """)
        center_distribution = cursor.fetchall()
        print("\nDistribution by center:")
        for center_name, count in center_distribution:
            print(f"  {center_name}: {count} students")
            
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        conn.rollback()
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    print("Student Attendance Management System - Dummy Data Generator")
    print("=" * 60)
    
    if not os.path.exists(db_path):
        print(f"Error: Database file not found at {db_path}")
        print("Please run the main application first to create the database.")
    else:
        add_dummy_data()
    
    print("\nPress Enter to exit...")
    input()
