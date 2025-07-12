document.addEventListener('DOMContentLoaded', function() {
    const socket = io();
    let currentChatUser = null;
    const messageForm = document.getElementById('message-form');
    const messageInput = document.getElementById('message-text');
    const messagesDiv = document.getElementById('messages');
    const userList = document.querySelector('.user-list');
    const chatArea = document.querySelector('.chat-area');
    const sidebar = document.querySelector('.sidebar');

    // Join user's room for receiving messages
    socket.emit('join', {});

    // Handle user selection
    userList.addEventListener('click', function(e) {
        const userItem = e.target.closest('.user-item');
        if (userItem) {
            const userId = userItem.dataset.userId;
            const username = userItem.querySelector('h4').textContent;
            const userPic = userItem.querySelector('.user-pic').src;
            
            currentChatUser = userId;
            
            // Update chat header
            document.getElementById('chat-username').textContent = username;
            document.getElementById('chat-user-pic').src = userPic;
            
            // Clear previous messages
            messagesDiv.innerHTML = '';
            
            // Show chat area and hide sidebar on mobile
            if (window.innerWidth <= 768) {
                sidebar.classList.add('hidden');
                chatArea.classList.add('active');
            }

            // Load previous messages
            fetch(`/messages/${userId}`)
                .then(response => response.json())
                .then(messages => {
                    messages.forEach(addMessage);
                });
        }
    });

    // Handle message form submission
    messageForm.addEventListener('submit', function(e) {
        e.preventDefault();
        if (!currentChatUser) return;

        const message = messageInput.value.trim();
        if (message) {
            socket.emit('send_message', {
                message: message,
                receiver_id: currentChatUser
            });

            addMessage({
                content: message,
                sender_id: currentUserId,
                timestamp: new Date().toISOString()
            });

            messageInput.value = '';
        }
    });

    // Handle receiving messages
    socket.on('receive_message', function(data) {
        if (currentChatUser == data.sender_id) {
            addMessage(data);
        }
    });

    // Function to add a message to the chat
    function addMessage(message) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message');
        messageDiv.classList.add(message.sender_id == currentUserId ? 'sent' : 'received');
        
        const timestamp = new Date(message.timestamp).toLocaleTimeString([], { 
            hour: '2-digit', 
            minute: '2-digit' 
        });
        
        messageDiv.innerHTML = `
            <p>${message.content}</p>
            <span class="timestamp">${timestamp}</span>
        `;
        
        messagesDiv.appendChild(messageDiv);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }

    // Handle back button on mobile
    document.querySelector('.chat-header').addEventListener('click', function() {
        if (window.innerWidth <= 768) {
            sidebar.classList.remove('hidden');
            chatArea.classList.remove('active');
        }
    });
});

if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/firebase-messaging-sw.js')
    .then(reg => {
      console.log('Service Worker registered', reg);
    })
    .catch(err => {
      console.error('Service Worker registration failed', err);
    });
}
