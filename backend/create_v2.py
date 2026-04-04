import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

try:
    conn = psycopg2.connect(
        dbname='postgres', 
        user='postgres', 
        password='admin123', 
        host='127.0.0.1',
        port='5433' 
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()

    print("Creating brand new database: sangi_v2...")
    cursor.execute("CREATE DATABASE sangi_v2;")

    cursor.close()
    conn.close()
    print("✅ sangi_v2 created successfully! The slate is perfectly clean.")

except Exception as e:
    print(f"❌ Error: {e}")