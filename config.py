# Central configuration for all NEMT pipeline modules.
# Change a value here and it applies everywhere.

# --- 🗺️ GEOGRAPHY ---
CITY_COUNTY_MAP = {
    "springfield": "Sangamon County", "chatham": "Sangamon County",
    "mattoon": "Coles County", "charleston": "Coles County", "oakland": "Coles County",
    "decatur": "Macon County", "champaign": "Champaign County",
    "urbana": "Champaign County", "danville": "Vermilion County", "indianola": "Vermilion County",
    "effingham": "Effingham County", "vandalia": "Fayette County",
    "centralia": "Marion County", "salem": "Marion County",
    "mt vernon": "Jefferson County", "mt. vernon": "Jefferson County",
    "taylorville": "Christian County", "monticello": "Piatt County",
    "louisville": "Clay County", "flora": "Clay County",
    "paris": "Edgar County", "casey": "Clark County", "marshall": "Clark County",
    "peoria": "Peoria County", "bloomington": "McLean County", "normal": "McLean County"
}

HUBS = {
    "Effingham":   {"coords": (39.1200, -88.5434)},
    "Springfield": {"coords": (39.8017, -89.6680)},
}

MIDWEST_VIEWBOX = [(35.0, -95.0), (44.0, -84.0)]

EXCLUDED_COUNTIES = {
    'Cook County', 'DuPage County', 'Kane County',
    'Lake County', 'McHenry County', 'Will County'
}

# --- 🚗 DRIVING LOGISTICS ---
AVG_MPH             = 50.0
VAN_CAPACITY        = 4
DEPOT_ADDRESS       = "506 South St, Effingham, IL 62401"

# --- ⏱️ SHIFT CONSTRAINTS ---
MAX_SHIFT_HOURS     = 11.0
MIN_PROFIT_PER_HOUR = 39.0
MAX_DEADHEAD_MINUTES = 60
MAX_RADIUS_MILES    = 30
MIN_GAP_HOURS       = 0.5

# --- 🗄️ FILE PATHS ---
DB_PATH       = 'data/nemt_data.db'
CLINICS_FILE  = 'clinics.txt'
ROUTES_FILE   = 'potential_routes.csv'

import logging
import os

LOG_DIR = 'logs'
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'nemt_pipeline.log')),
        logging.StreamHandler()
    ]
)

def get_logger(name):
    return logging.getLogger(name)
