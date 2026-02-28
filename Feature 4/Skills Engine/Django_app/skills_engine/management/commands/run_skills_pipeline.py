from django.core.management.base import BaseCommand
from django.conf import settings
import logging

from skills_engine.job_scraper import JobScraper
from skills_engine.skill_extractor import SkillExtractor

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Run the complete skills analysis pipeline'

    def add_arguments(self, parser):
        parser.add_argument(
            '--query',
            type=str,
            default='Software Developer',
            help='Job search query'
        )
        parser.add_argument(
            '--country',
            type=str,
            default='US',
            help='Country code (e.g., US, UK, CA)'
        )
        parser.add_argument(
            '--pages',
            type=int,
            default=1,
            help='Number of pages to scrape'
        )
        parser.add_argument(
            '--date_posted',
            type=str,
            default="today",
            help='Posted date of jobs scraped'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 Starting Skills Analysis Pipeline...'))
        
        query = options['query']
        country = options['country']
        num_pages = options['pages']
        date_posted = options['date_posted']
        
        try:
            # 1. Scrape jobs
            self.stdout.write('\n1. Scraping jobs...')
            scraper = JobScraper(
                output_file=str(settings.SKILLS_ENGINE['DATA_DIR'] / 'jobs.json')
            )
            
            jobs = scraper.scrape_jobs({
                "query": query,
                "page": "1",
                "num_pages": str(num_pages),
                "country": country,
                "date_posted": date_posted,
                "language": "en",
                "fields": "job_id,job_title,employer_name,job_description"
            })
            
            if not jobs:
                self.stdout.write(self.style.ERROR('❌ No jobs found. Exiting.'))
                return
            
            self.stdout.write(self.style.SUCCESS(f'✓ Scraped {len(jobs)} jobs'))
            
            # 2. Extract skills
            self.stdout.write('\n2. Extracting skills from job descriptions...')
            extractor = SkillExtractor(
                output_file=str(settings.SKILLS_ENGINE['DATA_DIR'] / 'skills.json')
            )
            skills = extractor.extract_from_jobs(jobs)
            
            self.stdout.write(self.style.SUCCESS(
                f'✓ Extracted {len(skills["hard_skills"])} hard skills, '
                f'{len(skills["soft_skills"])} soft skills'
            ))
            
            # 3. Generate summary
            self.stdout.write('\n3. Generating analysis summary...')
            summary = extractor.generate_summary(skills, industry_context=query)
            
            # Save summary
            summary_file = settings.SKILLS_ENGINE['DATA_DIR'] / 'summary.txt'
            with open(summary_file, 'w') as f:
                f.write(summary)
            
            # Display results
            self.stdout.write('\n' + '='*60)
            self.stdout.write(self.style.SUCCESS('📊 ANALYSIS COMPLETE'))
            self.stdout.write('='*60)
            
            self.stdout.write(f'\n📄 Output Files:')
            self.stdout.write(f'   - {settings.SKILLS_ENGINE["DATA_DIR"]}/jobs.json')
            self.stdout.write(f'   - {settings.SKILLS_ENGINE["DATA_DIR"]}/skills.json')
            self.stdout.write(f'   - {settings.SKILLS_ENGINE["DATA_DIR"]}/summary.txt')
            
            self.stdout.write(f'\n📊 Top 10 Hard Skills:')
            top_hard = sorted(skills['hard_skills'].items(), key=lambda x: x[1], reverse=True)[:10]
            for i, (skill, count) in enumerate(top_hard, 1):
                self.stdout.write(f'   {i:2d}. {skill:30s} ({count} mentions)')
            
            self.stdout.write(f'\n💬 Top 5 Soft Skills:')
            top_soft = sorted(skills['soft_skills'].items(), key=lambda x: x[1], reverse=True)[:5]
            for i, (skill, count) in enumerate(top_soft, 1):
                self.stdout.write(f'   {i:2d}. {skill:30s} ({count} mentions)')
            
            self.stdout.write(f'\n📝 Summary:\n{summary}')
            
            self.stdout.write('\n' + '='*60)
            self.stdout.write(self.style.SUCCESS('✅ Pipeline completed successfully!'))
            self.stdout.write('='*60)
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ Error: {str(e)}'))
            logger.error(f'Pipeline error: {e}', exc_info=True)
