import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- SUPABASE CONFIG ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# --- PROPERTY RADAR CONFIG ---
PROPERTY_RADAR_API_KEY = os.getenv("PROPERTY_RADAR_API_KEY")
PROPERTY_RADAR_LIST_ID = os.getenv("PROPERTY_RADAR_LIST_ID")

# --- GENERAL SETTINGS ---
# You can add other settings here, like batch sizes or log levels
INGEST_BATCH_LIMIT = 4 # Example: How many records to pull from the list at once


# --- PEOPLE DATA LABS CONFIG ---
PDL_API_KEY = os.getenv("PDL_API_KEY")

# --- WORKER SETTINGS ---
ENRICHMENT_BATCH_SIZE = 4 # How many records to process in one go

# --- VERIFICATION SERVICES ---
MILLIONVERIFIER_API_KEY = os.getenv("MILLIONVERIFIER_API_KEY")
NEVERBOUNCE_API_KEY = os.getenv("NEVERBOUNCE_API_KEY")