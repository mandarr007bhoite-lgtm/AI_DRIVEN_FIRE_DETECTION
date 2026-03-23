(function() {
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
    console.warn('Push not supported');
    return;
  }

  async function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);
    for (let i = 0; i < rawData.length; ++i) {
      outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
  }

  async function registerAndSubscribe() {
    try {
      const reg = await navigator.serviceWorker.register('/static/sw.js');
      const perm = await Notification.requestPermission();
      if (perm !== 'granted') return;
      const resp = await fetch('/vapid_public_key');
      const data = await resp.json();
      const key = data.publicKey;
      const sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: await urlBase64ToUint8Array(key)
      });
      await fetch('/subscribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(sub)
      });
      console.log('Push subscribed');
    } catch (e) {
      console.error('Push subscribe error', e);
    }
  }

  window.enableFirePush = registerAndSubscribe;
})();



