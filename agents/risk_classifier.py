import os
import sys
import dotenv
from openai import OpenAI
import supabase
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from fetch_codebase import get_relevant_content_for_agent 

dotenv.load_dotenv()

class RiskClassifier:
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
                agent_type="risk_classifier",
                repo_url=repo_url,
                token=self.github_token
            )

            initial_response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system", 
                        "content": (
                            "You are an EU AI Act Compliance Officer. Scan the provided project documentation "
                            "to identify its 'Intended Purpose' and 'Use Case'. "
                            "Look for high-risk keywords defined in Annex III: Biometrics, Critical Infrastructure, "
                            "Education, Employment, Credit Scoring, Law Enforcement, Migration, Justice. "
                            "Output a concise summary of what the system does and which category it might belong to."
                        )
                    },
                    {"role": "user", "content": f"Analyze this codebase metadata: {llm_input}"}
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
                            "You are a Chief Risk Officer. Based on the matched EU AI Act rules (Annex III / Article 5) and the system analysis, "
                            "provide a final Legal Classification. "
                            "TASK: "
                            "1. State clearly: 'High Risk', 'Prohibited', or 'Low Risk'. "
                            "2. Cite the specific legal article or annex point (e.g., 'Annex III, Point 4(a)'). "
                            "3. Explain the reasoning based on the system's intended purpose. "
                            "4. Mention the 'Risk Owner' (Developer Name) from the metadata in your summary."
                        )
                    },
                    {"role": "user", "content": f"LEGAL RULES: {rules}\n\nSYSTEM ANALYSIS: {audit_text}\n\nREPO METADATA: {repo_metadata}"}
                ]
            )

            return final_response.choices[0].message.content

        except Exception as e:
            print(f"An error occurred: {e}")
            return f"Error: {e}"