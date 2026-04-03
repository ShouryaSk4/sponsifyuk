import sqlite3
import traceback

def recreate_fts():
    conn = sqlite3.connect('jobs.db')
    c = conn.cursor()
    try:
        # Drop if exists
        c.execute("DROP TABLE IF EXISTS jobs_fts")
        c.execute("DROP TRIGGER IF EXISTS jobs_ai")
        c.execute("DROP TRIGGER IF EXISTS jobs_au")
        c.execute("DROP TRIGGER IF EXISTS jobs_ad")
        
        print("Creating jobs_fts virtual table...")
        c.execute('''
            CREATE VIRTUAL TABLE jobs_fts USING fts5(
                job_title,
                organisation_name,
                location,
                salary,
                remote_type,
                experience_level,
                content=jobs,
                content_rowid=id
            )
        ''')
        
        print("Populating initial data...")
        c.execute('''
            INSERT INTO jobs_fts(rowid, job_title, organisation_name, location, salary, remote_type, experience_level)
            SELECT id, job_title, organisation_name, location, salary, remote_type, experience_level FROM jobs
        ''')
        
        print("Creating AFTER INSERT trigger...")
        c.execute('''
            CREATE TRIGGER jobs_ai AFTER INSERT ON jobs BEGIN
              INSERT INTO jobs_fts(rowid, job_title, organisation_name, location, salary, remote_type, experience_level)
              VALUES (new.id, new.job_title, new.organisation_name, new.location, new.salary, new.remote_type, new.experience_level);
            END;
        ''')
        
        print("Creating AFTER DELETE trigger...")
        c.execute('''
            CREATE TRIGGER jobs_ad AFTER DELETE ON jobs BEGIN
              INSERT INTO jobs_fts(jobs_fts, rowid, job_title, organisation_name, location, salary, remote_type, experience_level)
              VALUES ('delete', old.id, old.job_title, old.organisation_name, old.location, old.salary, old.remote_type, old.experience_level);
            END;
        ''')

        print("Creating AFTER UPDATE trigger...")
        c.execute('''
            CREATE TRIGGER jobs_au AFTER UPDATE ON jobs BEGIN
              INSERT INTO jobs_fts(jobs_fts, rowid, job_title, organisation_name, location, salary, remote_type, experience_level)
              VALUES ('delete', old.id, old.job_title, old.organisation_name, old.location, old.salary, old.remote_type, old.experience_level);
              INSERT INTO jobs_fts(rowid, job_title, organisation_name, location, salary, remote_type, experience_level)
              VALUES (new.id, new.job_title, new.organisation_name, new.location, new.salary, new.remote_type, new.experience_level);
            END;
        ''')
        
        conn.commit()
        print("FTS index and triggers recreated successfully!")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
        traceback.print_exc()
    except Exception as e:
        print(f"Exception: {e}")
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == '__main__':
    recreate_fts()
    
