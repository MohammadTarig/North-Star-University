import logging
from datetime import datetime

from job_scraper import JobScraper
from skill_extractor import SkillExtractor

logging.basicConfig(level=logging.INFO)

def run_pipeline():
    """Run pipeline with default parameters"""
    print("🚀 Starting Job Skills Analysis Pipeline...")
        
    # 1. Scrape jobs
    print("\n1. Scraping jobs...")
    scraper = JobScraper(output_file=f"jobs.json")
    
    jobs = scraper.scrape_jobs({
        "query": "AI Engineer", # example query
        "page": "1",
        "num_pages": "1",
        "country": "US",
        "date_posted": "today",
        "language": "en",
        "fields": "job_id,job_title,employer_name,job_description"
    })
    
    if not jobs:
        print("No jobs found. Exiting.")
        return
    
    print(f"✓ Scraped {len(jobs)} jobs")
    
    # 2. Extract skills
    print("\n2. Extracting skills from job descriptions...")
    extractor = SkillExtractor(output_file=f"skills.json")
    skills = extractor.extract_from_jobs(jobs)
    
    print(f"✓ Extracted {len(skills['hard_skills'])} hard skills, {len(skills['soft_skills'])} soft skills")
    
    # 3. Generate summary
    print("\n3. Generating analysis summary...")
    
    summary = extractor.generate_summary(skills)
    
    # Save summary
    with open(f"summary.txt", 'w') as f:
        f.write(summary)
    
    print("\n" + "="*50)
    print("📊 ANALYSIS COMPLETE")

if __name__ == "__main__":    
    run_pipeline()
