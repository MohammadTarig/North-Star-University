import logging
from datetime import datetime
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings

from .job_scraper import JobScraper
from .skill_extractor import SkillExtractor

logger = logging.getLogger(__name__)


class HealthCheckView(APIView):
    """
    Health check endpoint
    """
    def get(self, request):
        return Response({
            'status': 'healthy',
            'service': 'Skills Engine API',
            'timestamp': datetime.now().isoformat()
        })


class TrendingSkillsView(APIView):
    """
    Main API endpoint for trending skills analysis
    GET /api/trending-skills/
    """
    
    def get(self, request):
        """
        Analyze job market and return trending skills
        
        Query Parameters:
        - query: Job search query (default: "Software Developer")
        - country: Country code (default: "US")
        - num_pages: Number of pages to scrape from 1-50 (10 jobs per page) (default: 1)
        - date_posted: Posted date of jobs scraped. Allowed values: "all", "today", "3days", "week", "month" (default: "today")
        """
        try:
            # Get query parameters
            query = request.GET.get('query', settings.SKILLS_ENGINE['DEFAULT_QUERY'])
            country = request.GET.get('country', settings.SKILLS_ENGINE['DEFAULT_COUNTRY'])
            num_pages = request.GET.get('num_pages', settings.SKILLS_ENGINE['DEFAULT_PAGES'])
            date_posted = request.GET.get('date_posted', settings.SKILLS_ENGINE['DEFAULT_DATE_POSTED'])
            
            logger.info(f"API request: query='{query}', country='{country}', pages={num_pages}, date_posted={date_posted}")
            
            # 1. Scrape jobs
            logger.info("Scraping jobs...")
            scraper = JobScraper(output_file=str(settings.SKILLS_ENGINE['DATA_DIR'] / 'jobs.json'))
            
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
                return Response({
                    'status': 'error',
                    'message': 'No jobs found. Please try a different query or check API credentials.'
                }, status=status.HTTP_404_NOT_FOUND)
            
            logger.info(f"Scraped {len(jobs)} jobs")
            
            # 2. Extract skills
            logger.info("Extracting skills...")
            extractor = SkillExtractor(output_file=str(settings.SKILLS_ENGINE['DATA_DIR'] / 'skills.json'))
            skills_data = extractor.extract_from_jobs(jobs)
            
            logger.info(f"Extracted {len(skills_data['hard_skills'])} hard skills, {len(skills_data['soft_skills'])} soft skills")
            
            # 3. Generate summary
            logger.info("Generating summary...")
            summary = extractor.generate_summary(skills_data, industry_context=query)
            
            # Save summary
            summary_file = settings.SKILLS_ENGINE['DATA_DIR'] / 'summary.txt'
            with open(summary_file, 'w') as f:
                f.write(summary)
            
            # 4. Format response
            # Get top skills
            top_hard_skills = sorted(
                skills_data['hard_skills'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
            
            top_soft_skills = sorted(
                skills_data['soft_skills'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
            
            response_data = {
                'status': 'success',
                'timestamp': datetime.now().isoformat(),
                'query': query,
                'country': country,
                'total_jobs_analyzed': len(jobs),
                'hard_skills': skills_data['hard_skills'],
                'soft_skills': skills_data['soft_skills'],
                'summary': summary,
                'top_10_hard_skills': [skill for skill, _ in top_hard_skills],
                'top_5_soft_skills': [skill for skill, _ in top_soft_skills],
                'metadata': {
                    'total_hard_skills': len(skills_data['hard_skills']),
                    'total_soft_skills': len(skills_data['soft_skills'])
                }
            }
            
            logger.info("API request completed successfully")
            return Response(response_data, status=status.HTTP_200_OK)
            
        except ValueError as e:
            logger.error(f"Configuration error: {e}")
            return Response({
                'status': 'error',
                'message': f'Configuration error: {str(e)}',
                'hint': 'Check your .env file and ensure all API keys are set correctly'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return Response({
                'status': 'error',
                'message': f'An unexpected error occurred: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)