import requests
import os
import sqlite3
import json
import shutil
import re  # Import the 're' module for regular expressions

# Constants
BASE_URL_TEMPLATE = 'https://script.google.com/macros/s/{deployment_id}/exec?action=read&sheet={endpoint}'
REQUIREMENTS_FILE = 'requirements.txt'
RESPONSES_DIR = 'api_responses'
DATABASE_FILE = 'database/database.db'
VERSION_FILE = 'db_version'
BACKUP_DIR = 'api_responses_backup'

# Ensure directories exist
os.makedirs(RESPONSES_DIR, exist_ok=True)
os.makedirs('database', exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)

def call_apis_and_store():
    with open(REQUIREMENTS_FILE, 'r') as f:
        lines = f.readlines()

    for line in lines:
        github_secret_name, endpoint = line.strip().split(',')
        deployment_id = os.getenv(github_secret_name)
        if deployment_id:
            url = BASE_URL_TEMPLATE.format(deployment_id=deployment_id, endpoint=endpoint)
             print(f"Data for endpoint '{url}'")
            response = requests.get(url)
             print(f"'{endpoint}' ==> '{url}'")
            if response.status_code == 200:
                file_path = os.path.join(RESPONSES_DIR, f"{endpoint}.json")
                with open(file_path, 'w') as f:
                    f.write(response.text)
                print(f"Data for endpoint '{endpoint}' fetched and stored.")
            else:
                print(f"Failed to fetch data from {url}")
        else:
            print(f"No deployment ID found for GitHub secret variable '{github_secret_name}'")

def create_db_from_responses():
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    for filename in os.listdir(RESPONSES_DIR):
        if filename.endswith(".json"):
            table_name = filename.split('.')[0]
            table_name = re.sub(r'\W+', '_', table_name)
            with open(os.path.join(RESPONSES_DIR, filename), 'r') as f:
                data = json.load(f)
            
            if data and isinstance(data, list) and len(data) > 0:
                keys = data[0].keys()
                columns = ", ".join([f"{key} TEXT" for key in keys])
                cursor.execute(f"DROP TABLE IF EXISTS '{table_name}'")
                cursor.execute(f"CREATE TABLE '{table_name}' ({columns})")
                
                placeholders = ", ".join(["?" for _ in keys])
                for record in data:
                    values = tuple(record.get(key, '') for key in keys)
                    cursor.execute(f"INSERT INTO '{table_name}' VALUES ({placeholders})", values)
                print(f"Table '{table_name}' created and data inserted.")
            else:
                print(f"No data or empty data to insert for table '{table_name}'.")

    conn.commit()
    conn.close()

def update_version_file():
    if not os.path.exists(VERSION_FILE):
        with open(VERSION_FILE, 'w') as f:
            f.write("1.0.0")
        return "1.0.0"
    
    with open(VERSION_FILE, 'r') as f:
        version = f.read().strip()
    
    if not version or not all(part.isdigit() for part in version.split('.')):
        version = "1.0.0"
    
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
    
    return new_version

def compare_and_backup():
    changes_detected = False
    existing_files = os.listdir(BACKUP_DIR)
    
    for filename in os.listdir(RESPONSES_DIR):
        new_file = os.path.join(RESPONSES_DIR, filename)
        existing_file = os.path.join(BACKUP_DIR, filename)

        if not os.path.exists(existing_file) or \
                (os.path.getsize(new_file) != os.path.getsize(existing_file)) or \
                (os.path.getmtime(new_file) != os.path.getmtime(existing_file)):
            changes_detected = True
            break

    if changes_detected:
        create_db_from_responses()
        new_version = update_version_file()
        print(f"Database updated to version {new_version}")

        for filename in os.listdir(RESPONSES_DIR):
            new_file = os.path.join(RESPONSES_DIR, filename)
            backup_file = os.path.join(BACKUP_DIR, filename)
            shutil.copyfile(new_file, backup_file)
    else:
        print("No changes detected. Database and version file not updated.")

def main():
    call_apis_and_store()
    compare_and_backup()

if __name__ == "__main__":
    main()
