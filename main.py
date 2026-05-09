from flask import Flask, request, Response, jsonify, make_response
from openai import OpenAI, InvalidWebhookSignatureError
import asyncio
import json
import os
import requests
import time
import threading
import websockets

app = Flask(__name__)
client = OpenAI(
    webhook_secret=os.environ["OPENAI_WEBHOOK_SECRET"]
)

AUTH_HEADER = {
    "Authorization": "Bearer " + os.getenv("OPENAI_API_KEY")
}

call_accept = {
    "type": "realtime",
    "instructions": "You are a voice agent for a user named Gabe.",
    "model": "gpt-realtime-mini",
}

response_create = {
    "type": "response.create",
    "response": {
        "instructions": (
            "Wait 10 seconds and then say to the user 'Hello, Gabe. I'm your AI assistant. How can I help you today?'"
        )
    },
}


async def websocket_task(call_id):
    try:
        async with websockets.connect(
            "wss://api.openai.com/v1/realtime?call_id=" + call_id,
            additional_headers=AUTH_HEADER,
        ) as websocket:
            await websocket.send(json.dumps(response_create))

            while True:
                response = await websocket.recv()
                print(f"Received from WebSocket: {response}")
    except Exception as e:
        print(f"WebSocket error: {e}")


@app.route("/", methods=["POST"])
def webhook():
    try:
        event = client.webhooks.unwrap(request.data, request.headers)

        if event.type == "realtime.call.incoming":
            requests.post(
                "https://api.openai.com/v1/realtime/calls/"
                + event.data.call_id
                + "/accept",
                headers={**AUTH_HEADER, "Content-Type": "application/json"},
                json=call_accept,
            )
            threading.Thread(
                target=lambda: asyncio.run(
                    websocket_task(event.data.call_id)
                ),
                daemon=True,
            ).start()
            return Response(status=200)
    except InvalidWebhookSignatureError as e:
        print("Invalid signature", e)
        return Response("Invalid signature", status=400)

@app.route("/test", methods=["GET"])
def test():
    return "It works!"


if __name__ == "__main__":
    app.run(port=8000)