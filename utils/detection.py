import cv2
import numpy as np
import threading
import time
import pyttsx3
from playsound import playsound
from datetime import datetime
from utils.storage import save_detection
from utils.notifications import send_fire_alert_sms, send_sms, log_detection
import os

ALARM_SOUND = "static/fire_alarm.mp3"
alarm_running = False

# Play alarm + voice
def play_alarm_and_voice():
    start_time = time.time()
    while time.time() - start_time < 30:
        playsound(ALARM_SOUND)

    engine = pyttsx3.init()
    engine.setProperty('rate', 150)
    engine.setProperty('volume', 1.0)
    engine.say("Fire detected! Please take action immediately.")
    engine.runAndWait()

def detect_fire_smoke(frame):
    global alarm_running
    fire_detected = False
    intensity = "Low"

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # 🔥 Narrowed down fire color ranges (orange/yellow)
    lower_fire1 = np.array([0, 120, 150])   # dark red/orange
    upper_fire1 = np.array([15, 255, 255])

    lower_fire2 = np.array([16, 150, 150])  # bright orange/yellow
    upper_fire2 = np.array([35, 255, 255])

    mask1 = cv2.inRange(hsv, lower_fire1, upper_fire1)
    mask2 = cv2.inRange(hsv, lower_fire2, upper_fire2)
    mask = cv2.bitwise_or(mask1, mask2)

    # Noise reduction
    mask = cv2.GaussianBlur(mask, (5, 5), 0)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))

    fire_pixels = cv2.countNonZero(mask)

    if fire_pixels > 1500:  # ✅ fire must cover enough area
        fire_detected = True
        if fire_pixels > 7000:
            intensity = "High"
        elif fire_pixels > 3000:
            intensity = "Medium"

        # Draw bounding boxes only if fire is confirmed
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            if cv2.contourArea(cnt) > 1200:  # ✅ only big enough flames
                x, y, w, h = cv2.boundingRect(cnt)
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 3)
                cv2.putText(frame, f"FIRE ({intensity})", (x, y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)

        if not alarm_running:
            alarm_running = True
            threading.Thread(target=play_alarm_and_voice, daemon=True).start()
            # Also record detection and notify immediately in real-time path
            now = datetime.now()
            day = now.strftime("%A")
            date_str = now.strftime("%Y-%m-%d")
            time_str = now.strftime("%H:%M:%S")
            save_detection(day, date_str, time_str, intensity, 0)
            log_detection(intensity)
            msg = f"FIRE ALERT: Intensity={intensity}. Detected at {date_str} {time_str}. 0 seconds ago."
            admin_phone = os.getenv("ADMIN_PHONE_NUMBER")
            brigade_phone = os.getenv("FIRE_BRIGADE_PHONE_NUMBER")
            if admin_phone:
                send_sms(admin_phone, msg, intensity=intensity)
            if brigade_phone:
                send_sms(brigade_phone, msg, intensity=intensity)
    else:
        alarm_running = False  # reset when no fire

    return {"fire_detected": fire_detected, "intensity": intensity}


# ---- Run in real-time ----
if __name__ == "__main__":
    cap = cv2.VideoCapture(0)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        detect_fire_smoke(frame)
        cv2.imshow("Fire Detection", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

