#!/usr/bin/env python3
"""
Enhanced Job Search API Module - Multi-source job searching with improved data quality
"""

import os
import json
import hashlib
import re
import sqlite3
from datetime import datetime
from dataclasses import dataclass
from typing import List, Dict, Optional
from dotenv import load_dotenv
import logging

# Import JobSpy for job scraping
from jobspy import scrape_jobs
import pandas as pd

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
    skills_match: List[str] = None
    missing_skills: List[str] = None
    red_flags: List[str] = None
    ai_summary: Optional[str] = None
    culture_fit_score: Optional[int] = None
    salary_analysis: Optional[str] = None
    status: str = 'new'
    applied: bool = False
    resume_generated: bool = False

class EnhancedJobSearchAPI:
    """Enhanced job search API handler with improved data quality"""

    def __init__(self, db_path: str = r"C:\runb\JobSearchBot\job_search.db"):
        self.db_path = db_path
        self.data_cleaner = JobDataCleaner()
        self._ensure_database()
        print("🔍 Enhanced JobSpy API handler initialized with data cleaning")

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

    def _get_existing_jobs(self) -> List[dict]:
        """Get existing jobs for deduplication"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT title, company, location FROM jobs")
        jobs = cursor.fetchall()
        
        existing_jobs = []
        for job in jobs:
            existing_jobs.append({
                'title': job[0],
                'company': job[1],
                'location': job[2]
            })
        
        conn.close()
        return existing_jobs

    def _save_jobs_to_db(self, jobs: List[JobListing]) -> int:
        """Save jobs to database with duplicate checking"""
        if not jobs:
            return 0
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        saved_count = 0
        existing_jobs = self._get_existing_jobs()
        
        for job in jobs:
            job_data = {
                'title': job.title,
                'company': job.company,
                'location': job.location,
                'description': job.description,
                'salary_range': job.salary_range,
                'employment_type': job.employment_type,
                'url': job.url
            }
            
            # Check for duplicates
            if not self.data_cleaner.is_duplicate_job(job_data, existing_jobs):
                try:
                    cursor.execute('''
                    INSERT OR IGNORE INTO jobs (
                        job_id, title, company, description, location, 
                        salary_range, employment_type, source, url, date_found,
                        relevance_score, ai_summary, status, applied, resume_generated,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        job.job_id, job.title, job.company, job.description, job.location,
                        job.salary_range, job.employment_type, job.source, job.url, job.date_found,
                        job.relevance_score, job.ai_summary, job.status, job.applied, job.resume_generated,
                        datetime.now(), datetime.now()
                    ))
                    
                    if cursor.rowcount > 0:
                        saved_count += 1
                        existing_jobs.append(job_data)  # Add to list for future duplicate checks
                        
                except sqlite3.IntegrityError:
                    # Job already exists (duplicate job_id)
                    continue
        
        conn.commit()
        conn.close()
        
        return saved_count

    def _process_job_data(self, df: pd.DataFrame, source_prefix: str = "jobspy") -> List[JobListing]:
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
                
                # Calculate relevance score (simple keyword matching)
                relevance_score = self._calculate_relevance(cleaned_job['title'], cleaned_job['description'])
                
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
                    relevance_score=relevance_score,
                    ai_summary=f"Processed with enhanced data cleaning. Relevance: {relevance_score}%"
                )
                
                jobs.append(job_listing)

            except Exception as e:
                print(f"Error processing job row: {e}")
                continue
        
        return jobs

    def _calculate_relevance(self, title: str, description: str) -> int:
        """Calculate job relevance score based on keywords"""
        # Simple keyword-based scoring - can be enhanced with ML
        tech_keywords = [
            'python', 'javascript', 'java', 'sql', 'aws', 'docker', 'kubernetes',
            'react', 'nodejs', 'api', 'database', 'cloud', 'devops', 'git'
        ]
        
        text = f"{title} {description}".lower()
        matches = sum(1 for keyword in tech_keywords if keyword in text)
        
        # Convert to percentage (max 100%)
        return min(100, (matches * 10) + 10)

    def search_all_sites(self, query: str, location: str = "Los Angeles", save_to_db: bool = True) -> List[JobListing]:
        """Search jobs across multiple sites with enhanced data processing"""
        jobs = []

        try:
            print(f"🔍 Searching for '{query}' in {location} using Enhanced JobSpy...")

            df = scrape_jobs(
                search_term=query,
                location=location,
                results_wanted=25,  # Increased results
                hours_old=72,
                country_indeed='USA',
                verbose=0
            )

            if df is not None and len(df) > 0:
                jobs = self._process_job_data(df, "jobspy_multi")
                
                if save_to_db:
                    saved_count = self._save_jobs_to_db(jobs)
                    print(f"✅ Enhanced JobSpy found {len(jobs)} jobs, saved {saved_count} new jobs to database")
                else:
                    print(f"✅ Enhanced JobSpy found {len(jobs)} jobs")

        except Exception as e:
            print(f"❌ Enhanced JobSpy search failed: {e}")

        return jobs

    def search_indeed(self, query: str, location: str = "Los Angeles", save_to_db: bool = True) -> List[JobListing]:
        """Search jobs on Indeed with enhanced processing"""
        jobs = []

        try:
            print(f"🔍 Searching Indeed (Enhanced) for '{query}' in {location}...")

            df = scrape_jobs(
                search_term=query,
                location=location,
                results_wanted=20,
                hours_old=72,
                site_name=['indeed'],
                country_indeed='USA',
                verbose=0
            )

            if df is not None and len(df) > 0:
                jobs = self._process_job_data(df, "enhanced_indeed")
                
                if save_to_db:
                    saved_count = self._save_jobs_to_db(jobs)
                    print(f"✅ Found {len(jobs)} Indeed jobs, saved {saved_count} new jobs to database")
                else:
                    print(f"✅ Found {len(jobs)} Indeed jobs")

        except Exception as e:
            print(f"❌ Enhanced Indeed search failed: {e}")

        return jobs

    def search_linkedin(self, query: str, location: str = "Los Angeles", save_to_db: bool = True) -> List[JobListing]:
        """Search jobs on LinkedIn with enhanced processing"""
        jobs = []

        try:
            print(f"🔍 Searching LinkedIn (Enhanced) for '{query}' in {location}...")

            df = scrape_jobs(
                search_term=query,
                location=location,
                results_wanted=20,
                hours_old=72,
                site_name=['linkedin'],
                verbose=0
            )

            if df is not None and len(df) > 0:
                jobs = self._process_job_data(df, "enhanced_linkedin")
                
                if save_to_db:
                    saved_count = self._save_jobs_to_db(jobs)
                    print(f"✅ Found {len(jobs)} LinkedIn jobs, saved {saved_count} new jobs to database")
                else:
                    print(f"✅ Found {len(jobs)} LinkedIn jobs")

        except Exception as e:
            print(f"❌ Enhanced LinkedIn search failed: {e}")

        return jobs

    def search_glassdoor(self, query: str, location: str = "Los Angeles", save_to_db: bool = True) -> List[JobListing]:
        """Search jobs on Glassdoor with enhanced processing"""
        jobs = []

        try:
            print(f"🔍 Searching Glassdoor (Enhanced) for '{query}' in {location}...")

            df = scrape_jobs(
                search_term=query,
                location=location,
                results_wanted=15,
                hours_old=72,
                site_name=['glassdoor'],
                verbose=0
            )

            if df is not None and len(df) > 0:
                jobs = self._process_job_data(df, "enhanced_glassdoor")
                
                if save_to_db:
                    saved_count = self._save_jobs_to_db(jobs)
                    print(f"✅ Found {len(jobs)} Glassdoor jobs, saved {saved_count} new jobs to database")
                else:
                    print(f"✅ Found {len(jobs)} Glassdoor jobs")

        except Exception as e:
            print(f"❌ Enhanced Glassdoor search failed: {e}")

        return jobs

    def clean_existing_database(self):
        """Clean existing database using the data cleaner"""
        from job_data_cleaner import DatabaseCleaner
        
        print("🧹 Starting database cleanup...")
        db_cleaner = DatabaseCleaner(self.db_path)
        
        print("1. Cleaning existing data...")
        db_cleaner.clean_existing_data()
        
        print("2. Removing duplicates...")
        db_cleaner.remove_duplicates()
        
        print("✅ Database cleanup completed!")

    def get_job_stats(self) -> Dict:
        """Get enhanced job statistics from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stats = {}
        
        # Basic counts
        cursor.execute("SELECT COUNT(*) FROM jobs")
        stats['total_jobs'] = cursor.fetchone()[0]
        
        # Jobs with enhanced data
        cursor.execute("SELECT COUNT(*) FROM jobs WHERE salary_range IS NOT NULL AND salary_range != ''")
        stats['jobs_with_salary'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM jobs WHERE employment_type IS NOT NULL AND employment_type != ''")
        stats['jobs_with_employment_type'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM jobs WHERE company != 'Company Name Not Found'")
        stats['jobs_with_valid_company'] = cursor.fetchone()[0]
        
        # Source breakdown
        cursor.execute("SELECT source, COUNT(*) FROM jobs GROUP BY source ORDER BY COUNT(*) DESC")
        stats['jobs_by_source'] = cursor.fetchall()
        
        # Data quality percentages
        if stats['total_jobs'] > 0:
            stats['salary_coverage'] = (stats['jobs_with_salary'] / stats['total_jobs']) * 100
            stats['employment_type_coverage'] = (stats['jobs_with_employment_type'] / stats['total_jobs']) * 100
            stats['company_name_coverage'] = (stats['jobs_with_valid_company'] / stats['total_jobs']) * 100
        
        conn.close()
        return stats


if __name__ == "__main__":
    # Example usage
    api = EnhancedJobSearchAPI()
    
    # Search for jobs
    jobs = api.search_all_sites("python developer", "Los Angeles")
    
    # Get statistics
    stats = api.get_job_stats()
    print("\n📊 Database Statistics:")
    print(f"Total jobs: {stats['total_jobs']}")
    print(f"Salary coverage: {stats.get('salary_coverage', 0):.1f}%")
    print(f"Employment type coverage: {stats.get('employment_type_coverage', 0):.1f}%")
    print(f"Valid company names: {stats.get('company_name_coverage', 0):.1f}%")