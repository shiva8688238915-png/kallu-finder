import sqlite3

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE sellers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    address TEXT,
    phone TEXT,
    price TEXT,
    latitude REAL,
    longitude REAL,
    verified INTEGER DEFAULT 0,
    status TEXT DEFAULT 'unavailable'
)
''')

conn.commit()
conn.close()

print("Database created")