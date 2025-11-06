import time

# Import shared components
from core.database import supabase, check_db_connection
from core.api_clients import pdl_client

# A list of common role-based email prefixes to deprioritize
ROLE_BASED_PREFIXES = ['info@', 'contact@', 'admin@', 'support@', 'sales@', 'hello@', 'team@']

def extract_and_rank_emails(pdl_data):
    """
    Extracts, ranks, and returns ALL emails from the PDL enrichment response.

    Strategy:
    1.  Separate emails into 'personal' and 'work' lists.
    2.  Create a final ranked list in the following order of priority:
        - Non-role-based personal emails
        - All other personal emails
        - Non-role-based work emails
        - All other work emails
    
    Returns a sorted list of email strings, or an empty list if none are found.
    """
    if not pdl_data or 'emails' not in pdl_data or not pdl_data['emails']:
        return []

    personal_emails = [e['address'] for e in pdl_data['emails'] if e.get('type') == 'personal']
    work_emails = [e['address'] for e in pdl_data['emails'] if e.get('type') == 'work']

    def is_role_based(email):
        return any(email.lower().startswith(prefix) for prefix in ROLE_BASED_PREFIXES)

    # Separate each list into non-role-based and role-based
    non_role_personal = [email for email in personal_emails if not is_role_based(email)]
    role_personal = [email for email in personal_emails if is_role_based(email)]
    
    non_role_work = [email for email in work_emails if not is_role_based(email)]
    role_work = [email for email in work_emails if is_role_based(email)]

    # Combine the lists in order of priority to create the final ranked list
    ranked_emails = non_role_personal + role_personal + non_role_work + role_work
    
    return ranked_emails


def run_enrichment_worker():
    """Main orchestration function for the enrichment worker."""
    if not check_db_connection():
        return

    print("--- Starting Enrichment Worker ---")
    BATCH_SIZE = 50

    while True:
        try:
            response = supabase.table("owners") \
                .select("person_key, first_name, last_name, mail_street_address, mail_city, mail_state, mail_zip_code, original_email, original_phone") \
                .eq("processing_status", "pending_enrichment") \
                .limit(BATCH_SIZE) \
                .execute()
            
            owners_to_process = response.data
        except Exception as e:
            print(f"Error fetching owners from database: {e}")
            time.sleep(60)
            continue
        
        if not owners_to_process:
            print("No owners found for enrichment. Worker sleeping for 5 minutes...")
            time.sleep(300)
            continue
            
        print(f"\nFound {len(owners_to_process)} owners to enrich in this batch.")

        for owner in owners_to_process:
            person_key = owner['person_key']
            print(f"Processing owner with PersonKey: {person_key}")
            
            enrichment_params = {
                'first_name': owner.get('first_name'),
                'last_name': owner.get('last_name'),
                'street_address': owner.get('mail_street_address'),
                'locality': owner.get('mail_city'),
                'region': owner.get('mail_state'),
                'postal_code': owner.get('mail_zip_code'),
                'email': owner.get('original_email'),
                'phone': owner.get('original_phone')
            }

            enrichment_response = pdl_client.enrich_person(**enrichment_params)
            
            new_status = 'failed_enrichment'
            update_data = {}

            if enrichment_response["success"]:
                # --- THIS IS THE KEY CHANGE ---
                # Get the ranked list of all emails
                all_ranked_emails = extract_and_rank_emails(enrichment_response["data"])
                
                if all_ranked_emails:
                    print(f"    -> Success! Found {len(all_ranked_emails)} emails. Best one: {all_ranked_emails[0]}")
                    new_status = 'pending_post_enrichment_verification'
                    # Store the entire list in the new JSONB column
                    update_data['enriched_emails'] = all_ranked_emails
                else:
                    print("    -! Enrichment successful, but no usable emails were found.")
            else:
                print(f"    -! Enrichment API call failed: {enrichment_response['error']}")

            update_data['processing_status'] = new_status
            try:
                supabase.table("owners") \
                    .update(update_data) \
                    .eq("person_key", person_key) \
                    .execute()
            except Exception as e:
                print(f"    -! CRITICAL: Failed to update status for {person_key}. Error: {e}")
            
            time.sleep(1.5)

        print("\nBatch finished. Fetching next batch...")

if __name__ == "__main__":
    run_enrichment_worker()