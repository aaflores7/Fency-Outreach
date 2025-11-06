import time
import json

# Import shared components
from core.database import supabase, check_db_connection
from core.api_clients import verifier_client

# --- Define what constitutes a "good" or "bad" result from each service ---
# We are more lenient with "good" statuses to maximize accepted emails.
MV_GOOD_STATUSES = ['ok', 'catch_all']
NB_GOOD_STATUSES = ['valid', 'catchall', 'unknown'] # 'unknown' can be risky, but we accept it for now

# We are strict with "bad" statuses.
MV_BAD_STATUSES = ['invalid']
NB_BAD_STATUSES = ['invalid', 'disposable']


def run_verification_worker():
    """Main orchestration function for the verification worker."""
    if not check_db_connection():
        return

    print("--- Starting Verification Worker ---")
    BATCH_SIZE = 50

    while True:
        try:
            # Query for owners in either pending verification state
            response = supabase.table("owners") \
                .select("person_key, processing_status, original_email, enriched_emails") \
                .in_("processing_status", ['pending_verification', 'pending_post_enrichment_verification']) \
                .limit(BATCH_SIZE) \
                .execute()
            owners_to_process = response.data
        except Exception as e:
            print(f"Error fetching owners from database: {e}")
            time.sleep(60)
            continue

        if not owners_to_process:
            print("No owners found for verification. Worker sleeping for 5 minutes...")
            time.sleep(300)
            continue

        print(f"\nFound {len(owners_to_process)} owners to verify in this batch.")

        for owner in owners_to_process:
            person_key = owner['person_key']
            print(f"Processing owner with PersonKey: {person_key}")

            # Determine which emails to verify based on the current status
            emails_to_verify = []
            if owner['processing_status'] == 'pending_verification' and owner.get('original_email'):
                emails_to_verify = [owner['original_email']]
            elif owner['processing_status'] == 'pending_post_enrichment_verification' and owner.get('enriched_emails'):
                emails_to_verify = owner['enriched_emails']

            if not emails_to_verify:
                print("    -! No emails found to verify. Marking as failed.")
                supabase.table("owners").update({"processing_status": "failed_verification"}).eq("person_key", person_key).execute()
                continue

            final_status = 'failed_verification'
            is_verified = False
            # These logs will store the full history of all attempts for this owner
            verification_logs = {"millionverifier": {}, "neverbounce": {}}

            # Iterate through the ranked list of emails
            for email in emails_to_verify:
                print(f"  -> Verifying email: {email}")

                # Call both verification services
                mv_response = verifier_client.verify_millionverifier(email)
                nb_response = verifier_client.verify_neverbounce(email)

                # Log the full raw responses, keyed by the email address
                verification_logs["millionverifier"][email] = mv_response
                verification_logs["neverbounce"][email] = nb_response

                # Check if the email is considered valid
                mv_is_good = mv_response.get("success") and mv_response["data"].get("result") in MV_GOOD_STATUSES
                nb_is_good = nb_response.get("success") and nb_response["data"].get("result") in NB_GOOD_STATUSES
                
                # Check for strictly invalid results
                mv_is_bad = mv_response.get("success") and mv_response["data"].get("result") in MV_BAD_STATUSES
                nb_is_bad = nb_response.get("success") and nb_response["data"].get("result") in NB_BAD_STATUSES

                # --- Verification Logic ---
                if mv_is_good or nb_is_good:
                    print(f"    -> SUCCESS: Email '{email}' passed verification.")
                    final_status = 'complete'
                    is_verified = True
                    break # Exit the loop, we found a good email
                
                elif mv_is_bad or nb_is_bad:
                    print(f"    -> FAILED: Email '{email}' is invalid. Trying next email if available.")
                    # Continue to the next email in the list
                else:
                    print(f"    -> UNCERTAIN: Email '{email}' gave an uncertain result. Trying next email if available.")

            # After checking all emails for an owner, update their record
            update_data = {
                "processing_status": final_status,
                "millionverifier_response": json.dumps(verification_logs["millionverifier"]),
                "neverbounce_response": json.dumps(verification_logs["neverbounce"]),
                # For easy filtering, we can also store the final status of the primary email
                "millionverifier_status": verification_logs["millionverifier"].get(emails_to_verify[0], {}).get("data", {}).get("result"),
                "neverbounce_status": verification_logs["neverbounce"].get(emails_to_verify[0], {}).get("data", {}).get("result")
            }
            
            try:
                supabase.table("owners").update(update_data).eq("person_key", person_key).execute()
                print(f"  -> Database updated for {person_key} with final status: {final_status}")
            except Exception as e:
                print(f"    -! CRITICAL: Failed to update status for {person_key}. Error: {e}")
            
            time.sleep(1) # Brief pause between owners

        print("\nBatch finished. Fetching next batch...")


if __name__ == "__main__":
    run_verification_worker()

    