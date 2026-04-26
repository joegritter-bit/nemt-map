const GMAPS_KEY = 'AIzaSyD93_zSxbsB77NGyoJD7R3S1pxY4dRB9n4';

function anchorToIllinois(address) {
  if (!address) return address;
  const trimmed = address.trim();
  if (/,\s*(IL|Illinois)\b/i.test(trimmed)) return trimmed;
  if (/\b(IL|Illinois)\b/i.test(trimmed)) return trimmed;
  if (/\b6[0-2]\d{3}\b/.test(trimmed)) return trimmed;
  return trimmed + ', IL';
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.action === 'openRouteBuilder') {
    chrome.storage.local.set({
      pendingTrip: msg.tripData,
      pendingTripTime: Date.now()
    }, () => {
      if (chrome.runtime.lastError) return;

      const rbUrl = chrome.runtime.getURL('route_builder.html');

      chrome.tabs.query({}, (tabs) => {
        const existing = tabs.find(t => t.url && t.url.startsWith(rbUrl));

        if (existing) {
          chrome.tabs.update(existing.id, { active: true });
          chrome.windows.update(existing.windowId, { focused: true });
          chrome.tabs.sendMessage(existing.id, { action: 'loadPendingTrip' });
        } else {
          chrome.tabs.create({ url: rbUrl });
        }
      });
    });
    return false;
  }

  if (msg.type === 'GET_DEADHEAD_MILES') {
    const origin = anchorToIllinois(msg.origin);
    const destination = anchorToIllinois(msg.destination);
    const url = `https://maps.googleapis.com/maps/api/distancematrix/json` +
      `?origins=${encodeURIComponent(origin)}` +
      `&destinations=${encodeURIComponent(destination)}` +
      `&units=imperial&key=${GMAPS_KEY}`;

    fetch(url)
      .then(r => r.json())
      .then(data => {
        if (data.status === 'OK' &&
            data.rows[0].elements[0].status === 'OK') {
          const meters = data.rows[0].elements[0].distance.value;
          const miles = Math.round(meters / 1609.34);
          sendResponse({ miles, error: null });
        } else {
          sendResponse({ miles: null, error: data.status });
        }
      })
      .catch(err => {
        sendResponse({ miles: null, error: err.message });
      });

    return true; // keeps channel open for async sendResponse
  }
});
