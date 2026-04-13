// ── CONSTANTS ──────────────────────────────────────────────────────────────────
const COUNTY_BASE_RATES = {
  "Sangamon County": 65.00, "Vermilion County": 65.00,
  "Christian County": 55.00, "Macon County": 55.00,
  "Piatt County": 55.00, "Champaign County": 55.00,
  "Marion County": 50.00, "Jefferson County": 50.00,
  "Coles County": 40.00, "Fayette County": 40.00, "Clay County": 40.00,
};
const STANDARD_BASE_RATE = 20.00;
const MTM_MILEAGE_RATE   = 1.50;
const MILEAGE_BAND_LIMIT = 5.0;
const AVG_MPH            = 50;
const MAX_SHIFT_HOURS    = 11.0;
const MIN_REV_PER_HOUR   = 32.0;
const STANDARD_WAIT_HRS  = 1.0;
const CLINIC_WAIT_HRS    = 5 / 60;

const HUB_COORDS = {
  'Effingham':   { lat: 39.1200, lng: -88.5434 },
  'Springfield': { lat: 39.8017, lng: -89.6680 }
};

const CITY_COORDS = {
  'springfield':    { lat: 39.7817, lng: -89.6501 },
  'chatham':        { lat: 39.6736, lng: -89.7031 },
  'champaign':      { lat: 40.1164, lng: -88.2434 },
  'urbana':         { lat: 40.1106, lng: -88.2073 },
  'danville':       { lat: 40.1242, lng: -87.6297 },
  'decatur':        { lat: 39.8403, lng: -88.9548 },
  'bloomington':    { lat: 40.4842, lng: -88.9937 },
  'normal':         { lat: 40.5142, lng: -88.9906 },
  'clinton':        { lat: 40.1533, lng: -88.9642 },
  'rantoul':        { lat: 40.3053, lng: -88.1550 },
  'effingham':      { lat: 39.1200, lng: -88.5434 },
  'mattoon':        { lat: 39.4775, lng: -88.3728 },
  'charleston':     { lat: 39.4953, lng: -88.1764 },
  'taylorville':    { lat: 39.5467, lng: -89.2942 },
  'monticello':     { lat: 40.0239, lng: -88.5750 },
  'lincoln':        { lat: 40.1486, lng: -89.3648 },
  'mahomet':        { lat: 40.1939, lng: -88.4056 },
  'savoy':          { lat: 40.0628, lng: -88.2545 },
  'hoopeston':      { lat: 40.4664, lng: -87.6688 },
  'pontiac':        { lat: 40.8811, lng: -88.6298 },
  'dwight':         { lat: 41.0950, lng: -88.4298 },
  'pana':           { lat: 39.3889, lng: -89.0801 },
  'assumption':     { lat: 39.5197, lng: -89.0490 },
  'morrisonville':  { lat: 39.4220, lng: -89.4648 },
  'sullivan':       { lat: 39.5989, lng: -88.6073 },
  'tuscola':        { lat: 39.7992, lng: -88.2834 },
  'arcola':         { lat: 39.6836, lng: -88.3064 },
  'shelbyville':    { lat: 39.4070, lng: -88.7940 },
  'salem':          { lat: 38.6270, lng: -88.9456 },
  'vandalia':       { lat: 38.9609, lng: -89.0940 },
  'centralia':      { lat: 38.5245, lng: -89.1334 },
  'flora':          { lat: 38.6673, lng: -88.4856 },
  'olney':          { lat: 38.7306, lng: -88.0851 },
  'fairfield':      { lat: 38.3778, lng: -88.3592 },
  'benton':         { lat: 38.0009, lng: -88.9201 },
  'west frankfort': { lat: 37.8978, lng: -88.9290 },
  'carbondale':     { lat: 37.7273, lng: -89.2167 },
  'anna':           { lat: 37.4612, lng: -89.2434 },
  'robinson':       { lat: 39.0031, lng: -87.7348 },
  'lawrenceville':  { lat: 38.7278, lng: -87.6816 },
  'harrisburg':     { lat: 37.7381, lng: -88.5373 },
  'carmi':          { lat: 38.0909, lng: -88.1589 },
  'newton':         { lat: 38.9981, lng: -88.1631 },
  'albion':         { lat: 38.3756, lng: -88.0578 },
  'mt carmel':      { lat: 38.4106, lng: -87.7639 },
  'havana':         { lat: 40.3003, lng: -90.0612 },
  'beardstown':     { lat: 39.9978, lng: -90.4237 },
  'mt pulaski':     { lat: 40.0103, lng: -89.2834 },
  'atlanta':        { lat: 40.2589, lng: -89.2334 },
  'gibson city':    { lat: 40.4619, lng: -88.3742 },
  'paxton':         { lat: 40.4594, lng: -88.0987 },
  'streator':       { lat: 41.1214, lng: -88.8362 },
  'ottawa':         { lat: 41.3456, lng: -88.8426 },
  'lasalle':        { lat: 41.3484, lng: -89.0918 },
  'peru':           { lat: 41.3345, lng: -89.1290 },
  'kankakee':       { lat: 41.1200, lng: -87.8612 },
  'peoria':         { lat: 40.6936, lng: -89.5890 },
  'east peoria':    { lat: 40.6678, lng: -89.5390 },
  'washington':     { lat: 40.7031, lng: -89.4084 },
  'morton':         { lat: 40.6114, lng: -89.4637 },
  'galesburg':      { lat: 40.9478, lng: -90.3712 },
  'macomb':         { lat: 40.4589, lng: -90.6718 },
  'quincy':         { lat: 39.9356, lng: -91.4099 },
  'jacksonville':   { lat: 39.7345, lng: -90.2290 },
  'watseka':        { lat: 40.7767, lng: -87.7362 },
  'metropolis':     { lat: 37.1514, lng: -88.7320 },
  'murphysboro':    { lat: 37.7648, lng: -89.3354 },
};

const SPRINGFIELD_CITIES = [
  'springfield','chatham','taylorville','decatur',
  'champaign','urbana','rantoul','bloomington','normal',
  'clinton','lincoln','danville','mahomet','savoy',
  'monticello','farmer city','atlanta','pontiac','dwight',
  'gibson city','paxton','tuscola','arcola','sullivan',
  'pana','morrisonville','assumption','mt pulaski',
  'havana','beardstown'
];
const EFFINGHAM_CITIES = [
  'effingham','mattoon','charleston','vandalia',
  'centralia','salem','flora','louisville',
  'olney','fairfield','mt vernon','benton',
  'west frankfort','carbondale','anna','robinson',
  'lawrenceville','paris','casey','marshall',
  'newton','wayne city','albion','carmi','mt carmel','harrisburg'
];

const CITY_COUNTY_MAP = {
  "springfield":"Sangamon County","chatham":"Sangamon County",
  "mattoon":"Coles County","charleston":"Coles County",
  "decatur":"Macon County","champaign":"Champaign County",
  "urbana":"Champaign County","danville":"Vermilion County",
  "effingham":"Effingham County","vandalia":"Fayette County",
  "centralia":"Marion County","salem":"Marion County",
  "taylorville":"Christian County","monticello":"Piatt County",
  "louisville":"Clay County","flora":"Clay County",
  "peoria":"Peoria County","bloomington":"McLean County","normal":"McLean County",
  "rantoul":"Champaign County","savoy":"Champaign County","mahomet":"Champaign County",
  "st. joseph":"Champaign County","pesotum":"Champaign County",
  "hoopeston":"Vermilion County","georgetown":"Vermilion County",
  "clinton":"DeWitt County","farmer city":"DeWitt County",
  "chenoa":"McLean County","pontiac":"Livingston County","dwight":"Livingston County",
  "pana":"Christian County","morrisonville":"Christian County","assumption":"Christian County",
  "shelbyville":"Shelby County","sullivan":"Moultrie County",
  "tuscola":"Douglas County","arcola":"Douglas County","arthur":"Douglas County",
  "newton":"Jasper County","robinson":"Crawford County","lawrenceville":"Lawrence County",
  "olney":"Richland County","fairfield":"Wayne County",
  "benton":"Franklin County","west frankfort":"Franklin County",
  "anna":"Union County","metropolis":"Massac County","harrisburg":"Saline County",
  "herrin":"Williamson County","marion":"Williamson County",
  "carbondale":"Jackson County","murphysboro":"Jackson County",
  "washington":"Tazewell County","east peoria":"Tazewell County",
  "morton":"Tazewell County","pekin":"Tazewell County",
  "lincoln":"Logan County","ottawa":"LaSalle County","streator":"LaSalle County",
  "mcleansboro":"Hamilton County","carmi":"White County",
  "albion":"Edwards County","mt carmel":"Wabash County"
};

const CLINIC_KEYWORDS = [
  "treatment","recovery","substance","behavioral",
  "davita","fresenius","dialysis","cancer","radiation",
  "303 landmark","century pointe","gateway"
];

// ── STATE ──────────────────────────────────────────────────────────────────────
let trips = [];
let hubManuallySelected = false;

// ── INIT: Build rates reference table ─────────────────────────────────────────
(function() {
  const t = document.getElementById('rates-table');
  Object.entries(COUNTY_BASE_RATES)
    .sort((a,b) => b[1]-a[1])
    .forEach(([county, rate]) => {
      const tr = document.createElement('tr');
      tr.innerHTML = `<td>${county.replace(' County','')}</td><td>$${rate.toFixed(2)}</td>`;
      t.appendChild(tr);
    });
  const tr = document.createElement('tr');
  tr.innerHTML = `<td style="color:#bbb">Other</td><td>$${STANDARD_BASE_RATE.toFixed(2)}</td>`;
  t.appendChild(tr);
})();

// ── HELPERS ────────────────────────────────────────────────────────────────────
function detectCounty(addr) {
  const lower = addr.toLowerCase();
  for (const [city, county] of Object.entries(CITY_COUNTY_MAP)) {
    if (lower.includes(city)) return county;
  }
  // ZIP code fallback
  const zipMatch = addr.match(/\b(6[0-9]{4})\b/);
  if (zipMatch) {
    const zip = parseInt(zipMatch[1]);
    if (zip >= 61820 && zip <= 61825) return "Champaign County";
    if (zip >= 61840 && zip <= 61880) return "Champaign County";
    if (zip >= 61832 && zip <= 61834) return "Vermilion County";
    if (zip >= 62701 && zip <= 62799) return "Sangamon County";
    if (zip >= 62521 && zip <= 62526) return "Macon County";
    if (zip >= 62401 && zip <= 62410) return "Effingham County";
    if (zip >= 62801 && zip <= 62812) return "Marion County";
    if (zip >= 62864 && zip <= 62869) return "Jefferson County";
    if (zip >= 61920 && zip <= 61938) return "Coles County";
    if (zip >= 62540 && zip <= 62560) return "Christian County";
    if (zip >= 61856 && zip <= 61856) return "Piatt County";
  }
  return null;
}

function detectClinic(addr) {
  const lower = addr.toLowerCase();
  return CLINIC_KEYWORDS.some(k => lower.includes(k));
}

function calcPayout(miles, timeStr, county, riders) {
  const base = COUNTY_BASE_RATES[county] || STANDARD_BASE_RATE;
  let effectiveBase = base;
  if (timeStr) {
    const h = parseInt(timeStr.split(':')[0]);
    if (h < 6 || h >= 18) effectiveBase = Math.max(base, 20.00);
  }
  const billable = Math.max(0, miles - MILEAGE_BAND_LIMIT);
  const oneWay   = effectiveBase + (billable * MTM_MILEAGE_RATE);
  return +(oneWay * 2 * riders).toFixed(2);
}

function formatTime(t) {
  if (!t) return '';
  const [h, m] = t.split(':').map(Number);
  return `${h % 12 || 12}:${String(m).padStart(2,'0')} ${h >= 12 ? 'PM' : 'AM'}`;
}

function getHub() {
  return document.querySelector('input[name="hub"]:checked').value;
}

function parseTime(timeStr) {
  if (!timeStr || timeStr === '--' || timeStr === '—') return null;
  timeStr = timeStr.trim();
  const ampm = timeStr.match(/(\d+):(\d+)\s*(AM|PM)/i);
  if (ampm) {
    let h = parseInt(ampm[1]);
    const m = parseInt(ampm[2]);
    const isPM = ampm[3].toUpperCase() === 'PM';
    if (isPM && h !== 12) h += 12;
    if (!isPM && h === 12) h = 0;
    return h * 60 + m;
  }
  const mil = timeStr.match(/(\d+):(\d+)/);
  if (mil) return parseInt(mil[1]) * 60 + parseInt(mil[2]);
  return null;
}

function minutesToTimeStr(mins) {
  if (mins === null || mins === undefined) return '--';
  const h = Math.floor(mins / 60) % 24;
  const m = mins % 60;
  const ampm = h >= 12 ? 'PM' : 'AM';
  const h12 = h % 12 || 12;
  return `${h12}:${String(m).padStart(2,'0')} ${ampm}`;
}

function calcTripDuration(miles, isClinic) {
  const driveHrs = (parseFloat(miles) || 0) / AVG_MPH;
  const waitHrs  = isClinic ? CLINIC_WAIT_HRS : STANDARD_WAIT_HRS;
  return (driveHrs * 2) + waitHrs + 0.15;
}

function estimateDistanceMiles(lat1, lng1, lat2, lng2) {
  const latDiff = (lat2 - lat1) * 69;
  const lngDiff = (lng2 - lng1) * 55;
  return Math.sqrt(latDiff * latDiff + lngDiff * lngDiff);
}

function getHubCoords() {
  return HUB_COORDS[getHub()] || HUB_COORDS['Effingham'];
}

function getPickupCityCoords(address) {
  const lower = address.toLowerCase();
  for (const [city, coords] of Object.entries(CITY_COORDS)) {
    if (lower.includes(city)) return coords;
  }
  return null;
}

function calcDeadheadHours(address) {
  const hub  = getHubCoords();
  const city = getPickupCityCoords(address);
  if (city) {
    return estimateDistanceMiles(hub.lat, hub.lng, city.lat, city.lng) / AVG_MPH;
  }
  // City not in lookup — use hub-specific average and flag for display
  window._deadheadEstimated = true;
  return getHub() === 'Springfield' ? 0.6 : 0.5;
}

function getDeadheadMiles() {
  if (!trips.length) return null;
  const hub  = getHubCoords();
  const city = getPickupCityCoords(trips[0].pickup);
  if (!city) return null;
  return Math.round(estimateDistanceMiles(hub.lat, hub.lng, city.lat, city.lng));
}

function estimateTotalHours() {
  if (!trips.length) return 0;
  const hubToFirst = calcDeadheadHours(trips[0].pickup);
  const lastToHub  = calcDeadheadHours(trips[trips.length - 1].pickup);
  let total = hubToFirst + lastToHub;
  trips.forEach((t, i) => {
    total += t.duration_hrs;
    if (i < trips.length - 1) total += 0.1; // deadhead between trips (~6 min)
  });
  return +total.toFixed(2);
}

// ── HUB AUTO-SELECT ────────────────────────────────────────────────────────────
function updateSwitchBtnLabel() {
  const btn = document.getElementById('switchHubBtn');
  if (!btn) return;
  const other = getHub() === 'Springfield' ? 'Effingham' : 'Springfield';
  btn.textContent = `⇄ Switch to ${other}`;
}

function autoSelectHub(pickupAddress) {
  if (hubManuallySelected) return; // user made a deliberate choice
  if (trips.length > 0) return;    // only on first trip
  const lower = pickupAddress.toLowerCase();
  let suggestedHub = null;
  for (const city of SPRINGFIELD_CITIES) {
    if (lower.includes(city)) { suggestedHub = 'Springfield'; break; }
  }
  if (!suggestedHub) {
    for (const city of EFFINGHAM_CITIES) {
      if (lower.includes(city)) { suggestedHub = 'Effingham'; break; }
    }
  }
  if (!suggestedHub) suggestedHub = 'Effingham';

  const eff = document.getElementById('hubEffingham');
  const spr = document.getElementById('hubSpringfield');
  if (!eff || !spr) return;
  if (suggestedHub === 'Springfield') { spr.checked = true; eff.checked = false; }
  else { eff.checked = true; spr.checked = false; }

  let notice = document.getElementById('hubNotice');
  if (!notice) {
    notice = document.createElement('div');
    notice.id = 'hubNotice';
    notice.style.cssText = 'font-size:11px;color:#27ae60;margin-top:4px;height:16px;';
    document.querySelector('.hub-selector')?.appendChild(notice);
  }
  notice.textContent = `🎯 Auto-selected ${suggestedHub} hub`;
  setTimeout(() => { notice.textContent = ''; }, 3000);
  updateSwitchBtnLabel();
}

// ── ACTIONS ────────────────────────────────────────────────────────────────────
function addTrip() {
  const pickup  = document.getElementById('pickup').value.trim();
  const dropoff = document.getElementById('dropoff').value.trim();
  const miles   = parseFloat(document.getElementById('miles').value) || 0;
  const time    = document.getElementById('pickup_time').value;
  const riders  = Math.min(4, Math.max(1, parseInt(document.getElementById('riders').value) || 1));

  autoSelectHub(pickup);

  if (!pickup || !dropoff) {
    alert('Pickup and Dropoff addresses are required.');
    return;
  }

  const county          = detectCounty(pickup);
  const baseRate        = COUNTY_BASE_RATES[county] || STANDARD_BASE_RATE;
  const payout          = calcPayout(miles, time, county, riders);
  const isClinic        = detectClinic(dropoff);
  const duration_hrs    = calcTripDuration(miles, isClinic);
  const apptMins        = parseTime(time);
  const driveMins       = (miles / AVG_MPH) * 60;
  const pickupMins      = apptMins !== null ? Math.round(apptMins - driveMins) : null;
  const pickup_time_calc = minutesToTimeStr(pickupMins);

  trips.push({ pickup, dropoff, miles, time, riders, county, baseRate, payout, isClinic, duration_hrs, pickup_time_calc, hub: getHub() });

  // Reset form
  document.getElementById('pickup').value = '';
  document.getElementById('dropoff').value = '';
  document.getElementById('miles').value = '';
  document.getElementById('riders').value = '1';
  document.getElementById('pickup').focus();

  render();
}

function removeTrip(idx) {
  trips.splice(idx, 1);
  render();
}

function clearRoute() {
  if (trips.length && !confirm('Clear all trips?')) return;
  trips = [];
  hubManuallySelected = false;
  render();
}

// ── RENDER ─────────────────────────────────────────────────────────────────────
function render() {
  const totalRev  = trips.reduce((s, t) => s + t.payout, 0);
  window._deadheadEstimated = false;
  const totalHrs  = estimateTotalHours();
  const deadheadEstimated = window._deadheadEstimated;
  const revHr     = totalHrs > 0 ? totalRev / totalHrs : 0;
  const remaining = Math.max(0, MAX_SHIFT_HOURS - totalHrs);

  // Totals
  document.getElementById('stat-revenue').textContent = `$${totalRev.toFixed(2)}`;

  const hoursEl = document.getElementById('stat-hours');
  hoursEl.textContent = `${totalHrs.toFixed(1)}h`;
  hoursEl.className = `stat-value ${totalHrs > MAX_SHIFT_HOURS ? 'warn' : 'neutral'}`;
  const dhEl = document.getElementById('deadheadMiles');
  if (dhEl) {
    const dh = getDeadheadMiles();
    if (deadheadEstimated) {
      dhEl.textContent = '⚠️ est.';
    } else {
      dhEl.textContent = dh !== null ? dh : '?';
    }
  }

  const revHrEl = document.getElementById('stat-revhr');
  if (!trips.length) { revHrEl.textContent = '—'; revHrEl.className = 'stat-value'; }
  else {
    revHrEl.textContent = `$${revHr.toFixed(2)}`;
    revHrEl.className = `stat-value${revHr < MIN_REV_PER_HOUR ? ' warn' : ''}`;
  }

  const remEl = document.getElementById('stat-remaining');
  remEl.textContent = `${remaining.toFixed(1)}h`;
  remEl.className = `stat-value ${remaining <= 0 ? 'warn' : 'neutral'}`;

  // Warnings
  const warnDiv = document.getElementById('warnings');
  warnDiv.innerHTML = '';
  if (trips.length && totalHrs > MAX_SHIFT_HOURS)
    warnDiv.innerHTML += `<div class="warning-banner">⚠️ Shift exceeds ${MAX_SHIFT_HOURS}h limit — estimated ${totalHrs.toFixed(1)}h</div>`;
  if (trips.length && revHr < MIN_REV_PER_HOUR)
    warnDiv.innerHTML += `<div class="warning-banner">⚠️ Below minimum profit threshold ($${MIN_REV_PER_HOUR}/hr) — currently $${revHr.toFixed(2)}/hr</div>`;

  // Trip cards
  const area = document.getElementById('trips-area');
  if (!trips.length) {
    area.innerHTML = '<div class="empty-state">No trips yet.<br>Fill in the form and click <b>Add Trip</b>.</div>';
  } else {
    area.innerHTML = trips.map((t, i) => `
      <div class="trip-card${t.isClinic ? ' clinic' : ''}" data-trip-idx="${i}">
        <div class="trip-header">
          <div>
            <div class="trip-title">Trip ${i+1} &nbsp;·&nbsp; ${getHub()} → ${t.pickup.split(',')[0].trim()} → ${t.dropoff.split(',')[0].trim()}</div>
            <div class="trip-subtitle">${t.pickup}</div>
          </div>
          <button class="btn-remove" data-idx="${i}">Remove</button>
        </div>
        <div class="trip-details">
          <b>County:</b> ${t.county || `<span style="color:#e67e22">Unknown (using $${STANDARD_BASE_RATE.toFixed(2)})</span>`}<br>
          <b>Base Rate:</b> $${t.baseRate.toFixed(2)} &nbsp;&nbsp;
          <b>Miles:</b> ${t.miles} &nbsp;&nbsp;
          <b>Riders:</b> ${t.riders}
          ${t.isClinic ? '<br><span class="clinic-badge">💊 CLINIC</span>' : ''}
          <div style="font-size:11px; color:#666; margin-top:4px;">
            Appt: <b>${t.time || '--'}</b> &nbsp;|&nbsp;
            Est. Pickup: <b>${t.pickup_time_calc || '--'}</b> &nbsp;|&nbsp;
            Duration: <b>${t.duration_hrs.toFixed(1)}h</b> &nbsp;|&nbsp;
            Wait: <b>${t.isClinic ? '5 min (clinic)' : '1 hr'}</b>
          </div>
        </div>
        <div class="payout">Estimated RT Payout: $${t.payout.toFixed(2)}</div>
        <div style="font-size:11px;color:#888;margin-top:2px;">
          Rev/Hr this trip: <b style="color:#27ae60;">$${(t.duration_hrs > 0 ? t.payout / t.duration_hrs : 0).toFixed(2)}/hr</b>
          (${t.duration_hrs.toFixed(1)}h total inc. wait &amp; return)
        </div>
      </div>`).join('');
  }

  // Route flow
  const hub = getHub();
  const flow = [`${hub} Hub`];
  trips.forEach(t => flow.push(`${formatTime(t.time)} ${t.pickup.split(',')[0].trim()}`));
  if (trips.length) flow.push(`${hub} Hub`);
  document.getElementById('route-flow').textContent = flow.join(' → ');
  flagMultiLoads();
  checkTimeConflicts();
}

// ── EXPORT / PERSIST ───────────────────────────────────────────────────────────
function getTotalRevenue() {
  return trips.reduce((s, t) => s + (t.payout || 0), 0);
}
function getTotalHours() {
  return estimateTotalHours();
}
function getRevPerHour() {
  const hrs = getTotalHours();
  return hrs > 0 ? getTotalRevenue() / hrs : 0;
}
function getRouteFlowText() {
  const hub = getHub();
  if (!trips.length) return `${hub} Hub`;
  const stops = trips.map(t => t.pickup.split(',')[0].trim()).join(' → ');
  return `${hub} Hub → ${stops} → ${hub} Hub`;
}

function copyRouteSummary() {
  if (!trips.length) { alert('No trips to copy.'); return; }
  const hub = getHub();
  let msg = `🚗 DISPATCH ROUTE — ${hub} Hub\n`;
  msg += `Date: ${new Date().toLocaleDateString()}\n`;
  msg += `━━━━━━━━━━━━━━━━━━━━━━━\n`;
  trips.forEach((t, i) => {
    msg += `\nTrip ${i+1}`;
    if (t.time) msg += ` | Appt: ${t.time}`;
    msg += `\n`;
    msg += `  📍 Pickup: ${t.pickup}\n`;
    msg += `  🏥 Dropoff: ${t.dropoff}\n`;
    msg += `  Miles: ${t.miles || '?'} | Est. Payout: $${t.payout?.toFixed(2) || '?'}\n`;
    if (t.isClinic) msg += `  💊 CLINIC — 5 min wait\n`;
  });
  msg += `\n━━━━━━━━━━━━━━━━━━━━━━━\n`;
  msg += `Total Revenue: $${getTotalRevenue().toFixed(2)}\n`;
  msg += `Est. Hours: ${getTotalHours().toFixed(1)}h\n`;
  msg += `Rev/Hour: $${getRevPerHour().toFixed(2)}/hr\n`;
  msg += `\nRoute: ${getRouteFlowText()}`;
  const btn = document.querySelector('button[onclick*="copyRouteSummary"]');
  navigator.clipboard.writeText(msg).then(() => {
    if (btn) { btn.textContent = '✓ Copied!'; setTimeout(() => btn.textContent = '📋 Copy Route Summary', 2000); }
  }).catch(() => prompt('Copy this text:', msg));
}

function saveRoute() {
  if (!trips.length) { alert('No trips to save.'); return; }
  localStorage.setItem('nemt_saved_route', JSON.stringify({ trips, hub: getHub() }));
  alert('Route saved to browser storage.');
}

function loadRoute() {
  const raw = localStorage.getItem('nemt_saved_route');
  if (!raw) { alert('No saved route found.'); return; }
  const data = JSON.parse(raw);
  trips = data.trips || [];
  const radio = document.querySelector(`input[name="hub"][value="${data.hub}"]`);
  if (radio) radio.checked = true;
  render();
  alert(`Loaded ${trips.length} trip(s).`);
}

// ── SWITCH HUB ─────────────────────────────────────────────────────────────────
function switchHub() {
  hubManuallySelected = true;
  const eff = document.getElementById('hubEffingham');
  const spr = document.getElementById('hubSpringfield');
  if (!eff || !spr) return;

  const currentlySpringfield = spr.checked;
  console.log('NEMT: switchHub called, currently Springfield:', currentlySpringfield);

  if (currentlySpringfield) {
    spr.checked = false;
    eff.checked = true;
  } else {
    eff.checked = false;
    spr.checked = true;
  }

  console.log('NEMT: hub switched to:', getHub());

  const btn = document.getElementById('switchHubBtn');
  if (btn) {
    const otherHub = getHub() === 'Springfield' ? 'Effingham' : 'Springfield';
    btn.textContent = `⇄ Switch to ${otherHub}`;
  }

  render();
}

// ── MULTI-LOAD FLAGS ───────────────────────────────────────────────────────────
function flagMultiLoads() {
  const dropoffGroups = {};
  trips.forEach((t, i) => {
    const key = (t.dropoff || '').toLowerCase().slice(0, 20);
    if (!dropoffGroups[key]) dropoffGroups[key] = [];
    dropoffGroups[key].push(i);
  });
  Object.values(dropoffGroups).forEach(group => {
    if (group.length < 2) return;
    group.forEach(idx => {
      const card = document.querySelector(`[data-trip-idx="${idx}"]`);
      if (!card) return;
      card.style.borderLeft = '4px solid #f39c12';
      const badge = document.createElement('span');
      badge.textContent = `🚌 MULTI-LOAD (${group.length} riders)`;
      badge.style.cssText = 'background:#f39c12;color:white;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:bold;margin-right:8px;';
      card.querySelector('.trip-header')?.prepend(badge);
    });
  });
}

// ── OPTIMIZE ORDER ─────────────────────────────────────────────────────────────
function optimizeOrder() {
  if (trips.length < 2) { alert('Add at least 2 trips to optimize.'); return; }
  const before = trips.map(t => t.time).join(',');
  trips.sort((a, b) => {
    const tA = parseTime(a.time), tB = parseTime(b.time);
    if (tA === null && tB === null) return 0;
    if (tA === null) return 1;
    if (tB === null) return -1;
    return tA - tB;
  });
  const after = trips.map(t => t.time).join(',');
  render();
  const btn = document.getElementById('optimizeBtn');
  if (btn) {
    btn.textContent = before === after ? '✓ Already Optimal' : '✓ Optimized!';
    btn.style.background = '#27ae60';
    setTimeout(() => { btn.textContent = '⚡ Optimize Order'; btn.style.background = '#8e44ad'; }, 2000);
  }
}

// ── TIME CONFLICT CHECK ────────────────────────────────────────────────────────
function checkTimeConflicts() {
  const warnings = [];
  for (let i = 0; i < trips.length - 1; i++) {
    const curr = trips[i], next = trips[i + 1];
    const currAppt = parseTime(curr.time), nextAppt = parseTime(next.time);
    if (currAppt === null || nextAppt === null) continue;
    const currFinish = currAppt + (curr.isClinic ? 5 : 60) + ((parseFloat(curr.miles) || 0) / 50 * 60);
    const nextPickup = nextAppt - ((parseFloat(next.miles) || 0) / 50 * 60);
    if (currFinish > nextPickup + 30) {
      warnings.push(`⚠️ Trip ${i+1} → Trip ${i+2}: Potential time conflict — Trip ${i+1} may not finish before Trip ${i+2} pickup`);
    }
  }
  const el = document.getElementById('timeWarnings');
  if (el) el.innerHTML = warnings.map(w => `<div style="color:#c0392b;font-size:12px;padding:4px 0;">${w}</div>`).join('');
}

// ── GOOGLE MAPS EXPORT ─────────────────────────────────────────────────────────
function openInGoogleMaps() {
  if (!trips.length) { alert('No trips to map.'); return; }
  const originAddr = getHub() === 'Springfield'
    ? '506 S 6th St, Springfield, IL 62701'
    : '506 South St, Effingham, IL 62401';

  // Group trips by shared dropoff, preserving insertion order
  const dropoffGroups = {};
  const groupOrder = [];
  trips.forEach(t => {
    const key = (t.dropoff || '').toLowerCase().slice(0, 25);
    if (!dropoffGroups[key]) {
      dropoffGroups[key] = { dropoff: t.dropoff, pickups: [] };
      groupOrder.push(key);
    }
    dropoffGroups[key].pickups.push(t.pickup);
  });

  // Full round trip: outbound pickups → dropoff → return pickups (reverse)
  const waypoints = [];
  groupOrder.forEach(key => {
    const group = dropoffGroups[key];
    group.pickups.forEach(p => waypoints.push(encodeURIComponent(p)));
    waypoints.push(encodeURIComponent(group.dropoff));
    [...group.pickups].reverse().forEach(p => waypoints.push(encodeURIComponent(p)));
  });

  const origin = encodeURIComponent(originAddr);
  const url = `https://www.google.com/maps/dir/?api=1&origin=${origin}&destination=${origin}&waypoints=${waypoints.join('|')}&travelmode=driving`;
  window.open(url, '_blank');
}

// ── EVENT WIRING ───────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function() {
  document.getElementById('addTripBtn')?.addEventListener('click', addTrip);
  document.getElementById('clearRouteBtn')?.addEventListener('click', clearRoute);
  document.getElementById('switchHubBtn')?.addEventListener('click', switchHub);
  document.getElementById('optimizeBtn')?.addEventListener('click', optimizeOrder);
  document.getElementById('mapsBtn')?.addEventListener('click', openInGoogleMaps);
  document.getElementById('copyBtn')?.addEventListener('click', copyRouteSummary);
  document.getElementById('saveBtn')?.addEventListener('click', saveRoute);
  document.getElementById('loadBtn')?.addEventListener('click', loadRoute);

  // Delegated listener for dynamically generated Remove buttons
  document.getElementById('trips-area')?.addEventListener('click', e => {
    const btn = e.target.closest('.btn-remove');
    if (btn) {
      const idx = parseInt(btn.dataset.idx);
      if (!isNaN(idx)) removeTrip(idx);
    }
  });

  // Enter key in any input submits the form
  document.addEventListener('keydown', e => {
    if (e.key === 'Enter' && e.target.tagName === 'INPUT') addTrip();
  });

  console.log('NEMT: All button bindings attached');
  console.log('switchHubBtn:', document.getElementById('switchHubBtn'));

  render();
});
