# 💊 MediRemind — Smart Medicine Reminder App

MediRemind is a role-based web application designed to help patients, caregivers, and doctors manage medication schedules and track adherence. It features an AI-powered dose-risk predictor that analyzes patient intake logs to identify patterns and flag potential health risks.

## ✨ Features

- **Role-Based Access:** Separate dashboards and permissions for Patients, Caregivers, and Doctors.
- **Smart Reminders & Tracking:** Logs medication intake as taken, missed, or snoozed.
- **AI Dose-Risk Predictor:** Uses historical intake-log data and machine learning to assess dose risks and patient adherence patterns.
- **Habit & Health Tracking:** Dedicated modules for tracking daily habits and overall patient health.
- **Automated PDF Reports:** Generates downloadable adherence reports using ReportLab for patients and doctors to review.
- **Admin Panel:** Full control over user management and system data.

## 🛠️ Tech Stack

- **Backend:** Python, Flask
- **Database:** SQLite (`medicine.db`)
- **AI/ML & Data:** Scikit-learn (Predictive Modeling), Pandas (Data Processing)
- **Frontend:** HTML, CSS, JavaScript (Jinja2 Templates)
- **Libraries:** ReportLab (PDF generation), Flask-WTF (Forms)

## 📂 Project Structure

```text
medicine_reminder/
│
├── .vscode/                 # VS Code settings
├── static/                  # CSS, JS, and image assets
│   ├── css/
│   ├── images/
│   └── js/
├── templates/               # HTML files (Flask Jinja2)
│   ├── base.html            # Base layout template
│   ├── home.html            # Landing page
│   ├── login.html           # Authentication
│   ├── register.html        # User registration
│   ├── dashboard.html       # Role-based dashboard
│   ├── ai_prediction.html   # AI dose-risk prediction interface
│   ├── add_medicine.html    # Add medication schedule
│   ├── habits.html          # Habit tracking
│   ├── patients.html        # Doctor's patient management
│   ├── reports.html         # Adherence reports
│   ├── profile.html         # User profile
│   ├── admin.html           # Admin dashboard
│   └── macros.html          # Reusable UI components
├── uploads/                 # User-uploaded files (images/reports)
├── .env                     # Environment variables
├── app.py                   # Main Flask application
├── link_patient.py          # Logic for linking patient-caregiver-doctor
├── medicine.db              # SQLite Database
├── requirements.txt         # Python dependencies
└── README.md                # Project documentation
```

## ⚙️ How It Works

1. **Registration & Login:** Users register and are assigned specific roles (Patient, Doctor, or Admin).
2. **Medication Scheduling:** Patients add their medicine schedules which are stored in the SQLite database.
3. **Daily Tracking:** Patients log their medication status (taken/missed/snoozed) through the dashboard.
4. **AI Prediction:** The system processes this historical intake data to predict adherence risks and flag potential health issues.
5. **Reporting:** Doctors can generate PDF reports to review patient adherence over time.

## 🚀 Installation & Setup

To run this project locally, follow these steps:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Ruchithabr/Smart-Medicine-Reminder-.git
   cd Smart-Medicine-Reminder-
   ```

2. **Create a virtual environment (Recommended):**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On Mac/Linux:
   source venv/bin/activate
   ```

3. **Install the dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up Environment Variables:**
   Create a `.env` file in the root directory and add any necessary configuration keys (e.g., `SECRET_KEY` for Flask).

5. **Initialize the Database:**
   If the `medicine.db` file is not already in the repo, run:
   ```bash
   python app.py
   ```
   *(This will automatically create the SQLite database based on your models on the first run).*

6. **Run the application:**
   ```bash
   python app.py
   ```

7. **Open in your browser:**
   Navigate to `http://127.0.0.1:5000/`

## 📫 Connect with Me

- **LinkedIn:** [linkedin.com/in/ruchitha-br](https://linkedin.com/in/ruchitha-br)
- **Email:** ruchitha.b.r.01@gmail.com
- **GitHub:** [github.com/Ruchithabr](https://github.com/Ruchithabr)
