from flask import Flask, render_template_string, request, session, redirect, url_for, send_from_directory
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

FOREST_COLORS = {
    'greens': [
        {'name': 'spring_leaf', 'code': '#8FBC6B', 'display': 'Spring Leaf'},
        {'name': 'moss', 'code': '#3B7A57', 'display': 'Forest Moss'},
        {'name': 'sage', 'code': '#6B8E6B', 'display': 'Woodland Sage'},
    ],
    'browns': [
        {'name': 'bark', 'code': '#8B4513', 'display': 'Tree Bark'},
        {'name': 'acorn', 'code': '#6B4423', 'display': 'Acorn'},
    ],
    'purples': [
        {'name': 'wildflower', 'code': '#9B4F96', 'display': 'Wild Flower'},
        {'name': 'lavender', 'code': '#967BB6', 'display': 'Forest Lavender'},
    ]
}

FOREST_CREATURES = {
    'bear': {'file': 'bear.png', 'display': 'Forest Bear'},
    'deer': {'file': 'deer.png', 'display': 'Woodland Deer'},
    'fox': {'file': 'fox.png', 'display': 'Clever Fox'},
    'hedgehog': {'file': 'hedgehog.png', 'display': 'Friendly Hedgehog'},
    'owl': {'file': 'owl.png', 'display': 'Wise Owl'}
}

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    color_name = db.Column(db.String(30), default='spring_leaf')
    icon_name = db.Column(db.String(30), default='bear')

    @property
    def color_code(self):
        for category in FOREST_COLORS.values():
            for color in category:
                if color['name'] == self.color_name:
                    return color['code']
        return '#8FBC6B'  # default spring_leaf

    @property
    def icon_path(self):
        return f'/media/forest_creatures/{FOREST_CREATURES[self.icon_name]["file"]}'

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(500), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    username = db.Column(db.String(80), nullable=False)
    is_private = db.Column(db.Boolean, default=False)
    recipient = db.Column(db.String(80), nullable=True)
    color_name = db.Column(db.String(30))

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Oh Hello - Forest Friends Chat</title>
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
            0% { transform: translateY(0px) rotate(0deg); }
            50% { transform: translateY(-20px) rotate(5deg); }
            100% { transform: translateY(0px) rotate(0deg); }
        }
        .animate-float { animation: float 6s ease-in-out infinite; }
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
                        <img src="https://raw.githubusercontent.com/Bear-Bait/oh-hello/refs/heads/main/120314577.png"
                             alt="Boris the Bear"
                             class="rounded-full border-4 border-white shadow-lg hover:scale-110 transition-transform duration-300" />
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
                <div class="w-1/4 space-y-4">
                    <div class="bg-white/80 rounded-lg p-4 shadow-lg">
                        <h3 class="font-bold mb-2">Forest Creatures Online</h3>
                        <ul id="online-bears" class="space-y-1"></ul>
                    </div>

                    <div class="bg-white/80 rounded-lg p-4 shadow-lg">
                        <h3 class="font-bold mb-2">Choose Your Forest Color</h3>
                        <form action="/change_color" method="POST" class="space-y-4">
                            {% for category, colors in FOREST_COLORS.items() %}
                            <div class="space-y-2">
                                <h4 class="font-semibold capitalize">{{ category }}</h4>
                                {% for color in colors %}
                                <label class="flex items-center space-x-2 cursor-pointer">
                                    <input type="radio" name="color_name" value="{{ color.name }}"
                                        {% if current_user.color_name == color.name %}checked{% endif %}
                                        class="form-radio">
                                    <span class="w-4 h-4 rounded-full" style="background-color: {{ color.code }}"></span>
                                    <span>{{ color.display }}</span>
                                </label>
                                {% endfor %}
                            </div>
                            {% endfor %}
                            <button type="submit"
                                class="w-full bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700">
                                Update Color
                            </button>
                        </form>
                    </div>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE,
                                current_user=session.get('user'),
                                FOREST_COLORS=FOREST_COLORS,
                                FOREST_CREATURES=FOREST_CREATURES)

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

@app.route('/media/forest_creatures/<path:filename>')
def serve_forest_creature(filename):
    return send_from_directory('media/forest_creatures', filename)

@app.route('/change_color', methods=['POST'])
def change_color():
    if 'user' not in session:
        return redirect(url_for('index'))

    color_name = request.form.get('color_name')
    user = User.query.get(session['user']['id'])
    if user:
        user.color_name = color_name
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/change_icon', methods=['POST'])
def change_icon():
    if 'user' not in session:
        return redirect(url_for('index'))

    icon_name = request.form.get('icon_name')
    if icon_name in FOREST_CREATURES:
        user = User.query.get(session['user']['id'])
        if user:
            user.icon_name = icon_name
            db.session.commit()
    return redirect(url_for('index'))

HTML_TEMPLATE += '''
                    <div class="bg-white/80 rounded-lg p-4 shadow-lg">
                        <h3 class="font-bold mb-2">Choose Your Forest Creature</h3>
                        <form action="/change_icon" method="POST" class="space-y-4">
                            <div class="grid grid-cols-2 gap-2">
                                {% for icon_id, icon in FOREST_CREATURES.items() %}
                                <label class="flex flex-col items-center space-y-2 cursor-pointer">
                                    <input type="radio" name="icon_name" value="{{ icon_id }}"
                                        {% if current_user.icon_name == icon_id %}checked{% endif %}
                                        class="hidden peer">
                                    <div class="relative w-16 h-16 rounded-full overflow-hidden border-4 transition-all duration-300
                                            peer-checked:border-green-500 hover:border-green-300
                                            {% if current_user.icon_name == icon_id %}
                                            border-green-500
                                            {% else %}
                                            border-gray-200
                                            {% endif %}">
                                        <img src="/media/forest_creatures/{{ icon.file }}"
                                             alt="{{ icon.display }}"
                                             class="w-full h-full object-cover">
                                    </div>
                                    <span class="text-xs text-center">{{ icon.display }}</span>
                                </label>
                                {% endfor %}
                            </div>
                            <button type="submit"
                                class="w-full bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700">
                                Update Creature
                            </button>
                        </form>
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
            div.className = `message p-3 mb-2 rounded-lg ${data.private ? 'bg-opacity-75' : ''} transition-all duration-300`;
            div.style.backgroundColor = `${data.color}15`;
            div.style.borderLeft = `4px solid ${data.color}`;

            const timestamp = new Date(data.timestamp).toLocaleTimeString();
            const prefix = data.private ? '(Private) ' : '';

            div.innerHTML = `
                <div class="flex items-center gap-2">
                    <img src="${data.icon}" alt="" class="w-8 h-8 rounded-full border-2"
                         style="border-color: ${data.color}">
                    <div class="font-bold" style="color: ${data.color}">${data.sender}</div>
                </div>
                <div class="ml-10 text-gray-800">${prefix}${data.content}</div>
                <div class="ml-10 text-xs text-gray-500">${timestamp}</div>
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
                    <img src="${bear.icon}" alt="" class="w-6 h-6 rounded-full">
                    <span class="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                    <span>${bear.username}</span>
                </li>
            `).join('');

            recipientSelect.innerHTML = '<option value="">Public Message</option>';
            data.bears.forEach(bear => {
                if (bear.username !== currentUsername) {
                    const option = document.createElement('option');
                    option.value = bear.username;
                    option.textContent = `Private to ${bear.username}`;
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

@socketio.on('connect')
def handle_connect(auth):  # Add auth parameter
    if 'user' not in session:
        return False

    user = User.query.get(session.get('user', {}).get('id'))
    if not user:
        return False

    connected_bears[request.sid] = {
        'username': user.username,
        'icon': user.icon_path
    }

    emit('system', {
        'message': f'{user.username} joined the forest',
        'icon': user.icon_path
    }, broadcast=True)

    emit('bear_update', {
        'bears': [{'username': u['username'], 'icon': u['icon']}
                 for u in connected_bears.values()],
        'count': len(connected_bears)
    }, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    if request.sid in connected_bears:
        user = connected_bears.pop(request.sid)
        bear_count = len(connected_bears)

        emit('system', {
            'message': f'{user["username"]} left the forest',
        }, broadcast=True)

        emit('bear_update', {
            'bears': [{'username': u['username'], 'icon': u['icon']}
                     for u in connected_bears.values()],
            'count': bear_count
        }, broadcast=True)

@socketio.on('request_history')
def handle_history_request():
    messages = Message.query.order_by(Message.timestamp.desc()).limit(50).all()
    history = []
    for msg in messages:
        user = User.query.filter_by(username=msg.username).first()
        history.append({
            'sender': msg.username,
            'content': msg.content,
            'timestamp': msg.timestamp.isoformat(),
            'private': msg.is_private,
            'color': user.color_code if user else '#8FBC6B',
            'icon': user.icon_path if user else '/media/forest_creatures/bear.png'
        })
    emit('message_history', history)

@socketio.on('message')
def handle_message(data):
    if 'user' not in session:
        return

    user = User.query.get(session['user']['id'])
    content = data['content']
    recipient_username = data.get('recipient')

    message = Message(
        content=content,
        username=user.username,
        is_private=bool(recipient_username),
        recipient=recipient_username,
        color_name=user.color_name
    )
    db.session.add(message)
    db.session.commit()

    message_data = {
        'sender': user.username,
        'content': content,
        'timestamp': message.timestamp.isoformat(),
        'private': bool(recipient_username),
        'color': user.color_code,
        'icon': user.icon_path
    }

    if recipient_username:
        # Send to recipient and sender only
        for sid, connected_user in connected_bears.items():
            if connected_user['username'] in [recipient_username, user.username]:
                emit('message', message_data, room=sid)
    else:
        emit('message', message_data, broadcast=True)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
