# Feature 4 - Skills Engine

## Overview

The Skills Engine analyzes real-time job market data to extract trending technical skills using AI (Google Gemini). It provides insights into in-demand hard and soft skills.

## Features

- 🔍 **Real-time Job Scraping** - Fetches latest jobs via RapidAPI Jsearch
- 🤖 **AI-Powered Skill Extraction** - Uses Google Gemini for intelligent skill extraction
- 📊 **Hard/Soft Skills Classification** - Automatically categorizes skills
- 📈 **Frequency Analysis** - Tracks skill demand trends
- 📝 **Auto-Generated Summaries** - Natural language insights
- 🔌 **Django REST API** - `/api/trending-skills/` endpoint
- 📦 **Output for Dev B & C** - Formatted JSON for downstream modules

## Quick Start

### Prerequisites

- Python 3.8+
- Google Gemini API key
- RapidAPI key (for Jsearch)

### Installation

```bash
# Clone repository
git clone <repo-url>
cd skills_engine

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env and add your API keys
```

### Configuration

Create a `.env` file in the project root:

```env
# Google Gemini API
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.0-flash-exp

# RapidAPI Credentials
X_RAPIDAPI_KEY=your_rapidapi_key_here
X_RAPIDAPI_HOST=jsearch.p.rapidapi.com

# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=True
```

### Running the Pipeline

#### Standalone Mode

```bash
# Run the complete pipeline (recommended)
python manage.py run_skills_pipeline

# Or run directly (with preset query values, which can be changed by updating queries in `main.py`)
python main.py
```

#### Django API Mode

```bash
# Run migrations
python manage.py migrate

# Start server
python manage.py runserver

# Access API
curl http://localhost:8000/api/trending-skills/
```

## API Endpoints

### GET `/api/trending-skills/`

Returns trending skills analysis.

**Query Parameters:**
- `query` (optional): Job search query (default: "Software Developer")
- `country` (optional): Country code (default: "US")
- `num_pages` (optional): Pages to scrape (default: 1)
- `date_posted` (optional): Posted date of jobs scraped. Allowed values: "all", "today", "3days", "week", "month" (default: "today")

**Response:**
```json
{
  "status": "success",
  "timestamp": "2025-10-30T14:30:00",
  "query": "Software Developer",
  "country": "US",
  "total_jobs_analyzed": 10,
  "hard_skills": {
    "python": 8,
    "sql": 6,
    "machine learning": 5
  },
  "soft_skills": {
    "communication": 7,
    "teamwork": 5,
    "problem-solving": 4
  },
  "summary": "Top in-demand skills this week: Python, SQL, Machine Learning...",
  "top_10_hard_skills": ["python", "sql", "machine learning", "..."],
  "top_5_soft_skills": ["communication", "teamwork", "..."]
}
```

## Integration with Dev B

```python
import json

with open('data/skills.json') as f:
    skills = json.load(f)

# Get top hard skills for project ideas
top_skills = sorted(
    skills['hard_skills'].items(), 
    key=lambda x: x[1], 
    reverse=True
)[:5]

# Example: ['python', 'sql', 'machine learning', 'react', 'aws']
```

## Output Files

### `data/jobs.json`
Raw scraped job data from RapidAPI

### `data/skills.json`
```json
{
  "hard_skills": {
    "python": 8,
    "sql": 6,
    "machine learning": 5
  },
  "soft_skills": {
    "communication": 7,
    "teamwork": 5
  }
}
```

### `data/summary.txt`
AI-generated natural language summary of trends

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GEMINI_API_KEY` | Google Gemini API key | Yes |
| `GEMINI_MODEL` | Gemini model name | Yes |
| `X_RAPIDAPI_KEY` | RapidAPI key | Yes |
| `X_RAPIDAPI_HOST` | RapidAPI host | Yes |
| `SECRET_KEY` | Django secret key | Yes |
| `DEBUG` | Debug mode | No |

## Get API Keys

### Google Gemini API
1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Create a new API key
3. Add to `.env` as `GEMINI_API_KEY`

### RapidAPI (Jsearch)
1. Visit [RapidAPI Jsearch](https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch)
2. Subscribe to free tier
3. Set Version 2 "V2"
3. Get API key and host
4. Add to `.env`

## Future Enhancements

- [ ] Batch processing for faster extraction
- [ ] Historical trend analysis
- [ ] Scheduled daily scraping

## Acknowledgments

- Google Gemini for AI extraction
- RapidAPI Jsearch for job data