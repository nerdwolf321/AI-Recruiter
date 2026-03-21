Build me a complete n8n workflow called "AI Resume Screener" that automates the entire recruitment process — from multi-format resume ingestion to a fully scored Excel output with AI-generated SWOT analysis for every candidate.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TRIGGER — INPUT SOURCES (2 options)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Option A (primary): Use an n8n Form Trigger node with these fields:
  - Field 1: "resume_files" — type: File, allow multiple uploads, required
  - Field 2: "job_description" — type: Textarea, required, label: "Paste Job Description"
  - Field 3: "role_title" — type: Text, required, label: "Role Title / Position Name"
  - Form title: "AI Resume Screener"

Option B (secondary / automated): Add a Google Drive Trigger node that watches a specific folder for new files. Connect it in parallel so either trigger can start the workflow.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 1 — SPLIT FILES INTO LOOP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Add a Split In Batches node immediately after the trigger:
  - Batch Size: 1
  - This enables the workflow to process each uploaded resume individually through the full pipeline

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 2 — FILE TYPE DETECTION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Add a Switch node with 3 output branches based on MIME type:
  - Output 1 name: "PDF" — condition: {{ $binary.resume_files.mimeType === 'application/pdf' }}
  - Output 2 name: "DOCX" — condition: {{ $binary.resume_files.mimeType === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' }}
  - Output 3 name: "TXT" — condition: {{ $binary.resume_files.mimeType === 'text/plain' }}
  - Fallback: route to TXT branch

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 3 — FILE EXTRACTION (3 parallel branches)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PDF Branch:
  - Add an "Extract from File" node
  - Operation: Extract from PDF
  - Input binary field: resume_files
  - Put extracted text into a field called: resume_text

DOCX Branch:
  - Add HTTP Request node (POST to CloudConvert API) to convert DOCX to TXT
    URL: https://api.cloudconvert.com/v2/jobs
    Auth header: Bearer {{ $credentials.cloudconvert_api_key }}
    Body: JSON with import/convert/export task chain for docx → txt
  - Add second HTTP Request node (GET) to download the converted file URL
    URL: {{ $json.result.files[0].url }}
    Output field: resume_text

TXT / Plain text Branch:
  - Add a Code node (JavaScript)
  - Decode binary to UTF-8 string:
    const binaryData = $input.first().binary.resume_files;
    const text = Buffer.from(binaryData.data, 'base64').toString('utf-8');
    return [{ json: { resume_text: text } }];

All 3 branches connect into a Merge node (mode: Append) which outputs a unified { resume_text: "..." } item.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 4 — DATA PREPARATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Add a Set node after the Merge node to assemble all fields needed by the AI:
  - resume_text: {{ $json.resume_text }}
  - jd_text: {{ $("n8n Form Trigger").first().json.job_description }}
  - role_title: {{ $("n8n Form Trigger").first().json.role_title }}
  - file_name: {{ $binary.resume_files.fileName }}
  - processed_date: {{ $now.toISO() }}
  - source: "upload"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 5 — AI AGENT (THE CORE ENGINE)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Add an AI Agent node (Tools Agent type) with these sub-nodes connected:
  1. OpenAI Chat Model — model: gpt-4o, temperature: 0.2, max_tokens: 2500
  2. Structured Output Parser — with the JSON schema defined below

SYSTEM PROMPT for the AI Agent:
"""
You are an expert AI recruiter with 20 years of talent acquisition experience. Analyse the given resume against the provided job description and return a complete structured evaluation in valid JSON.

SCORING RULES:
- overall_score: 0–100 overall fit. 80+ = strong shortlist, 60–79 = consider, below 60 = significant gaps
- skills_match_pct: percentage of JD-required skills found in the resume (0–100)
- experience_score: 0–100 relevance and years of experience vs JD requirement
- education_score: 0–100 degree level and field relevance to role
- recommendation: exactly one of "Shortlist" / "Maybe" / "Reject"
- seniority_level: exactly one of "Intern" / "Junior" / "Mid" / "Senior" / "Lead" / "Executive"

SWOT ANALYSIS RULES:
- strengths: 3–5 specific, evidence-based reasons to hire for THIS role
- weaknesses: specific skill gaps or experience shortfalls vs THIS JD
- risks: job-hopping (tenures under 1 year), unexplained gaps over 6 months, overqualification, location mismatch
- opportunities: growth potential, adjacent transferable skills, trainability signals

EXTRACTION RULES:
- Extract ALL work experiences with company, role title, and duration
- Calculate total_years_exp by summing all work periods (do not count overlaps twice)
- Extract ALL skills mentioned anywhere in the resume into skills_list
- Compare skills_list with JD requirements and list gaps in missing_skills
- Generate exactly 5 tailored interview questions specific to this candidate and this JD
- Do not invent or assume any information not present in the resume text
- If a field cannot be determined, use an empty string or empty array
"""

USER MESSAGE for the AI Agent:
"""
Analyse this resume for the role below and return the complete JSON evaluation.

ROLE: {{ $json.role_title }}

JOB DESCRIPTION:
{{ $json.jd_text }}

RESUME TEXT:
{{ $json.resume_text }}

FILE: {{ $json.file_name }}
DATE: {{ $json.processed_date }}
"""

STRUCTURED OUTPUT PARSER JSON SCHEMA:
{
  "type": "object",
  "properties": {
    "candidate_name": { "type": "string" },
    "email": { "type": "string" },
    "phone": { "type": "string" },
    "location": { "type": "string" },
    "overall_score": { "type": "number" },
    "skills_match_pct": { "type": "number" },
    "experience_score": { "type": "number" },
    "education_score": { "type": "number" },
    "recommendation": { "type": "string", "enum": ["Shortlist", "Maybe", "Reject"] },
    "seniority_level": { "type": "string", "enum": ["Intern","Junior","Mid","Senior","Lead","Executive"] },
    "summary": { "type": "string" },
    "strengths": { "type": "array", "items": { "type": "string" } },
    "weaknesses": { "type": "array", "items": { "type": "string" } },
    "risks": { "type": "array", "items": { "type": "string" } },
    "opportunities": { "type": "array", "items": { "type": "string" } },
    "skills_list": { "type": "array", "items": { "type": "string" } },
    "missing_skills": { "type": "array", "items": { "type": "string" } },
    "past_experience": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "company": { "type": "string" },
          "role": { "type": "string" },
          "duration": { "type": "string" }
        }
      }
    },
    "total_years_exp": { "type": "number" },
    "education": { "type": "string" },
    "certifications": { "type": "string" },
    "interview_questions": { "type": "array", "items": { "type": "string" }, "minItems": 5, "maxItems": 5 }
  },
  "required": ["candidate_name","overall_score","skills_match_pct","experience_score","education_score","recommendation","seniority_level","summary","strengths","weaknesses","risks","opportunities","skills_list","missing_skills","past_experience","total_years_exp","education","interview_questions"]
}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 6 — FLATTEN ARRAYS TO STRINGS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Add a Set node after the AI Agent to convert all array fields into pipe-separated strings suitable for Excel cells:
  - strengths_flat: {{ $json.output.strengths.join(" | ") }}
  - weaknesses_flat: {{ $json.output.weaknesses.join(" | ") }}
  - risks_flat: {{ $json.output.risks.join(" | ") }}
  - opportunities_flat: {{ $json.output.opportunities.join(" | ") }}
  - skills_flat: {{ $json.output.skills_list.join(", ") }}
  - missing_skills_flat: {{ $json.output.missing_skills.join(", ") }}
  - interview_questions_flat: {{ $json.output.interview_questions.join(" | ") }}
  - experience_flat: {{ $json.output.past_experience.map(e => e.company + " · " + e.role + " · " + e.duration).join(" | ") }}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 7 — EXCEL OUTPUT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Add a Microsoft Excel 365 node (or Google Sheets node as alternative):
  - Operation: Append row to sheet
  - Workbook name: "AI Recruiter Results"
  - Sheet name: "Candidates"
  - Map these columns in this exact order:
      Col A  — Candidate Name:       {{ $json.output.candidate_name }}
      Col B  — Email:                {{ $json.output.email }}
      Col C  — Phone:                {{ $json.output.phone }}
      Col D  — Location:             {{ $json.output.location }}
      Col E  — Role Applied:         {{ $json.role_title }}
      Col F  — Overall Score:        {{ $json.output.overall_score }}
      Col G  — Skills Match %:       {{ $json.output.skills_match_pct }}
      Col H  — Experience Score:     {{ $json.output.experience_score }}
      Col I  — Education Score:      {{ $json.output.education_score }}
      Col J  — Recommendation:       {{ $json.output.recommendation }}
      Col K  — Seniority Level:      {{ $json.output.seniority_level }}
      Col L  — Summary:              {{ $json.output.summary }}
      Col M  — Strengths:            {{ $json.strengths_flat }}
      Col N  — Weaknesses:           {{ $json.weaknesses_flat }}
      Col O  — Risks:                {{ $json.risks_flat }}
      Col P  — Opportunities:        {{ $json.opportunities_flat }}
      Col Q  — Skills:               {{ $json.skills_flat }}
      Col R  — Missing Skills:       {{ $json.missing_skills_flat }}
      Col S  — Past Experience:      {{ $json.experience_flat }}
      Col T  — Total Years Exp:      {{ $json.output.total_years_exp }}
      Col U  — Education:            {{ $json.output.education }}
      Col V  — Certifications:       {{ $json.output.certifications }}
      Col W  — Interview Questions:  {{ $json.interview_questions_flat }}
      Col X  — File Name:            {{ $json.file_name }}
      Col Y  — Processed Date:       {{ $json.processed_date }}
      Col Z  — Source:               {{ $json.source }}
      Col AA — Recruiter Notes:      (leave blank — manual column)
      Col AB — Interview Status:     (leave blank — manual column)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 8 — LOOP BACK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Connect the Excel node output back to the Split In Batches node input to complete the loop. This makes the workflow process every uploaded file one by one, appending one row per resume to the Excel sheet.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CREDENTIALS REQUIRED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The workflow needs these credentials configured in n8n:
  1. OpenAI API — for the AI Agent node
  2. Microsoft 365 OAuth2 — for the Excel node (OR Google OAuth2 for Google Sheets)
  3. CloudConvert API key — for DOCX conversion (only needed if Word docs will be uploaded)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
IMPORTANT NOTES FOR BUILDER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- Every resume = 1 loop iteration = 1 Excel row appended
- The AI agent processes one resume at a time to avoid token limits
- The Structured Output Parser ensures the AI always returns clean JSON — never raw text
- Temperature 0.2 is critical for consistent and repeatable scoring across candidates
- The workflow supports unlimited resumes — 10, 40, or 100+ files in one form submission
- All array fields are flattened with pipe separator | so Excel cells stay clean and readable