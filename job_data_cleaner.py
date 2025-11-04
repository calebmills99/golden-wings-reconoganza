#!/usr/bin/env python3
"""
Job Data Cleaner - Enhanced data processing utilities for job search database
"""

import re
import html
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlparse
import sqlite3
from datetime import datetime

class JobDataCleaner:
    """Comprehensive data cleaning utilities for job listings"""
    
    def __init__(self):
        # Employment type patterns
        self.employment_patterns = {
            'full_time': [
                r'\bfull.?time\b', r'\bft\b', r'\bpermanent\b', r'\bfull.?time.?position\b'
            ],
            'part_time': [
                r'\bpart.?time\b', r'\bpt\b', r'\bpart.?time.?position\b'
            ],
            'contract': [
                r'\bcontract\b', r'\bcontractor\b', r'\bc2h\b', r'\bcontract.?to.?hire\b',
                r'\btemporary\b', r'\btemp\b', r'\bfreelance\b'
            ],
            'internship': [
                r'\bintern\b', r'\binternship\b', r'\bstudent\b'
            ],
            'remote': [
                r'\bremote\b', r'\bwork.?from.?home\b', r'\bwfh\b', r'\btelecommute\b'
            ]
        }
        
        # Salary patterns
        self.salary_patterns = [
            # $75k-$155k, $75,000-$155,000
            r'\$\d{1,3}[k,]\s*[-–]\s*\$\d{1,3}[k,]',
            r'\$\d{1,3},?\d{3}\s*[-–]\s*\$\d{1,3},?\d{3}',
            # $75k+, $75,000+
            r'\$\d{1,3}[k,]\+',
            r'\$\d{1,3},?\d{3}\+',
            # Up to $75k, Up to $75,000
            r'up\s+to\s+\$\d{1,3}[k,]',
            r'up\s+to\s+\$\d{1,3},?\d{3}',
            # Starting at $75k
            r'starting\s+at\s+\$\d{1,3}[k,]',
            r'starting\s+at\s+\$\d{1,3},?\d{3}',
        ]
        
        # Company name cleanup patterns
        self.company_cleanup_patterns = [
            (r'\s+\|\s+Indeed$', ''),
            (r'\s+\|\s+LinkedIn$', ''),
            (r'\s+\|\s+Glassdoor$', ''),
            (r'\s+Jobs,?\s+Employment.*$', ''),
            (r'\s+Careers?.*$', ''),
            (r'^\d+\s+', ''),  # Remove leading numbers
        ]

    def clean_html_content(self, text: str) -> str:
        """Clean HTML entities and tags from text content"""
        if not text or not isinstance(text, str):
            return ""
        
        # Decode HTML entities
        text = html.unescape(text)
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', text)
        
        # Clean up common HTML artifacts
        text = re.sub(r'&\w+;', ' ', text)  # Remove remaining entities
        text = re.sub(r'\s+', ' ', text)     # Normalize whitespace
        text = text.strip()
        
        return text

    def extract_company_name(self, title: str, company: str, url: str = "") -> str:
        """Enhanced company name extraction and cleaning"""
        if not company or company.strip() == "":
            return "Company Name Not Found"
        
        # If company is already clean and valid
        if company and not any(phrase in company.lower() for phrase in 
                              ['company name not found', 'indeed', 'linkedin', 'glassdoor', 'jobs']):
            cleaned = company.strip()
            # Apply cleanup patterns
            for pattern, replacement in self.company_cleanup_patterns:
                cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
            
            if cleaned.strip() and len(cleaned.strip()) > 2:
                return cleaned.strip()
        
        # Try to extract from title
        if title:
            # Look for "at CompanyName" pattern
            at_match = re.search(r'\bat\s+([A-Za-z][A-Za-z\s&\.,-]{2,50})', title, re.IGNORECASE)
            if at_match:
                candidate = at_match.group(1).strip()
                # Clean up the candidate
                for pattern, replacement in self.company_cleanup_patterns:
                    candidate = re.sub(pattern, replacement, candidate, flags=re.IGNORECASE)
                if candidate and len(candidate) > 2:
                    return candidate
        
        # Try to extract from URL domain
        if url:
            try:
                domain = urlparse(url).netloc.lower()
                if domain and not domain.startswith('www.'):
                    domain_parts = domain.split('.')
                    if len(domain_parts) >= 2:
                        company_candidate = domain_parts[0].replace('-', ' ').title()
                        if company_candidate not in ['Indeed', 'LinkedIn', 'Glassdoor', 'Jobs']:
                            return company_candidate
            except:
                pass
        
        return company or "Company Name Not Found"

    def parse_salary_info(self, title: str, description: str) -> Optional[str]:
        """Extract salary information from title and description"""
        text = f"{title} {description}".lower()
        
        for pattern in self.salary_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                salary = match.group(0)
                # Normalize salary format
                salary = re.sub(r'\s+', ' ', salary)
                return salary.strip()
        
        return None

    def detect_employment_type(self, title: str, description: str) -> str:
        """Detect employment type from title and description"""
        text = f"{title} {description}".lower()
        
        detected_types = []
        
        for emp_type, patterns in self.employment_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    detected_types.append(emp_type)
                    break
        
        # Prioritize employment types
        if 'internship' in detected_types:
            return 'internship'
        elif 'contract' in detected_types:
            return 'contract'
        elif 'part_time' in detected_types:
            return 'part_time'
        elif 'full_time' in detected_types:
            return 'full_time'
        elif 'remote' in detected_types:
            return 'remote'
        
        # Default to full_time if nothing detected but contains "position" or "job"
        if re.search(r'\b(position|job|role|opportunity)\b', text, re.IGNORECASE):
            return 'full_time'
        
        return ''

    def calculate_job_hash(self, title: str, company: str, location: str) -> str:
        """Calculate a hash for deduplication based on normalized job data"""
        # Normalize strings for comparison
        norm_title = re.sub(r'\W+', '', title.lower()) if title else ''
        norm_company = re.sub(r'\W+', '', company.lower()) if company else ''
        norm_location = re.sub(r'\W+', '', location.lower()) if location else ''
        
        # Create a combined string for hashing
        combined = f"{norm_title}_{norm_company}_{norm_location}"
        return combined

    def is_duplicate_job(self, job_data: dict, existing_jobs: List[dict]) -> bool:
        """Check if job is a duplicate based on normalized comparison"""
        current_hash = self.calculate_job_hash(
            job_data.get('title', ''),
            job_data.get('company', ''),
            job_data.get('location', '')
        )
        
        for existing_job in existing_jobs:
            existing_hash = self.calculate_job_hash(
                existing_job.get('title', ''),
                existing_job.get('company', ''),
                existing_job.get('location', '')
            )
            
            if current_hash == existing_hash:
                return True
                
            # Additional similarity check for very similar jobs
            title_similarity = self._calculate_similarity(
                job_data.get('title', '').lower(),
                existing_job.get('title', '').lower()
            )
            company_match = (job_data.get('company', '').lower().strip() == 
                           existing_job.get('company', '').lower().strip())
            
            if title_similarity > 0.8 and company_match:
                return True
        
        return False

    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings using simple word overlap"""
        if not str1 or not str2:
            return 0.0
        
        words1 = set(re.findall(r'\w+', str1.lower()))
        words2 = set(re.findall(r'\w+', str2.lower()))
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0

    def clean_job_data(self, job_data: dict) -> dict:
        """Comprehensive cleaning of job data"""
        cleaned = job_data.copy()
        
        # Clean HTML content
        if 'title' in cleaned:
            cleaned['title'] = self.clean_html_content(cleaned['title'])
        if 'description' in cleaned:
            cleaned['description'] = self.clean_html_content(cleaned['description'])
        
        # Enhance company name
        cleaned['company'] = self.extract_company_name(
            cleaned.get('title', ''),
            cleaned.get('company', ''),
            cleaned.get('url', '')
        )
        
        # Parse salary if not already present
        if not cleaned.get('salary_range'):
            salary = self.parse_salary_info(
                cleaned.get('title', ''),
                cleaned.get('description', '')
            )
            if salary:
                cleaned['salary_range'] = salary
        
        # Detect employment type if not present
        if not cleaned.get('employment_type'):
            emp_type = self.detect_employment_type(
                cleaned.get('title', ''),
                cleaned.get('description', '')
            )
            cleaned['employment_type'] = emp_type
        
        return cleaned


class DatabaseCleaner:
    """Database-specific cleaning operations"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.cleaner = JobDataCleaner()
    
    def clean_existing_data(self):
        """Clean all existing data in the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get all jobs
            cursor.execute("SELECT * FROM jobs")
            jobs = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            
            print(f"Processing {len(jobs)} jobs...")
            cleaned_count = 0
            
            for job_row in jobs:
                job_dict = dict(zip(columns, job_row))
                original_job = job_dict.copy()
                
                # Clean the job data
                cleaned_job = self.cleaner.clean_job_data(job_dict)
                
                # Check if anything changed
                changes = []
                for key in ['title', 'company', 'description', 'salary_range', 'employment_type']:
                    if cleaned_job.get(key) != original_job.get(key):
                        changes.append(key)
                
                if changes:
                    # Update the database
                    update_sql = """
                    UPDATE jobs SET 
                        title = ?, company = ?, description = ?, 
                        salary_range = ?, employment_type = ?, updated_at = ?
                    WHERE id = ?
                    """
                    cursor.execute(update_sql, (
                        cleaned_job['title'],
                        cleaned_job['company'], 
                        cleaned_job['description'],
                        cleaned_job.get('salary_range'),
                        cleaned_job.get('employment_type'),
                        datetime.now().isoformat(),
                        job_dict['id']
                    ))
                    cleaned_count += 1
                    
                    if cleaned_count % 10 == 0:
                        print(f"Cleaned {cleaned_count} jobs...")
            
            conn.commit()
            print(f"✅ Successfully cleaned {cleaned_count} jobs")
            
        except Exception as e:
            conn.rollback()
            print(f"❌ Error cleaning database: {e}")
        finally:
            conn.close()

    def remove_duplicates(self):
        """Remove duplicate jobs from the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get all jobs ordered by date (keep newest)
            cursor.execute("SELECT * FROM jobs ORDER BY date_found DESC")
            jobs = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            
            seen_hashes = set()
            duplicate_ids = []
            
            print(f"Checking {len(jobs)} jobs for duplicates...")
            
            for job_row in jobs:
                job_dict = dict(zip(columns, job_row))
                job_hash = self.cleaner.calculate_job_hash(
                    job_dict.get('title', ''),
                    job_dict.get('company', ''),
                    job_dict.get('location', '')
                )
                
                if job_hash in seen_hashes:
                    duplicate_ids.append(job_dict['id'])
                else:
                    seen_hashes.add(job_hash)
            
            if duplicate_ids:
                # Remove duplicates
                cursor.execute(f"DELETE FROM jobs WHERE id IN ({','.join(['?'] * len(duplicate_ids))})", 
                              duplicate_ids)
                conn.commit()
                print(f"✅ Removed {len(duplicate_ids)} duplicate jobs")
            else:
                print("✅ No duplicates found")
                
        except Exception as e:
            conn.rollback()
            print(f"❌ Error removing duplicates: {e}")
        finally:
            conn.close()


if __name__ == "__main__":
    db_path = r"C:\runb\JobSearchBot\job_search.db"
    
    print("🧹 Starting database cleanup...")
    db_cleaner = DatabaseCleaner(db_path)
    
    print("\n1. Cleaning existing data...")
    db_cleaner.clean_existing_data()
    
    print("\n2. Removing duplicates...")
    db_cleaner.remove_duplicates()
    
    print("\n✅ Database cleanup completed!")