import os
import glob
import re
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables (e.g., OPENAI_API_KEY)
load_dotenv()

from parser import read_document
from agents import TalentAcquisitionCrew
from schema import ResumeEvaluation

def clean_text(text: str) -> str:
    """Cleans raw extracted text by removing excessive whitespace and junk characters."""
    if not text:
        return ""
    # Remove null bytes and non-printable characters
    text = "".join(char for char in text if char.isprintable() or char in "\n\r\t")
    # Collapse multiple newlines/spaces
    text = re.sub(r'\n+', '\n', text)
    text = re.sub(r' +', ' ', text)
    return text.strip()

def flatten_outputs(eval_data: ResumeEvaluation, file_name: str, role_title: str) -> dict:
    """Flattens the Pydantic object into a dictionary suitable for a single Excel row."""
    # Ensure eval_data is not None
    if not eval_data:
        return {}
        
    strengths = getattr(eval_data, 'strengths', []) or []
    weaknesses = getattr(eval_data, 'weaknesses', []) or []
    risks = getattr(eval_data, 'risks', []) or []
    opportunities = getattr(eval_data, 'opportunities', []) or []
    skills = getattr(eval_data, 'skills_list', []) or []
    missing = getattr(eval_data, 'missing_skills', []) or []
    questions = getattr(eval_data, 'interview_questions', []) or []
    past_exp = getattr(eval_data, 'past_experience', []) or []

    return {
        "Candidate Name": eval_data.candidate_name,
        "Email": eval_data.email,
        "Phone": eval_data.phone,
        "Location": eval_data.location,
        "Source": "Upload / Local Scan",
        "LinkedIn URL": getattr(eval_data, 'linkedin_url', ""),
        
        "Overall Score": getattr(eval_data, 'overall_score', 0),
        "Skills Match %": getattr(eval_data, 'skills_match_pct', 0),
        "Experience Score": getattr(eval_data, 'experience_score', 0),
        "Education Score": getattr(eval_data, 'education_score', 0),
        "Recommendation": eval_data.recommendation,
        
        "Summary": eval_data.summary,
        "Strengths": " | ".join(strengths),
        "Weaknesses": " | ".join(weaknesses),
        "Risks": " | ".join(risks),
        "Opportunities": " | ".join(opportunities),
        "Skills List": ", ".join(skills),
        "Missing Skills": ", ".join(missing),
        "Past Experience": " | ".join([f"{e.company} ({e.role}) [{e.duration}]" for e in past_exp]),
        "Total Years Exp.": getattr(eval_data, 'total_years_exp', 0),
        "Education": eval_data.education,
        "Certifications": eval_data.certifications,
        "Interview Questions": " | ".join(questions),
        "Seniority Level": eval_data.seniority_level,
        
        "Processed Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "File Name": file_name,
        "Recruiter Notes": "",      # Manual column
        "Interview Status": ""      # Manual column
    }

def process_resumes():
    # 1. Read Job Description
    try:
        jd_path = "job_description.txt"
        if not os.path.exists(jd_path):
            print(f"Error: {jd_path} not found.")
            return
            
        with open(jd_path, "r", encoding="utf-8") as f:
            jd_text = f.read()
            # Grab role title from first line or default
            lines = [l.strip() for l in jd_text.split('\n') if l.strip()]
            role_title = lines[0].replace("Role:", "").strip() if lines and "Role:" in lines[0] else "Software Engineer"
    except Exception as e:
        print(f"Error reading job_description.txt: {e}")
        return

    # 2. Iterate through resumes folder
    resume_files = glob.glob("resumes/*.*")
    # Filter for supported extensions
    resume_files = [f for f in resume_files if f.lower().endswith(('.pdf', '.docx', '.txt'))]
    
    if not resume_files:
        print("No valid resumes found in 'resumes/'. Please add PDF, DOCX, or TXT files.")
        return

    print(f"🚀 Found {len(resume_files)} resumes to process for role: {role_title}")
    all_results = []
    
    for file_path in resume_files:
        file_name = os.path.basename(file_path)
        print(f"\n--- 📄 Analyzing {file_name} ---")
        
        # Parse Document
        raw_text = read_document(file_path)
        cleaned_text = clean_text(raw_text)
        
        if not cleaned_text or len(cleaned_text) < 50:
            print(f"⚠️ Skipping {file_name} - insufficient text extracted.")
            continue
            
        # Run CrewAI Pipeline
        try:
            print(f"-> Starting CrewAI pipeline for {file_name}...")
            crew = TalentAcquisitionCrew(cleaned_text, jd_text, role_title)
            pydantic_output = crew.process()
            
            if pydantic_output:
                flat_data = flatten_outputs(pydantic_output, file_name, role_title)
                if flat_data:
                    all_results.append(flat_data)
                    print(f"✅ Successfully analyzed {file_name}!")
            else:
                print(f"❌ Pipeline returned no structured data for {file_name}.")
        except Exception as e:
            print(f"💥 Critical failure analyzing {file_name}: {e}")

    # 3. Export to Excel
    if all_results:
        df = pd.DataFrame(all_results)
        output_file = f"AI_Recruiter_Results_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        try:
            df.to_excel(output_file, index=False)
            print(f"\n✨ Processing complete! {len(all_results)} resumes evaluated.")
            print(f"📊 Results saved to: {output_file}")
        except Exception as e:
            fallback_csv = output_file.replace(".xlsx", ".csv")
            print(f"Error saving to Excel: {e}\nFalling back to CSV: {fallback_csv}")
            df.to_csv(fallback_csv, index=False)

if __name__ == "__main__":
    process_resumes()
