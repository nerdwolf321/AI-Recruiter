from crewai import LLM
import traceback

print("Testing crewai LLM...")
try:
    llm = LLM(model="ollama/llama3", base_url="http://localhost:11434")
    print(llm)
    print("Success!")
except Exception as e:
    print(f"Error: {e}")
    traceback.print_exc()
