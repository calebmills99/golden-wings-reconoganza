#!/usr/bin/env python3
"""
Improved Job Search System - Addresses Glassdoor issues and adds alternatives
"""

import os
import json
import hashlib
import re
import sqlite3
import time
from datetime import datetime
from dataclasses import dataclass
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Import JobSpy for job scraping
try:
    from jobspy import scrape_jobs
    import pandas as pd
    JOBSPY_AVAILABLE = True
except ImportError:
    JOBSPY_AVAILABLE = False
    print("Warning: JobSpy not available")

# Import our data cleaner
from job_data_cleaner import JobDataCleaner

load_dotenv()

@dataclass
class JobListing:
    """Enhanced data class for job listings"""
    job_id: str
    title: str
    company: str
    description: str
    location: str
    salary_range: Optional[str]
    employment_type: Optional[str]
    url: str
    source: str
    date_found: datetime
    relevance_score: int = 0

class ImprovedJobSearchAPI:
    """Improved job search API with Glassdoor alternatives"""

    def __init__(self, db_path: str = r"C:\runb\JobSearchBot\job_search.db"):
        self.db_path = db_path
        self.data_cleaner = JobDataCleaner()
        self._ensure_database()
        print("🔍 Improved Job Search API initialized")

    def _ensure_database(self):
        """Ensure database and table exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            description TEXT,
            location TEXT,
            salary_range TEXT,
            employment_type TEXT,
            source TEXT NOT NULL,
            url TEXT,
            date_found TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            relevance_score INTEGER DEFAULT 0,
            skills_match TEXT,
            missing_skills TEXT,
            red_flags TEXT,
            ai_summary TEXT,
            culture_fit_score INTEGER DEFAULT NULL,
            salary_analysis TEXT,
            status TEXT DEFAULT 'new',
            applied BOOLEAN DEFAULT FALSE,
            resume_generated BOOLEAN DEFAULT FALSE,
            resume_path TEXT,
            cover_letter_path TEXT,
            resume_generated_date TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        conn.commit()
        conn.close()

    def diagnose_glassdoor_issue(self):
        """Diagnose and report Glassdoor integration issues"""
        print("🔍 Diagnosing Glassdoor Integration...")
        
        if not JOBSPY_AVAILABLE:
            print("❌ JobSpy not available - cannot test Glassdoor")
            return False
        
        # Test Glassdoor with different parameters
        test_cases = [
            {"search_term": "software engineer", "location": "Los Angeles"},
            {"search_term": "project manager", "location": "San Francisco"},
            {"search_term": "data analyst", "location": "New York"},
        ]
        
        glassdoor_working = False
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\nTest {i}: {test_case['search_term']} in {test_case['location']}")
            
            try:
                df = scrape_jobs(
                    search_term=test_case["search_term"],
                    location=test_case["location"],
                    results_wanted=3,
                    hours_old=168,  # Increase to 7 days
                    site_name=['glassdoor'],
                    verbose=1
                )
                
                if df is not None and len(df) > 0:
                    print(f"✅ Glassdoor returned {len(df)} results")
                    glassdoor_working = True
                    # Show sample
                    for _, row in df.head(2).iterrows():
                        print(f"  - {row.get('title', 'N/A')} at {row.get('company', 'N/A')}")
                else:
                    print("❌ Glassdoor returned no results")
                    
            except Exception as e:
                print(f"❌ Glassdoor error: {e}")
            
            time.sleep(2)  # Rate limiting
        
        if not glassdoor_working:
            print("\n🚨 GLASSDOOR DIAGNOSIS:")
            print("  - Glassdoor may be blocking requests")
            print("  - Rate limiting may be too aggressive") 
            print("  - Site structure may have changed")
            print("  - Alternative sources recommended")
        
        return glassdoor_working

    def search_with_alternatives(self, query: str, location: str = "Los Angeles", save_to_db: bool = True) -> List[JobListing]:
        """Search jobs with multiple sources including Glassdoor alternatives"""
        print(f"🔍 Multi-source job search for '{query}' in {location}")
        all_jobs = []
        
        if not JOBSPY_AVAILABLE:
            print("❌ JobSpy not available")
            return all_jobs

        # Primary sources (working well)
        primary_sources = ['indeed', 'linkedin']
        
        for source in primary_sources:
            try:
                print(f"\n🔎 Searching {source.title()}...")
                df = scrape_jobs(
                    search_term=query,
                    location=location,
                    results_wanted=20,
                    hours_old=72,
                    site_name=[source],
                    verbose=0
                )
                
                if df is not None and len(df) > 0:
                    jobs = self._process_job_data(df, f"improved_{source}")
                    all_jobs.extend(jobs)
                    print(f"✅ {source.title()}: {len(jobs)} jobs")
                else:
                    print(f"❌ {source.title()}: No results")
                    
            except Exception as e:
                print(f"❌ {source.title()} error: {e}")
            
            time.sleep(2)  # Rate limiting

        # Try Glassdoor with enhanced parameters
        try:
            print(f"\n🔎 Searching Glassdoor (Enhanced)...")
            df = scrape_jobs(
                search_term=query,
                location=location,
                results_wanted=15,
                hours_old=168,  # 7 days instead of 3
                site_name=['glassdoor'],
                verbose=0
            )
            
            if df is not None and len(df) > 0:
                jobs = self._process_job_data(df, "improved_glassdoor")
                all_jobs.extend(jobs)
                print(f"✅ Glassdoor (Enhanced): {len(jobs)} jobs")
            else:
                print("❌ Glassdoor (Enhanced): No results")
                
        except Exception as e:
            print(f"❌ Glassdoor (Enhanced) error: {e}")

        # Alternative: Try ZipRecruiter if available
        try:
            print(f"\n🔎 Searching ZipRecruiter...")
            df = scrape_jobs(
                search_term=query,
                location=location,
                results_wanted=10,
                hours_old=72,
                site_name=['zip_recruiter'],
                verbose=0
            )
            
            if df is not None and len(df) > 0:
                jobs = self._process_job_data(df, "ziprecruiter")
                all_jobs.extend(jobs)
                print(f"✅ ZipRecruiter: {len(jobs)} jobs")
            else:
                print("❌ ZipRecruiter: No results")
                
        except Exception as e:
            print(f"❌ ZipRecruiter error: {e}")

        # Deduplicate and save
        unique_jobs = self._remove_duplicates(all_jobs)
        print(f"\n📊 Found {len(all_jobs)} total jobs, {len(unique_jobs)} unique")
        
        if save_to_db and unique_jobs:
            saved_count = self._save_jobs_to_db(unique_jobs)
            print(f"💾 Saved {saved_count} new jobs to database")

        return unique_jobs

    def _process_job_data(self, df: pd.DataFrame, source_prefix: str = "improved") -> List[JobListing]:
        """Process DataFrame with enhanced data cleaning"""
        jobs = []
        
        for _, row in df.iterrows():
            try:
                # Create initial job data
                job_data = {
                    'title': str(row.get('title', '')),
                    'company': str(row.get('company', '')),
                    'description': str(row.get('description', ''))[:2000] if pd.notna(row.get('description')) else "No description available",
                    'location': str(row.get('location', '')),
                    'url': str(row.get('job_url', '')),
                    'salary_range': None,
                    'employment_type': None
                }
                
                # Extract salary info from JobSpy data
                salary_min = row.get('min_amount', '')
                salary_max = row.get('max_amount', '')
                if salary_min and salary_max:
                    job_data['salary_range'] = f"${salary_min}-${salary_max}"
                elif salary_min:
                    job_data['salary_range'] = f"${salary_min}+"

                # Clean the job data using our enhanced cleaner
                cleaned_job = self.data_cleaner.clean_job_data(job_data)
                
                # Create unique job ID
                job_url = cleaned_job['url']
                job_id = hashlib.md5(job_url.encode()).hexdigest()[:12]
                
                job_listing = JobListing(
                    job_id=f"{source_prefix}_{job_id}",
                    title=cleaned_job['title'],
                    company=cleaned_job['company'],
                    description=cleaned_job['description'],
                    location=cleaned_job['location'] or job_data['location'],
                    salary_range=cleaned_job.get('salary_range'),
                    employment_type=cleaned_job.get('employment_type'),
                    url=cleaned_job['url'],
                    source=f"{source_prefix}_{row.get('site', 'unknown')}",
                    date_found=datetime.now(),
                    relevance_score=self._calculate_relevance(cleaned_job['title'], cleaned_job['description'])
                )
                
                jobs.append(job_listing)

            except Exception as e:
                print(f"Error processing job row: {e}")
                continue
        
        return jobs

    def _calculate_relevance(self, title: str, description: str) -> int:
        """Calculate job relevance score based on keywords"""
        tech_keywords = [
            'python', 'javascript', 'java', 'sql', 'aws', 'docker', 'kubernetes',
            'react', 'nodejs', 'api', 'database', 'cloud', 'devops', 'git',
            'project management', 'scrum', 'agile', 'coordinator'
        ]
        
        text = f"{title} {description}".lower()
        matches = sum(1 for keyword in tech_keywords if keyword in text)
        
        # Convert to percentage (max 100%)
        return min(100, (matches * 8) + 20)

    def _remove_duplicates(self, jobs: List[JobListing]) -> List[JobListing]:
        """Remove duplicate jobs"""
        seen_hashes = set()
        unique_jobs = []
        
        for job in jobs:
            job_hash = self.data_cleaner.calculate_job_hash(job.title, job.company, job.location)
            if job_hash not in seen_hashes:
                seen_hashes.add(job_hash)
                unique_jobs.append(job)
        
        return unique_jobs

    def _save_jobs_to_db(self, jobs: List[JobListing]) -> int:
        """Save jobs to database"""
        if not jobs:
            return 0
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        saved_count = 0
        
        for job in jobs:
            try:
                cursor.execute('''
                INSERT OR IGNORE INTO jobs (
                    job_id, title, company, description, location, 
                    salary_range, employment_type, source, url, date_found,
                    relevance_score, status, applied, resume_generated,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    job.job_id, job.title, job.company, job.description, job.location,
                    job.salary_range, job.employment_type, job.source, job.url, job.date_found,
                    job.relevance_score, 'new', False, False,
                    datetime.now(), datetime.now()
                ))
                
                if cursor.rowcount > 0:
                    saved_count += 1
                    
            except sqlite3.IntegrityError:
                # Job already exists
                continue
        
        conn.commit()
        conn.close()
        
        return saved_count

    def get_source_performance(self) -> Dict:
        """Analyze performance of different job sources"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT source, COUNT(*) as count,
                   AVG(relevance_score) as avg_relevance,
                   COUNT(CASE WHEN salary_range IS NOT NULL THEN 1 END) as with_salary
            FROM jobs 
            WHERE date_found >= datetime('now', '-7 days')
            GROUP BY source 
            ORDER BY count DESC
        """)
        
        results = cursor.fetchall()
        
        performance = {}
        for source, count, avg_rel, with_salary in results:
            performance[source] = {
                'job_count': count,
                'avg_relevance': round(avg_rel, 1) if avg_rel else 0,
                'salary_coverage': round((with_salary / count) * 100, 1) if count > 0 else 0
            }
        
        conn.close()
        return performance

if __name__ == "__main__":
    # Test the improved system
    api = ImprovedJobSearchAPI()
    
    # Diagnose Glassdoor
    print("🔧 GLASSDOOR DIAGNOSTIC TEST")
    glassdoor_works = api.diagnose_glassdoor_issue()
    
    if not glassdoor_works:
        print("\n🔧 ALTERNATIVE SEARCH TEST")
        jobs = api.search_with_alternatives("project manager", "Los Angeles")
        
        print(f"\n📊 PERFORMANCE ANALYSIS")
        performance = api.get_source_performance()
        for source, metrics in performance.items():
            print(f"{source}:")
            print(f"  Jobs: {metrics['job_count']}")
            print(f"  Avg Relevance: {metrics['avg_relevance']}%")
            print(f"  Salary Coverage: {metrics['salary_coverage']}%")