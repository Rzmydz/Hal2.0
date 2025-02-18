from websocket import WebSocket
from websocket import create_connection
import os
import json
import random
import time
import logging
from config import *

# Configure logging - this will be overridden in __init__
#logging.basicConfig(
#    level=getattr(logging, LOG_LEVEL),
#    format=LOG_FORMAT
#)
logger = logging.getLogger(__name__)

class RVRBWebSocketClient:
    def __init__(self):
        self.url = f"{WS_URL}?apiKey={API_KEY}"
        self.channelId = None
        self.password = PASSWORD
        self.ws = None
        self.latency = 0
        self.reconnect = True
        self.joinId = None
        self.reconnect_attempts = 0
        logging.basicConfig(level=logging.DEBUG)  # Set logging to DEBUG level
        logger.info(f"Initializing WebSocket client with URL: {WS_URL} (API key hidden)")

    def join(self):
        """Attempt to join channel"""
        self.joinId = round(random.random() * 100)
        join_request = {
            "method": "join",
            "params": {
                "channelId": self.channelId
            },
            "id": self.joinId
        }
        if self.password:
            join_request["params"]["password"] = self.password

        self._send_message(join_request)
        logger.info(f"Attempting to join channel {self.channelId}")

    def _send_message(self, message):
        """Safely send a message through websocket"""
        try:
            if self.ws and self.ws.connected:
                self.ws.send(json.dumps(message))
            else:
                logger.error("WebSocket connection not established")
        except Exception as e:
            logger.error(f"Error sending message: {e}")

    def _handle_message(self):
        """Handle incoming messages"""
        while self.ws and self.ws.connected:
            try:
                message = self.ws.recv()
                if message:
                    data = json.loads(message)
                    logger.debug(f"Received message: {message}")

                    event_handlers = {
                        "keepAwake": self.keep_awake,
                        "ready": self.ready,
                        "pushChannelMessage": self.handle_channel_message,
                        "pushNotification": self.handle_notification,
                        "updateChannel": self.handle_channel_update,
                        "updateChannelUsers": self.handle_users_update,
                        "updateUser": self.handle_user_update,
                        "updateChannelDjs": self.handle_djs_update,
                        "updateChannelMeter": self.handle_meter_update,
                        "updateChannelUserStatus": self.handle_user_status,
                        "leaveChannel": self.handle_leave,
                        "playChannelTrack": self.handle_track_play,
                        "pauseChannelTrack": self.handle_track_pause
                    }

                    if 'method' in data and data['method'] in event_handlers:
                        event_handlers[data['method']](data)
                    elif 'id' in data and data['id'] == self.joinId:
                        if 'error' in data:
                            logger.error(f"Error joining channel: {data['error']['message']}")
                        else:
                            logger.info(f"Successfully joined channel {self.channelId}")

            except json.JSONDecodeError as e:
                logger.error(f"Error decoding message: {e}")
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                if not self.ws or not self.ws.connected:
                    break

    def keep_awake(self, data):
        """Handle keepAwake messages"""
        self.latency = data["params"]["latency"]
        logger.debug(f"Latency: {self.latency}ms")

        self._send_message({
            "jsonrpc": "2.0",
            "method": "stayAwake",
            "params": {
                "date": int(time.time() * 1000)
            }
        })

    def ready(self, data):
        """Handle ready event"""
        if "params" in data and "channelId" in data["params"]:
            self.channelId = data["params"]["channelId"]
        self.join()

    def handle_channel_message(self, data):
        """Handle channel messages"""
        try:
            # Log the raw message data
            logger.debug(f"Raw message data: {repr(data)}")

            params = data.get("params", {})
            logger.debug(f"Message params: {repr(params)}")

            # Extract message using multiple possible paths
            message = None
            if isinstance(params, dict):
                # Try different possible message locations
                if "payload" in params:
                    message = params["payload"]
                elif "message" in params:
                    message = params["message"]
                elif "content" in params:
                    message = params["content"]
                elif isinstance(params.get("data"), dict):
                    message = params["data"].get("message") or params["data"].get("content")

            logger.debug(f"Extracted raw message: {repr(message)}")

            # Normalize message if it exists
            if message:
                # Convert to string if not already
                message = str(message).strip()
                logger.debug(f"Normalized message: {repr(message)}")

                if message.lower() == "~ping":
                    logger.info("Detected ~ping command, sending ~pong response")
                    response = {
                        "jsonrpc": "2.0",
                        "method": "sendChannelMessage",
                        "params": {
                            "channelId": self.channelId,
                            "type": "chat",
                            "payload": "~pong"
                        }
                    }
                    logger.debug(f"Sending response: {repr(response)}")
                    self._send_message(response)
                    logger.info("Sent ~pong response")

        except Exception as e:
            logger.error(f"Error in handle_channel_message: {e}")
            logger.error(f"Error occurred with data: {json.dumps(data, indent=2)}")

    def handle_notification(self, data):
        """Handle notifications"""
        logger.info(f"Notification: {data['params']}")

    def handle_channel_update(self, data):
        """Handle channel updates"""
        logger.info(f"Channel update: {data['params']}")

    def handle_users_update(self, data):
        """Handle users update"""
        logger.info(f"Users update: {data['params']}")

    def handle_user_update(self, data):
        """Handle user update"""
        logger.info(f"User update: {data['params']}")

    def handle_djs_update(self, data):
        """Handle DJs update"""
        logger.info(f"DJs update: {data['params']}")

    def handle_meter_update(self, data):
        """Handle meter update"""
        logger.info(f"Meter update: {data['params']}")

    def handle_user_status(self, data):
        """Handle user status update"""
        logger.info(f"User status update: {data['params']}")

    def handle_leave(self, data):
        """Handle leave channel command"""
        logger.info("Received leave channel command")
        self.reconnect = False
        if self.ws and self.ws.connected:
            self.ws.close()

    def handle_track_play(self, data):
        """Handle track play event"""
        logger.info(f"Track playing: {data['params']}")

    def handle_track_pause(self, data):
        """Handle track pause event"""
        logger.info(f"Track paused: {data['params']}")

    def connect(self):
        """Establish WebSocket connection"""
        while self.reconnect_attempts < MAX_RECONNECT_ATTEMPTS:
            try:
                logger.info("Starting WebSocket connection...")
                self.ws = create_connection(
                    self.url,
                    ping_interval=PING_INTERVAL,
                    ping_timeout=PING_TIMEOUT
                )

                if self.ws.connected:
                    logger.info("WebSocket connection established")
                    self.reconnect_attempts = 0
                    self._handle_message()
                else:
                    raise Exception("Failed to establish WebSocket connection")

            except Exception as e:
                logger.error(f"Connection error: {e}")
                if self.reconnect:
                    self.reconnect_attempts += 1
                    logger.info(f"Attempting to reconnect... (Attempt {self.reconnect_attempts})")
                    time.sleep(RECONNECT_DELAY)
                else:
                    break

        if self.reconnect_attempts >= MAX_RECONNECT_ATTEMPTS:
            logger.error("Max reconnection attempts reached")

if __name__ == "__main__":
    if not API_KEY:
        logger.error("API key not found in environment variables")
        exit(1)

    logger.info("Starting RVRB WebSocket Client...")
    client = RVRBWebSocketClient()
    client.connect()