import json
import os
import logging
from typing import List, Dict
from collections import Counter
from google import genai
from dotenv import load_dotenv
load_dotenv()
gemini_api_key = os.getenv("GEMINI_API_KEY")
gemini_model = os.getenv("GEMINI_MODEL")
logger = logging.getLogger(__name__)

class SkillExtractor:
    def __init__(self, output_file: str = "skills.json"):

        if not gemini_api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        
        self.output_file = output_file

        try:
            self.client = genai.Client(api_key=gemini_api_key)
            self.model = gemini_model
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")
            raise

    def extract_from_job(self, job: Dict) -> Dict[str, List[str]]:
        """
        Extract skills from a single job posting

        Args:
            job: Job dictionary
        Returns:
            Dictionary with 'hard_skills' and 'soft_skills' lists
        """
        description = job.get('job_description', '')
        if not description:
            logger.warning("No job description found")
            return {"hard_skills": [], "soft_skills": []}
        
        # Limit description length to avoid token limits
        max_length = 10000
        if len(description) > max_length:
            description = description[:max_length] + "...[truncated]"
            logger.warning(f"Job description truncated to {max_length} characters")
        
        prompt = f"""You are an expert at analyzing job descriptions and extracting standardized skills. 

Extract all required skills from the job description below. 
Classify each skill into one of these categories:
- hard_skills: Technical skills, tools, programming languages, frameworks, software, methodologies
- soft_skills: Interpersonal skills, communication, teamwork, leadership, personal attributes

CRITICAL STANDARDIZATION RULES - APPLY THESE CONSISTENTLY:

1. **STANDARDIZE SIMILAR TERMS**: Always use the most common canonical form:
- "machine learning (ML)" → "machine learning"
- "artificial intelligence (AI)" → "artificial intelligence"
- "AI" → "artificial intelligence"
- "ML" → "machine learning"
- "GenAI" → "generative ai"
- "LLMs" → "large language models"
- "data analytics" → "data analysis"
- "statistical methodologies" → "statistical analysis"
- "Python programming" → "python"
- "SQL databases" → "sql"
- "problem solving" → "problem-solving"

2. **REMOVE REDUNDANT PARENTHESES**: Only keep parentheses if they add NEW information:
- "machine learning (ML)" → "machine learning" (redundant)
- "TensorFlow (deep learning framework)" → "tensorflow" (redundant)
- "AWS (Amazon Web Services)" → "aws" (redundant)
- "NLP (Natural Language Processing)" → "natural language processing" (convert to full name)

3. **CONSOLIDATE RELATED SKILLS**: Group under broader standardized terms:
- "data mining", "exploratory analysis", "data analytics" → "data analysis"
- "statistical modeling", "quantitative analysis", "statistical methodologies" → "statistical analysis"
- "written communication", "verbal communication", "communication skills" → "communication"
- "collaboration", "teamwork", "working cooperatively" → "teamwork"

4. **USE LOWERCASE**: All skills should be lowercase for consistency.

Only extract skills explicitly mentioned or strongly implied. 
Do not add skills that are not explicitly mentioned.
Return ONLY valid JSON in this exact format:
{{
    "hard_skills": ["skill1", "skill2"], 
    "soft_skills": ["skill3", "skill4"]
}}

Job Description:
{description}
"""
        
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            
            # Extract text safely
            response_text = ""
            if hasattr(response, 'text'):
                response_text = response.text
            elif hasattr(response, 'candidates') and response.candidates:
                response_text = response.candidates[0].content.parts[0].text
            else:
                response_text = str(response)
            
            # Clean the response text
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            
            # Parse JSON with error handling
            skills = json.loads(response_text)
            
            # Validate structure
            if not isinstance(skills, dict):
                raise ValueError("Response is not a dictionary")
            
            return {
                "hard_skills": skills.get("hard_skills", []),
                "soft_skills": skills.get("soft_skills", [])
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Raw response: {response_text[:500] if 'response_text' in locals() else 'No response'}")
            return {"hard_skills": [], "soft_skills": []}
        except Exception as e:
            logger.error(f"Error extracting skills: {e}")
            return {"hard_skills": [], "soft_skills": []}

    def extract_from_jobs(self, jobs: List[Dict]) -> Dict[str, Dict[str, int]]:
        """
        Extract skills from multiple job postings
        
        Args:
            jobs: List of job dictionaries
            
        Returns:
            Dictionary with skill frequencies
        """
        logger.info(f"Extracting skills from {len(jobs)} jobs...")
        
        all_skills = []
        
        for i, job in enumerate(jobs):
            logger.debug(f"Processing job {i+1}/{len(jobs)}: {job.get('job_title', 'Unknown')}")
            job_skills = self.extract_from_job(job)
            all_skills.append(job_skills)
        
        # Count frequencies
        hard_skills_counter = Counter()
        soft_skills_counter = Counter()
        
        for skills_dict in all_skills:
            # Normalize skills (lowercase, strip whitespace)
            hard_skills = [skill.lower().strip() for skill in skills_dict.get("hard_skills", [])]
            soft_skills = [skill.lower().strip() for skill in skills_dict.get("soft_skills", [])]
            
            hard_skills_counter.update(hard_skills)
            soft_skills_counter.update(soft_skills)
        
        # Convert to desired format
        result = {
            "hard_skills": dict(hard_skills_counter),
            "soft_skills": dict(soft_skills_counter)
        }

        self._save_skills(result)
        
        logger.info(f"Extracted {len(hard_skills_counter)} unique hard skills and {len(soft_skills_counter)} unique soft skills")
        return result
    
    def generate_summary(self, skills_data: Dict[str, Dict[str, int]], 
                        top_n: int = 10, industry_context: str = "") -> str:
        """
        Generate a human-readable summary of top in-demand skills
        
        Args:
            skills_data: Dictionary with skill frequencies
            top_n: Number of top skills to include
            industry_context: Optional industry context (e.g., "AI", "Data Science")
            
        Returns:
            String summary of top skills
        """
        # Get top skills
        top_hard_skills = sorted(
            skills_data["hard_skills"].items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:top_n]
        
        top_soft_skills = sorted(
            skills_data["soft_skills"].items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:top_n//2]  # Fewer soft skills for summary
        
        # Prepare data for Gemini
        context = f"{industry_context} " if industry_context else ""
        
        prompt = f"""Based on analysis of today's {context}job postings, here are the skill frequencies:

Top {top_n} Hard Skills:
{chr(10).join([f"- {skill}: {count} occurrences" for skill, count in top_hard_skills])}

Top {len(top_soft_skills)} Soft Skills:
{chr(10).join([f"- {skill}: {count} occurrences" for skill, count in top_soft_skills])}

Write a concise, engaging summary of the top in-demand skills (2-3 sentences max).
Focus on the most critical skills that employers are looking for.
Format as a natural, human-readable paragraph that could be used in a report or presentation.
Example format: "Top in-demand skills in AI this week: Python, TensorFlow, Data Visualization, and Communication skills."

Do not include markdown, just plain text."""
        
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            
            summary = response.text if hasattr(response, 'text') else str(response)
            summary = summary.strip().strip('"')
            
            logger.info("Generated skills summary")
            return summary
            
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return f"Based on today's job postings, the most in-demand skills are: {', '.join([skill for skill, _ in top_hard_skills[:5]])}."
    
    def _save_skills(self, skills: Dict[str, Dict[str, int]]) -> None:
        """
        Save skills to JSON file
        
        Args:
            skills: Dictionary with skill frequencies to save
        """
        try:
            with open(self.output_file, 'w') as file:
                json.dump(skills, file, indent=4)
            
            logger.info(f"Saved skills to {self.output_file}")
                        
        except IOError as e:
            logger.error(f"Error saving skills to file: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error saving skills: {str(e)}")
    
    def get_skills(self) -> Dict[str, Dict[str, int]]:
        """
        Get the saved skills from file
        
        Returns:
            Dictionary with skill frequencies
        """
        try:
            with open(self.output_file, 'r') as file:
                skills = json.load(file)
            
            logger.info(f"Loaded skills from {self.output_file}")
            return skills
            
        except FileNotFoundError:
            logger.warning(f"Skills file {self.output_file} does not exist")
            return {"hard_skills": {}, "soft_skills": {}}
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing skills file: {str(e)}")
            return {"hard_skills": {}, "soft_skills": {}}
        except Exception as e:
            logger.error(f"Unexpected error loading skills: {str(e)}")
            return {"hard_skills": {}, "soft_skills": {}}


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Test
    try:
        extractor = SkillExtractor()
        
        with open("jobs.json", 'r') as file:
            jobs = json.load(file)
        
        skills = extractor.extract_from_jobs(jobs)
        summary = extractor.generate_summary(skills)
        print("\n=== SUMMARY ===")
        print(summary)
        
    except ValueError as e:
        print(f"Initialization error: {e}")
        print("Set environment variable: export GEMINI_API_KEY='your_key_here'")
    except Exception as e:
        print(f"Error: {e}")