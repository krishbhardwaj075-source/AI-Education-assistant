import sqlite3
conn=sqlite3.connect("database.db",check_same_thread=False)
cursor=conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT,
username TEXT,
email TEXT,
password TEXT,
streak INTEGER DEFAULT 0,
last_study TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS subjects(
id INTEGER PRIMARY KEY AUTOINCREMENT,
user_id INTEGER,
subject_name TEXT,
difficulty TEXT,
topics TEXT,
exam_date TEXT
)"""
)
try:
 cursor.execute("""ALTER TABLE subjects ADD COLUMN status TEXT DEFAULT 'pending'""")
except:
  pass 

cursor.execute("""
CREATE TABLE IF NOT EXISTS progress(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    day INTEGER,
    subject_name TEXT,
    status INTEGER,
    date TEXT
)
""")

conn.commit()