import sqlite3
import pandas as pd
import numpy as np
import requests
import pickle
import base64
from pathlib import Path
from typing import Optional
import sys
import os
sys.path.append(r'c:\Users\srkyo\PycharmProjects\Helloworld\Research\Allen Project\Link Fetching\Trying 2\job-search-platform\integrations')
import location_tagger


class JobEmbeddingGenerator:
    """Separate class for generating and managing job embeddings"""

    def __init__(self, db_path: str = "jobs.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        """Create necessary database tables"""
        cursor = self.conn.cursor()

        # Main jobs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organisation_name TEXT,
                org_location TEXT,
                career_page_available TEXT,
                career_page_url TEXT,
                validation_reason TEXT,
                application_type TEXT,
                job_title TEXT,
                job_description TEXT,
                job_link TEXT,
                location TEXT,
                salary TEXT,
                dateposted TEXT,
                job_category_id INTEGER,
                remote_type TEXT,
                experience_level TEXT,
                job_type_id INTEGER,
                job_source TEXT,
                company_url TEXT,
                is_active INTEGER DEFAULT 1,
                views_count INTEGER DEFAULT 0,
                embedding_vector BLOB,
                embedding_dimension INTEGER,
                embedding_base64 TEXT
            )
        """)

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_is_active ON jobs(is_active)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_location ON jobs(location)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_remote_type ON jobs(remote_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_experience_level ON jobs(experience_level)")

        self.conn.commit()

    def import_from_excel(self, excel_file: str, force_reimport: bool = False):
        """Import jobs from Excel file"""
        print(f"📊 Importing data from {excel_file}...")

        df = pd.read_excel(excel_file)
        df = df[df['JOB_TITLE'].notna() & (df['JOB_TITLE'].str.strip() != '')]
        df.columns = df.columns.str.strip()

        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM jobs")
        existing_count = cursor.fetchone()[0]

        if existing_count > 0 and force_reimport:
            print(f"⚠️ Database already has {existing_count} jobs. Clearing...")
            cursor.execute("DELETE FROM jobs")
            self.conn.commit()
        elif existing_count > 0:
            print(f"⚠️ Database already has {existing_count} jobs. Skipping import.")
            return

        records = df.to_dict('records')
        inserted = 0
        embeddings_loaded = 0

        for record in records:
            try:
                # Check if embedding exists in Excel
                embedding_b64 = record.get('EMBEDDING_BASE64') or record.get('embedding_base64')
                embedding_blob = None
                embedding_dim = None

                if embedding_b64 and isinstance(embedding_b64, str) and len(embedding_b64) > 0:
                    try:
                        embedding_blob = base64.b64decode(embedding_b64)
                        embedding = pickle.loads(embedding_blob)
                        embedding_dim = len(embedding)
                        embeddings_loaded += 1
                    except Exception:
                        pass
                        
                # Tag location
                is_uk = False
                is_london = False
                loc_val = record.get('LOCATION')
                if loc_val and isinstance(loc_val, str):
                    is_uk, is_london = location_tagger.tag_location(loc_val)

                cursor.execute("""
                    INSERT INTO jobs (
                        organisation_name, org_location, career_page_available,
                        career_page_url, validation_reason, application_type,
                        job_title, job_description, job_link, location, salary, dateposted,
                        job_category_id, remote_type, experience_level,
                        job_type_id, job_source, company_url, is_active, views_count,
                        embedding_vector, embedding_dimension, embedding_base64,
                        exists_in_uk, exists_in_london
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record.get('ORGANISATION_NAME'),
                    record.get('ORG_LOCATION'),
                    str(record.get('CAREER_PAGE_AVAILABLE', '')),
                    record.get('CAREER_PAGE_URL'),
                    record.get('VALIDATION_REASON'),
                    record.get('APPLICATION_TYPE'),
                    record.get('JOB_TITLE'),
                    record.get('JOB_DESCRIPTION'),
                    record.get('JOB_LINK'),
                    record.get('LOCATION'),
                    record.get('SALARY'),
                    record.get('DATEPOSTED'),
                    record.get('JOB_CATEGORY_ID'),
                    record.get('REMOTE_TYPE'),
                    record.get('EXPERIENCE_LEVEL'),
                    record.get('JOB_TYPE_ID'),
                    record.get('JOB_SOURCE'),
                    record.get('COMPANY_URL'),
                    1 if str(record.get('IS_ACTIVE', 'TRUE')).upper() == 'TRUE' else 0,
                    int(record.get('VIEWS_COUNT', 0)) if pd.notna(record.get('VIEWS_COUNT')) else 0,
                    embedding_blob,
                    embedding_dim,
                    embedding_b64,
                    1 if is_uk else 0,
                    1 if is_london else 0
                ))
                inserted += 1
            except Exception as e:
                print(f"⚠️ Error inserting record: {e}")
                continue

        self.conn.commit()
        print(f"✅ Imported {inserted}/{len(records)} jobs successfully!")
        if embeddings_loaded > 0:
            print(f"📦 Loaded {embeddings_loaded} existing embeddings from Excel")

    def generate_job_description(self, job_title: str, org_name: str, location: str,
                                 model: str = "gemma3:4b-it-q4_K_M") -> Optional[str]:
        """Generate a job description using Ollama"""
        try:
            prompt = f"""You are a professional job description writer. Write ONLY the job description text. Do not include any labels, options, introductions, or formatting.

    Job Title: {job_title}
    Company: {org_name}
    Location: {location}

    Write a concise, professional job description in exactly 2-3 sentences. Include typical responsibilities and requirements.

    Output the description text ONLY. No "Option 1", no "Here is", no markdown, no extra text."""

            response = requests.post(
                'http://localhost:11434/api/generate',
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,  # Lower = more focused
                        "num_predict": 120,
                        "top_p": 0.9,
                        "stop": ["\n\n", "Option", "**", "###"]  # Stop at formatting
                    }
                },
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                description = result.get('response', '').strip()

                # Clean up any remaining artifacts
                description = description.replace("Here is", "").replace("Here's", "")
                description = description.replace("Option 1", "").replace("(Concise)", "")
                description = description.replace(":", "", 1).strip()  # Remove first colon
                description = description.strip('"').strip("'").strip()
                print(description)

                return description if description else None
            return None
        except Exception as e:
            print(f"⚠️ Error generating description: {e}")
            return None

    def get_ollama_embedding(self, text: str, model: str = "embeddinggemma:latest"):
        """Get embedding from Ollama API"""
        try:
            response = requests.post(
                'http://localhost:11434/api/embed',
                json={"model": model, "input": text},
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                if 'embeddings' in result and len(result['embeddings']) > 0:
                    return result['embeddings'][0]
                elif 'embedding' in result:
                    return result['embedding']
            return None
        except Exception as e:
            print(f"⚠️ Error getting embedding: {e}")
            return None

    def generate_embeddings(self,
                            batch_size: int = 10,
                            embedding_model: str = "embeddinggemma:latest",
                            description_model: str = "gemma3:4b-it-q4_K_M",
                            use_descriptions: bool = True,
                            generate_descriptions: bool = True):
        """
        Generate embeddings for jobs

        Args:
            batch_size: Number of jobs to process at once
            embedding_model: Ollama model for embeddings
            description_model: Ollama model for generating descriptions
            use_descriptions: Whether to include descriptions in embeddings
            generate_descriptions: Whether to generate missing descriptions
        """
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT id, job_title, job_description, organisation_name, location, 
                   experience_level, remote_type
            FROM jobs
            WHERE embedding_vector IS NULL AND is_active = 1
            ORDER BY id
        """)

        jobs_without_embeddings = cursor.fetchall()
        total_jobs = len(jobs_without_embeddings)

        print(f"Found {total_jobs} jobs without embeddings")
        print(f"Mode: {'WITH' if use_descriptions else 'WITHOUT'} descriptions")

        if generate_descriptions and use_descriptions:
            cursor.execute("""
                SELECT COUNT(*) FROM jobs 
                WHERE (job_description IS NULL OR job_description = '') 
                AND is_active = 1
            """)
            jobs_without_desc = cursor.fetchone()[0]
            if jobs_without_desc > 0:
                print(f"📝 {jobs_without_desc} jobs need descriptions")

        for i in range(0, total_jobs, batch_size):
            batch = jobs_without_embeddings[i:i + batch_size]

            for job in batch:
                job_id = job['id']
                job_title = job['job_title'] or ''
                job_desc = job['job_description'] or ''
                org_name = job['organisation_name'] or ''
                location = job['location'] or ''
                exp_level = job['experience_level'] or ''
                remote = job['remote_type'] or ''

                # Generate description if needed
                if generate_descriptions and use_descriptions and not job_desc:
                    if job_title and org_name:
                        print(f"   📝 Generating description for: {job_title[:40]}...")
                        job_desc = self.generate_job_description(
                            job_title, org_name, location, description_model
                        ) or ''

                        if job_desc:
                            cursor.execute("""
                                UPDATE jobs SET job_description = ? WHERE id = ?
                            """, (job_desc, job_id))
                            self.conn.commit()

                # Create embedding text (job_title only, descriptions stored but not used)
                text = f"{job_title} {job_desc} {org_name} {location} {exp_level} {remote}".strip()

                if not text or len(text) < 3:
                    print(f"⊘ Skipped job {job_id}: No meaningful text")
                    continue

                embedding = self.get_ollama_embedding(text, embedding_model)

                if embedding:
                    embedding_blob = pickle.dumps(embedding)
                    embedding_b64 = base64.b64encode(embedding_blob).decode('utf-8')

                    cursor.execute("""
                        UPDATE jobs
                        SET embedding_vector = ?,
                            embedding_dimension = ?,
                            embedding_base64 = ?
                        WHERE id = ?
                    """, (embedding_blob, len(embedding), embedding_b64, job_id))

                    self.conn.commit()

                    title_preview = job_title[:50] if job_title else 'No Title'
                    print(f"✓ Processed job {job_id}: {title_preview}")
                else:
                    print(f"✗ Failed to get embedding for job {job_id}")

            batch_num = (i // batch_size) + 1
            total_batches = (total_jobs + batch_size - 1) // batch_size
            print(f"\nCompleted batch {batch_num}/{total_batches}")

        print("\n✅ Embedding generation complete!")

    def export_to_excel(self, output_file: str = "jobs_with_embeddings.xlsx"):
        """Export jobs with embeddings to Excel"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM jobs WHERE is_active = 1")

        columns = [description[0] for description in cursor.description]
        data = cursor.fetchall()

        df = pd.DataFrame(data, columns=columns)
        df = df.drop(['embedding_vector'], axis=1, errors='ignore')

        df.to_excel(output_file, index=False)
        print(f"✅ Exported {len(df)} jobs to {output_file}")

    def close(self):
        """Close database connection"""
        self.conn.close()


# Usage Example
if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("JOB EMBEDDING GENERATOR")
    print("=" * 70)

    generator = JobEmbeddingGenerator(db_path="jobs.db")

    # Import from Excel
    generator.import_from_excel(
        excel_file=r"C:\Users\srkyo\PycharmProjects\Helloworld\Research\Allen Project\Link Fetching\Trying 2\LLM Extract\career_scraping_results_with_descriptions - Copy.xlsx",
        force_reimport=False
    )

    # Generate embeddings WITHOUT descriptions in embeddings
    # (descriptions will be generated and stored, but only job_title used for embeddings)
    generator.generate_embeddings(
        batch_size=5,
        embedding_model="embeddinggemma:latest",
        description_model="gemma3:4b-it-q4_K_M",
        use_descriptions=True,  # Don't include descriptions in embeddings
        generate_descriptions=True  # But still generate and store them
    )

    # Export results
    generator.export_to_excel("jobs_with_embeddings.xlsx")

    generator.close()