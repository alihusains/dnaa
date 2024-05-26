import requests
import os
import sqlite3
import json
from filecmp import cmp

# Constants
BASE_URL_TEMPLATE = 'https://script.google.com/macros/s/{deployment_id}/exec?action=read&sheet={endpoint}'
REQUIREMENTS_FILE = 'requirements.txt'
RESPONSES_DIR = 'api_responses'
DATABASE_FILE = 'database/database.db'
VERSION_FILE = 'db_version'

# Ensure directories exist
os.makedirs(RESPONSES_DIR, exist_ok=True)
os.makedirs('database', exist_ok=True)

def get_deployment_ids():
    deployment_ids = []
    for key, value in os.environ.items():
        if key.startswith('DEPLOYMENT_ID_'):
            deployment_ids.append(value)
    return deployment_ids

def call_apis_and_store():
    deployment_ids = get_deployment_ids()
    with open(REQUIREMENTS_FILE, 'r') as f:
        endpoints = f.readlines()

    for deployment_id in deployment_ids:
        for endpoint in endpoints:
            endpoint = endpoint.strip()
            url = BASE_URL_TEMPLATE.format(deployment_id=deployment_id, endpoint=endpoint)
            response = requests.get(url)
            if response.status_code == 200:
                file_path = os.path.join(RESPONSES_DIR, f"{deployment_id}_{endpoint}.json")
                with open(file_path, 'w') as f:
                    f.write(response.text)
            else:
                print(f"Failed to fetch data from {url}")

def create_db_from_responses():
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    for filename in os.listdir(RESPONSES_DIR):
        if filename.endswith(".json"):
            table_name = filename.split('.')[0]
            with open(os.path.join(RESPONSES_DIR, filename), 'r') as f:
                data = json.load(f)

            if data:
                columns = ", ".join(data[0].keys())
                cursor.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({columns})")
                for record in data:
                    values = ", ".join(f"'{v}'" for v in record.values())
                    cursor.execute(f"INSERT INTO {table_name} ({columns}) VALUES ({values})")

    conn.commit()
    conn.close()

def update_version_file():
    if not os.path.exists(VERSION_FILE):
        with open(VERSION_FILE, 'w') as f:
            f.write("1.0.0")
    else:
        with open(VERSION_FILE, 'r') as f:
            version = f.read().strip()
        major, minor, patch = map(int, version.split('.'))
        patch += 1
        if patch >= 10:
            patch = 0
            minor += 1
        if minor >= 10:
            minor = 0
            major += 1
        new_version = f"{major}.{minor}.{patch}"
        with open(VERSION_FILE, 'w') as f:
            f.write(new_version)

def main():
    # Step 1: Call APIs and store responses
    call_apis_and_store()

    # Step 2: Compare new responses with existing ones
    changes_detected = False
    for filename in os.listdir(RESPONSES_DIR):
        new_file = os.path.join(RESPONSES_DIR, filename)
        existing_file = os.path.join('api_responses_backup', filename)

        if not os.path.exists(existing_file) or not cmp(new_file, existing_file, shallow=False):
            changes_detected = True
            break

    if changes_detected:
        # Step 3: Create or update the database
        create_db_from_responses()

        # Step 4: Update the version file
        update_version_file()

        # Backup the current API responses for future comparisons
        os.makedirs('api_responses_backup', exist_ok=True)
        for filename in os.listdir(RESPONSES_DIR):
            new_file = os.path.join(RESPONSES_DIR, filename)
            backup_file = os.path.join('api_responses_backup', filename)
            with open(new_file, 'r') as f_new, open(backup_file, 'w') as f_backup:
                f_backup.write(f_new.read())
    else:
        print("No changes detected. Database and version file not updated.")

if __name__ == "__main__":
    main()
