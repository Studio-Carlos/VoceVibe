"""
OSC (Open Sound Control) client for sending messages over UDP.
Thread-safe implementation.
"""
import threading
from typing import Optional
from pythonosc import udp_client
from pythonosc.osc_message_builder import OscMessageBuilder


class OSCClient:
    """
    Thread-safe OSC client for sending messages to a remote host.
    """
    
    def __init__(self, target_ip: str, target_port: int):
        """
        Initialize OSC client.
        
        Args:
            target_ip: IP address of the target OSC server
            target_port: Port number of the target OSC server
        """
        self.target_ip = target_ip
        self.target_port = target_port
        self._client: Optional[udp_client.UDPClient] = None
        self._lock = threading.Lock()
        self._connected = False
    
    def connect(self):
        """Connect to the OSC server."""
        with self._lock:
            if not self._connected:
                try:
                    self._client = udp_client.SimpleUDPClient(
                        self.target_ip,
                        self.target_port
                    )
                    self._connected = True
                    print(f"[OSC] Connected to {self.target_ip}:{self.target_port}")
                except Exception as e:
                    print(f"[OSC] Connection error: {e}")
                    self._connected = False
    
    def disconnect(self):
        """Disconnect from the OSC server."""
        with self._lock:
            self._connected = False
            self._client = None
            print("[OSC] Disconnected")
    
    def send(self, address: str, *args):
        """
        Send an OSC message.
        
        Args:
            address: OSC address path (e.g., "/visual/prompt")
            *args: Arguments to send (will be auto-typed)
        """
        with self._lock:
            if not self._connected or self._client is None:
                print(f"[OSC] Not connected, cannot send to {address}")
                return
            
            try:
                self._client.send_message(address, args)
                print(f"[OSC] Sent to {address}: {args}")
            except Exception as e:
                print(f"[OSC] Send error: {e}")
    
    def send_json_prompt(self, prompt_data: dict):
        """
        Send a visual prompt as JSON via OSC.
        
        Args:
            prompt_data: Dictionary containing prompt, style, mood, etc.
        """
        # Send as separate messages for better compatibility
        self.send("/visual/prompt", prompt_data.get("prompt", ""))
        self.send("/visual/style", prompt_data.get("style", ""))
        self.send("/visual/mood", prompt_data.get("mood", ""))
        
        # Also send full JSON as string for flexibility
        import json
        self.send("/visual/json", json.dumps(prompt_data))
    
    def update_target(self, ip: str, port: int):
        """
        Update target IP and port, reconnecting if needed.
        
        Args:
            ip: New IP address
            port: New port number
        """
        was_connected = self._connected
        if was_connected:
            self.disconnect()
        
        self.target_ip = ip
        self.target_port = port
        
        if was_connected:
            self.connect()

