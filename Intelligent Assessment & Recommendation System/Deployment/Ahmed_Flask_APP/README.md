# AI Quiz Generator

An intelligent quiz generation and evaluation system powered by Gemini AI. Upload documents and get AI-generated quizzes with real-time evaluation.

## Features

### 🎯 **New Workflow**
1. **Category Selection**: Choose from Web Development, AI, or Cybersecurity
2. **Document Upload**: Upload images or PDFs for quiz generation
3. **Chat-like Interface**: Answer questions one by one in a conversational format
4. **Real-time Evaluation**: Get instant feedback and scoring for each answer
5. **Final Results**: View comprehensive results with pass/fail status

### 🤖 **AI-Powered Features**
- **OCR Integration**: Extract text from images and PDFs
- **Smart Quiz Generation**: AI creates contextual questions based on category
- **Intelligent Evaluation**: AI evaluates answers with detailed feedback
- **Category-Specific Prompts**: Tailored questions for Web, AI, and Cybersecurity

### 📊 **Evaluation System**
- **Real-time Scoring**: 0-5 scale for each answer
- **Pass/Fail Logic**: 60% pass rate requirement
- **Detailed Feedback**: AI provides reasoning for scores
- **Progress Tracking**: Visual progress through questions

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd eval
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp env_example.txt .env
   # Edit .env and add your GEMINI_API_KEY
   ```

5. **Run the application**
   ```bash
   python app/app.py
   ```

## Usage

### Step 1: Choose Category
- Select from **Web Development**, **AI**, or **Cybersecurity**
- Each category has specialized prompts for relevant questions

### Step 2: Upload Document
- Upload images (PNG, JPG, GIF) or PDFs
- Maximum file size: 16MB
- AI extracts text and generates category-specific questions

### Step 3: Take Quiz
- **Chat-like Interface**: Questions appear one at a time
- **Real-time Feedback**: Get instant evaluation after each answer
- **Progress Tracking**: See your progress through the quiz
- **Skip Option**: Skip questions if needed

### Step 4: View Results
- **Final Score**: Overall performance out of 5
- **Pass/Fail Status**: Based on 60% pass rate
- **Detailed Feedback**: AI reasoning for each answer
- **Performance Analytics**: Comprehensive breakdown

## API Endpoints

- `GET /` - Home page with category selection
- `POST /upload` - Upload document and generate quiz
- `GET /quiz/<quiz_id>` - Chat-like quiz interface
- `POST /submit_answer` - Submit and evaluate answer
- `GET /results/<quiz_id>` - View detailed results
- `GET /api/results/<quiz_id>` - API endpoint for results
- `GET /api/quizzes` - List all quizzes

## Database Schema

### Quizzes Table
- `id`: Unique quiz identifier
- `topic`: Quiz topic
- `questions`: JSON array of questions
- `category`: Quiz category (web, ai, cybersecurity)
- `created_at`: Creation timestamp
- `file_path`: Path to uploaded document

### Student Answers Table
- `id`: Unique answer identifier
- `quiz_id`: Reference to quiz
- `question_index`: Question number
- `student_answer`: Student's response
- `evaluation_result`: AI evaluation JSON
- `score`: Numerical score (0-5)
- `passed`: Boolean pass/fail status
- `submitted_at`: Submission timestamp

## Technology Stack

- **Backend**: Flask (Python)
- **Frontend**: Bootstrap 5, JavaScript
- **AI**: Google Gemini AI
- **OCR**: Tesseract (pytesseract)
- **Database**: SQLite
- **Image Processing**: Pillow (PIL)

## Environment Variables

Create a `.env` file with:
```
GEMINI_API_KEY=your_gemini_api_key_here
FLASK_SECRET_KEY=your_secret_key_here
```

## File Structure

```
eval/
├── app/
│   ├── __init__.py
│   ├── app.py                 # Main Flask application
│   ├── evaluation.py          # AI evaluation logic
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css     # Custom styles
│   │   └── js/
│   │       ├── main.js       # General utilities
│   │       ├── upload.js     # Upload functionality
│   │       └── quiz.js       # Quiz interface
│   └── templates/
│       ├── index.html        # Home page with categories
│       ├── quiz_chat.html    # Chat-like quiz interface
│       └── results.html      # Results page
├── evaluation.py             # AI evaluation module
├── requirements.txt          # Python dependencies
├── README.md                # This file
└── .env                     # Environment variables
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For support, please open an issue on GitHub or contact the development team. 