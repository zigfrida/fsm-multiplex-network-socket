import socket
import select
import sys
import os
import queue
import signal

HOST = "127.0.0.1"
PORT = 5432
SIZE = 2048
FORMAT = "utf-8"

class ServerStateMachine:
    def __init__(self, host, port, storage_directory):
        self.host = host
        self.port = port
        self.storage_directory = storage_directory
        self.server_socket = None
        self.inputs = []
        self.outputs = []
        self.message_queues = {}
        self.running = True
        self.state = "STARTING"

    def signal_handler(self, sig, frame):
        self.running = False
        print("Current State: EXIT")
        print("\nUser Interruption. Shutting down server.")
        self.handle_closing_connections_state()
        self.handle_stopping_server_state()

    def socket(self):
        try:
            # print("[STARTING] server is starting...")
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.state = "BIND"
        except Exception as e:
            print(f"Error in SOCKET state: {e}")
            self.state = "ERROR"
    
    def bind(self):
        try:
            self.server_socket.bind((self.host, int(self.port)))
            self.state = "LISTEN"
        except Exception as e:
            print(f"Error in BIND state: {e}")
            self.state = "ERROR"

    def listen(self):
        try:
            self.server_socket.listen()
            # print(f"[LISTEN] Server is listening on {self.host}:{self.port}")
            self.inputs = [self.server_socket]
            self.state = "ACCEPTING"
        except Exception as e:
            print(f"Error in LISTEN state: {e}")
            self.state = "ERROR"

    def accept_state(self):
        readable, _, _ = select.select(self.inputs, [], self.inputs)
        for s in readable:
            if s is self.server_socket:
                conn, addr = s.accept()
                conn.setblocking(0)
                self.inputs.append(conn)
                self.message_queues[conn] = queue.Queue()
                print(f"[NEW CONNECTION] Connected by {addr}")
                print(f"[ACTIVE CONNECTIONS] {len(self.inputs) - 1}")
                self.state = "PROCESSING_CONNECTIONS"

    def process_connections(self):
        while self.running:
            try:
                if self.state == "ACCEPTING":
                    self.accept_state()
                elif self.state == "PROCESSING_CONNECTIONS":
                    self.handle_processing_connections_state()
                elif self.state == "ERROR":
                    self.handle_error_state()
                elif self.state == "CLOSING_CONNECTIONS":
                    self.handle_closing_connections_state()
                elif self.state == "STOPPING_SERVER":
                    self.handle_stopping_server_state()

            except KeyboardInterrupt:
                print("Exception")
                self.running = False
            except Exception as e:
                print(f"An error occurred: {e}")
                self.state = "ERROR"

        for s in self.inputs:
            if s is not self.server_socket:
                s.close()
        if self.server_socket:
            self.server_socket.close()
        sys.exit(0)

    def handle_processing_connections_state(self):
        readable, writable, exceptional = select.select(self.inputs, self.outputs, self.inputs)
        for s in readable:
            if s is self.server_socket:
                conn, addr = s.accept()
                conn.setblocking(0)
                self.inputs.append(conn)
                self.message_queues[conn] = queue.Queue()
                print(f"[NEW CONNECTION] Connected by {addr}")
                print(f"[ACTIVE CONNECTIONS] {len(self.inputs) - 1}")
            else:
                data = s.recv(SIZE)

                if not data:
                    # No more data, close the connection
                    print(f"[CLOSED CONNECTION] No more data. Connection Closed.")
                    if s in self.outputs:
                        self.outputs.remove(s)
                    self.inputs.remove(s)
                    print(f"[ACTIVE CONNECTIONS] {len(self.inputs) - 1}")
                    s.close()
                    del self.message_queues[s]
                else:
                    # Process the received data
                    if b"!" in data:
                        file_name, file_size_str, content = data.split(b"!", 2)
                        file_size = int(file_size_str)
                        file_name = file_name.decode()
                        file_path = os.path.join(self.storage_directory, file_name)

                        already_exist = os.path.exists(file_path)

                        with open(file_path, "wb") as file:
                            file.write(content)  # Write the received content

                        if already_exist:
                            self.message_queues[s].put(f"File {file_name} already exists. Content replaced!".encode())
                        else:
                            self.message_queues[s].put(f"File: {file_name} has been saved.".encode())

                        if s not in self.outputs:
                            self.outputs.append(s)

        for s in writable:
            try:
                next_msg = self.message_queues[s].get_nowait()
            except queue.Empty:
                self.outputs.remove(s)
            else:
                print(f"[SEND] {next_msg.decode()}")
                s.send(next_msg)

        for s in exceptional:
            self.inputs.remove(s)
            if s in self.outputs:
                self.outputs.remove(s)
            s.close()
            del self.message_queues[s]
            print(f"[ACTIVE CONNECTIONS] {len(self.inputs) - 1}")

    def handle_error_state(self):
        print("Error state. Transitioning to STOPPING_SERVER.")
        self.state = "STOPPING_SERVER"

    def handle_closing_connections_state(self):
        for s in self.inputs:
            if s is not self.server_socket:
                s.close()
        self.inputs = []
        self.state = "STOPPING_SERVER"

    def handle_stopping_server_state(self):
        print("Server stopped.")
        sys.exit(0)

    def run(self):
        signal.signal(signal.SIGINT, self.signal_handler)
        while self.running:
            print("Current state: " + self.state)
            try:
                if self.state == "STARTING":
                    self.socket()
                elif self.state == "BIND":
                    self.bind()
                elif self.state == "LISTEN":
                    self.listen()
                elif self.state == "ACCEPTING":
                    self.accept_state()
                elif self.state == "PROCESSING_CONNECTIONS":
                    self.process_connections()
            except KeyboardInterrupt:
                print("Keyboard interruption!")
                self.running = False


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Missing required parameters: ./server <ip 4 or 6 address to bind to> <port> ./directory-to-store-files")
    else:
        HOST = sys.argv[1]
        PORT = sys.argv[2]
        storage_directory = sys.argv[3]

        if not os.path.exists(storage_directory):
            os.makedirs(storage_directory)
            print("Storage directory created!")

        server_fsm = ServerStateMachine(HOST, PORT, storage_directory)
        server_fsm.run()
