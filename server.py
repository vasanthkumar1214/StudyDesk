import socket
import threading
from datetime import datetime


HOST = "0.0.0.0"
PORT = 8080
BUFFER_SIZE = 1024

clients = {}
clients_lock = threading.Lock()


def timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(message):
    print(f"[{timestamp()}] {message}", flush=True)


def broadcast(message, exclude_socket=None):
    encoded_message = message.encode("utf-8")
    disconnected_clients = []

    with clients_lock:
        for client_socket in list(clients):
            if client_socket == exclude_socket:
                continue
            try:
                client_socket.sendall(encoded_message)
            except OSError:
                disconnected_clients.append(client_socket)

        for client_socket in disconnected_clients:
            nickname = clients.pop(client_socket, "Unknown")
            close_socket(client_socket)
            log(f"{nickname} disconnected during broadcast.")


def close_socket(client_socket):
    try:
        client_socket.shutdown(socket.SHUT_RDWR)
    except OSError:
        pass
    try:
        client_socket.close()
    except OSError:
        pass


def remove_client(client_socket):
    with clients_lock:
        nickname = clients.pop(client_socket, None)

    if nickname:
        log(f"{nickname} disconnected.")
        broadcast(f"[{timestamp()}] SERVER: {nickname} left the chat.\n")

    close_socket(client_socket)


def handle_client(client_socket, address):
    nickname = None

    try:
        client_socket.sendall("NICKNAME\n".encode("utf-8"))
        nickname = client_socket.recv(BUFFER_SIZE).decode("utf-8").strip()

        if not nickname:
            nickname = f"{address[0]}:{address[1]}"

        with clients_lock:
            clients[client_socket] = nickname

        log(f"{nickname} connected from {address[0]}:{address[1]}.")
        client_socket.sendall(f"[{timestamp()}] SERVER: Welcome, {nickname}!\n".encode("utf-8"))
        broadcast(f"[{timestamp()}] SERVER: {nickname} joined the chat.\n", exclude_socket=client_socket)

        while True:
            data = client_socket.recv(BUFFER_SIZE)
            if not data:
                break

            message = data.decode("utf-8").strip()
            if not message:
                continue

            formatted_message = f"[{timestamp()}] {nickname}: {message}\n"
            log(f"{nickname}: {message}")
            broadcast(formatted_message)

    except ConnectionResetError:
        if nickname:
            log(f"{nickname} connection reset.")
        else:
            log(f"Connection reset by {address[0]}:{address[1]}.")
    except OSError as error:
        log(f"Socket error for {address[0]}:{address[1]}: {error}")
    finally:
        remove_client(client_socket)


def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen()

    log(f"StudyDesk server started on {HOST}:{PORT}.")

    try:
        while True:
            client_socket, address = server_socket.accept()
            thread = threading.Thread(target=handle_client, args=(client_socket, address), daemon=True)
            thread.start()
    except KeyboardInterrupt:
        log("Server shutting down.")
    finally:
        with clients_lock:
            connected_sockets = list(clients)
            clients.clear()

        for client_socket in connected_sockets:
            close_socket(client_socket)

        close_socket(server_socket)


if __name__ == "__main__":
    start_server()
