import requests
import neverbounce_sdk
from config import MILLIONVERIFIER_API_KEY, NEVERBOUNCE_API_KEY

# --- MillionVerifier Client Logic ---

MV_BASE_URL = "https://api.millionverifier.com/api/v3"

def verify_millionverifier(email: str):
    """
    Verifies a single email using the MillionVerifier API.
    """
    if not MILLIONVERIFIER_API_KEY:
        return {"success": False, "error": "MillionVerifier API key is not configured."}

    params = {
        "api": MILLIONVERIFIER_API_KEY,
        "email": email,
        "timeout": 30
    }
    try:
        response = requests.get(MV_BASE_URL, params=params, timeout=35)
        response.raise_for_status()
        return {"success": True, "data": response.json()}
    except requests.exceptions.RequestException as err:
        print(f"    -! MillionVerifier API Error: {err}")
        return {"success": False, "error": str(err)}


# --- NeverBounce Client Logic ---

# Initialize the client once at the module level for efficiency
nb_client = None
if NEVERBOUNCE_API_KEY:
    try:
        nb_client = neverbounce_sdk.client(api_key=NEVERBOUNCE_API_KEY, timeout=30)
    except Exception as e:
        print(f"FATAL: Failed to initialize NeverBounce client. Error: {e}")

def verify_neverbounce(email: str):
    """
    Verifies a single email using the NeverBounce SDK.
    """
    if not nb_client:
        return {"success": False, "error": "NeverBounce client is not initialized."}

    try:
        # The SDK returns a dictionary directly
        result = nb_client.single_check(email)
        return {"success": True, "data": result}
    except Exception as err:
        # The SDK can throw various errors, including API connection issues
        print(f"    -! NeverBounce API Error: {err}")
        return {"success": False, "error": str(err)}