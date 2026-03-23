from flask import Flask, request, jsonify, render_template, Response, url_for, redirect, session, flash
import cv2
import numpy as np
from utils.detection import detect_fire_smoke
import datetime
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
from utils.storage import init_schema, save_detection, fetch_history_rows, save_push_subscription, fetch_push_subscriptions, fetch_latest_detection
from utils.push import send_web_push_to_all
from dotenv import load_dotenv
from utils.notifications import send_fire_alert_sms, send_sms, log_detection

load_dotenv()  # Load environment variables from .env if present
app = Flask(__name__)
app.secret_key = "supersecretkey"

# ========== DB SETUP ==========
DB_NAME = "users.db"

def init_db():
    # Use centralized schema creation, ensures seconds_ago column exists
    init_schema()

init_db()

# Open webcam
camera = cv2.VideoCapture(0)

# ====== ROUTES ======

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/contact")
def contact():
    return render_template("contact.html")

# Web Push endpoints
@app.route("/vapid_public_key")
def vapid_public_key():
    # VAPID_PUBLIC_KEY must be set (Base64 URL-safe encoded)
    return jsonify({"publicKey": os.getenv("VAPID_PUBLIC_KEY", "")})

@app.route("/subscribe", methods=["POST"])
def subscribe():
    try:
        data = request.get_json(force=True)
        endpoint = data.get("endpoint")
        keys = data.get("keys", {})
        p256dh = keys.get("p256dh")
        auth = keys.get("auth")
        if not endpoint or not p256dh or not auth:
            return jsonify({"ok": False, "error": "invalid_payload"}), 400
        save_push_subscription(endpoint, p256dh, auth)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400

# On-demand SMS test helper (bypasses cooldown). Use: /sms_test?to=+91XXXXXXXXXX&msg=Hello
@app.route("/sms_test")
def sms_test():
    to = request.args.get("to")
    msg = request.args.get("msg", "Fire is Detected")
    if not to:
        return jsonify({"ok": False, "error": "missing 'to'"}), 400
    try:
        result = send_sms(to, msg, cooldown_seconds=0, intensity=None)
        return jsonify({"ok": True, **result})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# 🔹 Login Page
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM users WHERE username=?", (username,))
        row = cursor.fetchone()
        conn.close()

        if row and check_password_hash(row[0], password):
            session["admin"] = username
            return redirect(url_for("history"))
        else:
            return render_template("login.html", error="Invalid Credentials")
    return render_template("login.html")

# 🔹 Signup Page
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        hashed_password = generate_password_hash(password)

        try:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
            conn.commit()
            conn.close()
            flash("Signup successful! Please login.", "success")
            return redirect(url_for("login"))
        except:
            return render_template("signup.html", error="Username already exists!")

    return render_template("signup.html")

@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect(url_for("dashboard"))

# 🔹 Fire Detection History
@app.route("/history")
def history():
    if "admin" not in session:
        return redirect(url_for("login"))

    rows = fetch_history_rows()
    logs = []
    for r in rows:
        # r: (day, date, time, intensity, created_at, seconds_ago)
        created_at_str = r[4]
        try:
            detected_time = datetime.datetime.strptime(created_at_str, "%Y-%m-%d %H:%M:%S")
            computed_seconds_ago = int((datetime.datetime.now() - detected_time).total_seconds())
        except Exception:
            computed_seconds_ago = r[5] if r[5] is not None else 0
        logs.append({
            "day": r[0],
            "date": r[1],
            "time": r[2],
            "intensity": r[3],
            "seconds_ago": computed_seconds_ago
        })

    return render_template("history.html", logs=logs)

# Admin-only latest detection (for on-app banner)
@app.route("/api/latest_detection")
def api_latest_detection():
    if "admin" not in session:
        return jsonify({}), 401
    latest = fetch_latest_detection()
    return jsonify(latest)

# 🔹 Fire Detection Route
@app.route("/detect", methods=["POST"])
def detect():
    try:
        frame_file = request.files['frame']
        npimg = np.frombuffer(frame_file.read(), np.uint8)
        frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)

        result = detect_fire_smoke(frame)

        if result["fire_detected"]:
            now = datetime.datetime.now()
            day = now.strftime("%A")
            date_str = now.strftime("%Y-%m-%d")
            time_str = now.strftime("%H:%M:%S")
            intensity = str(result["intensity"])
            seconds_ago = 0  # at detection time

            # Save to DB
            save_detection(day, date_str, time_str, intensity, seconds_ago)
            # CSV log
            log_detection(intensity)

            # Build alert message
            msg = f"FIRE ALERT: Intensity={intensity}. Detected at {date_str} {time_str}. {seconds_ago} seconds ago."

            # Send SMS to admin and fire brigade if configured
            admin_phone = os.getenv("ADMIN_PHONE_NUMBER")
            brigade_phone = os.getenv("FIRE_BRIGADE_PHONE_NUMBER")
            if admin_phone:
                send_sms(admin_phone, msg, intensity=intensity)
            if brigade_phone:
                send_sms(brigade_phone, msg, intensity=intensity)

            # Send Web Push to all subscribers
            try:
                subs = fetch_push_subscriptions()
                if subs:
                    send_web_push_to_all(subs, "🔥 Fire Detected", f"Intensity: {intensity} at {date_str} {time_str}")
            except Exception:
                pass

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 400

# ====== Live video stream ======
def generate_frames():
    while True:
        success, frame = camera.read()
        if not success:
            break

        detect_fire_smoke(frame)  # draws bounding boxes + triggers alarm

        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    print("🔥 Server is running! Open http://127.0.0.1:5000/ in your browser")
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
