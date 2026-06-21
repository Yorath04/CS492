import sqlite3


# ==========================================
# SETUP & AUTHENTICATION
# ==========================================
def setup_database():
    conn = sqlite3.connect('school_portal.db')
    cursor = conn.cursor()
    cursor.execute('PRAGMA foreign_keys = ON')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Teachers (
            teacher_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Logins (
            login_id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_id INTEGER,
            password TEXT NOT NULL,
            user_level TEXT NOT NULL,
            force_pw_change INTEGER DEFAULT 1,
            FOREIGN KEY (teacher_id) REFERENCES Teachers (teacher_id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Students (
            student_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            grade_level INTEGER NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Classes (
            class_id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_name TEXT NOT NULL,
            teacher_id INTEGER,
            FOREIGN KEY (teacher_id) REFERENCES Teachers (teacher_id) ON DELETE SET NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Rosters (
            roster_id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_id INTEGER,
            student_id INTEGER,
            FOREIGN KEY (class_id) REFERENCES Classes (class_id) ON DELETE CASCADE,
            FOREIGN KEY (student_id) REFERENCES Students (student_id) ON DELETE CASCADE,
            UNIQUE(class_id, student_id)
        )
    ''')

    cursor.execute("SELECT * FROM Teachers WHERE teacher_id = 1")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO Teachers (teacher_id, name) VALUES (1, 'Admin')")
        cursor.execute(
            "INSERT INTO Logins (teacher_id, password, user_level, force_pw_change) VALUES (1, 'admin', 'Admin', 1)")
        conn.commit()

    return conn


def verify_login(conn, teacher_id, password):
    cursor = conn.cursor()
    cursor.execute('''
        SELECT Logins.user_level, Logins.force_pw_change, Teachers.name 
        FROM Logins 
        JOIN Teachers ON Logins.teacher_id = Teachers.teacher_id
        WHERE Logins.teacher_id = ? AND Logins.password = ?
    ''', (teacher_id, password))
    result = cursor.fetchone()
    if result:
        return {
            'teacher_id': teacher_id,
            'name': result[2],
            'user_level': result[0],
            'force_pw_change': result[1]
        }
    return None


def update_password(conn, teacher_id, current_pw, new_pw):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Logins WHERE teacher_id = ? AND password = ?", (teacher_id, current_pw))
    if cursor.fetchone():
        cursor.execute("UPDATE Logins SET password = ?, force_pw_change = 0 WHERE teacher_id = ?", (new_pw, teacher_id))
        conn.commit()
        return True
    return False


# ==========================================
# CREATION FUNCTIONS
# ==========================================
def add_new_teacher(conn, name):
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO Teachers (name) VALUES (?)", (name,))
        new_teacher_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO Logins (teacher_id, password, user_level, force_pw_change) VALUES (?, 'welcome', 'User', 1)",
            (new_teacher_id,))
        conn.commit()
        return new_teacher_id
    except sqlite3.Error:
        conn.rollback()
        return False


def add_new_student(conn, name, grade_level):
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO Students (name, grade_level) VALUES (?, ?)", (name, grade_level))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error:
        conn.rollback()
        return False


def add_new_class(conn, class_name):
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO Classes (class_name) VALUES (?)", (class_name,))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error:
        conn.rollback()
        return False


# ==========================================
# READ FUNCTIONS
# ==========================================
def get_user_level(conn, teacher_id):
    cursor = conn.cursor()
    cursor.execute("SELECT user_level FROM Logins WHERE teacher_id = ?", (teacher_id,))
    result = cursor.fetchone()
    return result[0] if result else None


def get_teacher_list(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT teacher_id, name FROM Teachers WHERE teacher_id != 1 ORDER BY name")
    return cursor.fetchall()


def get_student_list(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT student_id, name, grade_level FROM Students ORDER BY name")
    return cursor.fetchall()


def get_class_list(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT class_id, class_name FROM Classes ORDER BY class_name")
    return cursor.fetchall()


def get_teacher_classes(conn, teacher_id):
    cursor = conn.cursor()
    cursor.execute("SELECT class_id, class_name FROM Classes WHERE teacher_id = ?", (teacher_id,))
    return cursor.fetchall()


def get_class_students(conn, class_id):
    cursor = conn.cursor()
    cursor.execute('''
        SELECT s.student_id, s.name, s.grade_level 
        FROM Students s
        JOIN Rosters r ON s.student_id = r.student_id
        WHERE r.class_id = ?
    ''', (class_id,))
    return cursor.fetchall()


def get_student_classes(conn, student_id):
    cursor = conn.cursor()
    cursor.execute('''
        SELECT c.class_id, c.class_name 
        FROM Classes c
        JOIN Rosters r ON c.class_id = r.class_id
        WHERE r.student_id = ?
    ''', (student_id,))
    return cursor.fetchall()


def get_class_teacher(conn, class_id):
    cursor = conn.cursor()
    cursor.execute('''
        SELECT t.teacher_id, t.name 
        FROM Teachers t
        JOIN Classes c ON t.teacher_id = c.teacher_id
        WHERE c.class_id = ?
    ''', (class_id,))
    return cursor.fetchone()


# ==========================================
# UPDATE & ASSIGNMENT FUNCTIONS
# ==========================================
def admin_reset_password(conn, target_id, new_temp_password, requester_id):
    """Resets password, enforcing strict hierarchical RBAC."""
    if target_id == 1:
        return False

    cursor = conn.cursor()
    cursor.execute("SELECT user_level FROM Logins WHERE teacher_id = ?", (target_id,))
    target_res = cursor.fetchone()
    if not target_res: return False
    target_level = target_res[0]

    cursor.execute("SELECT user_level FROM Logins WHERE teacher_id = ?", (requester_id,))
    req_res = cursor.fetchone()
    if not req_res: return False
    req_level = req_res[0]

    # NEW SECURITY RULES
    if req_level == 'Super_User':
        if target_level in ['Super_User', 'Admin']: return False
    elif req_level == 'Admin' and requester_id != 1:
        if target_level == 'Admin': return False

    try:
        cursor.execute("UPDATE Logins SET password = ?, force_pw_change = 1 WHERE teacher_id = ?",
                       (new_temp_password, target_id))
        if cursor.rowcount == 0: return False
        conn.commit()
        return True
    except sqlite3.Error:
        conn.rollback()
        return False


def update_user_level(conn, target_id, new_level, requester_id):
    """Updates user levels, enforcing strict hierarchical RBAC."""
    if target_id == 1:
        return False
    if new_level not in ['Admin', 'Super_User', 'User']:
        return False

    cursor = conn.cursor()
    cursor.execute("SELECT user_level FROM Logins WHERE teacher_id = ?", (target_id,))
    target_res = cursor.fetchone()
    if not target_res: return False
    target_level = target_res[0]

    cursor.execute("SELECT user_level FROM Logins WHERE teacher_id = ?", (requester_id,))
    req_res = cursor.fetchone()
    if not req_res: return False
    req_level = req_res[0]

    # NEW SECURITY RULES
    if req_level == 'Super_User':
        if target_level in ['Super_User', 'Admin']: return False
    elif req_level == 'Admin' and requester_id != 1:
        if target_level == 'Admin': return False

    try:
        cursor.execute("UPDATE Logins SET user_level = ? WHERE teacher_id = ?", (new_level, target_id))
        if cursor.rowcount == 0: return False
        conn.commit()
        return True
    except sqlite3.Error:
        conn.rollback()
        return False


def update_teacher_name(conn, teacher_id, new_name):
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE Teachers SET name = ? WHERE teacher_id = ?", (new_name, teacher_id))
        conn.commit()
        return True
    except sqlite3.Error:
        conn.rollback()
        return False


def update_student(conn, student_id, new_name, new_grade):
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE Students SET name = ?, grade_level = ? WHERE student_id = ?",
                       (new_name, new_grade, student_id))
        conn.commit()
        return True
    except sqlite3.Error:
        conn.rollback()
        return False


def update_class_name(conn, class_id, new_name):
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE Classes SET class_name = ? WHERE class_id = ?", (new_name, class_id))
        conn.commit()
        return True
    except sqlite3.Error:
        conn.rollback()
        return False


def assign_teacher_to_class(conn, class_id, teacher_id):
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE Classes SET teacher_id = ? WHERE class_id = ?", (teacher_id, class_id))
        conn.commit()
        return True
    except sqlite3.Error:
        conn.rollback()
        return False


def add_student_to_class(conn, class_id, student_id):
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO Rosters (class_id, student_id) VALUES (?, ?)", (class_id, student_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def remove_student_from_class(conn, class_id, student_id):
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM Rosters WHERE class_id = ? AND student_id = ?", (class_id, student_id))
        conn.commit()
        return True
    except sqlite3.Error:
        return False


def remove_teacher_from_class(conn, class_id):
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE Classes SET teacher_id = NULL WHERE class_id = ?", (class_id,))
        conn.commit()
        return True
    except sqlite3.Error:
        return False


# ==========================================
# DELETE FUNCTIONS
# ==========================================
def delete_teacher(conn, teacher_id):
    if teacher_id == 1: return False
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE Classes SET teacher_id = NULL WHERE teacher_id = ?", (teacher_id,))
        cursor.execute("DELETE FROM Logins WHERE teacher_id = ?", (teacher_id,))
        cursor.execute("DELETE FROM Teachers WHERE teacher_id = ?", (teacher_id,))
        conn.commit()
        return True
    except sqlite3.Error:
        conn.rollback()
        return False


def delete_student(conn, student_id):
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM Rosters WHERE student_id = ?", (student_id,))
        cursor.execute("DELETE FROM Students WHERE student_id = ?", (student_id,))
        conn.commit()
        return True
    except sqlite3.Error:
        conn.rollback()
        return False


def delete_class(conn, class_id):
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM Rosters WHERE class_id = ?", (class_id,))
        cursor.execute("DELETE FROM Classes WHERE class_id = ?", (class_id,))
        conn.commit()
        return True
    except sqlite3.Error:
        conn.rollback()
        return False