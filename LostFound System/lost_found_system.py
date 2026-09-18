import os
import re
import shutil
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from pathlib import Path

try:
    import mysql.connector
    from mysql.connector import Error
except ImportError:
    mysql = None
    Error = Exception

try:
    import bcrypt
except ImportError:
    bcrypt = None

try:
    from PIL import Image, ImageTk, ImageEnhance
except ImportError:
    Image = ImageTk = ImageEnhance = None

# ============================================================
# CONFIGURATION
# ============================================================
# CHANGE ONLY THE VALUES YOU NEED HERE.
DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = "Rinchen@123"       
DB_NAME = "lost_found_db"

APP_TITLE = "Student's Lost and Found Management System"
COLLEGE_NAME = "SAMTSE COLLEGE OF EDUCATION"

# ============================================================
# ASSET FILES - PUT THESE BESIDE THIS PYTHON FILE
# ============================================================
# College logo: college_logo.png
LOGO_FILE = "college_logo.png"

#
BACKGROUND_FILE = "background.jpg"

DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "Admin@123"

# ============================================================
# COLOURS
# ============================================================
BG = "#eef4f8"
NAVY = "#277abd"
BLUE = "#2478c9"
TEAL = "#9ed6de"
PURPLE = "#7654c8"
ORANGE = "#f5a313"
GREEN = "#2e9d67"
RED = "#d9534f"
WHITE = "#ffffff"
TEXT = "#18324a"
MUTED = "#617b91"
BORDER = "#d5e2eb"
LIGHT_BLUE = "#e2f0fb"
LIGHT_GREY = "#f7fafc"

CATEGORIES = [
    "Personal Item",
    "Electronics",
    "Documents",
    "Clothing",
    "Books/Stationery",
    "Keys",
    "Wallet/Purse",
    "Other",
]

BASE_DIR = Path(__file__).resolve().parent


# ============================================================
# MAIN APPLICATION
# ============================================================
class LostFoundSystem:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1250x800")
        self.root.minsize(1050, 700)
        self.root.configure(bg=BG)

        self.current_user = None
        self.current_role = None
        self.current_page = ""
        self.logo_photo = None
        self.bg_photo = None
        self.login_bg_label = None
        self.page_history = []
        self._navigating_back = False

        self.setup_style()
        self.db = None
        self.connect_and_setup_database()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        if self.db:
            self.show_login_screen(record_history=False)

    # ========================================================
    # DATABASE
    # ========================================================
    def connect_and_setup_database(self):
        if mysql is None:
            messagebox.showerror(
                "Missing Package",
                "mysql-connector-python is not installed.\n\n"
                "Run:\npip install mysql-connector-python bcrypt pillow"
            )
            return

        if bcrypt is None:
            messagebox.showerror(
                "Missing Package",
                "bcrypt is not installed.\n\nRun:\npip install bcrypt"
            )
            return

        try:
            server = mysql.connector.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASSWORD,
            )
            cur = server.cursor()
            cur.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}`")
            cur.close()
            server.close()

            self.db = mysql.connector.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME,
            )

            self.create_tables()
            self.create_default_admin()

        except Error as e:
            messagebox.showerror(
                "Database Setup Error",
                "Could not connect to MySQL.\n\n"
                f"Error: {e}\n\n"
                "Please check:\n"
                "1. MySQL Server is running.\n"
                "2. DB_USER is correct.\n"
                "3. DB_PASSWORD is correct."
            )
            self.db = None

    def table_columns(self, table):
        cur = self.db.cursor()
        cur.execute(f"SHOW COLUMNS FROM `{table}`")
        columns = {row[0] for row in cur.fetchall()}
        cur.close()
        return columns

    def backup_broken_table(self, table):
        """Preserve an old incompatible table before creating the correct one."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = f"{table}_old_{timestamp}"
        cur = self.db.cursor()
        cur.execute(f"RENAME TABLE `{table}` TO `{backup}`")
        self.db.commit()
        cur.close()
        return backup

    def create_tables(self):
        cur = self.db.cursor()

        # If a previous version created a table with the wrong structure
        # (for example, without the id column), preserve it and recreate it.
        existing = set()
        cur.execute("SHOW TABLES")
        for row in cur.fetchall():
            existing.add(row[0])
        cur.close()

        required_users = {"id", "full_name", "username", "email", "password_hash", "role"}
        required_lost = {"id", "item_no", "item_name", "category", "description", "location", "item_date", "status", "contact", "reported_by"}
        required_found = required_lost.copy()

        for table, required in [
            ("Users", required_users),
            ("Lost_items", required_lost),
            ("Found_items", required_found),
        ]:
            if table in existing:
                try:
                    columns = self.table_columns(table)
                    if not required.issubset(columns):
                        backup = self.backup_broken_table(table)
                        print(f"Old incompatible table preserved as {backup}")
                except Error:
                    pass

        cur = self.db.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS Users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                full_name VARCHAR(120) NOT NULL,
                username VARCHAR(60) NOT NULL UNIQUE,
                email VARCHAR(120) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                role ENUM('User','Administrator') NOT NULL DEFAULT 'User',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS Lost_items (
                id INT AUTO_INCREMENT PRIMARY KEY,
                item_no VARCHAR(40) NOT NULL UNIQUE,
                item_name VARCHAR(120) NOT NULL,
                category VARCHAR(80) NOT NULL,
                description TEXT NOT NULL,
                location VARCHAR(150) NOT NULL,
                item_date DATE NOT NULL,
                status VARCHAR(30) NOT NULL DEFAULT 'Lost',
                contact VARCHAR(150) NOT NULL,
                reported_by INT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (reported_by) REFERENCES Users(id) ON DELETE CASCADE
            ) ENGINE=InnoDB
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS Found_items (
                id INT AUTO_INCREMENT PRIMARY KEY,
                item_no VARCHAR(40) NOT NULL UNIQUE,
                item_name VARCHAR(120) NOT NULL,
                category VARCHAR(80) NOT NULL,
                description TEXT NOT NULL,
                location VARCHAR(150) NOT NULL,
                item_date DATE NOT NULL,
                status VARCHAR(30) NOT NULL DEFAULT 'Found',
                contact VARCHAR(150) NOT NULL,
                reported_by INT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (reported_by) REFERENCES Users(id) ON DELETE CASCADE
            ) ENGINE=InnoDB
        """)
        self.db.commit()
        cur.close()

    def create_default_admin(self):
        cur = self.db.cursor(dictionary=True)
        cur.execute("SELECT id, password_hash, role FROM Users WHERE username=%s", (DEFAULT_ADMIN_USERNAME,))
        user = cur.fetchone()

        if user is None:
            hashed = bcrypt.hashpw(
                DEFAULT_ADMIN_PASSWORD.encode("utf-8"),
                bcrypt.gensalt()
            ).decode("utf-8")
            cur.execute(
                """
                INSERT INTO Users
                (full_name, username, email, password_hash, role)
                VALUES (%s,%s,%s,%s,%s)
                """,
                (
                    "System Administrator",
                    DEFAULT_ADMIN_USERNAME,
                    "admin@sce.edu.bt",
                    hashed,
                    "Administrator",
                )
            )
            self.db.commit()
        elif user["role"] != "Administrator":
            cur.execute(
                "UPDATE Users SET role='Administrator' WHERE username=%s",
                (DEFAULT_ADMIN_USERNAME,)
            )
            self.db.commit()
        cur.close()

    def ensure_connection(self):
        if self.db is None:
            return False
        try:
            if not self.db.is_connected():
                self.db.reconnect(attempts=2, delay=1)
            return self.db.is_connected()
        except Exception:
            return False

    def db_query(self, query, params=()):
        if not self.ensure_connection():
            messagebox.showerror("Database", "Database connection is not available.")
            return []
        try:
            cur = self.db.cursor(dictionary=True)
            cur.execute(query, params)
            rows = cur.fetchall()
            cur.close()
            return rows
        except Error as e:
            messagebox.showerror("Database Error", str(e))
            return []

    def db_action(self, query, params=()):
        if not self.ensure_connection():
            messagebox.showerror("Database", "Database connection is not available.")
            return None
        try:
            cur = self.db.cursor()
            cur.execute(query, params)
            self.db.commit()
            result = cur.lastrowid
            cur.close()
            return result
        except Error as e:
            try:
                self.db.rollback()
            except Exception:
                pass
            messagebox.showerror("Database Error", str(e))
            return None

    # ========================================================
    # STYLE
    # ========================================================
    def setup_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("TEntry", padding=8, font=("Segoe UI", 11))
        style.configure("TCombobox", padding=7, font=("Segoe UI", 11))
        style.configure("TButton", font=("Segoe UI", 11, "bold"), padding=(14, 9))
        style.configure("Treeview", font=("Segoe UI", 10), rowheight=30)
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"), padding=7)
        style.configure("TNotebook.Tab", font=("Segoe UI", 10, "bold"), padding=(15, 8))
        style.map("TButton", background=[("active", "#dceaf5")])

    # ========================================================
    # GENERAL UI / NAVIGATION
    # ========================================================
    def clear_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()
        self.logo_photo = None
        self.bg_photo = None
        self.login_bg_label = None

    def navigate(self, page_function, record_history=True):
        if record_history and self.current_page:
            self.page_history.append(self.current_page)
        page_function(record_history=False)

    def go_back(self):
        if self.page_history:
            previous = self.page_history.pop()
            self._navigating_back = True
            try:
                previous_map = {
                    "login": self.show_login_screen,
                    "register": self.show_register_screen,
                    "dashboard": self.show_dashboard,
                    "lost_form": self.show_lost_form,
                    "found_form": self.show_found_form,
                    "lost_records": lambda record_history=False: self.show_records("Lost", record_history=record_history),
                    "found_records": lambda record_history=False: self.show_records("Found", record_history=record_history),
                    "search": self.show_search,
                    "my_reports": self.show_my_reports,
                    "admin_records": self.show_admin_records,
                    "details_lost": lambda record_history=False: self.show_dashboard(record_history=record_history),
                    "details_found": lambda record_history=False: self.show_dashboard(record_history=record_history),
                }
                func = previous_map.get(previous, self.show_dashboard)
                func(record_history=False)
            finally:
                self._navigating_back = False
        elif self.current_user:
            self.show_dashboard(record_history=False)
        else:
            self.show_login_screen(record_history=False)

    def begin_page(self, page_name, record_history=True):
        if record_history and self.current_page and self.current_page != page_name and not self._navigating_back:
            self.page_history.append(self.current_page)
        self.current_page = page_name
        self.clear_window()

    def load_logo(self, max_size=(100, 100)):
        if Image is None:
            return None
        path = BASE_DIR / LOGO_FILE
        if not path.exists():
            return None
        try:
            img = Image.open(path).convert("RGBA")
            img.thumbnail(max_size, Image.LANCZOS)
            self.logo_photo = ImageTk.PhotoImage(img)
            return self.logo_photo
        except Exception:
            return None

    def load_background(self):
        if Image is None:
            return None
        path = BASE_DIR / BACKGROUND_FILE
        if not path.exists():
            return None
        try:
            width = max(self.root.winfo_width(), 1050)
            height = max(self.root.winfo_height(), 700)
            img = Image.open(path).convert("RGB")
            img = ImageEnhance.Brightness(img).enhance(0.90)

            # Cover the available area without leaving large empty spaces.
            ratio = max(width / img.width, height / img.height)
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size, Image.LANCZOS)
            left = max((img.width - width) // 2, 0)
            top = max((img.height - height) // 2, 0)
            img = img.crop((left, top, left + width, top + height))
            self.bg_photo = ImageTk.PhotoImage(img)
            return self.bg_photo
        except Exception:
            return None

    def create_login_background(self):
        if Image is None or not (BASE_DIR / BACKGROUND_FILE).exists():
            return
        self.root.update_idletasks()
        photo = self.load_background()
        if photo:
            self.login_bg_label = tk.Label(self.root, image=photo, bd=0)
            self.login_bg_label.place(relx=0, rely=0, relwidth=1, relheight=1)
            self.login_bg_label.lower()

    def make_button(self, parent, text, command, bg_color=BLUE, fg=WHITE, width=None):
        options = {
            "text": text,
            "command": command,
            "font": ("Segoe UI", 11, "bold"),
            "bg": bg_color,
            "fg": fg,
            "activebackground": bg_color,
            "activeforeground": fg,
            "relief": "flat",
            "bd": 0,
            "cursor": "hand2",
            "padx": 14,
            "pady": 9,
        }
        if width:
            options["width"] = width
        return tk.Button(parent, **options)

    def create_header(self, parent, back_command=None, logout=False):
        header = tk.Frame(parent, bg=NAVY, height=135)
        header.pack(fill="x")
        header.pack_propagate(False)

        logo = self.load_logo((105, 105))
        if logo:
            tk.Label(header, image=logo, bg=NAVY, bd=0).pack(
                side="left", padx=(25, 18), pady=15
            )
        else:
            tk.Label(
                header, text="SCE", font=("Segoe UI", 26, "bold"),
                fg=WHITE, bg=NAVY
            ).pack(side="left", padx=(30, 20))

        title_box = tk.Frame(header, bg=NAVY)
        title_box.pack(side="left", fill="y", pady=25)
        tk.Label(
            title_box, text=COLLEGE_NAME,
            font=("Segoe UI", 25, "bold"), fg=WHITE, bg=NAVY
        ).pack(anchor="w")
        tk.Label(
            title_box, text=APP_TITLE,
            font=("Segoe UI", 13), fg="#dcebf7", bg=NAVY
        ).pack(anchor="w", pady=(7, 0))

        if logout:
            self.make_button(
                header, "Logout", self.logout, ORANGE, NAVY, width=10
            ).pack(side="right", padx=25, pady=38)
        elif back_command:
            self.make_button(
                header, "← Back", back_command, WHITE, NAVY, width=10
            ).pack(side="right", padx=25, pady=38)

    def create_page_body(self, title, subtitle=None, back_command=None, page_name=None):
        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True)

        self.create_header(
            body,
            back_command=back_command,
            logout=(back_command is None and self.current_user is not None),
        )

        content = tk.Frame(body, bg=BG)
        content.pack(fill="both", expand=True, padx=42, pady=25)

        tk.Label(
            content, text=title,
            font=("Segoe UI", 27, "bold"), fg=NAVY, bg=BG
        ).pack(anchor="w")
        if subtitle:
            tk.Label(
                content, text=subtitle,
                font=("Segoe UI", 12), fg=MUTED, bg=BG
            ).pack(anchor="w", pady=(6, 18))
        return content

    def add_entry(self, parent, label, row, col=0, colspan=1):
        box = tk.Frame(parent, bg=WHITE)
        box.grid(row=row, column=col, columnspan=colspan, sticky="ew", padx=16, pady=7)
        tk.Label(
            box, text=label, font=("Segoe UI", 10, "bold"),
            fg=TEXT, bg=WHITE
        ).pack(anchor="w", pady=(0, 4))
        entry = ttk.Entry(box)
        entry.pack(fill="x", ipady=3)
        return entry

    def show_password(self, entry, button):
        if entry.cget("show") == "*":
            entry.config(show="")
            button.config(text="Hide")
        else:
            entry.config(show="*")
            button.config(text="Show")

    # ========================================================
    # LOGIN
    # ========================================================
    def show_login_screen(self, record_history=True):
        self.begin_page("login", record_history)
        self.create_login_background()
        self.create_header(self.root)

        area = tk.Frame(self.root, bg=BG)
        area.pack(fill="both", expand=True, padx=55, pady=28)
        area.grid_columnconfigure(0, weight=1)
        area.grid_columnconfigure(1, weight=1)
        area.grid_rowconfigure(0, weight=1)

        left = tk.Frame(area, bg=TEAL)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 14))

        tk.Label(
            left,
            text="Together for a Safer\nand Stronger College Community",
            font=("Segoe UI", 23, "italic"),
            fg=WHITE, bg=TEAL, justify="center"
        ).pack(pady=(75, 25))

        tk.Label(
            left,
            text="Report lost items.\nFind missing belongings.\nHelp your college community.",
            font=("Segoe UI", 13), fg=WHITE, bg=TEAL,
            justify="center"
        ).pack(pady=10)

        tk.Label(
            left, text="4S: Stay Safe and Study Smart",
            font=("Segoe UI", 13, "bold"), fg="#ffd15c", bg=TEAL
        ).pack(side="bottom", pady=35)

        card = tk.Frame(area, bg=WHITE, highlightbackground=BORDER, highlightthickness=1)
        card.grid(row=0, column=1, sticky="nsew", padx=(14, 0))

        tk.Label(
            card, text="Welcome Back!",
            font=("Segoe UI", 25, "bold"), fg=NAVY, bg=WHITE
        ).pack(pady=(48, 4))
        tk.Label(
            card, text="Login to continue",
            font=("Segoe UI", 12), fg=MUTED, bg=WHITE
        ).pack(pady=(0, 22))

        form = tk.Frame(card, bg=WHITE)
        form.pack(fill="x", padx=60)

        tk.Label(form, text="Username", font=("Segoe UI", 11, "bold"), fg=TEXT, bg=WHITE).pack(anchor="w")
        username = ttk.Entry(form)
        username.pack(fill="x", pady=(6, 18), ipady=4)

        tk.Label(form, text="Password", font=("Segoe UI", 11, "bold"), fg=TEXT, bg=WHITE).pack(anchor="w")
        pwrow = tk.Frame(form, bg=WHITE)
        pwrow.pack(fill="x", pady=(6, 18))
        password = ttk.Entry(pwrow, show="*")
        password.pack(side="left", fill="x", expand=True, ipady=4)
        show_btn = self.make_button(
            pwrow, "Show", lambda: self.show_password(password, show_btn),
            LIGHT_BLUE, NAVY, width=7
        )
        show_btn.pack(side="left", padx=(8, 0))

        self.make_button(
            form, "LOGIN",
            lambda: self.login(username.get(), password.get()),
            NAVY, WHITE
        ).pack(fill="x", pady=4, ipady=2)

        self.make_button(
            form, "Create New Account",
            lambda: self.navigate(self.show_register_screen),
            WHITE, BLUE
        ).pack(fill="x", pady=(9, 8))

        default_box = tk.Frame(card, bg=LIGHT_BLUE)
        default_box.pack(side="bottom", fill="x", padx=35, pady=18)
        tk.Label(
            default_box,
            text="DEFAULT ADMINISTRATOR",
            font=("Segoe UI", 9, "bold"), fg=NAVY, bg=LIGHT_BLUE
        ).pack(pady=(9, 2))
        tk.Label(
            default_box,
            text=f"Username: {DEFAULT_ADMIN_USERNAME}   |   Password: {DEFAULT_ADMIN_PASSWORD}",
            font=("Segoe UI", 9), fg=MUTED, bg=LIGHT_BLUE
        ).pack(pady=(0, 9))

        username.focus_set()
        password.bind("<Return>", lambda e: self.login(username.get(), password.get()))

    def login(self, username, password):
        username = username.strip()
        if not username or not password:
            messagebox.showwarning("Login", "Please enter both username and password.")
            return

        rows = self.db_query("SELECT * FROM Users WHERE username=%s", (username,))
        if rows:
            user = rows[0]
            try:
                valid = bcrypt.checkpw(
                    password.encode("utf-8"),
                    user["password_hash"].encode("utf-8")
                )
            except Exception:
                valid = False
            if valid:
                self.current_user = user
                self.current_role = user["role"]
                self.page_history.clear()
                self.show_dashboard(record_history=False)
                return

        messagebox.showerror("Login Failed", "Incorrect username or password.")

    # ========================================================
    # REGISTRATION
    # ========================================================
    def show_register_screen(self, record_history=True):
        self.begin_page("register", record_history)
        content = self.create_page_body(
            "Create New Account",
            "Register to use the lost and found system.",
            self.go_back
        )

        # Scrollable registration area so buttons never disappear.
        scroll_frame, inner, _ = self.create_scrollable_area(content)
        card = tk.Frame(inner, bg=WHITE, highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="x", padx=50, pady=5)
        card.grid_columnconfigure(0, weight=1)
        card.grid_columnconfigure(1, weight=1)

        full_name = self.add_entry(card, "Full Name", 0, 0, 2)
        username = self.add_entry(card, "Username", 1, 0)
        email = self.add_entry(card, "Email", 1, 1)

        tk.Label(card, text="Password", font=("Segoe UI", 10, "bold"), fg=TEXT, bg=WHITE).grid(
            row=2, column=0, sticky="w", padx=16, pady=(8, 4)
        )
        pw_frame = tk.Frame(card, bg=WHITE)
        pw_frame.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 8))
        password = ttk.Entry(pw_frame, show="*")
        password.pack(side="left", fill="x", expand=True, ipady=3)
        pw_show = self.make_button(
            pw_frame, "Show", lambda: self.show_password(password, pw_show),
            LIGHT_BLUE, NAVY, width=7
        )
        pw_show.pack(side="left", padx=(8, 0))

        tk.Label(card, text="Confirm Password", font=("Segoe UI", 10, "bold"), fg=TEXT, bg=WHITE).grid(
            row=2, column=1, sticky="w", padx=16, pady=(8, 4)
        )
        cp_frame = tk.Frame(card, bg=WHITE)
        cp_frame.grid(row=3, column=1, sticky="ew", padx=16, pady=(0, 8))
        confirm = ttk.Entry(cp_frame, show="*")
        confirm.pack(side="left", fill="x", expand=True, ipady=3)
        cp_show = self.make_button(
            cp_frame, "Show", lambda: self.show_password(confirm, cp_show),
            LIGHT_BLUE, NAVY, width=7
        )
        cp_show.pack(side="left", padx=(8, 0))

        tk.Label(
            card,
            text="Password must contain at least 6 characters.",
            font=("Segoe UI", 9), fg=MUTED, bg=WHITE
        ).grid(row=4, column=0, columnspan=2, sticky="w", padx=16, pady=(0, 8))

        buttons = tk.Frame(card, bg=WHITE)
        buttons.grid(row=5, column=0, columnspan=2, pady=20)
        self.make_button(
            buttons, "← Back to Login", self.go_back,
            WHITE, NAVY, width=18
        ).pack(side="left", padx=6)
        self.make_button(
            buttons, "CREATE ACCOUNT",
            lambda: self.register(
                full_name.get(), username.get(), email.get(),
                password.get(), confirm.get()
            ),
            GREEN, WHITE, width=20
        ).pack(side="left", padx=6)

        full_name.focus_set()

    def register(self, full_name, username, email, password, confirm):
        full_name = full_name.strip()
        username = username.strip()
        email = email.strip().lower()

        if not all([full_name, username, email, password, confirm]):
            messagebox.showwarning("Registration", "Please complete all fields.")
            return
        if len(full_name) < 2:
            messagebox.showwarning("Registration", "Please enter your full name.")
            return
        if len(username) < 3 or not re.match(r"^[A-Za-z0-9_.-]+$", username):
            messagebox.showwarning(
                "Registration",
                "Username must contain at least 3 characters and use only letters, numbers, _, ., or -."
            )
            return
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            messagebox.showwarning("Registration", "Please enter a valid email address.")
            return
        if len(password) < 6:
            messagebox.showwarning("Registration", "Password must contain at least 6 characters.")
            return
        if password != confirm:
            messagebox.showerror("Registration", "Passwords do not match.")
            return

        existing = self.db_query(
            "SELECT id FROM Users WHERE username=%s OR email=%s",
            (username, email)
        )
        if existing:
            messagebox.showerror("Registration", "Username or email already exists.")
            return

        try:
            hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            result = self.db_action(
                """
                INSERT INTO Users
                (full_name, username, email, password_hash, role)
                VALUES (%s,%s,%s,%s,'User')
                """,
                (full_name, username, email, hashed)
            )
            if result is not None:
                messagebox.showinfo(
                    "Account Created",
                    "Your account has been created successfully.\n\nYou can now login."
                )
                self.page_history.clear()
                self.show_login_screen(record_history=False)
        except Exception as e:
            messagebox.showerror("Registration Error", str(e))

    # ========================================================
    # SCROLLABLE AREA
    # ========================================================
    def create_scrollable_area(self, parent):
        outer = tk.Frame(parent, bg=BG)
        outer.pack(fill="both", expand=True)

        canvas = tk.Canvas(outer, bg=BG, highlightthickness=0, bd=0)
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=BG)

        window_id = canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        def configure_inner(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfigure(window_id, width=event.width)

        inner.bind("<Configure>", configure_inner)
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(window_id, width=event.width))

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Mouse-wheel support only while the pointer is over this page.
        # Using bind_all here can leave callbacks attached to destroyed pages.
        def wheel(event):
            try:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except tk.TclError:
                pass

        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", wheel))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))
        return outer, inner, canvas

    # ========================================================
    # DASHBOARD
    # ========================================================
    def show_dashboard(self, record_history=True):
        self.begin_page("dashboard", record_history)
        self.create_header(self.root, logout=True)

        outer = tk.Frame(self.root, bg=BG)
        outer.pack(fill="both", expand=True, padx=45, pady=28)

        name = self.current_user["full_name"] if self.current_user else "User"
        role = self.current_role or "User"

        tk.Label(
            outer, text=f"Welcome, {name}!",
            font=("Segoe UI", 27, "bold"), fg=NAVY, bg=BG
        ).pack(anchor="w")
        tk.Label(
            outer, text=f"Account type: {role}",
            font=("Segoe UI", 12), fg=MUTED, bg=BG
        ).pack(anchor="w", pady=(4, 20))

        card = tk.Frame(outer, bg=WHITE, highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="x", padx=30)

        tk.Label(
            card, text="Main Functions",
            font=("Segoe UI", 20, "bold"), fg=NAVY, bg=WHITE
        ).pack(anchor="w", padx=32, pady=(24, 17))

        grid = tk.Frame(card, bg=WHITE)
        grid.pack(fill="x", padx=25, pady=(0, 25))
        for c in range(3):
            grid.grid_columnconfigure(c, weight=1)

        buttons = [
            ("Report Lost Item", self.show_lost_form, BLUE),
            ("Report Found Item", self.show_found_form, TEAL),
            ("View Lost Items", lambda: self.show_records("Lost"), PURPLE),
            ("View Found Items", lambda: self.show_records("Found"), ORANGE),
            ("Search Records", self.show_search, BLUE),
            ("My Reports", self.show_my_reports, TEAL),
        ]

        for i, (text, command, color) in enumerate(buttons):
            r, c = divmod(i, 3)
            self.make_button(grid, text, command, color, WHITE).grid(
                row=r, column=c, sticky="ew", padx=8, pady=8, ipady=13
            )

        info = tk.Frame(outer, bg=LIGHT_BLUE)
        info.pack(fill="x", padx=30, pady=16)
        tk.Label(
            info, text="4S: Stay Safe and Study Smart",
            font=("Segoe UI", 14, "bold"), fg=NAVY, bg=LIGHT_BLUE
        ).pack(pady=(12, 4))
        tk.Label(
            info,
            text="Use accurate item details and contact information so missing belongings can be returned safely.",
            font=("Segoe UI", 10), fg=MUTED, bg=LIGHT_BLUE
        ).pack(pady=(0, 12))

        if self.current_role == "Administrator":
            self.make_button(
                outer, "Administrator: Manage All Records",
                self.show_admin_records, NAVY, WHITE
            ).pack(pady=3)

    # ========================================================
    # REPORT LOST / FOUND
    # ========================================================
    def show_lost_form(self, record_history=True):
        self.show_item_form("Lost", record_history=record_history)

    def show_found_form(self, record_history=True):
        self.show_item_form("Found", record_history=record_history)

    def show_item_form(self, item_type, edit_data=None, record_history=True):
        page_name = "lost_form" if item_type == "Lost" else "found_form"
        if edit_data:
            page_name = "edit_lost" if item_type == "Lost" else "edit_found"

        self.begin_page(page_name, record_history)
        title = f"Report {item_type} Item" if edit_data is None else f"Update {item_type} Item"
        subtitle = (
            f"Enter the details of the item you {item_type.lower()}."
            if edit_data is None
            else "Update the information below and save your changes."
        )

        content = self.create_page_body(title, subtitle, self.go_back)

        # Main scroll area. Buttons are INSIDE the card and remain reachable.
        _, inner, canvas = self.create_scrollable_area(content)

        card = tk.Frame(inner, bg=WHITE, highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="x", padx=35, pady=5)
        card.grid_columnconfigure(0, weight=1)
        card.grid_columnconfigure(1, weight=1)

        item_name = self.add_entry(card, "Item Name", 0, 0)
        location = self.add_entry(card, "Location", 0, 1)

        tk.Label(card, text="Category", font=("Segoe UI", 10, "bold"), fg=TEXT, bg=WHITE).grid(
            row=1, column=0, sticky="w", padx=16, pady=(8, 4)
        )
        category = ttk.Combobox(card, values=CATEGORIES, state="readonly")
        category.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 8))
        category.set(CATEGORIES[0])

        tk.Label(card, text="Date (YYYY-MM-DD)", font=("Segoe UI", 10, "bold"), fg=TEXT, bg=WHITE).grid(
            row=1, column=1, sticky="w", padx=16, pady=(8, 4)
        )
        date_entry = ttk.Entry(card)
        date_entry.grid(row=2, column=1, sticky="ew", padx=16, pady=(0, 8), ipady=3)
        date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))

        tk.Label(card, text="Description", font=("Segoe UI", 10, "bold"), fg=TEXT, bg=WHITE).grid(
            row=3, column=0, columnspan=2, sticky="w", padx=16, pady=(8, 4)
        )
        description = tk.Text(
            card, height=4, font=("Segoe UI", 11),
            relief="solid", bd=1, wrap="word"
        )
        description.grid(row=4, column=0, columnspan=2, sticky="ew", padx=16, pady=(0, 8))

        contact = self.add_entry(card, "Contact Information (phone/email)", 5, 0, 2)

        if edit_data:
            item_name.insert(0, edit_data["item_name"])
            location.insert(0, edit_data["location"])
            category.set(edit_data["category"])
            date_entry.delete(0, "end")
            date_entry.insert(0, str(edit_data["item_date"]))
            description.insert("1.0", edit_data["description"])
            contact.insert(0, edit_data["contact"])

        # Button bar is part of the scrollable card, so it can never be
        # permanently hidden below the screen.
        buttons = tk.Frame(card, bg=WHITE)
        buttons.grid(row=6, column=0, columnspan=2, pady=18)

        self.make_button(buttons, "← Back", self.go_back, WHITE, NAVY, width=13).pack(side="left", padx=6)
        self.make_button(
            buttons, "Clear",
            lambda: self.clear_item_form(
                item_name, location, category, date_entry, description, contact
            ),
            ORANGE, NAVY, width=13
        ).pack(side="left", padx=6)

        action_text = "SUBMIT REPORT" if edit_data is None else "SAVE CHANGES"
        self.make_button(
            buttons, action_text,
            lambda: self.save_item(
                item_type,
                item_name.get(),
                category.get(),
                description.get("1.0", "end").strip(),
                location.get(),
                date_entry.get(),
                contact.get(),
                edit_data,
            ),
            GREEN, WHITE, width=20
        ).pack(side="left", padx=6)

        # Start at top.
        canvas.yview_moveto(0)
        item_name.focus_set()

    def clear_item_form(self, item_name, location, category, date_entry, description, contact):
        for e in (item_name, location, date_entry, contact):
            e.delete(0, "end")
        category.set(CATEGORIES[0])
        description.delete("1.0", "end")
        date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        item_name.focus_set()

    def save_item(self, item_type, item_name, category, description, location, item_date, contact, edit_data=None):
        values = [item_name.strip(), category.strip(), description.strip(), location.strip(), item_date.strip(), contact.strip()]
        if not all(values):
            messagebox.showwarning("Required Fields", "Please complete all fields before submitting.")
            return

        try:
            datetime.strptime(item_date.strip(), "%Y-%m-%d")
        except ValueError:
            messagebox.showwarning("Invalid Date", "Use the date format YYYY-MM-DD.")
            return

        if not self.current_user:
            messagebox.showerror("Login Required", "Please login before submitting a report.")
            return

        table = "Lost_items" if item_type == "Lost" else "Found_items"
        status = item_type

        if edit_data:
            # Users can edit their own reports; administrators can edit any report.
            if self.current_role == "Administrator":
                where = "WHERE id=%s"
                params = (
                    item_name.strip(), category, description.strip(), location.strip(),
                    item_date.strip(), status, contact.strip(), edit_data["id"]
                )
            else:
                where = "WHERE id=%s AND reported_by=%s"
                params = (
                    item_name.strip(), category, description.strip(), location.strip(),
                    item_date.strip(), status, contact.strip(),
                    edit_data["id"], self.current_user["id"]
                )

            result = self.db_action(
                f"""
                UPDATE {table}
                SET item_name=%s, category=%s, description=%s, location=%s,
                    item_date=%s, status=%s, contact=%s
                {where}
                """,
                params
            )
            if result is not None:
                messagebox.showinfo("Updated", f"{item_type} item updated successfully.")
                self.page_history.clear()
                self.show_my_reports(record_history=False) if self.current_role != "Administrator" else self.show_admin_records(record_history=False)
        else:
            prefix = "L" if item_type == "Lost" else "F"
            item_no = f"{prefix}-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
            result = self.db_action(
                f"""
                INSERT INTO {table}
                (item_no, item_name, category, description, location,
                 item_date, status, contact, reported_by)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    item_no, item_name.strip(), category, description.strip(),
                    location.strip(), item_date.strip(), status, contact.strip(),
                    self.current_user["id"]
                )
            )
            if result is not None:
                messagebox.showinfo(
                    "Report Submitted",
                    f"{item_type} item reported successfully.\n\nItem No.: {item_no}"
                )
                self.page_history.clear()
                self.show_dashboard(record_history=False)

    # ========================================================
    # RECORDS
    # ========================================================
    def show_records(self, item_type="Lost", back_command=None, record_history=True):
        page_name = "lost_records" if item_type == "Lost" else "found_records"
        self.begin_page(page_name, record_history)
        content = self.create_page_body(
            f"{item_type} Items",
            f"All currently recorded {item_type.lower()} items.",
            self.go_back
        )

        toolbar = tk.Frame(content, bg=BG)
        toolbar.pack(fill="x", pady=(0, 10))
        self.make_button(
            toolbar, "↻ Refresh",
            lambda: self.show_records(item_type, record_history=False),
            BLUE, WHITE
        ).pack(side="left")

        frame = tk.Frame(content, bg=WHITE, highlightbackground=BORDER, highlightthickness=1)
        frame.pack(fill="both", expand=True)

        cols = ("item_no", "item_name", "category", "description", "location", "date", "status", "contact")
        tree = ttk.Treeview(frame, columns=cols, show="headings")
        headings = {
            "item_no": "Item No.", "item_name": "Item Name", "category": "Category",
            "description": "Description", "location": "Location", "date": "Date",
            "status": "Status", "contact": "Contact"
        }
        widths = {
            "item_no": 150, "item_name": 150, "category": 130,
            "description": 260, "location": 150, "date": 105,
            "status": 80, "contact": 170
        }
        for col in cols:
            tree.heading(col, text=headings[col])
            tree.column(col, width=widths[col], anchor="w")

        yscroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        xscroll = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        table = "Lost_items" if item_type == "Lost" else "Found_items"
        rows = self.db_query(f"SELECT * FROM {table} ORDER BY created_at DESC")
        for row in rows:
            tree.insert(
                "", "end", iid=str(row["id"]),
                values=(
                    row["item_no"], row["item_name"], row["category"],
                    row["description"], row["location"], row["item_date"],
                    row["status"], row["contact"]
                )
            )

        action = tk.Frame(content, bg=BG)
        action.pack(fill="x", pady=10)
        self.make_button(action, "View Selected", lambda: self.view_selected(tree, item_type), BLUE, WHITE).pack(side="left")
        if self.current_role == "Administrator":
            self.make_button(action, "Edit Selected", lambda: self.edit_admin_selected(tree, item_type), GREEN, WHITE).pack(side="left", padx=8)
            self.make_button(action, "Delete Selected", lambda: self.delete_selected(tree, item_type), RED, WHITE).pack(side="left")
        self.make_button(action, "← Back", self.go_back, WHITE, NAVY).pack(side="right")

        if not rows:
            tk.Label(
                frame, text=f"No {item_type.lower()} items have been reported yet.",
                font=("Segoe UI", 12), fg=MUTED, bg=WHITE
            ).place(relx=0.5, rely=0.5, anchor="center")

    def view_selected(self, tree, item_type):
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("Select Record", "Please select a record first.")
            return
        table = "Lost_items" if item_type == "Lost" else "Found_items"
        rows = self.db_query(f"SELECT * FROM {table} WHERE id=%s", (int(selected[0]),))
        if rows:
            self.show_item_details(rows[0], item_type)

    def show_item_details(self, row, item_type, record_history=True):
        self.begin_page(f"details_{item_type.lower()}", record_history)
        content = self.create_page_body(
            "Item Details",
            f"Details of the selected {item_type.lower()} item.",
            self.go_back
        )

        _, inner, _ = self.create_scrollable_area(content)
        card = tk.Frame(inner, bg=WHITE, highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="x", padx=70, pady=5)
        card.grid_columnconfigure(1, weight=1)

        details = [
            ("Item No.", row["item_no"]),
            ("Item Name", row["item_name"]),
            ("Category", row["category"]),
            ("Location", row["location"]),
            ("Date", str(row["item_date"])),
            ("Status", row["status"]),
            ("Contact", row["contact"]),
            ("Description", row["description"]),
        ]
        for i, (label, value) in enumerate(details):
            tk.Label(
                card, text=label,
                font=("Segoe UI", 10, "bold"), fg=MUTED, bg=WHITE
            ).grid(row=i, column=0, sticky="nw", padx=25, pady=9)
            tk.Label(
                card, text=value,
                font=("Segoe UI", 11), fg=TEXT, bg=WHITE,
                wraplength=720, justify="left"
            ).grid(row=i, column=1, sticky="w", padx=25, pady=9)

        self.make_button(content, "← Back", self.go_back, WHITE, NAVY, width=15).pack(pady=10)

    def delete_selected(self, tree, item_type):
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("Select Record", "Please select a record first.")
            return
        if not messagebox.askyesno("Confirm Delete", "Delete the selected record permanently?"):
            return
        table = "Lost_items" if item_type == "Lost" else "Found_items"
        result = self.db_action(f"DELETE FROM {table} WHERE id=%s", (int(selected[0]),))
        if result is not None:
            messagebox.showinfo("Deleted", "Record deleted successfully.")
            self.show_records(item_type, record_history=False)

    # ========================================================
    # SEARCH
    # ========================================================
    def show_search(self, record_history=True):
        self.begin_page("search", record_history)
        content = self.create_page_body(
            "Search Records",
            "Search lost and found items by item number, name, category or location.",
            self.go_back
        )

        search_card = tk.Frame(content, bg=WHITE, highlightbackground=BORDER, highlightthickness=1)
        search_card.pack(fill="x", pady=(0, 12))
        search_card.grid_columnconfigure(1, weight=1)

        tk.Label(search_card, text="Search", font=("Segoe UI", 10, "bold"), fg=TEXT, bg=WHITE).grid(
            row=0, column=0, padx=(18, 7), pady=15
        )
        search_entry = ttk.Entry(search_card)
        search_entry.grid(row=0, column=1, sticky="ew", padx=7, pady=15, ipady=4)

        tk.Label(search_card, text="Type", font=("Segoe UI", 10, "bold"), fg=TEXT, bg=WHITE).grid(
            row=0, column=2, padx=(14, 7)
        )
        type_box = ttk.Combobox(search_card, values=["All", "Lost", "Found"], state="readonly", width=12)
        type_box.set("All")
        type_box.grid(row=0, column=3, padx=7, pady=15)

        frame = tk.Frame(content, bg=WHITE, highlightbackground=BORDER, highlightthickness=1)
        frame.pack(fill="both", expand=True)
        cols = ("item_no", "type", "item_name", "category", "location", "date", "contact")
        tree = ttk.Treeview(frame, columns=cols, show="headings")
        heads = {
            "item_no": "Item No.", "type": "Type", "item_name": "Item Name",
            "category": "Category", "location": "Location", "date": "Date", "contact": "Contact"
        }
        widths = {"item_no": 160, "type": 80, "item_name": 160, "category": 140, "location": 160, "date": 110, "contact": 180}
        for c in cols:
            tree.heading(c, text=heads[c])
            tree.column(c, width=widths[c], anchor="w")
        ys = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        xs = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
        tree.grid(row=0, column=0, sticky="nsew")
        ys.grid(row=0, column=1, sticky="ns")
        xs.grid(row=1, column=0, sticky="ew")
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        bottom = tk.Frame(content, bg=BG)
        bottom.pack(fill="x", pady=10)
        self.make_button(
            search_card, "SEARCH",
            lambda: self.perform_search(search_entry.get(), type_box.get(), tree),
            BLUE, WHITE, width=12
        ).grid(row=0, column=4, padx=7, pady=15)
        self.make_button(
            search_card, "CLEAR",
            lambda: self.clear_search(search_entry, type_box, tree),
            ORANGE, NAVY, width=10
        ).grid(row=0, column=5, padx=(0, 18), pady=15)

        self.make_button(bottom, "View Selected", lambda: self.view_search_selected(tree), BLUE, WHITE).pack(side="left")
        self.make_button(bottom, "← Back", self.go_back, WHITE, NAVY).pack(side="right")

        search_entry.focus_set()
        search_entry.bind("<Return>", lambda e: self.perform_search(search_entry.get(), type_box.get(), tree))

    def perform_search(self, term, item_type, tree):
        for item in tree.get_children():
            tree.delete(item)

        term = term.strip()
        like = f"%{term}%"
        results = []
        tables = (
            [("Lost_items", "Lost")] if item_type == "Lost"
            else [("Found_items", "Found")] if item_type == "Found"
            else [("Lost_items", "Lost"), ("Found_items", "Found")]
        )

        for table, typ in tables:
            rows = self.db_query(
                f"""
                SELECT id, item_no, item_name, category, location, item_date, contact
                FROM {table}
                WHERE item_no LIKE %s
                   OR item_name LIKE %s
                   OR category LIKE %s
                   OR location LIKE %s
                ORDER BY created_at DESC
                """,
                (like, like, like, like)
            )
            for row in rows:
                row["type"] = typ
                results.append(row)

        for row in results:
            tree.insert(
                "", "end", iid=f"{row['type']}_{row['id']}",
                values=(
                    row["item_no"], row["type"], row["item_name"],
                    row["category"], row["location"], row["item_date"], row["contact"]
                )
            )

        if not results:
            messagebox.showinfo("Search", "No matching records found.")

    def clear_search(self, entry, type_box, tree):
        entry.delete(0, "end")
        type_box.set("All")
        for item in tree.get_children():
            tree.delete(item)
        entry.focus_set()

    def view_search_selected(self, tree):
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("Select Record", "Please select a record first.")
            return
        typ, rid = selected[0].split("_", 1)
        table = "Lost_items" if typ == "Lost" else "Found_items"
        rows = self.db_query(f"SELECT * FROM {table} WHERE id=%s", (int(rid),))
        if rows:
            self.show_item_details(rows[0], typ)

    # ========================================================
    # MY REPORTS
    # ========================================================
    def show_my_reports(self, record_history=True):
        self.begin_page("my_reports", record_history)
        content = self.create_page_body(
            "My Reports",
            "View, edit and delete the reports submitted by your account.",
            self.go_back
        )

        frame = tk.Frame(content, bg=WHITE, highlightbackground=BORDER, highlightthickness=1)
        frame.pack(fill="both", expand=True)
        cols = ("item_no", "type", "item_name", "category", "location", "date", "status")
        tree = ttk.Treeview(frame, columns=cols, show="headings")
        widths = {"item_no": 160, "type": 80, "item_name": 160, "category": 140, "location": 160, "date": 110, "status": 90}
        for c in cols:
            tree.heading(c, text=c.replace("_", " ").title())
            tree.column(c, width=widths[c], anchor="w")
        ys = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=ys.set)
        tree.grid(row=0, column=0, sticky="nsew")
        ys.grid(row=0, column=1, sticky="ns")
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        total = 0
        for table, typ in [("Lost_items", "Lost"), ("Found_items", "Found")]:
            rows = self.db_query(
                f"SELECT * FROM {table} WHERE reported_by=%s ORDER BY created_at DESC",
                (self.current_user["id"],)
            )
            for row in rows:
                total += 1
                tree.insert(
                    "", "end", iid=f"{typ}_{row['id']}",
                    values=(
                        row["item_no"], typ, row["item_name"], row["category"],
                        row["location"], row["item_date"], row["status"]
                    )
                )

        buttons = tk.Frame(content, bg=BG)
        buttons.pack(fill="x", pady=10)
        self.make_button(buttons, "View Selected", lambda: self.view_my_report(tree), BLUE, WHITE).pack(side="left")
        self.make_button(buttons, "Edit Selected", lambda: self.edit_my_report(tree), GREEN, WHITE).pack(side="left", padx=8)
        self.make_button(buttons, "Delete Selected", lambda: self.delete_my_report(tree), RED, WHITE).pack(side="left")
        self.make_button(buttons, "← Back", self.go_back, WHITE, NAVY).pack(side="right")

        if total == 0:
            tk.Label(
                frame, text="You have not submitted any reports yet.",
                font=("Segoe UI", 12), fg=MUTED, bg=WHITE
            ).place(relx=0.5, rely=0.5, anchor="center")

    def get_type_and_id(self, tree):
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("Select Record", "Please select a report first.")
            return None, None
        typ, rid = selected[0].split("_", 1)
        return typ, int(rid)

    def view_my_report(self, tree):
        typ, rid = self.get_type_and_id(tree)
        if not typ:
            return
        table = "Lost_items" if typ == "Lost" else "Found_items"
        rows = self.db_query(
            f"SELECT * FROM {table} WHERE id=%s AND reported_by=%s",
            (rid, self.current_user["id"])
        )
        if rows:
            self.show_item_details(rows[0], typ)

    def edit_my_report(self, tree):
        typ, rid = self.get_type_and_id(tree)
        if not typ:
            return
        table = "Lost_items" if typ == "Lost" else "Found_items"
        rows = self.db_query(
            f"SELECT * FROM {table} WHERE id=%s AND reported_by=%s",
            (rid, self.current_user["id"])
        )
        if rows:
            self.page_history.append("my_reports")
            self.show_item_form(typ, rows[0], record_history=False)

    def delete_my_report(self, tree):
        typ, rid = self.get_type_and_id(tree)
        if not typ:
            return
        if not messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this report?"):
            return
        table = "Lost_items" if typ == "Lost" else "Found_items"
        result = self.db_action(
            f"DELETE FROM {table} WHERE id=%s AND reported_by=%s",
            (rid, self.current_user["id"])
        )
        if result is not None:
            messagebox.showinfo("Deleted", "Report deleted successfully.")
            self.show_my_reports(record_history=False)

    # ========================================================
    # ADMIN
    # ========================================================
    def show_admin_records(self, record_history=True):
        if self.current_role != "Administrator":
            messagebox.showerror("Access Denied", "Administrator access is required.")
            return

        self.begin_page("admin_records", record_history)
        content = self.create_page_body(
            "Administrator Records",
            "Manage all lost and found reports submitted by users.",
            self.go_back
        )

        tabs = ttk.Notebook(content)
        tabs.pack(fill="both", expand=True)

        lost_tab = tk.Frame(tabs, bg=WHITE)
        found_tab = tk.Frame(tabs, bg=WHITE)
        tabs.add(lost_tab, text="Lost Items")
        tabs.add(found_tab, text="Found Items")

        self.build_admin_tree(lost_tab, "Lost")
        self.build_admin_tree(found_tab, "Found")

        self.make_button(content, "← Back to Dashboard", self.go_back, WHITE, NAVY).pack(pady=10)

    def build_admin_tree(self, parent, item_type):
        cols = ("item_no", "item_name", "category", "location", "date", "contact", "reported_by")
        tree = ttk.Treeview(parent, columns=cols, show="headings")
        headings = {
            "item_no": "Item No.", "item_name": "Item Name", "category": "Category",
            "location": "Location", "date": "Date", "contact": "Contact", "reported_by": "Reported By"
        }
        for c in cols:
            tree.heading(c, text=headings[c])
            tree.column(c, width=145, anchor="w")

        ys = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        xs = ttk.Scrollbar(parent, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
        tree.grid(row=0, column=0, sticky="nsew", padx=(10, 0), pady=10)
        ys.grid(row=0, column=1, sticky="ns", pady=10)
        xs.grid(row=1, column=0, sticky="ew", padx=(10, 0))
        parent.grid_rowconfigure(0, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        table = "Lost_items" if item_type == "Lost" else "Found_items"
        rows = self.db_query(
            f"""
            SELECT i.*, u.username
            FROM {table} i
            JOIN Users u ON i.reported_by=u.id
            ORDER BY i.created_at DESC
            """
        )
        for row in rows:
            tree.insert(
                "", "end", iid=str(row["id"]),
                values=(
                    row["item_no"], row["item_name"], row["category"],
                    row["location"], row["item_date"], row["contact"], row["username"]
                )
            )

        btn = tk.Frame(parent, bg=WHITE)
        btn.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=10)
        self.make_button(btn, "View", lambda: self.view_admin_selected(tree, item_type), BLUE, WHITE).pack(side="left")
        self.make_button(btn, "Edit", lambda: self.edit_admin_selected(tree, item_type), GREEN, WHITE).pack(side="left", padx=8)
        self.make_button(btn, "Delete", lambda: self.delete_admin_selected(tree, item_type), RED, WHITE).pack(side="left")

        if not rows:
            tk.Label(
                parent, text=f"No {item_type.lower()} records found.",
                font=("Segoe UI", 11), fg=MUTED, bg=WHITE
            ).place(relx=0.5, rely=0.5, anchor="center")

    def admin_selected_id(self, tree):
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("Select Record", "Please select a record first.")
            return None
        return int(selected[0])

    def view_admin_selected(self, tree, item_type):
        rid = self.admin_selected_id(tree)
        if rid is None:
            return
        table = "Lost_items" if item_type == "Lost" else "Found_items"
        rows = self.db_query(f"SELECT * FROM {table} WHERE id=%s", (rid,))
        if rows:
            self.show_item_details(rows[0], item_type)

    def edit_admin_selected(self, tree, item_type):
        rid = self.admin_selected_id(tree)
        if rid is None:
            return
        table = "Lost_items" if item_type == "Lost" else "Found_items"
        rows = self.db_query(f"SELECT * FROM {table} WHERE id=%s", (rid,))
        if rows:
            self.page_history.append("admin_records")
            self.show_item_form(item_type, rows[0], record_history=False)

    def delete_admin_selected(self, tree, item_type):
        rid = self.admin_selected_id(tree)
        if rid is None:
            return
        if not messagebox.askyesno("Confirm Delete", "Delete the selected record permanently?"):
            return
        table = "Lost_items" if item_type == "Lost" else "Found_items"
        result = self.db_action(f"DELETE FROM {table} WHERE id=%s", (rid,))
        if result is not None:
            messagebox.showinfo("Deleted", "Record deleted successfully.")
            self.show_admin_records(record_history=False)

    # ========================================================
    # LOGOUT / CLOSE
    # ========================================================
    def logout(self):
        if messagebox.askyesno("Logout", "Are you sure you want to logout?"):
            self.current_user = None
            self.current_role = None
            self.page_history.clear()
            self.show_login_screen(record_history=False)

    def on_close(self):
        try:
            if self.db and self.db.is_connected():
                self.db.close()
        except Exception:
            pass
        self.root.destroy()


# ============================================================
# MAIN
# ============================================================
def main():
    root = tk.Tk()
    app = LostFoundSystem(root)
    root.mainloop()


if __name__ == "__main__":
    main()
