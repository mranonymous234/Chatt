from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_socketio import SocketIO, emit, join_room, leave_room
from werkzeug.security import generate_password_hash, check_password_hash
import os
import psycopg2
from datetime import datetime
app = Flask(__name__)
app.config['SECRET_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFybmJlZndjYmxhZ2NoaWhqa3BzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDgwOTIzMzEsImV4cCI6MjA2MzY2ODMzMX0.yW22yK420HFY-UVLTLjMzVHmVV2IhF7rpUnLhB4GNFk'  # Change this to a secure secret key
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg2://postgres:eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFybmJlZndjYmxhZ2NoaWhqa3BzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDgwOTIzMzEsImV4cCI6MjA2MzY2ODMzMX0.yW22yK420HFY-UVLTLjMzVHmVV2IhF7rpUnLhB4GNFk@db.arnbefwcblagchihjkps.supabase.co:5432/postgres'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_POOL_SIZE'] = 100
app.config['SQLALCHEMY_POOL_TIMEOUT'] = 30

db = SQLAlchemy(app)
socketio = SocketIO(app, async_mode='threading', cors_allowed_origins="*")
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Database Models
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(1024), nullable=False)  # Increased size to accommodate hash
    profile_pic = db.Column(db.String(200), default='default.jpg')
    status = db.Column(db.String(80), default='Hey there! I am using WhatsApp')

class Message(db.Model):
    __tablename__ = 'message'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(500), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    read = db.Column(db.Boolean, default=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('chat'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('chat'))
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('register'))
            
        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return redirect(url_for('register'))
            
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please login.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/chat')
@login_required
def chat():
    users = User.query.filter(User.id != current_user.id).all()
    return render_template('chat.html', users=users)

@app.route('/get_messages/<user_id>')
@login_required
def get_messages(user_id):
    messages = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.receiver_id == user_id)) |
        ((Message.sender_id == user_id) & (Message.receiver_id == current_user.id))
    ).order_by(Message.timestamp).all()
    
    return jsonify([{
        'sender_id': msg.sender_id,
        'receiver_id': msg.receiver_id,
        'content': msg.content,
        'timestamp': msg.timestamp.isoformat()
    } for msg in messages])

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Socket events
@socketio.on('message')
def handle_message(data):
    message = Message(
        content=data['content'],
        sender_id=data['sender_id'],
        receiver_id=data['receiver_id']
    )
    db.session.add(message)
    db.session.commit()
    
    room = f"chat_{min(data['sender_id'], data['receiver_id'])}_{max(data['sender_id'], data['receiver_id'])}"
    emit('message', {
        'content': message.content,
        'sender_id': message.sender_id,
        'receiver_id': message.receiver_id,
        'timestamp': message.timestamp.isoformat()
    }, room=room)

@socketio.on('join')
def on_join(data):
    sender_id = data['sender_id']
    receiver_id = data['receiver_id']
    room = f"chat_{min(sender_id, receiver_id)}_{max(sender_id, receiver_id)}"
    join_room(room)

def create_tables():
    with app.app_context():
        db.create_all()

if __name__ == '__main__':
    try:
        print("Starting server...")
        # Create tables before starting the server
        create_tables()
        # Run the server
        socketio.run(
            app,
            host='127.0.0.1',
            port=5002,
            debug=True,
            use_reloader=False,
            allow_unsafe_werkzeug=True
        )
    except Exception as e:
        print(f"Error starting the server: {str(e)}")
        print("Please make sure:")
        print("1. PostgreSQL server is running")
        print("2. Database credentials are correct")
        raise e
