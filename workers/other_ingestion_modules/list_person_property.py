import requests
import json
import time
import os

# --- Configuration ---
# Your actual API Key and the List ID you want to query.
API_KEY = "76a0b6bd071e39d29c21e77c36decfa8a4d83b2e" 
LIST_ID = "1087906" 

BASE_URL = "https://api.propertyradar.com/v1"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def save_to_json_file(data, filename, object_type="records"):
    """Saves the provided data to a specified JSON file."""
    if not data:
        print(f"-> No {object_type} data was provided to save for this operation.")
        return
    try:
        # 'with open' ensures the file is properly closed even if errors occur
        with open(filename, 'w') as json_file:
            # indent=4 makes the file human-readable (pretty-printed)
            json.dump(data, json_file, indent=4)
        print(f"-> Successfully saved {len(data)} {object_type} to '{filename}'")
    except IOError as e:
        print(f"-> ERROR: Could not write to file {filename}. Reason: {e}")

# --- API Call Functions ---

def get_radar_ids_from_list(list_id):
    """
    Step 1: Fetches a list of item summaries (containing RadarIDs) from a given List ID.
    """
    list_items_endpoint = f"{BASE_URL}/lists/{list_id}/items"
    params = {"Start": 0, "Limit": 1}
    print(f"Step 1: Fetching RadarID summaries from list: {list_id}...")
    try:
        response = requests.get(list_items_endpoint, headers=HEADERS, params=params)
        response.raise_for_status()
        data = response.json()
        property_summaries = data.get('results')
        if property_summaries and isinstance(property_summaries, list):
            print(f"Success! Found {len(property_summaries)} item summaries to process.")
            return property_summaries
        else:
            print("Could not find a 'results' key or the list was empty in the response.")
            return None
    except requests.exceptions.HTTPError as err:
        print(f"--- HTTP Error in Step 1 ---")
        print(f"Status Code: {err.response.status_code}\nResponse Body: {err.response.text}")
        return None

def get_persons_for_radar_id(radar_id):
    """
    Step 2a: Fetches the list of owners/persons for a single RadarID.
    """
    persons_endpoint = f"{BASE_URL}/properties/{radar_id}/persons"
    params = {
        "Purchase": 1, # Safety parameter
        "Fields": "default"
    }
    print(f"  -> Fetching PERSONS for RadarID: {radar_id}...")
    try:
        response = requests.get(persons_endpoint, headers=HEADERS, params=params)
        response.raise_for_status()
        data = response.json()
        return data.get("results")
    except requests.exceptions.HTTPError as err:
        print(f"    -! ERROR fetching persons for {radar_id}: {err.response.status_code}")
        return None

def get_property_details_for_radar_id(radar_id):
    """
    Step 2b: Fetches the full property details for a single RadarID.
    """
    property_endpoint = f"{BASE_URL}/properties/{radar_id}"
    params = {
        "Purchase": 1, # Safety parameter
        "Fields": "Overview"
    }
    print(f"  -> Fetching PROPERTY details for RadarID: {radar_id}...")
    try:
        response = requests.get(property_endpoint, headers=HEADERS, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as err:
        print(f"    -! ERROR fetching property details for {radar_id}: {err.response.status_code}")
        return None

# --- Main Script Execution ---
if __name__ == "__main__":
    
    # Step 1: Get the list of item summaries (containing RadarIDs)
    item_summaries = get_radar_ids_from_list(LIST_ID)
    
    all_persons_data = []
    
    if item_summaries:
        print("\nStep 2: Now fetching details for each RadarID individually...")

        # Create a directory to store the individual property files
        output_dir = f"property_details_for_list_{LIST_ID}"
        os.makedirs(output_dir, exist_ok=True)
        print(f"Individual property files will be saved in: '{output_dir}/'")
        
        # Step 2: Loop through the summaries and make two API calls for each
        for item in item_summaries:
            radar_id = item.get("RadarID")
            
            if radar_id:
                # --- Get and process PERSON data ---
                persons_list = get_persons_for_radar_id(radar_id)
                if persons_list and isinstance(persons_list, list):
                    print(f"    -> Found {len(persons_list)} owner(s) for {radar_id}.")
                    all_persons_data.extend(persons_list)
                
                # --- Get and save PROPERTY data ---
                property_details = get_property_details_for_radar_id(radar_id)
                if property_details:
                    property_filename = os.path.join(output_dir, f"property_{radar_id}.json")
                    # We save the single property record to its own file
                    save_to_json_file([property_details], property_filename, object_type="property")
                
                # Be a good API citizen: wait a little between requests
                time.sleep(0.5)
            else:
                print("  -! WARNING: Found an item in the list summary with no 'RadarID' key.")

        # --- Final Output and Saving of Aggregated Persons ---
        print("\n" + "="*50)
        print(f"   FINAL SCRIPT COMPLETE   ")
        print("="*50)

        # Now, save the master list of all persons collected from all properties
        persons_master_filename = f"all_persons_for_list_{LIST_ID}.json"
        save_to_json_file(all_persons_data, persons_master_filename, object_type="person records")
    else:
        print("No item summaries were retrieved. Script will now exit.")