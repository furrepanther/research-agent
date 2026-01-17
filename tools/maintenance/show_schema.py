import sqlite3

conn = sqlite3.connect(r'R:\My Drive\03 Research Papers\metadata.db')
cursor = conn.cursor()

print("=" * 80)
print("DATABASE SCHEMA - metadata.db")
print("=" * 80)

# Get all tables
cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

for table_name, table_sql in tables:
    print(f"\nTable: {table_name}")
    print("-" * 80)
    if table_sql:
        print(table_sql)
    print()

# Get row counts
print("\n" + "=" * 80)
print("TABLE ROW COUNTS")
print("=" * 80)
for table_name, _ in tables:
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cursor.fetchone()[0]
    print(f"{table_name}: {count} rows")

conn.close()
