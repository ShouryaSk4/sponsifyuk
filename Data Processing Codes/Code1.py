import pandas as pd
import asyncio
from playwright.async_api import async_playwright
from datetime import datetime
import time
import random
import json
import os


class CheckpointManager:
    """Handles saving and resuming progress"""

    def __init__(self, checkpoint_file: str = "scraper_checkpoint.json"):
        self.checkpoint_file = checkpoint_file
        self.results_file = "results_partial.xlsx"

    def save_checkpoint(self, processed_indices: list, results: list):
        """Save progress"""
        checkpoint = {
            'timestamp': datetime.now().isoformat(),
            'processed_count': len(processed_indices),
            'processed_indices': processed_indices,
            'last_index': max(processed_indices) if processed_indices else -1
        }

        with open(self.checkpoint_file, 'w') as f:
            json.dump(checkpoint, f, indent=2)

        # Save partial results
        if results:
            df = pd.DataFrame(results)
            df.to_excel(self.results_file, index=False)

        print(f"💾 Checkpoint saved: {len(processed_indices)} processed")

    def load_checkpoint(self):
        """Load previous progress"""
        if not os.path.exists(self.checkpoint_file):
            return None

        try:
            with open(self.checkpoint_file, 'r') as f:
                checkpoint = json.load(f)
            print(f"📂 Checkpoint found: {checkpoint['processed_count']} already processed")
            return checkpoint
        except Exception as e:
            print(f"⚠️  Checkpoint load failed: {e}")
            return None

    def clear_checkpoint(self):
        """Clear checkpoint after completion"""
        if os.path.exists(self.checkpoint_file):
            os.remove(self.checkpoint_file)


class SimplePlaywrightScraper:
    """Enhanced scraper with checkpoint/resume, domain filtering, and anti-detection"""

    def __init__(self, max_concurrent: int = 5, headless: bool = False,
                 search_engine: str = 'duckduckgo', use_proxy: bool = False,
                 proxy_config: dict = None):
        self.max_concurrent = max_concurrent
        self.headless = headless
        self.search_engine = search_engine.lower()
        self.processed_count = 0
        self.use_proxy = use_proxy
        self.proxy_config = proxy_config

        # Initialize managers
        self.checkpoint_manager = CheckpointManager()
        self.processed_indices = []
        self.all_results = []

        # Statistics for engine usage
        self.google_count = 0
        self.duckduckgo_count = 0

        # Domains to skip (job boards, aggregators, gov sites)
        self.blocked_domains = [
            # Professional job aggregators
            'jobsite.co.uk', 'fish4jobs.co.uk', 'jobs.ac.uk', "cv-library.co.uk",
            'gb.bebee.com', 'ukcompanydir.com', 'leicester.ukjob.co.uk', 'rocketreach.co',
            'www.s1jobs.com',

            # Government domains
            'gov.uk', 'dwp.gov.uk', 'nhs.uk',

            # Business aggregators
            'dnb.com', 'companieshouse.gov.uk', 'endole.co.uk',
            'bloomberg.com', 'crunchbase.com',

            # Visa/sponsorship aggregators
            'huntukvisasponsors.com', 'visajob.co.uk',
            'skilledworkersponsors.co.uk', 'licensed-sponsors-uk.com',
            'visasponsorshipuk.com', 'companyjobs.co.uk',

            # General aggregators/listings
            'techwaka.net', 'jobtoday.com', 'howdoyouspell.org',
            'restaurantguru.com', 'yelp.com', 'yelp.co.uk',
            'trustpilot.com', 'wikipedia.org', 'facebook.com',
            'twitter.com', 'instagram.com', 'youtube.com', 'midulstercouncil.org',
            '192.com', 'grabjobs.co', 'thebestof.co.uk', 'opencorpdata.com',

            # More UK job boards
            'cwjobs.co.uk', 'technojobs.co.uk', 'milkround.com',
            'graduate-jobs.com', 'targetjobs.co.uk', 'prospects.ac.uk'
        ]

    def is_blocked_domain(self, url: str) -> bool:
        """Check if URL contains blocked domain"""
        url_lower = url.lower()
        for domain in self.blocked_domains:
            if domain in url_lower:
                return True
        return False

    async def search_google(self, page, query: str) -> list:
        """Search Google with human-like behavior and fallback to DuckDuckGo"""
        try:
            search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            await page.goto(search_url, wait_until='domcontentloaded', timeout=30000)

            # Human-like behavior: random mouse movements
            await page.mouse.move(random.randint(50, 400), random.randint(50, 400))
            await asyncio.sleep(random.uniform(0.5, 1.5))

            # Random scrolling
            await page.mouse.wheel(delta_y=random.randint(100, 400))
            await asyncio.sleep(random.uniform(1, 3))

            links = []
            results = await page.query_selector_all('div.tF2Cxc')

            for element in results:
                if len(links) >= 5:
                    break
                try:
                    link_elem = await element.query_selector('a')
                    title_elem = await element.query_selector('h3')
                    if link_elem and title_elem:
                        url = await link_elem.get_attribute('href')
                        title = await title_elem.inner_text()
                        if url and not self.is_blocked_domain(url):
                            links.append({'url': url, 'title': title.strip()})
                except:
                    continue

            return links

        except Exception as e:
            print(f"[Google Fallback] {e} - Switching to DuckDuckGo")
            return await self.search_duckduckgo(page, query)

    async def search_duckduckgo(self, page, query: str) -> list:
        """Search DuckDuckGo with random human-like delays"""
        try:
            search_url = f"https://duckduckgo.com/?q={query.replace(' ', '+')}"
            await page.goto(search_url, wait_until='networkidle', timeout=15000)

            # Random human-like wait
            await page.wait_for_timeout(random.randint(500, 1200))

            await page.wait_for_selector('article[data-testid="result"]', timeout=10000)

            links = []
            result_elements = await page.query_selector_all('article[data-testid="result"]')

            for element in result_elements:
                if len(links) >= 5:
                    break

                try:
                    link_elem = await element.query_selector('a[href^="http"]')
                    if link_elem:
                        url = await link_elem.get_attribute('href')

                        if url and not self.is_blocked_domain(url):
                            title_elem = await element.query_selector('h2')
                            title = await title_elem.inner_text() if title_elem else ''
                            links.append({'url': url, 'title': title.strip()})
                except:
                    continue

            return links

        except Exception as e:
            print(f"\n⚠️  Error searching '{query[:50]}': {e}")
            return []

    def load_excel(self, file_path: str) -> pd.DataFrame:
        """Load your organizations Excel file"""
        print(f"📂 Loading: {file_path}")
        df = pd.read_excel(file_path)
        print(f"✓ Loaded {len(df)} organizations\n")
        return df

    def create_queries(self, df: pd.DataFrame) -> list:
        """Create search queries from your data"""
        queries = []

        for idx, row in df.iterrows():
            org = str(row.get('Organisation Name', '')).strip()
            town = str(row.get('Town/City', '')).strip()
            county = str(row.get('County', '')).strip()

            if not org or org == 'nan':
                continue

            town = '' if town == 'nan' else town
            county = '' if county == 'nan' else county

            parts = [org]
            if town:
                parts.append(town)
            if county:
                parts.append(county)
            parts.append('careers')

            query = ' '.join(parts)

            queries.append({
                'row_index': idx,
                'organisation_name': org,
                'town': town,
                'county': county,
                'search_query': query
            })

        print(f"✓ Created {len(queries)} queries\n")
        return queries

    async def process_single_query(self, browser, query_data: dict) -> dict:
        """Process one organization's query with random engine selection"""
        query = query_data['search_query']

        # 25% Google, 75% DuckDuckGo (random selection per query)
        use_google = random.random() < 0.25
        engine_used = "google" if use_google else "duckduckgo"

        # Update statistics
        if use_google:
            self.google_count += 1
        else:
            self.duckduckgo_count += 1

        # For Scraping Browser (WebSocket), create simpler context
        # For regular browser, add proxy to context
        if self.use_proxy and self.proxy_config and 'wss://' in str(self.proxy_config.get('server', '')):
            # Scraping Browser - no need to add proxy to context (already handled)
            context_options = {
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
        else:
            # Regular browser - add proxy if configured
            context_options = {
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            if self.use_proxy and self.proxy_config and 'server' in self.proxy_config:
                context_options['proxy'] = self.proxy_config

        context = await browser.new_context(**context_options)

        # Add stealth script
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        page = await context.new_page()

        links = []
        try:
            # Execute search based on randomly selected engine
            if use_google:
                links = await self.search_google(page, query)
            else:
                links = await self.search_duckduckgo(page, query)

            # Engine-specific delays (human-like behavior)
            if use_google:
                delay = random.uniform(15, 40)  # Slower for Google
            else:
                delay = random.uniform(3, 10)  # Faster for DuckDuckGo

            await asyncio.sleep(delay)

        except Exception as e:
            print(f"\n❌ Error for '{query_data['organisation_name']}': {e}")
            # Cool-off delay on error
            await asyncio.sleep(random.uniform(5, 15))

        finally:
            await context.close()

        self.processed_count += 1

        result = {
            'row_index': query_data['row_index'],
            'organisation_name': query_data['organisation_name'],
            'town': query_data['town'],
            'county': query_data['county'],
            'search_query': query,
            'links_found': len(links),
            'search_engine': engine_used
        }

        # Add up to 5 links
        for i, link in enumerate(links[:5], 1):
            result[f'link_{i}_url'] = link['url']
            result[f'link_{i}_title'] = link['title']

        # Fill empty columns if less than 5 links
        for i in range(len(links) + 1, 6):
            result[f'link_{i}_url'] = ''
            result[f'link_{i}_title'] = ''

        return result

    async def process_batch(self, browser, queries: list) -> list:
        """Process batch of queries concurrently"""
        tasks = [self.process_single_query(browser, q) for q in queries]
        return await asyncio.gather(*tasks)

    async def scrape_all(self, queries: list) -> pd.DataFrame:
        """Main scraping function with checkpoint support and random engine selection"""
        print(f"🚀 Starting Enhanced Playwright Scraper")
        print(f"   Concurrent browsers: {self.max_concurrent}")
        print(f"   Engine selection: 25% Google, 75% DuckDuckGo (random per query)")
        print(f"   Proxy enabled: {'✅ YES' if self.use_proxy else '❌ NO'}")
        print(f"   Headless: {self.headless}")
        print(f"   Links per org: 5 (filtered)")
        print(f"   Blocked domains: {len(self.blocked_domains)}")
        print(f"   Total queries: {len(queries)}\n")

        # Check for existing checkpoint
        checkpoint = self.checkpoint_manager.load_checkpoint()
        if checkpoint:
            self.processed_indices = checkpoint['processed_indices']
            queries = [q for q in queries if q['row_index'] not in self.processed_indices]
            print(f"▶️  Resuming: {len(queries)} remaining\n")

        start_time = datetime.now()

        async with async_playwright() as p:
            print("🌐 Launching browser...\n")

            # Check if using Bright Data Scraping Browser (WebSocket URL)
            if self.use_proxy and self.proxy_config and 'wss://' in str(self.proxy_config.get('server', '')):
                # Connect to Bright Data Scraping Browser
                print("🔗 Connecting to Bright Data Scraping Browser...")
                browser = await p.chromium.connect_over_cdp(self.proxy_config['server'])
            else:
                # Regular browser launch with optional HTTP proxy
                browser = await p.chromium.launch(headless=self.headless)

            batch_size = self.max_concurrent
            total_batches = (len(queries) - 1) // batch_size + 1
            checkpoint_interval = 50

            for i in range(0, len(queries), batch_size):
                batch = queries[i:i + batch_size]
                batch_num = i // batch_size + 1

                print(f"⏳ Batch {batch_num}/{total_batches} | "
                      f"Processed: {self.processed_count}/{len(queries)} "
                      f"({self.processed_count / len(queries) * 100:.1f}%) | "
                      f"Google: {self.google_count} | DDG: {self.duckduckgo_count}")

                batch_results = await self.process_batch(browser, batch)
                self.all_results.extend(batch_results)

                # Track processed indices
                for result in batch_results:
                    self.processed_indices.append(result['row_index'])

                # Save checkpoint periodically
                if len(self.processed_indices) % checkpoint_interval == 0:
                    self.checkpoint_manager.save_checkpoint(
                        self.processed_indices,
                        self.all_results
                    )

                if i + batch_size < len(queries):
                    await asyncio.sleep(2)

            await browser.close()

        elapsed = (datetime.now() - start_time).total_seconds()

        print(f"\n✓ Scraping complete!")
        print(f"⏱️  Time: {elapsed / 60:.1f} minutes")
        print(f"📈 Rate: {len(queries) / elapsed:.2f} queries/second")
        print(
            f"🔍 Engine usage: Google {self.google_count} ({self.google_count / (self.google_count + self.duckduckgo_count) * 100:.1f}%), "
            f"DuckDuckGo {self.duckduckgo_count} ({self.duckduckgo_count / (self.google_count + self.duckduckgo_count) * 100:.1f}%)")

        return pd.DataFrame(self.all_results)

    def save_results(self, df: pd.DataFrame, output_path: str):
        """Save final results and clear checkpoint"""
        df.to_excel(output_path, index=False)

        total_links = df['links_found'].sum()
        avg_links = df['links_found'].mean()

        print(f"\n📁 Saved to: {output_path}")
        print(f"\n📊 STATISTICS:")
        print(f"   Organizations: {len(df)}")
        print(f"   Total links found: {total_links}")
        print(f"   Average links per org: {avg_links:.1f}")
        print(f"   Orgs with 0 links: {sum(df['links_found'] == 0)}")
        print(f"   Orgs with 5 links: {sum(df['links_found'] >= 5)}")

        # Clear checkpoint
        self.checkpoint_manager.clear_checkpoint()
        print("\n🗑️  Checkpoint cleared")


async def main():
    print("=" * 80)
    print("  ENHANCED PLAYWRIGHT SCRAPER - Anti-Detection + Random Engine Selection")
    print("=" * 80)
    print()

    # ========== CONFIGURATION ==========
    input_file = r"C:\Users\srkyo\PycharmProjects\Helloworld\Research\Allen Project\2025-10-21_-_Worker_and_Temporary_Worker.xlsx"
    output_file = "raw_career_links_for_llm_Exaustive_part2.xlsx"

    # ========== PROXY CONFIGURATION ==========
    #
    # OPTION 1: Bright Data Scraping Browser (WebSocket) - RECOMMENDED!
    # This auto-solves CAPTCHAs and handles everything automatically
    use_proxy = True  # Set to True to enable
    proxy_config = {
        "server": "wss://brd-customer-hl_8390f0e1-zone-scraping_browser1:i6a86ogk25r5@brd.superproxy.io:9222"
    }

    # OPTION 2: Regular HTTP Proxy (if you don't have Scraping Browser)
    # use_proxy = False
    # proxy_config = {
    #     "server": "http://brd.superproxy.io:33335",
    #     "username": "brd-customer-<customer_id>-zone-<zone-name>",
    #     "password": "<zone-password>"
    # }

    # OPTION 3: No proxy (use your own IP)
    # use_proxy = False
    # proxy_config = None
    # ================================================

    scraper = SimplePlaywrightScraper(
        max_concurrent=3,  # Keep low with Scraping Browser (recommended: 1-5)
        headless=False,  # Note: Scraping Browser is already headless
        search_engine='duckduckgo',
        use_proxy=use_proxy,
        proxy_config=proxy_config
    )

    try:
        df = scraper.load_excel(input_file)
        queries = scraper.create_queries(df)

        # ===== TEST MODE =====
        print("⚠️  TEST MODE: Processing first 20 organizations")
        print("    Comment out line below to process all\n")
        # queries = queries[:20]  # ← REMOVE THIS LINE to process all
        # =====================

        results_df = await scraper.scrape_all(queries)
        scraper.save_results(results_df, output_file)

        print("\n✅ DONE! Now you can use LLM to filter the links.")

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        print("💾 Progress saved in checkpoint. Run again to resume!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":


    asyncio.run(main())

"""
🆕 ANTI-DETECTION FEATURES:
===========================

1. RANDOM ENGINE SELECTION (Per Query):
   - 25% chance of using Google
   - 75% chance of using DuckDuckGo
   - Selection happens RANDOMLY for each query
   - More natural, harder to detect

2. HUMAN-LIKE BEHAVIOR (Google):
   - Random mouse movements (50-400px range)
   - Random scrolling (100-400px delta)
   - Natural pauses (0.5-3 seconds)

3. SMART DELAYS:
   - Google: 15-40 seconds between searches
   - DuckDuckGo: 3-10 seconds between searches
   - Error cooldown: 5-15 seconds on failures

4. AUTOMATIC FALLBACK:
   - If Google fails → automatically tries DuckDuckGo

5. 🌟 BRIGHT DATA SCRAPING BROWSER SUPPORT:
   - Auto-solves CAPTCHAs automatically! 🎯
   - Built-in residential proxy rotation
   - Pre-configured anti-detection
   - WebSocket connection (wss://)
   - NO manual proxy configuration needed
   - Just paste your WebSocket URL!

==========================================
🚀 SETUP WITH YOUR SCRAPING BROWSER:
==========================================

1. Your WebSocket URL format:
   wss://brd-customer-hl_8390f0e1-zone-scraping_browser1:i6a86ogk25r5@brd.superproxy.io:9222

2. In main(), set:
   use_proxy = True
   proxy_config = {
       "server": "wss://YOUR_WEBSOCKET_URL_HERE"
   }

3. Set max_concurrent LOW (1-5 recommended with Scraping Browser)

4. Run script - CAPTCHAs will be solved automatically!

==========================================
📊 PRICING (Bright Data Scraping Browser):
==========================================
- Pay per request (~$3-5 per 1000 requests)
- Much cheaper than residential proxies
- Auto-CAPTCHA solving included
- No monthly commitment needed

==========================================
✅ BENEFITS VS REGULAR PROXY:
==========================================
Regular HTTP Proxy:
  ✓ Reduces CAPTCHA triggers (90%)
  ✗ Still need manual solving if triggered
  ✗ More configuration needed
  ✗ More expensive ($500-1000/month)

Scraping Browser (WebSocket):
  ✓ AUTO-SOLVES CAPTCHAs! 🎯
  ✓ Built-in anti-detection
  ✓ Zero configuration
  ✓ Pay-per-use (cheaper for small jobs)
  ✓ Just works!

==========================================
🧪 TESTING STEPS:
==========================================
1. Copy your WebSocket URL to proxy_config
2. Set use_proxy=True
3. Set max_concurrent=3 (low and safe)
4. Test with 5-10 queries first
5. Watch console for "Connecting to Bright Data Scraping Browser..."
6. If successful, increase batch size gradually

==========================================
⚠️ IMPORTANT NOTES:
==========================================
- Scraping Browser runs remotely (can't see browser UI)
- Keep max_concurrent LOW (1-5) - each connection uses resources
- WebSocket URL includes credentials - keep it private!
- Works with both sync and async Playwright
- CAPTCHAs solved in ~2-5 seconds automatically
- Much more reliable than free methods

USAGE:
------
WITH SCRAPING BROWSER (RECOMMENDED):
scraper = SimplePlaywrightScraper(
    max_concurrent=3,
    use_proxy=True,
    proxy_config={"server": "wss://your-url-here"}
)

WITHOUT PROXY (YOUR CURRENT SETUP):
scraper = SimplePlaywrightScraper(
    max_concurrent=8,
    use_proxy=False
)
"""