import sqlite3
import requests
from bs4 import BeautifulSoup
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import warnings

# Suppress noisy BeautifulSoup encoding warnings
warnings.filterwarnings("ignore", category=UserWarning, module='bs4')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = 'jobs.db'
NUM_WORKERS = 15

def get_job_description(url: str) -> tuple:
    """Fetches and cleans main description text. Returns (text, status_code_string)."""
    if not url or not url.startswith('http'):
        return None, "invalid_url"
        
    try:
        # Workday native JSON API bypass
        if "myworkdayjobs.com" in url:
            match = re.search(r'https://([^.]+)\.([^.]+)\.myworkdayjobs\.com/([^/]+)/([^/]+)/(job/.*)', url)
            if match:
                tenant, wd_sub, lang_or_site, site_or_job, job_path = match.groups()
                lang_pattern = re.compile(r'^[a-z]{2}(-[A-Z]{2})?$')
                jobsite = lang_or_site if not lang_pattern.match(lang_or_site) else site_or_job
                
                api_url = f"https://{tenant}.{wd_sub}.myworkdayjobs.com/wday/cxs/{tenant}/{jobsite}/{job_path}"
                wd_headers = {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                resp = requests.get(api_url, headers=wd_headers, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                html_desc = data.get('jobPostingInfo', {}).get('jobDescription', '')
                
                if html_desc:
                    # Pass from_encoding utf-8 to prevent unicode warnings on bytes
                    soup = BeautifulSoup(html_desc, 'html.parser')
                    text = soup.get_text(separator='\n', strip=True)
                    text = re.sub(r'\n{3,}', '\n\n', text)
                    if len(text) > 5000:
                        text = text[:5000] + "\n\n... [Truncated due to length]"
                    return text.strip(), "success"
                return None, "no_description_found"

        # Standard HTML fallback for non-Workday sites
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5'
        }
        response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove noisy elements
        for element in soup(["script", "style", "nav", "footer", "header", "aside", "noscript", "meta", "svg", "form"]):
            element.decompose()
            
        main_content = soup.find('main') or soup.find('article') or soup.find('div', class_=re.compile(r'content|job-description|details|body', re.I)) or soup.find('body')
        
        if not main_content:
            return None, "missing_main_container"
            
        text = main_content.get_text(separator='\n', strip=True)
        text = re.sub(r'\n{3,}', '\n\n', text)
        if len(text) > 5000:
            text = text[:5000] + "\n\n... [Truncated due to length]"
            
        return text.strip(), "success"
        
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code
        if status_code in (404, 410):
            return None, "expired"
        elif status_code in (403, 503):
            return None, "blocked_by_bot_protection"
        return None, f"http_error_{status_code}"
    except Exception as e:
        return None, f"error_{type(e).__name__}"

def process_job(job_id: int, url: str) -> tuple:
    description, status = get_job_description(url)
    return job_id, description, status

def main():
    logger.info("Connecting to database...")
    conn = sqlite3.connect(DB_PATH, timeout=10)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, job_link FROM jobs WHERE job_link IS NOT NULL AND (job_description IS NULL OR job_description = '') ORDER BY id DESC LIMIT 2000")
    jobs_to_process = cursor.fetchall()
    
    if not jobs_to_process:
        logger.info("No jobs found that need descriptions scraped!")
        conn.close()
        return
        
    logger.info(f"Found {len(jobs_to_process)} jobs to process. Starting {NUM_WORKERS} workers...")
    
    success_count = 0
    expired_count = 0
    blocked_count = 0
    other_fail_count = 0
    
    with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
        future_to_job = {executor.submit(process_job, job_id, url): job_id for job_id, url in jobs_to_process}
        
        for i, future in enumerate(as_completed(future_to_job), 1):
            job_id, description, status = future.result()
            
            if description and status == "success":
                cursor.execute("UPDATE jobs SET job_description = ? WHERE id = ?", (description, job_id))
                success_count += 1
                if success_count % 50 == 0:
                    conn.commit()
            elif status == "expired":
                expired_count += 1
            elif "blocked" in status:
                blocked_count += 1
            else:
                other_fail_count += 1
                
            if i % 100 == 0:
                logger.info(f"Progress: {i}/{len(jobs_to_process)} | Success: {success_count} | Expired: {expired_count} | Blocked: {blocked_count} | Failed: {other_fail_count}")

    conn.commit()
    conn.close()
    
    logger.info(f"Finished! Scraped: {success_count} | Expired (404/410): {expired_count} | Blocked: {blocked_count} | Other Error: {other_fail_count}")

if __name__ == "__main__":
    main()
