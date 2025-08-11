from flask import Flask
from threading import Thread
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KeepAlive")

app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run():
    try:
        logger.info("Starting keep-alive server...")
        app.run(host="0.0.0.0", port=8080)
    except Exception as e:
        logger.error(f"Keep-alive server failed: {e}", exc_info=True)

def keep_alive():
    try:
        t = Thread(target=run)
        t.daemon = True  # Make sure thread closes with main program
        t.start()
        logger.info("Keep-alive thread started successfully.")
    except Exception as e:
        logger.error(f"Failed to start keep-alive thread: {e}", exc_info=True)
