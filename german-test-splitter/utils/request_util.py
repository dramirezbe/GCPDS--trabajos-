"""
@file utils/request_util.py
@brief Simple reusable HTTP client helper with rc codes and print-based logging.
"""

import requests
from typing import Optional, Tuple, Dict, Any
import zmq
import json
import asyncio
# Import the asynchronous context and socket from pyzmq
import zmq.asyncio as azmq

class RequestClient:
    """
    Lightweight HTTP client with unified return codes and internal logging.

    Return codes:
        0 -> success (HTTP 2xx)
        1 -> known network/server/client error
        2 -> unexpected error
    """

    def __init__(
        self,
        base_url: str,
        timeout: Tuple[float, float] = (5, 15),
        verbose: bool = False,
        logger=None,
        api_key: str = "",
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.verbose = verbose
        self._log = logger
        self.api_key = api_key # Stored API key

    # -------------------------------------------------------------------------
    # Public methods
    # -------------------------------------------------------------------------
    def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Tuple[int, Optional[requests.Response]]:
        # Add default Accept header for GET
        hdrs = {"Accept": "application/json"}
        if headers:
            hdrs.update(headers)
        return self._send_request("GET", endpoint, headers=hdrs, params=params)

    def post_json(
        self,
        endpoint: str,
        json_dict: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
    ) -> Tuple[int, Optional[requests.Response]]:
        try:
            body = json.dumps(json_dict).encode("utf-8")
        except Exception as e:
            if self._log:
                self._log.error(f"[HTTP] JSON serialization error: {e}")
            return 2, None

        # Add default Content-Type header for POST_JSON
        hdrs = {"Content-Type": "application/json"}
        if headers:
            hdrs.update(headers)
        return self._send_request("POST", endpoint, headers=hdrs, data=body)

    # -------------------------------------------------------------------------
    # Internal unified handler
    # -------------------------------------------------------------------------
    def _send_request(
        self,
        method: str,
        endpoint: str,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[bytes] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Tuple[int, Optional[requests.Response]]:

        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        # --- NEW LOGIC: Add API Key Authorization Header ---
        final_headers = headers if headers is not None else {}
        if self.api_key and "Authorization" not in final_headers:
            # Ensure the Authorization header is set if an API key exists
            final_headers["Authorization"] = f"ApiKey {self.api_key}"
            
        if self.verbose and self._log:
            self._log.info(f"[HTTP] Authorization header set: {'Authorization' in final_headers}")
        # --------------------------------------------------

        try:
            if self.verbose and self._log:
                # Log URL and method
                self._log.info(f"[HTTP] {method} → {url}")
                # Optional: Log headers to confirm API key is present (use with caution)
                # self._log.info(f"[HTTP] Headers: {final_headers}")

            resp = requests.request(
                method,
                url,
                headers=final_headers, # Use final_headers with API key
                data=data,
                params=params,
                timeout=self.timeout,
            )

            # Success
            if 200 <= resp.status_code < 300:
                if self.verbose and self._log:
                    self._log.info(f"[HTTP] success rc={resp.status_code}")
                return 0, resp

            # Known HTTP errors
            # ... (Existing error handling logic remains the same)
            if 300 <= resp.status_code < 400:
                msg = f"[HTTP] redirect rc={resp.status_code}"
            elif 400 <= resp.status_code < 500:
                msg = f"[HTTP] client error rc={resp.status_code}"
            elif 500 <= resp.status_code < 600:
                msg = f"[HTTP] server error rc={resp.status_code}"
            else:
                msg = f"[HTTP] unknown status rc={resp.status_code}"

            if self._log:
                self._log.error(msg)
            return 1, resp

        except requests.exceptions.Timeout:
            if self._log:
                self._log.error("[HTTP] timeout")
            return 1, None

        except requests.exceptions.ConnectionError as e:
            if self._log:
                self._log.error(f"[HTTP] connection error: {e}")
            return 1, None

        except requests.exceptions.RequestException as e:
            if self._log:
                self._log.error(f"[HTTP] request exception: {e}")
            return 1, None

        except Exception as e:
            if self._log:
                self._log.error(f"[HTTP] unexpected error: {e}")
            return 2, None
        

# --- Publisher Class (UNCHANGED) ---
class ZmqPub:
    def __init__(self, verbose=False, log=None):
        self.verbose = verbose
        self._log = log
        # Use standard zmq.Context for a synchronous publisher
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUB)
        self.socket.bind("tcp://*:5555")

    def public_client(self, client_str:str, payload:dict):
        """Sends a message with a topic prefix."""
        json_msg = json.dumps(payload)
        # Format: "TOPIC_STRING JSON_PAYLOAD"
        full_msg = f"{client_str} {json_msg}" 
        self.socket.send_string(full_msg)
        if self.verbose:
            print(f"Publisher sent: '{full_msg}'")

    def close(self):
        """Closes the socket and terminates the context."""
        if hasattr(self, 'socket'):
            self.socket.close()
        if hasattr(self, 'context'):
            self.context.term()

# --- Subscriber Class (ASYNC IMPLEMENTATION) ---
class ZmqSub:
    def __init__(self, verbose=False, log=None, topic:str=""):
        self.verbose = verbose
        self._log = log
        # Use asynchronous context and socket
        self.context = azmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.connect("tcp://localhost:5555")
        
        self.topic = topic
        # Subscribing to the topic
        self.socket.subscribe(self.topic.encode('utf-8'))
        
        if self.verbose:
             print(f"ZmqSub: Subscribed to topic '{self.topic}' on tcp://localhost:5555")

    # The wait_msg method must be an async function
    async def wait_msg(self):
        """
        Asynchronously waits for and receives a message from the socket.
        It handles filtering (though ZMQ also filters).
        """
        while True:
            # 1. Block ASYNCHRONOUSLY and wait for a message
            # We use await self.socket.recv_string() which is now a coroutine
            # provided by the azmq.Socket.
            full_msg = await self.socket.recv_string()

            # 2. Split the string into the topic and the JSON part
            pub_topic, json_msg = full_msg.split(" ", 1)

            # 3. Check if the published topic matches (explicit check)
            if pub_topic == self.topic:
                if self.verbose:
                    print(f"Subscriber received matching message on topic '{self.topic}'")
                # 4. If it matches, deserialize the JSON and return the payload
                return json.loads(json_msg)
            
            # The loop continues if the message was received but the topic didn't match.

    def close(self):
        """Closes the socket and terminates the context."""
        if hasattr(self, 'socket'):
            self.socket.close()
        if hasattr(self, 'context'):
            # The asynchronous context also has a term method
            self.context.term()

