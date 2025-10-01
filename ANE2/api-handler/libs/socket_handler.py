"""
@file socket_handler.py
@brief Utility functions for creating and cleaning up UNIX domain sockets.
"""

import socket
import os

def print(*args, **kwargs):
    """Overrides the built-in print for consistent log formatting."""
    __builtins__.print("[SocketHandler]", *args, **kwargs)

def clean_socket(socket_path):
    """
    Ensures a socket file at the given path is removed if it exists.
    This prevents "Address already in use" errors on startup.
    """
    if os.path.exists(socket_path):
        try:
            os.remove(socket_path)
            print(f"Removed stale socket file: {socket_path}")
        except OSError as e:
            print(f"Error removing socket file {socket_path}: {e}")

def create_socket(socket_path):
    """
    Creates and binds a UNIX domain socket.
    
    @param socket_path The file path to bind the socket to.
    @return The created and bound socket object.
    @raises Exception if socket creation or binding fails.
    """
    try:
        # Create the Unix domain socket
        server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        
        # Bind the socket to the path
        print(f"Binding socket to {socket_path}...")
        server_socket.bind(socket_path)
        print("Socket bound successfully.")
        return server_socket
    except Exception as e:
        print(f"Failed to create or bind socket at {socket_path}: {e}")
        # Re-raise the exception to be handled by the main application
        raise