// Register current user
const username = prompt("Enter your username:");
socket.emit('register', {username});

// Call a user
async function callUser(targetUsername) {
    const offer = await pc.createOffer();
    await pc.setLocalDescription(offer);
    socket.emit('call-user', { from: username, target: targetUsername, offer });
}

// Handle incoming call
socket.on('incoming-call', async (data) => {
    const accept = confirm(`Incoming call from ${data.from}. Accept?`);
    if (!accept) return;
    await pc.setRemoteDescription(new RTCSessionDescription(data.offer));
    const answer = await pc.createAnswer();
    await pc.setLocalDescription(answer);
    // Send back answer to caller
    socket.emit('answer-call', { target_sid: data.from, answer });
});

// Handle call answer
socket.on('call-answered', async (data) => {
    await pc.setRemoteDescription(new RTCSessionDescription(data.answer));
});
