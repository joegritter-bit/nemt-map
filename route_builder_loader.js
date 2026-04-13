function convertTo24Hr(timeStr) {
  if (!timeStr || timeStr === '--') return '';
  var match = timeStr.match(/(\d+):(\d+)\s*(AM|PM)/i);
  if (!match) return timeStr;
  var h = parseInt(match[1]);
  var m = match[2];
  var isPM = match[3].toUpperCase() === 'PM';
  if (isPM && h !== 12) h += 12;
  if (!isPM && h === 12) h = 0;
  return h.toString().padStart(2, '0') + ':' + m;
}

function loadAndAddTrip() {
  if (typeof chrome === 'undefined' || !chrome.storage) return;

  chrome.storage.local.get(['pendingTrip', 'pendingTripTime'], function(result) {
    if (chrome.runtime.lastError) return;
    if (!result.pendingTrip) return;

    var age = Date.now() - (result.pendingTripTime || 0);
    if (age > 30000) {
      chrome.storage.local.remove(['pendingTrip', 'pendingTripTime']);
      return;
    }

    var trip = result.pendingTrip;
    chrome.storage.local.remove(['pendingTrip', 'pendingTripTime']);

    var pickupEl  = document.getElementById('pickup');
    var dropoffEl = document.getElementById('dropoff');
    var milesEl   = document.getElementById('miles');
    var timeEl    = document.getElementById('pickup_time');

    if (pickupEl)  pickupEl.value  = trip.pickup;
    if (dropoffEl) dropoffEl.value = trip.dropoff || '';
    if (milesEl && trip.miles) milesEl.value = trip.miles;
    if (timeEl  && trip.time)  timeEl.value  = convertTo24Hr(trip.time);

    var attempts = 0;
    var tryAddTrip = setInterval(function() {
      attempts++;
      if (typeof addTrip === 'function') {
        clearInterval(tryAddTrip);
        addTrip();
      } else if (attempts > 20) {
        clearInterval(tryAddTrip);
      }
    }, 100);
  });
}

document.addEventListener('DOMContentLoaded', loadAndAddTrip);

chrome.runtime.onMessage.addListener(function(msg) {
  if (msg.action === 'loadPendingTrip') {
    loadAndAddTrip();
  }
});
