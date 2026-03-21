import os
import glob
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables (e.g., OPENAI_API_KEY)
load_dotenv()

from parser import read_document
from agents import TalentAcquisitionCrew
from schema import ResumeEvaluation

def flatten_outputs(eval_data: ResumeEvaluation, file_name: str, role_title: str) -> dict:
    """Flattens the Pydantic object into a dictionary suitable for a single Excel row."""
    # Handle potentially missing lists by safely defaulting to empty list
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
        "Past Experience": " | ".join([f"{e.company} · {e.role} · {e.duration}" for e in past_exp]),
        "Total Years Exp.": getattr(eval_data, 'total_years_exp', 0),
        "Education": eval_data.education,
        "Certifications": eval_data.certifications,
        "Interview Questions": " | ".join(questions),
        "Seniority Level": eval_data.seniority_level,
        
        "Processed Date": datetime.now().isoformat(),
        "File Name": file_name,
        "Recruiter Notes": "",      # Manual column
        "Interview Status": ""      # Manual column
    }

def process_resumes():
    # 1. Read Job Description
    try:
        with open("job_description.txt", "r", encoding="utf-8") as f:
            jd_text = f.read()
            # Try to grab the role title from the very first line of the JD
            first_line = jd_text.strip().split('\n')[0]
            role_title = first_line.replace("Role:", "").strip() if "Role:" in first_line else "Software Engineer"
    except Exception as e:
        print(f"Error reading job_description.txt: {e}")
        print("Please create 'job_description.txt' with 'Role: [Role Name]' on the first line.")
        return

    # 2. Iterate through resumes folder
    resume_files = glob.glob("resumes/*.*")
    if not resume_files:
        print("No resumes found in the 'resumes/' directory. Please add some PDF/DOCX/TXT files.")
        return

    all_results = []
    
    for file_path in resume_files:
        file_name = os.path.basename(file_path)
        print(f"\n--- Processing {file_name} ---")
        
        # Parse Document Extractor
        resume_text = read_document(file_path)
        if not resume_text or len(resume_text.strip()) < 20:
            print(f"Skipping {file_name} - no text could be extracted.")
            continue
            
        # Run CrewAI Pipeline
        try:
            print(f"-> Running AI evaluation for {file_name} using Ollama...")
            crew = TalentAcquisitionCrew(resume_text, jd_text, role_title)
            pydantic_output = crew.process()
            
            if pydantic_output:
                flat_data = flatten_outputs(pydantic_output, file_name, role_title)
                all_results.append(flat_data)
                print(f"-> Successfully analyzed {file_name}!")
            else:
                print(f"-> Failed to generate structured Pydantic output for {file_name}.")
        except Exception as e:
            print(f"-> Agent pipeline failed for {file_name}: {e}")

    # 3. Export to Excel
    if all_results:
        df = pd.DataFrame(all_results)
        output_file = "AI_Recruiter_Results.xlsx"
        try:
            df.to_excel(output_file, index=False)
            print(f"\n✅ Processing complete! {len(all_results)} resumes evaluated.\nResults saved to: {output_file}")
        except Exception as e:
            # Fallback to CSV if openpyxl fails
            print(f"Error saving to Excel: {e}\nFalling back to CSV...")
            df.to_csv("AI_Recruiter_Results.csv", index=False)
            print(f"Results saved to: AI_Recruiter_Results.csv")

if __name__ == "__main__":
    # if not os.environ.get("OPENAI_API_KEY"):
    #     print("WARNING: OPENAI_API_KEY environment variable is missing! Please set it.")
    #     print("Example: set OPENAI_API_KEY=sk-xxxxxx")
    
    process_resumes()
