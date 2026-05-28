const GMAPS_KEY = 'AIzaSyD93_zSxbsB77NGyoJD7R3S1pxY4dRB9n4';

// In-memory geocode cache — survives for the lifetime of the service worker session.
// Key: "origin||destination", Value: miles (float)
const geocodeCache = new Map();

function logCacheStats() {
  chrome.storage.local.get(['geocache'], (stored) => {
    const size = Object.keys(stored.geocache || {}).length;
    console.log(`NEMT geocache: ${size} addresses cached, ${geocodeCache.size} in memory`);
  });
}

// Log stats on startup
logCacheStats();

function anchorToIllinois(address) {
  if (!address) return address;
  const trimmed = address.trim();
  if (/,\s*(IL|Illinois)\b/i.test(trimmed)) return trimmed;
  if (/\b(IL|Illinois)\b/i.test(trimmed)) return trimmed;
  if (/\b6[0-2]\d{3}\b/.test(trimmed)) return trimmed;
  return trimmed + ', IL';
}

// ── Week-sync helpers ──────────────────────────────────────────────────────────

// Return YYYY-MM-DD string for a Date object
function toYMD(d) {
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `${d.getFullYear()}-${mm}-${dd}`;
}

// Return MM/DD/YYYY string for a Date object (MTM API query param format)
function toMMDDYYYY(d) {
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `${mm}/${dd}/${d.getFullYear()}`;
}

// Return array of 7 Date objects for the Mon–Sun week containing `today`
function getWeekDates(today) {
  const dow = today.getDay(); // 0=Sun … 6=Sat
  const monday = new Date(today);
  monday.setDate(today.getDate() - ((dow === 0 ? 7 : dow) - 1));
  monday.setHours(0, 0, 0, 0);
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(monday);
    d.setDate(monday.getDate() + i);
    return d;
  });
}

// True if lastSyncedAt ISO string is older than 4 hours
const FOUR_HOURS_MS = 4 * 60 * 60 * 1000;
function isStale(lastSyncedAt) {
  if (!lastSyncedAt) return true;
  return Date.now() - new Date(lastSyncedAt).getTime() > FOUR_HOURS_MS;
}

// Address building — mirrors trips_scraper.js (runs in service worker context)
function joinAddr(a1, a2, city, state, zip) {
  const street = [a1, a2].filter(s => s && s.trim()).join(' ').trim();
  const region = [state, zip].filter(Boolean).join(' ').trim();
  const cityRegion = [city, region].filter(Boolean).join(', ');
  return [street, cityRegion].filter(Boolean).join(', ');
}
function buildPickupBg(r) {
  return joinAddr(
    r.pickAddress1 || r.pickupAddress1 || r.pick_address_1 || '',
    r.pickAddress2 || r.pickupAddress2 || r.pick_address_2 || '',
    r.pickCity     || r.pickupCity     || r.pick_city      || '',
    r.pickState    || r.pickupState    || r.pick_state     || '',
    r.pickZip      || r.pickupZip      || r.pick_zip       || ''
  );
}
function buildDropoffBg(r) {
  return joinAddr(r.dropAddress1, r.dropAddress2, r.dropCity, r.dropState, r.dropZip);
}

// Map raw API trips to the HIPAA-stripped schema used by the pipeline.
// tripDate must be YYYY-MM-DD.
function processTripsForDate(rawArray, tripDate) {
  if (!Array.isArray(rawArray)) return [];
  const now = new Date().toISOString();
  const out = [];
  for (const r of rawArray) {
    const driverRaw = String(r.driverName || '').trim();
    if (!driverRaw || driverRaw.toLowerCase() === 'nan') continue;

    const pickup  = buildPickupBg(r);
    const dropoff = buildDropoffBg(r);
    out.push({
      trip_number:        String(r.mfTripId              || ''),
      assignment_number:  String(r.manifestName          || ''),
      driver:             driverRaw,
      driver_id:          String(r.driverId              || ''),
      trip_date:          tripDate,
      appt_time:          String(r.appointmentTime       || ''),
      pickup_time:        String(r.pickupTime || r.pickTime || r.driverPickNotes || ''),
      pickup_address:     pickup,
      dropoff_address:    dropoff,
      level_of_service:   String(r.levelOfService        || ''),
      mode:               String(r.modeOfTransportation  || ''),
      is_will_call:       Boolean(r.isWillCall),
      trip_status:        'Valid',
      scraped_at:         now,
      // HIPAA fields intentionally omitted: memberFirstName, memberLastName,
      // memberPhoneNumber, memberSecondaryNumber, enrouteLocator
    });
  }
  return out;
}

// Merge processed trips for one date into chrome.storage.local
function mergeAndStoreBg(processed, tripDate) {
  return new Promise(resolve => {
    chrome.storage.local.get('scheduled_trips', result => {
      const existing = result.scheduled_trips;
      const byDate = Array.isArray(existing) ? {} : (existing || {});
      byDate[tripDate] = processed;
      chrome.storage.local.set({ scheduled_trips: byDate }, resolve);
    });
  });
}

// POST to route server (best-effort — server may not be running)
async function postToRouteServer(processed, tripDate) {
  try {
    await fetch('http://localhost:8765/scheduled_trips', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ date: tripDate, trips: processed }),
    });
  } catch (_) { /* server offline — silent */ }
}

// ── Week sync (all 7 days for the current week) ────────────────────────────────
let _weekSyncInProgress = false;

async function syncWeekTrips(token, organizationId) {
  const today     = new Date();
  const todayYMD  = toYMD(today);
  const weekDates = getWeekDates(today);

  // Load per-date sync metadata
  const meta = await new Promise(resolve =>
    chrome.storage.local.get('scheduled_trips_meta', r =>
      resolve(r.scheduled_trips_meta || {})
    )
  );

  const summary = { total: 0, dates: [], drivers: new Set() };

  for (let i = 0; i < weekDates.length; i++) {
    const date    = weekDates[i];
    const ymd     = toYMD(date);
    const mmdd    = toMMDDYYYY(date);

    // Skip non-today dates that were synced within the last 4 hours
    if (ymd !== todayYMD && !isStale(meta[ymd])) {
      console.log(`[NEMT Week Sync] ${ymd} — cached, skipping`);
      continue;
    }

    const url = `https://api-ua.mtmlink.net/provider/trip/v1.0/all` +
      `?startDateTime=${encodeURIComponent(mmdd)}` +
      `&endDateTime=${encodeURIComponent(mmdd)}` +
      `&driverName=&driverId=` +
      `&status=Valid&activeOnly=true&enabled=true` +
      `&organizationId=${organizationId}`;

    let fetchOk = false;
    try {
      const resp = await fetch(url, {
        headers: {
          'Authorization': token,
          'Content-Type': 'application/json',
        },
      });

      if (resp.status === 401 || resp.status === 403) {
        console.warn('[NEMT Week Sync] Token expired — aborting remaining dates');
        break;
      }

      if (!resp.ok) {
        console.warn(`[NEMT Week Sync] HTTP ${resp.status} for ${ymd} — skipping`);
      } else {
        const rawTrips = await resp.json();
        const processed = processTripsForDate(rawTrips, ymd);
        console.log(`[NEMT Week Sync] ${ymd}: ${processed.length} trips`);

        if (processed.length) {
          await mergeAndStoreBg(processed, ymd);
          await postToRouteServer(processed, ymd);

          summary.total += processed.length;
          summary.dates.push(ymd);
          processed.forEach(t => { if (t.driver) summary.drivers.add(t.driver); });
        }

        meta[ymd] = new Date().toISOString();
        fetchOk = true;
      }
    } catch (err) {
      console.warn(`[NEMT Week Sync] Network error for ${ymd}:`, err.message);
    }

    // Human-paced delay between requests (skip after the last one)
    if (i < weekDates.length - 1) {
      await new Promise(r => setTimeout(r, Math.random() * 1500 + 1000));
    }
  }

  // Persist updated metadata
  await new Promise(resolve =>
    chrome.storage.local.set({ scheduled_trips_meta: meta }, resolve)
  );

  const result = {
    total:   summary.total,
    dates:   summary.dates,
    drivers: summary.drivers.size,
  };

  // Notify any open trips tabs so the badge updates
  chrome.tabs.query({ url: '*://mtm.mtmlink.net/pe/v1/trips*' }, tabs => {
    tabs.forEach(tab =>
      chrome.tabs.sendMessage(tab.id, { action: 'weekSyncComplete', summary: result })
    );
  });

  return result;
}

// ── Message listener ───────────────────────────────────────────────────────────
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

  // Batch trips (from trips_scraper.js "Build Route" button and dashboard bridge)
  if (msg.action === 'openRouteBatch') {
    // Store as {label, trips} so the loader can display a named divider.
    // Plain-array trips (legacy path) still work via the loader's backward-compat check.
    chrome.storage.local.set({
      pendingTripsBatch: { label: msg.label || '', trips: msg.trips },
      pendingTripsBatchTime: Date.now()
    }, () => {
      if (chrome.runtime.lastError) return;
      const rbUrl = chrome.runtime.getURL('route_builder.html');
      chrome.tabs.query({}, (tabs) => {
        const existing = tabs.find(t => t.url && t.url.startsWith(rbUrl));
        if (existing) {
          chrome.tabs.update(existing.id, { active: true });
          chrome.windows.update(existing.windowId, { focused: true });
          chrome.tabs.sendMessage(existing.id, { action: 'loadPendingBatch' });
        } else {
          chrome.tabs.create({ url: rbUrl });
        }
      });
    });
    return false;
  }

  // Relay scheduled trips POST from content script — service workers are exempt
  // from Chrome's Local Network Access restriction that affects content scripts.
  if (msg.action === 'postScheduledTrips') {
    fetch('http://localhost:8765/scheduled_trips', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ date: msg.date, trips: msg.trips })
    })
      .then(r => sendResponse({ ok: r.ok }))
      .catch(() => sendResponse({ ok: false }));
    return true;
  }

  // Week sync: token captured by trips_bridge.js, relayed here by trips_scraper.js
  if (msg.action === 'syncWeekTrips') {
    if (_weekSyncInProgress) {
      // Already running — ignore duplicate (happens if user navigates between dates quickly)
      return false;
    }
    _weekSyncInProgress = true;
    syncWeekTrips(msg.token, msg.organizationId || '2853')
      .then(() => { _weekSyncInProgress = false; })
      .catch(err => {
        _weekSyncInProgress = false;
        console.warn('[NEMT Week Sync] Fatal:', err.message);
      });
    return false;
  }

  if (msg.type === 'GET_DEADHEAD_MILES') {
    const origin = anchorToIllinois(msg.origin);
    const destination = anchorToIllinois(msg.destination);
    const cacheKey = `${origin}||${destination}`;

    // Layer 1: in-memory cache (fastest)
    if (geocodeCache.has(cacheKey)) {
      sendResponse({ miles: geocodeCache.get(cacheKey) });
      return true;
    }

    // Layer 2: chrome.storage.local (persists across extension reloads)
    chrome.storage.local.get(['geocache'], (stored) => {
      const persistentCache = stored.geocache || {};

      if (persistentCache[cacheKey] !== undefined) {
        // Populate in-memory cache too
        geocodeCache.set(cacheKey, persistentCache[cacheKey]);
        sendResponse({ miles: persistentCache[cacheKey] });
        return;
      }

      // Layer 3: API call (last resort)
      const url = `https://maps.googleapis.com/maps/api/distancematrix/json` +
        `?origins=${encodeURIComponent(origin)}` +
        `&destinations=${encodeURIComponent(destination)}` +
        `&units=imperial` +
        `&key=${GMAPS_KEY}`;

      fetch(url)
        .then(r => r.json())
        .then(data => {
          const element = data.rows?.[0]?.elements?.[0];
          if (element?.status === 'OK') {
            const meters = element.distance.value;
            const miles = Math.round((meters / 1609.34) * 10) / 10;

            // Store in both cache layers
            geocodeCache.set(cacheKey, miles);
            persistentCache[cacheKey] = miles;

            // Limit persistent cache to 2000 entries to avoid storage bloat
            const keys = Object.keys(persistentCache);
            if (keys.length > 2000) {
              keys.slice(0, 200).forEach(k => delete persistentCache[k]);
            }

            chrome.storage.local.set({ geocache: persistentCache });
            sendResponse({ miles });
          } else {
            sendResponse({ miles: null });
          }
        })
        .catch(() => sendResponse({ miles: null }));
    });
    return true; // keep message channel open
  }

  // Geocode a single address → lat/lng + formatted result
  if (msg.type === 'GEOCODE_ADDRESS') {
    const addr = anchorToIllinois(msg.address);
    const url = `https://maps.googleapis.com/maps/api/geocode/json` +
      `?address=${encodeURIComponent(addr)}&key=${GMAPS_KEY}`;

    fetch(url)
      .then(r => r.json())
      .then(data => {
        if (data.status === 'OK' && data.results.length > 0) {
          const result = data.results[0];
          const loc  = result.geometry.location;
          const comp = result.address_components;
          const city  = (comp.find(c => c.types.includes('locality'))                          || {}).long_name  || '';
          const state = (comp.find(c => c.types.includes('administrative_area_level_1'))
                          || {}).short_name || '';
          sendResponse({
            lat: loc.lat, lng: loc.lng,
            formatted: result.formatted_address,
            cityState: city ? `${city}, ${state}` : result.formatted_address,
            error: null
          });
        } else {
          sendResponse({ lat: null, lng: null, error: data.status });
        }
      })
      .catch(e => sendResponse({ lat: null, lng: null, error: e.message }));

    return true;
  }
});
