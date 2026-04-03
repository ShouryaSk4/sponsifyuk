import sqlite3

conn = sqlite3.connect('jobs.db')
cur = conn.cursor()

# Find all duplicate IDs to deactivate (keep lowest ID per group active)
cur.execute("""
    SELECT GROUP_CONCAT(id ORDER BY id) AS ids
    FROM jobs
    GROUP BY LOWER(TRIM(job_title)), LOWER(TRIM(organisation_name))
    HAVING COUNT(*) > 1
""")

rows = cur.fetchall()
ids_to_deactivate = []

for r in rows:
    all_ids = r[0].split(',')
    # Keep the first (lowest) ID, deactivate the rest
    ids_to_deactivate.extend(all_ids[1:])

ids_to_deactivate = [int(i) for i in ids_to_deactivate]

# Deactivate them
placeholders = ','.join('?' * len(ids_to_deactivate))
cur.execute(f"UPDATE jobs SET is_active = 0 WHERE id IN ({placeholders})", ids_to_deactivate)
conn.commit()

print(f"Deactivated {cur.rowcount} duplicate job listings.")
conn.close()
