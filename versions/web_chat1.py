from flask import Flask, render_template_string, request, session, redirect, url_for
from flask_socketio import SocketIO, emit
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
socketio = SocketIO(app)
connected_bears = {}

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    color = db.Column(db.String(20), default='forest')

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(500), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    username = db.Column(db.String(80), nullable=False)
    is_private = db.Column(db.Boolean, default=False)
    recipient = db.Column(db.String(80), nullable=True)
    color = db.Column(db.String(20), default='forest')

HTML_TEMPLATE = r'''
<!DOCTYPE html>
<html>
<head>
    <title>Oh, Hello - Forest Friends Chat</title>
    <link rel="icon" type="image/png" href="https://raw.githubusercontent.com/Bear-Bait/oh-hello/refs/heads/main/favicon.png">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/tailwindcss/2.2.19/tailwind.min.css" rel="stylesheet">
    <style>
        .message-container { height: calc(100vh - 200px); }
        body {
            background: linear-gradient(rgba(255,255,255,0.9), rgba(255,255,255,0.9));
            background-size: cover;
            background-attachment: fixed;
        }
        @keyframes float {
            0% { transform: translateY(0px) rotate(0deg); }666666666666666666666      50% { transform: translateY(-20px) rotate(5deg); }
            100% { transform: translateY(0px) rotate(0deg); }
        }
        .animate-float { animation: float 666s ease-in-out infinite; }
    </style>
</head>
<body class="bg-gray-100">
    <div class="container mx-auto px-4 py-8">
        <div class="relative overflow-hidden bg-green-800 text-white p-4 rounded-lg mb-6">
            <div class="absolute inset-0 pointer-events-none">
                {% for i in range(5) %}
                <div class="absolute animate-float" style="left: {{ range(0, 100) | random }}%;">🍂</div>
                {% endfor %}
            </div>

            <div class="flex items-center justify-between relative z-10">
                <div class="flex items-center gap-4">
                    <div class="relative w-16 h-16">
                        <img src="https://raw.githubusercontent.com/Bear-Bait/oh-hello/refs/heads/main/120314577.png" alt="Boris the Bear" class="rounded-full border-4 border-white shadow-lg hover:scale-110 transition-transform duration-300" />
                        <div class="absolute -bottom-2 -right-2 bg-white text-green-800 rounded-full px-3 py-1 text-sm font-bold shadow-lg">Oh!</div>
                    </div>
                    <div>
                        <h1 class="text-3xl font-bold">Oh, Hello!</h1>
                        <div id="bear-counter" class="text-green-200"></div>
                    </div>
                </div>
            </div>
        </div>

        {% if current_user %}
            <div class="flex gap-4">
                <div class="w-1/4">
                    <div class="bg-white/80 rounded-lg p-4 shadow-lg">
                        <h3 class="font-bold mb-2">Forest Creatures Online</h3>
                        <ul id="online-bears" class="space-y-1"></ul>
                    </div>
                </div>
                <div class="w-3/4">
                    <div id="messages" class="message-container overflow-y-auto bg-white/80 p-4 rounded-lg shadow-lg mb-4"></div>
                    <form id="message-form" class="flex gap-2">
                        <select id="recipient" class="w-1/4 rounded border-gray-300 p-2">
                            <option value="">Public Message</option>
                        </select>
                        <input type="text" id="message-input"
                            class="flex-1 rounded border-gray-300 p-2"
                            placeholder="Whisper to the forest..." required>
                        <button type="submit"
                            class="bg-green-600 text-white px-6 py-2 rounded hover:bg-green-700 transition-colors">
                            Send 🌿
                        </button>
                    </form>
                </div>
            </div>
        {% else %}
            <div class="bg-white/80 rounded-lg shadow-lg p-6 max-w-md mx-auto">
                <h2 class="text-2xl font-bold mb-4">Login to the Forest</h2>
                <form action="/login" method="POST" class="space-y-4">
                    <div>
                        <label class="block text-sm font-medium text-gray-700">Username</label>
                        <input type="text" name="username" required
                            class="mt-1 block w-full rounded border-gray-300 shadow-sm">
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700">Password</label>
                        <input type="password" name="password" required
                            class="mt-1 block w-full rounded border-gray-300 shadow-sm">
                    </div>
                    <button type="submit"
                        class="w-full bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700">
                        Enter the Forest
                    </button>
                </form>
                <div class="mt-4 text-center">
                    <a href="/register" class="text-green-600 hover:text-green-700">Register</a>
                </div>
            </div>
        {% endif %}
    </div>

    {% if current_user %}
    <script>
        const socket = io();
        const messages = document.getElementById('messages');
        const messageForm = document.getElementById('message-form');
        const messageInput = document.getElementById('message-input');
        const recipientSelect = document.getElementById('recipient');
        const bearCounter = document.getElementById('bear-counter');
        const currentUsername = "{{ current_user.username }}";

        function displayMessage(data) {
            const div = document.createElement('div');
            div.className = `message p-3 mb-2 rounded-lg bg-${data.color}-100 border-l-4 border-${data.color}-600 ${data.private ? 'bg-yellow-50' : ''}`;

            const timestamp = new Date(data.timestamp).toLocaleTimeString();
            const prefix = data.private ? '(Private) ' : '';

            div.innerHTML = `
                <div class="font-bold text-${data.color}-800">${data.sender}</div>
                <div>${prefix}${data.content}</div>
                <div class="text-xs text-gray-500">${timestamp}</div>
            `;
            messages.appendChild(div);
            messages.scrollTop = messages.scrollHeight;
        }

        socket.on('connect', function() {
            socket.emit('request_history');
        });

        socket.on('message_history', function(messages) {
            messages.forEach(message => displayMessage(message));
        });

        messageForm.onsubmit = function(e) {
            e.preventDefault();
            if (messageInput.value) {
                socket.emit('message', {
                    content: messageInput.value,
                    recipient: recipientSelect.value
                });
                messageInput.value = '';
            }
        };

        socket.on('message', function(data) {
            displayMessage(data);
        });

        socket.on('bear_update', function(data) {
            const bearCount = data.count;
            bearCounter.textContent = `${bearCount} ${bearCount === 1 ? 'Creature' : 'Creatures'} in the Forest`;

            const bearsList = document.getElementById('online-bears');
            bearsList.innerHTML = data.bears.map(bear => `
                <li class="flex items-center gap-2 py-1">
                    <span class="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                    <span>${bear}</span>
                </li>
            `).join('');

            recipientSelect.innerHTML = '<option value="">Public Message</option>';
            data.bears.forEach(username => {
                if (username !== currentUsername) {
                    const option = document.createElement('option');
                    option.value = username;
                    option.textContent = `Private to ${username}`;
                    recipientSelect.appendChild(option);
                }
            });
        });

        socket.on('system', function(data) {
            const div = document.createElement('div');
            div.className = 'message system p-2 text-gray-500 italic';
            div.textContent = data.message;
            messages.appendChild(div);
            messages.scrollTop = messages.scrollHeight;
        });
    </script>
    {% endif %}
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, current_user=session.get('user'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if User.query.filter_by(username=username).first():
            return "Username already exists"

        user = User(username=username, password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('index'))

    return '''
        <form method="POST" class="space-y-4">
            <input type="text" name="username" placeholder="Username" required class="block w-full mb-4">
            <input type="password" name="password" placeholder="Password" required class="block w-full mb-4">
            <button type="submit" class="bg-green-600 text-white px-4 py-2 rounded">Register</button>
        </form>
    '''

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')

    user = User.query.filter_by(username=username).first()
    if user and check_password_hash(user.password_hash, password):
        session['user'] = {'id': user.id, 'username': user.username}
        return redirect(url_for('index'))
    return "Invalid credentials"

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))

@socketio.on('connect')
def handle_connect():
    if 'user' not in session:
        return False

    user = session['user']
    connected_bears[request.sid] = user
    bear_count = len(connected_bears)

    emit('system', {
        'message': f'{user["username"]} joined the forest',
        'bearCount': bear_count
    }, broadcast=True)

    emit('bear_update', {
        'bears': [u['username'] for u in connected_bears.values()],
        'count': bear_count
    }, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    if request.sid in connected_bears:
        user = connected_bears.pop(request.sid)
        bear_count = len(connected_bears)

        emit('system', {
            'message': f'{user["username"]} left the forest',
            'bearCount': bear_count
        }, broadcast=True)

        emit('bear_update', {
            'bears': [u['username'] for u in connected_bears.values()],
            'count': bear_count
        }, broadcast=True)

@socketio.on('request_history')
def handle_history_request():
    messages = Message.query.order_by(Message.timestamp.desc()).limit(50).all()
    history = [{
        'sender': msg.username,
        'content': msg.content,
        'timestamp': msg.timestamp.isoformat(),
        'private': msg.is_private,
        'color': msg.color
    } for msg in messages]
    emit('message_history', history)

@socketio.on('message')
def handle_message(data):
    if 'user' not in session:
        return

    sender = session['user']
    content = data['content']
    recipient_username = data.get('recipient')

    message = Message(
        content=content,
        username=sender['username'],
        is_private=bool(recipient_username),
        recipient=recipient_username,
        color='forest'  # You can modify this to use user's chosen color
    )
    db.session.add(message)
    db.session.commit()

    message_data = {
        'sender': sender['username'],
        'content': content,
        'timestamp': message.timestamp.isoformat(),
        'private': bool(recipient_username),
        'color': message.color
    }

    if recipient_username:
        # Send to recipient and sender only
        for sid, user in connected_bears.items():
            if user['username'] in [recipient_username, sender['username']]:
                emit('message', message_data, room=sid)
    else:
        emit('message', message_data, broadcast=True)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
