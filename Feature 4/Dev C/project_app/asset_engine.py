import os
import re
import json
import time
import random
import pandas as pd
from dotenv import load_dotenv
import google.generativeai as genai


# ---- Configure Gemini ----
load_dotenv()
gemini_api_key = os.getenv("GEMINI_API_KEY")
if not gemini_api_key:
    raise ValueError("Set the GEMINI_API_KEY environment variable.")
genai.configure(api_key=gemini_api_key)

model_name = "gemini-2.0-flash"
client = genai.GenerativeModel(model_name)


def load_info(file_path="project_app/info.json"):
    """
    Load and extract metadata from info.json.
    Returns a dictionary with extracted fields.
    """
    with open(file_path, "r") as f:
        info = json.load(f)

    title = info.get("title", "")
    level = info.get("level", "")
    description = info.get("description", "")
    required_tools = info.get("required_tools", "")
    dataset = info.get("dataset", "false")

    return {
        "title": title,
        "level": level,
        "description": description,
        "required_tools": required_tools,
        "dataset": dataset
    }

def safe_generate(prompt, retries=5, delay=5):
    for attempt in range(retries):
        try:
            return client.generate_content(prompt)
        except hex.ServiceUnavailable:
            print(
                f"⚠️ Service unavailable, retrying in {delay} seconds... (Attempt {attempt+1}/{retries})"
            )
            time.sleep(delay)
    raise RuntimeError("Failed to generate content after multiple retries")

def dataset_gen(topic: str, lvl: str, desc: str, tools: str):
    """Generate and save a dummy dataset."""

    data_prompt = f"""
    You are a project asset generator for University students.
    Given the following information, generate a dummy dataset:

    Project Title: {topic}
    Project Level: {lvl}
    Project Description:
    {desc}
    Required Tools: {tools}

    Important instructions:
    - Do NOT include any introductory or explanatory sentences (e.g., “Okay, here’s your data...”).
    - Do NOT mention that you are an AI or that you are generating content.
    - Start directly with the dummy data.
    - Avoid meta language (e.g., “This rubric is designed to…”).
    - Dont add the "'''csv" and "'''" before and after the data, it will get add as a row in the csv.
    """

    dataset = safe_generate(data_prompt)
    csv_content = dataset.text
    filename = "project_dataset.csv"

    lines = [line for line in csv_content.strip().splitlines() if line.strip()]
    if len(lines) > 2:
        cleaned_csv = "\n".join(lines[1:-1])
    else:
        cleaned_csv = csv_content.strip()
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(cleaned_csv)
        print(f"✅ Success! dataset saved as {filename}")
    except Exception as e:
        print(f"❌ Error saving dataset: {e}")


def prompt_engine():
    """Generate success criteria and evaluation rubric."""
    info = load_info()
    title, level, description, tools, dataset_flag = (
        info["title"],
        info["level"],
        info["description"],
        info["required_tools"],
        info["dataset"],
    )

    success_prompt = f"""
    You are a project asset generator for University students.
    Given the following information, generate Success Criteria:

    Project Title: {title}
    Project Level: {level}
    Project Description:
    {description}
    Required Tools: {tools}

    Important instructions:
    - Do NOT include any introductory or explanatory sentences (e.g., “Okay, here’s your rubric...”).
    - Do NOT mention that you are an AI or that you are generating content.
    - Start directly with the rubric or criteria content.
    - The output should look like a professional document written by an instructor, not an AI.
    - Avoid meta language (e.g., “This rubric is designed to…”).
    - Present the output in clear, structured form using bullet points or tables if suitable.
    """

    rubric_prompt = f"""
    You are a project asset generator for University students.
    Given the following information, generate an Evaluation Rubric:

    Project Title: {title}
    Project Level: {level}
    Project Description:
    {description}
    Required Tools: {tools}

    Important instructions:
    - Do NOT include any introductory or explanatory sentences (e.g., “Okay, here’s your rubric...”).
    - Do NOT mention that you are an AI or that you are generating content.
    - Start directly with the rubric or criteria content.
    - The output should look like a professional document written by an instructor, not an AI.
    - Avoid meta language (e.g., “This rubric is designed to…”).
    - Present the output in clear, structured form using bullet points or tables if suitable.
    """

    if dataset_flag:
        dataset_gen(title, level, description, tools)

    success_criteria = safe_generate(success_prompt)
    evaluation_rubric = safe_generate(rubric_prompt)

    return success_criteria.text, evaluation_rubric.text


def project_docs():
    """Generate and save success criteria and evaluation rubric."""
    success_content, rubric_content = prompt_engine()

    files_to_save = {
        "success_criteria.txt": success_content,
        "evaluation_rubric.txt": rubric_content,
    }

    print("\n--- Saving Project Documentation ---")

    for filename, content in files_to_save.items():
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(content.strip())
            full_path = os.path.abspath(filename)
            print(f"✅ Saved: {filename}")
        except Exception as e:
            print(f"❌ Error saving {filename}: {e}")

    print("\nDocumentation saving complete.")


if __name__ == "__main__":
    project_docs()
