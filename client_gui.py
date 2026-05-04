import socket
import threading
import tkinter as tk
from tkinter import messagebox, ttk

import database


PORT = 8080
BUFFER_SIZE = 1024


class StudyDeskClient:
    def __init__(self, root):
        self.root = root
        self.root.title("StudyDesk")
        self.root.geometry("820x560")
        self.root.minsize(720, 480)

        self.client_socket = None
        self.connected = False
        self.receive_thread = None

        self.build_ui()
        self.initialize_database()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def build_ui(self):
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.chat_tab = ttk.Frame(notebook)
        self.database_tab = ttk.Frame(notebook)
        notebook.add(self.chat_tab, text="Chat")
        notebook.add(self.database_tab, text="Database")

        self.build_chat_tab()
        self.build_database_tab()

    def build_chat_tab(self):
        connection_frame = ttk.LabelFrame(self.chat_tab, text="Connection")
        connection_frame.pack(fill=tk.X, padx=8, pady=8)

        ttk.Label(connection_frame, text="Server IP").grid(row=0, column=0, padx=6, pady=8, sticky=tk.W)
        self.server_ip_var = tk.StringVar(value="127.0.0.1")
        ttk.Entry(connection_frame, textvariable=self.server_ip_var, width=20).grid(row=0, column=1, padx=6, pady=8)

        ttk.Label(connection_frame, text="Nickname").grid(row=0, column=2, padx=6, pady=8, sticky=tk.W)
        self.nickname_var = tk.StringVar(value="Student")
        ttk.Entry(connection_frame, textvariable=self.nickname_var, width=20).grid(row=0, column=3, padx=6, pady=8)

        self.connect_button = ttk.Button(connection_frame, text="Connect", command=self.connect_to_server)
        self.connect_button.grid(row=0, column=4, padx=6, pady=8)

        self.disconnect_button = ttk.Button(
            connection_frame,
            text="Disconnect",
            command=self.disconnect_from_server,
            state=tk.DISABLED,
        )
        self.disconnect_button.grid(row=0, column=5, padx=6, pady=8)

        connection_frame.columnconfigure(6, weight=1)

        chat_frame = ttk.Frame(self.chat_tab)
        chat_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        self.chat_display = tk.Text(chat_frame, wrap=tk.WORD, state=tk.DISABLED)
        self.chat_display.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(chat_frame, command=self.chat_display.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.chat_display.config(yscrollcommand=scrollbar.set)

        message_frame = ttk.Frame(self.chat_tab)
        message_frame.pack(fill=tk.X, padx=8, pady=(0, 8))

        self.message_var = tk.StringVar()
        self.message_entry = ttk.Entry(message_frame, textvariable=self.message_var)
        self.message_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        self.message_entry.bind("<Return>", lambda event: self.send_message())

        self.send_button = ttk.Button(message_frame, text="Send", command=self.send_message, state=tk.DISABLED)
        self.send_button.pack(side=tk.RIGHT)

    def build_database_tab(self):
        form_frame = ttk.LabelFrame(self.database_tab, text="User Details")
        form_frame.pack(fill=tk.X, padx=8, pady=8)

        ttk.Label(form_frame, text="Name").grid(row=0, column=0, padx=6, pady=8, sticky=tk.W)
        self.name_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.name_var, width=24).grid(row=0, column=1, padx=6, pady=8)

        ttk.Label(form_frame, text="Age").grid(row=0, column=2, padx=6, pady=8, sticky=tk.W)
        self.age_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.age_var, width=10).grid(row=0, column=3, padx=6, pady=8)

        ttk.Label(form_frame, text="Email").grid(row=0, column=4, padx=6, pady=8, sticky=tk.W)
        self.email_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.email_var, width=28).grid(row=0, column=5, padx=6, pady=8)

        form_frame.columnconfigure(6, weight=1)

        action_frame = ttk.Frame(self.database_tab)
        action_frame.pack(fill=tk.X, padx=8, pady=(0, 8))

        ttk.Button(action_frame, text="Add User", command=self.add_user).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(action_frame, text="Search", command=self.load_users).pack(side=tk.LEFT, padx=6)
        ttk.Button(action_frame, text="Update Email", command=self.update_email).pack(side=tk.LEFT, padx=6)
        ttk.Button(action_frame, text="Delete", command=self.delete_user).pack(side=tk.LEFT, padx=6)

        table_frame = ttk.Frame(self.database_tab)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        columns = ("UserID", "Name", "Age", "Email", "CreatedAt")
        self.user_table = ttk.Treeview(table_frame, columns=columns, show="headings")
        for column in columns:
            self.user_table.heading(column, text=column)
            self.user_table.column(column, width=120, anchor=tk.W)

        self.user_table.column("UserID", width=70)
        self.user_table.column("Age", width=60)
        self.user_table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.user_table.bind("<<TreeviewSelect>>", self.on_user_select)

        table_scrollbar = ttk.Scrollbar(table_frame, command=self.user_table.yview)
        table_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.user_table.config(yscrollcommand=table_scrollbar.set)

    def initialize_database(self):
        success, message = database.init_db()
        if not success:
            self.show_chat_message(f"Database warning: {message}\n")

    def connect_to_server(self):
        if self.connected:
            return

        server_ip = self.server_ip_var.get().strip()
        nickname = self.nickname_var.get().strip()

        if not server_ip or not nickname:
            messagebox.showwarning("Missing Details", "Enter both Server IP and Nickname.")
            return

        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((server_ip, PORT))

            prompt = self.client_socket.recv(BUFFER_SIZE).decode("utf-8").strip()
            if prompt in ("AUTH", "NICKNAME"):
                self.client_socket.sendall(nickname.encode("utf-8"))

            auth_data = self.client_socket.recv(BUFFER_SIZE).decode("utf-8")
            auth_lines = auth_data.splitlines(keepends=True)
            auth_response = auth_lines[0].strip() if auth_lines else ""
            extra_server_text = "".join(auth_lines[1:])

            if auth_response == "AUTH_FAIL":
                self.connected = False
                self.close_socket()
                messagebox.showerror("Authentication Failed", "This nickname is not authorized on the server.")
                return
            if auth_response != "AUTH_OK":
                self.connected = False
                self.close_socket()
                messagebox.showerror("Connection Failed", "Unexpected server authentication response.")
                return

            self.connected = True
            self.set_chat_controls(connected=True)
            self.show_chat_message("Connected to server.\n")
            if extra_server_text:
                self.show_chat_message(extra_server_text)

            self.receive_thread = threading.Thread(target=self.receive_messages, daemon=True)
            self.receive_thread.start()
        except OSError as error:
            self.connected = False
            self.close_socket()
            messagebox.showerror("Connection Failed", str(error))

    def receive_messages(self):
        while self.connected and self.client_socket:
            try:
                data = self.client_socket.recv(BUFFER_SIZE)
                if not data:
                    break
                self.root.after(0, self.show_chat_message, data.decode("utf-8"))
            except OSError:
                break

        self.root.after(0, self.handle_server_disconnect)

    def send_message(self):
        message = self.message_var.get().strip()
        if not message:
            return

        if not self.connected or not self.client_socket:
            messagebox.showwarning("Not Connected", "Connect to the server before sending messages.")
            return

        try:
            self.client_socket.sendall(message.encode("utf-8"))
            self.message_var.set("")
        except OSError as error:
            messagebox.showerror("Send Failed", str(error))
            self.disconnect_from_server()

    def disconnect_from_server(self):
        if self.connected:
            self.show_chat_message("Disconnected from server.\n")
        self.connected = False
        self.close_socket()
        self.set_chat_controls(connected=False)

    def handle_server_disconnect(self):
        if self.connected:
            self.show_chat_message("Server connection closed.\n")
        self.connected = False
        self.close_socket()
        self.set_chat_controls(connected=False)

    def close_socket(self):
        if self.client_socket:
            try:
                self.client_socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                self.client_socket.close()
            except OSError:
                pass
            self.client_socket = None

    def set_chat_controls(self, connected):
        self.connect_button.config(state=tk.DISABLED if connected else tk.NORMAL)
        self.disconnect_button.config(state=tk.NORMAL if connected else tk.DISABLED)
        self.send_button.config(state=tk.NORMAL if connected else tk.DISABLED)

    def show_chat_message(self, message):
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, message)
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)

    def add_user(self):
        name = self.name_var.get().strip()
        age = self.age_var.get().strip()
        email = self.email_var.get().strip()

        if not name or not age or not email:
            messagebox.showwarning("Missing Details", "Enter Name, Age, and Email.")
            return

        if not age.isdigit():
            messagebox.showwarning("Invalid Age", "Age must be a number.")
            return

        success, message = database.insert_user(name, age, email)
        self.show_database_result(success, message)
        if success:
            self.clear_user_form()
            self.load_users()

    def load_users(self):
        success, result = database.get_all_users()
        if not success:
            self.show_database_result(False, result)
            return

        self.user_table.delete(*self.user_table.get_children())
        search_name = self.name_var.get().strip().lower()

        for user in result:
            user_values = tuple(user)
            if search_name and search_name not in str(user.Name).lower():
                continue
            self.user_table.insert("", tk.END, values=user_values)

    def update_email(self):
        name = self.name_var.get().strip()
        email = self.email_var.get().strip()

        if not name or not email:
            messagebox.showwarning("Missing Details", "Enter Name and Email.")
            return

        success, message = database.update_email(name, email)
        self.show_database_result(success, message)
        if success:
            self.load_users()

    def delete_user(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showwarning("Missing Details", "Enter Name.")
            return

        if not messagebox.askyesno("Confirm Delete", f"Delete user '{name}'?"):
            return

        success, message = database.delete_user(name)
        self.show_database_result(success, message)
        if success:
            self.clear_user_form()
            self.load_users()

    def on_user_select(self, event):
        selected_items = self.user_table.selection()
        if not selected_items:
            return

        values = self.user_table.item(selected_items[0], "values")
        if len(values) >= 4:
            self.name_var.set(values[1])
            self.age_var.set(values[2])
            self.email_var.set(values[3])

    def show_database_result(self, success, message):
        if success:
            messagebox.showinfo("StudyDesk Database", message)
        else:
            messagebox.showerror("StudyDesk Database", message)

    def clear_user_form(self):
        self.name_var.set("")
        self.age_var.set("")
        self.email_var.set("")

    def on_close(self):
        self.disconnect_from_server()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = StudyDeskClient(root)
    root.mainloop()
