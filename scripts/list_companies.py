import sqlite3, os
DB = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'instance', 'database.db'))
print('DB:', DB)
conn = sqlite3.connect(DB)
cur = conn.cursor()
cur.execute('PRAGMA table_info(company)')
print('schema:', [r[1] for r in cur.fetchall()])
cur.execute('SELECT id, name, manager_id, is_admin_created, encrypted_password, blocked FROM company ORDER BY id')
rows = cur.fetchall()
for r in rows:
    print(r)
conn.close()
