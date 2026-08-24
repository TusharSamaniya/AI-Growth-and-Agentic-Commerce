# Subscribes to the SSE stream and prints the first event, proving the endpoint
# streams. A real UI would keep this open (new EventSource("/events")) and react
# to each message. Needs the server running in another terminal:
#     uvicorn backend.main:app --reload
# Then, from the project root:  python -m scripts.try_sse

import sys

import httpx

sys.stdout.reconfigure(encoding="utf-8")

url = "http://127.0.0.1:8000/events"
print("Subscribing to", url, "...")
with httpx.stream("GET", url, timeout=None) as response:
    for line in response.iter_lines():
        if line:                          # ignore the blank separator lines
            print("received:", line)
        if line.startswith("data:"):      # got our first real event -> done
            break
print("Stream works. A browser would keep this open and react to each message.")
