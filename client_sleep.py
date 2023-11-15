import socket
import sys
import os
import time

HOST = "127.0.0.1"
PORT = 5432
SIZE = 2048
FORMAT = "utf-8"

class StateMachine:

    def __init__(self, host, port, files):
        self.host = host
        self.port = port
        self.files = files
        self.message = None
        self.errormsg = None
        self.server_socket = None

    def connect(self):
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # Creating a socket object
            self.server_socket.connect((HOST, int(PORT)))
            self.message = "Connected!"
            return "SENDING_FILES"
        except ConnectionRefusedError:
            self.errormsg = "Server does not seem to be running."
            return "ERROR"
        
    def send_file(self, file_path):
        if not os.path.exists(file_path):
            self.message = f"File {file_path} does not exist."
            return

        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        file_info = f"{file_name}!{file_size}"
        print(f"Sending file: {file_name}, file size: {file_size}")

        with open(file_path, 'rb') as file:
            file_data = f"{file_info}!{file.read().decode()}"
            self.server_socket.sendall(file_data.encode())
        
        response = self.server_socket.recv(SIZE).decode()
        if response != "":
            self.message = f"Server: {response}"
            return

    def send_files(self):
        try:
            for file_path in files:
                self.send_file(file_path)
                time.sleep(5)
            self.message = "All files sent."
            return "EXIT"
        except KeyboardInterrupt:
            self.errormsg = "User Interruption. Exit client."
            return "ERROR"

    def close(self):
        self.server_socket.close()

    def error(self):
        print(self.errormsg)
        return "EXIT"

    def run(self):
        state = "CONNECTING"
        while state != "EXIT":
            print("Current state: " + state)
            if state == "CONNECTING":
                state = self.connect()
            elif state == "SENDING_FILES":
                state = self.send_files()
            elif state == "ERROR":
                state = self.error()

            if self.message:
                print(self.message)

        print("Current state: " + state)
        self.close()        


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Missing required parameters: ./client <ip 4 or 6 address to connect to> <port> *.txt")
    else:

        HOST = sys.argv[1]
        PORT = sys.argv[2]
        files = sys.argv[3:]
        fsm = StateMachine(HOST, PORT, files)
        fsm.run()
    


