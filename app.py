from flask import Flask, request, Response, redirect
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Gather
from datetime import datetime, timedelta
import pytz, os

app = Flask(**name**)

ACCOUNT_SID = “ACe12f3117ae792a3d7d12806d4b81f66c”
AUTH_TOKEN  = “d386286b38b7642c1388864b3e089690”
FROM_NUMBER = “+16812726403”
TO_NUMBER   = “+12159627989”
MICKEY_MP3  = “https://drive.google.com/uc?id=1pD7ATjLY2u-tbCjJ7mwe7BTuqvkpjZzO”
VOICE       = “Polly.Joanna-Neural”
ET          = pytz.timezone(“America/New_York”)

wakeup_job = {“sid”: None, “time_str”: None, “date_str”: None}

def ordinal(n):
if 11 <= n <= 13:
return f”{n}th”
return f”{n}{[‘th’,‘st’,‘nd’,‘rd’,‘th’,‘th’,‘th’,‘th’,‘th’,‘th’][n % 10]}”

def ssml(text):
return f”<speak>{text}</speak>”

def say(text):
r = VoiceResponse()
r.say(ssml(text), voice=VOICE)
return Response(str(r), mimetype=“text/xml”)

@app.route(”/”)
def home():
return “Mickey Morning Call is running!”, 200

@app.route(”/incoming”, methods=[“GET”, “POST”])
def incoming():
r = VoiceResponse()
gather = Gather(num_digits=1, action=”/language”, method=“POST”, timeout=10)
gather.say(ssml(
“Greetings! <break time='400ms'/> “
“Thank you for calling <emphasis level='moderate'>Disney’s All-Star Music Resort</emphasis> “
“wakeup service. <break time='500ms'/> “
“To continue in English, <break time='200ms'/> press star.”
), voice=VOICE)
r.append(gather)
r.say(ssml(“We didn’t receive your input. <break time='300ms'/> Goodbye!”), voice=VOICE)
return Response(str(r), mimetype=“text/xml”)

@app.route(”/language”, methods=[“GET”, “POST”])
def language():
digit = request.form.get(“Digits”, “”)
if digit != “*”:
return say(“Invalid selection. <break time='200ms'/> Goodbye!”)
r = VoiceResponse()
gather = Gather(num_digits=1, action=”/menu”, method=“POST”, timeout=10)
gather.say(ssml(
“Press <emphasis level='moderate'>one</emphasis> to set a new wakeup call. “
“<break time='400ms'/> “
“Press <emphasis level='moderate'>two</emphasis> to cancel your current wakeup.”
), voice=VOICE)
r.append(gather)
r.say(ssml(“We didn’t receive your input. <break time='300ms'/> Goodbye!”), voice=VOICE)
return Response(str(r), mimetype=“text/xml”)

@app.route(”/menu”, methods=[“GET”, “POST”])
def menu():
digit = request.form.get(“Digits”, “”)
if digit == “1”:
r = VoiceResponse()
gather = Gather(finish_on_key=”#”, action=”/get_time”, method=“POST”, timeout=15)
gather.say(ssml(
“Please enter the four digit time for your wakeup, “
“<break time='200ms'/> followed by the pound key.”
), voice=VOICE)
r.append(gather)
r.say(ssml(“We didn’t receive your input. <break time='300ms'/> Goodbye!”), voice=VOICE)
return Response(str(r), mimetype=“text/xml”)
elif digit == “2”:
if wakeup_job[“sid”]:
try:
client = Client(ACCOUNT_SID, AUTH_TOKEN)
client.calls(wakeup_job[“sid”]).update(status=“canceled”)
except:
pass
wakeup_job[“sid”] = None
wakeup_job[“time_str”] = None
wakeup_job[“date_str”] = None
return say(“Your wakeup call has been cancelled. <break time='300ms'/> Have a magical night!”)
else:
return say(“You have no wakeup call scheduled. <break time='300ms'/> Have a magical night!”)
else:
return say(“Invalid selection. <break time='200ms'/> Goodbye!”)

@app.route(”/get_time”, methods=[“GET”, “POST”])
def get_time():
digits = request.form.get(“Digits”, “”)
if len(digits) != 4 or not digits.isdigit():
return say(“Invalid time entered. <break time='200ms'/> Please call back and try again. Goodbye!”)

```
hour = int(digits[:2])
minute = int(digits[2:])

if hour > 12 or minute > 59:
    return say("Invalid time entered. <break time='200ms'/> Please call back and try again. Goodbye!")

app.config["PENDING_HOUR"] = hour
app.config["PENDING_MINUTE"] = minute

r = VoiceResponse()
gather = Gather(num_digits=1, action="/get_ampm", method="POST", timeout=10)
gather.say(ssml(
    "Press <emphasis level='moderate'>one</emphasis> for A M. "
    "<break time='400ms'/> "
    "Press <emphasis level='moderate'>two</emphasis> for P M."
), voice=VOICE)
r.append(gather)
r.say(ssml("We didn't receive your input. <break time='300ms'/> Goodbye!"), voice=VOICE)
return Response(str(r), mimetype="text/xml")
```

@app.route(”/get_ampm”, methods=[“GET”, “POST”])
def get_ampm():
digit = request.form.get(“Digits”, “”)
hour = app.config.get(“PENDING_HOUR”, 0)
minute = app.config.get(“PENDING_MINUTE”, 0)

```
if digit == "1":
    ampm = "AM"
elif digit == "2":
    ampm = "PM"
else:
    return say("Invalid selection. <break time='200ms'/> Goodbye!")

now = datetime.now(ET)
wake_hour = hour if ampm == "AM" else (hour + 12 if hour != 12 else 12)
if ampm == "AM" and hour == 12:
    wake_hour = 0

wake_time = now.replace(hour=wake_hour, minute=minute, second=0, microsecond=0)
if wake_time <= now:
    wake_time += timedelta(days=1)

day_name = wake_time.strftime("%A")
month_name = wake_time.strftime("%B")
day_ord = ordinal(wake_time.day)
display_hour = hour if hour != 0 else 12
time_spoken = f"{display_hour} {'00' if minute == 0 else minute} {ampm}"
date_spoken = f"{day_name}, {month_name} {day_ord}"

app.config["WAKE_TIME"] = wake_time
app.config["TIME_SPOKEN"] = time_spoken
app.config["DATE_SPOKEN"] = date_spoken

r = VoiceResponse()
gather = Gather(num_digits=1, action="/confirm", method="POST", timeout=10)
gather.say(ssml(
    f"You entered <break time='200ms'/> {date_spoken}, <break time='200ms'/> {time_spoken}. "
    f"<break time='500ms'/> "
    f"If this is correct, <break time='200ms'/> press one. "
    f"<break time='300ms'/> To start over, <break time='200ms'/> press two."
), voice=VOICE)
r.append(gather)
r.say(ssml("We didn't receive your input. <break time='300ms'/> Goodbye!"), voice=VOICE)
return Response(str(r), mimetype="text/xml")
```

@app.route(”/confirm”, methods=[“GET”, “POST”])
def confirm():
digit = request.form.get(“Digits”, “”)
if digit == “2”:
return redirect(”/incoming”)
if digit != “1”:
return say(“Invalid selection. <break time='200ms'/> Goodbye!”)

```
wake_time = app.config.get("WAKE_TIME")
time_spoken = app.config.get("TIME_SPOKEN")
date_spoken = app.config.get("DATE_SPOKEN")

if not wake_time:
    return say("Something went wrong. <break time='200ms'/> Please call back. Goodbye!")

if wakeup_job["sid"]:
    try:
        client = Client(ACCOUNT_SID, AUTH_TOKEN)
        client.calls(wakeup_job["sid"]).update(status="canceled")
    except:
        pass

now = datetime.now(ET)
now_utc = datetime.now(pytz.utc)
delay_seconds = (wake_time - now).total_seconds()
wake_time_utc = now_utc + timedelta(seconds=delay_seconds)

now_str = datetime.now(ET)
day_ord = ordinal(now_str.day)
hour_12 = now_str.strftime("%I").lstrip("0")
minute_str = now_str.strftime("%M")
ampm_str = now_str.strftime("%p").lower()
time_now = f"{hour_12}:{minute_str} {ampm_str}"

mickey_twiml = (
    f'<Response>'
    f'<Play>{MICKEY_MP3}</Play>'
    f'<Say voice="{VOICE}">'
    f'<speak>'
    f'The current time is <break time="200ms"/> {time_now} '
    f'<break time="300ms"/> on the {day_ord} of {now_str.strftime("%B")}, '
    f'{now_str.strftime("%Y")}.'
    f'</speak>'
    f'</Say>'
    f'</Response>'
)

client = Client(ACCOUNT_SID, AUTH_TOKEN)
call = client.calls.create(
    to=TO_NUMBER,
    from_=FROM_NUMBER,
    twiml=mickey_twiml,
    schedule_type="fixed",
    send_at=wake_time_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
)

wakeup_job["sid"] = call.sid
wakeup_job["time_str"] = time_spoken
wakeup_job["date_str"] = date_spoken

r = VoiceResponse()
gather = Gather(num_digits=1, action="/after_confirm", method="POST", timeout=10)
gather.say(ssml(
    f"You have a confirmed wakeup <break time='200ms'/> for {date_spoken}, "
    f"<break time='200ms'/> {time_spoken}. <break time='600ms'/> "
    f"Press one to hear your current wakeup settings."
), voice=VOICE)
r.append(gather)
r.say(ssml("Have a magical night!"), voice=VOICE)
return Response(str(r), mimetype="text/xml")
```

@app.route(”/after_confirm”, methods=[“GET”, “POST”])
def after_confirm():
digit = request.form.get(“Digits”, “”)
if digit == “1” and wakeup_job[“time_str”]:
return say(
f”Your current wakeup is set for {wakeup_job[‘date_str’]} “
f”<break time='200ms'/> at {wakeup_job[‘time_str’]}. “
f”<break time='400ms'/> Have a magical night!”
)
return say(“Have a magical night!”)

@app.route(”/ring”)
def ring():
now = datetime.now(ET)
day_ord = ordinal(now.day)
hour_12 = now.strftime(”%I”).lstrip(“0”)
minute_str = now.strftime(”%M”)
ampm_str = now.strftime(”%p”).lower()
time_now = f”{hour_12}:{minute_str} {ampm_str}”

```
r = VoiceResponse()
r.play(MICKEY_MP3)
r.say(ssml(
    f"The current time is <break time='200ms'/> {time_now} "
    f"<break time='300ms'/> on the {day_ord} of {now.strftime('%B')}, "
    f"{now.strftime('%Y')}."
), voice=VOICE)
return Response(str(r), mimetype="text/xml")
```

if **name** == “**main**”:
port = int(os.environ.get(“PORT”, 5000))
app.run(host=“0.0.0.0”, port=port)
