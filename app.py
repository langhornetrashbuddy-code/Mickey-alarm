from flask import Flask
from twilio.rest import Client
import os

app = Flask(__name__)

ACCOUNT_SID = "ACe12f3117ae792a3d7d12806d4b81f66c"
AUTH_TOKEN  = "1a6d256a12638877a5b5a4c2ffb08e0b"
FROM_NUMBER = "+16812726403"
TO_NUMBER   = "+12159627989"
MICKEY_MP3  = "https://drive.google.com/uc?id=1pD7ATjLY2u-tbCjJ7mwe7BTuqvkpjZzO"

@app.route("/")
def home():
    return "Mickey Morning Call is running!", 200

@app.route("/ring")
def ring():
    client = Client(ACCOUNT_SID, AUTH_TOKEN)
    client.calls.create(
        to=TO_NUMBER,
        from_=FROM_NUMBER,
        twiml='<Response><Play>' + MICKEY_MP3 + '</Play></Response>'
    )
    return "Calling!", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
