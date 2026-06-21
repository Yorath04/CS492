import tkinter as tk
from tkinter import ttk, messagebox
import backend


class SchoolPortalApp:
    def __init__(self, root):
        self.root = root
        self.root.title("School Information Management System")
        self.root.geometry("400x300")

        self.db_conn = backend.setup_database()
        self.session_data = None

        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(expand=True, fill='both')

        self.create_login_screen()

    def clear_screen(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()

    # ==========================================
    # LOGIN SCREEN
    # ==========================================
    def create_login_screen(self):
        self.clear_screen()
        self.root.geometry("400x300")

        tk.Label(self.main_frame, text="Portal Login", font=("Arial", 20, "bold")).pack(pady=20)

        id_frame = tk.Frame(self.main_frame)
        id_frame.pack(pady=10)
        tk.Label(id_frame, text="Employee ID:", width=12, anchor="e").pack(side=tk.LEFT)
        self.id_entry = tk.Entry(id_frame)
        self.id_entry.pack(side=tk.LEFT, padx=5)

        pw_frame = tk.Frame(self.main_frame)
        pw_frame.pack(pady=10)
        tk.Label(pw_frame, text="Password:", width=12, anchor="e").pack(side=tk.LEFT)
        self.pw_entry = tk.Entry(pw_frame, show="*")
        self.pw_entry.pack(side=tk.LEFT, padx=5)

        tk.Button(self.main_frame, text="Login", command=self.handle_login, width=15).pack(pady=20)

    def handle_login(self):
        user_id_text = self.id_entry.get()
        password = self.pw_entry.get()

        try:
            teacher_id = int(user_id_text)
        except ValueError:
            messagebox.showerror("Login Failed", "Employee ID must be a number.")
            return

        self.session_data = backend.verify_login(self.db_conn, teacher_id, password)

        if self.session_data:
            if self.session_data.get('force_pw_change') == 1:
                self.popup_mandatory_password_change(teacher_id)
            else:
                self.create_main_dashboard()
        else:
            messagebox.showerror("Login Failed", "Invalid Employee ID or Password.")

    def popup_mandatory_password_change(self, teacher_id):
        popup = tk.Toplevel(self.root)
        popup.title("Mandatory Password Change")
        popup.geometry("350x300")
        popup.grab_set()

        def on_close():
            self.session_data = None
            popup.destroy()
            messagebox.showwarning("Login Cancelled", "You must change your password to proceed.")

        popup.protocol("WM_DELETE_WINDOW", on_close)

        tk.Label(popup, text="Your password has been reset.\nPlease choose a new password.",
                 font=("Arial", 10, "bold")).pack(pady=10)
        tk.Label(popup, text="Current Temp Password:").pack()
        current_pw_entry = tk.Entry(popup, show="*")
        current_pw_entry.pack(pady=5)
        tk.Label(popup, text="New Password:").pack()
        new_pw_entry = tk.Entry(popup, show="*")
        new_pw_entry.pack(pady=5)
        tk.Label(popup, text="Confirm New Password:").pack()
        confirm_pw_entry = tk.Entry(popup, show="*")
        confirm_pw_entry.pack(pady=5)

        def submit():
            current_pw = current_pw_entry.get()
            new_pw = new_pw_entry.get()
            confirm_pw = confirm_pw_entry.get()

            if not current_pw or not new_pw or not confirm_pw:
                messagebox.showwarning("Input Error", "All fields are required.", parent=popup)
                return
            if new_pw != confirm_pw:
                messagebox.showwarning("Input Error", "New passwords do not match.", parent=popup)
                return

            success = backend.update_password(self.db_conn, teacher_id, current_pw, new_pw)
            if success:
                messagebox.showinfo("Success", "Password successfully updated!", parent=popup)
                self.session_data['force_pw_change'] = 0
                popup.destroy()
                self.create_main_dashboard()
            else:
                messagebox.showerror("Update Failed", "Current password is incorrect.", parent=popup)

        tk.Button(popup, text="Update Password", command=submit).pack(pady=15)

    # ==========================================
    # MAIN DASHBOARD
    # ==========================================
    def create_main_dashboard(self):
        self.clear_screen()
        self.root.geometry("850x650")

        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(expand=True, fill='both', padx=10, pady=10)

        # Tab 0: Home (Hierarchical Treeview)
        tab_home = ttk.Frame(self.notebook)
        self.notebook.add(tab_home, text="Home")
        self.build_home_tab(tab_home)

        # Search Tabs
        tab_student = ttk.Frame(self.notebook)
        self.notebook.add(tab_student, text="Student Search")
        self.build_student_search_tab(tab_student)

        tab_teacher = ttk.Frame(self.notebook)
        self.notebook.add(tab_teacher, text="Teacher Search")
        self.build_teacher_search_tab(tab_teacher)

        tab_class = ttk.Frame(self.notebook)
        self.notebook.add(tab_class, text="Class Search")
        self.build_class_search_tab(tab_class)

        # RBAC: Tab 4 & Profile Tabs
        user_level = self.session_data['user_level']
        if user_level in ['Admin', 'Super_User']:
            tab_admin = ttk.Frame(self.notebook)
            self.notebook.add(tab_admin, text="Admin Tasks")
            self.build_admin_tab(tab_admin)

        if self.session_data['teacher_id'] == 1:
            tab_profile = ttk.Frame(self.notebook)
            self.notebook.add(tab_profile, text="Security")
            self.build_base_admin_tab(tab_profile)
        else:
            tab_profile = ttk.Frame(self.notebook)
            self.notebook.add(tab_profile, text="Profile")
            self.build_profile_tab(tab_profile)

        tk.Button(self.main_frame, text="Logout", command=self.create_login_screen, width=15).pack(pady=10)

    # ==========================================
    # TAB 0: HOME PAGE
    # ==========================================
    def build_home_tab(self, parent_frame):
        user_level = self.session_data['user_level']
        welcome_name = self.session_data['name']

        header_text = f"{user_level} Dashboard\nWelcome, {welcome_name}"
        color = "red" if user_level == "Admin" else "black"
        tk.Label(parent_frame, text=header_text, font=("Arial", 20, "bold"), fg=color).pack(pady=20)

        tk.Label(parent_frame, text="My Assigned Classes & Rosters:", font=("Arial", 14, "underline")).pack(pady=5,
                                                                                                            anchor="w",
                                                                                                            padx=20)

        columns = ("grade",)
        self.home_tree = ttk.Treeview(parent_frame, columns=columns, show="tree headings", selectmode="none")
        self.home_tree.heading("#0", text="Classes & Students")
        self.home_tree.heading("grade", text="Grade Level")
        self.home_tree.column("#0", width=400)
        self.home_tree.column("grade", width=100, anchor="center")
        self.home_tree.pack(expand=True, fill='both', padx=20, pady=10)

        t_id = self.session_data['teacher_id']
        classes = backend.get_teacher_classes(self.db_conn, t_id)

        if not classes:
            self.home_tree.insert("", "end", text="You are not assigned to any classes.")
        else:
            for c in classes:
                c_id, c_name = c[0], c[1]
                # Open=True automatically expands the folders
                class_node = self.home_tree.insert("", "end", text=f"📂 {c_name} (Class ID: {c_id})", open=True,
                                                   tags=("class_row",))

                students = backend.get_class_students(self.db_conn, c_id)
                if not students:
                    self.home_tree.insert(class_node, "end", text="   └─ (No students enrolled)")
                else:
                    for s in students:
                        self.home_tree.insert(class_node, "end", text=f"   ├─ {s[1]} (ID: {s[0]})",
                                              values=(f"Grade {s[2]}",))

        self.home_tree.tag_configure("class_row", font=("Arial", 11, "bold"))

    # ==========================================
    # TAB 1: STUDENT SEARCH
    # ==========================================
    def build_student_search_tab(self, parent_frame):
        can_edit = self.session_data['user_level'] in ['Admin', 'Super_User']

        control_frame = tk.Frame(parent_frame)
        control_frame.pack(fill='x', padx=10, pady=10)

        tk.Label(control_frame, text="Filter by Name/ID:").pack(side=tk.LEFT)
        self.student_filter_var = tk.StringVar()
        self.student_filter_var.trace_add("write", self.filter_students)
        tk.Entry(control_frame, textvariable=self.student_filter_var, width=30).pack(side=tk.LEFT, padx=5)
        tk.Button(control_frame, text="Clear Filters", command=self.clear_student_filter).pack(side=tk.LEFT, padx=5)

        tk.Button(control_frame, text="View Assigned Classes", command=self.view_student_details).pack(side=tk.RIGHT,
                                                                                                       padx=5)
        if can_edit:
            tk.Button(control_frame, text="Update Student", command=self.update_student_popup).pack(side=tk.RIGHT,
                                                                                                    padx=5)

        columns = ("id", "name", "grade")
        self.student_tree = ttk.Treeview(parent_frame, columns=columns, show="headings", selectmode="browse")
        self.student_tree.heading("id", text="Student ID")
        self.student_tree.heading("name", text="Name")
        self.student_tree.heading("grade", text="Grade Level")

        self.student_tree.column("id", width=100, anchor="center")
        self.student_tree.column("name", anchor="center")
        self.student_tree.column("grade", width=100, anchor="center")
        self.student_tree.pack(expand=True, fill='both', padx=10, pady=5)

        self.student_tree.bind("<Double-1>", lambda e: self.view_student_details())

        self.all_students = backend.get_student_list(self.db_conn)
        self.populate_student_tree(self.all_students)

    def populate_student_tree(self, data):
        for item in self.student_tree.get_children():
            self.student_tree.delete(item)
        for row in data:
            self.student_tree.insert("", "end", values=row)

    def filter_students(self, *args):
        search_term = self.student_filter_var.get().lower()
        filtered = [s for s in self.all_students if search_term in str(s[1]).lower() or search_term in str(s[0])]
        self.populate_student_tree(filtered)

    def clear_student_filter(self):
        self.student_filter_var.set("")

    def get_selected_student(self):
        selected = self.student_tree.selection()
        if not selected:
            messagebox.showwarning("Selection Error", "Please select a student from the list first.")
            return None
        return self.student_tree.item(selected[0])['values']

    def update_student_popup(self):
        student = self.get_selected_student()
        if not student: return
        s_id, current_name, current_grade = student[0], student[1], student[2]

        popup = tk.Toplevel(self.root)
        popup.title("Update Student")
        popup.geometry("300x200")
        popup.grab_set()

        tk.Label(popup, text=f"Updating ID: {s_id}").pack(pady=5)
        tk.Label(popup, text="Name:").pack()
        name_entry = tk.Entry(popup, width=25)
        name_entry.insert(0, current_name)
        name_entry.pack(pady=5)

        tk.Label(popup, text="Grade Level:").pack()
        grade_combo = ttk.Combobox(popup, values=[9, 10, 11, 12], state="readonly")
        grade_combo.set(current_grade)
        grade_combo.pack(pady=5)

        def submit():
            new_name = name_entry.get().strip()
            new_grade = grade_combo.get()
            if not new_name or not new_grade:
                messagebox.showwarning("Error", "All fields required.", parent=popup)
                return
            success = backend.update_student(self.db_conn, s_id, new_name, int(new_grade))
            if success:
                messagebox.showinfo("Success", "Student updated.", parent=popup)
                popup.destroy()
                self.all_students = backend.get_student_list(self.db_conn)
                self.clear_student_filter()
            else:
                messagebox.showerror("Error", "Update failed.", parent=popup)

        tk.Button(popup, text="Save Changes", command=submit).pack(pady=10)

    def view_student_details(self):
        student = self.get_selected_student()
        if not student: return
        s_id, s_name = student[0], student[1]
        can_edit = self.session_data['user_level'] in ['Admin', 'Super_User']

        popup = tk.Toplevel(self.root)
        popup.title(f"Details: {s_name}")
        popup.geometry("350x400")
        popup.grab_set()

        content_frame = tk.Frame(popup)
        content_frame.pack(expand=True, fill='both', padx=10, pady=10)

        def refresh_ui():
            for widget in content_frame.winfo_children():
                widget.destroy()

            classes = backend.get_student_classes(self.db_conn, s_id)
            tk.Label(content_frame, text=f"Classes for {s_name}:", font=("Arial", 12, "bold")).pack(pady=10)

            self.student_class_listbox = tk.Listbox(content_frame, width=40, height=10)
            self.student_class_listbox.pack(expand=True, fill='both', pady=5)
            self.current_student_classes = classes

            if not classes:
                self.student_class_listbox.insert(tk.END, "Not enrolled in any classes.")
            else:
                for c in classes:
                    self.student_class_listbox.insert(tk.END, f"{c[1]} (ID: {c[0]})")

        refresh_ui()

        btn_frame = tk.Frame(popup)
        btn_frame.pack(fill='x', pady=10)

        if can_edit:
            tk.Button(btn_frame, text="Enroll in Class",
                      command=lambda: self.popup_assign_student_class(s_id, s_name, refresh_ui)).pack(fill='x', pady=2)
            tk.Button(btn_frame, text="Remove from Class",
                      command=lambda: self.popup_remove_student_from_class(s_id, refresh_ui)).pack(fill='x', pady=2)

        tk.Button(btn_frame, text="Close", command=popup.destroy).pack(fill='x', pady=5)

    def popup_assign_student_class(self, s_id, s_name, refresh_callback):
        popup = tk.Toplevel(self.root)
        popup.title(f"Enroll {s_name}")
        popup.geometry("300x150")
        popup.grab_set()

        classes = backend.get_class_list(self.db_conn)
        class_options = [f"{c[0]} - {c[1]}" for c in classes]

        tk.Label(popup, text="Select Class:").pack(pady=10)
        class_combo = ttk.Combobox(popup, values=class_options, state="readonly", width=25)
        class_combo.pack(pady=5)

        def submit():
            selected = class_combo.get()
            if not selected: return
            c_id = int(selected.split(" - ")[0])
            success = backend.add_student_to_class(self.db_conn, c_id, s_id)
            if success:
                refresh_callback()
                popup.destroy()
            else:
                messagebox.showerror("Error", "Could not enroll student. They may already be in this class.",
                                     parent=popup)

        tk.Button(popup, text="Assign", command=submit).pack(pady=10)

    def popup_remove_student_from_class(self, s_id, refresh_callback):
        selection = self.student_class_listbox.curselection()
        if not selection or not self.current_student_classes:
            messagebox.showerror("Error", "No class selected. Please highlight a class first.")
            return

        c_id = self.current_student_classes[selection[0]][0]
        c_name = self.current_student_classes[selection[0]][1]

        if messagebox.askyesno("Confirm", f"Remove student from {c_name}?"):
            if backend.remove_student_from_class(self.db_conn, c_id, s_id):
                refresh_callback()
            else:
                messagebox.showerror("Error", "Failed to remove from class.")

    # ==========================================
    # TAB 2: TEACHER SEARCH
    # ==========================================
    def build_teacher_search_tab(self, parent_frame):
        can_edit = self.session_data['user_level'] in ['Admin', 'Super_User']

        control_frame = tk.Frame(parent_frame)
        control_frame.pack(fill='x', padx=10, pady=10)

        tk.Label(control_frame, text="Filter by Name/ID:").pack(side=tk.LEFT)
        self.teacher_filter_var = tk.StringVar()
        self.teacher_filter_var.trace_add("write", self.filter_teachers)
        tk.Entry(control_frame, textvariable=self.teacher_filter_var, width=30).pack(side=tk.LEFT, padx=5)
        tk.Button(control_frame, text="Clear Filters", command=self.clear_teacher_filter).pack(side=tk.LEFT, padx=5)

        tk.Button(control_frame, text="View Assigned Classes", command=self.view_teacher_details).pack(side=tk.RIGHT,
                                                                                                       padx=5)
        if can_edit:
            tk.Button(control_frame, text="Update Teacher", command=self.update_teacher_popup).pack(side=tk.RIGHT,
                                                                                                    padx=5)

        columns = ("id", "name")
        self.teacher_tree = ttk.Treeview(parent_frame, columns=columns, show="headings", selectmode="browse")
        self.teacher_tree.heading("id", text="Teacher ID")
        self.teacher_tree.heading("name", text="Name")
        self.teacher_tree.column("id", width=100, anchor="center")
        self.teacher_tree.column("name", anchor="center")
        self.teacher_tree.pack(expand=True, fill='both', padx=10, pady=5)

        self.teacher_tree.bind("<Double-1>", self.on_teacher_double_click)

        self.all_teachers = backend.get_teacher_list(self.db_conn)
        self.populate_teacher_tree(self.all_teachers)

    def populate_teacher_tree(self, data):
        for item in self.teacher_tree.get_children():
            self.teacher_tree.delete(item)
        for row in data:
            self.teacher_tree.insert("", "end", values=row)

    def filter_teachers(self, *args):
        search_term = self.teacher_filter_var.get().lower()
        filtered = [t for t in self.all_teachers if search_term in str(t[1]).lower() or search_term in str(t[0])]
        self.populate_teacher_tree(filtered)

    def clear_teacher_filter(self):
        self.teacher_filter_var.set("")

    def get_selected_teacher(self):
        selected = self.teacher_tree.selection()
        if not selected:
            messagebox.showwarning("Selection Error", "Please select a teacher from the list first.")
            return None
        return self.teacher_tree.item(selected[0])['values']

    def update_teacher_popup(self):
        teacher = self.get_selected_teacher()
        if not teacher: return
        t_id, current_name = teacher[0], teacher[1]

        popup = tk.Toplevel(self.root)
        popup.title("Update Teacher")
        popup.geometry("300x150")
        popup.grab_set()

        tk.Label(popup, text=f"Updating ID: {t_id}").pack(pady=5)
        name_entry = tk.Entry(popup, width=25)
        name_entry.insert(0, current_name)
        name_entry.pack(pady=10)

        def submit():
            new_name = name_entry.get().strip()
            if not new_name:
                messagebox.showwarning("Error", "Name cannot be blank.", parent=popup)
                return
            success = backend.update_teacher_name(self.db_conn, t_id, new_name)
            if success:
                messagebox.showinfo("Success", "Teacher updated successfully.", parent=popup)
                popup.destroy()
                self.all_teachers = backend.get_teacher_list(self.db_conn)
                self.clear_teacher_filter()
            else:
                messagebox.showerror("Error", "Update failed.", parent=popup)

        tk.Button(popup, text="Save Changes", command=submit).pack()

    def on_teacher_double_click(self, event):
        teacher = self.get_selected_teacher()
        if not teacher: return
        t_id = teacher[0]
        classes = backend.get_teacher_classes(self.db_conn, t_id)
        self.notebook.select(3)
        self.populate_class_tree(classes)

    def view_teacher_details(self):
        teacher = self.get_selected_teacher()
        if not teacher: return
        t_id, t_name = teacher[0], teacher[1]
        can_edit = self.session_data['user_level'] in ['Admin', 'Super_User']

        popup = tk.Toplevel(self.root)
        popup.title(f"Details: {t_name}")
        popup.geometry("350x400")
        popup.grab_set()

        content_frame = tk.Frame(popup)
        content_frame.pack(expand=True, fill='both', padx=10, pady=10)

        def refresh_ui():
            for widget in content_frame.winfo_children():
                widget.destroy()

            classes = backend.get_teacher_classes(self.db_conn, t_id)
            tk.Label(content_frame, text=f"Classes assigned to {t_name}:", font=("Arial", 12, "bold")).pack(pady=10)

            self.teacher_class_listbox = tk.Listbox(content_frame, width=40, height=10)
            self.teacher_class_listbox.pack(expand=True, fill='both', pady=5)
            self.current_teacher_classes = classes

            if not classes:
                self.teacher_class_listbox.insert(tk.END, "No classes assigned yet.")
            else:
                for c in classes:
                    self.teacher_class_listbox.insert(tk.END, f"{c[1]} (ID: {c[0]})")

        refresh_ui()

        btn_frame = tk.Frame(popup)
        btn_frame.pack(fill='x', pady=10)

        if can_edit:
            tk.Button(btn_frame, text="Assign to Class",
                      command=lambda: self.popup_assign_teacher_class(t_id, t_name, refresh_ui)).pack(fill='x', pady=2)
            tk.Button(btn_frame, text="Remove from Class",
                      command=lambda: self.popup_remove_teacher_from_class(t_id, refresh_ui)).pack(fill='x', pady=2)

        tk.Button(btn_frame, text="Close", command=popup.destroy).pack(fill='x', pady=5)

    def popup_assign_teacher_class(self, t_id, t_name, refresh_callback):
        popup = tk.Toplevel(self.root)
        popup.title(f"Assign {t_name}")
        popup.geometry("300x150")
        popup.grab_set()

        classes = backend.get_class_list(self.db_conn)
        class_options = [f"{c[0]} - {c[1]}" for c in classes]

        tk.Label(popup, text="Select Class to Take Over:").pack(pady=10)
        class_combo = ttk.Combobox(popup, values=class_options, state="readonly", width=25)
        class_combo.pack(pady=5)

        def submit():
            selected = class_combo.get()
            if not selected: return
            c_id = int(selected.split(" - ")[0])
            success = backend.assign_teacher_to_class(self.db_conn, c_id, t_id)
            if success:
                refresh_callback()
                popup.destroy()
            else:
                messagebox.showerror("Error", "Could not assign teacher.", parent=popup)

        tk.Button(popup, text="Assign", command=submit).pack(pady=10)

    def popup_remove_teacher_from_class(self, t_id, refresh_callback):
        selection = self.teacher_class_listbox.curselection()
        if not selection or not self.current_teacher_classes:
            messagebox.showerror("Error", "No class selected. Please highlight a class first.")
            return

        c_id = self.current_teacher_classes[selection[0]][0]
        c_name = self.current_teacher_classes[selection[0]][1]

        if messagebox.askyesno("Confirm", f"Remove teacher from {c_name}?"):
            if backend.remove_teacher_from_class(self.db_conn, c_id):
                refresh_callback()
            else:
                messagebox.showerror("Error", "Failed to remove from class.")

    # ==========================================
    # TAB 3: CLASS SEARCH & DETAILS
    # ==========================================
    def build_class_search_tab(self, parent_frame):
        can_edit = self.session_data['user_level'] in ['Admin', 'Super_User']

        control_frame = tk.Frame(parent_frame)
        control_frame.pack(fill='x', padx=10, pady=10)

        tk.Label(control_frame, text="Filter by Name/ID:").pack(side=tk.LEFT)
        self.class_filter_var = tk.StringVar()
        self.class_filter_var.trace_add("write", self.filter_classes)
        tk.Entry(control_frame, textvariable=self.class_filter_var, width=30).pack(side=tk.LEFT, padx=5)
        tk.Button(control_frame, text="Clear Filters", command=self.clear_class_filter).pack(side=tk.LEFT, padx=5)

        tk.Button(control_frame, text="View Details", command=self.view_class_details).pack(side=tk.RIGHT, padx=5)
        if can_edit:
            tk.Button(control_frame, text="Update Class", command=self.update_class_popup).pack(side=tk.RIGHT, padx=5)

        columns = ("id", "name")
        self.class_tree = ttk.Treeview(parent_frame, columns=columns, show="headings", selectmode="browse")
        self.class_tree.heading("id", text="Class ID")
        self.class_tree.heading("name", text="Class Name")
        self.class_tree.column("id", width=100, anchor="center")
        self.class_tree.column("name", anchor="center")
        self.class_tree.pack(expand=True, fill='both', padx=10, pady=5)

        self.class_tree.bind("<Double-1>", self.on_class_double_click)

        self.all_classes = backend.get_class_list(self.db_conn)
        self.populate_class_tree(self.all_classes)

    def populate_class_tree(self, data):
        for item in self.class_tree.get_children():
            self.class_tree.delete(item)
        for row in data:
            self.class_tree.insert("", "end", values=row)

    def filter_classes(self, *args):
        search_term = self.class_filter_var.get().lower()
        filtered = [c for c in self.all_classes if search_term in str(c[1]).lower() or search_term in str(c[0])]
        self.populate_class_tree(filtered)

    def clear_class_filter(self):
        self.class_filter_var.set("")

    def get_selected_class(self):
        selected = self.class_tree.selection()
        if not selected:
            messagebox.showwarning("Selection Error", "Please select a class from the list first.")
            return None
        return self.class_tree.item(selected[0])['values']

    def update_class_popup(self):
        cls = self.get_selected_class()
        if not cls: return
        c_id, current_name = cls[0], cls[1]

        popup = tk.Toplevel(self.root)
        popup.title("Update Class")
        popup.geometry("300x150")
        popup.grab_set()

        tk.Label(popup, text=f"Updating ID: {c_id}").pack(pady=5)
        name_entry = tk.Entry(popup, width=25)
        name_entry.insert(0, current_name)
        name_entry.pack(pady=10)

        def submit():
            new_name = name_entry.get().strip()
            if not new_name:
                messagebox.showwarning("Error", "Class name cannot be blank.", parent=popup)
                return
            success = backend.update_class_name(self.db_conn, c_id, new_name)
            if success:
                messagebox.showinfo("Success", "Class updated successfully.", parent=popup)
                popup.destroy()
                self.all_classes = backend.get_class_list(self.db_conn)
                self.clear_class_filter()
            else:
                messagebox.showerror("Error", "Update failed.", parent=popup)

        tk.Button(popup, text="Save Changes", command=submit).pack()

    def on_class_double_click(self, event):
        cls = self.get_selected_class()
        if not cls: return
        c_id = cls[0]
        students = backend.get_class_students(self.db_conn, c_id)
        self.notebook.select(1)
        self.populate_student_tree(students)

    def view_class_details(self):
        cls = self.get_selected_class()
        if not cls: return
        c_id, c_name = cls[0], cls[1]
        can_edit = self.session_data['user_level'] in ['Admin', 'Super_User']

        popup = tk.Toplevel(self.root)
        popup.title(f"Class Details: {c_name}")
        popup.geometry("350x550")
        popup.grab_set()

        content_frame = tk.Frame(popup)
        content_frame.pack(expand=True, fill='both', padx=10, pady=10)

        def refresh_ui():
            for widget in content_frame.winfo_children():
                widget.destroy()

            teacher = backend.get_class_teacher(self.db_conn, c_id)
            students = backend.get_class_students(self.db_conn, c_id)

            teacher_name = teacher[1] if teacher else "No Teacher Assigned"
            tk.Label(content_frame, text=f"Teacher: {teacher_name}", font=("Arial", 11, "bold"), fg="blue").pack(pady=5)
            tk.Label(content_frame, text="Enrolled Students:", font=("Arial", 10, "underline")).pack(pady=5)

            self.class_listbox = tk.Listbox(content_frame, width=40, height=10)
            self.class_listbox.pack(expand=True, fill='both', pady=5)

            self.current_students = students
            for s in students:
                self.class_listbox.insert(tk.END, f"{s[1]} (Grade: {s[2]})")

        refresh_ui()

        btn_frame = tk.Frame(popup)
        btn_frame.pack(fill='x', pady=10, padx=10)

        if can_edit:
            tk.Button(btn_frame, text="Add Student",
                      command=lambda: self.popup_class_add_students(c_id, c_name, refresh_ui)).pack(fill='x', pady=2)
            tk.Button(btn_frame, text="Remove Selected Student",
                      command=lambda: self.popup_remove_student(c_id, refresh_ui)).pack(fill='x', pady=2)
            tk.Button(btn_frame, text="Assign/Change Teacher",
                      command=lambda: self.popup_class_assign_teacher(c_id, c_name, refresh_ui)).pack(fill='x', pady=2)
            tk.Button(btn_frame, text="Remove Teacher",
                      command=lambda: self.popup_remove_teacher(c_id, refresh_ui)).pack(fill='x', pady=2)

        tk.Button(btn_frame, text="Close", command=popup.destroy).pack(fill='x', pady=10)

    def popup_class_add_students(self, c_id, c_name, refresh_callback):
        popup = tk.Toplevel(self.root)
        popup.title(f"Add Students to {c_name}")
        popup.geometry("300x200")
        popup.grab_set()

        students = backend.get_student_list(self.db_conn)
        student_options = [f"{s[0]} - {s[1]} (Gr: {s[2]})" for s in students]

        tk.Label(popup, text="Select Student:").pack(pady=10)
        student_combo = ttk.Combobox(popup, values=student_options, state="readonly", width=25)
        student_combo.pack(pady=5)

        def submit():
            selected = student_combo.get()
            if not selected: return
            s_id = int(selected.split(" - ")[0])
            if backend.add_student_to_class(self.db_conn, c_id, s_id):
                refresh_callback()
                student_combo.set('')
            else:
                messagebox.showerror("Error", "Student already in class.", parent=popup)

        tk.Button(popup, text="Add to Class", command=submit).pack(pady=10)
        tk.Button(popup, text="Done", command=popup.destroy).pack(pady=5)

    def popup_class_assign_teacher(self, c_id, c_name, refresh_callback):
        popup = tk.Toplevel(self.root)
        popup.title(f"Set Teacher")
        popup.geometry("300x150")
        popup.grab_set()

        teachers = backend.get_teacher_list(self.db_conn)
        teacher_options = [f"{t[0]} - {t[1]}" for t in teachers]
        teacher_combo = ttk.Combobox(popup, values=teacher_options, state="readonly", width=25)
        teacher_combo.pack(pady=10)

        def submit():
            selected = teacher_combo.get()
            if not selected: return
            t_id = int(selected.split(" - ")[0])
            if backend.assign_teacher_to_class(self.db_conn, c_id, t_id):
                refresh_callback()
                popup.destroy()

        tk.Button(popup, text="Assign", command=submit).pack()

    def popup_remove_student(self, c_id, refresh_callback):
        selection = self.class_listbox.curselection()
        if not selection:
            messagebox.showerror("Error", "No student selected. Please highlight a student from the list first.")
            return

        s_id = self.current_students[selection[0]][0]
        s_name = self.current_students[selection[0]][1]

        if messagebox.askyesno("Confirm", f"Remove {s_name} from class?"):
            if backend.remove_student_from_class(self.db_conn, c_id, s_id):
                refresh_callback()
            else:
                messagebox.showerror("Error", "Failed to remove student.")

    def popup_remove_teacher(self, c_id, refresh_callback):
        if messagebox.askyesno("Confirm", "Remove the assigned teacher from this class?"):
            if backend.remove_teacher_from_class(self.db_conn, c_id):
                refresh_callback()
            else:
                messagebox.showerror("Error", "Failed to remove teacher.")

    # ==========================================
    # PROFILE & SETTINGS TABS
    # ==========================================
    def build_profile_tab(self, parent_frame):
        tk.Label(parent_frame, text="My Profile", font=("Arial", 18, "bold")).pack(pady=20)

        tk.Label(parent_frame, text=f"ID: {self.session_data['teacher_id']}").pack(pady=5)
        tk.Label(parent_frame, text=f"Role: {self.session_data['user_level']}").pack(pady=5)

        tk.Button(parent_frame, text="Update My Name", width=20, command=self.popup_update_own_name).pack(pady=15)
        tk.Button(parent_frame, text="Change Password", width=20, command=self.popup_change_own_password).pack(pady=5)

    def build_base_admin_tab(self, parent_frame):
        tk.Label(parent_frame, text="Base Admin Security", font=("Arial", 18, "bold")).pack(pady=20)
        tk.Label(parent_frame, text="WARNING: You are the root administrator.\nDo not lose this password.",
                 fg="red").pack(pady=10)

        tk.Button(parent_frame, text="Change Admin Password", width=25, command=self.popup_change_own_password).pack(
            pady=15)

    def popup_update_own_name(self):
        popup = tk.Toplevel(self.root)
        popup.title("Update Name")
        popup.geometry("300x150")
        popup.grab_set()

        tk.Label(popup, text="New Name:").pack(pady=10)
        name_entry = tk.Entry(popup, width=25)
        name_entry.insert(0, self.session_data['name'])
        name_entry.pack(pady=5)

        def submit():
            new_name = name_entry.get().strip()
            if not new_name: return

            if backend.update_teacher_name(self.db_conn, self.session_data['teacher_id'], new_name):
                self.session_data['name'] = new_name
                messagebox.showinfo("Success", "Name updated! Please logout to see changes everywhere.", parent=popup)
                popup.destroy()
            else:
                messagebox.showerror("Error", "Failed to update name.", parent=popup)

        tk.Button(popup, text="Save", command=submit).pack(pady=10)

    def popup_change_own_password(self):
        popup = tk.Toplevel(self.root)
        popup.title("Change Password")
        popup.geometry("300x250")
        popup.grab_set()

        tk.Label(popup, text="Current Password:").pack(pady=5)
        current_entry = tk.Entry(popup, show="*")
        current_entry.pack()

        tk.Label(popup, text="New Password:").pack(pady=5)
        new_entry = tk.Entry(popup, show="*")
        new_entry.pack()

        tk.Label(popup, text="Confirm New:").pack(pady=5)
        confirm_entry = tk.Entry(popup, show="*")
        confirm_entry.pack()

        def submit():
            curr = current_entry.get()
            new_pw = new_entry.get()
            conf = confirm_entry.get()

            if not curr or not new_pw or not conf:
                messagebox.showwarning("Error", "All fields required.", parent=popup)
                return
            if new_pw != conf:
                messagebox.showwarning("Error", "New passwords do not match.", parent=popup)
                return

            if backend.update_password(self.db_conn, self.session_data['teacher_id'], curr, new_pw):
                messagebox.showinfo("Success", "Password updated successfully.", parent=popup)
                popup.destroy()
            else:
                messagebox.showerror("Error", "Current password incorrect.", parent=popup)

        tk.Button(popup, text="Update Password", command=submit).pack(pady=15)

    # ==========================================
    # TAB 4: ADMIN TASKS & POPUPS
    # ==========================================
    def build_admin_tab(self, parent_frame):
        tk.Label(parent_frame, text="Admin Control Panel", font=("Arial", 18, "bold")).pack(pady=20)

        btn_frame = tk.Frame(parent_frame)
        btn_frame.pack()

        tk.Button(btn_frame, text="Add New Teacher", width=25, command=self.popup_add_teacher).grid(row=0, column=0,
                                                                                                    pady=5, padx=5)
        tk.Button(btn_frame, text="Add New Student", width=25, command=self.popup_add_student).grid(row=1, column=0,
                                                                                                    pady=5, padx=5)
        tk.Button(btn_frame, text="Add New Class", width=25, command=self.popup_add_class).grid(row=2, column=0, pady=5,
                                                                                                padx=5)
        tk.Button(btn_frame, text="Force Password Change", width=25, command=self.popup_force_password).grid(row=3,
                                                                                                             column=0,
                                                                                                             pady=5,
                                                                                                             padx=5)
        tk.Button(btn_frame, text="Assign User Level", width=25, command=self.popup_assign_level).grid(row=4, column=0,
                                                                                                       pady=5, padx=5)

        if self.session_data['user_level'] == 'Admin':
            tk.Button(btn_frame, text="Delete Teacher", width=25, fg="red", command=self.popup_delete_teacher).grid(
                row=0, column=1, pady=5, padx=5)
            tk.Button(btn_frame, text="Delete Student", width=25, fg="red", command=self.popup_delete_student).grid(
                row=1, column=1, pady=5, padx=5)
            tk.Button(btn_frame, text="Delete Class", width=25, fg="red", command=self.popup_delete_class).grid(row=2,
                                                                                                                column=1,
                                                                                                                pady=5,
                                                                                                                padx=5)

    def popup_add_teacher(self):
        popup = tk.Toplevel(self.root)
        popup.title("Add New Teacher")
        popup.geometry("300x150")
        popup.grab_set()

        tk.Label(popup, text="Teacher Name:").pack(pady=10)
        name_entry = tk.Entry(popup)
        name_entry.pack()

        def submit():
            name = name_entry.get().strip()
            if not name:
                messagebox.showwarning("Input Error", "Name cannot be empty.", parent=popup)
                return
            new_id = backend.add_new_teacher(self.db_conn, name)
            if new_id:
                messagebox.showinfo("Success", f"Teacher '{name}' added!\nEmployee ID: {new_id}", parent=popup)
                self.all_teachers = backend.get_teacher_list(self.db_conn)
                self.clear_teacher_filter()
                popup.destroy()
            else:
                messagebox.showerror("Database Error", "Failed to add teacher.", parent=popup)

        tk.Button(popup, text="Save", command=submit).pack(pady=15)

    def popup_add_student(self):
        popup = tk.Toplevel(self.root)
        popup.title("Add New Student")
        popup.geometry("300x200")
        popup.grab_set()

        tk.Label(popup, text="Student Name:").pack(pady=5)
        name_entry = tk.Entry(popup)
        name_entry.pack(pady=5)

        tk.Label(popup, text="Grade Level (9-12):").pack(pady=5)
        grade_combo = ttk.Combobox(popup, values=[9, 10, 11, 12], state="readonly")
        grade_combo.pack()

        def submit():
            name = name_entry.get().strip()
            grade = grade_combo.get()
            if not name or not grade:
                messagebox.showwarning("Input Error", "Please fill out all fields.", parent=popup)
                return
            new_id = backend.add_new_student(self.db_conn, name, int(grade))
            if new_id:
                messagebox.showinfo("Success", f"Student '{name}' added!\nStudent ID: {new_id}", parent=popup)
                self.all_students = backend.get_student_list(self.db_conn)
                self.clear_student_filter()
                popup.destroy()
            else:
                messagebox.showerror("Database Error", "Failed to add student.", parent=popup)

        tk.Button(popup, text="Save", command=submit).pack(pady=15)

    def popup_add_class(self):
        popup = tk.Toplevel(self.root)
        popup.title("Add New Class")
        popup.geometry("300x150")
        popup.grab_set()

        tk.Label(popup, text="Class Name:").pack(pady=10)
        class_entry = tk.Entry(popup)
        class_entry.pack()

        def submit():
            class_name = class_entry.get().strip()
            if not class_name:
                messagebox.showwarning("Input Error", "Class name cannot be empty.", parent=popup)
                return
            new_id = backend.add_new_class(self.db_conn, class_name)
            if new_id:
                messagebox.showinfo("Success", f"Class '{class_name}' added!\nClass ID: {new_id}", parent=popup)
                self.all_classes = backend.get_class_list(self.db_conn)
                self.clear_class_filter()
                popup.destroy()
            else:
                messagebox.showerror("Database Error", "Failed to add class.", parent=popup)

        tk.Button(popup, text="Save", command=submit).pack(pady=15)

    def popup_force_password(self):
        popup = tk.Toplevel(self.root)
        popup.title("Force Password Reset")
        popup.geometry("350x250")
        popup.grab_set()

        teachers = backend.get_teacher_list(self.db_conn)
        teacher_options = [f"{t[0]} - {t[1]}" for t in teachers]

        tk.Label(popup, text="Select Teacher:").pack(pady=5)
        teacher_combo = ttk.Combobox(popup, values=teacher_options, state="readonly", width=30)
        teacher_combo.pack(pady=5)

        tk.Label(popup, text="New Temp Password:").pack(pady=5)
        pw_entry = tk.Entry(popup, show="*")
        pw_entry.pack(pady=5)

        def submit():
            selected_teacher = teacher_combo.get()
            new_pw = pw_entry.get().strip()

            if not selected_teacher:
                messagebox.showwarning("Input Error", "Please select a teacher.", parent=popup)
                return
            if not new_pw:
                messagebox.showwarning("Input Error", "Please enter a temporary password.", parent=popup)
                return

            teacher_id = int(selected_teacher.split(" - ")[0])
            success = backend.admin_reset_password(self.db_conn, teacher_id, new_pw, self.session_data['teacher_id'])

            if success:
                messagebox.showinfo("Success", f"Password reset successful for {selected_teacher}.", parent=popup)
                popup.destroy()
            else:
                messagebox.showerror("Update Failed",
                                     "Could not reset password. Ensure you have the proper permission level to modify this user.",
                                     parent=popup)

        tk.Button(popup, text="Update Password", command=submit).pack(pady=15)

    def popup_assign_level(self):
        popup = tk.Toplevel(self.root)
        popup.title("Assign User Level")
        popup.geometry("300x200")
        popup.grab_set()

        teachers = backend.get_teacher_list(self.db_conn)
        teacher_options = [f"{t[0]} - {t[1]}" for t in teachers]

        tk.Label(popup, text="Select Teacher:").pack(pady=5)
        teacher_combo = ttk.Combobox(popup, values=teacher_options, state="readonly")
        teacher_combo.pack(pady=5)

        tk.Label(popup, text="Select New Level:").pack(pady=5)
        if self.session_data['user_level'] == 'Admin':
            allowed_levels = ['Admin', 'Super_User', 'User']
        else:
            allowed_levels = ['Super_User', 'User']

        level_combo = ttk.Combobox(popup, values=allowed_levels, state="readonly")
        level_combo.pack(pady=5)

        def submit():
            selected_teacher = teacher_combo.get()
            new_level = level_combo.get()

            if not selected_teacher or not new_level:
                messagebox.showwarning("Input Error", "Please select a teacher and a User Level.", parent=popup)
                return

            teacher_id = int(selected_teacher.split(" - ")[0])
            success = backend.update_user_level(self.db_conn, teacher_id, new_level, self.session_data['teacher_id'])

            if success:
                messagebox.showinfo("Success", f"Role for {selected_teacher} successfully updated to {new_level}.",
                                    parent=popup)
                popup.destroy()
            else:
                messagebox.showerror("Update Failed",
                                     "Could not update role. Ensure you have the proper permission level to modify this user.",
                                     parent=popup)

        tk.Button(popup, text="Update Role", command=submit).pack(pady=15)

    # --- DELETE POPUPS ---
    def popup_delete_teacher(self):
        popup = tk.Toplevel(self.root)
        popup.title("Delete Teacher")
        popup.geometry("300x150")
        popup.grab_set()

        teachers = backend.get_teacher_list(self.db_conn)
        options = [f"{t[0]} - {t[1]}" for t in teachers]

        tk.Label(popup, text="Select Teacher to Delete:").pack(pady=10)
        combo = ttk.Combobox(popup, values=options, state="readonly", width=25)
        combo.pack()

        def submit():
            selected = combo.get()
            if not selected: return
            t_id = int(selected.split(" - ")[0])
            t_name = selected.split(" - ")[1]

            if messagebox.askyesno("Confirm", f"PERMANENTLY delete Teacher: {t_name}?", parent=popup):
                if backend.delete_teacher(self.db_conn, t_id):
                    messagebox.showinfo("Deleted", f"{t_name} removed from system.", parent=popup)
                    self.all_teachers = backend.get_teacher_list(self.db_conn)
                    self.clear_teacher_filter()
                    popup.destroy()
                else:
                    messagebox.showerror("Error", "Could not delete.", parent=popup)

        tk.Button(popup, text="DELETE", fg="red", command=submit).pack(pady=15)

    def popup_delete_student(self):
        popup = tk.Toplevel(self.root)
        popup.title("Delete Student")
        popup.geometry("300x150")
        popup.grab_set()

        students = backend.get_student_list(self.db_conn)
        options = [f"{s[0]} - {s[1]}" for s in students]

        tk.Label(popup, text="Select Student to Delete:").pack(pady=10)
        combo = ttk.Combobox(popup, values=options, state="readonly", width=25)
        combo.pack()

        def submit():
            selected = combo.get()
            if not selected: return
            s_id = int(selected.split(" - ")[0])
            s_name = selected.split(" - ")[1]

            if messagebox.askyesno("Confirm", f"PERMANENTLY delete Student: {s_name}?", parent=popup):
                if backend.delete_student(self.db_conn, s_id):
                    messagebox.showinfo("Deleted", f"{s_name} removed from system.", parent=popup)
                    self.all_students = backend.get_student_list(self.db_conn)
                    self.clear_student_filter()
                    popup.destroy()
                else:
                    messagebox.showerror("Error", "Could not delete.", parent=popup)

        tk.Button(popup, text="DELETE", fg="red", command=submit).pack(pady=15)

    def popup_delete_class(self):
        popup = tk.Toplevel(self.root)
        popup.title("Delete Class")
        popup.geometry("300x150")
        popup.grab_set()

        classes = backend.get_class_list(self.db_conn)
        options = [f"{c[0]} - {c[1]}" for c in classes]

        tk.Label(popup, text="Select Class to Delete:").pack(pady=10)
        combo = ttk.Combobox(popup, values=options, state="readonly", width=25)
        combo.pack()

        def submit():
            selected = combo.get()
            if not selected: return
            c_id = int(selected.split(" - ")[0])
            c_name = selected.split(" - ")[1]

            if messagebox.askyesno("Confirm", f"PERMANENTLY delete Class: {c_name}?", parent=popup):
                if backend.delete_class(self.db_conn, c_id):
                    messagebox.showinfo("Deleted", f"{c_name} removed from system.", parent=popup)
                    self.all_classes = backend.get_class_list(self.db_conn)
                    self.clear_class_filter()
                    popup.destroy()
                else:
                    messagebox.showerror("Error", "Could not delete.", parent=popup)

        tk.Button(popup, text="DELETE", fg="red", command=submit).pack(pady=15)


if __name__ == "__main__":
    root = tk.Tk()
    app = SchoolPortalApp(root)
    root.mainloop()