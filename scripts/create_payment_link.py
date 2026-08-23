# De-risk script: create a Razorpay TEST Payment Link and open it in the browser.
# Run from the project root:  .venv/Scripts/python -m scripts.create_payment_link

import webbrowser

import razorpay

from backend.config import settings

client = razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))

# Amount is in PAISE: 50000 paise = 500 rupees.
link = client.payment_link.create({
    "amount": 50000,
    "currency": "INR",
    "description": "CartPilot test payment",
})

print("Payment link created!")
print("  id       :", link["id"])
print("  amount   :", link["amount"], "paise")
print("  status   :", link["status"])
print("  short_url:", link["short_url"])

# Open the hosted payment page in your default browser.
webbrowser.open(link["short_url"])
