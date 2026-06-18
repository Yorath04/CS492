import sqlite3
import os

DB_FILE = 'school_portal.db'


# ==========================================
# DATABASE INITIALIZATION
# ==========================================

def setup_database():
    """Connects to the database and creates tables if they don't exist."""
    is_new_db = not os.path.exists(DB_FILE)

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Enable foreign key support for cascading deletes/updates
    cursor.execute('PRAGMA foreign_keys = ON')

    if is_new_db:
        print("Initializing new database...")

        # 1. Teachers Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Teachers (
                teacher_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL
            )
        ''')

        # 2. Logins Table (Updated with Super_User and force_pw_change)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Logins (
                teacher_id INTEGER PRIMARY KEY,
                password TEXT NOT NULL,
                user_level TEXT CHECK(user_level IN ('Admin', 'Super_User', 'User')) NOT NULL,
                force_pw_change INTEGER DEFAULT 1,
                FOREIGN KEY(teacher_id) REFERENCES Teachers(teacher_id) ON DELETE CASCADE
            )
        ''')

        # 3. Classes Table (Many-to-1 relationship with Teachers)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Classes (
                class_id INTEGER PRIMARY KEY AUTOINCREMENT,
                class_name TEXT NOT NULL,
                teacher_id INTEGER,
                FOREIGN KEY(teacher_id) REFERENCES Teachers(teacher_id) ON DELETE SET NULL
            )
        ''')

        # 4. Students Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Students (
                student_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                grade_level INTEGER NOT NULL
            )
        ''')

        # 5. Rosters Table (Many-to-Many relationship)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Rosters (
                class_id INTEGER,
                student_id INTEGER,
                PRIMARY KEY (class_id, student_id),
                FOREIGN KEY(class_id) REFERENCES Classes(class_id) ON DELETE CASCADE,
                FOREIGN KEY(student_id) REFERENCES Students(student_id) ON DELETE CASCADE
            )
        ''')

        # Create the Base Admin Profile
        cursor.execute("INSERT INTO Teachers (name) VALUES ('Base Admin')")
        admin_id = cursor.lastrowid

        cursor.execute('''
            INSERT INTO Logins (teacher_id, password, user_level, force_pw_change) 
            VALUES (?, ?, ?, ?)
        ''', (admin_id, 'Admin', 'Admin', 0))

        conn.commit()
        print("Database built and Base Admin created successfully.")
    else:
        print("Database already exists. Waiting for frontend input...")

    return conn


# ==========================================
# CREATE FUNCTIONS (Adding Data)
# ==========================================

def add_new_teacher(conn, name, user_level="User"):
    """Adds a new teacher and creates their Login profile with default password."""
    cursor = conn.cursor()
    default_password = "password"
    try:
        cursor.execute("INSERT INTO Teachers (name) VALUES (?)", (name,))
        new_teacher_id = cursor.lastrowid

        cursor.execute('''
            INSERT INTO Logins (teacher_id, password, user_level) 
            VALUES (?, ?, ?)
        ''', (new_teacher_id, default_password, user_level))

        conn.commit()
        print(f"Success: Teacher '{name}' added with ID {new_teacher_id}.")
        return new_teacher_id
    except sqlite3.Error as e:
        print(f"An error occurred while adding the teacher: {e}")
        conn.rollback()


def add_new_class(conn, class_name):
    """Creates a new class with no teacher assigned yet."""
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO Classes (class_name) VALUES (?)", (class_name,))
        new_class_id = cursor.lastrowid
        conn.commit()
        print(f"Success: Class '{class_name}' added with ID {new_class_id}.")
        return new_class_id
    except sqlite3.Error as e:
        print(f"An error occurred while adding the class: {e}")
        conn.rollback()


def add_new_student(conn, student_name, grade_level):
    """Adds a new student to the database."""
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO Students (name, grade_level) VALUES (?, ?)", (student_name, grade_level))
        new_student_id = cursor.lastrowid
        conn.commit()
        print(f"Success: Student '{student_name}' added with ID {new_student_id}.")
        return new_student_id
    except sqlite3.Error as e:
        print(f"An error occurred while adding the student: {e}")
        conn.rollback()


def assign_teacher_to_class(conn, class_id, teacher_id):
    """Assigns an existing teacher to an existing class."""
    cursor = conn.cursor()
    cursor.execute("UPDATE Classes SET teacher_id = ? WHERE class_id = ?", (teacher_id, class_id))
    conn.commit()
    print(f"Teacher {teacher_id} assigned to Class {class_id}.")


def add_student_to_class(conn, class_id, student_id):
    """Adds a student to a class roster."""
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO Rosters (class_id, student_id) VALUES (?, ?)", (class_id, student_id))
        conn.commit()
        print(f"Student {student_id} added to Class {class_id}.")
    except sqlite3.IntegrityError:
        print("Error: Student is already in this class or ID doesn't exist.")


# ==========================================
# READ FUNCTIONS (Retrieving Data)
# ==========================================

def verify_login(conn, teacher_id, password):
    """Checks credentials and returns session data if successful."""
    cursor = conn.cursor()
    cursor.execute('''
        SELECT Teachers.name, Logins.user_level, Logins.force_pw_change 
        FROM Logins 
        JOIN Teachers ON Logins.teacher_id = Teachers.teacher_id
        WHERE Logins.teacher_id = ? AND Logins.password = ?
    ''', (teacher_id, password))

    result = cursor.fetchone()
    if result:
        print(f"Login successful for {result[0]}.")
        return {
            "teacher_id": teacher_id,
            "name": result[0],
            "user_level": result[1],
            "force_pw_change": bool(result[2])
        }
    else:
        print("Login failed: Invalid ID or password.")
        return None


def get_all_teachers_with_classes(conn):
    """Returns a list of all teachers and a string of their classes."""
    cursor = conn.cursor()
    cursor.execute('''
        SELECT Teachers.teacher_id, Teachers.name, 
               GROUP_CONCAT(Classes.class_name, ', ') AS class_list
        FROM Teachers
        LEFT JOIN Classes ON Teachers.teacher_id = Classes.teacher_id
        GROUP BY Teachers.teacher_id
    ''')
    teachers = cursor.fetchall()
    return teachers


def get_all_students_with_classes(conn):
    """Returns a list of all students and a string of their enrolled classes."""
    cursor = conn.cursor()
    cursor.execute('''
        SELECT Students.student_id, Students.name, Students.grade_level,
               GROUP_CONCAT(Classes.class_name, ', ') AS enrolled_classes
        FROM Students
        LEFT JOIN Rosters ON Students.student_id = Rosters.student_id
        LEFT JOIN Classes ON Rosters.class_id = Classes.class_id
        GROUP BY Students.student_id
    ''')
    students = cursor.fetchall()
    return students


def get_teacher_homepage_data(conn, teacher_id):
    """Returns a dictionary of a teacher's classes and their student rosters."""
    cursor = conn.cursor()
    homepage_data = {}

    cursor.execute("SELECT class_id, class_name FROM Classes WHERE teacher_id = ?", (teacher_id,))
    classes = cursor.fetchall()

    if not classes:
        return homepage_data

    for class_id, class_name in classes:
        cursor.execute('''
            SELECT Students.name 
            FROM Rosters
            JOIN Students ON Rosters.student_id = Students.student_id
            WHERE Rosters.class_id = ?
        ''', (class_id,))
        students = [row[0] for row in cursor.fetchall()]
        homepage_data[class_name] = students

    return homepage_data


def search_students(conn, search_term):
    """
    Searches for a student by ID (exact match) or Name (partial match).
    Returns a list of matching students and their enrolled classes.
    """
    cursor = conn.cursor()

    # Prepare the search string for the LIKE clause
    # Adding % on both sides means "find this text anywhere in the name"
    like_term = f"%{search_term}%"

    # We use a LEFT JOIN just like the global directory to ensure students
    # with zero classes still show up in the search results.
    cursor.execute('''
        SELECT Students.student_id, Students.name, Students.grade_level,
               GROUP_CONCAT(Classes.class_name, ', ') AS enrolled_classes
        FROM Students
        LEFT JOIN Rosters ON Students.student_id = Rosters.student_id
        LEFT JOIN Classes ON Rosters.class_id = Classes.class_id
        WHERE Students.student_id = ? OR Students.name LIKE ?
        GROUP BY Students.student_id
    ''', (search_term, like_term))

    results = cursor.fetchall()

    # Handle the feedback safely
    if not results:
        print(f"No students found matching '{search_term}'.")
        return []  # Return an empty list so the frontend knows there are no results

    print(f"\n--- Search Results for '{search_term}' ---")
    for s_id, name, grade, classes in results:
        class_display = classes if classes else "Not enrolled in any classes"
        print(f"ID: {s_id} | Name: {name} | Grade: {grade} | Classes: {class_display}")

    return results
# ==========================================
# UPDATE FUNCTIONS (Modifying Data)
# ==========================================

def admin_reset_password(conn, teacher_id, new_temp_password):
    """Admin function to reset password and force a change on next login."""
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE Logins SET password = ?, force_pw_change = 1 WHERE teacher_id = ?",
                       (new_temp_password, teacher_id))
        if cursor.rowcount == 0:
            print(f"Error: Teacher ID {teacher_id} not found.")
        else:
            conn.commit()
            print(f"Success: Password reset for Teacher {teacher_id}.")
    except sqlite3.Error as e:
        print(f"Error during password reset: {e}")
        conn.rollback()


def update_user_level(conn, teacher_id, new_level):
    """Admin function to change a teacher's user level."""
    if new_level not in ['Admin', 'Super_User', 'User']:
        print("Error: Invalid user level.")
        return
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE Logins SET user_level = ? WHERE teacher_id = ?", (new_level, teacher_id))
        if cursor.rowcount == 0:
            print(f"Error: Teacher ID {teacher_id} not found.")
        else:
            conn.commit()
            print(f"Success: Teacher {teacher_id} level updated to {new_level}.")
    except sqlite3.Error as e:
        print(f"Error updating user level: {e}")
        conn.rollback()


def remove_teacher_from_class(conn, class_id):
    """Unassigns a teacher from a class by setting teacher_id to NULL."""
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE Classes SET teacher_id = NULL WHERE class_id = ?", (class_id,))
        if cursor.rowcount == 0:
            print(f"Error: Class ID {class_id} not found.")
        else:
            conn.commit()
            print(f"Success: Teacher removed from Class {class_id}.")
    except sqlite3.Error as e:
        print(f"Error unassigning teacher: {e}")
        conn.rollback()


# ==========================================
# DELETE FUNCTIONS (Removing Data)
# ==========================================

def delete_teacher(conn, teacher_id):
    """Deletes teacher. Cascades to Logins, sets NULL in Classes."""
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM Teachers WHERE teacher_id = ?", (teacher_id,))
        if cursor.rowcount == 0:
            print(f"Error: Teacher ID {teacher_id} not found.")
        else:
            conn.commit()
            print(f"Success: Teacher {teacher_id} deleted.")
    except sqlite3.Error as e:
        print(f"Error deleting teacher: {e}")
        conn.rollback()


def delete_class(conn, class_id):
    """Deletes class. Cascades to Rosters."""
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM Classes WHERE class_id = ?", (class_id,))
        if cursor.rowcount == 0:
            print(f"Error: Class ID {class_id} not found.")
        else:
            conn.commit()
            print(f"Success: Class {class_id} deleted.")
    except sqlite3.Error as e:
        print(f"Error deleting class: {e}")
        conn.rollback()


def delete_student(conn, student_id):
    """Deletes student. Cascades to Rosters."""
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM Students WHERE student_id = ?", (student_id,))
        if cursor.rowcount == 0:
            print(f"Error: Student ID {student_id} not found.")
        else:
            conn.commit()
            print(f"Success: Student {student_id} deleted.")
    except sqlite3.Error as e:
        print(f"Error deleting student: {e}")
        conn.rollback()


def remove_student_from_class(conn, class_id, student_id):
    """Removes a specific student from a specific class roster."""
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM Rosters WHERE class_id = ? AND student_id = ?", (class_id, student_id))
        if cursor.rowcount == 0:
            print(f"Notice: Student {student_id} not in Class {class_id}.")
        else:
            conn.commit()
            print(f"Success: Student {student_id} removed from Class {class_id}.")
    except sqlite3.Error as e:
        print(f"Error modifying roster: {e}")
        conn.rollback()


# ==========================================
# MAIN EXECUTION
# ==========================================

if __name__ == '__main__':
    # Initialize the database and get the connection
    db_connection = setup_database()

    # You can test your functions here by calling them, for example:
    # new_teacher = add_new_teacher(db_connection, "Mr. Smith", "User")
    # print(get_all_teachers_with_classes(db_connection))