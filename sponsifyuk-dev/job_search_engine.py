import pickle
import re
import sqlite3
from typing import List, Dict, Optional
from datetime import datetime
import numpy as np
import requests


class JobSearchEngine:
    """Separate class for searching jobs using embeddings"""

    def __init__(self, db_path: str = "jobs.db"):
        self.db_path = db_path
        self._initialize_database()

    def _get_connection(self):
        """Get a new connection for current thread"""
        conn = sqlite3.connect(self.db_path, timeout=5.0)
        conn.execute("PRAGMA busy_timeout = 5000;")
        conn.row_factory = sqlite3.Row
        return conn

    # Map category IDs to representative job-title keywords used in SQL LIKE filters
    CATEGORY_KEYWORDS = {
        '1':  ['software', 'developer', 'engineer', 'devops', 'cloud', 'data', 'IT', 'cyber', 'network', 'architect', 'QA', 'machine learning', 'AI'],
        '2':  ['manager', 'director', 'operations', 'strategy', 'business', 'consultant', 'executive', 'CEO', 'COO', 'VP', 'head of'],
        '4':  ['finance', 'accountant', 'accounting', 'audit', 'tax', 'treasury', 'CFO', 'financial', 'investment', 'actuary'],
        '5':  ['marketing', 'sales', 'SEO', 'content', 'brand', 'communications', 'PR', 'advertising', 'copywriter', 'growth'],
        '6':  ['designer', 'design', 'UX', 'UI', 'creative', 'graphic', 'illustrator', 'motion', 'art director', 'visual'],
        '7':  ['nurse', 'doctor', 'healthcare', 'clinical', 'pharmacist', 'therapist', 'medical', 'biotech', 'laboratory', 'GP'],
        '8':  ['construction', 'manufacturing', 'trades', 'electrician', 'plumber', 'carpenter', 'fabrication', 'civil', 'site manager'],
        '9':  ['scientist', 'researcher', 'research', 'biology', 'chemistry', 'physics', 'R&D', 'lab', 'ecology'],
        '10': ['teacher', 'lecturer', 'tutor', 'education', 'training', 'instructor', 'professor', 'curriculum', 'school'],
        '11': ['lawyer', 'solicitor', 'legal', 'barrister', 'compliance', 'policy', 'paralegal', 'counsel', 'regulatory'],
        '12': ['logistics', 'supply chain', 'warehouse', 'transport', 'driver', 'freight', 'procurement', 'fleet', 'shipping'],
        '13': ['retail', 'hospitality', 'hotel', 'restaurant', 'tourism', 'chef', 'barista', 'store manager', 'customer service'],
        '14': ['HR', 'human resources', 'recruiter', 'talent', 'payroll', 'admin', 'office manager', 'PA', 'coordinator'],
        '15': ['security', 'CCTV', 'guard', 'police', 'risk', 'investigator', 'protective', 'fire safety', 'surveillance'],
        '16': ['agriculture', 'sustainability', 'renewable', 'energy', 'environment', 'green', 'farming', 'carbon', 'solar'],
        '17': ['media', 'entertainment', 'gaming', 'journalist', 'editor', 'producer', 'film', 'broadcast', 'animator'],
    }

    def _apply_category_filter(self, sql: str, params: list, filters: dict) -> tuple:
        """Translate a numeric category filter into SQL LIKE job_title conditions.
        Also handles the special 'remote_global' category."""
        cat = str(filters.get('category', '')).strip() if filters else ''
        if not cat:
            return sql, params
        if cat == 'remote_global':
            return sql + ' AND exists_in_uk = 0', params
        keywords = self.CATEGORY_KEYWORDS.get(cat)
        if not keywords:
            return sql, params
        conditions = ' OR '.join(['LOWER(job_title) LIKE ?' for _ in keywords])
        sql += f' AND ({conditions})'
        params.extend([f'%{kw.lower()}%' for kw in keywords])
        return sql, params

    def _initialize_database(self):
        """One-time setup of FTS tables and triggers"""
        conn = self._get_connection()
        try:
            self._create_fts_tables(conn)
        finally:
            conn.close()

    def _create_fts_tables(self, conn):
        """Create FTS5 tables for full-text search"""
        cursor = conn.cursor()

        # Create FTS5 virtual table (without job_description for search)
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS jobs_fts USING fts5(
                job_title,
                organisation_name,
                location,
                remote_type,
                experience_level,
                content=jobs,
                content_rowid=id
            )
        """)

        # Create triggers to keep FTS table in sync
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS jobs_ai AFTER INSERT ON jobs BEGIN
                INSERT INTO jobs_fts(rowid, job_title, organisation_name, location, remote_type, experience_level)
                VALUES (new.id, new.job_title, new.organisation_name, new.location, new.remote_type, new.experience_level);
            END
        """)

        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS jobs_ad AFTER DELETE ON jobs BEGIN
                DELETE FROM jobs_fts WHERE rowid = old.id;
            END
        """)

        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS jobs_au AFTER UPDATE ON jobs BEGIN
                UPDATE jobs_fts SET 
                    job_title = new.job_title,
                    organisation_name = new.organisation_name,
                    location = new.location,
                    remote_type = new.remote_type,
                    experience_level = new.experience_level
                WHERE rowid = old.id;
            END
        """)

        conn.commit()

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

    def preprocess_query(self, query: str) -> str:
        """Clean and prepare search query"""
        query = re.sub(r'[^\w\s]', ' ', query.lower())
        return ' '.join(query.split())

    def bm25_search(self, query: str, limit: int = 50, filters: Dict = None) -> List[Dict]:
        """Perform BM25 full-text search (job_title + org_name only)"""
        processed_query = self.preprocess_query(query)
        query_words = processed_query.split()
        # Scope match to job_title column only — prevents company names from polluting results
        fts_query = 'job_title : (' + ' OR '.join(query_words) + ')'

        sql = """
            SELECT 
                j.*,
                fts.rank as bm25_score,
                CASE WHEN LOWER(j.job_title) = LOWER(?) THEN 1 ELSE 0 END as exact_match
            FROM jobs_fts fts
            JOIN jobs j ON fts.rowid = j.id
            WHERE jobs_fts MATCH ?
            AND j.is_active = 1
        """

        params = [processed_query, fts_query]

        # Add filters
        if filters:
            if filters.get('location'):
                sql += " AND j.location LIKE ?"
                params.append(f"%{filters['location']}%")
            if filters.get('org_location'):
                sql += " AND j.org_location LIKE ?"
                params.append(f"%{filters['org_location']}%")
            if filters.get('experience_level'):
                sql += " AND j.experience_level = ?"
                params.append(filters['experience_level'])
            if filters.get('remote_type'):
                sql += " AND j.remote_type = ?"
                params.append(filters['remote_type'])
            if filters.get('job_source'):
                sql += " AND j.job_source = ?"
                params.append(filters['job_source'])
            if filters.get('organisation_name'):
                sql += " AND j.organisation_name LIKE ?"
            sql, params = self._apply_category_filter(sql, params, filters)

        sql += f" ORDER BY j.exists_in_london DESC, j.exists_in_uk DESC, exact_match DESC, j.has_description DESC, bm25_score LIMIT {limit}"

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, params)

            results = []
            for i, row in enumerate(cursor.fetchall(), 1):
                result = dict(row)
                result['rank'] = i
                result['bm25_score'] = abs(result['bm25_score']) if result['bm25_score'] else 0
                results.append(result)

            return results
        except Exception as e:
            print(f"BM25 search error: {e}")
            return []
        finally:
            conn.close()

    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)

        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def semantic_search(self, query: str, limit: int = 50, filters: Dict = None) -> List[Dict]:
        """Perform semantic search (embeddings based on job_title only)"""
        query_embedding = self.get_ollama_embedding(query)

        if query_embedding is None:
            print("Warning: Could not get query embedding")
            return []

        sql = """
            SELECT *
            FROM jobs
            WHERE is_active = 1
            AND embedding_vector IS NOT NULL
        """

        params = []

        if filters:
            if filters.get('location'):
                sql += " AND location LIKE ?"
                params.append(f"%{filters['location']}%")
            if filters.get('org_location'):
                sql += " AND org_location LIKE ?"
                params.append(f"%{filters['org_location']}%")
            if filters.get('experience_level'):
                sql += " AND experience_level = ?"
                params.append(filters['experience_level'])
            if filters.get('remote_type'):
                sql += " AND remote_type = ?"
                params.append(filters['remote_type'])
            if filters.get('job_source'):
                sql += " AND job_source = ?"
                params.append(filters['job_source'])
            if filters.get('organisation_name'):
                sql += " AND organisation_name LIKE ?"
            sql, params = self._apply_category_filter(sql, params, filters)

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, params)

            results = []
            for row in cursor.fetchall():
                job_data = dict(row)
                job_embedding = pickle.loads(job_data['embedding_vector'])
                similarity = self.cosine_similarity(query_embedding, job_embedding)
                job_data['semantic_score'] = similarity
                results.append(job_data)

            results.sort(key=lambda x: x['semantic_score'], reverse=True)

            for i, result in enumerate(results[:limit], 1):
                result['rank'] = i

            return results[:limit]
        finally:
            conn.close()

    def rrf_score(self, rank: int, k: int = 60) -> float:
        """Calculate Reciprocal Rank Fusion score"""
        return 1.0 / (k + rank)

    def hybrid_search(self, query: str, limit: int = 20, filters: Dict = None,
                      min_score_threshold: float = 0.15) -> List[Dict]:
        """Perform hybrid search combining BM25 and semantic search"""

        # If query is empty, just return filtered results without scoring
        if not query or query.strip() == '':
            return self.get_filtered_jobs(limit=limit, filters=filters)

        bm25_results = self.bm25_search(query, limit=50, filters=filters)
        semantic_results = self.semantic_search(query, limit=50, filters=filters)

        # Adaptive weighting
        if len(bm25_results) == 0 and len(semantic_results) > 0:
            bm25_weight, semantic_weight = 0.0, 1.0
        elif len(bm25_results) > 0 and len(semantic_results) == 0:
            bm25_weight, semantic_weight = 1.0, 0.0
        else:
            bm25_weight, semantic_weight = 0.3, 0.7

        bm25_dict = {r['id']: {'data': r, 'rank': r['rank']} for r in bm25_results}
        semantic_dict = {r['id']: {'data': r, 'rank': r['rank']} for r in semantic_results}

        all_job_ids = set(bm25_dict.keys()) | set(semantic_dict.keys())

        scored_results = []
        for job_id in all_job_ids:
            bm25_rank = bm25_dict.get(job_id, {}).get('rank', len(bm25_results) + 1)
            semantic_rank = semantic_dict.get(job_id, {}).get('rank', len(semantic_results) + 1)

            bm25_rrf = self.rrf_score(bm25_rank)
            semantic_rrf = self.rrf_score(semantic_rank)

            hybrid_score = (bm25_weight * bm25_rrf) + (semantic_weight * semantic_rrf)

            job_data = bm25_dict.get(job_id, {}).get('data') or semantic_dict.get(job_id, {}).get('data')

            if job_data:
                job_data['hybrid_score'] = hybrid_score
                job_data['bm25_rank'] = bm25_rank if bm25_rank <= len(bm25_results) else None
                job_data['semantic_rank'] = semantic_rank if semantic_rank <= len(semantic_results) else None

                semantic_data = semantic_dict.get(job_id, {}).get('data')
                if semantic_data and 'semantic_score' in semantic_data:
                    job_data['semantic_similarity'] = semantic_data['semantic_score']

                scored_results.append(job_data)

        # Primary sort: London first, then UK, then exact keyword match, then description presence, then hybrid score
        scored_results.sort(key=lambda x: (
            x.get('exists_in_london', 0),
            x.get('exists_in_uk', 0),
            1 if x.get('job_title', '').lower().strip() == query.lower().strip() else 0,
            x.get('has_description', 0),
            x.get('hybrid_score', 0)
        ), reverse=True)

        # More lenient filtering - only apply threshold if query is specific
        if min_score_threshold > 0 and len(query.split()) > 2:
            filtered_results = [r for r in scored_results if r['hybrid_score'] >= min_score_threshold]
        else:
            filtered_results = scored_results

        # Always return at least some results if available
        if len(filtered_results) == 0 and len(scored_results) > 0:
            return scored_results[:limit]

        return filtered_results[:limit]

    def get_filtered_jobs(self, limit: int = 100, filters: Dict = None, sort_by: str = 'relevance') -> List[Dict]:
        """Get jobs with filters but no search query (for browsing with smart sorting and filtering)"""

        sql = """
            SELECT *
            FROM jobs
            WHERE is_active = 1
            AND job_link IS NOT NULL
            AND job_link != ''
        """

        params = []

        # FILTER OUT COURSES AND TRAINING
        course_keywords = [
            'course', 'training', 'apprentice', 'internship', 'graduate scheme',
            'placement', 'work experience', 'student', 'learner', 'trainee',
            'bootcamp', 'certification', 'diploma', 'degree programme'
        ]

        for keyword in course_keywords:
            sql += f" AND LOWER(job_title) NOT LIKE '%{keyword}%'"

        # Apply user filters
        if filters:
            if filters.get('location'):
                sql += " AND location LIKE ?"
                params.append(f"%{filters['location']}%")
            if filters.get('org_location'):
                sql += " AND org_location LIKE ?"
                params.append(f"%{filters['org_location']}%")
            if filters.get('experience_level'):
                sql += " AND experience_level = ?"
                params.append(filters['experience_level'])
            if filters.get('remote_type'):
                sql += " AND remote_type = ?"
                params.append(filters['remote_type'])
            if filters.get('job_source'):
                sql += " AND job_source = ?"
                params.append(filters['job_source'])
            if filters.get('organisation_name'):
                sql += " AND organisation_name LIKE ?"
                params.append(f"%{filters['organisation_name']}%")
            sql, params = self._apply_category_filter(sql, params, filters)

        # SMART SORTING
        if sort_by == 'relevance':
            # Relevance = Recent + Popular + Has description
            sql += """
            ORDER BY 
                exists_in_london DESC,
                exists_in_uk DESC,
                has_description DESC,
                added_at DESC, job_title ASC,
                views_count DESC,
                CASE WHEN salary IS NOT NULL AND salary != '' THEN 0 ELSE 1 END,
                id DESC
            """
        elif sort_by == 'date':
            sql += " ORDER BY exists_in_london DESC, exists_in_uk DESC, added_at DESC, job_title ASC"
        elif sort_by == 'popular':
            sql += " ORDER BY exists_in_london DESC, exists_in_uk DESC, views_count DESC, added_at DESC"
        elif sort_by == 'company':
            sql += " ORDER BY exists_in_london DESC, exists_in_uk DESC, organisation_name ASC, added_at DESC"
        else:
            sql += " ORDER BY exists_in_london DESC, exists_in_uk DESC, added_at DESC, job_title ASC"

        sql += f" LIMIT {limit}"

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, params)

            results = []
            for row in cursor.fetchall():
                result = dict(row)
                result['hybrid_score'] = 1.0  # Default score for consistency

                # Calculate quality score for ranking
                quality_score = 0.0

                # Recent job bonus
                if result.get('dateposted'):
                    try:
                        posted_date = datetime.fromisoformat(result['dateposted'])
                        days_old = (datetime.now() - posted_date).days
                        if days_old < 7:
                            quality_score += 0.3
                        elif days_old < 30:
                            quality_score += 0.2
                        elif days_old < 60:
                            quality_score += 0.1
                    except:
                        pass

                # Has description bonus
                if result.get('job_description') and len(result['job_description']) > 100:
                    quality_score += 0.2

                # Has salary bonus
                if result.get('salary') and result['salary'] not in ['Not Specified', '']:
                    quality_score += 0.15

                # Has views (popular) bonus
                if result.get('views_count', 0) > 0:
                    quality_score += min(0.15, result['views_count'] / 1000)

                # Remote/Hybrid preference
                if result.get('remote_type') in ['Remote', 'Hybrid']:
                    quality_score += 0.1

                result['quality_score'] = quality_score
                results.append(result)

            return results
        finally:
            conn.close()

    def search(self, query: str, limit: int = 20, filters: Dict = None,
               min_score: float = 0.15, sort_by: str = 'relevance') -> List[Dict]:
        """Main search interface with improved handling"""

        # For empty queries or browsing, use simple filtering with sorting
        if not query or query.strip() == '':
            return self.get_filtered_jobs(limit=limit, filters=filters, sort_by=sort_by)

        # For actual searches, use hybrid search with lower threshold
        adjusted_min_score = min_score
        if len(query.split()) <= 2:
            adjusted_min_score = max(0.05, min_score * 0.5)

        results = self.hybrid_search(
            query,
            limit=limit * 2,  # Get more results to filter
            filters=filters,
            min_score_threshold=adjusted_min_score
        )

        # FILTER OUT COURSES from search results too
        course_keywords = [
            'course', 'training', 'apprentice', 'internship', 'graduate scheme',
            'placement', 'work experience', 'student', 'learner', 'trainee'
        ]

        filtered_results = []
        for job in results:
            job_title_lower = job.get('job_title', '').lower()
            is_course = any(keyword in job_title_lower for keyword in course_keywords)

            if not is_course:
                filtered_results.append(job)

            if len(filtered_results) >= limit:
                break

        return filtered_results

    def get_filter_options(self) -> Dict:
        """Get available filter options from database"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            filters = {}

            # Get unique values for each filter
            cursor.execute(
                "SELECT DISTINCT location FROM jobs WHERE is_active = 1 AND location IS NOT NULL ORDER BY location")
            filters['locations'] = [row[0] for row in cursor.fetchall()]

            cursor.execute(
                "SELECT DISTINCT org_location FROM jobs WHERE is_active = 1 AND org_location IS NOT NULL ORDER BY org_location")
            filters['org_locations'] = [row[0] for row in cursor.fetchall()]

            cursor.execute(
                "SELECT DISTINCT remote_type FROM jobs WHERE is_active = 1 AND remote_type IS NOT NULL ORDER BY remote_type")
            filters['remote_types'] = [row[0] for row in cursor.fetchall()]

            cursor.execute(
                "SELECT DISTINCT experience_level FROM jobs WHERE is_active = 1 AND experience_level IS NOT NULL ORDER BY experience_level")
            filters['experience_levels'] = [row[0] for row in cursor.fetchall()]

            cursor.execute(
                "SELECT DISTINCT job_source FROM jobs WHERE is_active = 1 AND job_source IS NOT NULL ORDER BY job_source")
            filters['job_sources'] = [row[0] for row in cursor.fetchall()]

            cursor.execute(
                "SELECT DISTINCT organisation_name FROM jobs WHERE is_active = 1 AND organisation_name IS NOT NULL ORDER BY organisation_name")
            filters['organisations'] = [row[0] for row in cursor.fetchall()]

            return filters
        finally:
            conn.close()

    def get_job_by_id(self, job_id: int) -> Optional[Dict]:
        """Get a specific job by ID"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM jobs WHERE id = ? AND is_active = 1", (job_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def increment_view_count(self, job_id: int):
        """Increment view count for a job"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE jobs SET views_count = views_count + 1 WHERE id = ?", (job_id,))
            conn.commit()
        finally:
            conn.close()

    def close(self):
        """Cleanup method (no longer needed but kept for compatibility)"""
        pass


# Usage Example
if __name__ == "__main__":
    search_engine = JobSearchEngine(db_path="jobs.db")

    # Get available filters
    filters = search_engine.get_filter_options()
    print("Available Filters:")
    print(f"  Locations: {len(filters['locations'])}")
    print(f"  Remote Types: {filters['remote_types']}")
    print(f"  Experience Levels: {filters['experience_levels']}")

    # Browse (empty query)
    print("\n" + "=" * 80)
    print("BROWSING (No search query)")
    results = search_engine.search(query='', limit=20, sort_by='relevance')
    print(f"Found {len(results)} jobs")
    for i, job in enumerate(results[:5], 1):
        print(f"{i}. {job['job_title']} at {job['organisation_name']}")
        print(f"   Quality: {job.get('quality_score', 0):.2f}")

    # Search
    print("\n" + "=" * 80)
    print("SEARCHING: 'python developer'")
    results = search_engine.search(
        query="python developer",
        limit=10,
        filters={'remote_type': 'Remote'},
        min_score=0.05
    )

    # Display results
    for i, job in enumerate(results, 1):
        print(f"\n{i}. {job['job_title']}")
        print(f"   Company: {job['organisation_name']}")
        print(f"   Location: {job['location']} | Remote: {job['remote_type']}")
        print(f"   Score: {job['hybrid_score']:.4f}")

    search_engine.close()
