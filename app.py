from flask import Flask, render_template, request, redirect, url_for, session, flash
import firebase_admin
from firebase_admin import credentials, auth, firestore
import requests
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
import threading

# Initialize Flask app
app = Flask(__name__, static_folder='static')
app.secret_key = "supersecretkey"  # Ensure this is kept secure

# Initialize Firebase Admin SDK
cred = credentials.Certificate("firebase_config.json")  # Ensure this file exists
firebase_admin.initialize_app(cred)
db = firestore.client()  # Firestore database

# Firebase Web API Key (replace with actual key)
FIREBASE_API_KEY = "AIzaSyDaTK1m5WRAE6MEY8N4N-SNMxEBpCJogNQ"

# Configure Flask-Mail (Replace with your email provider details)
app.config["MAIL_SERVER"] = "smtp.gmail.com"  # SMTP server (Gmail, Outlook, etc.)
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = "studentrajagiri123@gmail.com"  # Replace with your email
app.config["MAIL_PASSWORD"] = "bjcf qljg mbvj iuoh"  # Replace with your email password
app.config["MAIL_DEFAULT_SENDER"] = ("RSET BUS", "rsetbussystem@gmail.com")

mail = Mail(app)
s = URLSafeTimedSerializer(app.secret_key)  # For generating secure tokens

# Global flag to prevent multiple listeners
listener_started = False


# Function to Send Email Notifications
def send_email_notification(user_email, subject, message):
    try:
        msg = Message(subject, sender=("RSET BUS", "rsetbussystem@gmail.com"), recipients=[user_email])
        msg.body = message
        mail.send(msg)
        print(f"Email sent to {user_email}")
    except Exception as e:
        print(f"Failed to send email: {str(e)}")


# Firestore Alert Listener
def listen_for_alerts():
    global listener_started
    if listener_started:
        return  # Prevent multiple listeners
    listener_started = True  

    def on_snapshot(col_snapshot, changes, read_time):
        with app.app_context():  
            for change in changes:
                if change.type.name == "ADDED":  
                    new_alert = change.document.to_dict().get("message", "New Alert")
                    print(f"New Alert: {new_alert}")

                    users = auth.list_users().iterate_all()
                    for user in users:
                        send_email_notification(user.email, "New Bus Alert!", new_alert)

    listener_thread = threading.Thread(target=lambda: db.collection("alerts").on_snapshot(on_snapshot), daemon=True)
    listener_thread.start()


# Forgot Password Route
@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email")
        if not email:
            flash("Email field is required!", "danger")
            return redirect(url_for("forgot_password"))

        token = s.dumps(email, salt="password-reset-salt")
        reset_url = url_for("reset_password", token=token, _external=True)

        msg = Message("Password Reset Request", recipients=[email])
        msg.body = f"Click the link to reset your password: {reset_url}"
        mail.send(msg)

        flash("Password reset link sent to your email!", "info")
        return redirect(url_for("login"))

    return render_template("forgot_password.html")


# Reset Password Route
@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    try:
        email = s.loads(token, salt="password-reset-salt", max_age=3600)
    except:
        flash("Invalid or expired reset link.", "danger")
        return redirect(url_for("forgot_password"))

    if request.method == "POST":
        new_password = request.form["password"]
        try:
            user = auth.get_user_by_email(email)
            auth.update_user(user.uid, password=new_password)
            return redirect(url_for("index"))
        except Exception as e:
            flash(f"Error updating password: {str(e)}", "danger")

    return render_template("reset_password.html", token=token)


# Display Alerts
@app.route("/alerts")
def alerts():
    if "user" not in session:
        return redirect(url_for("index"))

    alerts_data = [alert.to_dict() for alert in db.collection("alerts").stream()]
    return render_template("alerts.html", alerts=alerts_data)


@app.route("/")
def index():
    return render_template("login.html", error=None)


# Login Route
@app.route("/login", methods=["POST"])
def login():
    email = request.form["email"]
    password = request.form["password"]

    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
    response = requests.post(url, json={"email": email, "password": password, "returnSecureToken": True})
    data = response.json()

    if "idToken" in data:
        session["user"] = data["localId"]
        session["user_email"] = email
        return redirect(url_for("home"))
    else:
        flash("Invalid email or password", "danger")
        return render_template("login.html", error="Invalid email or password")


@app.route("/home")
def home():
    if "user" not in session:
        return redirect(url_for("index"))
    return render_template("home.html")


@app.route("/logout")
def logout():
    session.pop("user", None)
    session.pop("user_email", None)
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


# Bus Schedule Route
@app.route("/bus_schedule")
def bus_schedule():
    if "user" not in session:
        return redirect(url_for("index"))

    bus_schedule_data = [
        {"bus_number": "1", "time": "7:15 AM", "route": "Thoppumpady - Vyttila- Karingachira -Campus"},
        {"bus_number": "2", "time": "7:15 AM", "route": "Thevara- Menaka - High court- Kaloor- Palarivattam -Campus"},
        {"bus_number": "3", "time": "7:15 AM", "route": "Paravoor- K M K Jn.- Koonammav - Kothad- Varappuza -lulu - Toll Jn.-B M C - Campus"},
        {"bus_number": "4", "time": "7:15 AM", "route": "Angamaly ksrtc - Aluva - HMT -BMC - Campus"},
        {"bus_number": "5", "time": "7:15 AM", "route": "Perumbavoor- Ponjacherry - Kizhakkambalam - Pallikkara - Kakkanad - Campus"},
        {"bus_number": "6", "time": "7:15 AM", "route": "Poothotta - Nadakkav - Puthiyakav - Tripunithura - Campus"},
        {"bus_number": "7", "time": "7:30 AM", "route": "Panampilly Nagar - Passport office - Manorama - Kadavantra - Vyttila - Medical centre - Campus"}
    ]
    
    return render_template("bus_schedule.html", bus_schedule=bus_schedule_data)


# Fee Payment Route
@app.route("/fee_payment")
def fee_payment():
    return redirect("https://www.rajagiritech.ac.in/stud/ktu/student/")


# Feedback Form Route
@app.route("/feedback")
def feedback():
    return render_template("feedback.html")


@app.route("/submit_feedback", methods=["POST"])
def submit_feedback():
    name = request.form["name"]
    email = request.form["email"]
    rating = request.form["rating"]
    comments = request.form["comments"]

    feedback_data = {
        "name": name,
        "email": email,
        "rating": rating,
        "comments": comments,
    }

    try:
        db.collection("feedbacks").add(feedback_data)
        return render_template("submit_feedback.html")  # Show confirmation page
    except Exception as e:
        flash(f"Error: {str(e)}", "danger")
        return redirect(url_for("feedback"))



if __name__ == "__main__":
    listen_for_alerts()
    app.run(debug=True)
