# 🔥 AI Driven Fire Detection System

An AI-powered fire detection and alert system that identifies fire incidents in real-time using computer vision and provides instant notifications and monitoring through a web dashboard.

---

## 🚀 Features

* 🔍 **Real-time Fire Detection**

  * Detects fire using AI/ML models (YOLO / OpenCV)

* 📊 **Dashboard Interface**

  * Monitor live alerts and system activity

* 📁 **Fire History Tracking**

  * Stores detected fire incidents in CSV / database

* 🔔 **Alert System**

  * Audio alerts and push notifications

* 🌐 **Web Application**

  * Built with Flask backend and interactive frontend

---

## 🛠️ Tech Stack

* **Frontend:** HTML, CSS, JavaScript
* **Backend:** Python (Flask)
* **AI Model:** YOLO / OpenCV
* **Database:** SQLite / CSV
* **Other:** Service Workers, Push Notifications

---

## 📂 Project Structure

AI_Driven_Fire_Detection/
│── app.py
│── requirements.txt
│── fire_log.csv
│── users.db

├── templates/
│   ├── index.html
│   ├── dashboard.html
│   ├── history.html
│   └── login.html

├── static/
│   ├── notify.js
│   ├── push.js
│   ├── sw.js
│   ├── fire_alarm.mp3
│   └── assets (images / pdfs)

└── utils/
├── detection.py
├── notifications.py
├── storage.py
└── push.py

---

## ⚙️ Installation & Setup

### 1️⃣ Clone the repository

git clone https://github.com/mandarr007bhoite-lgtm/AI_DRIVEN_FIRE_DETECTION.git
cd AI_DRIVEN_FIRE_DETECTION

### 2️⃣ Create virtual environment (recommended)

python -m venv venv
venv\Scripts\activate

### 3️⃣ Install dependencies

pip install -r requirements.txt

---

## ▶️ Run the Project

python app.py

Open in browser:
http://127.0.0.1:5000

---

## 📸 Screenshots

(Add your screenshots here to make project look professional)

---

## 📌 Future Improvements

* 🔥 Live CCTV camera integration
* 📱 Mobile app version
* ☁️ Cloud deployment (AWS / Azure)
* 📡 IoT-based fire sensors
* 📊 Advanced analytics dashboard

---

## 👨‍💻 Author

Mandar Bhoite

---

## ⭐ Contributing

Contributions are welcome! Feel free to fork this repository and submit a pull request.

---

## 📜 License

This project is open-source and available under the MIT License.
