import json
import os
import logging
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import google.generativeai as genai
from pydantic import BaseModel, ValidationError
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProficiencyLevel(Enum):
    """Enum for student proficiency levels"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate" 
    ADVANCED = "advanced"


@dataclass
class StudentProfile:
    """Student profile data structure"""
    proficiency_score: float
    level: str = None
    
    def __post_init__(self):
        """Auto-calculate level based on proficiency score"""
        if self.proficiency_score < 3.0:
            self.level = ProficiencyLevel.BEGINNER.value
        elif self.proficiency_score < 6.0:
            self.level = ProficiencyLevel.INTERMEDIATE.value
        else:
            self.level = ProficiencyLevel.ADVANCED.value


class TieredContentModel(BaseModel):
    """Pydantic model for validating tiered content output"""
    concept_name: str
    content: Dict[str, str]
    examples: Dict[str, str]
    
    class Config:
        extra = "forbid"  # Reject extra fields


class ContentPersonalizer:
    """
    Main class for generating personalized educational content
    Handles API calls, prompt engineering, and content tier selection
    """
    
    def __init__(self, api_key: str):
        """
        Initialize the ContentPersonalizer with Gemini API
        
        Args:
            api_key (str): Google Gemini API key
        """
        self.api_key = api_key
        genai.configure(api_key=api_key)
        
        # Initialize the model
        self.model = genai.GenerativeModel(
            model_name="models/gemini-2.0-flash",
            generation_config={
                "temperature": 0.7,
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 2048,
            }
        )
        
        # Cache for storing generated content to avoid repeated API calls
        self.content_cache = {}
        
        # Performance tracking
        self.api_call_count = 0
        self.total_response_time = 0.0
        
    def _get_system_instruction(self) -> str:
        """
        Get the system instruction for the AI model
        
        Returns:
            str: System instruction for educational content generation
        """
        return """Act as a specialized technical educator and curriculum expert. 
        You excel at explaining complex concepts at different levels of understanding, from absolute beginners to advanced practitioners.

        Your explanations should be:
        - Accurate and pedagogically sound
        - Appropriately complex for each level
        - Engaging and clear
        - Include practical, relevant examples

        Always maintain a supportive, encouraging tone that builds confidence."""
    
    def _build_user_prompt(self, concept_name: str) -> str:
        """
        Build the user prompt for content generation
        
        Args:
            concept_name (str): The concept to explain
            
        Returns:
            str: Formatted user prompt
        """
        return f'''
        Explain the concept "{concept_name}" in three different versions:

    1. BEGINNER Level:
    - Use simple analogies and everyday language
    - Avoid technical jargon
    - Focus on what it is and why it matters
    - Make it approachable and non-intimidating

    2. INTERMEDIATE Level:
    - Include technical details and proper terminology
    - Show relationships to other concepts
    - Provide more depth and context
    - Assume basic foundational knowledge

    3. ADVANCED Level:
    - Focus on implementation details and nuances
    - Discuss edge cases and performance considerations
    - Include advanced applications and implications
    - Assume strong technical background

    For each level, also provide a practical example that matches the complexity.

    The response MUST be a valid JSON object with this exact structure:
    {{
    "concept_name": "{concept_name}",
    "content": {{
        "beginner": "clear explanation for beginners",
        "intermediate": "detailed explanation for intermediate learners",
        "advanced": "comprehensive explanation for advanced learners"
    }},
    "examples": {{
        "beginner": "simple, relatable example",
        "intermediate": "more detailed practical example",
        "advanced": "complex real-world example or implementation"
    }}
    }}

    Ensure the JSON is properly formatted and parseable. Do not include any extra text outside the JSON.'''

    def _call_gemini_api(self, prompt: str, max_retries: int = 3) -> Optional[Dict[str, Any]]:
        """
        Make API call to Gemini with retry logic
        
        Args:
            prompt (str): The formatted prompt
            max_retries (int): Maximum number of retry attempts
            
        Returns:
            Optional[Dict[str, Any]]: Parsed JSON response or None if failed
        """
        for attempt in range(max_retries):
            try:
                start_time = time.time()
                
                response = self.model.generate_content(
                    prompt,
                    generation_config={
                        "temperature": 0.7,
                        "response_mime_type": "application/json"
                    }
                )
                
                response_time = time.time() - start_time
                self.api_call_count += 1
                self.total_response_time += response_time
                
                logger.info(f"API call {self.api_call_count} completed in {response_time:.2f}s")
                
                # Parse JSON response
                json_response = json.loads(response.text)
                return json_response
                
            except json.JSONDecodeError as e:
                logger.warning(f"JSON parsing failed on attempt {attempt + 1}: {e}")
                if attempt == max_retries - 1:
                    logger.error("All JSON parsing attempts failed")
                    return None
                    
            except Exception as e:
                logger.error(f"API call failed on attempt {attempt + 1}: {e}")
                if attempt == max_retries - 1:
                    logger.error("All API call attempts failed")
                    return None
                    
        return None
    
    def _validate_content(self, content_data: Dict[str, Any]) -> Optional[TieredContentModel]:
        """
        Validate the generated content using Pydantic
        
        Args:
            content_data (Dict[str, Any]): Raw content data from API
            
        Returns:
            Optional[TieredContentModel]: Validated content model or None
        """
        try:
            # Validate required structure
            required_levels = ["beginner", "intermediate", "advanced"]
            
            if "content" not in content_data or "examples" not in content_data:
                logger.error("Missing required 'content' or 'examples' fields")
                return None
                
            for level in required_levels:
                if level not in content_data["content"]:
                    logger.error(f"Missing content for {level} level")
                    return None
                if level not in content_data["examples"]:
                    logger.error(f"Missing example for {level} level")
                    return None
            
            # Use Pydantic for validation
            validated_content = TieredContentModel(**content_data)
            logger.info(f"Content validation successful for: {validated_content.concept_name}")
            return validated_content
            
        except ValidationError as e:
            logger.error(f"Content validation failed: {e}")
            return None
    
    def generate_tiered_content(self, concept_name: str) -> Optional[Dict[str, Any]]:
        """
        Generate tiered educational content for a concept
        
        Args:
            concept_name (str): The concept to create content for
            
        Returns:
            Optional[Dict[str, Any]]: Generated tiered content or None if failed
        """
        # Check cache first
        cache_key = concept_name.lower().strip()
        if cache_key in self.content_cache:
            logger.info(f"Returning cached content for: {concept_name}")
            return self.content_cache[cache_key]
        
        logger.info(f"Generating tiered content for: {concept_name}")
        
        # Build the full prompt
        system_instruction = self._get_system_instruction()
        user_prompt = self._build_user_prompt(concept_name)
        full_prompt = f"{system_instruction}\n\n{user_prompt}"
        
        # Make API call
        raw_response = self._call_gemini_api(full_prompt)
        if raw_response is None:
            logger.error(f"Failed to generate content for: {concept_name}")
            return None
        
        # Validate response
        validated_content = self._validate_content(raw_response)
        if validated_content is None:
            logger.error(f"Content validation failed for: {concept_name}")
            return None
        
        # Convert to dict and cache
        content_dict = validated_content.model_dump()
        self.content_cache[cache_key] = content_dict
        
        logger.info(f"Successfully generated and cached content for: {concept_name}\n")
        return content_dict
    
    def get_content_for_level(self, concept_name: str, proficiency_level: str) -> Optional[Dict[str, Any]]:
        """
        Get content for a specific proficiency level
        
        Args:
            concept_name (str): The concept name
            proficiency_level (str): Target proficiency level
            
        Returns:
            Optional[Dict[str, Any]]: Content and example for the specified level
        """
        # Validate proficiency level
        valid_levels = [level.value for level in ProficiencyLevel]
        if proficiency_level not in valid_levels:
            logger.error(f"Invalid proficiency level: {proficiency_level}")
            return None
        
        # Generate full tiered content
        tiered_content = self.generate_tiered_content(concept_name)
        if tiered_content is None:
            return None
        
        # Extract content for specific level
        try:
            level_content = {
                "concept_name": concept_name,
                "proficiency_level": proficiency_level,
                "content": tiered_content["content"][proficiency_level],
                "example": tiered_content["examples"][proficiency_level]
            }
            
            logger.info(f"Retrieved {proficiency_level} level content for: {concept_name}")
            return level_content
            
        except KeyError as e:
            logger.error(f"Failed to extract {proficiency_level} content: {e}")
            return None
    
    def get_content_by_profile(self, student_profile: StudentProfile, concept_name: str) -> Optional[Dict[str, Any]]:
        """
        Get content based on student profile
        
        Args:
            student_profile (StudentProfile): Student's profile with proficiency score
            concept_name (str): The concept to explain
            
        Returns:
            Optional[Dict[str, Any]]: Personalized content for the student
        """
        logger.info(f"Getting content for student (score: {student_profile.proficiency_score}, "
                   f"level: {student_profile.level}) - concept: {concept_name}")
        
        content = self.get_content_for_level(concept_name, student_profile.level)
        if content:
            # Add student profile info to response
            content["student_profile"] = {
                "proficiency_score": student_profile.proficiency_score,
                "level": student_profile.level
            }
        
        return content
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get performance statistics
        
        Returns:
            Dict[str, Any]: Performance metrics
        """
        avg_response_time = (self.total_response_time / self.api_call_count 
                           if self.api_call_count > 0 else 0)
        
        return {
            "total_api_calls": self.api_call_count,
            "total_response_time": round(self.total_response_time, 2),
            "average_response_time": round(avg_response_time, 2),
            "cached_concepts": len(self.content_cache),
            "cache_keys": list(self.content_cache.keys())
        }
    
    def clear_cache(self):
        """Clear the content cache"""
        self.content_cache.clear()
        logger.info("Content cache cleared")


def get_personalized_content(api_key: str, concept_name: str, proficiency_score: float) -> Optional[Dict[str, Any]]:
    """
    Simple function for web team integration - get personalized content
    
    Args:
        api_key (str): Gemini API key
        concept_name (str): Concept to explain
        proficiency_score (float): Student's proficiency score
        
    Returns:
        Optional[Dict[str, Any]]: Personalized content
    """
    personalizer = ContentPersonalizer(api_key)
    student_profile = StudentProfile(proficiency_score)
    return personalizer.get_content_by_profile(student_profile, concept_name)


# Example usage and testing
if __name__ == "__main__":
    """
    CLI runner for generating educational content
    Steps:
    1. Load base course structure
    2. Generate tiered content for all concepts
    3. Generate personalized content for a sample profile
    """
    
    # Load environment variables from the .env file
    load_dotenv()

    # Access environment variables
    API_KEY = os.getenv("GEMINI_API_KEY")
    course_structure = os.getenv("COURSE_STRUCTURE_PATH")
    generated_content = os.getenv("GENERATED_CONTENT_PATH")
    personalized_content = os.getenv("PERSONALIZED_CONTENT_PATH")


    personalizer = ContentPersonalizer(API_KEY)

    # Load the base course structure
    with open(course_structure, "r", encoding="utf-8") as f:
        course_data = json.load(f)

    # === STEP 1: Generate full tiered content for all concepts ===
    for module in course_data["modules"]:
        new_concepts = []
        for concept_name in module["concepts"]:
            tiered_content = personalizer.generate_tiered_content(concept_name)
            if tiered_content:
                new_concepts.append({
                    "name": concept_name,
                    "content": tiered_content["content"],
                    "examples": tiered_content["examples"]
                })
            else:
                new_concepts.append({
                    "name": concept_name,
                    "content": {},
                    "examples": {}
                })
        module["concepts"] = new_concepts

    # Save the full generated tiered content
    with open(generated_content, "w", encoding="utf-8") as f:
        json.dump(course_data, f, ensure_ascii=False, indent=4)

    print(f"✅ Tiered content generation complete. Saved to {generated_content}")

    # === STEP 2: Generate personalized content basd on proficiency level ===

    profile = StudentProfile(proficiency_score=4.2)  # Intermediate
    personalized_results = []
    sample_concept_name = "Statement and meaning of the third law"
    content = personalizer.get_content_by_profile(profile, sample_concept_name)
    if content:
        personalized_results.append({
            "concept_name": content["concept_name"],
            "proficiency_level": content["proficiency_level"],
            "content": content["content"],
            "example": content["example"]
        })

    # Save the personalized (level-based) content
    with open(personalized_content, "w", encoding="utf-8") as f:
        json.dump(personalized_results, f, ensure_ascii=False, indent=4)

    print(f"✅ Personalized content generation complete. Saved to {personalized_content}")
