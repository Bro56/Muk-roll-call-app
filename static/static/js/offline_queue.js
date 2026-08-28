(function () {
  const QUEUE_KEY = 'rollcall_offline_queue';
  const SYNCING_KEY = 'rollcall_syncing';

  function getQueue() {
    try { return JSON.parse(localStorage.getItem(QUEUE_KEY)) || []; } catch (e) { return []; }
  }

  function setQueue(q) {
    localStorage.setItem(QUEUE_KEY, JSON.stringify(q));
  }

  function isOnline() {
    return navigator.onLine;
  }

  window.queueOfflineAttendance = function (formData) {
    const q = getQueue();
    q.push({
      timestamp: Date.now(),
      data: formData,
      retries: 0
    });
    setQueue(q);
    showOfflineToast('Attendance saved offline. Will sync automatically when you reconnect.');
  };

  window.processOfflineQueue = function () {
    if (!isOnline() || localStorage.getItem(SYNCING_KEY) === 'true') return;
    const q = getQueue();
    if (!q.length) return;
    localStorage.setItem(SYNCING_KEY, 'true');
    
    let processed = 0;
    const remaining = [];

    function processNext() {
      if (processed >= q.length) {
        setQueue(remaining);
        localStorage.removeItem(SYNCING_KEY);
        if (processed > 0) showOfflineToast(processed + ' offline attendance record(s) synced! ✅');
        return;
      }
      const item = q[processed];
      fetch(item.data.action, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: item.data.body
      }).then(function(r) {
        if (r.ok || r.status === 400) {
          processed++;
        } else {
          item.retries++;
          if (item.retries < 3) remaining.push(item);
          processed++;
        }
        processNext();
      }).catch(function() {
        item.retries++;
        if (item.retries < 3) remaining.push(item);
        processed++;
        processNext();
      });
    }
    processNext();
  };

  function showOfflineToast(msg) {
    const div = document.createElement('div');
    div.className = 'flash flash-info';
    div.style.position = 'fixed';
    div.style.top = '18px';
    div.style.right = '18px';
    div.style.zIndex = '200';
    div.textContent = msg;
    document.body.appendChild(div);
    setTimeout(function() {
      div.style.opacity = '0';
      div.style.transform = 'translateX(24px)';
      div.style.transition = 'all 0.35s ease';
      setTimeout(function() { div.remove(); }, 350);
    }, 4000);
  }

  window.addEventListener('online', window.processOfflineQueue);
  document.addEventListener('DOMContentLoaded', window.processOfflineQueue);
})();