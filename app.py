from flask import Flask, request, Response, redirect
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Gather
from datetime import datetime, timedelta
from threading import Thread
import pytz
import time
import os

app = Flask(__name__)

# ======================
# ENV VARIABLES (SET THESE IN RENDER)
# ======================
ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
AUTH_TOKEN  = os.environ.get("TWILIO_AUTH_TOKEN")
FROM_NUMBER = os.environ.get("TWILIO_FROM_NUMBER")
TO_NUMBER   = os.environ.get("TWILIO_TO_NUMBER")

MICKEY_MP3  = "https://drive.google.com/uc?id=1pD7ATjLY2u-tbCjJ7mwe7BTuqvkpjZzO"
VOICE       = "Polly.Joanna-Neural"
ET          = pytz.timezone("America/New_York")

client = Client(ACCOUNT_SID, AUTH_TOKEN)

# ======================
# ALARM STORAGE (1 alarm system for now)
# ======================
wakeup_job = {
    "time": None,
    "time_str": None,
    "date_str": None,
    "triggered": False
}

# ======================
# HELPERS
# ======================
def ordinal(n):
    if 11 <= n <= 13:
        return str(n) + "th"
    suffixes = ["th","st","nd","rd","th","th","th","th","th","th"]
    return str(n) + suffixes[n % 10]

def format_time_spoken(hour_24, minute):
    if hour_24 == 0:
        h, ampm = 12, "AM"
    elif hour_24 < 12:
        h, ampm = hour_24, "AM"
    elif hour_24 == 12:
        h, ampm = 12, "PM"
    else:
        h, ampm = hour_24 - 12, "PM"

    return f"{h}:{str(minute).zfill(2)} {ampm}" if minute else f"{h} {ampm}"

def ssml(text):
    return f"<speak>{text}</speak>"

def say(text):
    r = VoiceResponse()
    r.say(ssml(text), voice=VOICE)
    return Response(str(r), mimetype="text/xml")

# ======================
# BACKGROUND CRON WORKER (THE REAL ALARM ENGINE)
# ======================
def alarm_worker():
    while True:
        try:
            if wakeup_job["time"] and not wakeup_job["triggered"]:
                now = datetime.now(pytz.utc)

                if now >= wakeup_job["time"]:
                    twiml = f"""
                    <Response>
                        <Play>{MICKEY_MP3}</Play>
                        <Say voice="{VOICE}">
                            <speak>
                            Good morning. It is time to wake up.
                            </speak>
                        </Say>
                    </Response>
                    """

                    client.calls.create(
                        to=TO_NUMBER,
                        from_=FROM_NUMBER,
                        twiml=twiml
                    )

                    wakeup_job["triggered"] = True

        except Exception as e:
            print("Alarm worker error:", e)

        time.sleep(30)

# ======================
# ROUTES
# ======================
@app.route("/")
def home():
    return "Mickey Morning Call is running!", 200

@app.route("/incoming", methods=["GET", "POST"])
def incoming():
    r = VoiceResponse()
    gather = Gather(num_digits=1, action="/language", method="POST")
    gather.say(ssml("Press star to continue."), voice=VOICE)
    r.append(gather)
    return Response(str(r), mimetype="text/xml")

@app.route("/language", methods=["GET", "POST"])
def language():
    digit = request.form.get("Digits", "")
    if digit != "*":
        return say("Goodbye.")

    r = VoiceResponse()
    gather = Gather(num_digits=1, action="/menu", method="POST")
    gather.say(ssml("Press 1 to set alarm. Press 2 to cancel."), voice=VOICE)
    r.append(gather)
    return Response(str(r), mimetype="text/xml")

@app.route("/menu", methods=["GET", "POST"])
def menu():
    digit = request.form.get("Digits", "")

    if digit == "1":
        r = VoiceResponse()
        gather = Gather(finish_on_key="#", action="/get_time", method="POST")
        gather.say(ssml("Enter 4 digit time like 0730 then press pound."), voice=VOICE)
        r.append(gather)
        return Response(str(r), mimetype="text/xml")

    if digit == "2":
        wakeup_job["time"] = None
        wakeup_job["triggered"] = False
        return say("Alarm cancelled.")

    return say("Invalid.")

@app.route("/get_time", methods=["POST"])
def get_time():
    digits = request.form.get("Digits", "")

    if len(digits) != 4 or not digits.isdigit():
        return say("Invalid time.")

    hour = int(digits[:2])
    minute = int(digits[2:])

    if hour > 12 or minute > 59:
        return say("Invalid time.")

    app.config["HOUR"] = hour
    app.config["MINUTE"] = minute

    r = VoiceResponse()
    gather = Gather(num_digits=1, action="/get_ampm", method="POST")
    gather.say(ssml("Press 1 AM or 2 PM"), voice=VOICE)
    r.append(gather)
    return Response(str(r), mimetype="text/xml")

@app.route("/get_ampm", methods=["POST"])
def get_ampm():
    digit = request.form.get("Digits", "")
    hour = app.config.get("HOUR", 0)
    minute = app.config.get("MINUTE", 0)

    if digit == "1":
        ampm = "AM"
    elif digit == "2":
        ampm = "PM"
    else:
        return say("Invalid.")

    now = datetime.now(ET)

    if ampm == "AM":
        wake_hour = 0 if hour == 12 else hour
    else:
        wake_hour = 12 if hour == 12 else hour + 12

    wake_time = now.replace(hour=wake_hour, minute=minute, second=0, microsecond=0)

    if wake_time <= now:
        wake_time += timedelta(days=1)

    wake_utc = wake_time.astimezone(pytz.utc)

    wakeup_job["time"] = wake_utc
    wakeup_job["time_str"] = format_time_spoken(wake_hour, minute)
    wakeup_job["date_str"] = wake_time.strftime("%A %B %d")
    wakeup_job["triggered"] = False

    r = VoiceResponse()
    gather = Gather(num_digits=1, action="/confirm", method="POST")
    gather.say(ssml(
        f"Alarm set for {wakeup_job['date_str']} at {wakeup_job['time_str']}. Press 1 to confirm."
    ), voice=VOICE)

    r.append(gather)
    return Response(str(r), mimetype="text/xml")

@app.route("/confirm", methods=["POST"])
def confirm():
    digit = request.form.get("Digits", "")

    if digit != "1":
        return say("Cancelled.")

    return say("Your alarm is set. Goodbye.")

# ======================
# START BACKGROUND WORKER
# ======================
thread = Thread(target=alarm_worker)
thread.daemon = True
thread.start()

# ======================
# RUN
# ======================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
