from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import pytz
from datetime import datetime, timedelta

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

eastern = pytz.timezone('America/New_York')

def print_message_info(message):
    """Print detailed message info for debugging"""
    print(f"ID: {message.id}")
    print(f"Content: {message.content}")
    print(f"UTC Timestamp: {message.timestamp}")
    print(f"Is TZ aware: {message.timestamp.tzinfo is not None}")
    
    # Convert to Eastern time for display
    if message.timestamp.tzinfo is None:
        aware_time = pytz.UTC.localize(message.timestamp)
    else:
        aware_time = message.timestamp
    eastern_time = aware_time.astimezone(eastern)
    print(f"Eastern time: {eastern_time}")
    print("---")

with app.app_context():
    # Show current server time
    now = datetime.now()
    utc_now = datetime.utcnow()
    
    print(f"Server local time: {now}")
    print(f"Server UTC time: {utc_now}")
    print(f"Current Eastern time: {datetime.now(eastern)}")
    print("---")
    
    # Get some recent messages
    recent = Message.query.order_by(Message.id.desc()).limit(5).all()
    
    print("Recent messages BEFORE fix:")
    for msg in recent:
        print_message_info(msg)
    
    # Fix all messages - adjust all timestamps by -12 hours to correct them
    all_messages = Message.query.all()
    print(f"Found {len(all_messages)} messages to update")
    
    for message in all_messages:
        # Apply a 12-hour adjustment to fix the offset
        message.timestamp = message.timestamp - timedelta(hours=12)
    
    db.session.commit()
    print("All message timestamps adjusted")
    
    # Show the fixed messages
    recent = Message.query.order_by(Message.id.desc()).limit(5).all()
    print("Recent messages AFTER fix:")
    for msg in recent:
        print_message_info(msg)
    
    print("Time fix completed!")
