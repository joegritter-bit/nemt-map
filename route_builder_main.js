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

const TRIP_COST_RB = {
  MPG: 15.5, GAS_PRICE: 4.14, DRIVER_RATE: 19.00,
  AVG_SPEED_MPH: 45, WEAR_PER_MILE: 0.14
};
const EFFINGHAM_DEADHEAD_MILES_RB = {
  'springfield': 96, 'chatham': 91, 'decatur': 58, 'bloomington': 117,
  'normal': 117, 'champaign': 82, 'urbana': 84, 'danville': 115,
  'rantoul': 90, 'clinton': 80, 'monticello': 70, 'mahomet': 78,
  'savoy': 83, 'tuscola': 38, 'arcola': 34, 'mattoon': 38,
  'charleston': 44, 'sullivan': 20, 'shelbyville': 30, 'taylorville': 58,
  'pana': 44, 'assumption': 38, 'morrisonville': 62, 'lincoln': 80,
  'mt pulaski': 72, 'atlanta': 85, 'gibson city': 72, 'paxton': 88,
  'pontiac': 105, 'dwight': 130, 'streator': 125, 'ottawa': 145,
  'lasalle': 148, 'peru': 148, 'kankakee': 160,
  'robinson': 62, 'lawrenceville': 82, 'olney': 42, 'flora': 28,
  'fairfield': 50, 'carmi': 70, 'albion': 55, 'mt carmel': 75,
  'newton': 20, 'salem': 40, 'vandalia': 28, 'centralia': 55,
  'benton': 72, 'west frankfort': 80, 'carbondale': 100, 'anna': 115,
  'harrisburg': 85, 'havana': 120, 'beardstown': 140,
  'effingham': 0, 'altamont': 14, 'teutopolis': 8, 'dieterich': 10,
  'montrose': 12, 'watson': 15, 'mason': 18, 'sigel': 10,
};
const SPRINGFIELD_DEADHEAD_MILES_RB = {
  'springfield': 0, 'chatham': 9, 'decatur': 38, 'bloomington': 60,
  'normal': 60, 'champaign': 90, 'urbana': 92, 'danville': 120,
  'rantoul': 100, 'clinton': 25, 'monticello': 60, 'mahomet': 85,
  'taylorville': 28, 'pana': 48, 'assumption': 40, 'morrisonville': 20,
  'lincoln': 35, 'mt pulaski': 25, 'atlanta': 25, 'havana': 40,
  'beardstown': 50, 'effingham': 96, 'mattoon': 95, 'charleston': 100,
  'robinson': 115, 'lawrenceville': 140, 'vandalia': 68, 'salem': 82,
  'centralia': 100, 'carbondale': 155, 'anna': 165, 'benton': 120,
};

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

  // Metro East / SW Illinois (Madison, Jersey,
  // Macoupin, Montgomery, Bond counties)
  'alton':          { lat: 38.8906, lng: -90.1843 },
  'jerseyville':    { lat: 39.1203, lng: -90.3287 },
  'grafton':        { lat: 38.9678, lng: -90.4326 },
  'brighton':       { lat: 39.0367, lng: -90.1418 },
  'bethalto':       { lat: 38.9101, lng: -90.0418 },
  'bunker hill':    { lat: 39.0450, lng: -89.9473 },
  'sorento':        { lat: 39.0456, lng: -89.5756 },
  'edwardsville':   { lat: 38.8117, lng: -89.9523 },
  'granite city':   { lat: 38.7020, lng: -90.1487 },
  'collinsville':   { lat: 38.6703, lng: -89.9845 },
  'maryville':      { lat: 38.7231, lng: -89.9573 },
  'troy':           { lat: 38.7303, lng: -89.8851 },
  'highland':       { lat: 38.7442, lng: -89.6773 },
  'greenville':     { lat: 38.8928, lng: -89.4134 },
  'litchfield':     { lat: 39.1753, lng: -89.6540 },
  'gillespie':      { lat: 39.1320, lng: -89.8201 },
  'carlinville':    { lat: 39.2789, lng: -89.8823 },
  'staunton':       { lat: 39.0128, lng: -89.7923 },
  'worden':         { lat: 38.9342, lng: -89.8412 },
  'shipman':        { lat: 39.0703, lng: -90.0501 },
  'white hall':     { lat: 39.4328, lng: -90.4023 },
  'hardin':         { lat: 39.1567, lng: -90.6223 },
  'kampsville':     { lat: 39.3023, lng: -90.6134 },
  'brussels':       { lat: 38.9456, lng: -90.5823 },

  // Southern Illinois additions
  'du quoin':       { lat: 37.9995, lng: -89.2367 },
  'christopher':    { lat: 37.9748, lng: -89.0556 },
  'herrin':         { lat: 37.7970, lng: -89.0267 },
  'carterville':    { lat: 37.7609, lng: -89.0820 },
  'freeburg':       { lat: 38.4317, lng: -89.9134 },
  'belleville':     { lat: 38.5201, lng: -89.9840 },
  'ofallon':        { lat: 38.5934, lng: -89.9109 },
  'mascoutah':      { lat: 38.4887, lng: -89.7923 },
  'lebanon':        { lat: 38.6048, lng: -89.8048 },
  'breese':         { lat: 38.6112, lng: -89.5273 },
  'okawville':      { lat: 38.4317, lng: -89.5484 },
  'nashville':      { lat: 38.3442, lng: -89.3801 },
  'mt vernon':      { lat: 38.3173, lng: -88.9031 },
  'moline':         { lat: 41.5067, lng: -90.5151 },
  'rock island':    { lat: 41.5098, lng: -90.5787 },
  'morris':         { lat: 41.3578, lng: -88.4214 },
  'joliet':         { lat: 41.5250, lng: -88.0817 },
  'bourbonnais':    { lat: 41.1553, lng: -87.8889 },
  'manteno':        { lat: 41.2509, lng: -87.8306 },
  'momence':        { lat: 41.1592, lng: -87.6647 },
  'gifford':        { lat: 40.3072, lng: -88.0183 },
  'minonk':         { lat: 40.9003, lng: -89.0337 },
  'topeka':         { lat: 40.3350, lng: -89.9324 },
  'bethany':        { lat: 39.6453, lng: -88.7362 },
};

// In-memory distance cache for route builder session
const distanceCache = new Map();

async function getDistanceMiles(fromAddr, toAddr) {
  if (!fromAddr || !toAddr) return null;

  const key = `${fromAddr}||${toAddr}`;
  if (distanceCache.has(key)) {
    return distanceCache.get(key);
  }

  return new Promise((resolve) => {
    try {
      chrome.runtime.sendMessage({
        type: 'GET_DEADHEAD_MILES',
        origin: fromAddr,
        destination: toAddr
      }, (response) => {
        if (chrome.runtime.lastError) {
          console.warn('Route builder geocode error:', chrome.runtime.lastError);
          resolve(null);
          return;
        }
        const miles = response?.miles ?? null;
        if (miles !== null) {
          console.log('Route builder geocode:', fromAddr, '→', toAddr, '=', miles, 'mi');
          distanceCache.set(key, miles);
        }
        resolve(miles);
      });
    } catch(e) { resolve(null); }
  });
}

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
let currentLoad = 1;   // Feature 3: tracks which load the next trip belongs to
let loadLabels  = {};  // {loadNum → custom label} — set by loader for named batches
window.nemt_setLoadLabel   = (num, label) => { loadLabels[num] = label; };
window.nemt_getCurrentLoad = () => currentLoad;
window.nemt_hasTrips       = () => trips.length > 0;

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

function calcTripDuration(miles, isClinic, avgSpeed = AVG_MPH) {
  const driveHrs = (parseFloat(miles) || 0) / avgSpeed;
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

function calcDeadheadHours(address, avgSpeed = AVG_MPH) {
  const hub  = getHubCoords();
  const city = getPickupCityCoords(address);
  if (city) {
    return estimateDistanceMiles(hub.lat, hub.lng, city.lat, city.lng) / avgSpeed;
  }
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

function getInterStopMiles(fromAddr, toAddr) {
  const from = getPickupCityCoords(fromAddr);
  const to   = getPickupCityCoords(toAddr);
  if (!from || !to) return 30;
  return Math.round(estimateDistanceMiles(from.lat, from.lng, to.lat, to.lng) * 1.3);
}

function estimateTotalHours(avgSpeed = AVG_MPH) {
  if (!trips.length) return 0;

  const deadheadOutMiles = trips[0].deadheadMiles !== undefined
    ? trips[0].deadheadMiles
    : getDeadheadMilesRB(trips[0].pickup);
  const hubToFirst = deadheadOutMiles / avgSpeed;

  const lastTrip = trips[trips.length - 1];
  const deadheadBackMiles = lastTrip.deadheadMiles !== undefined
    ? lastTrip.deadheadMiles
    : getDeadheadMilesRB(lastTrip.pickup);
  const lastToHub = deadheadBackMiles / avgSpeed;

  let total = hubToFirst + lastToHub;
  trips.forEach((t, i) => {
    total += calcTripDuration(t.miles, t.isClinic, avgSpeed);
    if (i < trips.length - 1) {
      const interMiles = t.interStopToNext !== undefined
        ? t.interStopToNext
        : getInterStopMiles(t.dropoff, trips[i + 1].pickup);
      total += interMiles / avgSpeed;
    }
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
  if (hubManuallySelected) return;
  if (trips.length > 0) return;
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

// ── FEATURE 1: ADDRESS GEOCODING IN FORM ──────────────────────────────────────

// Called from inline card editing too (tripIdx ≥ 0) or form (tripIdx = -1)
function geocodeAddress(address, onSuccess, onError) {
  if (!address || address.trim().length < 5) { if (onError) onError(); return; }
  if (typeof chrome === 'undefined' || !chrome.runtime) { if (onError) onError(); return; }
  chrome.runtime.sendMessage({ type: 'GEOCODE_ADDRESS', address: address.trim() }, (response) => {
    if (chrome.runtime.lastError || !response || !response.lat) {
      if (onError) onError(response?.error);
      return;
    }
    if (onSuccess) onSuccess(response);
  });
}

function setupAddressGeocode(fieldId, latId, lngId, statusId, sublabelId) {
  const field = document.getElementById(fieldId);
  if (!field) return;

  // Clear geo markers when user edits the field
  field.addEventListener('input', () => {
    field.dataset.geocodedValue = '';
    const s = document.getElementById(statusId);
    const sub = document.getElementById(sublabelId);
    const latEl = document.getElementById(latId);
    const lngEl = document.getElementById(lngId);
    if (s) { s.textContent = ''; s.title = ''; }
    if (sub) sub.textContent = '';
    if (latEl) latEl.value = '';
    if (lngEl) lngEl.value = '';
  });

  field.addEventListener('blur', () => {
    const addr = field.value.trim();
    if (!addr) return;
    // Skip if this exact value was already geocoded (incl. pre-populated from marketplace)
    if (field.dataset.geocodedValue === addr) return;

    const statusEl  = document.getElementById(statusId);
    const sublabel  = document.getElementById(sublabelId);
    const latEl     = document.getElementById(latId);
    const lngEl     = document.getElementById(lngId);
    if (statusEl) statusEl.textContent = '🔄';

    geocodeAddress(addr, (res) => {
      field.dataset.geocodedValue = addr;
      if (latEl) latEl.value = res.lat;
      if (lngEl) lngEl.value = res.lng;
      if (statusEl) { statusEl.textContent = '✅'; statusEl.title = res.formatted; }
      if (sublabel) sublabel.textContent = res.cityState;
    }, (err) => {
      if (statusEl) { statusEl.textContent = '❌'; statusEl.title = err || 'Geocoding failed'; }
      if (sublabel) sublabel.textContent = '';
    });
  });
}

// Pre-populate lat/lng hidden fields when a trip is loaded from the marketplace
// (currently marketplace doesn't pass coords, but this future-proofs it)
function markFieldGeocoded(fieldId, latId, lngId, statusId, sublabelId, lat, lng, formatted, cityState) {
  const field  = document.getElementById(fieldId);
  const latEl  = document.getElementById(latId);
  const lngEl  = document.getElementById(lngId);
  const status = document.getElementById(statusId);
  const sub    = document.getElementById(sublabelId);
  if (latEl)  latEl.value  = lat;
  if (lngEl)  lngEl.value  = lng;
  if (field)  field.dataset.geocodedValue = field.value;
  if (status) { status.textContent = '✅'; status.title = formatted || ''; }
  if (sub)    sub.textContent = cityState || '';
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

  // Capture hidden lat/lng if geocoded in form (Feature 1)
  const pickupLat  = parseFloat(document.getElementById('pickup_lat')?.value)  || null;
  const pickupLng  = parseFloat(document.getElementById('pickup_lng')?.value)  || null;
  const dropoffLat = parseFloat(document.getElementById('dropoff_lat')?.value) || null;
  const dropoffLng = parseFloat(document.getElementById('dropoff_lng')?.value) || null;

  const trip = {
    pickup, dropoff, miles, time, riders, county, baseRate, payout,
    isClinic, duration_hrs, pickup_time_calc, hub: getHub(),
    loadNum: currentLoad,
    pickupLat, pickupLng, dropoffLat, dropoffLng
  };
  trips.push(trip);

  // Geocode deadhead (hub → pickup)
  const hubAddr = trip.hub === 'Springfield'
    ? '1 North Old State Capitol Plaza, Springfield, IL 62701'
    : '506 South St, Effingham, IL 62401';
  getDistanceMiles(hubAddr, trip.pickup).then(geoMiles => {
    if (geoMiles !== null) { trip.deadheadMiles = geoMiles; render(); }
  });

  // Geocode inter-stop from previous trip's dropoff → this pickup
  if (trips.length > 1) {
    const prevTrip = trips[trips.length - 2];
    getDistanceMiles(prevTrip.dropoff, trip.pickup).then(geoMiles => {
      if (geoMiles !== null) { prevTrip.interStopToNext = geoMiles; render(); }
    });
  }

  // Reset form
  document.getElementById('pickup').value  = '';
  document.getElementById('dropoff').value = '';
  document.getElementById('miles').value   = '';
  document.getElementById('riders').value  = '1';
  // Clear geocode state on form fields
  ['pickup','dropoff'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.dataset.geocodedValue = '';
  });
  ['pickup_lat','pickup_lng','dropoff_lat','dropoff_lng'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = '';
  });
  ['pickup-geo-status','dropoff-geo-status'].forEach(id => {
    const el = document.getElementById(id);
    if (el) { el.textContent = ''; el.title = ''; }
  });
  ['pickup-geo-sublabel','dropoff-geo-sublabel'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.textContent = '';
  });
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
  currentLoad = 1;
  hubManuallySelected = false;
  render();
}

// ── FEATURE 3: MULTI-LOAD ─────────────────────────────────────────────────────
function newLoad() {
  if (!trips.length) {
    // No trips yet — still increment so first trip lands in Load 2 if user insists,
    // but warn them it's unusual.
    currentLoad++;
    const btn = document.getElementById('newLoadBtn');
    if (btn) {
      btn.textContent = `✓ Load ${currentLoad}`;
      setTimeout(() => { btn.textContent = '＋ New Load'; }, 1500);
    }
    return;
  }
  currentLoad++;
  render();
  const btn = document.getElementById('newLoadBtn');
  if (btn) {
    btn.textContent = `✓ Load ${currentLoad} started`;
    setTimeout(() => { btn.textContent = '＋ New Load'; }, 1500);
  }
}

function renderLoadBreakdown() {
  const el = document.getElementById('load-breakdown');
  if (!el) return;

  // Gather per-load stats
  const loads = {};
  trips.forEach(t => {
    const ln = t.loadNum || 1;
    if (!loads[ln]) loads[ln] = { trips: 0, miles: 0, rev: 0, hrs: 0 };
    loads[ln].trips++;
    loads[ln].miles += parseFloat(t.miles) || 0;
    loads[ln].rev   += t.payout || 0;
    loads[ln].hrs   += t.duration_hrs || 0;
  });

  const loadNums = Object.keys(loads).map(Number).sort((a,b) => a - b);

  // Only show breakdown if more than one load is in use
  if (loadNums.length <= 1) { el.innerHTML = ''; return; }

  let html = '';
  let totalTrips = 0, totalMiles = 0, totalRev = 0, totalHrs = 0;

  loadNums.forEach(ln => {
    const d = loads[ln];
    const revHr = d.hrs > 0 ? d.rev / d.hrs : 0;
    totalTrips += d.trips; totalMiles += d.miles;
    totalRev   += d.rev;   totalHrs   += d.hrs;
    html += `<div class="load-row">
      <span class="load-label" style="color:#b39ddb;">Load ${ln}</span>
      <span>${d.trips} trip${d.trips !== 1 ? 's' : ''}</span>
      <span>·</span>
      <span>${d.miles.toFixed(1)} mi</span>
      <span>·</span>
      <span style="color:#7dffb3;">$${d.rev.toFixed(2)}</span>
      <span>·</span>
      <span>$${revHr.toFixed(0)}/hr</span>
    </div>`;
  });

  const totalRevHr = totalHrs > 0 ? totalRev / totalHrs : 0;
  html += `<div class="load-row total-row">
    <span class="load-label">Total</span>
    <span>${totalTrips} trip${totalTrips !== 1 ? 's' : ''}</span>
    <span>·</span>
    <span>${totalMiles.toFixed(1)} mi</span>
    <span>·</span>
    <span>$${totalRev.toFixed(2)}</span>
    <span>·</span>
    <span>$${totalRevHr.toFixed(0)}/hr</span>
  </div>`;

  el.innerHTML = html;
}

// ── ROUTE COST ─────────────────────────────────────────────────────────────────
function getDeadheadMilesRB(addr) {
  if (!addr) return 50;
  const lower = addr.toLowerCase();
  const table = getHub().toLowerCase() === 'springfield'
    ? SPRINGFIELD_DEADHEAD_MILES_RB
    : EFFINGHAM_DEADHEAD_MILES_RB;
  for (const [city, miles] of Object.entries(table)) {
    if (lower.includes(city)) return miles;
  }
  return 50;
}

function calculateRouteCost(trips) {
  if (!trips.length) return null;

  const firstPickup  = trips[0]?.pickup || '';
  const lastDropoff  = trips[trips.length - 1]?.dropoff || '';

  const deadheadOut = trips[0].deadheadMiles !== undefined
    ? trips[0].deadheadMiles
    : getDeadheadMilesRB(firstPickup);

  const lastTrip = trips[trips.length - 1];
  const deadheadBack = lastTrip.deadheadMiles !== undefined
    ? lastTrip.deadheadMiles
    : getDeadheadMilesRB(lastDropoff);

  const riderMiles = trips.reduce(
    (s, t) => s + (parseFloat(t.miles) || 0), 0) * 2;

  let interStopMiles = 0;
  for (let i = 0; i < trips.length - 1; i++) {
    if (trips[i].interStopToNext !== undefined) {
      interStopMiles += trips[i].interStopToNext;
    } else {
      interStopMiles += getInterStopMiles(trips[i].dropoff, trips[i + 1].pickup);
    }
  }

  const totalMiles = deadheadOut + riderMiles + interStopMiles + deadheadBack;
  const fuel = (totalMiles / TRIP_COST_RB.MPG) * TRIP_COST_RB.GAS_PRICE;
  const avgSpeed = totalMiles > 60 ? 55 : 45;
  const driveHours = totalMiles / avgSpeed;
  const waitHours = trips.reduce((s, t) => s + (parseFloat(t.duration_hrs) || STANDARD_WAIT_HRS), 0);
  const labor = (driveHours + waitHours) * TRIP_COST_RB.DRIVER_RATE;
  const wear = totalMiles * TRIP_COST_RB.WEAR_PER_MILE;

  const totalCost = fuel + labor + wear;
  const multiload = trips.length > 1;
  return { totalCost, totalMiles, deadheadOut, deadheadBack, riderMiles, interStopMiles, multiload };
}

// ── FEATURE 2: INLINE EDITING ─────────────────────────────────────────────────
function startInlineEdit(span) {
  if (span.querySelector('input')) return; // already editing

  const tripIdx = parseInt(span.dataset.tripIdx);
  const field   = span.dataset.field;
  const type    = span.dataset.type || 'text';
  const trip    = trips[tripIdx];
  if (!trip) return;

  const originalValue   = trip[field];
  const displayOriginal = type === 'time' ? (formatTime(originalValue) || '--') : String(originalValue);
  let _done = false;

  const input = document.createElement('input');
  input.type  = type;
  input.value = type === 'number' ? (parseFloat(originalValue) || 0) : (originalValue || '');
  if (type === 'number') { input.step = '0.1'; input.min = '0'; input.style.width = '70px'; }
  else if (type === 'time') { input.style.width = '110px'; }
  else { input.style.width = '100%'; }

  span.textContent = '';
  span.appendChild(input);
  input.focus();
  if (input.select) input.select();

  function confirm() {
    if (_done) return;
    _done = true;

    const rawVal = input.value;
    const newVal = type === 'number' ? (parseFloat(rawVal) || 0) : rawVal.trim();
    trip[field]  = newVal;

    // Recalculate derived fields when key trip properties change
    if (field === 'miles' || field === 'time' || field === 'pickup' || field === 'dropoff') {
      const county    = detectCounty(trip.pickup);
      trip.county     = county;
      trip.baseRate   = COUNTY_BASE_RATES[county] || STANDARD_BASE_RATE;
      trip.payout     = calcPayout(trip.miles, trip.time, county, trip.riders);
      trip.isClinic   = detectClinic(trip.dropoff);
      trip.duration_hrs = calcTripDuration(trip.miles, trip.isClinic);
    }

    // Re-geocode inter-stop distances when addresses change
    if (field === 'pickup' && newVal) {
      trip.deadheadMiles = undefined;
      const hubAddr = trip.hub === 'Springfield'
        ? '1 North Old State Capitol Plaza, Springfield, IL 62701'
        : '506 South St, Effingham, IL 62401';
      getDistanceMiles(hubAddr, trip.pickup).then(m => {
        if (m !== null) { trip.deadheadMiles = m; render(); }
      });
      if (tripIdx > 0) {
        const prev = trips[tripIdx - 1];
        prev.interStopToNext = undefined;
        getDistanceMiles(prev.dropoff, trip.pickup).then(m => {
          if (m !== null) { prev.interStopToNext = m; render(); }
        });
      }
    }
    if (field === 'dropoff' && newVal && tripIdx < trips.length - 1) {
      trips[tripIdx].interStopToNext = undefined;
      getDistanceMiles(trip.dropoff, trips[tripIdx + 1].pickup).then(m => {
        if (m !== null) { trips[tripIdx].interStopToNext = m; render(); }
      });
    }

    render();
  }

  function cancel() {
    if (_done) return;
    _done = true;
    span.textContent = displayOriginal;
  }

  input.addEventListener('keydown', e => {
    if (e.key === 'Enter' || e.key === 'Tab') { e.preventDefault(); confirm(); }
    if (e.key === 'Escape') { e.preventDefault(); cancel(); }
  });

  // Blur confirms unless already resolved (by keydown or span disconnected by render())
  input.addEventListener('blur', () => {
    setTimeout(() => {
      if (!_done) confirm();
    }, 60);
  });
}

// ── RENDER ─────────────────────────────────────────────────────────────────────
function render() {
  const totalRev  = trips.reduce((s, t) => s + t.payout, 0);
  window._deadheadEstimated = false;
  const estMiles  = trips.reduce((s, t) => s + (parseFloat(t.miles) || 0) * 2, 0);
  const avgSpeed  = estMiles > 60 ? 55 : 45;
  const totalHrs  = estimateTotalHours(avgSpeed);
  const deadheadEstimated = window._deadheadEstimated;
  const revHr     = totalHrs > 0 ? totalRev / totalHrs : 0;
  const remaining = Math.max(0, MAX_SHIFT_HOURS - totalHrs);

  // Totals bar
  document.getElementById('stat-revenue').textContent = `$${totalRev.toFixed(2)}`;

  const hoursEl = document.getElementById('stat-hours');
  hoursEl.textContent = `${totalHrs.toFixed(1)}h`;
  hoursEl.className = `stat-value ${totalHrs > MAX_SHIFT_HOURS ? 'warn' : 'neutral'}`;
  const dhEl = document.getElementById('deadheadMiles');
  if (dhEl) {
    const dh = getDeadheadMiles();
    dhEl.textContent = deadheadEstimated ? '⚠️ est.' : (dh !== null ? dh : '?');
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

  // Cost / margin
  const costResult    = trips.length ? calculateRouteCost(trips) : null;
  const costEl        = document.getElementById('stat-route-cost');
  const marginEl      = document.getElementById('stat-route-margin');
  const marginPctEl   = document.getElementById('stat-route-margin-pct');
  const totalMilesEl  = document.getElementById('stat-total-miles');
  const multiloadNoteEl = document.getElementById('multiload-note');
  if (costEl) costEl.textContent = costResult ? `$${costResult.totalCost.toFixed(2)}` : '—';
  if (totalMilesEl) totalMilesEl.textContent = costResult ? `${Math.round(costResult.totalMiles)} mi` : '—';

  const geoCount = trips.filter(t => t.deadheadMiles !== undefined).length;
  const allGeo = trips.length > 0 && geoCount === trips.length &&
    trips.every((t, i) => i === trips.length - 1 || t.interStopToNext !== undefined);
  const geoIndicator = document.getElementById('geoStatusIndicator');
  if (geoIndicator) {
    geoIndicator.textContent = trips.length === 0 ? '📍 Est.' : allGeo ? '📍 Geocoded' : '⏳ Est...';
    geoIndicator.style.color = allGeo ? '#27ae60' : '#aaa';
  }

  if (marginEl && marginPctEl) {
    if (costResult) {
      const margin = totalRev - costResult.totalCost;
      const pct    = totalRev > 0 ? (margin / totalRev * 100) : 0;
      marginEl.textContent = `${margin >= 0 ? '+' : ''}$${margin.toFixed(2)}`;
      marginEl.className = `stat-value ${margin >= 40 ? 'good' : margin >= 0 ? 'neutral' : 'warn'}`;
      marginPctEl.textContent = `${pct.toFixed(0)}% margin`;
    } else {
      marginEl.textContent = '—';
      marginEl.className = 'stat-value';
      marginPctEl.textContent = '';
    }
  }
  if (multiloadNoteEl) {
    if (costResult && costResult.multiload && trips.length >= 2) {
      const savedDeadhead = costResult.deadheadOut + costResult.deadheadBack;
      const savedCost = (savedDeadhead * (trips.length - 1) / TRIP_COST_RB.MPG * TRIP_COST_RB.GAS_PRICE)
        + (savedDeadhead * (trips.length - 1) / TRIP_COST_RB.AVG_SPEED_MPH * TRIP_COST_RB.DRIVER_RATE)
        + (savedDeadhead * (trips.length - 1) * TRIP_COST_RB.WEAR_PER_MILE);
      multiloadNoteEl.style.display = 'block';
      multiloadNoteEl.textContent = `⚡ Multi-load: ${trips.length} riders share deadhead (${Math.round(savedDeadhead)} mi) — est. $${savedCost.toFixed(2)} saved vs. separate runs`;
    } else {
      multiloadNoteEl.style.display = 'none';
    }
  }

  // Per-load breakdown (Feature 3)
  renderLoadBreakdown();

  // Warnings
  const warnDiv = document.getElementById('warnings');
  warnDiv.innerHTML = '';
  if (trips.length && totalHrs > MAX_SHIFT_HOURS)
    warnDiv.innerHTML += `<div class="warning-banner">⚠️ Shift exceeds ${MAX_SHIFT_HOURS}h limit — estimated ${totalHrs.toFixed(1)}h</div>`;
  if (trips.length && revHr < MIN_REV_PER_HOUR)
    warnDiv.innerHTML += `<div class="warning-banner">⚠️ Below minimum profit threshold ($${MIN_REV_PER_HOUR}/hr) — currently $${revHr.toFixed(2)}/hr</div>`;

  // Trip cards + load dividers (Features 2 & 3)
  const area = document.getElementById('trips-area');
  if (!trips.length) {
    area.innerHTML = '<div class="empty-state">No trips yet.<br>Fill in the form and click <b>Add Trip</b>.</div>';
  } else {
    let html = '';
    let lastLoadNum = null;

    trips.forEach((t, i) => {
      const loadNum = t.loadNum || 1;

      // Insert load divider when load changes (Feature 3)
      if (lastLoadNum !== null && loadNum !== lastLoadNum) {
        const divText = loadLabels[loadNum] || `Load ${loadNum}`;
        html += `<div class="load-divider">── ${divText} ──</div>`;
      }
      lastLoadNum = loadNum;

      // Load badge in top-right of card (Feature 3)
      const loadBadge = `<span class="load-badge">L${loadNum}</span>`;

      // Editable field spans (Feature 2)
      const editPickup  = `<span class="editable-field" data-editable data-trip-idx="${i}" data-field="pickup"  data-type="text"   title="Click to edit">${t.pickup}</span>`;
      const editDropoff = `<span class="editable-field" data-editable data-trip-idx="${i}" data-field="dropoff" data-type="text"   title="Click to edit">${t.dropoff}</span>`;
      const editMiles   = `<span class="editable-field" data-editable data-trip-idx="${i}" data-field="miles"   data-type="number" title="Click to edit">${t.miles}</span>`;
      const editTime    = `<span class="editable-field" data-editable data-trip-idx="${i}" data-field="time"    data-type="time"   title="Click to edit">${t.time || '--'}</span>`;

      html += `
        <div class="trip-card${t.isClinic ? ' clinic' : ''}" data-trip-idx="${i}">
          ${loadBadge}
          <div class="trip-header">
            <div>
              <div class="trip-title">Trip ${i+1} &nbsp;·&nbsp; ${getHub()}</div>
              <div class="trip-subtitle" style="color:#2c3e50;font-size:12px;">${editPickup}</div>
              <div class="trip-subtitle" style="color:#888;font-size:11px;margin-top:1px;">→ ${editDropoff}</div>
            </div>
            <button class="btn-remove" data-idx="${i}">Remove</button>
          </div>
          <div class="trip-details">
            <b>County:</b> ${t.county || `<span style="color:#e67e22">Unknown (using $${STANDARD_BASE_RATE.toFixed(2)})</span>`}<br>
            <b>Base Rate:</b> $${t.baseRate.toFixed(2)} &nbsp;&nbsp;
            <b>Miles:</b> ${editMiles} &nbsp;&nbsp;
            <b>Riders:</b> ${t.riders}
            ${t.isClinic ? '<br><span class="clinic-badge">💊 CLINIC</span>' : ''}
            <div style="font-size:11px; color:#666; margin-top:4px;">
              Appt: <b>${editTime}</b> &nbsp;|&nbsp;
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
        </div>`;
    });

    area.innerHTML = html;
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
  const estMiles = trips.reduce((s, t) => s + (parseFloat(t.miles) || 0) * 2, 0);
  const avgSpeed = estMiles > 60 ? 55 : 45;
  return estimateTotalHours(avgSpeed);
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

  let lastLoad = null;
  trips.forEach((t, i) => {
    const ln = t.loadNum || 1;
    if (lastLoad !== null && ln !== lastLoad) {
      msg += `\n── Load ${ln} ──\n`;
    }
    lastLoad = ln;
    msg += `\nTrip ${i+1} [L${ln}]`;
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

  navigator.clipboard.writeText(msg).then(() => {
    const btn = document.getElementById('copyBtn');
    if (btn) { btn.textContent = '✓ Copied!'; setTimeout(() => btn.textContent = '📋 Copy Route Summary', 2000); }
  }).catch(() => prompt('Copy this text:', msg));
}

function saveRoute() {
  if (!trips.length) { alert('No trips to save.'); return; }
  localStorage.setItem('nemt_saved_route', JSON.stringify({ trips, hub: getHub(), currentLoad }));
  alert('Route saved to browser storage.');
}

function loadRoute() {
  const raw = localStorage.getItem('nemt_saved_route');
  if (!raw) { alert('No saved route found.'); return; }
  const data = JSON.parse(raw);
  trips = data.trips || [];
  currentLoad = data.currentLoad || 1;
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
  if (currentlySpringfield) { spr.checked = false; eff.checked = true; }
  else { eff.checked = false; spr.checked = true; }

  const btn = document.getElementById('switchHubBtn');
  if (btn) {
    const otherHub = getHub() === 'Springfield' ? 'Effingham' : 'Springfield';
    btn.textContent = `⇄ Switch to ${otherHub}`;
  }
  render();
}

// ── MULTI-LOAD FLAGS (shared dropoff detection) ────────────────────────────────
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
  if (trips.length < 2) {
    alert('Add at least 2 trips to optimize.');
    return;
  }

  const hub = getHub();
  const hubCoords = HUB_COORDS[hub] || HUB_COORDS['Effingham'];

  // Get coordinates for a trip pickup —
  // use geocoded lat/lng if available,
  // fall back to city table, then hub
  function getTripCoords(trip) {
    if (trip.pickupLat && trip.pickupLng) {
      return { lat: trip.pickupLat, lng: trip.pickupLng };
    }
    const cityCoords = getPickupCityCoords(trip.pickup || '');
    if (cityCoords) return cityCoords;
    return hubCoords; // last resort
  }

  // Get dropoff coords
  function getDropoffCoords(trip) {
    if (trip.dropoffLat && trip.dropoffLng) {
      return { lat: trip.dropoffLat, lng: trip.dropoffLng };
    }
    const cityCoords = getPickupCityCoords(trip.dropoff || '');
    if (cityCoords) return cityCoords;
    return hubCoords;
  }

  // Check if all trips share the same dropoff
  // (multi-load clinic run)
  function normalizeAddr(addr) {
    return (addr || '').toLowerCase()
      .replace(/[^a-z0-9]/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();
  }

  const dropoffs = trips.map(t => normalizeAddr(t.dropoff));
  const uniqueDropoffs = new Set(dropoffs);
  const isSharedDropoff = uniqueDropoffs.size === 1;

  let optimized;

  if (isSharedDropoff) {
    // CLINIC RUN: all riders go to same dropoff
    // Sort by distance from hub DESCENDING —
    // farthest pickup first, sweep toward clinic
    const clinicCoords = getDropoffCoords(trips[0]);

    optimized = [...trips].sort((a, b) => {
      const coordsA = getTripCoords(a);
      const coordsB = getTripCoords(b);

      // Distance from hub
      const distA = estimateDistanceMiles(
        hubCoords.lat, hubCoords.lng,
        coordsA.lat, coordsA.lng);
      const distB = estimateDistanceMiles(
        hubCoords.lat, hubCoords.lng,
        coordsB.lat, coordsB.lng);

      // Farthest from hub goes first
      // (driver sweeps outward then back to clinic)
      return distB - distA;
    });

    console.log('NEMT Optimize: clinic run — ' +
      'sorted by distance from hub descending');

  } else {
    // MIXED ROUTE: different dropoffs
    // Use nearest-neighbor greedy algorithm
    // starting from hub
    const remaining = [...trips];
    optimized = [];
    let currentCoords = hubCoords;

    while (remaining.length > 0) {
      // Find closest unvisited pickup to current position
      let closestIdx = 0;
      let closestDist = Infinity;

      for (let i = 0; i < remaining.length; i++) {
        const coords = getTripCoords(remaining[i]);
        const dist = estimateDistanceMiles(
          currentCoords.lat, currentCoords.lng,
          coords.lat, coords.lng);
        if (dist < closestDist) {
          closestDist = dist;
          closestIdx = i;
        }
      }

      const nextTrip = remaining.splice(closestIdx, 1)[0];
      optimized.push(nextTrip);

      // Move to the dropoff of this trip
      // (next pickup starts from here)
      currentCoords = getDropoffCoords(nextTrip);
    }

    console.log('NEMT Optimize: mixed route — ' +
      'nearest-neighbor from hub');
  }

  // Apply optimized order
  trips.length = 0;
  optimized.forEach(t => trips.push(t));

  render();

  // Update button feedback
  const btn = document.getElementById('optimizeBtn');
  if (btn) {
    const modeLabel = isSharedDropoff
      ? '✓ Clinic Sweep!'
      : '✓ Optimized!';
    btn.textContent = modeLabel;
    btn.style.background = '#27ae60';
    setTimeout(() => {
      btn.textContent = '⚡ Optimize Order';
      btn.style.background = '#8e44ad';
    }, 2000);
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
  document.getElementById('newLoadBtn')?.addEventListener('click', newLoad);
  document.getElementById('clearRouteBtn')?.addEventListener('click', clearRoute);
  document.getElementById('switchHubBtn')?.addEventListener('click', switchHub);
  document.getElementById('optimizeBtn')?.addEventListener('click', optimizeOrder);
  document.getElementById('mapsBtn')?.addEventListener('click', openInGoogleMaps);
  document.getElementById('copyBtn')?.addEventListener('click', copyRouteSummary);
  document.getElementById('saveBtn')?.addEventListener('click', saveRoute);
  document.getElementById('loadBtn')?.addEventListener('click', loadRoute);

  // Delegated listener: Remove buttons + inline edit clicks (Features 2 & 3)
  document.getElementById('trips-area')?.addEventListener('click', e => {
    const removeBtn = e.target.closest('.btn-remove');
    if (removeBtn) {
      const idx = parseInt(removeBtn.dataset.idx);
      if (!isNaN(idx)) removeTrip(idx);
      return;
    }
    const editable = e.target.closest('[data-editable]');
    if (editable) startInlineEdit(editable);
  });

  // Enter key in form inputs submits the form
  document.addEventListener('keydown', e => {
    if (e.key === 'Enter' && e.target.tagName === 'INPUT' && !e.target.dataset.tripIdx) {
      addTrip();
    }
  });

  // Feature 1: wire up geocode-on-blur for form address fields
  setupAddressGeocode('pickup',  'pickup_lat',  'pickup_lng',  'pickup-geo-status',  'pickup-geo-sublabel');
  setupAddressGeocode('dropoff', 'dropoff_lat', 'dropoff_lng', 'dropoff-geo-status', 'dropoff-geo-sublabel');

  console.log('NEMT: All button bindings attached (v1.4.0)');

  // Load today's driver assignments from GitHub Pages
  fetch('https://joegritter-bit.github.io/nemt-map/driver_routes.json?t=' + Date.now())
    .then(r => r.json())
    .then(data => {
      if (!data.drivers) return;
      const today = new Date().toLocaleDateString('en-US', {
        month: '2-digit', day: '2-digit', year: 'numeric'
      });
      if (data.date === today) {
        const existing = JSON.parse(localStorage.getItem('nemt_driver_routes') || '{}');
        const merged = { ...existing };
        for (const [driver, driverTrips] of Object.entries(data.drivers)) {
          merged[driver] = { trips: driverTrips, hub: 'Effingham', savedAt: data.generated_at, source: 'auto' };
        }
        localStorage.setItem('nemt_driver_routes', JSON.stringify(merged));
        console.log(`NEMT: Loaded ${Object.keys(data.drivers).length} driver routes from assignments scraper`);
      }
    })
    .catch(() => console.log('NEMT: No driver routes file available yet'));

  render();
});
