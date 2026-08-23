# De-risk script: prove our Razorpay TEST keys work by creating a real test Order.
# Run from the project root:  .venv/Scripts/python -m scripts.create_order

import razorpay

from backend.config import settings

# Build the client once, using the keys loaded from .env.
client = razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))

# Razorpay amounts are in PAISE (the smallest unit): 50000 paise = 500 rupees.
order = client.order.create({
    "amount": 50000,
    "currency": "INR",
    "receipt": "cartpilot_test_1",
})

# Print the key fields Razorpay returned.
print("Order created!")
print("  id      :", order["id"])
print("  amount  :", order["amount"], "paise")
print("  currency:", order["currency"])
print("  status  :", order["status"])
