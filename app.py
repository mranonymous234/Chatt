from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_socketio import SocketIO, emit, join_room, leave_room
from werkzeug.security import generate_password_hash, check_password_hash
import os
import psycopg
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, messaging

cred = credentials.Certificate("/static/firebase-messaging-sw.js")
firebase_admin.initialize_app(cred)

def send_fcm_message(token, title, body):
    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body
        ),
        token=token
    )
    response = messaging.send(message)
    print('Successfully sent message:', response)
    
app = Flask(__name__)
app.config['SECRET_KEY'] = 'zFy4haF8rV2nNRGO'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg://postgres:zFy4haF8rV2nNRGO@db.arnbefwcblagchihjkps.supabase.co:5432/postgres?sslmode=require'
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
    password_hash = db.Column(db.String(1024), nullable=False)
    profile_pic = db.Column(db.String(200), default='default.jpg')
    status = db.Column(db.String(80), default='Hey there! I am using WhatsApp')

    sent_messages = db.relationship('Message', backref='sender', foreign_keys='Message.sender_id', lazy=True)
    received_messages = db.relationship('Message', backref='receiver', foreign_keys='Message.receiver_id', lazy=True)

class Message(db.Model):
    __tablename__ = 'message'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(500), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    read = db.Column(db.Boolean, default=False)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))  # Updated for SQLAlchemy 2.0

# Routes
@app.route('/firebase-messaging-sw.js')
def service_worker():
    return app.send_static_file('firebase-messaging-sw.js')
    
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
    try:
        user_id = int(user_id)  # Fix: Convert user_id from string to int
    except ValueError:
        return jsonify({'error': 'Invalid user ID'}), 400

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

# Add these new socket event handlers to your existing app.py

@socketio.on('call')
def handle_call(data):
    """Handle incoming call request"""
    caller_id = data['caller_id']
    callee_id = data['callee_id']
    
    callee = User.query.get(callee_id)
    if callee:
        emit('incoming_call', {
            'caller_id': caller_id,
            'caller_name': User.query.get(caller_id).username,
            'caller_pic': User.query.get(caller_id).profile_pic
        }, room=str(callee_id))
    else:
        emit('call_rejected', {'reason': 'User not found'}, room=str(caller_id))

@socketio.on('answer_call')
def handle_answer_call(data):
    """Handle call answer (accept/reject)"""
    callee_id = data['callee_id']
    caller_id = data['caller_id']
    accepted = data['accepted']
    
    if accepted:
        emit('call_accepted', {
            'callee_id': callee_id,
            'callee_name': User.query.get(callee_id).username
        }, room=str(caller_id))
    else:
        emit('call_rejected', {'reason': 'User declined'}, room=str(caller_id))

@socketio.on('ice_candidate')
def handle_ice_candidate(data):
    """Handle ICE candidate exchange"""
    target_user_id = data['target_user_id']
    emit('ice_candidate', {
        'candidate': data['candidate']
    }, room=str(target_user_id))

@socketio.on('end_call')
def handle_end_call(data):
    """Handle call termination"""
    target_user_id = data['target_user_id']
    emit('call_ended', {}, room=str(target_user_id))

@socketio.on('join_call_room')
def handle_join_call_room(data):
    """Join a user to their personal call room"""
    user_id = data['user_id']
    join_room(str(user_id))

def create_tables():
    with app.app_context():
        db.create_all()

if __name__ == '__main__':
    try:
        print("Starting server...")
        create_tables()
        socketio.run(
            app,
            host='0.0.0.0',
            port=8080,
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
