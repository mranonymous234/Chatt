from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_socketio import SocketIO, emit, join_room, leave_room
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# ----------------- App & DB Setup -----------------
app = Flask(__name__)
app.config['SECRET_KEY'] = 'zFy4haF8rV2nNRGO'  # Hardcoded secret key
app.config['SQLALCHEMY_DATABASE_URI'] = (
    'postgresql+psycopg://postgres:'
    'zFy4haF8rV2nNRGO@db.arnbefwcblagchihjkps.supabase.co:5432/postgres?sslmode=require'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*")
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ----------------- Models -----------------
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(1024), nullable=False)
    profile_pic = db.Column(db.String(200), default='default.jpg')
    status = db.Column(db.String(80), default='Hey there! I am using WhatsApp')

class Message(db.Model):
    __tablename__ = 'message'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(1000), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    read = db.Column(db.Boolean, default=False)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# ----------------- Routes -----------------
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
        user = User(username=username, email=email, password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please login.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/chat')
@login_required
def chat():
    users = User.query.filter(User.id != current_user.id).all()
    return render_template('chat.html', users=users, current_user=current_user)

@app.route('/get_messages/<int:user_id>')
@login_required
def get_messages(user_id):
    messages = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.receiver_id == user_id)) |
        ((Message.sender_id == user_id) & (Message.receiver_id == current_user.id))
    ).order_by(Message.timestamp).all()
    return jsonify([{
        'id': m.id,
        'content': m.content,
        'sender_id': m.sender_id,
        'receiver_id': m.receiver_id,
        'timestamp': m.timestamp.isoformat()
    } for m in messages])

@app.route('/get_user_id/<username>')
@login_required
def get_user_id(username):
    u = User.query.filter_by(username=username).first()
    if not u:
        return jsonify({'error': 'User not found'}), 404
    return jsonify({'id': u.id})

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# ----------------- Socket.IO -----------------
@socketio.on('join_user_room')
def join_user_room(data):
    user_id = str(data.get('user_id'))
    join_room(user_id)

@socketio.on('join_chat_room')
def join_chat_room(data):
    a = int(data['user_a'])
    b = int(data['user_b'])
    room = f"chat_{min(a,b)}_{max(a,b)}"
    join_room(room)

@socketio.on('message')
def handle_message(data):
    content = data.get('content')
    sender_id = int(data.get('sender_id'))
    receiver_id = int(data.get('receiver_id'))
    if not content:
        return
    msg = Message(content=content, sender_id=sender_id, receiver_id=receiver_id)
    db.session.add(msg)
    db.session.commit()
    room = f"chat_{min(sender_id, receiver_id)}_{max(sender_id, receiver_id)}"
    emit('message', {
        'id': msg.id,
        'content': msg.content,
        'sender_id': msg.sender_id,
        'receiver_id': msg.receiver_id,
        'timestamp': msg.timestamp.isoformat()
    }, room=room)

# ----------------- Call Signalling -----------------
@socketio.on('call_user')
def call_user(data):
    caller_id = int(data.get('caller_id'))
    callee_id = int(data.get('callee_id'))
    callee = db.session.get(User, callee_id)
    if callee:
        emit('incoming_call', {
            'caller_id': caller_id,
            'caller_name': db.session.get(User, caller_id).username
        }, room=str(callee_id))
    else:
        emit('call_error', {'error': 'User not found'}, room=str(caller_id))

@socketio.on('answer_call')
def answer_call(data):
    callee_id = int(data.get('callee_id'))
    caller_id = int(data.get('caller_id'))
    accepted = bool(data.get('accepted'))
    if accepted:
        emit('call_accepted', {
            'callee_id': callee_id,
            'callee_name': db.session.get(User, callee_id).username
        }, room=str(caller_id))
    else:
        emit('call_rejected', {'reason': 'User declined'}, room=str(caller_id))

@socketio.on('offer')
def forward_offer(data):
    target_user_id = str(data.get('target_user_id'))
    emit('offer', {'offer': data.get('offer'), 'from': data.get('from')}, room=target_user_id)

@socketio.on('answer')
def forward_answer(data):
    target_user_id = str(data.get('target_user_id'))
    emit('answer', {'answer': data.get('answer'), 'from': data.get('from')}, room=target_user_id)

@socketio.on('ice_candidate')
def forward_ice(data):
    target_user_id = str(data.get('target_user_id'))
    emit('ice_candidate', {'candidate': data.get('candidate')}, room=target_user_id)

@socketio.on('end_call')
def forward_end_call(data):
    target_user_id = str(data.get('target_user_id'))
    emit('call_ended', {}, room=target_user_id)

# ----------------- DB Init -----------------
def create_tables():
    with app.app_context():
        db.create_all()

# ----------------- Run -----------------
if __name__ == '__main__':
    create_tables()
    socketio.run(app, host='0.0.0.0', port=8080, debug=True)
