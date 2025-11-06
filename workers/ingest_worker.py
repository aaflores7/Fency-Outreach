import time
import json
from datetime import datetime
import pytz

# Import shared components
from core.database import supabase, check_db_connection
from core.api_clients import property_radar_client
from config import PROPERTY_RADAR_LIST_ID, INGEST_BATCH_LIMIT

UTC = pytz.UTC

# --- Data Transformation & Database Functions ---
# These functions are now part of the worker's responsibility, transforming API
# data into a format ready for the database.

def parse_mail_address(mail_address_list):
    """
    Parses a complex 'MailAddress' field from the PropertyRadar person object.
    It robustly handles different address formats (e.g., "City, ST ZIP" and "City ST ZIP")
    and correctly removes trailing commas from the city name.
    """
    # Initial checks for valid input data structure
    if not mail_address_list or not isinstance(mail_address_list, list):
        return {"street": None, "city": None, "state": None, "zip": None}
        
    first_address_obj = mail_address_list[0]
    if not isinstance(first_address_obj, dict) or "Address" not in first_address_obj:
        return {"street": None, "city": None, "state": None, "zip": None}

    full_address = first_address_obj.get("Address", "")
    if not full_address:
        return {"street": None, "city": None, "state": None, "zip": None}

    # Split the full address string by commas
    parts = full_address.split(',')
    
    # The first part is always assumed to be the street address
    street = parts[0].strip()
    city, state, zip_code = None, None, None

    # Process the remaining parts of the address if they exist
    if len(parts) > 1:
        # Re-join everything after the street address to handle the rest as a single block.
        # This makes the logic consistent for different comma placements.
        city_state_zip_str = ",".join(parts[1:]).strip()

        # We work backwards from the end of the string, which is generally more reliable.
        # Find the last space, which typically separates the zip code.
        last_space_index = city_state_zip_str.rfind(' ')
        
        if last_space_index != -1:
            # Assume everything after the last space is the zip code
            zip_code_candidate = city_state_zip_str[last_space_index + 1:].strip()
            
            # The part before the zip code contains the city and state
            state_city_part = city_state_zip_str[:last_space_index].strip()
            
            # Find the last space in the remaining part to separate state from city
            second_last_space_index = state_city_part.rfind(' ')

            if second_last_space_index != -1:
                # Everything after this space is the state
                state = state_city_part[second_last_space_index + 1:].strip()
                # Everything before it is the city
                city_raw = state_city_part[:second_last_space_index].strip()
                city = city_raw.rstrip(',').strip()

            else:
                state = state_city_part.rstrip(',').strip()

            # Assign the zip code if it looks valid (e.g., is a digit)
            if zip_code_candidate.isdigit():
                zip_code = zip_code_candidate

    return {"street": street, "city": city, "state": state, "zip": zip_code}

def upsert_property_to_supabase(property_data):
    """Transforms and upserts a single property's data into the 'properties' table."""
    def to_bool(value):
        return True if value == 1 else False if value == 0 else None

    record = {
        "radar_id": property_data.get("RadarID"),
        "address": property_data.get("Address"),
        "city": property_data.get("City"),
        "state": property_data.get("State"),
        "zip_code": property_data.get("ZipFive"),
        "county": property_data.get("County"),
        "latitude": property_data.get("Latitude"),
        "longitude": property_data.get("Longitude"),
        "last_transfer_rec_date": property_data.get("LastTransferRecDate"),
        "last_transfer_type": property_data.get("LastTransferType"),
        "last_transfer_value": property_data.get("LastTransferValue"),
        "ptype": property_data.get("PType"),
        "advanced_type": property_data.get("AdvancedPropertyType"),
        "beds": property_data.get("Beds"),
        "baths": property_data.get("Baths"),
        "sqft": property_data.get("SqFt"),
        "lot_size_acres": property_data.get("LotSizeAcres"),
        "year_built": property_data.get("YearBuilt"),
        "has_pool": to_bool(property_data.get("Pool")),
        "avm": property_data.get("AVM"),
        "available_equity": property_data.get("AvailableEquity"),
        "is_same_mailing": to_bool(property_data.get("isSameMailing")),
        "in_foreclosure": to_bool(property_data.get("inForeclosure")),
        "in_tax_delinquency": to_bool(property_data.get("inTaxDelinquency")),
        "is_listed_for_sale": to_bool(property_data.get("isListedForSale")),
        "last_fetched_at": datetime.now(UTC).isoformat()
    }

    if not record["radar_id"]:
        print(f"    -! ERROR: Missing RadarID. Cannot upsert. Data: {property_data}")
        return False

    print(f"    -> Upserting property record for RadarID {record['radar_id']}...")
    try:
        supabase.table("properties").upsert(record, on_conflict="radar_id").execute()
        return True
    except Exception as e:
        print(f"    -! Supabase Error (Property): {e}")
        return False

def upsert_owners_to_supabase(owners_data, radar_id):
    """Transforms and upserts a list of owner data into the 'owners' table."""
    records_to_upsert = []
    for person in owners_data:
        address_parts = parse_mail_address(person.get("MailAddress"))
        initial_email = person.get("Email")
        status = 'pending_verification' if initial_email else 'pending_enrichment'
        is_primary_raw = person.get("isPrimaryContact")
        is_primary_contact = True if is_primary_raw == 1 else False if is_primary_raw == 0 else None
        primary_res_raw = person.get("PrimaryResidence")
        is_primary_residence = True if primary_res_raw and isinstance(primary_res_raw, list) else False
        age_str = person.get("Age")
        age_int = int(age_str) if age_str and age_str.isdigit() else None
        phone_obj = person.get("Phone")
        phone_str = json.dumps(phone_obj) if phone_obj else None

        record = {
            "person_key": person.get("PersonKey"),
            "radar_id": radar_id,
            "first_name": person.get("FirstName"),
            "last_name": person.get("LastName"),
            "entity_name": person.get("EntityName"),
            "person_type": person.get("PersonType"),
            "age": age_int,
            "gender": person.get("Gender"),
            "occupation": person.get("Occupation"),
            "is_primary_contact": is_primary_contact,
            "ownership_role": person.get("OwnershipRole"),
            "is_primary_residence": is_primary_residence,
            "original_phone": phone_str,
            "original_email": initial_email,
            "processing_status": status,
            "mail_street_address": address_parts["street"],
            "mail_city": address_parts["city"],
            "mail_state": address_parts["state"],
            "mail_zip_code": address_parts["zip"]
        }
        records_to_upsert.append(record)

    if not records_to_upsert:
        return
        
    print(f"    -> Upserting {len(records_to_upsert)} owner records for RadarID {radar_id}...")
    try:
        supabase.table("owners").upsert(records_to_upsert, on_conflict="person_key").execute()
        print("    -> Supabase upsert for owners successful!")
    except Exception as e:
        print(f"    -! Supabase Error (Owners): {e}")


def run_ingestion_worker():
    """Main orchestration function for the ingestion worker."""
    if not check_db_connection():
        return

    # 1. Get a batch of RadarIDs from the specified list
    id_response = property_radar_client.get_radar_ids_from_list(PROPERTY_RADAR_LIST_ID, INGEST_BATCH_LIMIT)

    if not id_response["success"] or not id_response["data"]:
        print("Failed to retrieve item summaries or list is empty. Worker finished.")
        return

    item_summaries = id_response["data"]
    print(f"\nFound {len(item_summaries)} records to process. Starting ingestion...")

    # 2. Process each RadarID
    for item in item_summaries:
        radar_id = item.get("RadarID")
        if not radar_id:
            print("  -! WARNING: Item found with no 'RadarID'. Skipping.")
            continue
        
        print(f"\n--- Processing RadarID: {radar_id} ---")

        # 2a. Fetch and save property details
        property_response = property_radar_client.get_property_details(radar_id)

        if not property_response["success"]:
            print(f"Failed to get property details for {radar_id}. Error: {property_response['error']}. Skipping.")
            continue

        property_save_success = upsert_property_to_supabase(property_response["data"])
        
        # 2b. If property saved, fetch and save associated owners
        if property_save_success:
            persons_response = property_radar_client.get_persons_for_property(radar_id)
            if persons_response["success"] and persons_response["data"]:
                upsert_owners_to_supabase(persons_response["data"], radar_id)
            else:
                print(f"    -! Could not fetch owners for {radar_id}. Reason: {persons_response.get('error', 'No owners found')}")
        else:
            print(f"    -! Skipping owners since property upsert failed for {radar_id}.")
            
        time.sleep(0.5)  # Rate limiting to be kind to the API

    print("\n" + "="*50)
    print("   INGESTION SCRIPT COMPLETE   ")
    print("="*50)


if __name__ == "__main__":
    run_ingestion_worker()