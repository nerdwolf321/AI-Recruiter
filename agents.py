import os
from schema import ResumeEvaluation
from crewai import Agent, Task, Crew, Process, LLM

class LLMConfigManager:
    """Manages different LLM API configurations and allows switching between them."""
    
    def __init__(self):
        self.configs = {}
        # Pre-load default configuration pulling from the environment variables
        self.add_config(
            name="default",
            provider=os.getenv("LLM_PROVIDER", "ollama").lower(),
            model=os.getenv("LLM_MODEL", "llama3"),
            api_key=os.getenv("OPENAI_API_KEY", ""),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            temperature=0.0
        )
        self.add_config(
            name="anthropic",
            provider="anthropic",
            model=os.getenv("LLM_MODEL", "claude-3-5-sonnet-20241022"),
            api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            temperature=0.0
        )

    def add_config(self, name: str, provider: str, model: str, api_key: str = "", base_url: str = "", temperature: float = 0.0):
        """Register a new API configuration profile."""
        self.configs[name] = {
            "provider": provider.lower(),
            "model": model,
            "api_key": api_key,
            "base_url": base_url,
            "temperature": temperature
        }

    def get_llm(self, config_name: str = "default", temperature_override: float = 0.0):
        """Get an initialized LLM instance based on a registered config name."""
        if config_name not in self.configs:
            config_name = "default"
            
        config = self.configs[config_name]
        provider = config["provider"]
        model_name = config["model"]
        temperature = temperature_override if temperature_override is not None else config["temperature"]
        base_url = config.get("base_url")
        
        try:
            if provider == "ollama":
                # Try standard CrewAI LLM first
                try:
                    return LLM(model=f"ollama/{model_name}", base_url=base_url, temperature=temperature)
                except Exception:
                    # Fallback for older/buggy LiteLLM installs
                    return LLM(model=f"openai/{model_name}", base_url=f"{base_url}/v1", api_key="ollama", temperature=temperature)
            elif provider == "anthropic":
                return LLM(model=f"anthropic/{model_name}", api_key=config["api_key"], temperature=temperature)
            elif provider == "openai":
                return LLM(model=model_name, api_key=config["api_key"], temperature=temperature)
            else:
                return LLM(model=model_name, temperature=temperature)
        except Exception as e:
            print(f"Failed to initialize LLM provider '{provider}': {e}")
            return None

# Initialize the manager
llm_manager = LLMConfigManager()

# Load specific overrides from .env for Anthropic as requested
ACTIVE_LLM = os.getenv("ACTIVE_LLM", "anthropic").lower()
LLM_MODEL = os.getenv("LLM_MODEL", "claude-3-5-sonnet-20241022")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")

# Set the active configuration
llm_default = llm_manager.get_llm(ACTIVE_LLM, temperature_override=0.0) # For Auditing
llm_creative = llm_manager.get_llm(ACTIVE_LLM, temperature_override=0.2) # For Analysis

class TalentAcquisitionCrew:
    def __init__(self, resume_text: str, jd_text: str, role_title: str):
        self.resume_text = resume_text
        self.jd_text = jd_text
        self.role_title = role_title
        
        # Initialize attributes for Pyre consistency
        self.parser_agent = None
        self.evaluator_agent = None
        self.director_agent = None
        self.tasks = []
        
        if not llm_default:
            raise Exception("LLM is not initialized. Ensure ANTHROPIC_API_KEY is set in .env.")

    def create_agents(self):
        # Agent 1: Senior HR Data Auditor (Anthropic ONLY)
        self.parser_agent = Agent(
            role='Senior HR Data Auditor',
            goal='Extract UNIQUE factual entities. Focus on unique roles, companies, education, and skills.',
            backstory=(
                "You are an expert HR Auditor. Your objective is to extract factual units from resumes. "
                "If the same experience appears in multiple sections, you MERGE them into one entry. "
                "STRICT RULES: NO hallucinations. If info is not explicitly present, leave the field empty. "
                "Do NOT double-count overlapping time periods."
            ),
            verbose=True,
            llm=llm_default,
            allow_delegation=False
        )

        # Agent 2: Evaluator - STRATEGIC ANALYSIS (Temp 0.2)
        self.evaluator_agent = Agent(
            role='Expert Technical Talent Strategist',
            goal='Analyze candidate fit against Job Descriptions with critical, objective scoring.',
            backstory=(
                "You are a seasoned Technical Recruiter. You look beyond keywords to understand the IMPACT "
                "of a candidate's work. You identify red flags, growth potential, and culture fit."
            ),
            verbose=True,
            llm=llm_creative,
            allow_delegation=False
        )

        # Agent 3: Director - DATA CONSOLIDATOR (Temp 0.0)
        self.director_agent = Agent(
            role='Head of Global Talent Analytics',
            goal='Consolidated all findings into a clean, duplicate-free, Pydantic-compliant report.',
            backstory=(
                "You are a data perfectionist. Your job is to take the auditor's facts and the recruiter's "
                "insights and merge them. You strictly ensure NO DUPLICATE entries in the final list fields. "
                "If the recruiter and auditor mention the same skill, you normalize it to a single list entry."
            ),
            verbose=True,
            llm=llm_default,
            allow_delegation=False
        )

    def create_tasks(self):
        if not self.parser_agent or not self.evaluator_agent or not self.director_agent:
            self.create_agents()
            
        task1 = Task(
            description=(
                "### CONTEXT ###\n"
                "Raw resume text provided below.\n\n"
                "### OBJECTIVE ###\n"
                "Extract UNIQUE factual entities. If the same experience is mentioned twice in different sections, "
                "MERGE them into one entry. Focus on unique roles, companies, and skills.\n\n"
                "### CONSTRAINTS ###\n"
                "- STRICTLY NO HALLUCINATIONS. If info is not there, leave empty.\n"
                "- Use the raw text below:\n"
                f"<RESUME_TEXT>\n{self.resume_text}\n</RESUME_TEXT>\n"
                "- For 'total_years_exp', do not double-count overlapping periods."
            ),
            expected_output='A clean, unique factual summary of history and skills.',
            agent=self.parser_agent
        )

        task2 = Task(
            description=(
                "### CONTEXT ###\n"
                "Evaluate the parsed profile against the role: {role_title}.\n\n"
                "### OBJECTIVE ###\n"
                "Perform matching analysis (Scores 0-100, SWOT, Seniority).\n\n"
                "### JOB DESCRIPTION ###\n"
                f"{self.jd_text}\n\n"
                "### CONSTRAINTS ###\n"
                "- Identify 'Missing Skills' specifically required by the JD."
            ).format(role_title=self.role_title),
            expected_output='A strategic evaluation report.',
            agent=self.evaluator_agent,
            context=[task1]
        )

        task3 = Task(
            description=(
                "### CONTEXT ###\n"
                "Finalize the Report for {role_title}.\n\n"
                "### OBJECTIVE ###\n"
                "1. Merge the Auditor's facts and Recruiter's insights.\n"
                "2. Generate 5 unique gap-targeted interview questions.\n"
                "3. REMOVE ALL DUPLICATES from `skills_list`, `past_experience`, and SWOT lists.\n\n"
                "### CONSTRAINTS ###\n"
                "- The output MUST be valid Pydantic/JSON according to schema.\n"
                "- If a skill like 'Python' appears twice, keep only one."
            ).format(role_title=self.role_title),
            expected_output='The final ResumeEvaluation object with strictly unique entries.',
            agent=self.director_agent,
            context=[task2], # PRUNED CONTEXT: task2 already includes task1 in its flow
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
        
        result = crew.kickoff()
        return result.pydantic
