import sqlite3
conn = sqlite3.connect('support_copilot.db')
cur = conn.cursor()
try:
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    print('Tables:', cur.fetchall())
    try:
        cur.execute('SELECT count(*) FROM users')
        print('User count:', cur.fetchone()[0])
    except Exception as e:
        print('Error querying users table:', e)
except Exception as e:
    print('Error opening DB:', e)
finally:
    conn.close()
