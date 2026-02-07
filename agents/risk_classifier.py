import sys
import os
import json
import asyncio
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from fetch_codebase import *
from openai import AsyncOpenAI

class RiskClassifier:
    def __init__(self, supabase, openai_key, fetch_relevant_codebase_data: callable, repo_url: str):
        self.supabase = supabase
        self.openai = AsyncOpenAI(api_key=openai_key)
        self.fetch_relevant_codebase_data = fetch_relevant_codebase_data
        self.repo_url = repo_url
        self.token = ""

    async def detection(self):
        """
        Scans the codebase for 'Intent' and 'Stakeholders'.
        """
        print(f"--- 1. DETECTION ---")
        llm_context, stakeholder_metadata = self.fetch_relevant_codebase_data(
            "risk_classifier",
            self.repo_url,
            self.token,
        )

        prompt = f"""
        Analyze this codebase summary. 
        Does it appear to be a 'High Risk' AI system under the EU AI Act? 
        (e.g. Biometrics, Critical Infrastructure, Education, Employment, Credit, Law Enforcement, Migration, Justice).
        
        CODE SUMMARY:
        {llm_context[:2000]}
        
        Return JSON: {{ "is_suspected_high_risk": bool, "category": "Biometrics/Critical Infrastructure/...etc.", "reason": "..." }}
        """

        llm_response = await self.openai.chat.completions.create(
            model = "gpt-4o-mini",
            messages = [{"role": "user", "content": prompt}],
            response_format = {"type": "json_object"}
        )

        prediction = json.loads(llm_response.choices[0].message.content)

        return {
            "llm_context": llm_context,
            "stakeholder_metadata": stakeholder_metadata,
            "prediction": prediction,
        }


    async def similarity(self, data):
        """
        Retreives specific laws that relate to the code
        """
        prediction = data['prediction']
        print(f"--- 2. SIMILARITY: Smart Search for {prediction['category']} ---")
        if not prediction['is_suspected_high_risk']:
            return "General Purpose AI transparency rules (Article 50)."
        
        query_prompt = f"Generate a search query to find the specific EU AI Act Annex III paragraph for '{prediction['category']}'."
        query_response = await self.openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": query_prompt}]
        )

        search_query = query_response.choices[0].message.content
        embedding = await self.openai.embeddings.create(
            model="text-embedding-3-small",
            input=search_query
        )

        supabase_response = self.supabase.rpc("match_documents", {
            "query_embedding": embedding.data[0].embedding,
            "match_threshold": 0.75,
            "match_count": 2,
        }).execute()

        laws = "\n".join([item['content'] for item in supabase_response.data])
        return laws

    async def forensic_audit(self, detection_data, law_text):

        prompt = f"""
        You are a Chief Risk Officer.
        
        EVIDENCE (CODE):
        {detection_data['text_context'][:4000]}
        
        LAW (EU AI ACT):
        {law_text}
        
        TASK:
        Compare the code against the law. 
        1. Does this code DEFINITELY fall under the High Risk classification?
        2. Identify the specific file or feature that triggers this.
        
        Return JSON: 
        {{ 
            "final_verdict": "High Risk" | "Low Risk", 
            "confidence_score": 0-100, 
            "violating_feature": "The resume_parser.py module...",
            "citation": "Annex III Point 4(a)" 
        }}
        """

        response = await self.openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )

        return json.loads(response.choices[0].message.content)


    async def synthesis(self, audit_result, detection_data):
        stakeholder_metadata = detection_data['stakeholder_metadata']
        risk_owner = stakeholder_metadata[0] if stakeholder_metadata else {"author": "Unknown", "email": "Unknown"}

        final_report = {
            "status": "BLOCKED" if audit_result['final_verdict'] == "High Risk" else "APPROVED",
            "risk_score": audit_result['confidence_score'],
            "summary": f"Detected {audit_result['final_verdict']} system ({audit_result['citation']}).",
            
            # The OpenAI "Chief of Staff" Feature:
            "stakeholder_map": {
                "responsible_dev": risk_owner['author'],
                "email": risk_owner['email'],
                "last_active": risk_owner['timestamp'],
                "team": "Engineering" # You could infer this from email domain
            },
            
            "voice_briefing": f"Chief, I've blocked a deployment from {risk_owner['author']}. It contains {audit_result['violating_feature']} which violates {audit_result['citation']}."
        }
        
        return final_report
    

    async def run(self):
        data = await self.detection()
        law = await self.similarity(data)
        verdict = await self.forensic_audit(data, law)
        report = await self.synthesis(verdict, data)
        return report


from supabase import create_client

async def main():
    # 2. Initialize Supabase
    supabase = create_client("", "")

    # 3. Initialize the Agent
    # Note: Ensure your __init__ accepts the OpenAI key for the LLM steps
    agent = RiskClassifier(
        supabase=supabase,
        openai_key="",
        fetch_relevant_codebase_data=get_relevant_content_for_agent,
        repo_url="https://github.com/FilipDolejsi/Pneumonia-Classifier"
    )

    # 4. Run the full Agentic Workflow
    # We pass the repo_url and github_token to the run method
    report = await agent.run()

    # 5. Output the Chief of Staff Report
    import json
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    asyncio.run(main())