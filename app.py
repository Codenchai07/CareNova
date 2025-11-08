import os
import random
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import mysql.connector
from flask_bcrypt import Bcrypt
from doctor_brain import get_diagnosis_response

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)
bcrypt = Bcrypt(app)

# --- MySQL Connection ---
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="@Sunisha620",  # Replace with your MySQL root password
        database="carenova"
    )

try:
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(255),
            email VARCHAR(255) UNIQUE,
            password VARCHAR(255),
            age INT,
            gender VARCHAR(50),
            language VARCHAR(100),
            medical_history TEXT
        )
    """)
    db.commit()
    print("Connected to MySQL and ensured users table exists.")
except mysql.connector.Error as err:
    print(f"MySQL Error: {err}")

# --- Index Route ---
@app.route("/")
def index():
    return jsonify({"message": "Welcome to CareNova API"})

# --- Diagnosis ---
@app.route('/diagnose', methods=['POST'])
def diagnose():
    if 'image' not in request.files or 'query' not in request.form:
        return jsonify({'error': 'No image or query provided.'}), 400

    image = request.files['image']
    query = request.form['query']

    try:
        image_path = os.path.join('uploads', image.filename)
        os.makedirs('uploads', exist_ok=True)
        image.save(image_path)
        diagnosis = get_diagnosis_response(image_path, query)
        return jsonify({'diagnosis': diagnosis})
    except Exception as e:
        print(f"Error in diagnose: {e}")
        return jsonify({'error': 'Something went wrong. Please try again.'}), 500

# --- Nearby Clinics ---
@app.route('/nearby-clinics')
def nearby_clinics():
    lat = request.args.get('lat')
    lng = request.args.get('lng')
    api_key = os.getenv("GEOAPIFY_API_KEY", "5e9f5c7d4f414da187b1f18e392d2203")

    url = (
        f"https://api.geoapify.com/v2/places"
        f"?categories=healthcare.hospital,healthcare.dentist,healthcare.pharmacy"
        f"&filter=circle:{lng},{lat},5000"
        f"&limit=10&apiKey={api_key}"
    )

    try:
        response = requests.get(url)
        data = response.json()
        clinics = [
            {
                "name": feature.get("properties", {}).get("name", "Unnamed Clinic"),
                "address": feature.get("properties", {}).get("formatted", "Address not available"),
                "phone": feature.get("properties", {}).get("contact:phone", "N/A"),
                "opening_hours": feature.get("properties", {}).get("opening_hours", "Not available")
            }
            for feature in data.get("features", [])
        ]
        return jsonify({"clinics": clinics})
    except Exception as e:
        print("Error fetching nearby clinics:", e)
        return jsonify({"clinics": []})

# --- Register ---
@app.route("/register", methods=["POST"])
def register():
    data = request.json
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    age = data.get("age")
    gender = data.get("gender")
    language = data.get("language")
    medical_history = data.get("medical_history")

    if not username or not email or not password:
        return jsonify({"error": "Missing required fields"}), 400

    hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO users (username, email, password, age, gender, language, medical_history)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (username, email, hashed_password, age, gender, language, medical_history))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"message": "User registered successfully"}), 201
    except mysql.connector.Error as err:
        print("MySQL Error:", err)
        return jsonify({"error": str(err)}), 500

# --- OTP Login ---
user_otps = {}

def send_otp_email(recipient, otp):
    sender_email = "codenchai07@gmail.com"
    sender_password = "akzi kztu xjwc wfgy"  # App password

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = recipient
    msg["Subject"] = "CareNova Login OTP"
    msg.attach(MIMEText(f"Your CareNova login OTP is: {otp}", "plain"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        print(f"OTP sent to {recipient}")
    except Exception as e:
        print("Error sending email:", e)

@app.route('/login-request', methods=['POST'])
def login_request():
    data = request.json
    print("Login Request Data:", data)  # Debug log
    email = data.get("email")

    if not email:
        return jsonify({"error": "Email is required"}), 400

    cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
    user = cursor.fetchone()
    print("User Found:", user)

    if not user:
        return jsonify({"error": "Email not registered"}), 400

    otp = random.randint(100000, 999999)
    user_otps[email] = otp
    send_otp_email(email, otp)
    return jsonify({"message": "OTP sent to email"}), 200


@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    data = request.get_json() or {}
    print("Verify OTP Data:", data)  # debug

    email = data.get("email")
    otp_input = str(data.get("otp", "")).strip()

    if not email or not otp_input:
        return jsonify({"error": "Email and OTP are required."}), 400

    if not otp_input.isdigit():
        return jsonify({"error": "OTP must be numeric."}), 400

    expected = user_otps.get(email)
    print(f"Expected OTP for {email}: {expected}")  # debug

    if expected is None:
        return jsonify({"error": "No OTP issued or OTP expired."}), 400

    if otp_input == str(expected):
        # OTP good – clear it
        del user_otps[email]
        # Optionally issue session token / JWT here
        return jsonify({"message": "Login successful", "email": email}), 200

    return jsonify({"error": "Invalid OTP."}), 400

# --- Profile Management ---
@app.route("/profile", methods=["GET"])
def get_profile():
    email = request.args.get("email")
    if not email:
        return jsonify({"error": "Email is required"}), 400

    cursor.execute("""
        SELECT p.name, p.age, p.gender, p.language, p.medical_history, u.email
        FROM users u
        LEFT JOIN profile p ON u.id = p.user_id
        WHERE u.email=%s
    """, (email,))
    profile = cursor.fetchone()

    if not profile:
        return jsonify({"error": "Profile not found"}), 404

    keys = ["name", "age", "gender", "language", "medical_history", "email"]
    return jsonify(dict(zip(keys, profile)))




@app.route("/profile", methods=["POST"])
def save_profile():
    data = request.json
    email = data.get("email")

    cursor.execute("SELECT id FROM users WHERE email=%s", (email,))
    user = cursor.fetchone()
    if not user:
        return jsonify({"error": "User not found"}), 404

    user_id = user[0]

    cursor.execute("SELECT id FROM profile WHERE user_id=%s", (user_id,))
    existing_profile = cursor.fetchone()

    if existing_profile:
        cursor.execute("""
            UPDATE profile
            SET name=%s, age=%s, gender=%s, language=%s, medical_history=%s
            WHERE user_id=%s
        """, (data.get("name"), data.get("age"), data.get("gender"),
              data.get("language"), data.get("medical_history"), user_id))
    else:
        cursor.execute("""
            INSERT INTO profile (user_id, name, age, gender, language, medical_history)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (user_id, data.get("name"), data.get("age"), data.get("gender"),
              data.get("language"), data.get("medical_history")))
    db.commit()
    return jsonify({"message": "Profile saved successfully"}), 200


@app.route("/profile/delete", methods=["DELETE"])
def delete_profile():
    data = request.json
    email = data.get("email")
    if not email:
        return jsonify({"error": "Email is required"}), 400

    try:
        cursor.execute("DELETE FROM users WHERE email=%s", (email,))
        db.commit()
        return jsonify({"message": "Account deleted successfully"})
    except mysql.connector.Error as err:
        return jsonify({"error": str(err)}), 500

# --- Chat History ---
@app.route("/chat-history", methods=["GET"])
def chat_history():
    email = request.args.get("email")
    if not email:
        return jsonify({"error": "Email is required"}), 400
    try:
        cursor.execute("""
            SELECT user_message, bot_response, created_at FROM chat_history WHERE email=%s ORDER BY created_at DESC LIMIT 10
        """, (email,))
        history = cursor.fetchall()
        return jsonify(history), 200
    except mysql.connector.Error as err:
        return jsonify({"error": str(err)}), 500

def save_chat(email, user_message, bot_response):
    try:
        cursor.execute(
            "INSERT INTO chat_history (email, user_message, bot_response) VALUES (%s, %s, %s)",
            (email, user_message, bot_response)
        )
        db.commit()
    except mysql.connector.Error as err:
        print(f"MySQL Error (save_chat): {err}")

if __name__ == "__main__":
    app.run(debug=True)
