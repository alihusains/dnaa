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

# Ensure directories exist
os.makedirs(RESPONSES_DIR, exist_ok=True)
os.makedirs('database', exist_ok=True)

def get_deployment_ids():
    deployment_ids = []
    for key, value in os.environ.items():
        if key.startswith('DEPLOYMENT_ID_'):
            deployment_ids.append(value)
    return deployment_ids


# def call_apis_and_store():
#     with open(REQUIREMENTS_FILE, 'r') as f:
#         lines = f.readlines()

#     for line in lines:
#         github_secret_name, endpoint = line.strip().split(',')
#         deployment_id = os.getenv(github_secret_name)
#         if deployment_id:
#             url = BASE_URL_TEMPLATE.format(deployment_id=deployment_id, endpoint=endpoint)
#             response = requests.get(url)
#             if response.status_code == 200:
#                 file_path = os.path.join(RESPONSES_DIR, f"{endpoint}.json")
#                 with open(file_path, 'w') as f:
#                     f.write(response.text)
#             else:
#                 print(f"Failed to fetch data from {url}")
#         else:
#             print(f"No deployment ID found for GitHub secret variable '{github_secret_name}'")




def call_apis_and_store():
    with open(REQUIREMENTS_FILE, 'r') as f:
        lines = f.readlines()

    for line in lines:
        github_secret_name, endpoint = line.strip().split(',')
        deployment_id = os.getenv(github_secret_name)
        if deployment_id:
            url = BASE_URL_TEMPLATE.format(deployment_id=deployment_id, endpoint=endpoint)
            response = requests.get(url)
            if response.status_code == 200:
                file_path = os.path.join(RESPONSES_DIR, f"{endpoint}.json")
                with open(file_path, 'w') as f:
                    f.write(response.text)
            else:
                print(f"Failed to fetch data from {url}")
        else:
            print(f"No deployment ID found for GitHub secret variable '{github_secret_name}'")


# def create_db_from_responses():
#     conn = sqlite3.connect(DATABASE_FILE)
#     cursor = conn.cursor()

#     for filename in os.listdir(RESPONSES_DIR):
#         if filename.endswith(".json"):
#             table_name = filename.split('.')[0]
#             # Sanitize table name to comply with SQLite's naming rules
#             table_name = re.sub(r'\W+', '_', table_name)
#             with open(os.path.join(RESPONSES_DIR, filename), 'r') as f:
#                 data = json.load(f)
            
#             if data and isinstance(data, list) and len(data) > 0:
#                 # Check if the JSON response is not empty and contains records
#                 # Extract all keys from the first record
#                 keys = data[0].keys()
#                 # Generate column names and types for SQL table creation
#                 columns = ", ".join([f"{key} TEXT" for key in keys])
#                 cursor.execute(f"DROP TABLE IF EXISTS '{table_name}'")  # Use single quotes to handle special characters
#                 cursor.execute(f"CREATE TABLE '{table_name}' ({columns})")  # Use single quotes to handle special characters
                
#                 placeholders = ", ".join(["?" for _ in keys])
#                 for record in data:
#                     values = tuple(record.get(key, '') for key in keys)  # Use .get() to handle missing keys
#                     cursor.execute(f"INSERT INTO '{table_name}' VALUES ({placeholders})", values)  # Use single quotes to handle special characters
#                 print(f"Table '{table_name}' created and data inserted.")
#             else:
#                 print(f"No data or empty data to insert for table '{table_name}'.")

#     conn.commit()
#     conn.close()

def create_db_from_responses():
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    for filename in os.listdir(RESPONSES_DIR):
        if filename.endswith(".json"):
            table_name = filename.split('.')[0]
            # Sanitize table name to comply with SQLite's naming rules
            table_name = re.sub(r'\W+', '_', table_name)
            with open(os.path.join(RESPONSES_DIR, filename), 'r') as f:
                data = json.load(f)
            
            if data and isinstance(data, list) and len(data) > 0:
                # Check if the JSON response is not empty and contains records
                # Extract all keys from the first record
                keys = data[0].keys()
                # Generate column names and types for SQL table creation
                columns = ", ".join([f"{key} TEXT" for key in keys])
                cursor.execute(f"DROP TABLE IF EXISTS '{table_name}'")  # Use single quotes to handle special characters
                cursor.execute(f"CREATE TABLE '{table_name}' ({columns})")  # Use single quotes to handle special characters
                
                placeholders = ", ".join(["?" for _ in keys])
                for record in data:
                    values = tuple(record.get(key, '') for key in keys)  # Use .get() to handle missing keys
                    cursor.execute(f"INSERT INTO '{table_name}' VALUES ({placeholders})", values)  # Use single quotes to handle special characters
                print(f"Table '{table_name}' created and data inserted.")
            else:
                print(f"No data or empty data to insert for table '{table_name}'.")

    # Once all tables are created and data inserted, commit the changes and close the connection
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

def main():
    # Step 1: Call APIs and store responses
    call_apis_and_store()

    # Step 2: Compare new responses with existing ones
    changes_detected = False
    existing_files = os.listdir('api_responses_backup')
    for filename in os.listdir(RESPONSES_DIR):
        new_file = os.path.join(RESPONSES_DIR, filename)
        existing_file = os.path.join('api_responses_backup', filename)

        # Compare files by size and modification time
        if not os.path.exists(existing_file) or \
                (os.path.getsize(new_file) != os.path.getsize(existing_file)) or \
                (os.path.getmtime(new_file) != os.path.getmtime(existing_file)):
            changes_detected = True
            break

    if changes_detected:
        # Step 3: Create or update the database
        create_db_from_responses()

        # Step 4: Update the version file
        new_version = update_version_file()
        print(f"Database updated to version {new_version}")

        # Backup the current API responses for future comparisons
        os.makedirs('api_responses_backup', exist_ok=True)
        for filename in os.listdir(RESPONSES_DIR):
            new_file = os.path.join(RESPONSES_DIR, filename)
            backup_file = os.path.join('api_responses_backup', filename)
            shutil.copyfile(new_file, backup_file)
    else:
        print("No changes detected. Database and version file not updated.")


if __name__ == "__main__":
    main()
