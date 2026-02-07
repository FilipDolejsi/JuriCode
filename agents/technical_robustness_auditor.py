import os
from openai import OpenAI
import supabase
from fetch_codebase import get_relevant_content_for_agent 

dotenv.load_dotenv()

class TechnicalRobustnessAuditor:
    def __init__(self):
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.supabase_client = supabase.create_client(
            os.getenv("SUPABASE_URL"), 
            os.getenv("SUPABASE_KEY")
        )
        
    def run_audit(self, repo_url, github_token):
        try:
            llm_input, repo_metadata = get_relevant_content_for_agent(
                agent_type="robustness_auditor", 
                repo_url=repo_url,
                token=github_token
            )
            
            initial_response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system", 
                        "content": (
                            "You are a senior Cybersecurity & AI Robustness Auditor. "
                            "Scan the provided API routes and model inference logic for Article 15 compliance (Accuracy, Robustness, Cybersecurity). "
                            "MANDATORY CHECKS: "
                            "1. Look for 'naked' endpoints (missing input validation/Pydantic models). "
                            "2. Check for missing error handling (try/except blocks) around inference calls. "
                            "3. Identify risks of data poisoning or model feedback loops. "
                            "Output the violating code snippets and cite specific risks."
                        )
                    },
                    {"role": "user", "content": f"Analyze this codebase for robustness: {llm_input}"}
                ]
            )
            audit_text = initial_response.choices[0].message.content

            emb_resp = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=audit_text
            )
            query_vector = emb_resp.data[0].embedding
            
            matches = self.supabase_client.rpc("match_documents", {
                "query_embedding": query_vector,
                "match_threshold": 0.40,
                "match_count": 3
            }).execute()

            rules = [match['chunk_content'] for match in matches.data]
            
            final_response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system", 
                        "content": (
                            "You are a senior AI Compliance Engineer. Based on the matched EU AI Act rules (specifically Article 15), "
                            "determine if the code violates requirements for 'Resilience to errors and faults'. "
                            "TASK: "
                            "1. Link technical gaps to Article 15(4) (Resilience to third-party exploits). "
                            "2. Provide REMEDIATION CODE snippets (e.g., adding a try/except block or Pydantic validator). "
                            "3. Summarize findings for the Annex IV Technical File."
                        )
                    },
                    {"role": "user", "content": f"LEGAL RULES: {rules}\n\nTECHNICAL ANALYSIS: {audit_text}\n\nREPO METADATA: {repo_metadata}"}
                ]
            )
            
            final_report = final_response.choices[0].message.content
            print("\n--- FINAL ROBUSTNESS REPORT ---")
            print(final_report[:500] + "...")
            
            return final_report

        except Exception as e:
            print(f"An error occurred in Robustness Auditor: {e}")
            return f"Error: {e}"
        

def test_robustness_audit():
    # 1. Verification: Check if keys exist
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY is missing from .env")
        return
    if not os.getenv("SUPABASE_URL"):
        print("❌ Error: SUPABASE_URL is missing from .env")
        return

    print("✅ Environment keys loaded.")

    # 2. Initialize the Auditor
    try:
        auditor = TechnicalRobustnessAuditor()
        print("✅ Auditor initialized.")
    except Exception as e:
        print(f"❌ Failed to init auditor: {e}")
        return

    # 3. Define a Test Repo
    # Use a repo that is likely to have 'robustness' issues (e.g. simple Flask/FastAPI apps)
    # This one is a simple example, or use your own
    test_repo = "https://github.com/fastapi/fastapi" 
    
    # Get token from env or hardcode for testing
    token = os.getenv("GITHUB_TOKEN")

    print(f"🚀 Starting Audit on {test_repo}...")
    
    # 4. Run the Audit
    # Since your run_audit is synchronous (no 'async def'), we call it directly
    report = auditor.run_audit(test_repo, token)

    # 5. Output Result
    print("\n" + "="*40)
    print("TEST RESULT:")
    print("="*40)
    print(report)

if __name__ == "__main__":
    test_robustness_audit()