import os
from openai import OpenAI
from supabase import create_client
from fetch_codebase import get_relevant_content_for_agent 

# Assuming dotenv is loaded in main or via environment variables
# from dotenv import load_dotenv
# load_dotenv()

class TechnicalRobustnessAuditor:
    def __init__(self, supabase_client, openai_api_key):
        # Initialize clients
        self.openai_client = OpenAI(api_key=openai_api_key)
        self.supabase_client = supabase_client
        
    def run_audit(self, repo_url, github_token):
        try:
            print(f"--- STARTING ROBUSTNESS AUDIT FOR {repo_url} ---")
            
            # 1. FETCH RELEVANT CODE (FastAPI routes, Inference logic)
            # This calls the logic we wrote earlier to get main.py, app.py, etc.
            llm_input, repo_metadata = get_relevant_content_for_agent(
                agent_type="robustness_auditor", 
                repo_url=repo_url,
                token=github_token
            )
            
            # 2. DETECTION & INITIAL AUDIT (The "Red Team" Scan)
            # We ask the LLM to act as a penetration tester/auditor
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
            print("--- INITIAL VULNERABILITY SCAN ---")
            print(audit_text[:500] + "...") # Print preview

            # 3. SIMILARITY CHECK (Retrieving Article 15 Rules)
            # Embed the findings to find the exact legal requirements
            emb_resp = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=audit_text
            )
            query_vector = emb_resp.data[0].embedding
            
            # Query Supabase for Article 15 context
            matches = self.supabase_client.rpc("match_documents", {
                "query_embedding": query_vector,
                "match_threshold": 0.40,
                "match_count": 3
            }).execute()

            rules = [match['content'] for match in matches.data] # Assuming 'content' column
            
            # 4. SYNTHESIS & REMEDIATION (The "Blue Team" Fix)
            # Compare findings against the law and generate Fixes
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