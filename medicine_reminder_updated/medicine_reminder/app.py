import sqlite3
import os
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from io import BytesIO


load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'fallback-secret-key')

@app.template_filter('medicine_icon')
def medicine_icon_filter(med_type):
    icons = {
        'tablet': '💊',
        'syrup': '🧪',
        'ointment': '🧴',
        'injection': '💉',
        'drops': '👁️'
    }
    return icons.get(med_type, '💊')

# ==================== DATABASE SETUP ====================
def init_db():
    conn = sqlite3.connect('medicine.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        full_name TEXT NOT NULL,
        age INTEGER,
        gender TEXT,
        contact_no TEXT,
        emergency_contact TEXT,
        role TEXT NOT NULL
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS caregiver_patient (
    caregiver_id INTEGER NOT NULL,
    patient_id INTEGER NOT NULL,
    PRIMARY KEY (caregiver_id, patient_id),
    FOREIGN KEY (caregiver_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (patient_id) REFERENCES users(user_id) ON DELETE CASCADE
)''')
    c.execute('''CREATE TABLE IF NOT EXISTS medicines (
    medicine_id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    type TEXT,
    dosage TEXT,
    frequency TEXT,
    food_timing TEXT,           -- 'before', 'after', 'either'
    start_date TEXT,
    end_date TEXT,
    FOREIGN KEY (patient_id) REFERENCES users (user_id)
)''')
    c.execute('''CREATE TABLE IF NOT EXISTS intake_log (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        medicine_id INTEGER NOT NULL,
        scheduled_time TEXT NOT NULL,
        taken_status TEXT DEFAULT 'missed',
        taken_at TEXT,
        FOREIGN KEY (medicine_id) REFERENCES medicines (medicine_id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS health_habits (
        habit_id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER NOT NULL,
        habit_type TEXT,
        goal TEXT,
        instruction TEXT,
        FOREIGN KEY (patient_id) REFERENCES users (user_id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS habit_log (
        habit_log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        habit_id INTEGER NOT NULL,
        log_date TEXT,
        amount_achieved REAL,
        FOREIGN KEY (habit_id) REFERENCES health_habits (habit_id)
    )''')
    conn.commit()
    conn.close()

init_db()

def get_db():
    return sqlite3.connect('medicine.db')

def get_home_stats():
    """Real, live counts pulled straight from the database for the home page."""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users WHERE role = 'patient'")
    total_patients = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM users WHERE role IN ('caregiver', 'doctor')")
    total_care_team = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM intake_log")
    total_doses = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM intake_log WHERE taken_status = 'taken'")
    taken_doses = c.fetchone()[0] or 0
    adherence_pct = round((taken_doses / total_doses) * 100) if total_doses > 0 else 0
    conn.close()
    return {
        'total_patients': total_patients,
        'total_care_team': total_care_team,
        'total_doses': total_doses,
        'adherence_pct': adherence_pct
    }

def can_manage_patient(cursor, user_id, role, patient_id):
    """Checks whether the logged-in user is allowed to view/update this patient's data."""
    try:
        patient_id = int(patient_id)
    except (TypeError, ValueError):
        return False
    if role == 'patient':
        return user_id == patient_id
    if role == 'doctor':
        return True
    if role == 'caregiver':
        cursor.execute("SELECT 1 FROM caregiver_patient WHERE caregiver_id = ? AND patient_id = ?",
                        (user_id, patient_id))
        return cursor.fetchone() is not None
    return False

# ==================== ROUTES ====================
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    stats = get_home_stats()
    return render_template('home.html', stats=stats)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT user_id, password_hash, role FROM users WHERE email = ?", (email,))
        user = c.fetchone()
        conn.close()
        if user and check_password_hash(user[1], password):
            session['user_id'] = user[0]
            session['role'] = user[2]
            flash('Login successful', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        password_hash = generate_password_hash(request.form['password'])
        # Public registration may only create patient/caregiver/doctor accounts —
        # admin accounts must never be self-assigned through this form.
        role = request.form.get('role', 'patient')
        if role not in ('patient', 'caregiver', 'doctor'):
            role = 'patient'
        conn = get_db()
        c = conn.cursor()
        try:
            c.execute('''INSERT INTO users 
                (email, password_hash, full_name, age, gender, contact_no, emergency_contact, role)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                (request.form['email'], password_hash, request.form['full_name'],
                 request.form.get('age'), request.form.get('gender'),
                 request.form.get('contact_no'), request.form.get('emergency_contact'),
                 role))
            conn.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'Error: {e}', 'danger')
        finally:
            conn.close()
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'POST':
        # Update profile
        full_name = request.form['full_name']
        age = request.form.get('age')
        gender = request.form.get('gender')
        contact_no = request.form.get('contact_no')
        emergency_contact = request.form.get('emergency_contact')
        c.execute('''UPDATE users 
                     SET full_name=?, age=?, gender=?, contact_no=?, emergency_contact=?
                     WHERE user_id=?''',
                  (full_name, age, gender, contact_no, emergency_contact, user_id))
        conn.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))
    
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    conn.close()
    return render_template('profile.html', user=user)

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    conn = get_db()
    c = conn.cursor()
    today = datetime.now().strftime('%Y-%m-%d')
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

    c.execute('''SELECT il.log_id, m.name, m.type, m.dosage, il.scheduled_time
                 FROM intake_log il
                 JOIN medicines m ON il.medicine_id = m.medicine_id
                 WHERE m.patient_id = ? AND DATE(il.scheduled_time) = DATE(?)
                 AND il.taken_status = 'missed'
                 ORDER BY il.scheduled_time''', (user_id, today))
    pending_meds = c.fetchall()

    c.execute('''SELECT COUNT(*) FROM intake_log il
                 JOIN medicines m ON il.medicine_id = m.medicine_id
                 WHERE m.patient_id = ? AND DATE(il.scheduled_time) = DATE(?)''', (user_id, today))
    total_today = c.fetchone()[0] or 0

    c.execute('''SELECT COUNT(*) FROM intake_log il
                 JOIN medicines m ON il.medicine_id = m.medicine_id
                 WHERE m.patient_id = ? AND DATE(il.scheduled_time) = DATE(?)
                 AND il.taken_status = 'taken' ''', (user_id, today))
    taken_today = c.fetchone()[0] or 0

    c.execute('''SELECT COUNT(*) FROM intake_log il
                 JOIN medicines m ON il.medicine_id = m.medicine_id
                 WHERE m.patient_id = ? AND DATE(il.scheduled_time) = DATE(?)''', (user_id, tomorrow))
    has_tomorrow = c.fetchone()[0] > 0

    c.execute('''SELECT SUM(amount_achieved) FROM habit_log hl
                 JOIN health_habits hh ON hl.habit_id = hh.habit_id
                 WHERE hh.patient_id = ? AND hh.habit_type = 'water'
                 AND hl.log_date = DATE(?)''', (user_id, today))
    water = c.fetchone()[0] or 0

    # Find (don't hardcode!) this user's own water habit, so the quick-log
    # button always writes to the correct person's record.
    c.execute("SELECT habit_id FROM health_habits WHERE patient_id = ? AND habit_type = 'water' LIMIT 1", (user_id,))
    water_habit_row = c.fetchone()
    water_habit_id = water_habit_row[0] if water_habit_row else None
    conn.close()

    if total_today == 0:
        status_message = "✨ No medicines scheduled for today. Stay healthy!"
    elif taken_today == total_today:
        status_message = "🎉 Excellent! You've taken all your medicines today. Keep up the great work!"
    else:
        remaining = total_today - taken_today
        status_message = f"💪 You've taken {taken_today} out of {total_today} medicines today. {remaining} remaining. You can do it!"

    if has_tomorrow:
        status_message += " 📅 You have medicines scheduled for tomorrow. Prepare in advance."
    else:
        status_message += " 🌟 No medicines for tomorrow. Enjoy your day!"

    return render_template('dashboard.html', 
                           medicines=pending_meds, 
                           water_total=water,
                           water_habit_id=water_habit_id,
                           taken_today=taken_today,
                           total_today=total_today,
                           status_message=status_message,
                           role=session.get('role'))

@app.route('/mark_taken/<int:log_id>', methods=['POST'])
def mark_taken(log_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    c = conn.cursor()
    c.execute('''SELECT m.patient_id FROM intake_log il
                 JOIN medicines m ON il.medicine_id = m.medicine_id
                 WHERE il.log_id = ?''', (log_id,))
    row = c.fetchone()
    if not row or not can_manage_patient(c, session['user_id'], session.get('role'), row[0]):
        conn.close()
        flash('You are not authorized to update this reminder.', 'danger')
        return redirect(url_for('dashboard'))
    now = datetime.now().isoformat()
    c.execute("UPDATE intake_log SET taken_status = 'taken', taken_at = ? WHERE log_id = ?", (now, log_id))
    conn.commit()
    conn.close()
    flash('Medicine marked as taken!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/snooze/<int:log_id>', methods=['POST'])
def snooze_medicine(log_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    c = conn.cursor()
    c.execute('''SELECT m.patient_id FROM intake_log il
                 JOIN medicines m ON il.medicine_id = m.medicine_id
                 WHERE il.log_id = ?''', (log_id,))
    row = c.fetchone()
    if not row or not can_manage_patient(c, session['user_id'], session.get('role'), row[0]):
        conn.close()
        flash('You are not authorized to update this reminder.', 'danger')
        return redirect(url_for('dashboard'))
    # Move the reminder 5 minutes into the future
    new_time = (datetime.now() + timedelta(minutes=5)).isoformat()
    c.execute("UPDATE intake_log SET scheduled_time = ? WHERE log_id = ?", (new_time, log_id))
    conn.commit()
    conn.close()
    flash('Medicine snoozed for 5 minutes.', 'info')
    return redirect(url_for('dashboard'))

@app.route('/add_medicine', methods=['GET', 'POST'])
def add_medicine():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    role = session['role']
    conn = get_db()
    c = conn.cursor()
    patients = []
    
    # Determine patient list for dropdown (if doctor or caregiver)
    if role in ['doctor', 'caregiver']:
        if role == 'doctor':
            c.execute("SELECT user_id, full_name FROM users WHERE role = 'patient' ORDER BY full_name")
            patients = c.fetchall()
        else:  # caregiver
            c.execute('''SELECT u.user_id, u.full_name 
                         FROM caregiver_patient cp
                         JOIN users u ON cp.patient_id = u.user_id
                         WHERE cp.caregiver_id = ?''', (user_id,))
            patients = c.fetchall()
    
    if request.method == 'POST':
        # Determine patient_id
        if role == 'patient':
            patient_id = user_id
        else:
            patient_id = request.form.get('patient_id')
            if not patient_id:
                flash('Please select a patient.', 'danger')
                return redirect(url_for('add_medicine'))
            # Verify caregiver's access to this patient
            if role == 'caregiver' and not can_manage_patient(c, user_id, role, patient_id):
                flash('You are not authorized to add medicine for this patient.', 'danger')
                return redirect(url_for('add_medicine'))
        
        name = request.form['name']
        med_type = request.form['type']
        dosage = request.form['dosage']
        frequency = request.form['frequency']
        food_timing = request.form['food_timing']
        start_date = request.form['start_date']
        end_date = request.form['end_date'] or None
        reminder_time = request.form['reminder_time']
        
        c.execute('''INSERT INTO medicines 
            (patient_id, name, type, dosage, frequency, food_timing, start_date, end_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            (patient_id, name, med_type, dosage, frequency, food_timing, start_date, end_date))
        med_id = c.lastrowid
        
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d') if end_date else start + timedelta(days=30)
        reminder_dt = datetime.strptime(reminder_time, '%H:%M')
        current = start
        while current <= end:
            scheduled = datetime(current.year, current.month, current.day, reminder_dt.hour, reminder_dt.minute)
            if scheduled >= datetime.now():
                c.execute("INSERT INTO intake_log (medicine_id, scheduled_time) VALUES (?, ?)",
                         (med_id, scheduled.isoformat()))
            current += timedelta(days=1)
        conn.commit()
        conn.close()
        flash('Medicine added successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    conn.close()
    return render_template('add_medicine.html', patients=patients, role=role)

def get_medicine_icon(med_type):
    icons = {
        'tablet': '💊',
        'syrup': '🧪',
        'ointment': '🧴',
        'injection': '💉',
        'drops': '👁️'
    }
    return icons.get(med_type, '💊')

@app.route('/habits', methods=['GET', 'POST'])
def habits():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    patient_id = session['user_id']
    conn = get_db()
    c = conn.cursor()
    if request.method == 'POST':
        habit_type = request.form['habit_type']
        goal = request.form.get('goal')
        instruction = request.form.get('instruction')
        c.execute('''INSERT INTO health_habits (patient_id, habit_type, goal, instruction)
                     VALUES (?, ?, ?, ?)''', (patient_id, habit_type, goal, instruction))
        conn.commit()
        flash('Habit added', 'success')
        return redirect(url_for('habits'))
    
    if request.args.get('log_water'):
        amount = float(request.args.get('amount'))
        habit_id = request.args.get('habit_id')
        # Make sure this habit actually belongs to the logged-in patient
        c.execute("SELECT 1 FROM health_habits WHERE habit_id = ? AND patient_id = ?", (habit_id, patient_id))
        if not c.fetchone():
            conn.close()
            flash('That habit could not be found for your account.', 'danger')
            return redirect(url_for('habits'))
        today = datetime.now().strftime('%Y-%m-%d')
        c.execute("SELECT habit_log_id FROM habit_log WHERE habit_id = ? AND log_date = ?", (habit_id, today))
        existing = c.fetchone()
        if existing:
            c.execute("UPDATE habit_log SET amount_achieved = amount_achieved + ? WHERE habit_id = ? AND log_date = ?",
                      (amount, habit_id, today))
        else:
            c.execute("INSERT INTO habit_log (habit_id, log_date, amount_achieved) VALUES (?, ?, ?)",
                      (habit_id, today, amount))
        conn.commit()
        flash('Water intake logged', 'success')
        return redirect(url_for('habits'))
    
    c.execute("SELECT * FROM health_habits WHERE patient_id = ?", (patient_id,))
    habits_list = c.fetchall()
    conn.close()
    return render_template('habits.html', habits=habits_list)

@app.route('/reports')
def reports():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    patient_id = session['user_id']
    conn = get_db()
    c = conn.cursor()
    
    # Get local today and 6 days ago using Python
    from datetime import datetime, timedelta
    today = datetime.now().date()
    six_days_ago = today - timedelta(days=6)
    today_str = today.strftime('%Y-%m-%d')
    six_days_ago_str = six_days_ago.strftime('%Y-%m-%d')
    
    # Weekly adherence – using Python date strings
    c.execute('''SELECT DATE(scheduled_time) as day,
                        COUNT(*) as total,
                        SUM(CASE WHEN taken_status = 'taken' THEN 1 ELSE 0 END) as taken
                 FROM intake_log il
                 JOIN medicines m ON il.medicine_id = m.medicine_id
                 WHERE m.patient_id = ? 
                   AND DATE(scheduled_time) >= ?
                   AND DATE(scheduled_time) <= ?
                 GROUP BY DATE(scheduled_time)
                 ORDER BY day''', (patient_id, six_days_ago_str, today_str))
    weekly = c.fetchall()
    
    # Missed doses – only up to today
    c.execute('''SELECT m.name, il.scheduled_time, il.taken_status
                 FROM intake_log il
                 JOIN medicines m ON il.medicine_id = m.medicine_id
                 WHERE m.patient_id = ? 
                   AND il.taken_status != 'taken'
                   AND DATE(scheduled_time) <= ?
                 ORDER BY il.scheduled_time DESC 
                 LIMIT 20''', (patient_id, today_str))
    missed = c.fetchall()
    conn.close()
    return render_template('reports.html', weekly=weekly, missed=missed)

# ==================== ADMIN PANEL ====================
@app.route('/admin')
def admin_dashboard():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Access denied. Admin only.', 'danger')
        return redirect(url_for('dashboard'))
    
    conn = get_db()
    c = conn.cursor()
    # Get all users
    c.execute("SELECT user_id, full_name, email, role FROM users ORDER BY role, full_name")
    users = c.fetchall()
    
    # Get all caregiver-patient links
    c.execute('''SELECT cp.caregiver_id, u1.full_name AS caregiver_name,
                        cp.patient_id, u2.full_name AS patient_name
                 FROM caregiver_patient cp
                 JOIN users u1 ON cp.caregiver_id = u1.user_id
                 JOIN users u2 ON cp.patient_id = u2.user_id''')
    links = c.fetchall()
    conn.close()
    return render_template('admin.html', users=users, links=links)

@app.route('/admin/link', methods=['POST'])
def admin_link():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    
    caregiver_id = request.form.get('caregiver_id')
    patient_id = request.form.get('patient_id')
    
    if not caregiver_id or not patient_id:
        flash('Please select both caregiver and patient.', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO caregiver_patient (caregiver_id, patient_id) VALUES (?, ?)", (caregiver_id, patient_id))
        conn.commit()
        flash('Link created successfully!', 'success')
    except Exception as e:
        flash(f'Error: {e}', 'danger')
    finally:
        conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/unlink/<int:caregiver_id>/<int:patient_id>', methods=['POST'])
def admin_unlink(caregiver_id, patient_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM caregiver_patient WHERE caregiver_id = ? AND patient_id = ?", (caregiver_id, patient_id))
    conn.commit()
    conn.close()
    flash('Link removed.', 'info')
    return redirect(url_for('admin_dashboard'))

@app.route('/download-pdf')
def download_pdf():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from io import BytesIO
    
    patient_id = session['user_id']
    conn = get_db()
    c = conn.cursor()
    
    c.execute("SELECT full_name FROM users WHERE user_id = ?", (patient_id,))
    patient = c.fetchone()
    patient_name = patient[0] if patient else "Patient"
    
    # Past 7 days (including today)
    c.execute('''SELECT DATE(scheduled_time) as day,
                        COUNT(*) as total,
                        SUM(CASE WHEN taken_status = 'taken' THEN 1 ELSE 0 END) as taken
                 FROM intake_log il
                 JOIN medicines m ON il.medicine_id = m.medicine_id
                 WHERE m.patient_id = ? 
                   AND scheduled_time >= DATE('now', '-6 days')
                   AND scheduled_time <= DATE('now')
                 GROUP BY DATE(scheduled_time)
                 ORDER BY day''', (patient_id,))
    weekly = c.fetchall()
    
    # Only past missed doses
    c.execute('''SELECT m.name, il.scheduled_time, il.taken_status
                 FROM intake_log il
                 JOIN medicines m ON il.medicine_id = m.medicine_id
                 WHERE m.patient_id = ? 
                   AND il.taken_status != 'taken'
                   AND il.scheduled_time <= datetime('now')
                 ORDER BY il.scheduled_time DESC 
                 LIMIT 20''', (patient_id,))
    missed = c.fetchall()
    conn.close()
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    title_style = styles['Title']
    heading_style = styles['Heading2']
    normal_style = styles['Normal']
    
    elements = []
    
    # Title
    elements.append(Paragraph("Medicine Adherence Report", title_style))
    elements.append(Spacer(1, 0.2*inch))
    elements.append(Paragraph(f"Patient: {patient_name}", normal_style))
    elements.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", normal_style))
    elements.append(Spacer(1, 0.3*inch))
    
    # Weekly adherence
    elements.append(Paragraph("Weekly Adherence", heading_style))
    if weekly:
        data = [['Date', 'Total Doses', 'Taken', 'Compliance %']]
        for row in weekly:
            day = row[0] if row[0] else "N/A"
            total = row[1] or 0
            taken = row[2] or 0
            compliance = round((taken/total)*100, 1) if total > 0 else 0
            data.append([day, str(total), str(taken), f"{compliance}%"])
        table = Table(data, colWidths=[1.5*inch, 0.8*inch, 0.8*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.grey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 10),
            ('BOTTOMPADDING', (0,0), (-1,0), 6),
            ('BACKGROUND', (0,1), (-1,-1), colors.beige),
            ('GRID', (0,0), (-1,-1), 1, colors.black),
        ]))
        elements.append(table)
    else:
        elements.append(Paragraph("No adherence data for the past 7 days.", normal_style))
    elements.append(Spacer(1, 0.3*inch))
    
    # Missed doses
    elements.append(Paragraph("Recent Missed Doses (Past)", heading_style))
    if missed:
        for miss in missed:
            med_name = miss[0]
            scheduled = miss[1] if miss[1] else "N/A"
            status = miss[2]
            elements.append(Paragraph(f"• {med_name} - {scheduled} - {status}", normal_style))
    else:
        elements.append(Paragraph("No missed doses in the past.", normal_style))
    
    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    
    response = make_response(pdf_bytes)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=adherence_report_{datetime.now().strftime("%Y%m%d")}.pdf'
    return response


@app.route('/api/notifications/pending')
def pending_notifications():
    if 'user_id' not in session:
        return jsonify([])
    user_id = session['user_id']
    conn = get_db()
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute('''SELECT il.log_id, m.name, il.scheduled_time
                 FROM intake_log il
                 JOIN medicines m ON il.medicine_id = m.medicine_id
                 WHERE m.patient_id = ? AND il.taken_status = 'missed'
                 AND il.scheduled_time <= ?''', (user_id, now))
    pending = c.fetchall()
    conn.close()
    notifs = [{'notif_id': p[0], 'message': f"Time to take {p[1]}"} for p in pending]
    return jsonify(notifs)

@app.route('/ai-prediction')
def ai_prediction():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''SELECT COUNT(*) FROM intake_log il
                 JOIN medicines m ON il.medicine_id = m.medicine_id
                 WHERE m.patient_id = ? AND il.scheduled_time > datetime('now')''', (user_id,))
    future_doses = c.fetchone()[0]
    
    if future_doses == 0:
        conn.close()
        return render_template('ai_prediction.html', state='no_meds')
    
    c.execute('''SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN taken_status = 'taken' THEN 1 ELSE 0 END) as taken
                 FROM intake_log il
                 JOIN medicines m ON il.medicine_id = m.medicine_id
                 WHERE m.patient_id = ? 
                   AND il.scheduled_time BETWEEN datetime('now', '-30 days') AND datetime('now')
              ''', (user_id,))
    history = c.fetchone()
    total_past = history[0] or 0
    taken_past = history[1] or 0
    conn.close()
    
    if total_past < 5:
        return render_template('ai_prediction.html', state='not_enough_data', total_past=total_past)
    
    adherence = (taken_past / total_past) * 100 if total_past > 0 else 0
    if adherence >= 80:
        miss_chance = 15
        recommendation = "Great adherence! Keep it up. You're doing very well."
        risk_level = 'low'
    elif adherence >= 50:
        miss_chance = 40
        recommendation = "Medium risk. Consider setting an extra reminder for your hardest‑to‑remember dose."
        risk_level = 'medium'
    else:
        miss_chance = 70
        recommendation = "High risk of missing doses. Please review your schedule and set more frequent alerts."
        risk_level = 'high'
    
    return render_template('ai_prediction.html', state='result', total_past=total_past,
                           adherence=round(adherence, 1), miss_chance=miss_chance,
                           recommendation=recommendation, risk_level=risk_level)

@app.route('/patients')
def patients_list():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Only doctors and caregivers can view all patients
    if session['role'] not in ['doctor', 'caregiver']:
        flash('Access denied. Only doctors and caregivers can view patient list.', 'danger')
        return redirect(url_for('dashboard'))
    
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT user_id, full_name, email, age, contact_no FROM users WHERE role = 'patient'")
    patients = c.fetchall()
    conn.close()
    
    return render_template('patients.html', patients=patients)

        
if __name__ == '__main__':
    app.run(debug=True, port=5000)