import os
import sys
import dotenv
from openai import OpenAI
import supabase
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

dotenv.load_dotenv()

class TechnicalDocumentSynthesizer:
    def __init__(self):
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.supabase_client = supabase.create_client(
            os.getenv("SUPABASE_URL"), 
            os.getenv("SUPABASE_KEY")
        )
        
    def generate_report(self, repo_url: str, risk_assessment: str, data_audit: str, robustness_audit: str):
        try:
            emb_resp = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input="EU AI Act Annex IV Technical Documentation mandatory fields and structure"
            )
            query_vector = emb_resp.data[0].embedding
            
            matches = self.supabase_client.rpc("match_documents", {
                "query_embedding": query_vector,
                "match_threshold": 0.40,
                "match_count": 5
            }).execute()

            annex_iv_template = "\n".join([match['chunk_content'] for match in matches.data])
            
            final_response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system", 
                        "content": (
                            "You are a Senior EU AI Act Compliance Officer. Your task is to compile a "
                            "Technical Documentation File (Annex IV) based on forensic audit reports.\n\n"
                            "STRICT FORMATTING RULES:\n"
                            "1. The report MUST be written in a formal, legal-technical style.\n"
                            "2. It MUST be structured into these three specific sections:\n"
                            "   - Section A: System Classification & Risk (based on Risk Agent)\n"
                            "   - Section B: Data Governance & Bias Control (based on Data Auditor)\n"
                            "   - Section C: Technical Robustness & Cybersecurity (based on Robustness Auditor)\n"
                            "3. For every claim, cite the specific Agent Findings provided in the input.\n"
                            "4. Use the retrieved 'Annex IV Requirements' to ensure the language complies with the law."
                            "5. The header of the final file MUST be 'Annex_IV_Technical_Documentation_{repo_name}' where repo_name is derived from the URL."
                        )
                    },
                    {
                        "role": "user", 
                        "content": (
                            f"TARGET REPO: {repo_url}\n\n"
                            f"--- ANNEX IV LEGAL REQUIREMENTS ---\n{annex_iv_template}\n\n"
                            f"--- INPUT: RISK AGENT REPORT ---\n{risk_assessment}\n\n"
                            f"--- INPUT: DATA GOVERNANCE REPORT ---\n{data_audit}\n\n"
                            f"--- INPUT: ROBUSTNESS REPORT ---\n{robustness_audit}\n\n"
                            "TASK: Generate the final Annex IV Technical Report."
                        )
                    }
                ]
            )
            
            return final_response.choices[0].message.content

        except Exception as e:
            print(f"An error occurred in Synthesis: {e}")
            return f"Error compiling report: {e}"
