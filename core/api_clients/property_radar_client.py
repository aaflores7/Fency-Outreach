import requests
from config import PROPERTY_RADAR_API_KEY

BASE_URL = "https://api.propertyradar.com/v1"
HEADERS = {
    "Authorization": f"Bearer {PROPERTY_RADAR_API_KEY}",
    "Content-Type": "application/json"
}

def get_radar_ids_from_list(list_id, limit=1):
    """Fetches a batch of RadarID summaries from a given List ID."""
    endpoint = f"{BASE_URL}/lists/{list_id}/items"
    params = {"Start": 0, "Limit": limit}
    print(f"Fetching up to {limit} RadarID summaries from list: {list_id}...")
    try:
        response = requests.get(endpoint, headers=HEADERS, params=params)
        response.raise_for_status()
        data = response.json()
        return {"success": True, "data": data.get('results', [])}
    except requests.exceptions.RequestException as err:
        print(f"--- API Error (get_radar_ids_from_list): {err}")
        return {"success": False, "error": str(err)}

def get_property_details(radar_id):
    """Fetches the full property details for a single RadarID."""
    endpoint = f"{BASE_URL}/properties/{radar_id}"
    params = {"Purchase": 1, "Fields": "Overview"}
    print(f"  -> Fetching PROPERTY details for RadarID: {radar_id}...")
    try:
        response = requests.get(endpoint, headers=HEADERS, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict) and "results" in data and data["results"]:
            return {"success": True, "data": data["results"][0]}
        else:
            return {"success": False, "error": "Unexpected JSON structure", "data": data}
    except requests.exceptions.RequestException as err:
        print(f"    -! ERROR fetching property details for {radar_id}: {err}")
        return {"success": False, "error": str(err)}

def get_persons_for_property(radar_id):
    """Fetches the list of owners/persons for a single RadarID."""
    endpoint = f"{BASE_URL}/properties/{radar_id}/persons"
    params = {"Purchase": 1, "Fields": "default"}
    print(f"  -> Fetching PERSONS for RadarID: {radar_id}...")
    try:
        response = requests.get(endpoint, headers=HEADERS, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()
        return {"success": True, "data": data.get("results")}
    except requests.exceptions.RequestException as err:
        print(f"    -! ERROR fetching persons for {radar_id}: {err}")
        return {"success": False, "error": str(err)}