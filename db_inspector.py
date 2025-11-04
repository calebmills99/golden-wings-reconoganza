#!/usr/bin/env python3
"""
Database Inspector for job_search.db
"""

import sqlite3
import json
from datetime import datetime

def inspect_database(db_path):
    """Inspect the job search database"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get table schema
        print("=== DATABASE SCHEMA ===")
        cursor.execute("PRAGMA table_info(jobs)")
        schema = cursor.fetchall()
        
        print("Jobs table schema:")
        for col in schema:
            col_name, col_type, not_null, default, pk = col[1], col[2], col[3], col[4], col[5]
            nullable = "NOT NULL" if not_null else "NULLABLE"
            primary_key = " (PRIMARY KEY)" if pk else ""
            default_val = f" DEFAULT {default}" if default else ""
            print(f"  {col_name}: {col_type} {nullable}{default_val}{primary_key}")
        
        # Get row count
        cursor.execute("SELECT COUNT(*) FROM jobs")
        row_count = cursor.fetchone()[0]
        print(f"\nTotal jobs in database: {row_count}")
        
        if row_count > 0:
            # Get sample data
            print("\n=== SAMPLE DATA ===")
            cursor.execute("SELECT * FROM jobs LIMIT 3")
            sample_jobs = cursor.fetchall()
            
            # Get column names for display
            column_names = [desc[0] for desc in cursor.description]
            
            for i, job in enumerate(sample_jobs, 1):
                print(f"\nJob {i}:")
                for col_name, value in zip(column_names, job):
                    if isinstance(value, str) and len(value) > 100:
                        display_value = value[:100] + "..."
                    else:
                        display_value = value
                    print(f"  {col_name}: {display_value}")
            
            # Get statistics
            print("\n=== DATABASE STATISTICS ===")
            
            # Jobs by source
            cursor.execute("SELECT source, COUNT(*) FROM jobs GROUP BY source ORDER BY COUNT(*) DESC")
            sources = cursor.fetchall()
            print("Jobs by source:")
            for source, count in sources:
                print(f"  {source}: {count}")
            
            # Jobs by date (last 7 days)
            cursor.execute("""
                SELECT DATE(date_found) as date, COUNT(*) 
                FROM jobs 
                WHERE date_found >= date('now', '-7 days')
                GROUP BY DATE(date_found) 
                ORDER BY date DESC
            """)
            recent_jobs = cursor.fetchall()
            if recent_jobs:
                print("\nJobs added by date (last 7 days):")
                for date, count in recent_jobs:
                    print(f"  {date}: {count}")
            
            # Top companies
            cursor.execute("SELECT company, COUNT(*) FROM jobs GROUP BY company ORDER BY COUNT(*) DESC LIMIT 5")
            top_companies = cursor.fetchall()
            print("\nTop companies:")
            for company, count in top_companies:
                print(f"  {company}: {count}")
            
            # Salary information
            cursor.execute("SELECT COUNT(*) FROM jobs WHERE salary_range IS NOT NULL AND salary_range != ''")
            jobs_with_salary = cursor.fetchone()[0]
            salary_percentage = (jobs_with_salary / row_count) * 100 if row_count > 0 else 0
            print(f"\nJobs with salary information: {jobs_with_salary} ({salary_percentage:.1f}%)")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error inspecting database: {e}")
        return False

if __name__ == "__main__":
    db_path = r"C:\runb\JobSearchBot\job_search.db"
    inspect_database(db_path)