# AI Resume Screener: Python & CrewAI Architecture Plan

Based on the n8n workflow outlined in `Plan.md`, here is how you can replicate and enhance this system using Python and CrewAI. 

By moving to Python, we eliminate the need for premium third-party APIs (like CloudConvert for DOCX) by processing documents locally, and we can leverage CrewAI to break the analysis into specialized expert agents for better precision.

## 1. Required APIs & Credentials
- **OpenAI API Key (`OPENAI_API_KEY`)**: Required for the `gpt-4o` LLM to process and evaluate the resumes.
- **Google Drive / Google Sheets API** (Optional): If you want to automatically download resumes from a Drive folder and append results to a live Google Sheet.
- *(Note: CloudConvert API is NO LONGER NEEDED. Python can parse DOCX locally and for free).*

## 2. Python Tech Stack & Libraries
Initialize your environment installing these key libraries:
```bash
pip install crewai langchain-openai pymupdf python-docx pandas pydantic openpyxl
```
- **File Parsing**: `pymupdf` (for PDF), `python-docx` (for DOCX)
- **AI Orchestration**: `crewai` (for agents/tasks) and `pydantic` (for structured JSON outputs)
- **Data Export**: `pandas` and `openpyxl` (for saving directly to Excel)

## 3. System Architecture & CrewAI Design

### Phase 1: Local Ingestion & Parsing (Replacing Steps 1-3)
Instead of relying on n8n Webhooks/Forms, we will write a Python script that reads from a local directory (e.g., `./resumes/`).
- **Python Function**: A `read_document(file_path)` function that uses Python's `os` module to detect extensions.
  - If `.pdf`, use `pymupdf` to extract text.
  - If `.docx`, use `python-docx` to extract text.
  - If `.txt`, read standard UTF-8.

### Phase 2: CrewAI Agents (Replacing Step 5)
In the n8n plan, one giant AI prompt did all the work. With CrewAI, we can create a "Talent Acquisition Team" to divide the processing, preventing LLM context confusion and improving quality.

1. **Agent 1: Senior Technical Sourcer**
   - **Role**: Read the raw resume and concisely extract past experience, total years of experience, education, and skills.
2. **Agent 2: Expert Technical Recruiter**
   - **Role**: Compare Agent 1's extracted profile against the Job Description.
   - **Task**: Calculate the `overall_score`, `skills_match_pct`, formulate a `recommendation` (Shortlist/Maybe/Reject), and write the SWOT analysis (Strengths, Weaknesses, Risks, Opportunities).
3. **Agent 3: Talent Assessment Director**
   - **Role**: Review the evaluation and generate exactly 5 tailored interview questions based on the candidate's specific weaknesses or gaps, formatting the final output.

*Note: We will use LangChain's structured output features with a Pydantic model that mirrors the JSON schema in your `Plan.md` so the Crew output is strictly typed.*

### Phase 3: Data Flattening & Excel Export (Replacing Steps 6-8)
- The final output from the CrewAI execution will be a structured dictionary (via Pydantic).
- **Python Function**: A script iterates over the JSON arrays (`strengths`, `weaknesses`, `skills`) and uses standard Python `.join(" | ")` to flatten them.
- **Export**: Append the structured flattened dictionary to a `pandas` DataFrame, then use `.to_excel('AI_Recruiter_Results.xlsx', index=False)` to generate or append to the Excel file.

## 4. Step-by-Step Implementation Guide

1. **Setup Project Structure**:
   ```text
   /recruiter/
    ├── main.py (Entry point & loop)
    ├── parser.py (PDF/DOCX reading logic)
    ├── agents.py (CrewAI definitions)
    ├── schema.py (Pydantic models for JSON output)
    ├── resumes/ (Folder containing PDFs/DOCX)
    └── job_description.txt
   ```
2. **Define Pydantic Schema**: Replicate the exact JSON structure from `Plan.md` using Python `pydantic` classes to enforce rules like `minItems=5` on interview questions.
3. **Build the Crew**: Code the `Crew`, `Agent`, and `Task` objects in `agents.py`. Use the Pydantic schema as the `output_pydantic` property on the final Task.
4. **Build the Loop**: In `main.py`, iterate over the `resumes/` folder, call the parser, pass the text to the Crew, get the JSON, append to a list, and finally save to `.xlsx`.
