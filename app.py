from flask import Flask, request, redirect, url_for, session, render_template_string
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "change-this-secret-key-before-deployment"

DATABASE = "students.db"


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                branch TEXT NOT NULL,
                cgpa REAL NOT NULL
            )
        """)


PAGE_STYLE = """
<style>
body {
    font-family: Arial, sans-serif;
    background: #eef2ff;
    margin: 0;
    padding: 35px 15px;
}
.card {
    background: white;
    max-width: 450px;
    margin: auto;
    padding: 28px;
    border-radius: 14px;
    box-shadow: 0 5px 20px #0001;
}
h1, h2 { color: #253575; }
input, select, button {
    box-sizing: border-box;
    width: 100%;
    padding: 12px;
    margin: 8px 0;
    border: 1px solid #ccd2e5;
    border-radius: 6px;
}
button, .button {
    background: #3449a3;
    color: white;
    border: none;
    cursor: pointer;
    text-decoration: none;
    display: inline-block;
    padding: 12px;
    border-radius: 6px;
}
a { color: #3449a3; }
.message { color: #b42318; }
</style>
"""


@app.route("/")
def home():
    return render_template_string(PAGE_STYLE + """
    <div class="card">
        <h1>Student Placement Portal</h1>
        <p>Manage your student profile and placement details.</p>
        <a class="button" href="{{ url_for('register') }}">Student Registration</a>
        <a class="button" href="{{ url_for('login') }}">Student Login</a>
    </div>
    """)


@app.route("/register", methods=["GET", "POST"])
def register():
    message = ""

    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        branch = request.form["branch"]
        try:
            cgpa = float(request.form["cgpa"])
        except ValueError:
            cgpa = -1

        if not name or len(password) < 8 or not branch or not 0 <= cgpa <= 10:
            message = "Enter valid details. Password must have at least 8 characters and CGPA must be 0–10."
        else:
            try:
                with get_db() as conn:
                    conn.execute("""
                        INSERT INTO students (name, email, password, branch, cgpa)
                        VALUES (?, ?, ?, ?, ?)
                    """, (name, email, generate_password_hash(password), branch, cgpa))
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                message = "This email is already registered."

    return render_template_string(PAGE_STYLE + """
    <div class="card">
        <h2>Student Registration</h2>
        <p class="message">{{ message }}</p>
        <form method="post">
            <input name="name" placeholder="Full name" required>
            <input name="email" type="email" placeholder="Email address" required>
            <input name="password" type="password" placeholder="Password (8+ characters)" minlength="8" required>
            <select name="branch" required>
                <option value="">Select branch</option>
                <option>CSE</option>
                <option>AI & ML</option>
                <option>IT</option>
                <option>ECE</option>
                <option>Other</option>
            </select>
            <input name="cgpa" type="number" min="0" max="10" step="0.01" placeholder="CGPA (0–10)" required>
            <button type="submit">Register</button>
        </form>
        <a href="{{ url_for('login') }}">Already registered? Login</a>
    </div>
    """, message=message)


@app.route("/login", methods=["GET", "POST"])
def login():
    message = ""

    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        with get_db() as conn:
            student = conn.execute(
                "SELECT * FROM students WHERE email = ?", (email,)
            ).fetchone()

        if student and check_password_hash(student["password"], password):
            session.clear()
            session["student_id"] = student["id"]
            return redirect(url_for("dashboard"))

        message = "Invalid email or password."

    return render_template_string(PAGE_STYLE + """
    <div class="card">
        <h2>Student Login</h2>
        <p class="message">{{ message }}</p>
        <form method="post">
            <input name="email" type="email" placeholder="Email address" required>
            <input name="password" type="password" placeholder="Password" required>
            <button type="submit">Login</button>
        </form>
        <a href="{{ url_for('register') }}">Create a student account</a>
    </div>
    """, message=message)


@app.route("/dashboard")
def dashboard():
    if "student_id" not in session:
        return redirect(url_for("login"))

    with get_db() as conn:
        student = conn.execute(
            "SELECT id, name, email, branch, cgpa FROM students WHERE id = ?",
            (session["student_id"],)
        ).fetchone()

    if not student:
        session.clear()
        return redirect(url_for("login"))

    return render_template_string(PAGE_STYLE + """
    <div class="card">
        <h1>Student Dashboard</h1>
        <h2>Welcome, {{ student.name }}!</h2>
        <p><strong>Student ID:</strong> {{ student.id }}</p>
        <p><strong>Email:</strong> {{ student.email }}</p>
        <p><strong>Branch:</strong> {{ student.branch }}</p>
        <p><strong>CGPA:</strong> {{ "%.2f"|format(student.cgpa) }}</p>
        <a class="button" href="{{ url_for('edit_profile') }}">Edit Profile</a>
        <a class="button" href="{{ url_for('logout') }}">Logout</a>
    </div>
    """, student=student)


@app.route("/edit-profile", methods=["GET", "POST"])
def edit_profile():
    if "student_id" not in session:
        return redirect(url_for("login"))

    with get_db() as conn:
        student = conn.execute(
            "SELECT * FROM students WHERE id = ?", (session["student_id"],)
        ).fetchone()

        if request.method == "POST":
            name = request.form["name"].strip()
            branch = request.form["branch"]
            try:
                cgpa = float(request.form["cgpa"])
            except ValueError:
                cgpa = -1

            if name and branch and 0 <= cgpa <= 10:
                conn.execute(
                    "UPDATE students SET name=?, branch=?, cgpa=? WHERE id=?",
                    (name, branch, cgpa, session["student_id"])
                )
                return redirect(url_for("dashboard"))

    return render_template_string(PAGE_STYLE + """
    <div class="card">
        <h2>Edit Student Profile</h2>
        <form method="post">
            <input name="name" value="{{ student.name }}" required>
            <input name="branch" value="{{ student.branch }}" required>
            <input name="cgpa" type="number" min="0" max="10" step="0.01"
                   value="{{ student.cgpa }}" required>
            <button type="submit">Save Changes</button>
        </form>
        <a href="{{ url_for('dashboard') }}">Back to Dashboard</a>
    </div>
    """, student=student)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


if __name__ == "__main__":
    initialize_database()
    app.run(debug=True)