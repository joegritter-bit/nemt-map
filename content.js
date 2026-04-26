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

const TRIP_COST = {
  MPG: 15.5,
  GAS_PRICE: 4.14,       // Central IL average (AAA, April 2026)
  DRIVER_RATE: 19.00,    // per hour
  WEAR_PER_MILE: 0.14    // wear & tear, high-mileage van
};

const EFFINGHAM_DEADHEAD_MILES = {
  'springfield': 96,   'chatham': 91,
  'decatur': 58,       'taylorville': 66,
  'champaign': 75,     'urbana': 77,
  'rantoul': 85,       'danville': 100,
  'bloomington': 90,   'normal': 92,
  'clinton': 68,       'farmer city': 78,
  'mattoon': 38,       'charleston': 46,
  'paris': 65,         'robinson': 54,
  'olney': 44,         'fairfield': 52,
  'mt vernon': 72,     'benton': 76,
  'west frankfort': 84,'carbondale': 105,
  'anna': 115,         'harrisburg': 88,
  'vandalia': 34,      'centralia': 58,
  'salem': 48,         'flora': 28,
  'louisville': 26,    'newton': 25,
  'effingham': 0,      'altamont': 14,
  'teutopolis': 8,     'dieterich': 10,
  'greenup': 30,       'casey': 42,
  'marshall': 55,      'oblong': 50,
  'lawrenceville': 70, 'peoria': 133,
  'streator': 145,     'ottawa': 155,
  'galesburg': 175,    'quincy': 215,
  'macomb': 170,       'jacksonville': 122,
  'beardstown': 140,   'carmi': 110,
  'mt carmel': 90,     'watseka': 105,
  'kankakee': 130,     'pontiac': 110
};

function geocodeDeadhead(hubAddress, pickupAddress) {
  return new Promise((resolve) => {
    try {
      chrome.runtime.sendMessage({
        type: 'GET_DEADHEAD_MILES',
        origin: hubAddress,
        destination: pickupAddress
      }, (response) => {
        if (chrome.runtime.lastError) {
          console.warn('NEMT geocode message error:', chrome.runtime.lastError);
          resolve(null);
          return;
        }
        if (response && response.miles !== null) {
          console.log('NEMT geocode result:', pickupAddress, '→', response.miles, 'mi');
          resolve(response.miles);
        } else {
          console.warn('NEMT geocode failed:', response?.error);
          resolve(null);
        }
      });
    } catch(e) {
      console.warn('NEMT geocode exception:', e);
      resolve(null);
    }
  });
}

const HUB_ADDRESSES_EXT = {
  'effingham': '506 South St, Effingham, IL 62401',
  'springfield': '1 North Old State Capitol Plaza, Springfield, IL 62701'
};

async function geocodeAllBadges() {
  const badges = document.querySelectorAll('.nemt-badge-wrapper');
  console.log('NEMT geocodeAllBadges: found', badges.length, 'badge wrappers');
  if (!badges.length) return;

  const badgeArray = Array.from(badges);
  const BATCH_SIZE = 8;
  const BATCH_DELAY = 150; // ms between batches

  for (let i = 0; i < badgeArray.length; i += BATCH_SIZE) {
    const batch = badgeArray.slice(i, i + BATCH_SIZE);

    const batchUpdates = batch.map(async (wrapper) => {
      try {
        const pickupText = wrapper.dataset.pickup || '';
        if (!pickupText || pickupText.trim() === '') return;
        if (wrapper.dataset.geocoded === 'true') return;

        console.log('NEMT geocode: firing for', pickupText,
          '| miles:', wrapper.dataset.miles,
          '| geocoded already:', wrapper.dataset.geocoded);

        const hubAddress = HUB_ADDRESSES_EXT['effingham'];
        const deadheadMi = await geocodeDeadhead(hubAddress, pickupText);
        if (deadheadMi === null) return;

        const miles = parseFloat(wrapper.dataset.miles) || 0;
        const dropoff = wrapper.dataset.dropoff || '';
        const newCost = calculateTripCost(miles, pickupText, dropoff, deadheadMi);
        if (!newCost) return;

        const costLine = wrapper.querySelector('.nemt-cost-line');
        if (costLine) {
          const payout = parseFloat(wrapper.dataset.payout) || 0;
          const margin = payout - newCost;
          const marginStr = margin >= 0
            ? `+$${margin.toFixed(2)}`
            : `-$${Math.abs(margin).toFixed(2)}`;
          const marginColor = margin >= 40
            ? '#155724' : margin >= 15
            ? '#856404' : '#721c24';

          costLine.innerHTML =
            `Cost ~$${newCost.toFixed(2)} ` +
            `<span style="font-weight:bold;color:${marginColor}">${marginStr}</span> ` +
            `<span style="color:#aaa;font-size:10px">📍</span>`;

          wrapper.dataset.geocoded = 'true';
        }
      } catch(e) {
        // Silent fail — lookup table value stays
      }
    });

    await Promise.all(batchUpdates);

    if (i + BATCH_SIZE < badgeArray.length) {
      await new Promise(resolve => setTimeout(resolve, BATCH_DELAY));
    }
  }
}

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
  .catch(() => {});

// Clinic address database — loaded from bundled JSON
let CLINIC_ADDRESSES_NORMALIZED = [];
let CLINIC_DATA = [];

fetch('https://joegritter-bit.github.io/nemt-map/clinics.json?t=' + Date.now())
  .then(r => r.json())
  .then(data => {
    CLINIC_DATA = data.clinics || [];
    CLINIC_ADDRESSES_NORMALIZED = CLINIC_DATA.map(c => normalizeAddrJS(c.address));
    console.log(`NEMT: Loaded ${CLINIC_DATA.length} clinic addresses`);
  })
  .catch(() => {});

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

  // Primary: match against known clinic address database
  if (CLINIC_ADDRESSES_NORMALIZED.length > 0) {
    const normalized = normalizeAddrJS(dropoffAddress);
    if (CLINIC_ADDRESSES_NORMALIZED.some(c =>
        normalized.includes(c) || c.includes(normalized))) {
      return true;
    }
  }

  // Fallback: keyword matching
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

function getDeadheadMiles(pickupAddress) {
  if (!pickupAddress) return 50; // default unknown
  const lower = pickupAddress.toLowerCase();
  for (const [city, miles] of Object.entries(EFFINGHAM_DEADHEAD_MILES)) {
    if (lower.includes(city)) return miles;
  }
  return 50; // default if city not found
}

function calculateTripCost(miles, pickupAddress, dropoffAddress, overrideDeadhead = null) {
  const tripMiles = parseFloat(miles) || 0;
  if (tripMiles <= 0) return null;

  // Full mileage picture:
  // deadhead out + rider RT + deadhead back
  const deadhead = overrideDeadhead !== null
    ? overrideDeadhead
    : getDeadheadMiles(pickupAddress);
  const totalMiles = (deadhead * 2) + (tripMiles * 2);

  // Fuel
  const fuel = (totalMiles / TRIP_COST.MPG) * TRIP_COST.GAS_PRICE;

  // Driver labor: drive time at 45mph avg + wait time
  // Clinic dropoffs: 5 min wait; standard appointments: 1 hr wait
  const avgSpeed = totalMiles > 60 ? 55 : 45;
  const driveHours = totalMiles / avgSpeed;
  const waitHours = isClinic(dropoffAddress || '') ? (5 / 60) : 1.0;
  const labor = (driveHours + waitHours) * TRIP_COST.DRIVER_RATE;

  // Wear & tear
  const wear = totalMiles * TRIP_COST.WEAR_PER_MILE;

  const total = fuel + labor + wear;
  return Math.round(total * 100) / 100;
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



function createBadge(pickupAddr, dropoffAddr, miles, tripTime, apptTime, rawPickupTime) {
  const county = detectCounty(pickupAddr);
  const payout = calculatePayout(county, parseFloat(miles) || 0, tripTime);
  const clinic = isClinic(dropoffAddr);

  const tripCost = calculateTripCost(miles, pickupAddr, dropoffAddr);
  const margin = (payout && tripCost) ? payout - tripCost : null;
  const marginStr = margin !== null
    ? (margin >= 0
        ? `+$${margin.toFixed(2)}`
        : `-$${Math.abs(margin).toFixed(2)}`)
    : '';
  const marginColor = margin !== null
    ? (margin >= 40 ? '#155724' : margin >= 15 ? '#856404' : '#721c24')
    : '#555';
  const costStr = tripCost ? `Cost ~$${tripCost.toFixed(2)}` : '';

  const wrapper = document.createElement('div');
  wrapper.className = 'nemt-badge-wrapper';
  wrapper.style.marginTop = '4px';
  wrapper.dataset.miles = miles;
  wrapper.dataset.payout = payout || 0;
  wrapper.dataset.pickup = pickupAddr || '';
  wrapper.dataset.dropoff = dropoffAddr || '';
  wrapper.dataset.geocoded = 'false';

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
      <div class="nemt-cost-line">${costStr} <span style="font-weight:bold; color:${marginColor}">${marginStr}</span></div>
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
      <div class="nemt-cost-line">${costStr} <span style="font-weight:bold; color:${marginColor}">${marginStr}</span></div>
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
    <div class="nemt-cost-line">${costStr} <span style="font-weight:bold; color:${marginColor}">${marginStr}</span></div>
    ${clinic ? '<span class="nemt-badge clinic">💊 Clinic</span>' : ''}
    <button class="nemt-add-btn nemt-route-btn" data-trip='${tripData}'>+ Route</button>
  `;

  return wrapper;
}


function isOnMarketplace() {
  return window.location.href.includes('/marketplace');
}

function processRows() {
  if (!isOnMarketplace()) return;

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

    } catch(e) {
      console.error('NEMT: Row processing error', e);
    }
  });

  sortAllRows();

  // Geocode deadhead for all badges in background
  setTimeout(() => geocodeAllBadges(), 500);
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

      // Clinic — just below regular riders, above all county tiers
      if (row.querySelector('.nemt-badge.clinic')) return 90000 + (payout || 0);

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
      processRows();
      return;
    }
    if (Date.now() - start > TIMEOUT_MS) {
      clearInterval(interval);
      processRows();
    }
  }, 100);
})();

let _processTimer = null;

const observer = new MutationObserver((mutations) => {
  if (!isOnMarketplace()) return;

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
// SPA NAVIGATION DETECTION — re-initialize when React Router
// navigates back to the marketplace without a page reload.
// ============================================================

let lastUrl = window.location.href;

const navObserver = new MutationObserver(() => {
  if (window.location.href !== lastUrl) {
    lastUrl = window.location.href;
    if (isOnMarketplace()) {
      console.log('[NEMT] SPA navigation detected — reinitializing');
      document.documentElement.dataset.nemtBridgeLoaded = '';
      setTimeout(() => {
        autoToggleServiceArea();
        processRows();
      }, 1000);
    }
  }
});

navObserver.observe(document.body, { childList: true, subtree: true });

window.addEventListener('popstate', () => {
  if (isOnMarketplace()) {
    setTimeout(() => {
      autoToggleServiceArea();
      processRows();
    }, 1000);
  }
});

