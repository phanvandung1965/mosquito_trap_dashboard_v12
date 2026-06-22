
import sqlite3
import csv
import os

# Define paths
workspace_root = '/home/dung/.openclaw/workspace-VP2_codex/'
project_path = os.path.join(workspace_root, 'projects/mosquito_trap_dashboard')
db_path = os.path.join(project_path, 'data/mosquito_trap_dashboard.db')
csv_path = os.path.join(project_path, 'data/official/20260327_003727---b2d06196-ea4d-489c-a03a-0ab2a55182db.csv')
print(f"Database path: {db_path}")
print(f"CSV source path: {csv_path}")

# Table definition
table_name = 'raw_data'
# Read header from CSV to create table dynamically
try:
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        header = next(reader)
        # Sanitize column names for SQL
        sql_columns = [f'"{col.strip()}" TEXT' for col in header]
        create_table_sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(sql_columns)});"
        
except Exception as e:
    print(f"Error reading CSV header: {e}")
    exit(1)


# Connect to the database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # Drop the old table if it exists
    print(f"Dropping table '{table_name}' if it exists...")
    cursor.execute(f"DROP TABLE IF EXISTS {table_name};")

    # Create the new table
    print(f"Creating new table '{table_name}'...")
    print(create_table_sql)
    cursor.execute(create_table_sql)

    # Read CSV and insert data
    print(f"Reading data from {os.path.basename(csv_path)} and inserting into '{table_name}'...")
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        next(reader) # Skip header row
        
        # Prepare insert statement
        placeholders = ', '.join(['?'] * len(header))
        insert_sql = f"INSERT INTO {table_name} VALUES ({placeholders});"
        
        # Use executemany for performance
        cursor.executemany(insert_sql, reader)

    # Commit the transaction
    conn.commit()
    print(f"Successfully inserted {cursor.rowcount} records into '{table_name}'.")

    # Verification
    cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
    count = cursor.fetchone()[0]
    print(f"Verification: Table '{table_name}' now contains {count} rows.")

    cursor.execute(f"PRAGMA table_info({table_name});")
    print(f"\nTable Schema for '{table_name}':")
    for column in cursor.fetchall():
        print(column)

except Exception as e:
    print(f"An error occurred: {e}")
    conn.rollback()

finally:
    # Close the connection
    conn.close()
    print("Database connection closed.")
