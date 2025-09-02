import sqlite3
import os
import random
import datetime
from datetime import date, timedelta

# Get the directory where the script is running
app_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(app_dir, 'students.db')

def add_attendance_data():
    """Add dummy attendance data for month 8 (August)"""
    
    # Check if database exists
    if not os.path.exists(db_path):
        print("Database not found. Please run the main application first to create the database.")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Get all student IDs
        cursor.execute("SELECT id FROM students")
        student_ids = [row[0] for row in cursor.fetchall()]
        
        if not student_ids:
            print("No students found in the database. Please add students first.")
            return
        
        # Define August dates (month 8)
        august_start = date(2024, 8, 1)
        august_end = date(2024, 8, 31)
        
        # Generate dates for August (excluding weekends for more realistic data)
        august_dates = []
        current_date = august_start
        while current_date <= august_end:
            # Skip weekends (Saturday = 5, Sunday = 6)
            if current_date.weekday() < 5:  # Monday to Friday
                august_dates.append(current_date.strftime("%Y-%m-%d"))
            current_date += timedelta(days=1)
        
        print(f"Generated {len(august_dates)} working days in August")
        
        # Generate attendance records
        attendance_records = []
        
        # Distribute attendance across different patterns
        for student_id in student_ids:
            # Each student will have different attendance patterns
            attendance_probability = random.uniform(0.6, 0.95)  # 60-95% attendance rate
            
            for date_str in august_dates:
                # Randomly decide if student attended based on probability
                if random.random() < attendance_probability:
                    # Generate random marks (0-100)
                    marks = random.randint(0, 100)
                    attendance_records.append((student_id, date_str, marks))
                    
                    # Occasionally skip some days (simulating absences)
                    if random.random() < 0.1:  # 10% chance to skip next day
                        continue
        
        # Shuffle records to make them more random
        random.shuffle(attendance_records)
        
        # Limit to around 100 records
        if len(attendance_records) > 100:
            attendance_records = random.sample(attendance_records, 100)
        
        # Insert attendance records
        cursor.executemany(
            "INSERT INTO attendance (student_id, date, marks) VALUES (?, ?, ?)",
            attendance_records
        )
        
        conn.commit()
        
        # Get statistics
        cursor.execute("SELECT COUNT(*) FROM attendance")
        total_attendance = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT student_id) FROM attendance")
        students_with_attendance = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT date) FROM attendance")
        unique_dates = cursor.fetchone()[0]
        
        print(f"✅ Successfully added {len(attendance_records)} attendance records!")
        print(f"📊 Total attendance records in database: {total_attendance}")
        print(f"👥 Students with attendance records: {students_with_attendance}")
        print(f"📅 Unique dates covered: {unique_dates}")
        print(f"📈 Average attendance per student: {len(attendance_records) / len(student_ids):.1f}")
        
        # Show distribution by date
        print("\n📅 Attendance distribution by date:")
        cursor.execute("""
            SELECT date, COUNT(*) as count 
            FROM attendance 
            GROUP BY date 
            ORDER BY date
        """)
        date_distribution = cursor.fetchall()
        
        for date_str, count in date_distribution:
            print(f"   {date_str}: {count} students")
        
        # Show distribution by student
        print("\n👥 Top 5 students by attendance:")
        cursor.execute("""
            SELECT s.name, COUNT(a.id) as attendance_count
            FROM students s
            JOIN attendance a ON s.id = a.student_id
            GROUP BY s.id, s.name
            ORDER BY attendance_count DESC
            LIMIT 5
        """)
        top_students = cursor.fetchall()
        
        for name, count in top_students:
            print(f"   {name}: {count} days")
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        conn.rollback()
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    print("🎯 Adding dummy attendance data for August 2024...")
    add_attendance_data()
    print("\n✨ Script completed!")
