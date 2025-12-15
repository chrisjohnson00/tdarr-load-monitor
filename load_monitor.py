#!/usr/bin/env python3
"""
Load monitor script that listens for webhooks and checks system load on trigger.
"""

import os
import requests
import logging
from flask import Flask, jsonify

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Configuration from environment variables with defaults
API_URL = os.getenv("API_URL", "http://192.168.1.131:8265")
GET_NODES_URL = f"{API_URL}/api/v2/get-nodes"
TARGET_NODE_NAME = os.getenv("TARGET_NODE_NAME", "r10-ubuntu")
WORKER_TYPE = os.getenv("WORKER_TYPE", "transcodecpu")
LOW_THRESHOLD = int(os.getenv("LOW_THRESHOLD", "12"))  # <= 12 => increase
HIGH_THRESHOLD = int(os.getenv("HIGH_THRESHOLD", "24"))  # >= 24 => decrease
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "5000"))

NODE_ID = None  # Will be set on startup


def get_node_id_from_api() -> str:
    """Fetch the node ID for the target node from the API."""
    try:
        response = requests.get(GET_NODES_URL, timeout=10)
        response.raise_for_status()
        nodes = response.json()

        for node_id, node_data in nodes.items():
            if node_data.get("nodeName") == TARGET_NODE_NAME:
                logger.info(f"Found target node '{TARGET_NODE_NAME}' with ID: {node_id}")
                return node_id

        logger.error(f"Target node '{TARGET_NODE_NAME}' not found in API response")
        raise ValueError(f"Node '{TARGET_NODE_NAME}' not found")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch nodes from API: {e}")
        raise


def get_load_avg_1m() -> float:
    """Get the 1-minute load average."""
    return os.getloadavg()[0]


def post_process_change(process: str) -> None:
    """Post a process change request to the API."""
    payload = {
        "data": {
            "nodeID": NODE_ID,
            "process": process,
            "workerType": WORKER_TYPE
        }
    }

    try:
        response = requests.post(API_URL, json=payload, timeout=10)
        response.raise_for_status()
        logger.info(f"Successfully posted '{process}' request. Status: {response.status_code}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to post '{process}' request: {e}")


def check_load_and_post() -> dict:
    """Check system load and post appropriate action. Returns status dict."""
    try:
        load_1m = get_load_avg_1m()
        logger.info(f"Current 1m load average: {load_1m:.2f}")

        if load_1m <= LOW_THRESHOLD:
            logger.info(f"Load ({load_1m:.2f}) <= {LOW_THRESHOLD}, requesting increase")
            post_process_change("increase")
            return {
                "success": True,
                "load": load_1m,
                "action": "increase"
            }
        elif load_1m >= HIGH_THRESHOLD:
            logger.info(f"Load ({load_1m:.2f}) >= {HIGH_THRESHOLD}, requesting decrease")
            post_process_change("decrease")
            return {
                "success": True,
                "load": load_1m,
                "action": "decrease"
            }
        else:
            logger.info(f"Load ({load_1m:.2f}) is between thresholds, no action taken")
            return {
                "success": True,
                "load": load_1m,
                "action": "none"
            }
    except Exception as e:
        logger.error(f"Error during load check: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook endpoint that triggers load check."""
    logger.info("Webhook triggered, checking system load...")
    result = check_load_and_post()
    return jsonify(result), 200 if result["success"] else 500


def main() -> None:
    """Initialize and start the webhook server."""
    global NODE_ID
    logger.info("Starting load monitor webhook server...")

    try:
        NODE_ID = get_node_id_from_api()
    except Exception as e:
        logger.critical(f"Failed to initialize NODE_ID: {e}")
        return

    logger.info(f"NODE_ID initialized: {NODE_ID}")
    logger.info(f"Starting Flask webhook server on port {WEBHOOK_PORT}")
    logger.info(f"Webhook endpoint: http://localhost:{WEBHOOK_PORT}/webhook")

    app.run(host='0.0.0.0', port=WEBHOOK_PORT, debug=False)


if __name__ == "__main__":
    main()
