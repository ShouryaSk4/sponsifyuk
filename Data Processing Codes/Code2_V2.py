import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import time
import json
import re
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import sys
import ollama
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options
import pickle
import logging
from contextlib import contextmanager
import threading
import queue
import numpy as np

# ─────────────────────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler('scraper_debug.log', mode='w'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# FIX SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
# FIX 1 – Robust AI response parsing
#   Old: startswith() line-by-line matching that broke on any whitespace/
#        markdown from the LLM.
#   New: regex-based extraction that tolerates bold markers, extra spaces,
#        lowercase, trailing punctuation, etc.  If parsing still produces no
#        BEST_URL, the rule-based fallback is called automatically instead of
#        silently returning REJECT.
#
# FIX 2 – Workday scraper uses the public JSON API
#   Old: Selenium DOM walk that picked up stale React href placeholders
#        belonging to the wrong job.
#   New: POST to /wday/cxs/{tenant}/{jobsite}/jobs, parse the JSON response,
#        build the URL from base_url + externalPath.  No Selenium needed.
#        Pagination handled up to 200 jobs.  Workday jobs bypass Gemma
#        (already structured data) via a 'direct_jobs' flag.
#
# FIX 3 – UK location filter and cross-domain job-link guard
#   Old: `if not (is_job_uk or is_org_uk)` — because almost every org IS UK,
#        every job passed the filter regardless of its own location.
#   New: If the job's location is explicitly stated AND is not UK → reject.
#        If the job has no stated location → keep (UK org, assume UK job).
#        Added domain cross-check in _parse_gemma_response: job links whose
#        domain does not match the org's career page domain AND is not a known
#        ATS provider are silently dropped.
# ─────────────────────────────────────────────────────────────────────────────


class JobDescriptionGenerator:
    """Background thread that generates AI job descriptions and writes them to Excel."""

    def __init__(self, output_excel_path: str):
        self.output_excel_path = output_excel_path
        self.description_queue = queue.Queue()
        self.running = False
        self.thread = None
        self.descriptions_generated = 0
        self.lock = threading.Lock()
        logger.info("JobDescriptionGenerator initialised")

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._process_descriptions, daemon=True)
        self.thread.start()
        print("Job description generator started in background")

    def add_job(self, idx: int, job_data: Dict):
        self.description_queue.put((idx, job_data))

    def _process_descriptions(self):
        logger.info("Description processing thread started")
        while self.running:
            try:
                idx, job_data = self.description_queue.get(timeout=5)
                description = self._generate_single_description(
                    job_data.get('job_title'),
                    job_data.get('job_link'),
                    job_data.get('organisation_name'),
                    job_data.get('Location'),
                    job_data.get('Salary')
                )
                if description:
                    self._update_excel_with_description(idx, description)
                    self.descriptions_generated += 1
                    if self.descriptions_generated % 10 == 0:
                        print(f"   Generated {self.descriptions_generated} descriptions so far…")
                time.sleep(1)
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in description generator: {e}", exc_info=True)

    def _generate_single_description(self, job_title, job_link, org_name,
                                     location, salary) -> Optional[str]:
        if not job_title or (isinstance(job_title, float) and pd.isna(job_title)):
            return None
        prompt = (
            f"Generate a realistic job description for the following position.\n"
            f"Output ONLY the job description text itself, nothing else.\n\n"
            f"Job Title: {job_title}\nCompany: {org_name}\n"
            f"Location: {location or 'Not provided'}\nSalary: {salary or 'Not provided'}\n\n"
            "Requirements:\n"
            "- Write a professional 2-3 sentence description (NO bullets)\n"
            "- Include key responsibilities and qualifications\n"
            "- NO headers like 'Job Description' or 'Responsibilities'\n"
            "- NO extra commentary or notes\n"
            "- Start directly with the description text"
        )
        try:
            response = ollama.generate(
                model='gemma3:4b-it-q4_K_M',
                prompt=prompt,
                options={'temperature': 0.3, 'num_predict': 300,
                         'stop': ['\n\n\n', '---', 'Note:', 'Output:']}
            )
            desc = response['response'].strip()
            desc = re.sub(r'(?i)job description\s*:', '', desc).strip()
            desc = desc.strip('"\'').strip()
            return desc if desc else None
        except Exception as e:
            logger.error(f"Description error for {job_title}: {e}", exc_info=True)
            return None

    def _update_excel_with_description(self, idx: int, description: str):
        try:
            with self.lock:
                df = pd.read_excel(self.output_excel_path)
                if idx < len(df):
                    if 'job_description' in df.columns:
                        existing = df.at[idx, 'job_description']
                        if pd.isna(existing) or existing == '':
                            df.at[idx, 'job_description'] = description
                    df.to_excel(self.output_excel_path, index=False)
                    logger.info(f"Excel updated with description at index {idx}")
        except Exception as e:
            logger.error(f"Error updating Excel at index {idx}: {e}", exc_info=True)

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=10)
        print(f"\nDescription generator stopped. Total generated: {self.descriptions_generated}")


# ─────────────────────────────────────────────────────────────────────────────

class CareerPageScraper:

    def __init__(self, excel_path: str, checkpoint_file: str = 'scraper_checkpoint.pkl',
                 generate_descriptions: bool = True):
        logger.info("=" * 70)
        logger.info("Initialising CareerPageScraper")

        self.df = pd.read_excel(excel_path)
        logger.info(f"Excel loaded — {len(self.df)} rows, {len(self.df.columns)} columns")

        self.results: List[Dict] = []
        self.checkpoint_file = checkpoint_file
        self.processed_count = 0
        self.generate_descriptions = generate_descriptions
        self.description_generator: Optional[JobDescriptionGenerator] = None
        self.checkpoint_data = self._load_checkpoint()

        self.job_categories = {
            'engineering': 1, 'tech': 1, 'software': 1, 'developer': 1,
            'marketing': 2, 'sales': 2, 'business development': 2,
            'finance': 3, 'accounting': 3, 'financial': 3,
            'healthcare': 4, 'medical': 4, 'nurse': 4, 'doctor': 4,
            'education': 5, 'teacher': 5, 'professor': 5, 'tutor': 5,
            'trainer': 5, 'instructor': 5,
            'administration': 6, 'admin': 6, 'office': 6,
            'customer service': 7, 'support': 7, 'client': 7,
            'operations': 8, 'logistics': 8, 'supply chain': 8,
            'human resources': 9, 'hr': 9, 'recruitment': 9,
            'design': 10, 'creative': 10, 'ux': 10, 'ui': 10
        }

        self.job_types = {
            'full-time': 1, 'full time': 1, 'permanent': 1,
            'part-time': 2, 'part time': 2,
            'contract': 3, 'contractor': 3,
            'internship': 4, 'intern': 4,
            'freelance': 5, 'freelancer': 5
        }

        self.ALLOWED_EXTERNAL_DOMAINS = [
            "myworkdayjobs.com", "greenhouse.io", "lever.co", "smartrecruiters.com",
            "workable.com", "bamboohr.com", "recruitee.com", "icims.com", "jobvite.com",
            "successfactors.com", "oraclecloud.com", "dayforcehcm.com", "teamtailor.com",
            "taleo.net", "zoho.com", "applytracking.com", "workday.com"
        ]

        self.BLACKLIST_DOMAINS = [
            'gov.uk', 'gov.scot', 'gov.wales', 'nidirect.gov.uk',
            'companieshouse.gov.uk', 'dnb.com', 'endole.co.uk', 'opencorporates.com',
            'worksponsors.co.uk', 'visasponsors.uk', 'ukworksponsors.co.uk',
            'indeed.com', 'indeed.co.uk', 'reed.co.uk', 'totaljobs.com',
            'cv-library.co.uk', 'glassdoor.com', 'monster.co.uk',
            'facebook.com', 'twitter.com', 'linkedin.com', 'instagram.com'
        ]

    # ──────────────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _clean_markdown_url(url: str) -> str:
        """Convert [text](url) → url and strip whitespace."""
        if not url:
            return url
        s = str(url).strip()
        m = re.search(r'\((https?://[^\)]+)\)', s)
        return m.group(1).strip() if m else s

    @staticmethod
    def _is_http_url(value: Optional[str]) -> bool:
        """Light check — returns True only for syntactically valid http/https URLs.
        We deliberately do NOT do a live HEAD request here because this method is
        called thousands of times during sanitisation and would be far too slow."""
        if not value or not isinstance(value, str):
            return False
        v = value.strip()
        return v.lower().startswith("http://") or v.lower().startswith("https://")

    @staticmethod
    def _is_uk_location(text: Optional[str]) -> bool:
        if not text:
            return False
        t = text.lower()
        uk_keywords = [
            'uk', 'united kingdom', 'england', 'scotland', 'wales', 'northern ireland',
            'london', 'manchester', 'birmingham', 'leeds', 'glasgow', 'edinburgh',
            'cardiff', 'belfast', 'bristol', 'sheffield', 'nottingham', 'liverpool',
            'newcastle', 'york', 'oxford', 'cambridge', 'basingstoke', 'guildford',
            'colchester', 'surrey', 'essex', 'kent', 'berkshire', 'hampshire',
            'yorkshire', 'lancashire', 'cheshire', 'devon', 'cornwall', 'dorset',
            'somerset', 'suffolk', 'norfolk', 'hertfordshire', 'buckinghamshire',
            'gloucestershire', 'plymouth', 'reading', 'swindon', 'milton keynes',
            'remote', 'hybrid', 'nationwide', 'various locations'
        ]
        return any(k in t for k in uk_keywords)

    def _safe_print(self, text: str) -> None:
        enc = sys.stdout.encoding or "utf-8"
        if not isinstance(text, str):
            text = str(text)
        print(text.encode(enc, errors="replace").decode(enc, errors="replace"))

    def _sanitize_results_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """Strip any non-HTTP values and placeholder text from URL columns."""
        GARBAGE_MARKERS = [
            '[no url', '[job url]', 'no url provided', 'not specified',
            '[implied', '[url]', '[link]', 'placeholder', '[contact',
            '[email', '[apply', 'example.com', 'company.com',
            '[no direct', '[not available', '[see ', '[visit ',
            'no direct link', 'not provided', 'n/a',
        ]

        def _is_clean_url(val):
            if not self._is_http_url(val):
                return False
            v = str(val).lower()
            if any(p in v for p in GARBAGE_MARKERS):
                return False
            parsed = urlparse(str(val))
            return bool(parsed.netloc) and '.' in parsed.netloc

        for col in ['job_link', 'career_page_url', 'company_url']:
            if col in df.columns:
                invalid = ~df[col].apply(_is_clean_url)
                if invalid.any():
                    logger.warning(f"Sanitising {invalid.sum()} invalid {col} values")
                df.loc[invalid, col] = None
        return df

    # ──────────────────────────────────────────────────────────────────────────
    # Checkpointing
    # ──────────────────────────────────────────────────────────────────────────

    def _load_checkpoint(self) -> Dict:
        try:
            with open(self.checkpoint_file, 'rb') as f:
                ckpt = pickle.load(f)
                logger.info(f"Checkpoint loaded: {len(ckpt.get('processed_indices', []))} rows done")
                return ckpt
        except FileNotFoundError:
            return {'processed_indices': [], 'results': []}
        except Exception as e:
            logger.error(f"Error loading checkpoint: {e}", exc_info=True)
            return {'processed_indices': [], 'results': []}

    def _save_checkpoint(self):
        try:
            self.checkpoint_data['processed_indices'] = list(
                set(self.checkpoint_data.get('processed_indices', []))
            )
            self.checkpoint_data['results'] = self.results
            with open(self.checkpoint_file, 'wb') as f:
                pickle.dump(self.checkpoint_data, f)
            logger.info(f"Checkpoint saved: {len(self.checkpoint_data['processed_indices'])} rows")
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}", exc_info=True)

    # ──────────────────────────────────────────────────────────────────────────
    # FIX 1 — Robust AI URL validation
    # ──────────────────────────────────────────────────────────────────────────

    def validate_multiple_urls_with_ai(self, row: pd.Series) -> Dict:
        """Validate up to 5 URLs using AI + rule-based fallback."""
        org_name = row['organisation_name']
        logger.info(f"STEP 1: URL VALIDATION — {org_name}")

        urls = []
        for i in range(1, 6):
            url_col = f'link_{i}_url'
            title_col = f'link_{i}_title'
            if url_col in row.index and pd.notna(row[url_col]):
                url = str(row[url_col]).strip()
                title = str(row.get(title_col, '')).strip() if title_col in row.index else ''
                if url and url.lower() != 'nan':
                    urls.append({'url': url, 'title': title, 'rank': i})

        self._safe_print(f"\n{'─'*60}\nORGANIZATION: {org_name}")
        self._safe_print("Candidate career URLs:")
        for u in (urls or []):
            self._safe_print(f"  [{u['rank']}] {u['url']}  |  {u['title']}")
        self._safe_print('─' * 60)

        if not urls:
            return self._empty_validation('No URLs provided')

        prompt = f"""You are validating URLs to find the best career page for an organization.

Organization: {org_name}

URLs to validate (in priority order):
{json.dumps(urls, indent=2)}

REJECTION CRITERIA — reject if domain is any of:
  gov.uk, companieshouse.gov.uk, gov.scot, gov.wales,
  dnb.com, endole.co.uk, opencorporates.com,
  worksponsors.co.uk, visasponsors.uk, ukworksponsors.co.uk,
  indeed.com, reed.co.uk, totaljobs.com, cv-library.co.uk,
  glassdoor.com, monster.co.uk,
  facebook.com, twitter.com, linkedin.com, instagram.com

ACCEPTANCE CRITERIA:
  - Domain is the organization's own website
  - Domain name relates to the organization name
  - URL path contains /careers, /jobs, /vacancies, /join-us, /recruitment

Respond with EXACTLY this format (no extra text before or after):
BEST_URL: <the best valid URL or NONE>
DECISION: ACCEPT or REJECT
CATEGORY: Own Website / Government / Directory / Aggregator / Social Media / Job Board
REASON: <one line>
CONFIDENCE: High / Medium / Low"""

        try:
            response = ollama.generate(
                model='gemma3:4b-it-q4_K_M',
                prompt=prompt,
                options={'temperature': 0.05, 'num_predict': 200}
            )
            raw = response['response']
            self._safe_print("AI URL VALIDATION OUTPUT:")
            self._safe_print(raw)
            self._safe_print('─' * 60)

            result = self._parse_multi_url_validation_robust(raw, urls, org_name)

        except Exception as e:
            logger.error(f"AI validation error: {e}", exc_info=True)
            result = self._fallback_multi_url_validation(urls, org_name)

        self._safe_print(f"FINAL DECISION: {result['decision']}  |  URL: {result['best_url']}")
        self._safe_print(f"Reason: {result['reason']}\n{'='*60}\n")
        return result

    def _parse_multi_url_validation_robust(self, response: str,
                                           urls: List[Dict], org_name: str) -> Dict:
        """
        FIX 1 — Regex-based parser that tolerates:
          • Bold markdown (**BEST_URL:**)
          • Extra whitespace / tabs
          • Lowercase keys
          • Trailing punctuation on the URL
          • Content before the structured block
        Falls back to rule-based if no valid BEST_URL is found.
        """
        # Strip markdown bold/italic and code fences
        clean = re.sub(r'\*+', '', response)
        clean = re.sub(r'`+', '', clean)

        result: Dict = {
            'is_valid': False,
            'best_url': None,
            'decision': 'REJECT',
            'category': 'Unknown',
            'reason': 'Unable to parse AI response',
            'confidence': 'Low'
        }

        # BEST_URL — must contain http
        m = re.search(r'BEST[_\s]URL\s*:\s*(https?://\S+)', clean, re.IGNORECASE)
        if m:
            candidate = m.group(1).rstrip('.,);\'\"')
            result['best_url'] = candidate
            result['is_valid'] = True
            result['decision'] = 'ACCEPT'
            logger.debug(f"Parsed BEST_URL: {candidate}")

        # DECISION
        m = re.search(r'DECISION\s*:\s*(ACCEPT|REJECT)', clean, re.IGNORECASE)
        if m:
            dec = m.group(1).upper()
            result['decision'] = dec
            result['is_valid'] = (dec == 'ACCEPT')
            logger.debug(f"Parsed DECISION: {dec}")

        # CATEGORY
        m = re.search(r'CATEGORY\s*:\s*(.+?)(?:\n|$)', clean, re.IGNORECASE)
        if m:
            result['category'] = m.group(1).strip().rstrip('.,')

        # REASON
        m = re.search(r'REASON\s*:\s*(.+?)(?:\n|$)', clean, re.IGNORECASE)
        if m:
            result['reason'] = m.group(1).strip().rstrip('.,')

        # CONFIDENCE
        m = re.search(r'CONFIDENCE\s*:\s*(High|Medium|Low)', clean, re.IGNORECASE)
        if m:
            result['confidence'] = m.group(1).capitalize()

        # If ACCEPT but no URL was parsed, use highest-priority URL from list
        if result['is_valid'] and not result['best_url'] and urls:
            result['best_url'] = urls[0]['url']
            logger.debug(f"ACCEPT but no URL parsed — using fallback: {result['best_url']}")

        # If parsing completely failed (reason unchanged), run rule-based fallback
        if result['reason'] == 'Unable to parse AI response':
            logger.warning("AI response unparseable — switching to rule-based fallback")
            return self._fallback_multi_url_validation(urls, org_name)

        return result

    def _fallback_multi_url_validation(self, urls: List[Dict], org_name: str) -> Dict:
        """Rule-based URL validation when AI output cannot be parsed."""
        logger.warning("Using rule-based fallback URL validation")
        for url_data in urls:
            url = url_data['url']
            domain = urlparse(url).netloc.lower()
            blacklisted = any(b in domain for b in self.BLACKLIST_DOMAINS)
            has_http = url.lower().startswith('http')
            if not blacklisted and has_http:
                logger.info(f"Fallback ACCEPT: {url}")
                return {
                    'is_valid': True,
                    'best_url': url,
                    'decision': 'ACCEPT',
                    'category': 'Own Website (Fallback)',
                    'reason': f'Passed rule-based validation (Rank {url_data["rank"]})',
                    'confidence': 'Medium'
                }
        return self._empty_validation('All provided URLs are blacklisted or invalid')

    @staticmethod
    def _empty_validation(reason: str) -> Dict:
        return {
            'is_valid': False,
            'best_url': None,
            'decision': 'REJECT',
            'category': 'Missing URL',
            'reason': reason,
            'confidence': 'High'
        }

    # ──────────────────────────────────────────────────────────────────────────
    # Page scraping
    # ──────────────────────────────────────────────────────────────────────────

    def scrape_page(self, url: str, extract_all_links: bool = False) -> Optional[Dict]:
        try:
            headers = {
                'User-Agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/120.0.0.0 Safari/537.36'
                ),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-GB,en;q=0.9',
            }
            resp = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.content, 'html.parser')
            for el in soup(["script", "style", "nav", "footer", "header"]):
                el.decompose()

            text = ' '.join(soup.get_text(separator=' ', strip=True).split())
            job_links, all_links = [], []

            for a in soup.find_all('a', href=True):
                href = a['href']
                full_url = urljoin(url, href)
                link_text = a.get_text(strip=True)
                if not full_url or full_url == url:
                    continue
                link_data = {'url': full_url, 'text': link_text, 'href': href}
                if extract_all_links:
                    all_links.append(link_data)
                if self._is_job_link(href, link_text):
                    job_links.append(link_data)

            forms = soup.find_all('form')
            form_keywords = ['application', 'apply', 'cv', 'resume', 'upload', 'career', 'job']
            has_application_form = any(
                kw in str(f).lower() for f in forms for kw in form_keywords
            )

            return {
                'text': text[:10000],
                'job_links': job_links[:50],
                'all_links': all_links[:100] if extract_all_links else [],
                'has_form': len(forms) > 0,
                'has_application_form': has_application_form,
                'title': soup.title.string if soup.title else '',
                'success': True
            }
        except requests.Timeout:
            logger.error(f"Timeout: {url}")
        except requests.RequestException as e:
            logger.error(f"Request error {url}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error {url}: {e}", exc_info=True)
        return None

    def _is_job_link(self, href: str, link_text: str) -> bool:
        job_keywords = [
            'job', 'position', 'role', 'opening', 'vacancy', 'vacancies',
            'apply', 'career', 'opportunity', 'hiring', 'employment'
        ]
        combined = (href + ' ' + link_text).lower()
        return any(kw in combined for kw in job_keywords)

    # ──────────────────────────────────────────────────────────────────────────
    # FIX 2 — Workday API scraper (replaces Selenium DOM walk)
    # ──────────────────────────────────────────────────────────────────────────

    def scrape_workday_portal(self, workday_url: str, org_name: str) -> List[Dict]:
        """
        FIX 2 — Use Workday's public JSON API instead of Selenium.

        Workday API endpoint pattern:
          POST https://{host}/wday/cxs/{tenant}/{jobsite}/jobs
          Body: {"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": ""}

        Response contains jobPostings[].externalPath which is the stable URL fragment.
        Full job URL = base_url + externalPath.
        """
        logger.info(f"Workday API scrape: {workday_url}")
        print(f"   Workday portal detected — using public JSON API…")

        parsed = urlparse(workday_url)
        host = parsed.netloc                        # e.g. acme.wd3.myworkdayjobs.com
        tenant = host.split('.')[0]                 # e.g. acme
        base_url = f"https://{host}"

        # Extract jobsite name from URL path  (skip language segment like en-US / en-GB)
        lang_pattern = re.compile(r'^[a-z]{2}(-[A-Z]{2})?$')
        path_parts = [p for p in parsed.path.split('/') if p]
        jobsite = None
        for part in path_parts:
            if not lang_pattern.match(part) and not part.lower().startswith('job'):
                jobsite = part
                break

        if not jobsite:
            logger.error(f"Cannot parse jobsite from Workday URL: {workday_url}")
            print("   Could not determine Workday jobsite — skipping")
            return []

        api_url = f"{base_url}/wday/cxs/{tenant}/{jobsite}/jobs"
        logger.info(f"Workday API endpoint: {api_url}")
        print(f"   API endpoint: {api_url}")

        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            ),
        }

        jobs: List[Dict] = []
        offset = 0
        limit = 20
        max_jobs = 200          # safety cap

        while len(jobs) < max_jobs:
            payload = {
                "appliedFacets": {},
                "limit": limit,
                "offset": offset,
                "searchText": ""
            }
            try:
                resp = requests.post(api_url, json=payload, headers=headers, timeout=15)
                resp.raise_for_status()
                data = resp.json()

                postings = data.get('jobPostings', [])
                total = data.get('total', 0)
                logger.info(f"Workday API offset={offset}: got {len(postings)} of {total} total")

                if not postings:
                    break

                for posting in postings:
                    ext_path = posting.get('externalPath', '')
                    if not ext_path:
                        continue

                    # Build the correct, stable job URL from base + externalPath
                    job_url = base_url + ext_path

                    location = posting.get('locationsText') or None
                    date_posted = posting.get('postedOn') or None

                    jobs.append({
                        'title': posting.get('title', '').strip(),
                        'link': job_url,
                        'url': job_url,
                        'text': posting.get('title', ''),
                        'href': ext_path,
                        'location': location,
                        'date_posted': date_posted,
                        'remote_type': None,
                        'salary': None
                    })

                offset += limit
                if offset >= total:
                    break

                time.sleep(0.5)     # polite delay

            except requests.HTTPError as e:
                logger.error(f"Workday API HTTP error: {e}")
                print(f"   Workday API HTTP error: {e}")
                break
            except Exception as e:
                logger.error(f"Workday API error: {e}", exc_info=True)
                print(f"   Workday API error: {e}")
                break

        logger.info(f"Workday API returned {len(jobs)} jobs for {org_name}")
        print(f"   Fetched {len(jobs)} jobs from Workday API")
        return jobs

    # ──────────────────────────────────────────────────────────────────────────
    # Crawl orchestration
    # ──────────────────────────────────────────────────────────────────────────

    def crawl_career_pages(self, start_url: str, org_name: str, max_depth: int = 4) -> Dict:
        logger.info(f"STEP 2: CRAWLING — {org_name}  |  {start_url}")
        print(f"   Crawling career pages (max depth: {max_depth})")

        # ── Workday: use API, skip crawl + Gemma entirely ──
        if any(d in start_url for d in ['myworkdayjobs.com', 'workday.com']):
            workday_jobs = self.scrape_workday_portal(start_url, org_name)
            return {
                'pages_data': [],                   # no pages to pass to Gemma
                'unique_jobs': workday_jobs,
                'direct_jobs': workday_jobs,        # flag consumed by extract_jobs_with_gemma
                'has_form': True,
                'has_application_form': True,
                'pages_crawled': 1
            }

        # ── Standard crawl ──
        base_domain = urlparse(start_url).netloc
        visited: set = set()
        queue_list = [(start_url, 0)]
        pages_data: List[Dict] = []
        unique_jobs: Dict[str, Dict] = {}
        has_form = False
        has_application_form = False

        while queue_list and len(visited) < 20:
            current_url, depth = queue_list.pop(0)
            if current_url in visited or depth >= max_depth:
                continue
            visited.add(current_url)

            print(f"   {'  ' * depth}Depth {depth}: {current_url[:80]}…")
            data = self.scrape_page(current_url, extract_all_links=(depth < max_depth - 1))
            if not data:
                continue

            pages_data.append({
                'url': current_url,
                'text': data['text'],
                'job_links': data['job_links'],
                'has_form': data['has_form'],
                'has_application_form': data['has_application_form'],
                'title': data['title']
            })
            has_form = has_form or data['has_form']
            has_application_form = has_application_form or data['has_application_form']

            for job in data['job_links']:
                if job['url'] not in unique_jobs:
                    unique_jobs[job['url']] = job

            # Only follow links that stay within the same domain (or known ATS)
            for link in data.get('all_links', []):
                link_domain = urlparse(link['url']).netloc
                same_domain = (link_domain == base_domain or
                               link_domain.endswith('.' + base_domain))
                allowed_ats = any(ats in link_domain for ats in self.ALLOWED_EXTERNAL_DOMAINS)
                if (same_domain or allowed_ats) and link['url'] not in visited:
                    queue_list.append((link['url'], depth + 1))

            time.sleep(1)

        logger.info(f"Crawl done: {len(visited)} pages, {len(unique_jobs)} unique job links")
        print(f"   Crawl done: {len(visited)} pages, {len(unique_jobs)} unique job links")

        return {
            'pages_data': pages_data,
            'unique_jobs': list(unique_jobs.values()),
            'direct_jobs': None,
            'has_form': has_form,
            'has_application_form': has_application_form,
            'pages_crawled': len(visited)
        }

    # ──────────────────────────────────────────────────────────────────────────
    # Gemma job extraction
    # ──────────────────────────────────────────────────────────────────────────

    def extract_jobs_with_gemma(self, crawl_results: Dict,
                                org_name: str, career_url: str) -> Dict:
        logger.info(f"STEP 3: EXTRACTING JOBS — {org_name}")

        # ── FIX 2 continued: Workday jobs are already structured, skip Gemma ──
        if crawl_results.get('direct_jobs') is not None:
            direct = crawl_results['direct_jobs']
            logger.info(f"Using {len(direct)} direct Workday jobs (skipping Gemma)")
            return {
                'jobs': direct,
                'application_type': 'Job Openings' if direct else 'No Jobs and No Form',
                'career_page_available': 'Yes',
                'has_form': True,
                'has_application_form': True
            }

        all_jobs: List[Dict] = []
        for idx, page_data in enumerate(crawl_results.get('pages_data', []), 1):
            logger.info(f"Processing page {idx}: {page_data['url']}")
            result = self.extract_jobs_from_page(page_data, org_name, career_url)
            all_jobs.extend(result.get('jobs', []))

        has_form = crawl_results.get('has_form', False)
        has_application_form = crawl_results.get('has_application_form', False)

        if all_jobs:
            app_type = 'Job Openings'
            available = 'Yes'
        elif has_application_form or has_form:
            app_type = 'Only Form'
            available = 'Yes'
        else:
            app_type = 'No Jobs and No Form'
            available = 'Yes (Validated) - No Data'

        return {
            'jobs': all_jobs,
            'application_type': app_type,
            'career_page_available': available,
            'has_form': has_form,
            'has_application_form': has_application_form
        }

    def extract_jobs_from_page(self, page_data: Dict, org_name: str,
                               career_url: str = '') -> Dict:
        """Extract jobs from a single page using Gemma, with domain guard."""
        text = page_data['text'][:10000]
        prompt = f"""You are a factual job vacancy extractor for UK-based organizations.
Extract ONLY real, currently open employment positions.

Company: {org_name}
Page URL: {page_data['url']}
Page Text: {text}
Job Links: {json.dumps(page_data['job_links'][:20], indent=2)}

STRICT RULES:
DO NOT EXTRACT:
- Navigation links, categories, departments
- Services, capabilities, business offerings
- Blog posts, news, awards, training courses
- Generic "Careers", "Join Us" without specific job titles
- "Our People", "Meet the Team", staff profiles, biographies
- Historical or past roles not actively being advertised

ONLY EXTRACT:
- Actual job titles actively being advertised
- Each job MUST have a corresponding clickable link from the Job Links list
- Each job MUST have a clear, specific job title

OUTPUT FORMAT (one job per line, nothing else):
- Job Title | Job Link | Location | Salary

If NO jobs found, output exactly:
NO_JOBS_FOUND

Valid example:
- Senior Software Engineer | https://company.com/jobs/123 | London, UK | £50,000-£60,000

Invalid (DO NOT output):
- Careers | https://company.com/careers | |
- Join Our Team | | |"""

        try:
            response = ollama.generate(
                model='gemma3:4b-it-q4_K_M',
                prompt=prompt,
                options={'temperature': 0.1, 'num_predict': 500}
            )
            raw = response['response']
            logger.debug(f"Gemma raw: {raw[:200]}")

            if 'NO_JOBS_FOUND' in raw.upper():
                return {'jobs': []}

            # Pass career_url so domain guard knows what's in-scope
            return self._parse_gemma_response(raw, page_data, career_url)

        except Exception as e:
            logger.error(f"Gemma extraction error: {e}", exc_info=True)
            return {'jobs': []}

    def _parse_gemma_response(self, response: str, page_data: Dict,
                              career_url: str = '') -> Dict:
        """
        Parse Gemma job lines.

        FIX 3 — Domain cross-check:
        Job links whose domain does not match the career page domain AND is not
        a known ATS provider are dropped.  This prevents jobs from other
        companies or generic job boards sneaking through.
        """
        jobs: List[Dict] = []

        # Determine the allowed domains for this org
        career_domain = urlparse(career_url or page_data['url']).netloc.lower()
        # Strip leading www.
        if career_domain.startswith('www.'):
            career_domain = career_domain[4:]

        def _link_is_in_scope(link: str) -> bool:
            if not link:
                return False
            link_domain = urlparse(link).netloc.lower()
            if link_domain.startswith('www.'):
                link_domain = link_domain[4:]

            same = (link_domain == career_domain or
                    link_domain.endswith('.' + career_domain) or
                    career_domain.endswith('.' + link_domain))
            allowed_ats = any(ats in link_domain for ats in self.ALLOWED_EXTERNAL_DOMAINS)
            return same or allowed_ats

        lines = [l.strip() for l in response.split('\n') if l.strip()]
        for line in lines:
            if not line.startswith('- '):
                continue
            parts = [p.strip() for p in line[2:].split('|')]
            if not parts:
                continue

            job_title = parts[0]
            job_link = parts[1] if len(parts) > 1 else None
            location = parts[2] if len(parts) > 2 else None
            salary = parts[3] if len(parts) > 3 else None

            # Try to match from page job_links if Gemma gave no link
            if not job_link:
                for ld in page_data['job_links']:
                    if job_title.lower() in ld['text'].lower():
                        job_link = ld['url']
                        break

            # Clean markdown URL format
            if job_link:
                job_link = self._clean_markdown_url(job_link)

            # Resolve relative paths against career URL
            if job_link and job_link.startswith('/'):
                job_link = urljoin(career_url or page_data['url'], job_link)
                logger.debug(f"Resolved relative link: {job_link}")

            # ── STRICT VALIDATION: only accept real HTTP URLs ──
            # Step 1: must start with http
            if not job_link or not job_link.startswith('http'):
                logger.debug(f"Skipping (no valid link): {job_title}")
                continue

            # Step 2: must have a proper domain with at least one dot
            parsed_link = urlparse(job_link)
            if not parsed_link.netloc or '.' not in parsed_link.netloc:
                logger.debug(f"Skipping (malformed URL): {job_title} -> {job_link}")
                continue

            # Step 3: reject placeholder / garbage text in URLs
            link_lower = job_link.lower()
            GARBAGE_MARKERS = [
                '[no url', '[job url]', 'no url provided', 'not specified',
                '[implied', '[url]', '[link]', 'example.com', 'company.com',
                'placeholder', '[contact', '[apply', 'not provided',
            ]
            if any(gm in link_lower for gm in GARBAGE_MARKERS):
                logger.debug(f"Skipping (placeholder text in link): {job_title} -> {job_link}")
                continue

            # Step 4: reject suspiciously short URLs (scheme + less than 8 chars)
            url_body = re.sub(r'^https?://', '', job_link)
            if len(url_body) < 8:
                logger.debug(f"Skipping (too short URL): {job_title} -> {job_link}")
                continue

            # FIX 3: Domain cross-check — reject out-of-scope links
            if not _link_is_in_scope(job_link):
                logger.warning(
                    f"Dropping out-of-scope job link: {job_link} "
                    f"(career domain: {career_domain})"
                )
                continue

            # Sanitise empty / nan strings
            location = None if not location or location.lower() in ('not specified', 'nan', '') else location
            salary = None if not salary or salary.lower() in ('not specified', 'nan', '') else salary

            jobs.append({
                'title': job_title,
                'link': job_link,
                'location': location,
                'salary': salary
            })
            logger.debug(f"Accepted job: {job_title} → {job_link}")

        logger.info(f"Total jobs parsed from Gemma: {len(jobs)}")
        return {'jobs': jobs}

    # ──────────────────────────────────────────────────────────────────────────
    # Job enrichment
    # ──────────────────────────────────────────────────────────────────────────

    def enrich_job_fields(self, job: Dict, org_name: str) -> Dict:
        enriched = job.copy()
        title = (enriched.get('title') or '').strip()
        title_lower = title.lower()

        cat = 11
        for k, v in self.job_categories.items():
            if k in title_lower:
                cat = v
                break
        enriched['job_category_id'] = cat

        jtype = 1
        for k, v in self.job_types.items():
            if k in title_lower:
                jtype = v
                break
        enriched['job_type_id'] = jtype

        loc = (enriched.get('location') or '').strip()
        enriched['location'] = loc if loc and loc.lower() not in ('not specified', 'nan') else None
        enriched['date_posted'] = enriched.get('date_posted') or None
        enriched['salary'] = enriched.get('salary') or None
        enriched['remote_type'] = enriched.get('remote_type') or None
        enriched['experience_level'] = enriched.get('experience_level') or None
        enriched['job_source'] = 'Web Scraping'
        enriched['is_active'] = True
        enriched['views_count'] = 0
        enriched['embedding_vector'] = None
        return enriched

    # ──────────────────────────────────────────────────────────────────────────
    # Row processing — FIX 3: corrected UK filter logic
    # ──────────────────────────────────────────────────────────────────────────

    def process_row(self, row: pd.Series, current_excel_idx: int) -> List[Dict]:
        org_name = row['organisation_name']
        logger.info(f"PROCESSING ROW {current_excel_idx}: {org_name}")

        town = str(row['town']) if 'town' in row.index and pd.notna(row['town']) else ''
        county = str(row['county']) if 'county' in row.index and pd.notna(row['county']) else ''
        org_location = f"{town}, {county}".strip(', ')

        print("=" * 70)
        print(f"Organisation: {org_name}")

        if current_excel_idx in set(self.checkpoint_data.get('processed_indices', [])):
            print(f"Skipping row {current_excel_idx} (already processed)")
            return []

        # ── Step 1: URL validation ──
        validation = self.validate_multiple_urls_with_ai(row)
        best_url = validation['best_url']

        if not validation['is_valid'] or not best_url:
            logger.warning("URL validation failed — metadata row only")
            return [self._empty_row(org_name, org_location, validation, best_url)]

        # ── Step 2: Crawl ──
        crawl_results = self.crawl_career_pages(best_url, org_name, max_depth=4)
        if not crawl_results or (
            not crawl_results.get('pages_data') and
            not crawl_results.get('direct_jobs')
        ):
            logger.warning("Crawl returned nothing")
            return [self._empty_row(org_name, org_location, validation, best_url,
                                   available='Yes Validated - No Data')]

        # ── Step 3: Extract jobs ──
        analysis = self.extract_jobs_with_gemma(crawl_results, org_name, best_url)

        # ── Step 4: Enrich + UK filter ──
        results: List[Dict] = []
        filtered_out = 0

        for job in analysis['jobs']:
            enriched = self.enrich_job_fields(job, org_name)

            # Resolve job location
            job_loc = enriched.get('location')
            if not job_loc:
                job_loc = org_location.split(',')[0].strip() if org_location else None

            # ── FIX 3: Correct UK filter ──
            # OLD (broken): if not (is_job_uk OR is_org_uk) → filter
            #   → any UK org caused ALL its jobs to pass, even US-located jobs
            # NEW: if location IS explicitly stated AND IS NOT UK → filter out
            #   If location is unknown/empty → keep (assume UK since we target UK orgs)
            if job_loc and not self._is_uk_location(job_loc):
                logger.warning(
                    f"Filtered OUT (non-UK location): {enriched.get('title')} — {job_loc}"
                )
                filtered_out += 1
                continue

            print(f"   ✓ {enriched.get('title', '?')} | {job_loc or 'Location unknown'}")

            results.append({
                'organisation_name': org_name,
                'org_location': org_location,
                'career_page_available': analysis['career_page_available'],
                'career_page_url': best_url,
                'validation_reason': validation['reason'],
                'application_type': analysis['application_type'],
                'job_title': enriched.get('title'),
                'job_link': enriched.get('link'),
                'Location': job_loc,
                'Salary': enriched.get('salary'),
                'DatePosted': enriched.get('date_posted'),
                'job_category_id': enriched['job_category_id'],
                'remote_type': enriched.get('remote_type'),
                'experience_level': enriched.get('experience_level'),
                'job_type_id': enriched['job_type_id'],
                'job_source': enriched['job_source'],
                'company_url': best_url,
                'is_active': True,
                'views_count': 0,
                'embedding_vector': None,
                'job_description': None
            })

        logger.info(f"UK jobs kept: {len(results)}, filtered out: {filtered_out}")

        if not results:
            return [self._empty_row(org_name, org_location, validation, best_url,
                                   available=analysis['career_page_available'],
                                   app_type=analysis['application_type'])]

        return results

    # ──────────────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _empty_row(self, org_name: str, org_location: str,
                   validation: Dict, best_url: Optional[str],
                   available: str = None, app_type: str = None) -> Dict:
        return {
            'organisation_name': org_name,
            'org_location': org_location,
            'career_page_available': available or validation.get('decision', 'REJECT'),
            'career_page_url': best_url,
            'validation_reason': validation.get('reason', ''),
            'application_type': app_type,
            'job_title': None,
            'job_link': None,
            'Location': None,
            'Salary': None,
            'DatePosted': None,
            'job_category_id': None,
            'remote_type': None,
            'experience_level': None,
            'job_type_id': None,
            'job_source': 'Web Scraping',
            'company_url': best_url,
            'is_active': True,
            'views_count': 0,
            'embedding_vector': None,
            'job_description': None
        }

    # ──────────────────────────────────────────────────────────────────────────
    # Main run loop
    # ──────────────────────────────────────────────────────────────────────────

    def run(self, output_excel_path: str, start_idx: int = 0, batch_size: int = 10):
        logger.info("STARTING CAREER PAGE SCRAPER — UK JOBS ONLY")
        print(f"\n{'='*70}\nCAREER PAGE SCRAPER — UK JOBS ONLY\n{'='*70}")
        print(f"Total organisations: {len(self.df)}")
        print(f"Start index: {start_idx}  |  Batch size: {batch_size}\n{'='*70}\n")

        if self.generate_descriptions:
            self.description_generator = JobDescriptionGenerator(output_excel_path)
            self.description_generator.start()

        try:
            for idx, row in self.df.iterrows():
                if idx < start_idx:
                    continue

                print(f"\n[{idx + 1}/{len(self.df)}] Row {idx}…")
                row_results = self.process_row(row, idx)
                self.results.extend(row_results)

                # Queue description generation for any rows with a job title
                if self.generate_descriptions and self.description_generator:
                    for result in row_results:
                        if result.get('job_title'):
                            result_idx = len(self.results) - len(row_results) + row_results.index(result)
                            self.description_generator.add_job(result_idx, result)

                self.checkpoint_data['processed_indices'].append(idx)
                self.processed_count += 1

                if self.processed_count % batch_size == 0:
                    self._save_checkpoint()
                    df_out = pd.DataFrame(self.results)
                    df_out = self._sanitize_results_df(df_out)
                    if 'job_description' not in df_out.columns:
                        df_out['job_description'] = None
                    df_out.to_excel(output_excel_path, index=False)
                    print(f"\n   → Saved {len(self.results)} rows to {output_excel_path}")

            # Final save
            df_out = pd.DataFrame(self.results)
            df_out = self._sanitize_results_df(df_out)
            if 'job_description' not in df_out.columns:
                df_out['job_description'] = None
            df_out.to_excel(output_excel_path, index=False)
            self._save_checkpoint()

            print(f"\n{'='*70}\nSCRAPING COMPLETE!\n{'='*70}")
            print(f"Organisations processed: {self.processed_count}")
            print(f"Total results: {len(self.results)}")
            print(f"Output: {output_excel_path}\n{'='*70}\n")

        finally:
            if self.description_generator:
                print("\nWaiting for description generator to finish…")
                time.sleep(10)
                self.description_generator.stop()


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    scraper = CareerPageScraper(
        excel_path=r"C:\Users\srkyo\PycharmProjects\Helloworld\Research\Allen Project\Link Fetching\Trying 2\raw_career_links_for_llm_Exaustive_part2.xlsx",
        checkpoint_file='scraper_checkpoint.pkl',
        generate_descriptions=True
    )
    scraper.run(
        output_excel_path='career_scraping_results_with_descriptions_V2.xlsx',
        start_idx=0,
        batch_size=10
    )