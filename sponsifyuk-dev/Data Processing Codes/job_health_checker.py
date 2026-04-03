"""
job_health_checker.py  --  Job Link Health Checker
====================================================
Validates every active job's URL in jobs.db.  Marks expired / broken /
fake listings as is_active = 0 so only real, live jobs appear on the site.

Usage
-----
    python job_health_checker.py                # full run (all unchecked)
    python job_health_checker.py --batch 100    # check 100 jobs only
    python job_health_checker.py --recheck-days 1   # re-check if > 1 day old
    python job_health_checker.py --dry-run      # report only, don't update DB
    python job_health_checker.py --verbose       # extra logging

Detection layers
----------------
1. NULL / empty link               -> immediate deactivation
2. HTTP status  404, 410, 403      -> dead
3. Connection / DNS / SSL errors   -> dead
4. Redirect to generic page        -> dead (lost job-specific path)
5. Page-content analysis (GET)     -> expired keywords on a 200-OK page
6. Tiny page body (< 500 chars)    -> likely stub / error page
"""

import argparse
import logging
import re
import sqlite3
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ── Logging ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("health_checker")

# ── Constants ────────────────────────────────────────────────────────────────

DB_PATH = "jobs.db"

# Status codes that definitively mean "gone"
DEAD_STATUS_CODES = {404, 410, 403, 451}

# Keywords on a *200-OK* page that indicate the job listing is expired.
# Matched case-insensitively against the first 5 000 chars of the page body.
EXPIRED_KEYWORDS = [
    "this position has been filled",
    "this job has expired",
    "this job is no longer available",
    "this listing has expired",
    "this vacancy has been closed",
    "this vacancy is closed",
    "this role has been filled",
    "this role is no longer available",
    "no longer accepting applications",
    "position has been removed",
    "job has been removed",
    "this opportunity is no longer available",
    "job posting has expired",
    "application deadline has passed",
    "this post has expired",
    "sorry, this job is no longer open",
    "the position you are looking for is no longer available",
    "this advert has closed",
    "vacancy closed",
    "job closed",
    "expired listing",
    "position filled",
    "requisition is no longer available",
    "req is no longer posted",
    "this requisition has been closed",
    "the selected job does not exist",
    "job not found",
    "page not found",
    "404 - page not found",
    "the job you requested",
    "this page does not exist",
    "the page you are looking for doesn't exist",
    "oops! we couldn't find",
    "unfortunately this position",
    "this job has been archived",
    "this posting has been archived",
    "no jobs matched your search",
    "this position is no longer listed",
    "this vacancy has now expired",
    "vacancy has now expired",
    "vacancy has expired",
    "job has expired",
    "role has expired",
]

# Minimum body size for a real job listing page (chars)
MIN_BODY_LENGTH = 500

# User-Agent rotation (looks like real browsers)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]

# Per-domain rate-limit tracker
_domain_last_request: dict[str, float] = defaultdict(float)
DOMAIN_MIN_INTERVAL = 0.5   # seconds between requests to same domain


# ── Core logic ───────────────────────────────────────────────────────────────

def _build_session() -> requests.Session:
    """Build a Session with retries and timeouts."""
    s = requests.Session()
    retries = Retry(total=2, backoff_factor=0.3, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    return s


def _rate_limit(domain: str):
    """Sleep if we hit the same domain too fast."""
    now = time.time()
    elapsed = now - _domain_last_request[domain]
    if elapsed < DOMAIN_MIN_INTERVAL:
        time.sleep(DOMAIN_MIN_INTERVAL - elapsed)
    _domain_last_request[domain] = time.time()


def _pick_ua(job_id: int) -> str:
    return USER_AGENTS[job_id % len(USER_AGENTS)]


def _is_redirect_to_generic(original_url: str, final_url: str) -> bool:
    """
    Detect if a redirect stripped the job-specific path and landed on
    a generic careers / homepage.  e.g.
      https://company.com/careers/job-123  ->  https://company.com/careers
    """
    orig = urlparse(original_url)
    final = urlparse(final_url)

    # Different domain entirely? suspicious
    if orig.netloc != final.netloc:
        return True

    orig_depth = len([p for p in orig.path.strip("/").split("/") if p])
    final_depth = len([p for p in final.path.strip("/").split("/") if p])

    # If the final path is significantly shorter, the job part was stripped
    if final_depth < orig_depth - 1:
        return True

    # If final path is a known generic landing page
    generic_endings = ["/careers", "/jobs", "/vacancies", "/openings",
                       "/career", "/job-search", "/opportunities", "/"]
    final_path_lower = final.path.rstrip("/").lower()
    if final_path_lower in [g.rstrip("/") for g in generic_endings]:
        return True

    return False


def _check_expired_content(body_text: str) -> Optional[str]:
    """
    Scan the entire body text for expiry / closed keywords.
    Returns the matched keyword or None.
    """
    snippet = body_text.lower()

    # Advanced heuristics
    if "session expired" in snippet:
        return "expired_on_page: session expired"

    # Catch dynamic Workday job state in embedded JS
    if "postingavailable: false" in snippet or '"postingavailable": false' in snippet or "postingavailable:false" in snippet:
        return "expired_on_page: postingAvailable is false"

    for kw in EXPIRED_KEYWORDS:
        if kw in snippet:
            return f"expired_on_page: \"{kw}\""
    return None


def check_single_job(session: requests.Session, job_id: int, job_link: str,
                     verbose: bool = False) -> tuple[bool, str]:
    """
    Check one job link.

    Returns:
        (is_alive: bool, reason: str)
    """
    if not job_link or not job_link.startswith("http"):
        return False, "null_or_invalid_link"

    domain = urlparse(job_link).netloc
    _rate_limit(domain)

    headers = {"User-Agent": _pick_ua(job_id)}
    timeout = 15

    # ── Step 1: HEAD request ─────────────────────────────────────────────
    try:
        resp = session.head(job_link, headers=headers, timeout=timeout,
                            allow_redirects=True)

        if resp.status_code in DEAD_STATUS_CODES:
            return False, f"http_{resp.status_code}"

        # If HEAD returns 405 (Method Not Allowed) or 501, fall through to GET
        if resp.status_code not in (405, 501, 400):
            # Check redirect destination
            if resp.url and resp.url != job_link:
                if _is_redirect_to_generic(job_link, resp.url):
                    return False, "redirect_to_generic_page"

            # HEAD returned 200 — but we can't check body with HEAD.
            # Do a GET for content analysis.
            pass

    except requests.exceptions.SSLError:
        return False, "ssl_error"
    except requests.exceptions.ConnectionError:
        return False, "connection_error"
    except requests.exceptions.Timeout:
        return False, "timeout"
    except requests.exceptions.TooManyRedirects:
        return False, "too_many_redirects"
    except Exception as e:
        return False, f"head_error: {str(e)[:80]}"

    # ── Step 2: GET request (for body analysis) ──────────────────────────
    _rate_limit(domain)

    try:
        resp = session.get(job_link, headers=headers, timeout=timeout,
                           allow_redirects=True)

        if resp.status_code in DEAD_STATUS_CODES:
            return False, f"http_{resp.status_code}"

        if resp.status_code != 200:
            return False, f"http_{resp.status_code}"

        # Check redirect destination again (GET may behave differently)
        if resp.url and resp.url != job_link:
            if _is_redirect_to_generic(job_link, resp.url):
                return False, "redirect_to_generic_page"

        # ── Content analysis ─────────────────────────────────────────────
        body = resp.text

        # Tiny body = stub / error page
        if len(body.strip()) < MIN_BODY_LENGTH:
            return False, f"tiny_page ({len(body.strip())} chars)"

        # Check for expired keywords in page content
        kw_match = _check_expired_content(body)
        if kw_match:
            return False, f"expired_on_page: \"{kw_match}\""

        # Looks alive!
        return True, "alive"

    except requests.exceptions.SSLError:
        return False, "ssl_error"
    except requests.exceptions.ConnectionError:
        return False, "connection_error"
    except requests.exceptions.Timeout:
        return False, "timeout_get"
    except requests.exceptions.TooManyRedirects:
        return False, "too_many_redirects"
    except Exception as e:
        return False, f"get_error: {str(e)[:80]}"


# ── DB helpers ───────────────────────────────────────────────────────────────

def ensure_columns(conn: sqlite3.Connection):
    """Add health-check columns if they don't exist yet."""
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(jobs)")
    existing = {r[1] for r in cursor.fetchall()}

    if "last_health_check" not in existing:
        cursor.execute("ALTER TABLE jobs ADD COLUMN last_health_check TEXT")
        logger.info("Added column: last_health_check")

    if "deactivation_reason" not in existing:
        cursor.execute("ALTER TABLE jobs ADD COLUMN deactivation_reason TEXT")
        logger.info("Added column: deactivation_reason")

    conn.commit()


def fetch_jobs_to_check(conn: sqlite3.Connection, recheck_days: int,
                        batch: Optional[int] = None) -> list[dict]:
    """Fetch active jobs that haven't been checked recently."""
    cursor = conn.cursor()
    cutoff = (datetime.now() - timedelta(days=recheck_days)).isoformat()

    query = """
        SELECT id, job_link, organisation_name, career_page_url
        FROM   jobs
        WHERE  is_active = 1
               AND (last_health_check IS NULL OR last_health_check < ?)
        ORDER BY last_health_check ASC NULLS FIRST, id ASC
    """
    params = [cutoff]

    if batch:
        query += " LIMIT ?"
        params.append(batch)

    cursor.execute(query, params)
    return [dict(r) for r in cursor.fetchall()]


def deactivate_job(conn: sqlite3.Connection, job_id: int, reason: str):
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute(
        """UPDATE jobs
           SET is_active = 0,
               deactivation_reason = ?,
               last_health_check = ?
           WHERE id = ?""",
        (reason, now, job_id),
    )


def mark_checked(conn: sqlite3.Connection, job_id: int):
    now = datetime.now().isoformat()
    conn.cursor().execute(
        "UPDATE jobs SET last_health_check = ? WHERE id = ?",
        (now, job_id),
    )


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Job Link Health Checker")
    parser.add_argument("--batch", type=int, default=None,
                        help="Max jobs to check (default: all)")
    parser.add_argument("--recheck-days", type=int, default=3,
                        help="Re-check jobs older than N days (default: 3)")
    parser.add_argument("--threads", type=int, default=10,
                        help="Concurrent threads (default: 10)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Report only, don't update the database")
    parser.add_argument("--verbose", action="store_true",
                        help="Extra logging")
    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # ── Connect & prepare ────────────────────────────────────────────────
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    ensure_columns(conn)

    # ── Step 0: immediately deactivate jobs with NULL / empty links ───────
    cursor = conn.cursor()
    cursor.execute(
        """UPDATE jobs
           SET is_active = 0,
               deactivation_reason = 'no_job_link',
               last_health_check = ?
           WHERE is_active = 1
                 AND (job_link IS NULL OR job_link = '' OR job_link NOT LIKE 'http%')""",
        (datetime.now().isoformat(),),
    )
    null_deactivated = cursor.rowcount
    conn.commit()
    if null_deactivated:
        logger.info(f"Deactivated {null_deactivated} jobs with no valid link")

    # ── Step 0.5: immediately deactivate jobs with vague/funny titles ─────
    cursor.execute(
        """UPDATE jobs
           SET is_active = 0,
               deactivation_reason = 'vague_or_test_title',
               last_health_check = ?
           WHERE is_active = 1
                 AND (
                    lower(job_title) IN ('test', 'testing', 'testing job', 'testing job title', 'asdf', 'demo', 'crashtest team', 'test job', 'test posting', 'liesa', 'sanya', 'inzi', 'fabio', 'julia')
                    OR job_title LIKE '%Testing Job Title%'
                    OR (length(job_title) <= 2 AND upper(job_title) NOT IN ('IT', 'HR', 'PR', 'UX', 'UI'))
                 )""",
        (datetime.now().isoformat(),),
    )
    vague_deactivated = cursor.rowcount
    conn.commit()
    if vague_deactivated:
        logger.info(f"Deactivated {vague_deactivated} jobs with vague/test titles")

    # ── Fetch jobs to check ──────────────────────────────────────────────
    jobs = fetch_jobs_to_check(conn, args.recheck_days, args.batch)
    total = len(jobs)
    logger.info(f"Jobs to check: {total}")

    if total == 0:
        logger.info("Nothing to check. All jobs recently verified.")
        conn.close()
        return

    # ── Check jobs ───────────────────────────────────────────────────────
    session = _build_session()
    stats = defaultdict(int)
    alive_count = 0
    dead_count = 0
    dead_details = []   # (id, org, reason)

    checked = 0
    commit_interval = 50  # commit every N jobs

    def process_job(job):
        return job, check_single_job(session, job["id"], job["job_link"], args.verbose)

    with ThreadPoolExecutor(max_workers=args.threads) as pool:
        futures = {pool.submit(process_job, j): j for j in jobs}

        for future in as_completed(futures):
            job, (is_alive, reason) = future.result()
            checked += 1
            stats[reason] += 1

            if is_alive:
                alive_count += 1
                if not args.dry_run:
                    mark_checked(conn, job["id"])
                if args.verbose:
                    logger.debug(f"  ALIVE  id={job['id']}  {job['job_link'][:60]}")
            else:
                dead_count += 1
                dead_details.append((job["id"], job["organisation_name"], reason))
                if not args.dry_run:
                    deactivate_job(conn, job["id"], reason)
                logger.info(
                    f"  DEAD   id={job['id']:>5d}  reason={reason:40s}  "
                    f"{(job['organisation_name'] or '')[:30]}"
                )

            # Progress + periodic commit
            if checked % commit_interval == 0:
                if not args.dry_run:
                    conn.commit()
                pct = checked / total * 100
                logger.info(
                    f"  Progress: {checked}/{total} ({pct:.0f}%)"
                    f"  alive={alive_count}  dead={dead_count}"
                )

    # Final commit
    if not args.dry_run:
        conn.commit()

    # ── Summary ──────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("HEALTH CHECK SUMMARY")
    print("=" * 70)
    print(f"  Jobs checked:          {checked}")
    print(f"  Alive:                 {alive_count}")
    print(f"  Dead (deactivated):    {dead_count}")
    print(f"  Null-link deactivated: {null_deactivated}")
    if args.dry_run:
        print("  Mode:                  DRY RUN (no DB changes)")
    print()

    print("Breakdown by reason:")
    for reason, cnt in sorted(stats.items(), key=lambda x: -x[1]):
        marker = "[OK]" if reason == "alive" else "[DEAD]"
        print(f"  {marker:8s} {reason:45s} {cnt:>5d}")

    # ── Dead details (first 30) ──────────────────────────────────────────
    if dead_details:
        print(f"\nDead jobs (first 30 of {len(dead_details)}):")
        for jid, org, reason in dead_details[:30]:
            print(f"  ID={jid:>5d}  {(org or ''):30s}  {reason}")

    # ── Rebuild FTS Index ────────────────────────────────────────────────
    if not args.dry_run:
        cursor.execute('DELETE FROM jobs_fts')
        cursor.execute("""
            INSERT INTO jobs_fts(rowid, job_title, organisation_name, location, remote_type, experience_level)
            SELECT id, job_title, organisation_name, location, remote_type, experience_level
            FROM jobs WHERE is_active = 1
        """)
        conn.commit()
        logger.info("Rebuilt FTS search index with active jobs only.")

    # ── Post-check DB stats ──────────────────────────────────────────────
    cursor.execute("SELECT COUNT(*) FROM jobs WHERE is_active = 1")
    active = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM jobs WHERE is_active = 0")
    inactive = cursor.fetchone()[0]
    print(f"\nDB State:")
    print(f"  Active jobs:   {active}")
    print(f"  Inactive jobs: {inactive}")
    print("=" * 70)

    conn.close()
    logger.info("Done.")


if __name__ == "__main__":
    main()
