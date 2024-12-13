import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import socketio
import requests
from datetime import datetime
import ttkthemes

# Server configuration
SERVER_URL = 'http://10.147.17.139:5000'

# Colors from the web app
COLORS = {
    'green_800': '#166534',
    'green_600': '#16a34a',
    'white': '#ffffff',
    'gray_500': '#6b7280',
    'gray_700': '#374151',
}

class ForestChatClient:
    def __init__(self):
        # Initialize main window
        self.root = tk.Tk()
        self.root.title("Forest Chat")
        self.root.geometry("1200x800")
        
        # Apply theme
        self.style = ttkthemes.ThemedStyle(self.root)
        self.style.set_theme("arc")
        
        # Initialize variables
        self.username = None
        self.session = requests.Session()
        self.sio = socketio.Client(
            reconnection=True,
            reconnection_attempts=5,
            reconnection_delay=1
        )
        
        # Create UI elements
        self.main_container = None
        self.login_frame = None
        self.chat_frame = None
        self.username_entry = None
        self.password_entry = None
        self.messages_area = None
        self.users_list = None
        self.message_entry = None
        self.recipient_combo = None
        self.online_count_label = None
        
        # Set up the UI
        self.create_ui()
        
        # Set up socket events
        self.setup_socket_events()
        
        # Handle window closing
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def create_ui(self):
        # Main container
        self.main_container = ttk.Frame(self.root)
        self.main_container.pack(fill=tk.BOTH, expand=True)
        
        # Create frames
        self.login_frame = ttk.Frame(self.main_container)
        self.chat_frame = ttk.Frame(self.main_container)
        
        self.create_login_ui()
        self.create_chat_ui()
        
        # Show login first
        self.show_login()
    
    def create_login_ui(self):
        # Header
        header = ttk.Frame(self.login_frame, style="Header.TFrame")
        header.pack(fill=tk.X)
        header.configure(style='Header.TFrame')
        
        # Title
        title_frame = ttk.Frame(header)
        title_frame.pack(pady=20)
        title_label = ttk.Label(
            title_frame,
            text="Forest Chat",
            font=('Helvetica', 24, 'bold')
        )
        title_label.pack()
        
        # Login box
        login_box = ttk.Frame(self.login_frame)
        login_box.pack(expand=True)
        
        # Username field
        ttk.Label(login_box, text="Username:").pack(pady=(0, 5))
        self.username_entry = ttk.Entry(login_box, width=30)
        self.username_entry.pack(pady=(0, 15))
        
        # Password field
        ttk.Label(login_box, text="Password:").pack(pady=(0, 5))
        self.password_entry = ttk.Entry(login_box, show="*", width=30)
        self.password_entry.pack(pady=(0, 15))
        
        # Login button
        login_btn = ttk.Button(
            login_box,
            text="Enter the Forest",
            command=self.handle_login,
            style='Accent.TButton'
        )
        login_btn.pack(pady=(0, 20))
        
        # Bind Enter key to login
        self.password_entry.bind('<Return>', lambda e: self.handle_login())
    
    def create_chat_ui(self):
        # Header
        header = ttk.Frame(self.chat_frame)
        header.pack(fill=tk.X, pady=10, padx=10)
        
        title_label = ttk.Label(
            header,
            text="Forest Chat",
            font=('Helvetica', 18, 'bold')
        )
        title_label.pack(side=tk.LEFT)
        
        self.online_count_label = ttk.Label(
            header,
            text="0 Creatures in the Forest",
            font=('Helvetica', 12)
        )
        self.online_count_label.pack(side=tk.LEFT, padx=20)
        
        # Main content area with paned window
        paned = ttk.PanedWindow(self.chat_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, pady=10, padx=10)
        
        # Left side (users list)
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=1)
        
        ttk.Label(
            left_frame,
            text="Forest Creatures Online",
            font=('Helvetica', 12, 'bold')
        ).pack(pady=(0, 10))
        
        self.users_list = ttk.Treeview(
            left_frame,
            columns=(),
            show='tree',
            height=20
        )
        self.users_list.pack(fill=tk.BOTH, expand=True)
        
        # Right side (chat area)
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=3)
        
        # Messages area
        self.messages_area = scrolledtext.ScrolledText(
            right_frame,
            wrap=tk.WORD,
            height=25
        )
        self.messages_area.pack(fill=tk.BOTH, expand=True)
        self.messages_area.config(state=tk.DISABLED)
        
        # Input area
        input_frame = ttk.Frame(right_frame)
        input_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.recipient_combo = ttk.Combobox(
            input_frame,
            values=['Everyone'],
            state='readonly',
            width=20
        )
        self.recipient_combo.set('Everyone')
        self.recipient_combo.pack(side=tk.LEFT, padx=(0, 10))
        
        self.message_entry = ttk.Entry(input_frame)
        self.message_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.message_entry.bind('<Return>', self.send_message)
        
        send_btn = ttk.Button(
            input_frame,
            text="Send 🌿",
            command=self.send_message
        )
        send_btn.pack(side=tk.LEFT)
    
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
            for message in messages:
                self.display_message(message)
            self.messages_area.config(state=tk.DISABLED)
        
        @self.sio.on('bear_update')
        def on_bear_update(data):
            self.update_users_list(data['bears'])
        
        @self.sio.on('system')
        def on_system(data):
            if data.get('type') == 'forced_logout':
                messagebox.showwarning("Logged Out", "You have been logged out from another location")
                self.show_login()
            else:
                self.display_system_message(data['message'])
    
    def handle_login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        
        try:
            response = self.session.post(
                f'{SERVER_URL}/login',
                data={'username': username, 'password': password}
            )
            
            if response.url.endswith('/'):  # Successful login
                self.username = username
                if self.connect_socket():
                    self.show_chat()
                    self.message_entry.focus()
            else:
                messagebox.showerror("Error", "Invalid credentials")
        except Exception as e:
            messagebox.showerror("Error", f"Connection error: {str(e)}")
    
    def connect_socket(self):
        try:
            cookies = '; '.join([f'{k}={v}' for k, v in self.session.cookies.items()])
            self.sio.connect(
                SERVER_URL,
                headers={'Cookie': cookies},
                transports=['websocket', 'polling']
            )
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Socket connection error: {str(e)}")
            return False
    
    def send_message(self, event=None):
        message = self.message_entry.get().strip()
        recipient = self.recipient_combo.get()
        
        if message:
            try:
                self.sio.emit('message', {
                    'content': message,
                    'recipient': recipient if recipient != 'Everyone' else ''
                })
                self.message_entry.delete(0, tk.END)
            except Exception as e:
                messagebox.showerror("Error", "Failed to send message")
    
    def display_message(self, data):
        self.messages_area.config(state=tk.NORMAL)
        timestamp = datetime.fromisoformat(data['timestamp']).strftime('%H:%M:%S')
        prefix = "(Private) " if data.get('private') else ""
        
        self.messages_area.insert(tk.END, f"[{timestamp}] ", "timestamp")
        self.messages_area.insert(tk.END, f"{data['sender']}: ", "sender")
        self.messages_area.insert(tk.END, f"{prefix}{data['content']}\n", "message")
        
        self.messages_area.tag_config("timestamp", foreground=COLORS['gray_500'])
        self.messages_area.tag_config("sender", foreground=COLORS['green_600'])
        self.messages_area.tag_config("message", foreground=COLORS['gray_700'])
        
        self.messages_area.see(tk.END)
        self.messages_area.config(state=tk.DISABLED)
    
    def display_system_message(self, message):
        self.messages_area.config(state=tk.NORMAL)
        self.messages_area.insert(tk.END, f"*** {message} ***\n", "system")
        self.messages_area.tag_config("system", foreground=COLORS['gray_500'])
        self.messages_area.see(tk.END)
        self.messages_area.config(state=tk.DISABLED)
    
    def update_users_list(self, users):
        self.users_list.delete(*self.users_list.get_children())
        self.recipient_combo['values'] = ['Everyone']
        
        # Update online count
        count = len(users)
        self.online_count_label.config(
            text=f"{count} {'Creature' if count == 1 else 'Creatures'} in the Forest"
        )
        
        for user in users:
            if user['username'] != self.username:
                self.users_list.insert('', 'end', text=user['username'])
                self.recipient_combo['values'] = list(self.recipient_combo['values']) + [user['username']]
    
    def show_login(self):
        self.chat_frame.pack_forget()
        self.login_frame.pack(fill=tk.BOTH, expand=True)
        self.username_entry.focus()
    
    def show_chat(self):
        self.login_frame.pack_forget()
        self.chat_frame.pack(fill=tk.BOTH, expand=True)
    
    def on_closing(self):
        try:
            if self.sio.connected:
                self.sio.disconnect()
        except:
            pass
        self.root.destroy()
    
    def run(self):
        self.root.mainloop()

if __name__ == '__main__':
    app = ForestChatClient()
    app.run()
