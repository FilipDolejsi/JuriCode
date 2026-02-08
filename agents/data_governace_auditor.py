import os
import sys
import dotenv
from openai import OpenAI
import supabase
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from fetch_codebase import get_relevant_content_for_agent 

dotenv.load_dotenv()

class DataEthicsAuditor:
    def __init__(self):
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.supabase_client = supabase.create_client(
            os.getenv("SUPABASE_URL"), 
            os.getenv("SUPABASE_KEY")
        )
        
    def run_audit(self, repo_url):
        try:
            llm_input, repo_metadata = get_relevant_content_for_agent(
                agent_type="data_auditor",
                repo_url=repo_url,
                token=self.github_token
            )
            initial_response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system", 
                        "content": (
                            "You are a senior Data Ethics Auditor. Scan database schemas and processing scripts for Article 10 compliance. "
                            "MANDATORY: If you find protected attributes (e.g., gender, race) without bias-mitigation logic, output the violating code snippet. "
                            "You MUST cite the specific sub-paragraph of Article 10 for every claim (e.g., Article 10(2)(f) for bias examination)."
                        )
                    },
                    {"role": "user", "content": f"Analyze this codebase: {llm_input}"}
                ]
            )
            audit_text = initial_response.choices[0].message.content
            print("--- EU AI ACT ANALYSIS ---")
            print(audit_text)

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
                            "You are a senior Data Ethics Auditor. Based on the following matched documents from the EU AI Act, "
                            "determine if the code snippets violate Article 10. For each violation, cite the specific sub-paragraph. "
                            "If compliant, state 'Compliant with Article 10'. Cite the rules used and create a summary of findings per Annex IV."
                        )
                    },
                    {"role": "user", "content": f"rules: {rules}, analysis: {audit_text} , repo metadata: {repo_metadata}"}
                ]
            )
            
            print("\n--- FINAL COMPLIANCE ASSESSMENT ---")
            print(final_response.choices[0].message.content)

        except Exception as e:
            print(f"An error occurred: {e}")
