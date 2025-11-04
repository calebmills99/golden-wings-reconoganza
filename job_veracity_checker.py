#!/usr/bin/env python3
"""
Job Posting Veracity Checker - Analyzes job postings for authenticity and quality
"""

import sqlite3
import re
import requests
from urllib.parse import urlparse
from datetime import datetime, timedelta
import time

class JobVeracityChecker:
    """Comprehensive job posting verification system"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.suspicious_patterns = {
            'fake_companies': [
                'company name not found', 'indeed', 'linkedin', 'glassdoor', 
                'ziprecruiter', 'jobs', 'careers', 'employment'
            ],
            'suspicious_titles': [
                'make money fast', 'work from home easy', '$5000/week',
                'no experience needed', 'guaranteed income'
            ],
            'spam_indicators': [
                'click here now', 'limited time offer', 'act fast',
                'too good to be true', 'guaranteed success'
            ]
        }
        
    def check_database_veracity(self):
        """Comprehensive database verification check"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        print("🔍 JOB POSTING VERACITY CHECK")
        print("=" * 50)
        
        # Get total job count
        cursor.execute("SELECT COUNT(*) FROM jobs")
        total_jobs = cursor.fetchone()[0]
        print(f"📊 Total jobs in database: {total_jobs}")
        
        if total_jobs == 0:
            print("❌ No jobs found in database")
            conn.close()
            return
        
        # Check recent jobs
        print(f"\n📅 Recent Job Analysis (Last 7 days)")
        cursor.execute("""
            SELECT COUNT(*) FROM jobs 
            WHERE date_found >= datetime('now', '-7 days')
        """)
        recent_jobs = cursor.fetchone()[0]
        print(f"Recent jobs: {recent_jobs}")
        
        # Sample recent jobs for detailed analysis
        print(f"\n🔬 DETAILED ANALYSIS OF RECENT JOBS")
        cursor.execute("""
            SELECT id, title, company, url, description, salary_range, source, date_found
            FROM jobs 
            ORDER BY date_found DESC 
            LIMIT 10
        """)
        
        jobs = cursor.fetchall()
        verified_jobs = 0
        suspicious_jobs = 0
        
        for i, job in enumerate(jobs, 1):
            job_id, title, company, url, description, salary, source, date = job
            print(f"\n--- Job {i}/{len(jobs)} ---")
            print(f"ID: {job_id}")
            print(f"Title: {title}")
            print(f"Company: {company}")
            print(f"Source: {source}")
            print(f"Date: {date}")
            print(f"URL: {url[:80]}..." if len(url) > 80 else f"URL: {url}")
            
            # Verify job authenticity
            verification_result = self._verify_job(job_id, title, company, url, description, salary, source)
            
            if verification_result['is_suspicious']:
                suspicious_jobs += 1
                print(f"🚨 SUSPICIOUS: {', '.join(verification_result['issues'])}")
            else:
                verified_jobs += 1
                print(f"✅ VERIFIED: Appears legitimate")
                
            if verification_result['quality_score']:
                print(f"📊 Quality Score: {verification_result['quality_score']}/10")
        
        # Summary statistics
        print(f"\n📈 VERACITY SUMMARY")
        print(f"✅ Verified jobs: {verified_jobs}/{len(jobs)} ({verified_jobs/len(jobs)*100:.1f}%)")
        print(f"🚨 Suspicious jobs: {suspicious_jobs}/{len(jobs)} ({suspicious_jobs/len(jobs)*100:.1f}%)")
        
        # Additional database analysis
        self._analyze_database_patterns(cursor)
        
        conn.close()
        
    def _verify_job(self, job_id, title, company, url, description, salary, source):
        """Verify individual job posting"""
        result = {
            'is_suspicious': False,
            'issues': [],
            'quality_score': 0
        }
        
        quality_points = 0
        max_points = 10
        
        # Check company name
        if self._is_suspicious_company(company):
            result['issues'].append("Suspicious company name")
            result['is_suspicious'] = True
        else:
            quality_points += 2
            
        # Check job title
        if self._is_suspicious_title(title):
            result['issues'].append("Suspicious job title")
            result['is_suspicious'] = True
        else:
            quality_points += 2
            
        # Check description
        if description and len(description) > 50:
            if self._contains_spam_indicators(description):
                result['issues'].append("Contains spam indicators")
                result['is_suspicious'] = True
            else:
                quality_points += 2
        else:
            result['issues'].append("Missing or poor description")
            
        # Check URL validity
        if self._is_valid_url(url):
            quality_points += 2
        else:
            result['issues'].append("Invalid or suspicious URL")
            
        # Check salary information
        if salary and salary.strip():
            quality_points += 1
            
        # Check source legitimacy
        if source and any(legitimate in source.lower() for legitimate in ['jobspy', 'indeed', 'linkedin', 'glassdoor']):
            quality_points += 1
        
        result['quality_score'] = quality_points
        
        return result
        
    def _is_suspicious_company(self, company):
        """Check if company name appears suspicious"""
        if not company:
            return True
            
        company_lower = company.lower().strip()
        return any(suspicious in company_lower for suspicious in self.suspicious_patterns['fake_companies'])
        
    def _is_suspicious_title(self, title):
        """Check if job title appears suspicious"""
        if not title:
            return True
            
        title_lower = title.lower()
        return any(suspicious in title_lower for suspicious in self.suspicious_patterns['suspicious_titles'])
        
    def _contains_spam_indicators(self, description):
        """Check if description contains spam indicators"""
        if not description:
            return False
            
        desc_lower = description.lower()
        return any(spam in desc_lower for spam in self.suspicious_patterns['spam_indicators'])
        
    def _is_valid_url(self, url):
        """Basic URL validation"""
        try:
            parsed = urlparse(url)
            return all([parsed.scheme, parsed.netloc])
        except:
            return False
            
    def _analyze_database_patterns(self, cursor):
        """Analyze database for patterns that might indicate issues"""
        print(f"\n🔍 DATABASE PATTERN ANALYSIS")
        
        # Duplicate URL analysis
        cursor.execute("""
            SELECT url, COUNT(*) as count 
            FROM jobs 
            GROUP BY url 
            HAVING COUNT(*) > 1 
            ORDER BY count DESC 
            LIMIT 5
        """)
        duplicates = cursor.fetchall()
        
        if duplicates:
            print(f"🔄 Found {len(duplicates)} duplicate URLs:")
            for url, count in duplicates:
                print(f"  {count}x: {url[:60]}...")
        else:
            print("✅ No duplicate URLs found")
            
        # Source distribution
        cursor.execute("""
            SELECT source, COUNT(*) as count 
            FROM jobs 
            GROUP BY source 
            ORDER BY count DESC
        """)
        sources = cursor.fetchall()
        
        print(f"\n📊 Jobs by Source:")
        for source, count in sources:
            print(f"  {source}: {count}")
            
        # Company distribution
        cursor.execute("""
            SELECT company, COUNT(*) as count 
            FROM jobs 
            WHERE company != 'Company Name Not Found'
            GROUP BY company 
            HAVING COUNT(*) > 2
            ORDER BY count DESC 
            LIMIT 10
        """)
        companies = cursor.fetchall()
        
        print(f"\n🏢 Top Companies (2+ jobs):")
        for company, count in companies:
            print(f"  {company}: {count}")
            
        # Date distribution
        cursor.execute("""
            SELECT DATE(date_found) as date, COUNT(*) as count 
            FROM jobs 
            GROUP BY DATE(date_found) 
            ORDER BY date DESC 
            LIMIT 7
        """)
        dates = cursor.fetchall()
        
        print(f"\n📅 Jobs by Date (Last 7 days):")
        for date, count in dates:
            print(f"  {date}: {count}")

def main():
    """Main execution function"""
    db_path = "job_search.db"
    
    try:
        checker = JobVeracityChecker(db_path)
        checker.check_database_veracity()
        
    except Exception as e:
        print(f"❌ Error checking job veracity: {e}")

if __name__ == "__main__":
    main()