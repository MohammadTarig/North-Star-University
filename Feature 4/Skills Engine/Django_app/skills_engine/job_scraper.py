import json
import os
import requests
import logging
from typing import List, Dict
from dotenv import load_dotenv
load_dotenv()
x_rapidapi_key = os.getenv("X_RAPIDAPI_KEY")
x_rapidapi_host = os.getenv("X_RAPIDAPI_HOST")
logger = logging.getLogger(__name__)

class JobScraper:
    """
    Web Scrape Jobs from RapidAPI Jsearch
    """
    
    def __init__(self, output_file: str = "jobs.json"):
        self.output_file = output_file
        
        # Validate API credentials
        if not x_rapidapi_key or not x_rapidapi_host:
            logger.warning("RapidAPI credentials not found in environment variables")

    def scrape_jobs(self, querydata: Dict) -> List[Dict]:
        """
        Web scrape jobs using RapidAPI's Jsearch API
        
        Args:
            querydata: Dictionary containing query parameters
            
        Returns:
            List of job dictionaries
        """
        # Check API credentials
        if not x_rapidapi_key or not x_rapidapi_host:
            logger.error("Missing RapidAPI credentials. Set X_RAPIDAPI_KEY and X_RAPIDAPI_HOST environment variables.")
            return []
        
        url = "https://jsearch.p.rapidapi.com/search"
        headers = {
            "x-rapidapi-key": x_rapidapi_key,
            "x-rapidapi-host": x_rapidapi_host
        }
        
        # Set default values for optional parameters
        query_params = {
            "query": querydata.get("query", ""),
            "page": querydata.get("page", "1"),
            "num_pages": querydata.get("num_pages", "1"),
            "date_posted": querydata.get("date_posted", "today"),
            "language": querydata.get("language", "en"),
            "fields": querydata.get("fields", "job_id,job_title,employer_name,job_description,job_country")
        }
        
        # Add country only if specified
        if "country" in querydata and querydata["country"]:
            query_params["country"] = querydata["country"]
        
        logger.info(f"Fetching jobs from RapidAPI Jsearch API with query: {query_params['query']}")
        
        try:
            response = requests.get(url, headers=headers, params=query_params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if API returned an error in the JSON
                if data.get("status") != "OK":
                    error_msg = data.get("message", "Unknown API error")
                    logger.error(f"API returned error: {error_msg}")
                    return []
                
                jobs = data.get("data", [])
                logger.info(f"Successfully fetched {len(jobs)} jobs from RapidAPI Jsearch API")
                
                # Overwrite file with new jobs
                self._save_jobs(jobs)
                
                return jobs
                
            elif response.status_code == 401:
                logger.error("Invalid RapidAPI key. Check your API credentials.")
            elif response.status_code == 429:
                logger.error("Rate limit exceeded. Try again later or upgrade your plan.")
            elif response.status_code == 500:
                logger.error("RapidAPI server error. Try again later.")
            else:
                logger.warning(f"RapidAPI Jsearch API returned status {response.status_code}")
                
            return []
                
        except requests.Timeout:
            logger.error("Request to RapidAPI timed out. Try again later.")
            return []
        except requests.ConnectionError:
            logger.error("Network connection error. Check your internet connection.")
            return []
        except requests.RequestException as e:
            logger.error(f"Error fetching from RapidAPI: {str(e)}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse API response as JSON: {str(e)}")
            logger.debug(f"Raw response: {response.text[:500] if 'response' in locals() else 'No response'}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error with RapidAPI: {str(e)}")
            return []
    
    def _save_jobs(self, jobs: List[Dict]) -> None:
        """
        Save jobs to JSON file
        
        Args:
            jobs: List of job dictionaries to save
        """
        try:
            with open(self.output_file, 'w') as file:
                json.dump(jobs, file, indent=4)
            
            logger.info(f"Saved {len(jobs)} jobs to {self.output_file}")
            
        except IOError as e:
            logger.error(f"Error saving jobs to file: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error saving jobs: {str(e)}")
    
    def get_jobs(self) -> List[Dict]:
        """
        Get the saved jobs from file
        
        Returns:
            List of job dictionaries
        """
        try:
            with open(self.output_file, 'r') as file:
                jobs = json.load(file)
            
            logger.info(f"Loaded {len(jobs)} jobs from {self.output_file}")
            return jobs
            
        except FileNotFoundError:
            logger.warning(f"Jobs file {self.output_file} does not exist")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing jobs file: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error loading jobs: {str(e)}")
            return []

# Usage example
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Create scraper
    scraper = JobScraper(output_file="jobs.json")
    
    # Define search query
    query_params = {
        "query": "Data Scientist",
        "page": "1",
        "num_pages": "1",
        "country": "US",
        "date_posted": "today",
        "language": "en",
        "fields": "job_id,job_title,employer_name,job_description,job_country,job_highlights"
    }
    
    # Scrape jobs
    jobs = scraper.scrape_jobs(query_params)
    
    # Get jobs (from cache)
    all_jobs = scraper.get_jobs()
    print(f"Total jobs available: {len(all_jobs)}")