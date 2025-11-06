import requests
import json
from config import PDL_API_KEY

BASE_URL = "https://api.peopledatalabs.com/v5/person/enrich"
HEADERS = {
    "X-Api-Key": PDL_API_KEY,
    "Content-Type": "application/json"
}

def enrich_person(**kwargs):
    """
    Enriches a person's profile using PDL with any available data points.
    
    Dynamically builds the parameters from the provided keyword arguments,
    ignoring any keys with None or empty values.

    Args:
        **kwargs: A dictionary of person attributes (e.g., first_name, email, etc.).

    Returns:
        A dictionary with success status and data or an error message.
    """
    params = {}
    # Dynamically build the params dictionary, including only keys with valid values
    for key, value in kwargs.items():
        if value: # This checks for both None and empty strings/lists
            params[key] = value

    # PDL requires at least one identifier to attempt a match.
    if not params:
        return {"success": False, "error": "No valid parameters provided for enrichment."}

    # Add a minimum likelihood to avoid low-quality matches
    params['min_likelihood'] = 3

    print(f"  -> Enriching profile with parameters: {list(params.keys())}")
    try:
        response = requests.get(BASE_URL, headers=HEADERS, params=params, timeout=25)
        
        if response.status_code == 404:
            print("    -! Person not found in People Data Labs.")
            return {"success": True, "data": None, "status_code": 404}
            
        response.raise_for_status()
        
        data = response.json()
        
        if data.get("status") == 200 and 'data' in data:
            return {"success": True, "data": data['data'], "status_code": 200}
        else:
            # This can happen for validation errors (e.g., malformed email)
            error_detail = data.get('error', {}).get('message', 'API returned a non-200 status')
            print(f"    -! PDL API Error: {error_detail}")
            return {"success": False, "error": error_detail, "data": data}

    except requests.exceptions.RequestException as err:
        print(f"    -! ERROR calling PDL API: {err}")
        return {"success": False, "error": str(err)}