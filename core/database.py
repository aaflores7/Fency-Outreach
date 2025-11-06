from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY

# Initialize Supabase client
# The 'if' statement handles cases where credentials might be missing
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

def check_db_connection():
    """Checks if the Supabase client was successfully initialized."""
    if not supabase:
        print("FATAL ERROR: Supabase URL or Key is missing. Cannot connect to the database.")
        return False
    print("Database client initialized successfully.")
    return True