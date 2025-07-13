// firebase-messaging-sw.js
importScripts("https://www.gstatic.com/firebasejs/10.12.1/firebase-app-compat.js");
importScripts("https://www.gstatic.com/firebasejs/10.12.1/firebase-messaging-compat.js");

const firebaseConfig = {
  apiKey: "AIzaSyAKzhBMcMwGjml2H1bwtYwtFoW3DL7OBIg",
  authDomain: "chart-9e5cb.firebaseapp.com",
  projectId: "chart-9e5cb",
  storageBucket: "chart-9e5cb.firebasestorage.app",
  messagingSenderId: "232200875234",
  appId: "1:232200875234:web:565ebaee263e2831e782bb",
  measurementId: "G-VCLEVPDYZL"
};

const messaging = firebase.messaging();

messaging.onBackgroundMessage(function(payload) {
  const { title, body } = payload.notification;
  self.registration.showNotification(title, {
    body,
    icon: '/static/favicon.png' // Optional
  });
});
