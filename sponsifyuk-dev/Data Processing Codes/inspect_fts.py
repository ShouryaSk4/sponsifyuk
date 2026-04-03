import sqlite3
conn = sqlite3.connect('jobs.db')
c = conn.cursor()
c.execute("SELECT name, sql FROM sqlite_master WHERE type IN ('table', 'trigger') AND name LIKE '%fts%'")
for r in c.fetchall():
    print(r[0])
    print(r[1])
    print("-" * 40)
