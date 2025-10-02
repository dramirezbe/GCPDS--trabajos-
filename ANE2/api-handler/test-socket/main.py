import socket
import os
import json
import time

# A simple logger-like function for demonstration
def logger(level, message):
    print(f"[{level.upper()}] {message}")

def clean_socket(socket_path):
    """
    Ensures a socket file at the given path is removed if it exists.
    This prevents "Address already in use" errors on startup.
    """
    if os.path.exists(socket_path):
        try:
            os.remove(socket_path)
            logger("info", f"Removed stale socket file: {socket_path}")
        except OSError as e:
            logger("error", f"Error removing socket file {socket_path}: {e}")

def create_socket(socket_path):
    """
    Creates and binds a UNIX domain socket.

    @param socket_path The file path to bind the socket to.
    @return The created and bound socket object.
    @raises Exception if socket creation or binding fails.
    """
    try:
        server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        logger("info", f"Binding socket to {socket_path}...")
        server_socket.bind(socket_path)
        logger("info", "Socket bound successfully.")
        return server_socket
    except Exception as e:
        logger("error", f"Failed to create or bind socket at {socket_path}: {e}")
        raise

def main():
    socket_path = "/tmp/my_unix_socket"
    clean_socket(socket_path)

    try:
        server_socket = create_socket(socket_path)
        server_socket.listen(1)

        # This is the main server superloop
        while True:
            logger("info", "Waiting for a client to connect...")
            
            # accept() blocks here until a client connects.
            # The 'if/else' is not needed.
            connection, _ = server_socket.accept()
            
            try:
                logger("info", "Client connected.")

                # 1. Define and send the job to the client
                job_to_send = {"service": "acquire", "timeService": "5seconds"}
                message = json.dumps(job_to_send).encode('utf-8')

                logger("info", f"Sending job to client: {job_to_send}")
                connection.sendall(message)

                # 2. Wait for the processed data from the client
                logger("info", "Waiting for processed data from client...")
                data_received = connection.recv(1024)

                if data_received:
                    try:
                        decoded_data = data_received.decode('utf-8')
                        result_data = json.loads(decoded_data)
                        logger("info", f"Received result from client: {result_data}")

                        # 3. Master Logic: Validate the result from the slave
                        original_service = result_data.get("original_service")
                        result_code = result_data.get("result_code")

                        if result_code == 0 and original_service == job_to_send["service"]:
                            time_taken = result_data.get("time_taken", "N/A")
                            logger("info", f"SUCCESS: Client completed job '{original_service}' in {time_taken} seconds.")
                        else:
                            error_message = result_data.get("message", "No details provided.")
                            logger("error", f"FAILURE: Client reported an error for job '{original_service}'. Details: {error_message}")

                    except (json.JSONDecodeError, UnicodeDecodeError) as e:
                        logger("error", f"Could not decode or parse client's response: {e}")
                else:
                    # This happens if the client connects and immediately disconnects without sending data.
                    logger("error", "Connection established, but no data received from client.")
            
            except socket.error as e:
                # This can catch errors during sendall() or recv()
                logger("error", f"A socket error occurred during communication: {e}")

            finally:
                # This block ensures the connection is always closed,
                # preparing the server for the next client.
                logger("info", "Closing client connection.")
                connection.close()
                time.sleep(1) # Optional small delay

    except Exception as e:
        logger("error", f"A critical server error occurred: {e}")
    finally:
        clean_socket(socket_path)

if __name__ == "__main__":
    main()