import queue
import socket
import threading
from dataclasses import dataclass
from datetime import datetime

import database


HOST = "0.0.0.0"
PORT = 8080
BUFFER_SIZE = 1024
MESSAGE_QUEUE_SIZE = 100


@dataclass
class ChatMessage:
    sender_socket: socket.socket | None
    sender_name: str
    text: str
    is_system_message: bool = False


# Shared producer-consumer buffer. Client handler threads put messages here;
# the dedicated consumer thread takes messages from it and broadcasts them.
message_queue = queue.Queue(maxsize=MESSAGE_QUEUE_SIZE)

# Shared client registry. Every access is protected by clients_lock so client
# handler threads and the consumer thread cannot race while clients join/leave.
clients = {}
clients_lock = threading.Lock()


def timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(message):
    print(f"[{timestamp()}] {message}", flush=True)


def close_socket(client_socket):
    try:
        client_socket.shutdown(socket.SHUT_RDWR)
    except OSError:
        pass
    try:
        client_socket.close()
    except OSError:
        pass


def authenticate_client(client_socket, address):
    """Ask the client for credentials and validate them before joining chat."""
    try:
        client_socket.sendall("AUTH\n".encode("utf-8"))
        username = client_socket.recv(BUFFER_SIZE).decode("utf-8").strip()
    except OSError:
        log(f"Authentication failed: could not read credentials from {address[0]}:{address[1]}.")
        return None

    if not username:
        log(f"Rejected empty username from {address[0]}:{address[1]}.")
        try:
            client_socket.sendall("AUTH_FAIL\n".encode("utf-8"))
        except OSError:
            pass
        return None

    # Authentication logic: the client sends its Nickname value as the username.
    # The server checks SQL Server and allows the connection only if that name
    # already exists in Studydesk.dbo.Users.
    lookup_success, lookup_result = database.user_exists(username)
    if not lookup_success:
        log(f"Authentication lookup failed for '{username}': {lookup_result}")
        try:
            client_socket.sendall("AUTH_FAIL\n".encode("utf-8"))
        except OSError:
            pass
        return None

    if lookup_result:
        try:
            client_socket.sendall("AUTH_OK\n".encode("utf-8"))
        except OSError:
            return None
        return username

    try:
        client_socket.sendall("AUTH_FAIL\n".encode("utf-8"))
    except OSError:
        pass
    log(f"Rejected unauthorized client from {address[0]}:{address[1]} as '{username}'.")
    return None


def add_client(client_socket, username):
    with clients_lock:
        clients[client_socket] = username


def remove_client(client_socket, announce=True):
    with clients_lock:
        username = clients.pop(client_socket, None)

    close_socket(client_socket)

    if username and announce:
        log(f"{username} disconnected.")
        enqueue_message(
            ChatMessage(
                sender_socket=None,
                sender_name="SERVER",
                text=f"{username} left the chat.",
                is_system_message=True,
            )
        )


def enqueue_message(chat_message):
    # Queue.put is already thread-safe. A bounded queue applies backpressure
    # when many producers send faster than the consumer can broadcast.
    message_queue.put(chat_message)


def broadcast(chat_message):
    if chat_message.is_system_message:
        formatted_message = f"[{timestamp()}] SERVER: {chat_message.text}\n"
    else:
        formatted_message = f"[{timestamp()}] {chat_message.sender_name}: {chat_message.text}\n"

    encoded_message = formatted_message.encode("utf-8")
    disconnected_clients = []

    # Take a snapshot under the lock, then do network I/O after releasing it.
    # This keeps slow or broken clients from blocking other synchronized work.
    with clients_lock:
        client_sockets = list(clients)

    for client_socket in client_sockets:
        # Normal chat messages go to every connected GUI, including the sender,
        # so the person who typed the message sees the server-broadcast copy too.
        # System join messages still skip the joining user's socket because that
        # user already receives a direct welcome message.
        if chat_message.is_system_message and client_socket == chat_message.sender_socket:
            continue
        try:
            client_socket.sendall(encoded_message)
        except OSError:
            disconnected_clients.append(client_socket)

    for client_socket in disconnected_clients:
        remove_client(client_socket, announce=False)

    log(formatted_message.strip())


def process_messages():
    """Consumer thread: drains queued producer messages and broadcasts them."""
    while True:
        chat_message = message_queue.get()
        try:
            broadcast(chat_message)
        finally:
            message_queue.task_done()


def handle_client(client_socket, address):
    """Producer thread: authenticate one client and enqueue received messages."""
    username = authenticate_client(client_socket, address)
    if not username:
        close_socket(client_socket)
        return

    add_client(client_socket, username)
    log(f"{username} connected from {address[0]}:{address[1]}.")

    try:
        client_socket.sendall(f"[{timestamp()}] SERVER: Welcome, {username}!\n".encode("utf-8"))
        enqueue_message(
            ChatMessage(
                sender_socket=client_socket,
                sender_name="SERVER",
                text=f"{username} joined the chat.",
                is_system_message=True,
            )
        )

        while True:
            data = client_socket.recv(BUFFER_SIZE)
            if not data:
                break

            message = data.decode("utf-8").strip()
            if not message:
                continue

            enqueue_message(
                ChatMessage(
                    sender_socket=client_socket,
                    sender_name=username,
                    text=message,
                )
            )
    except ConnectionResetError:
        log(f"{username} connection reset.")
    except OSError as error:
        log(f"Socket error for {username}: {error}")
    finally:
        remove_client(client_socket)


def accept_clients(server_socket):
    """Accept connections and start one producer thread per authenticated client."""
    while True:
        client_socket, address = server_socket.accept()
        thread = threading.Thread(
            target=handle_client,
            args=(client_socket, address),
            daemon=True,
        )
        thread.start()


def start_server():
    consumer_thread = threading.Thread(target=process_messages, daemon=True)
    consumer_thread.start()

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen()

    log(f"StudyDesk server started on {HOST}:{PORT}.")
    log(f"Authentication source: server={database.SERVER}, database={database.DATABASE}, table=dbo.Users")

    try:
        accept_clients(server_socket)
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
