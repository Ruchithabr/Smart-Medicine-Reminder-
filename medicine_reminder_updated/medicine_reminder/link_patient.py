import sqlite3

def link_caregiver_patient():
    conn = sqlite3.connect('medicine.db')
    c = conn.cursor()
    
    # Show all users
    print("All users:")
    c.execute("SELECT user_id, full_name, role FROM users")
    users = c.fetchall()
    for user in users:
        print(f"ID: {user[0]} | Name: {user[1]} | Role: {user[2]}")
    
    caregiver_id = input("Enter caregiver ID: ")
    patient_id = input("Enter patient ID: ")
    
    try:
        c.execute("INSERT INTO caregiver_patient (caregiver_id, patient_id) VALUES (?, ?)", (caregiver_id, patient_id))
        conn.commit()
        print("✅ Link created successfully!")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    link_caregiver_patient()