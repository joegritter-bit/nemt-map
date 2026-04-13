// ============================================
// NEMT RATE DECODER - MTM Marketplace Overlay
// ============================================

// Guard — checked again inside processRows() and observer for SPA navigation safety

const COUNTY_BASE_RATES = {
  "Sangamon County": 65.00,
  "Vermilion County": 65.00,
  "Christian County": 55.00,
  "Macon County": 55.00,
  "Piatt County": 55.00,
  "Champaign County": 55.00,
  "Marion County": 50.00,
  "Jefferson County": 50.00,
  "Coles County": 40.00,
  "Fayette County": 40.00,
  "Clay County": 40.00,
};

const STANDARD_BASE_RATE = 20.00;
const MTM_MILEAGE_RATE = 1.50;
const MILEAGE_BAND_LIMIT = 5.0;
const MIN_PROFIT_PER_HOUR = 32.00;

const CITY_COUNTY_MAP = {
  // Contracted counties
  "springfield": "Sangamon County",
  "chatham": "Sangamon County",
  "mattoon": "Coles County",
  "charleston": "Coles County",
  "decatur": "Macon County",
  "champaign": "Champaign County",
  "urbana": "Champaign County",
  "rantoul": "Champaign County",
  "mahomet": "Champaign County",
  "savoy": "Champaign County",
  "danville": "Vermilion County",
  "hoopeston": "Vermilion County",
  "effingham": "Effingham County",
  "vandalia": "Fayette County",
  "centralia": "Marion County",
  "salem": "Marion County",
  "taylorville": "Christian County",
  "pana": "Christian County",
  "morrisonville": "Christian County",
  "assumption": "Christian County",
  "monticello": "Piatt County",
  "louisville": "Clay County",
  "flora": "Clay County",
  "peoria": "Peoria County",
  "bloomington": "McLean County",
  "normal": "McLean County",
  "chenoa": "McLean County",
  "carbondale": "Jackson County",
  "murphysboro": "Jackson County",
  "mt vernon": "Jefferson County",
  "mt. vernon": "Jefferson County",
  "mount vernon": "Jefferson County",

  // Southern Illinois
  "metropolis": "Massac County",
  "anna": "Union County",
  "benton": "Franklin County",
  "west frankfort": "Franklin County",
  "fairfield": "Wayne County",
  "olney": "Richland County",
  "noble": "Richland County",
  "lawrenceville": "Lawrence County",
  "carmi": "White County",
  "harrisburg": "Saline County",
  "herrin": "Williamson County",
  "marion": "Williamson County",
  "du quoin": "Perry County",
  "pinckneyville": "Perry County",
  "sparta": "Randolph County",
  "red bud": "Randolph County",
  "chester": "Randolph County",
  "belleville": "St. Clair County",
  "o'fallon": "St. Clair County",
  "collinsville": "Madison County",
  "alton": "Madison County",
  "edwardsville": "Madison County",
  "granite city": "Madison County",
  "jerseyville": "Jersey County",
  "carlinville": "Macoupin County",
  "staunton": "Macoupin County",
  "litchfield": "Montgomery County",
  "hillsboro": "Montgomery County",
  "sullivan": "Moultrie County",
  "shelbyville": "Shelby County",
  "stewardson": "Shelby County",
  "newton": "Jasper County",
  "robinson": "Crawford County",
  "palestine": "Crawford County",
  "mt carmel": "Wabash County",
  "albion": "Edwards County",

  // Central Illinois
  "washington": "Tazewell County",
  "east peoria": "Tazewell County",
  "morton": "Tazewell County",
  "canton": "Fulton County",
  "macomb": "McDonough County",
  "galesburg": "Knox County",
  "kewanee": "Henry County",
  "geneseo": "Henry County",
  "rock falls": "Whiteside County",
  "sterling": "Whiteside County",
  "dixon": "Lee County",
  "ottawa": "LaSalle County",
  "streator": "LaSalle County",
  "peru": "LaSalle County",
  "lasalle": "LaSalle County",
  "pontiac": "Livingston County",
  "lincoln": "Logan County",
  "clinton": "DeWitt County",
  "farmer city": "DeWitt County",
  "gibson city": "Ford County",
  "paxton": "Ford County",
  "watseka": "Iroquois County",
  "tuscola": "Douglas County",
  "arcola": "Douglas County",
  "paris": "Edgar County",
  "casey": "Clark County",
  "marshall": "Clark County",
};

const EXCLUDED_CITIES = [
  "chicago", "arlington heights", "palatine", "schaumburg",
  "naperville", "aurora", "elgin", "waukegan", "bolingbrook",
  "downers grove", "evanston", "joliet", "yorkville",
  "carpentersville", "hoffman estates", "rockdale", "lemont",
  "hazel crest", "east moline", "moline", "silvis", "rock island",
  "mchenry", "crystal lake", "algonquin", "oswego", "plainfield",
  "romeoville", "lockport", "homer glen", "tinley park",
  "orland park", "oak lawn", "cicero", "berwyn", "oak park",
  "des plaines", "mount prospect", "rolling meadows", "elk grove",
  "addison", "glendale heights", "carol stream", "wheaton",
  "glen ellyn", "lisle", "woodridge", "darien", "westmont",
  "lombard", "villa park", "elmhurst",
  "bensenville", "wood dale", "itasca", "roselle", "hanover park",
  "streamwood", "bartlett", "south elgin", "st charles",
  "geneva", "batavia", "north aurora", "montgomery",
  "sandwich", "plano", "seneca", "dwight", "pontiac",
  "kankakee", "bradley", "bourbonnais", "manteno"
];

const CLINIC_KEYWORDS = [
  "treatment", "recovery", "substance", "behavioral",
  "davita", "fresenius", "dialysis", "cancer", "radiation",
  "303 landmark", "century pointe", "gateway", "behavioral health"
];

// Regular rider addresses — loaded from bundled JSON
let REGULAR_RIDER_NORMALIZED = [];
let _sortingInProgress = false;

fetch('https://joegritter-bit.github.io/nemt-map/regular_riders.json?t=' + Date.now())
  .then(r => r.json())
  .then(data => {
    const addrs = data.addresses || [];
    REGULAR_RIDER_NORMALIZED = addrs.map(a => normalizeAddrJS(a));
    console.log(`NEMT: Loaded ${addrs.length} regular rider addresses`);
  })
  .catch(e => console.log('NEMT: No regular riders file', e));

function normalizeAddrJS(addr) {
  if (!addr) return '';
  addr = addr.replace(
    /,?\s*(apt|unit|ste|suite|#|lot|bldg|rm|apt\.)\s*\S*/gi, '');
  return addr.trim().toLowerCase().replace(/\s+/g, ' ');
}

function isRegularRider(pickupAddr) {
  if (!pickupAddr || REGULAR_RIDER_NORMALIZED.length === 0) return false;
  const n1 = normalizeAddrJS(pickupAddr);
  const num1 = n1.match(/^(\d+)/);
  if (!num1) return false;

  return REGULAR_RIDER_NORMALIZED.some(n2 => {
    const num2 = n2.match(/^(\d+)/);
    if (!num2 || num1[1] !== num2[1]) return false;
    const s1 = n1.slice(num1[1].length).trim().slice(0, 6);
    const s2 = n2.slice(num2[1].length).trim().slice(0, 6);
    if (s1.length < 4 || s2.length < 4) return false;
    return s2.startsWith(s1) || s1.startsWith(s2);
  });
}

function detectCounty(address) {
  if (!address) return "Unknown";
  const lower = address.toLowerCase();

  for (const city of EXCLUDED_CITIES) {
    if (lower.includes(city)) return "EXCLUDED";
  }

  for (const [city, county] of Object.entries(CITY_COUNTY_MAP)) {
    if (lower.includes(city)) return county;
  }

  const zipMatch = address.match(/\b(6[0-9]{4})\b/);
  if (zipMatch) {
    const zip = parseInt(zipMatch[1]);
    if (zip >= 62701 && zip <= 62799) return "Sangamon County";
    if (zip >= 62521 && zip <= 62526) return "Macon County";
    if (zip >= 61820 && zip <= 61822) return "Champaign County";
    if (zip >= 61830 && zip <= 61834) return "Vermilion County";
    if (zip >= 61832 && zip <= 61834) return "Vermilion County";
    if (zip >= 62401 && zip <= 62410) return "Effingham County";
    if (zip >= 62471 && zip <= 62471) return "Fayette County";
    if (zip >= 62801 && zip <= 62810) return "Marion County";
    if (zip >= 62864 && zip <= 62869) return "Jefferson County";
    if (zip >= 62801 && zip <= 62812) return "Marion County";
    if (zip >= 61938 && zip <= 61938) return "Coles County";
    if (zip >= 61920 && zip <= 61938) return "Coles County";
    if (zip >= 62440 && zip <= 62450) return "Clay County";
    if (zip >= 62423 && zip <= 62432) return "Clay County";
    if (zip >= 62450 && zip <= 62462) return "Fayette County";
    if (zip >= 62540 && zip <= 62560) return "Christian County";
    if (zip >= 61856 && zip <= 61856) return "Piatt County";
    if (zip >= 60000 && zip <= 60699) return "EXCLUDED";
    if (zip >= 60800 && zip <= 60999) return "EXCLUDED";
  }

  return "Unknown";
}

function isClinic(dropoffAddress) {
  if (!dropoffAddress) return false;
  const lower = dropoffAddress.toLowerCase();
  return CLINIC_KEYWORDS.some(k => lower.includes(k));
}

function calculatePayout(county, miles, pickupTime) {
  if (county === "EXCLUDED") return null;

  let base = (county === "Standard" || !county)
    ? STANDARD_BASE_RATE
    : (COUNTY_BASE_RATES[county] || STANDARD_BASE_RATE);

  if (pickupTime) {
    const timeLower = pickupTime.toLowerCase();
    const parts = pickupTime.replace(/[apm]/gi, '').trim().split(':');
    let hour = parseInt(parts[0]);
    const isPM = timeLower.includes('pm');
    const isAM = timeLower.includes('am');
    if (isPM && hour !== 12) hour += 12;
    if (isAM && hour === 12) hour = 0;
    if (hour < 6 || hour >= 18) base = Math.max(base, 20.00);
  }

  const billable = Math.max(0, (parseFloat(miles) || 0) - MILEAGE_BAND_LIMIT);
  const oneWay = base + (billable * MTM_MILEAGE_RATE);
  return Math.round(oneWay * 2 * 100) / 100;
}

function calcSingleTripRevHr(payout, miles, isClinicTrip, pickupAddress) {
  if (!payout) return null;

  const driveHrs = (parseFloat(miles) || 0) / 50;
  const waitHrs = isClinicTrip ? (5 / 60) : 1.0;
  const tripDuration = (driveHrs * 2) + waitHrs + 0.15;

  // Estimate deadhead from Effingham hub
  const lower = (pickupAddress || '').toLowerCase();
  const EFFINGHAM_DEADHEAD = {
    'springfield': 1.0, 'chatham': 1.0,
    'decatur': 0.6, 'taylorville': 0.7,
    'champaign': 0.8, 'urbana': 0.8,
    'rantoul': 0.9, 'danville': 1.1,
    'bloomington': 0.9, 'normal': 0.9,
    'clinton': 0.7, 'farmer city': 0.8,
    'mattoon': 0.4, 'charleston': 0.5,
    'paris': 0.7, 'robinson': 0.6,
    'olney': 0.5, 'fairfield': 0.6,
    'mt vernon': 0.8, 'benton': 0.8,
    'west frankfort': 0.9, 'carbondale': 1.1,
    'anna': 1.2, 'harrisburg': 0.9,
    'vandalia': 0.4, 'centralia': 0.6,
    'salem': 0.5, 'flora': 0.3,
    'louisville': 0.3, 'newton': 0.3,
    'streator': 1.5, 'ottawa': 1.6,
    'peoria': 1.4, 'galesburg': 1.8,
    'quincy': 2.2, 'macomb': 1.8,
    'jacksonville': 1.3
  };

  let deadheadHrs = 0.5; // default 30 min
  for (const [city, hrs] of Object.entries(EFFINGHAM_DEADHEAD)) {
    if (lower.includes(city)) { deadheadHrs = hrs; break; }
  }

  // Total shift time: deadhead out + trip + deadhead back
  const totalHrs = deadheadHrs + tripDuration + deadheadHrs;
  return totalHrs > 0 ? payout / totalHrs : null;
}

function getBadgeClass(payout, county, miles, isClinicTrip, pickupAddr) {
  if (county === "EXCLUDED") return "excluded";
  if (county === "Unknown") return "excluded";
  if (!payout) return "low-value";
  const revHr = calcSingleTripRevHr(payout, miles, isClinicTrip, pickupAddr);
  if (revHr === null) {
    if (payout >= 130) return "high-value";
    if (payout >= 80)  return "medium-value";
    return "low-value";
  }
  if (revHr >= 45) return "high-value";
  if (revHr >= 32) return "medium-value";
  return "low-value";
}


function formatFiberTime(isoStr) {
  if (!isoStr) return null;
  try {
    const d = new Date(isoStr);
    if (isNaN(d)) return null;
    let h = d.getHours(), m = d.getMinutes();
    const ampm = h >= 12 ? 'PM' : 'AM';
    h = h % 12 || 12;
    return `${h}:${String(m).padStart(2, '0')} ${ampm}`;
  } catch(e) { return null; }
}

function createBadge(pickupAddr, dropoffAddr, miles, tripTime, apptTime, rawPickupTime) {
  const county = detectCounty(pickupAddr);
  const payout = calculatePayout(county, parseFloat(miles) || 0, tripTime);
  const clinic = isClinic(dropoffAddr);

  const wrapper = document.createElement('div');
  wrapper.style.marginTop = '4px';

  if (county === "EXCLUDED") {
    wrapper.innerHTML = `<span class="nemt-badge excluded">🚫 Chicago Area — Skip</span>`;
    return wrapper;
  }

  const tripData = btoa(unescape(encodeURIComponent(JSON.stringify({
    pickup: pickupAddr, dropoff: dropoffAddr, miles: miles,
    time: tripTime, appt_time: apptTime || '', pickup_time: rawPickupTime || '',
    county: county, payout: payout, clinic: clinic
  }))));

  // Regular rider check — must come before county/payout rendering
  if (isRegularRider(pickupAddr)) {
    const rrPayout = calculatePayout(county, parseFloat(miles) || 0, tripTime);
    const rrRevHr = calcSingleTripRevHr(rrPayout, miles, false, pickupAddr);
    const rrRevHrStr = rrRevHr ? ` · $${rrRevHr.toFixed(0)}/hr` : '';
    const rrPayoutStr = rrPayout ? `Est. RT $${rrPayout.toFixed(2)}${rrRevHrStr}` : '';
    wrapper.innerHTML = `
      <div class="nemt-county">${(county && county !== 'EXCLUDED' && county !== 'Unknown') ? county : 'Verify county'}</div>
      <span class="nemt-badge regular-rider">⚡ REGULAR RIDER — ACCEPT NOW</span>
      ${rrPayoutStr ? `<span class="nemt-badge high-value" style="margin-left:4px;">${rrPayoutStr}</span>` : ''}
      <button class="nemt-add-btn nemt-route-btn" data-trip='${tripData}'>+ Route</button>
    `;
    const row = wrapper.closest('tr');
    if (row) row.classList.add('nemt-regular-rider-row');
    return wrapper;
  }

  if (county === "Unknown") {
    const stdPayout = calculatePayout("Standard", miles, rawPickupTime);
    const stdPayoutStr = stdPayout ? `Est. RT $${stdPayout.toFixed(2)}` : 'Est. RT $40.00';
    wrapper.innerHTML = `
      <div class="nemt-county">Outside primary area</div>
      <span class="nemt-badge low-value">${stdPayoutStr}</span>
      ${clinic ? '<span class="nemt-badge clinic">💊 Clinic</span>' : ''}
      <button class="nemt-add-btn nemt-route-btn" data-trip='${tripData}'>+ Route</button>
    `;
    return wrapper;
  }

  const revHr     = calcSingleTripRevHr(payout, miles, clinic, pickupAddr);
  const revHrStr  = revHr ? ` · $${revHr.toFixed(0)}/hr` : '';
  const payoutStr  = payout ? `Est. RT $${payout.toFixed(2)}${revHrStr}` : 'Rate Unknown';
  const badgeClass = getBadgeClass(payout, county, miles, clinic, pickupAddr);

  wrapper.innerHTML = `
    <div class="nemt-county">${county}</div>
    <span class="nemt-badge ${badgeClass}">${payoutStr}</span>
    ${clinic ? '<span class="nemt-badge clinic">💊 Clinic</span>' : ''}
    <button class="nemt-add-btn nemt-route-btn" data-trip='${tripData}'>+ Route</button>
  `;

  return wrapper;
}

function injectFiberBadge(row, pickupCell, attempt) {
  // Skip if already injected (guard against retries after success)
  if (pickupCell.querySelector('.nemt-fiber-div')) return;

  const allRows = Array.from(document.querySelectorAll('tr.ant-table-row'));
  const rowIndex = allRows.indexOf(row);
  if (rowIndex === -1) return;

  // One-time listener for the result from page context
  function onResult(e) {
    if (!e.detail || e.detail.rowIndex !== rowIndex) return;
    document.removeEventListener('nemt-fiber-result', onResult);

    const rec = e.detail.record;

    if (!rec) {
      if (attempt < 5) {
        setTimeout(() => injectFiberBadge(row, pickupCell, attempt + 1), 500);
      }
      return;
    }

    // Skip single-leg trips
    if (rec.appointmentTime === null || rec.appointmentTime === undefined) {
      return;
    }

    if (pickupCell.querySelector('.nemt-fiber-div')) return;

    const bPickupFmt = formatFiberTime(rec.requestedPickTime);
    const pickupNotes = rec.driverPickupNotes || '';
    const dropoffNotes = rec.driverDropoffNotes || '';

    let html = '';
    if (bPickupFmt) {
      html += `<span class="nemt-badge" style="background:#555;color:white;margin-right:4px;">🅱 Pickup: ${bPickupFmt}</span>`;
    } else {
      // Round trip confirmed (appointmentTime set) but B leg pickup time not yet assigned
      html += `<span class="nemt-badge" style="background:#7f8c8d;color:white;margin-right:4px;">🕐 B Leg: TBD</span>`;
    }
    if (pickupNotes) {
      html += `<span class="nemt-badge" style="background:#2980b9;color:white;margin-right:4px;">📋 ${pickupNotes}</span>`;
    }
    if (dropoffNotes) {
      html += `<span class="nemt-badge" style="background:#27ae60;color:white;margin-right:4px;">📋 Drop: ${dropoffNotes}</span>`;
    }

    if (html) {
      const fiberDiv = document.createElement('div');
      fiberDiv.className = 'nemt-fiber-div';
      fiberDiv.style.marginTop = '2px';
      fiberDiv.dataset.tripId = rec.providerTripId || rec.tripId || rec.id || '';
      fiberDiv.innerHTML = html;
      pickupCell.appendChild(fiberDiv);

      // Apply any pending badge update (B leg time / will call) stored while summary was open
      const tripId = fiberDiv.dataset.tripId;
      if (tripId && pendingBadgeUpdates.has(tripId)) {
        const { willCall, bLegTime } = pendingBadgeUpdates.get(tripId);
        applyBadgeUpdate(fiberDiv, willCall, bLegTime);
        pendingBadgeUpdates.delete(tripId);
      }
    }
  }

  document.addEventListener('nemt-fiber-result', onResult);
  document.dispatchEvent(new CustomEvent('nemt-get-fiber', { detail: { rowIndex } }));
}

function processRows() {
  if (!window.location.href.includes('marketplace')) return;

  const rows = document.querySelectorAll('tr.ant-table-row');

  rows.forEach(row => {
    if (row.querySelector('.nemt-badge')) return;

    const cells = row.querySelectorAll('td');
    if (cells.length < 5) return;

    try {
      const apptTime    = cells[0]?.innerText?.trim() || '';
      const pickupTime  = cells[1]?.innerText?.trim() || '';
      const tripTime    = (apptTime && apptTime !== '—' && apptTime !== '--') ? apptTime : pickupTime;
      const pickupAddr  = cells[2]?.innerText?.replace('\n', ', ')?.trim() || '';
      const dropoffAddr = cells[3]?.innerText?.replace('\n', ', ')?.trim() || '';
      const milesText   = cells[4]?.innerText?.replace('mi', '')?.trim() || '0';
      const miles       = parseFloat(milesText) || 0;

      if (!pickupAddr) return;

      const pickupCell = cells[2];
      const badge = createBadge(pickupAddr, dropoffAddr, miles, tripTime, apptTime, pickupTime);
      pickupCell.appendChild(badge);

      // Read fiber record for B-leg and notes data — with retry for timing
      injectFiberBadge(row, pickupCell, 0);

    } catch(e) {
      console.error('NEMT: Row processing error', e);
    }
  });

  sortAllRows();
}

function sortAllRows() {
  if (_sortingInProgress) return;
  _sortingInProgress = true;

  try {
    const table = document.querySelector('.ant-table-tbody, tbody');
    if (!table) return;

    const rows = Array.from(table.querySelectorAll('tr.ant-table-row'));
    if (rows.length < 2) return;

    function extractPayout(badge) {
      if (!badge) return 0;
      const match = badge.textContent.match(/\$(\d+\.?\d*)/);
      return match ? parseFloat(match[1]) : 0;
    }

    function getRowScore(row) {
      // Regular rider — always first
      if (row.querySelector('.regular-rider')) return 100000;

      // Excluded/Chicago — always last
      const excludedBadge = row.querySelector('.nemt-badge.excluded');
      if (excludedBadge) return -1;

      // Get county from the county div
      const countyEl = row.querySelector('.nemt-county');
      const countyText = countyEl ? countyEl.textContent.trim() : '';

      // Get payout for secondary sort within tier
      const badge = row.querySelector(
        '.nemt-badge.high-value, .nemt-badge.medium-value, .nemt-badge.low-value');
      const payout = badge ? extractPayout(badge) : 0;

      // Tier 1: $65 counties (Sangamon, Vermilion)
      if (countyText.includes('Sangamon') || countyText.includes('Vermilion'))
        return 50000 + payout;

      // Tier 2: $55 counties
      if (countyText.includes('Macon') || countyText.includes('Champaign') ||
          countyText.includes('Christian') || countyText.includes('Piatt'))
        return 40000 + payout;

      // Tier 3: $50 counties
      if (countyText.includes('Marion') || countyText.includes('Jefferson'))
        return 30000 + payout;

      // Tier 4: $40 counties
      if (countyText.includes('Coles') || countyText.includes('Fayette') ||
          countyText.includes('Clay'))
        return 20000 + payout;

      // Tier 5: Other known Illinois counties (in service area but lower rate)
      if (countyText && !countyText.includes('Outside') &&
          !countyText.includes('Unknown') && !countyText.includes('Verify'))
        return 10000 + payout;

      // Tier 6: Unknown/outside primary area
      if (countyText.includes('Outside') || countyText.includes('Unknown') ||
          countyText.includes('Verify'))
        return 5000 + payout;

      // Unprocessed rows — middle
      return 500;
    }

    // Skip if already sorted
    const scores = rows.map(getRowScore);
    let alreadySorted = true;
    for (let i = 0; i < scores.length - 1; i++) {
      if (scores[i] < scores[i + 1]) { alreadySorted = false; break; }
    }
    if (alreadySorted) return;

    const sorted = [...rows].sort((a, b) => getRowScore(b) - getRowScore(a));
    const fragment = document.createDocumentFragment();
    sorted.forEach(r => fragment.appendChild(r));
    table.appendChild(fragment);

    // County grouping — alternate background on county change
    let lastCounty = null;
    let colorToggle = false;
    sorted.forEach(row => {
      const countyEl = row.querySelector('.nemt-county');
      const county = countyEl ? countyEl.textContent.trim() : '';
      if (county !== lastCounty && lastCounty !== null) {
        colorToggle = !colorToggle;
      }
      row.style.backgroundColor = colorToggle ? '#fafffe' : '';
      lastCounty = county;
    });

  } finally {
    setTimeout(() => { _sortingInProgress = false; }, 1000);
  }
}

function autoToggleServiceArea() {
  let done = false;

  document.addEventListener('nemt-toggle-clicked', () => {
    done = true;
    console.log('[NEMT TOGGLE] clicked via MAIN world bridge');
  }, { once: true });

  function tryNow() {
    if (done) return;
    const toggleDiv = document.querySelector('div[class*="toggleServiceArea-"]');
    if (!toggleDiv) return;

    // Check if already ON
    const sw = toggleDiv.querySelector('button.ant-switch, button[role="switch"]');
    const isOn = sw
      ? (sw.classList.contains('ant-switch-checked') || sw.getAttribute('aria-checked') === 'true')
      : false;

    if (isOn) {
      done = true;
      observer.disconnect();
      console.log('[NEMT TOGGLE] already enabled');
      return;
    }

    console.log('[NEMT TOGGLE] found toggleServiceArea div — clicking');
    observer.disconnect();
    // Delegate to MAIN world bridge for the actual click
    document.dispatchEvent(new CustomEvent('nemt-toggle-check'));
  }

  const observer = new MutationObserver(() => tryNow());
  observer.observe(document.body, { childList: true, subtree: true });

  tryNow();

  setTimeout(() => {
    if (!done) {
      observer.disconnect();
      console.log('[NEMT TOGGLE] gave up — toggleServiceArea div never appeared');
    }
  }, 30000);
}

autoToggleServiceArea();

// Poll for page_bridge.js to set dataset.nemtBridgeLoaded before running processRows.
// Content scripts cannot read page window directly, so we use a DOM data attribute.
(function waitForBridge() {
  const TIMEOUT_MS = 5000;
  const start = Date.now();

  const interval = setInterval(() => {
    if (document.documentElement.dataset.nemtBridgeLoaded === '1') {
      clearInterval(interval);
      console.log('[NEMT] bridge ready — running processRows');
      processRows();
      return;
    }
    if (Date.now() - start > TIMEOUT_MS) {
      clearInterval(interval);
      console.log('[NEMT] bridge timeout — running processRows anyway');
      processRows();
    }
  }, 100);
})();

let _processTimer = null;

const observer = new MutationObserver((mutations) => {
  if (!window.location.href.includes('marketplace')) return;

  const hasTableChange = mutations.some(m =>
    m.addedNodes.length > 0 || m.removedNodes.length > 0
  );
  if (!hasTableChange) return;

  // Debounce — only process after DOM settles for 500ms
  clearTimeout(_processTimer);
  _processTimer = setTimeout(() => {
    processRows();
    setTimeout(sortAllRows, 300);
  }, 500);
});

observer.observe(document.body, { childList: true, subtree: true });

// Delegated click handler for + Route buttons
// Works across the content script / page isolation boundary
document.addEventListener('click', function(e) {
  const btn = e.target.closest('.nemt-route-btn');
  if (!btn) return;

  e.preventDefault();
  e.stopPropagation();

  try {
    const tripData = btn.getAttribute('data-trip');
    if (!tripData) return;

    const trip = JSON.parse(decodeURIComponent(escape(atob(tripData))));
    const tripObj = {
      pickup:      trip.pickup      || '',
      dropoff:     trip.dropoff     || '',
      miles:       trip.miles       || '',
      time:        trip.time        || '',
      appt_time:   trip.appt_time   || '',
      pickup_time: trip.pickup_time || '',
      county:      trip.county      || '',
      payout:      trip.payout      || '',
      clinic:      trip.clinic      || false
    };

    // Send to background — it stores in session storage then opens tab
    chrome.runtime.sendMessage({ action: 'openRouteBuilder', tripData: tripObj });

    btn.textContent = '✓ Added';
    btn.style.background = '#27ae60';
    setTimeout(() => {
      btn.textContent = '+ Route';
      btn.style.background = '#2c3e50';
    }, 1500);

  } catch(err) {
    console.error('NEMT: Failed to open route builder', err);
  }
});

// ============================================================
// TRIP SUMMARY OBSERVER — reads B leg data from Trip Summary
// panel when user clicks the > button on a marketplace row.
// READ ONLY — never clicks Accept or any action button.
// ============================================================

let currentlyViewingTripId = null;
let lastSummaryReadTime = 0;
const pendingBadgeUpdates = new Map(); // key: providerTripId, value: { willCall, bLegTime }

// Capture tripId when user clicks the blue arrow (>) on a row
document.addEventListener('click', function(e) {
  const arrow = e.target.closest('img.mtm-icon, [class*="viewTrip"], td:last-child button');
  if (!arrow) return;
  const row = arrow.closest('tr.ant-table-row');
  if (!row) return;
  const fiberDiv = row.querySelector('.nemt-fiber-div[data-trip-id]');
  if (fiberDiv) {
    currentlyViewingTripId = fiberDiv.dataset.tripId;
  }
}, true); // capture phase so we see it before React

function parseTripSummaryPanel(container, attempt, onDone) {
  // Click the B Leg tab on first attempt so React renders B leg content
  if (attempt === 0) {
    const tabs = container.querySelectorAll('.ant-tabs-tab');
    const bLegTab = [...tabs].find(t => t.textContent.includes('B Leg'));
    if (bLegTab) {
      bLegTab.click();
    }
    // Wait 600ms after tab click for React to render B leg content, then re-enter
    setTimeout(() => parseTripSummaryPanel(container, 1, onDone), 600);
    return;
  }

  const checkboxes = container.querySelectorAll('.ant-checkbox-wrapper');
  const dataEls    = container.querySelectorAll('[class*="data-"]');
  const times = [];
  dataEls.forEach(el => {
    const text = el.textContent.trim();
    if (/^\d+:\d+\s*(AM|PM)$/i.test(text)) times.push(text);
  });

  // Validate render is complete — need >= 6 checkboxes and >= 2 times
  if ((checkboxes.length < 6 || times.length < 2) && attempt < 4) {
    setTimeout(() => parseTripSummaryPanel(container, attempt + 1, onDone), 500);
    return;
  }

  const providerTripId = currentlyViewingTripId;
  const bLegTime = times[1] || null;
  const willCall = checkboxes[5]
    ? checkboxes[5].querySelector('input')?.checked === true
    : false;

  onDone({ providerTripId, bLegTime, willCall });
}

function applyBadgeUpdate(fiberDiv, willCall, bLegTime) {
  let html = '';
  if (willCall) {
    html = `<span class="nemt-badge" style="background:#c0392b;color:white;margin-right:4px;">⚠️ WILL CALL</span>`;
  } else if (bLegTime) {
    html = `<span class="nemt-badge" style="background:#555;color:white;margin-right:4px;">🅱 Pickup: ${bLegTime}</span>`;
  }
  if (!html) return;
  const firstSpan = fiberDiv.querySelector('span');
  if (firstSpan) firstSpan.outerHTML = html;
}

function updateRowFiberBadge(providerTripId, willCall, bLegTime) {
  if (!providerTripId) {
    return;
  }
  pendingBadgeUpdates.set(providerTripId, { willCall, bLegTime });
}

function observeTripSummary() {
  let summaryObserver = null;
  let summaryWasOpen = false;

  function attachObserver() {
    if (summaryObserver) summaryObserver.disconnect();

    summaryObserver = new MutationObserver(() => {
      const container = document.querySelector('[class*="marketplaceTripSummaryContainer"]');

      // Summary just closed — marketplace is re-mounting, re-process rows
      if (!container && summaryWasOpen) {
        summaryWasOpen = false;
        setTimeout(() => processRows(), 500);
        return;
      }

      if (!container) return;

      // Debounce — ignore if we read within the last 2 seconds
      if (Date.now() - lastSummaryReadTime < 2000) return;

      summaryWasOpen = true;

      // Disconnect immediately — re-attach after reading
      summaryObserver.disconnect();
      summaryObserver = null;
      lastSummaryReadTime = Date.now();

      // Wait 800ms for React to fully render both legs
      setTimeout(() => {
        parseTripSummaryPanel(container, 0, ({ providerTripId, bLegTime, willCall }) => {
          updateRowFiberBadge(providerTripId, willCall, bLegTime);
          attachObserver();
        });
      }, 800);
    });

    summaryObserver.observe(document.body, { childList: true, subtree: true });
  }

  // Handle case where summary is already open on script load
  const existing = document.querySelector('[class*="marketplaceTripSummaryContainer"]');
  if (existing) {
    summaryWasOpen = true;
    setTimeout(() => {
      parseTripSummaryPanel(existing, 0, ({ providerTripId, bLegTime, willCall }) => {
        updateRowFiberBadge(providerTripId, willCall, bLegTime);
      });
    }, 800);
  }

  attachObserver();
}

observeTripSummary();
