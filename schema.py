from pydantic import BaseModel, Field
from typing import List

class PastExperience(BaseModel):
    company: str
    role: str
    duration: str

class ResumeEvaluation(BaseModel):
    candidate_name: str
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin_url: str = Field(default="", description="LinkedIn profile link if available in the resume")
    overall_score: float = Field(description="0-100 overall fit. 80+ = strong shortlist, 60-79 = consider, below 60 = significant gaps")
    skills_match_pct: float = Field(description="0-100 percentage of JD-required skills found in the resume")
    experience_score: float = Field(description="0-100 relevance and years of experience vs JD requirement")
    education_score: float = Field(description="0-100 degree level and field relevance to role")
    recommendation: str = Field(description="Exactly one of: Shortlist, Maybe, Reject")
    seniority_level: str = Field(description="Exactly one of: Intern, Junior, Mid, Senior, Lead, Executive")
    summary: str = Field(description="A brief 2-3 sentence summary of the candidate's profile")
    strengths: List[str] = Field(description="3-5 specific, evidence-based reasons to hire for THIS role")
    weaknesses: List[str] = Field(description="Specific skill gaps or experience shortfalls vs THIS JD")
    risks: List[str] = Field(description="e.g. job-hopping, unexplained gaps, overqualification, location mismatch")
    opportunities: List[str] = Field(description="Growth potential, adjacent transferable skills, trainability signals")
    skills_list: List[str] = Field(description="All skills mentioned anywhere in the resume")
    missing_skills: List[str] = Field(description="Skills required by the JD that are not found in the resume")
    past_experience: List[PastExperience]
    total_years_exp: float = Field(description="Sum of all work periods calculated iteratively (do not double-count overlapping periods)")
    education: str
    certifications: str = ""
    interview_questions: List[str] = Field(
        min_length=5, 
        max_length=5, 
        description="Exactly 5 tailored interview questions specific to this candidate and this JD based on weaknesses or gaps."
    )
