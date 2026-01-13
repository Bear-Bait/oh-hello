from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import pytz
from datetime import datetime

# Create a minimal app config to connect to the database
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Define only the needed models
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(500), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    username = db.Column(db.String(80), nullable=False)
    is_private = db.Column(db.Boolean, default=False)
    recipient = db.Column(db.String(80), nullable=True)
    color_name = db.Column(db.String(30))
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    color_name = db.Column(db.String(30), default='spring_leaf')
    icon_name = db.Column(db.String(30), default='bear')
    active_session = db.Column(db.String(100), nullable=True)
    last_seen = db.Column(db.DateTime, nullable=True)

with app.app_context():
    # 1. Update timestamps in existing messages to have correct timezone info
    eastern = pytz.timezone('America/New_York')
    utc = pytz.UTC
    
    # Get all messages
    messages = Message.query.all()
    print(f"Found {len(messages)} messages to update")
    
    for message in messages:
        # Convert UTC time to Eastern time
        if message.timestamp:
            aware_time = utc.localize(message.timestamp) if message.timestamp.tzinfo is None else message.timestamp
            eastern_time = aware_time.astimezone(eastern)
            message.timestamp = eastern_time
    
    db.session.commit()
    print("All message timestamps converted to Eastern time")
    
    print("Time fix completed successfully!")
