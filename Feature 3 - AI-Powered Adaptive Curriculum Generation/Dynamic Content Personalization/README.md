This code uses the **Gemini API** to generate and personalize course content.
It reads from a predefined course structure and saves the generated and personalized content into JSON files.

---

## ⚙️ Setup Instructions

### 1️⃣ Install Required Packages

```bash
pip install -r requirements.txt
```

*(Make sure you have `python-dotenv` installed.)*

---

### 2️⃣ Create a `.env` File

Create a file named `.env` in the same folder as your Python script and add:

```
GEMINI_API_KEY=YOUR_API_KEY_HERE
COURSE_STRUCTURE_PATH=course_structure.json
GENERATED_CONTENT_PATH=generated_content.json
PERSONALIZED_CONTENT_PATH=personalized_content.json
```

---

### 3️⃣ Run the Python Script

```bash
python your_script_name.py
```

---

## 📁 File Descriptions

| File                        | Description                                    |
| --------------------------- | ---------------------------------------------- |
| `.env`                      | Stores your API key and file paths             |
| `course_structure.json`     | Contains the input course structure            |
| `generated_content.json`    | Output file with generated course content      |
| `personalized_content.json` | Output file with personalized learning content |

---
