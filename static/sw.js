self.addEventListener('push', function(event) {
  let data = {};
  try { data = event.data ? event.data.json() : {}; } catch (e) {}
  const title = data.title || 'Fire Alert';
  const body = data.body || 'Fire detected! Please check immediately.';
  const timestamp = data.timestamp || '';
  event.waitUntil(
    self.registration.showNotification(title, {
      body: body + (timestamp ? `\n${timestamp}` : ''),
      icon: '/static/homepage.png',
      badge: '/static/homepage.png',
      vibrate: [200, 100, 200],
      data: { url: '/' }
    })
  );
});

self.addEventListener('notificationclick', function(event) {
  event.notification.close();
  event.waitUntil(
    clients.matchAll({ type: 'window' }).then(function(clientList) {
      for (const client of clientList) {
        if ('focus' in client) return client.focus();
      }
      if (clients.openWindow) return clients.openWindow('/');
    })
  );
});



