import tkinter as tk
from tkinter import ttk, scrolledtext
import socketio
import json
import requests
from datetime import datetime
import webbrowser
from PIL import Image, ImageTk
import os
from threading import Thread

class ForestChatClient:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Forest Chat")
        self.root.geometry("1000x600")
        
        # Initialize Socket.IO client
        self.sio = socketio.Client()
        self.setup_socket_events()
        
        # Store session info
        self.session = None
        self.username = None
        
        # Create UI
        self.create_ui()
        
    def create_ui(self):
        # Main container
        self.main_container = ttk.Frame(self.root)
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Login frame (shown first)
        self.login_frame = ttk.Frame(self.main_container)
        self.create_login_ui()
        
        # Chat frame (hidden initially)
        self.chat_frame = ttk.Frame(self.main_container)
        self.create_chat_ui()
        
        # Show login first
        self.show_login()
        
    def create_login_ui(self):
        # Login widgets
        ttk.Label(self.login_frame, text="Forest Chat", font=('Helvetica', 24)).pack(pady=20)
        
        login_box = ttk.Frame(self.login_frame)
        login_box.pack(pady=20)
        
        ttk.Label(login_box, text="Username:").pack()
        self.username_entry = ttk.Entry(login_box)
        self.username_entry.pack(pady=5)
        
        ttk.Label(login_box, text="Password:").pack()
        self.password_entry = ttk.Entry(login_box, show="*")
        self.password_entry.pack(pady=5)
        
        ttk.Button(login_box, text="Login", command=self.handle_login).pack(pady=10)
        ttk.Button(login_box, text="Register", command=self.open_register).pack()
        
    def create_chat_ui(self):
        # Split into left sidebar and main chat area
        paned = ttk.PanedWindow(self.chat_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)
        
        # Left sidebar
        left_frame = ttk.Frame(paned, width=200)
        paned.add(left_frame)
        
        # Online users list
        ttk.Label(left_frame, text="Forest Creatures Online").pack(pady=5)
        self.users_list = ttk.Treeview(left_frame, height=10, columns=("status",), show="tree")
        self.users_list.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Main chat area
        chat_frame = ttk.Frame(paned)
        paned.add(chat_frame)
        
        # Messages area
        self.messages_area = scrolledtext.ScrolledText(chat_frame, wrap=tk.WORD, height=20)
        self.messages_area.pack(fill=tk.BOTH, expand=True, pady=5)
        self.messages_area.config(state=tk.DISABLED)
        
        # Message input area
        input_frame = ttk.Frame(chat_frame)
        input_frame.pack(fill=tk.X, pady=5)
        
        self.recipient_var = tk.StringVar(value="")
        self.recipient_combo = ttk.Combobox(input_frame, textvariable=self.recipient_var)
        self.recipient_combo['values'] = ['Everyone']
        self.recipient_combo.set('Everyone')
        self.recipient_combo.pack(side=tk.LEFT, padx=5)
        
        self.message_entry = ttk.Entry(input_frame)
        self.message_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.message_entry.bind("<Return>", self.send_message)
        
        ttk.Button(input_frame, text="Send", command=self.send_message).pack(side=tk.LEFT, padx=5)
        
        # Logout button
        ttk.Button(chat_frame, text="Leave Forest", command=self.handle_logout).pack(pady=5)
        
    def setup_socket_events(self):
        @self.sio.on('connect')
        def on_connect():
            print("Connected to server")
            self.sio.emit('request_history')
            
        @self.sio.on('message')
        def on_message(data):
            self.display_message(data)
            
        @self.sio.on('message_history')
        def on_history(messages):
            self.messages_area.config(state=tk.NORMAL)
            self.messages_area.delete(1.0, tk.END)
            for message in reversed(messages):
                self.display_message(message)
            self.messages_area.config(state=tk.DISABLED)
            
        @self.sio.on('bear_update')
        def on_bear_update(data):
            self.update_users_list(data['bears'])
            
        @self.sio.on('system')
        def on_system(data):
            self.display_system_message(data['message'])
            
    def handle_login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        
        try:
            response = requests.post(
                'http://localhost:5000/login',
                data={'username': username, 'password': password}
            )
            
            if response.url.endswith('/'):  # Successful login
                self.username = username
                self.connect_socket()
                self.show_chat()
            else:
                tk.messagebox.showerror("Error", "Invalid credentials")
                
        except Exception as e:
            tk.messagebox.showerror("Error", f"Connection error: {str(e)}")
            
    def connect_socket(self):
        try:
            self.sio.connect('http://localhost:5000')
        except Exception as e:
            tk.messagebox.showerror("Error", f"Socket connection error: {str(e)}")
            
    def send_message(self, event=None):
        message = self.message_entry.get().strip()
        recipient = self.recipient_combo.get()
        
        if message:
            self.sio.emit('message', {
                'content': message,
                'recipient': recipient if recipient != 'Everyone' else ''
            })
            self.message_entry.delete(0, tk.END)
            
    def display_message(self, data):
        self.messages_area.config(state=tk.NORMAL)
        timestamp = datetime.fromisoformat(data['timestamp']).strftime('%H:%M:%S')
        prefix = "(Private) " if data.get('private') else ""
        
        self.messages_area.insert(tk.END, 
            f"[{timestamp}] {data['sender']}: {prefix}{data['content']}\n")
        self.messages_area.see(tk.END)
        self.messages_area.config(state=tk.DISABLED)
        
    def display_system_message(self, message):
        self.messages_area.config(state=tk.NORMAL)
        self.messages_area.insert(tk.END, f"*** {message} ***\n", "system")
        self.messages_area.see(tk.END)
        self.messages_area.config(state=tk.DISABLED)
        
    def update_users_list(self, users):
        self.users_list.delete(*self.users_list.get_children())
        self.recipient_combo['values'] = ['Everyone']
        
        for user in users:
            if user['username'] != self.username:
                self.users_list.insert('', 'end', text=user['username'])
                self.recipient_combo['values'] = list(self.recipient_combo['values']) + [user['username']]
                
    def handle_logout(self):
        try:
            requests.post('http://localhost:5000/logout')
            self.sio.disconnect()
        except:
            pass
        finally:
            self.show_login()
            
    def show_login(self):
        self.chat_frame.pack_forget()
        self.login_frame.pack(fill=tk.BOTH, expand=True)
        
    def show_chat(self):
        self.login_frame.pack_forget()
        self.chat_frame.pack(fill=tk.BOTH, expand=True)
        
    def open_register(self):
        webbrowser.open('http://localhost:5000/register')
        
    def run(self):
        self.root.mainloop()

if __name__ == '__main__':
    app = ForestChatClient()
    app.run()
