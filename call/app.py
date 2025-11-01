from flask import Flask, render_template, request
from flask_socketio import SocketIO, join_room, leave_room, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Keep track of users: {username: sid}
users = {}

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('register')
def handle_register(data):
    username = data['username']
    users[username] = request.sid  # save socket id

@socketio.on('call-user')
def handle_call(data):
    target = data['target']  # target username
    if target in users:
        emit('incoming-call', {'from': data['from'], 'offer': data['offer']}, room=users[target])

@socketio.on('answer-call')
def handle_answer(data):
    target_sid = data['target_sid']  # sid of caller
    emit('call-answered', {'answer': data['answer']}, room=target_sid)

@socketio.on('ice-candidate')
def handle_ice(data):
    target_sid = data['target_sid']
    emit('ice-candidate', {'candidate': data['candidate']}, room=target_sid)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
