import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# WebSocket Configuration
WS_URL = "wss://app.rvrb.one/ws-bot"
API_KEY = os.getenv('RVRB_API_KEY')
PASSWORD = os.getenv('RVRB_PASSWORD')

# Connection settings
RECONNECT_DELAY = 5  # seconds
MAX_RECONNECT_ATTEMPTS = 3
PING_INTERVAL = 30  # seconds
PING_TIMEOUT = 10  # seconds

# Logging configuration
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
