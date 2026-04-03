import sqlite3
import random
import string
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

DB_PATH = 'jobs.db'
NUM_WORKERS = 100
DURATION_SECONDS = 10

def random_string(length=10):
    return ''.join(random.choices(string.ascii_letters, k=length))

def worker_task(worker_id, stop_flag):
    """
    Worker function that continuously performs random reads and writes 
    to stress the DB locking mechanisms.
    """
    reads = 0
    writes = 0
    errors = 0
    error_msgs = []

    # Each worker gets its own connection
    # timeout handles lock waiting
    conn = sqlite3.connect(DB_PATH, timeout=1.0, isolation_level=None) 
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=1000;")
    cursor = conn.cursor()

    while not stop_flag[0]:
        try:
            # Randomly decide to Read (80%) or Write (20%)
            if random.random() < 0.8:
                # READ
                max_retries = 5
                for attempt in range(max_retries):
                    try:
                        cursor.execute("SELECT COUNT(*) FROM jobs")
                        cursor.fetchone()
                        reads += 1
                        break
                    except sqlite3.OperationalError as e:
                        if "database is locked" in str(e):
                            errors += 1
                            if attempt < max_retries - 1:
                                time.sleep(0.05 * (2 ** attempt))
                            else:
                                error_msgs.append("Max retries reached on lock (read)")
                        else:
                            error_msgs.append(str(e))
                            errors += 1
                            break
                    except Exception as e:
                        error_msgs.append(f"Other error: {str(e)}")
                        errors += 1
                        break
            else:
                # WRITE
                job_id = random.randint(1, 4000)
                now_str = str(time.time())
                
                max_retries = 5
                for attempt in range(max_retries):
                    try:
                        cursor.execute("BEGIN IMMEDIATE")
                        cursor.execute(
                            "UPDATE jobs SET last_health_check = ? WHERE id = ?",
                            (now_str, job_id)
                        )
                        conn.commit()
                        writes += 1
                        break # Success
                    except sqlite3.OperationalError as e:
                        if "database is locked" in str(e):
                            conn.rollback() # VERY IMPORTANT
                            errors += 1
                            if attempt < max_retries - 1:
                                time.sleep(0.05 * (2 ** attempt)) # Exponential backoff
                            else:
                                error_msgs.append("Max retries reached on lock")
                        else:
                            conn.rollback()
                            error_msgs.append(str(e))
                            errors += 1
                            break
                    except Exception as e:
                        conn.rollback()
                        error_msgs.append(f"Other error: {str(e)}")
                        errors += 1
                        break
                        
        except Exception as e:
             error_msgs.append(f"Other error: {str(e)}")
             errors += 1

    conn.close()
    return worker_id, reads, writes, errors, error_msgs

def main():
    print(f"Starting DB stress test with {NUM_WORKERS} concurrent workers for {DURATION_SECONDS} seconds...")
    print("This will test if WAL mode successfully prevents 'database is locked' errors under heavy load.")
    
    # We use a mutable list for the stop flag so threads can read the updated value
    stop_flag = [False]
    
    results = []
    
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
        # Submit all workers
        futures = {executor.submit(worker_task, i, stop_flag): i for i in range(NUM_WORKERS)}
        
        # Let them run for DURATION_SECONDS
        while time.time() - start_time < DURATION_SECONDS:
            time.sleep(0.5)
            
        print("Time up! Signaling workers to stop...")
        stop_flag[0] = True
        
        # Collect results
        for future in as_completed(futures):
            results.append(future.result())

    # Tally up
    total_reads = sum(r[1] for r in results)
    total_writes = sum(r[2] for r in results)
    total_lock_errors = sum(r[3] for r in results)
    
    print("\n--- STRESS TEST RESULTS ---")
    print(f"Total successful reads:  {total_reads}")
    print(f"Total successful writes: {total_writes}")
    print(f"Total DB LOCKED ERRS:    {total_lock_errors}")
    
    unique_errors = set()
    for r in results:
        unique_errors.update(r[4])
        
    if unique_errors:
        print("\nOther errors encountered:")
        for e in unique_errors:
            print(f" - {e}")

    if total_lock_errors == 0:
         print("\nSUCCESS: No database locks encountered! WAL mode is working perfectly.")
    else:
         print(f"\nFAILED: Encountered {total_lock_errors} lock errors. DB configuration still has issues.")

if __name__ == "__main__":
    main()
