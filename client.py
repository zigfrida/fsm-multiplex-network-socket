import socket
import sys
import os
import time

HOST = "10.0.0.10"
PORT = 8000
SIZE = 2048
FORMAT = "utf-8"

def send_file(file_path, server_socket):

    if not os.path.exists(file_path):
        print(f"File {file_path} does not exist.")
        return

    file_name = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    file_info = f"{file_name}!{file_size}"
    print(f"Sending file: {file_name}, file size: {file_size}")

    with open(file_path, 'rb') as file:
        file_data = f"{file_info}!{file.read().decode()}"
        server_socket.sendall(file_data.encode())
    
    response = server_socket.recv(SIZE).decode()
    if response != "":
        print(f"Server: {response}")
        return


def main(files):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # Creating a socket object

    try:
        server_socket.connect((HOST, int(PORT)))
        print("Connected!")
    except ConnectionRefusedError:
        print("Server does not seem to be running.")
        return
    
    try:
        for file_path in files:
            send_file(file_path, server_socket)
            # print("Sleeping...")
            # time.sleep(5)
    except KeyboardInterrupt:
        print("\nUser Interruption. Exit client.")
        sys.exit(1)
    
    finally:
        server_socket.close()


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Missing required parameters: ./client <ip 4 or 6 address to connect to> <port> *.txt")
    else:
        HOST = sys.argv[1]
        PORT = sys.argv[2]
        files = sys.argv[3:]
        main(files)