import requests
import json

# --- Configuration ---
# IMPORTANT: Replace with your actual API Key from your PropertyRadar account.
API_KEY = "76a0b6bd071e39d29c21e77c36decfa8a4d83b2e" 
BASE_URL = "https://api.propertyradar.com/v1"
LISTS_ENDPOINT = f"{BASE_URL}/lists"

# --- Request Headers ---
# The API uses a Bearer Token for authentication.
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def get_all_lists():
    """
    Fetches and displays a summary of all lists in the PropertyRadar account.
    """
    print(f"Fetching all lists from PropertyRadar: {LISTS_ENDPOINT}")

    try:
        # To get a collection of resources, we use a GET request.
        response = requests.get(LISTS_ENDPOINT, headers=headers)

        # This will automatically raise an exception for bad status codes (like 401, 404, 500).
        response.raise_for_status()

        # If the request was successful, parse the JSON response.
        lists_data = response.json()

        print("\n--- Request Successful! ---")

        # Check if the response is a list and not empty
        if isinstance(lists_data, list) and lists_data:
            print(f"Found {len(lists_data)} lists in your account:")
            print("-" * 40)
            
            # Iterate through each list and print its key details
            for pr_list in lists_data:
                # Use .get() to safely access keys that might be missing
                list_id = pr_list.get('id', 'N/A')
                list_name = pr_list.get('ListName', 'N/A')
                list_type = pr_list.get('ListType', 'N/A')
                is_monitored = "Yes" if pr_list.get('isMonitored') == 1 else "No"
                item_count = pr_list.get('itemCount', 'N/A')

                print(f"  ID:           {list_id}")
                print(f"  Name:         {list_name}")
                print(f"  Type:         {list_type}")
                print(f"  Monitored:    {is_monitored}")
                print(f"  Item Count:   {item_count}")
                print("-" * 40)
        
        elif isinstance(lists_data, list) and not lists_data:
             print("Found 0 lists in your account.")
        else:
            print("Received an unexpected response format. Full response:")
            print(json.dumps(lists_data, indent=2))

    except requests.exceptions.HTTPError as http_err:
        print(f"\n--- HTTP Error Occurred ---")
        print(f"Status Code: {http_err.response.status_code}")
        print(f"Response Body: {http_err.response.text}")
        print("\nCommon Errors:")
        print("401 Unauthorized: Double-check that your API_KEY is correct and valid.")
    except requests.exceptions.RequestException as err:
        print(f"\n--- A Network or Request Error Occurred ---")
        print(err)
    except json.JSONDecodeError:
        print("\n--- Error Decoding JSON ---")
        print("Received a response that was not valid JSON. Response Body:")
        print(response.text)


# --- Run the main function ---
if __name__ == "__main__":
    if API_KEY == "YOUR_TOKEN_HERE":
        print("ERROR: Please replace 'YOUR_TOKEN_HERE' with your actual PropertyRadar API key before running.")
    else:
        get_all_lists()