from pydantic import BaseModel, Field
from typing import List, Optional

class PastExperience(BaseModel):
    company: str = Field(description="Full name of the company")
    role: str = Field(description="Exact job title held")
    duration: str = Field(description="Time period (e.g., 'Jan 2020 - Mar 2022' or '2 years')")

class ResumeEvaluation(BaseModel):
    candidate_name: str = Field(description="Full name of the candidate extracted from the resume")
    email: str = Field(default="", description="Professional email address")
    phone: str = Field(default="", description="Contact phone number in international format if possible")
    location: str = Field(default="", description="Current city/state/country of residence")
    linkedin_url: str = Field(default="", description="Full LinkedIn profile URL if explicitly mentioned")
    
    overall_score: float = Field(description="Numerical score 0-100 indicating total fit for the JD. 85+ is Exceptional.")
    skills_match_pct: float = Field(description="0-100 percentage based on hard skills listed in JD vs Resume")
    experience_score: float = Field(description="0-100 score reflecting relevance of previous roles and seniority")
    education_score: float = Field(description="0-100 score for academic background and relevant certifications")
    
    recommendation: str = Field(description="MUST be exactly one of: 'Shortlist', 'Maybe', 'Reject'")
    seniority_level: str = Field(description="MUST be exactly one of: 'Intern', 'Junior', 'Mid', 'Senior', 'Lead', 'Executive'")
    
    summary: str = Field(description="A high-impact 3-sentence executive summary of the candidate's value proposition.")
    strengths: List[str] = Field(description="List 3-5 objective, evidence-backed reasons why this candidate fits the role.")
    weaknesses: List[str] = Field(description="List 3-5 specific gaps where the candidate does not meet JD requirements.")
    risks: List[str] = Field(description="Potential red flags (e.g., job hopping, lack of core tech stack, visa issues).")
    opportunities: List[str] = Field(description="Areas where the candidate could grow or bring unique adjacent value.")
    
    skills_list: List[str] = Field(description="Comprehensive list of all technical and soft skills found in the resume.")
    missing_skills: List[str] = Field(description="List of CRITICAL skills from the JD that are not in the resume.")
    
    past_experience: List[PastExperience] = Field(description="Chronological list of previous professional roles.")
    total_years_exp: float = Field(description="Calculated total professional experience in years (numeric). Use 0.5 for 6 months.")
    
    education: str = Field(description="Summary of highest degree, institution, and major.")
    certifications: str = Field(default="", description="Relevant professional certifications (e.g., AWS, PMP).")
    
    interview_questions: List[str] = Field(
        min_length=5, 
        max_length=5, 
        description="EXACTLY 5 tailored, difficult technical/behavioral questions to probe identified weaknesses."
    )
