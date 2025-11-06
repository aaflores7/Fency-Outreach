FENCY OUTREACH - AUTOMATED DATA PIPELINE


OVERVIEW
--------

This project implements a robust, three-stage automated data pipeline designed to ingest property and owner data, enrich it with contact information, and verify the validity of the found email addresses. The entire workflow is built to be resilient, auditable, and scalable.

The pipeline processes data in the following sequence:
1.  **Ingestion**: Fetches property and owner data from the PropertyRadar API.
2.  **Enrichment**: Enriches owner profiles using the People Data Labs (PDL) API to find potential email addresses.
3.  **Verification**: Verifies the enriched emails using two separate services, MillionVerifier and NeverBounce, to ensure high accuracy.


FEATURES
--------

*   **Automated Ingestion**: Regularly fetches new property and owner records from a specified PropertyRadar list.
*   **Intelligent Contact Enrichment**: Uses a multi-parameter query (name, address, phone, etc.) to get the highest quality matches from People Data Labs.
*   **Dual-Service Verification**: Cross-references email validity with both MillionVerifier and NeverBounce to reduce false positives and negatives.
*   **State-Driven Workflow**: The entire pipeline is managed by a "state machine" using a `processing_status` field in the database, ensuring each record is processed correctly and no steps are missed.
*   **Resilient Error Handling**: Includes pre-flight validation to avoid bad API calls and a retry mechanism to handle temporary network failures.
*   **Comprehensive Auditing**: Stores the full, raw JSON responses from all API services in the database for easy debugging and auditing.
*   **Modular & Scalable Architecture**: The code is separated by concern (API clients, workers, config), making it easy to maintain, test, and extend.


ARCHITECTURE & WORKFLOW
-----------------------

The pipeline's core logic is driven by a state machine managed by the `processing_status` column in the `owners` table. Each worker is responsible for handling records in a specific state and transitioning them to the next.

The flow is as follows:

1.  **Ingestion Worker (`ingest_worker.py`)**:
    - Fetches data from PropertyRadar.
    - Creates records in the `properties` and `owners` tables.
    - Sets the initial `processing_status` to:
        - `pending_verification` (if an original email was found).
        - `pending_enrichment` (if no original email was found).

2.  **Enrichment Worker (`enrichment_worker.py`)**:
    - Continuously queries for owners with `processing_status = 'pending_enrichment'`.
    - Calls the People Data Labs API to find emails.
    - If emails are found, it updates the `enriched_emails` column and sets `processing_status = 'pending_post_enrichment_verification'`.
    - If no emails are found or the call fails, it sets `processing_status = 'failed_enrichment'`.

3.  **Verification Worker (`verification_worker.py`)**:
    - Continuously queries for owners in `pending_verification` or `pending_post_enrichment_verification` status.
    - Iterates through the list of available emails for an owner.
    - Calls both the MillionVerifier and NeverBounce APIs for each email until a valid one is confirmed.
    - Updates the record with full API responses and sets the final `processing_status` to `complete` or `failed_verification`.


PROJECT STRUCTURE
-----------------

    /fency_outreach_pipeline/
    |-- workers/
    |   |-- ingest_worker.py
    |   |-- enrichment_worker.py
    |   `-- verification_worker.py
    |-- core/
    |   |-- database.py
    |   `-- api_clients/
    |       |-- property_radar_client.py
    |       |-- pdl_client.py
    |       `-- verifier_client.py
    |-- config.py
    |-- main.py
    |-- .env
    |-- .gitignore
    `-- requirements.txt


SETUP AND INSTALLATION
----------------------

Follow these steps to set up and run the project locally.

1.  **Prerequisites**:
    - Python 3.8+
    - pip

2.  **Clone the Repository**:
    git clone <your-repository-url>
    cd fency_outreach_pipeline

3.  **Set up a Virtual Environment** (Recommended):
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`

4.  **Install Dependencies**:
    pip install -r requirements.txt

5.  **Configure Environment Variables**:
    Create a file named `.env` in the root of the project directory. Copy and paste the following content into it, then fill in your actual API keys and credentials.

    ```ini
    # Supabase
    SUPABASE_URL="your-supabase-url"
    SUPABASE_KEY="your-supabase-key"

    # Property Radar
    PROPERTY_RADAR_API_KEY="your-pr-key"
    PROPERTY_RADAR_LIST_ID="your-list-id"

    # People Data Labs
    PDL_API_KEY="your-pdl-key"

    # Verification Services
    MILLIONVERIFIER_API_KEY="your-millionverifier-key"
    NEVERBOUNCE_API_KEY="secret_your-neverbounce-v4-key"
    ```

6.  **Set up the Database**:
    - Ensure you have a Supabase project created.
    - Run the SQL schema provided in the `database_schema.sql` file in the Supabase SQL Editor to create the `properties` and `owners` tables and their related functions/triggers.


HOW TO RUN
----------

The project includes a master orchestrator script, `main.py`, which acts as a command-line interface (CLI) to run the different workers.

**Important Note for the First Run:**
For the initial data population, you must run the workers in sequence.

1.  **Run the Ingestion Worker**: This will populate the database. It will run once and then exit.
    ```bash
    python main.py ingest
    ```

2.  **Run the Enrichment Worker**: This will start a long-running process to enrich the new records.
    ```bash
    python main.py enrich
    ```

3.  **Run the Verification Worker**: In a separate terminal, start this long-running process to verify the enriched records.
    ```bash
    python main.py verify
    ```


DEPLOYMENT & AUTOMATION
-----------------------

To run this pipeline in a production environment, you should:

1.  **Schedule Ingestion**: The `ingest` worker should be scheduled to run periodically (e.g., once a day) using a `cron` job (on Linux/macOS) or the Task Scheduler (on Windows).

2.  **Run Workers as Services**: The `enrich` and `verify` workers are designed to run continuously. They should be deployed to a cloud server (e.g., AWS EC2, DigitalOcean) and managed by a process supervisor like `systemd` or `supervisor`. This ensures they are always running and will be restarted automatically if they crash.
