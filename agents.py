import os
from schema import ResumeEvaluation
from crewai import Agent, Task, Crew, Process

class LLMConfigManager:
    """Manages different LLM API configurations and allows switching between them."""
    
    def __init__(self):
        self.configs = {}
        # Pre-load default configuration pulling from the environment variables
        self.add_config(
            name="default",
            provider=os.getenv("LLM_PROVIDER", "ollama").lower(),
            model=os.getenv("LLM_MODEL", "llama3"),
            api_key=os.getenv("OPENAI_API_KEY", "")
        )

    def add_config(self, name: str, provider: str, model: str, api_key: str = "", base_url: str = "", temperature: float = 0.2):
        """Register a new API configuration profile."""
        self.configs[name] = {
            "provider": provider.lower(),
            "model": model,
            "api_key": api_key,
            "base_url": base_url,
            "temperature": temperature
        }

    def get_llm(self, config_name: str = "default"):
        """Get an initialized LLM instance based on a registered config name."""
        if config_name not in self.configs:
            raise ValueError(f"Configuration '{config_name}' not found. Available: {list(self.configs.keys())}")
            
        config = self.configs[config_name]
        provider = config["provider"]
        model_name = config["model"]
        temperature = config["temperature"]
        api_key = config["api_key"]
        
        try:
            if provider == "openai":
                from langchain_openai import ChatOpenAI
                return ChatOpenAI(model=model_name, api_key=api_key, temperature=temperature)
                
            elif provider == "gemini":
                from langchain_google_genai import ChatGoogleGenerativeAI
                # Allow fallback to OS env if it was not explicitly passed in config
                key = api_key or os.getenv("GOOGLE_API_KEY", "")
                return ChatGoogleGenerativeAI(model=model_name, google_api_key=key, temperature=temperature)
                
            elif provider == "deepseek":
                from langchain_openai import ChatOpenAI
                key = api_key or os.getenv("DEEPSEEK_API_KEY", "")
                base_url = config.get("base_url") or "https://api.deepseek.com"
                return ChatOpenAI(
                    model=model_name, 
                    api_key=key, 
                    base_url=base_url,
                    temperature=temperature
                )
                
            elif provider == "anthropic":
                from langchain_anthropic import ChatAnthropic
                key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
                return ChatAnthropic(model=model_name, api_key=key, temperature=temperature)
                
            else: # defaults to ollama
                from crewai import LLM
                base_url = config.get("base_url") or "http://localhost:11434"
                return LLM(model="ollama/" + model_name, base_url=base_url, temperature=temperature)
                
        except Exception as e:
            print(f"Failed to initialize LLM provider '{provider}': {e}")
            return None

# Initialize the manager
llm_manager = LLMConfigManager()

# --- Pre-configure the APIs from your .env ---
llm_manager.add_config(
    name="openai", 
    provider="openai", 
    model="gpt-4o-mini", # Adjust model if needed
    api_key=os.getenv("OPENAI_API_KEY", "")
)

llm_manager.add_config(
    name="gemini", 
    provider="gemini", 
    model="gemini-pro", # Use 'gemini-pro' to avoid NOT_FOUND errors
    api_key=os.getenv("GEMINI_API_KEY", "")
)

llm_manager.add_config(
    name="ollama", 
    provider="ollama", 
    model="llama3", 
    api_key=os.getenv("Ollama_API_KEY", ""),
    base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
)

# Set the active configuration by checking ACTIVE_LLM in your .env file
# Defaults to "openai" if not explicitly specified.
active_config = os.getenv("ACTIVE_LLM", "openai").lower()
llm = llm_manager.get_llm(active_config)

class TalentAcquisitionCrew:
    def __init__(self, resume_text: str, jd_text: str, role_title: str):
        self.resume_text = resume_text
        self.jd_text = jd_text
        self.role_title = role_title
        if not llm:
            raise Exception("LLM is not initialized. Ensure OPENAI_API_KEY is available in the environment.")

    def create_agents(self):
        # Agent 1: Parser
        self.parser_agent = Agent(
            role='Senior HR Parsing Specialist',
            goal='Extract all factual information from the candidate resume precisely without inventing anything.',
            backstory='You are a meticulous HR specialist with 15 years of experience in data extraction and resume parsing. You find all the facts without making up information.',
            verbose=True,
            llm=llm,
            allow_delegation=False
        )

        # Agent 2: Evaluator
        self.evaluator_agent = Agent(
            role='Expert Technical Recruiter',
            goal='Compare the extracted candidate profile against the job description and accurately score the candidate.',
            backstory='You are an expert technical recruiter with 20 years of talent acquisition experience. You are known for your objective scoring and insightful SWOT analyses.',
            verbose=True,
            llm=llm,
            allow_delegation=False
        )

        # Agent 3: Director
        self.director_agent = Agent(
            role='Talent Assessment Director',
            goal='Review the evaluation, finalize the scoring, and generate targeted interview questions based on the candidate weaknesses.',
            backstory='You are the Director of Talent. Your job is to make the final call on candidates and prepare the hiring managers with tough, targeted questions.',
            verbose=True,
            llm=llm,
            allow_delegation=False
        )

    def create_tasks(self):
        task1 = Task(
            description=f'''
            Analyze the following resume text:
            <RESUME>
            {self.resume_text}
            </RESUME>
            
            Extract ALL work experiences (company, role, duration).
            Calculate total_years_exp (sum of contiguous work periods, do not double-count overlapping periods).
            Identify all skills mentioned. Extract education and certifications. 
            Find the candidate_name, email, phone, location, and linkedin_url (if present).
            Do not invent or assume any information not explicitly stated.
            '''.strip(),
            expected_output='A comprehensive and purely factual summary of the candidate\'s profile based strictly on the resume text.',
            agent=self.parser_agent
        )

        task2 = Task(
            description=f'''
            Evaluate the parsed candidate profile against the Job Description for the role: {self.role_title}
            <JOB_DESCRIPTION>
            {self.jd_text}
            </JOB_DESCRIPTION>
            
            Calculate the following core scores (0-100): overall_score, skills_match_pct, experience_score, education_score.
            Recommend exactly one of: Shortlist, Maybe, Reject.
            Determine seniority_level exactly one of: Intern, Junior, Mid, Senior, Lead, Executive.
            Write a critical SWOT analysis (Strengths, Weaknesses, Risks, Opportunities).
            Identify missing_skills (skills required by the JD that are NOT found in the resume).
            Write a concise 2-3 sentence summary evaluating the overall fit.
            '''.strip(),
            expected_output='Detailed evaluation including the 4 requested scores, standard categorized SWOT analysis, and matching/missing skills vs the job description.',
            agent=self.evaluator_agent,
            context=[task1]
        )

        task3 = Task(
            description=f'''
            Finalize the candidate evaluation for the {self.role_title} position.
            Review the extracted facts from the HR Parser and the evaluation scores/SWOT from the Recruiter.
            Based on the candidate's weaknesses, missing skills, and identified risks, generate exactly 5 tailored interview questions. The questions should be specific to testing the candidates gaps.
            Compile all extracted data, scores, SWOT, and interview questions into the final structured output format exactly matching the required schema.
            '''.strip(),
            expected_output='The complete JSON structured output representing the entire resume evaluation, strictly adhering to the mandated schema properties.',
            agent=self.director_agent,
            context=[task1, task2],
            output_pydantic=ResumeEvaluation
        )

        self.tasks = [task1, task2, task3]

    def process(self):
        self.create_agents()
        self.create_tasks()
        crew = Crew(
            agents=[self.parser_agent, self.evaluator_agent, self.director_agent],
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True
        )
        
        # CrewOutput object returned
        result = crew.kickoff()
        return result.pydantic
