from flask import Flask
from twilio.rest import Client
from datetime import datetime
import pytz, os

app = Flask(__name__)

ACCOUNT_SID = "ACe12f3117ae792a3d7d12806d4b81f66c"
AUTH_TOKEN  = "your_current_auth_token_here"
FROM_NUMBER = "+16812726403"
TO_NUMBER   = "+12159627989"
MICKEY_MP3  = "https://drive.google.com/uc?id=1pD7ATjLY2u-tbCjJ7mwe7BTuqvkpjZzO"

def ordinal(n):
    if 11 <= n <= 13:
        return f"{n}th"
    return f"{n}{['th','st','nd','rd','th','th','th','th','th','th'][n%10]}"

@app.route("/")
def home():
    return "Mickey Morning Call is running!", 200

@app.route("/ring")
def ring():
    et = pytz.timezone("America/New_York")
    now = datetime.now(et)
    hour = now.strftime("%I").lstrip("0")
    minute = now.strftime("%M")
    ampm = now.strftime("%p").lower()
    day = ordinal(now.day)
    month = now.strftime("%B")
    year = now.strftime("%Y")

    time_str = f"{hour}:{minute} {ampm}"
    speech = f"The current time is {time_str} on the {day} of {month}, {year}."

    client = Client(ACCOUNT_SID, AUTH_TOKEN)
    client.calls.create(
        to=TO_NUMBER,
        from_=FROM_NUMBER,
        twiml=f'''<Response>
  <Play>{MICKEY_MP3}</Play>
  <Say voice="Polly.Joanna-Neural">{speech}</Say>
</Response>'''
    )
    return "Calling!", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
