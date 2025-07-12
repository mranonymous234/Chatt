// firebase-messaging-sw.js
importScripts('https://www.gstatic.com/firebasejs/9.0.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/9.0.0/firebase-messaging-compat.js');

const firebaseConfig = {
    apiKey: "AIzaSyAKzhBMcMwGjml2H1bwtYwtFoW3DL7OBIg",
    authDomain: "chart-9e5cb.firebaseapp.com",
    projectId: "chart-9e5cb",
    storageBucket: "chart-9e5cb.firebasestorage.app",
    messagingSenderId: "232200875234",
    appId: "1:232200875234:web:565ebaee263e2831e782bb",
    measurementId: "G-VCLEVPDYZL"

const messaging = firebase.messaging();

messaging.onBackgroundMessage(function(payload) {
  const notificationTitle = payload.notification.title;
  const notificationOptions = {
    body: payload.notification.body,
    icon: '/static/images/favicon.png',
  };

  self.registration.showNotification(notificationTitle, notificationOptions);
});
