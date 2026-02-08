import os
import datetime
import supabase
import dotenv
from typing import List
from io import BytesIO
from fastapi import FastAPI, Response
from pydantic import BaseModel
from openai import OpenAI
from agents.data_governace_auditor import DataEthicsAuditor
from agents.risk_classifier import RiskClassifier
from agents.technical_robustness_auditor import TechnicalRobustnessAuditor
from agents.technical_document_synthesizer import TechnicalDocumentSynthesizer
from graph import get_graph_metadata

dotenv.load_dotenv()

app = FastAPI()

supabase_client = supabase.create_client(
    os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY")
)
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class Input(BaseModel):
    url: str = None

class MultiRepoRequest(BaseModel):
    urls: List[str]

def save_report(repo_url, agent_type, report_content):
    try:
        response = supabase_client.table("agent_reports").select("*").eq("repo_url", repo_url).eq("agent_type", agent_type).execute()
        if response.data:
            supabase_client.table("agent_reports").update({
                "report_content": report_content
            }).eq("repo_url", repo_url).eq("agent_type", agent_type).execute()
        else:
            report_data = {
                "repo_url": repo_url,
                "agent_type": agent_type,
                "report_content": report_content
            }
            supabase_client.table("agent_reports").insert(report_data).execute()
    except Exception as e:
        print(f"Error saving report: {e}")
        raise

def run_risk_agent(url):
    agent = RiskClassifier()
    report = agent.run_audit(url)
    save_report(repo_url=url, agent_type="risk_classifier", report_content=report)
    return report

def run_data_agent(url):
    agent = DataEthicsAuditor()
    report = agent.run_audit(url)
    save_report(repo_url=url, agent_type="data_ethics_auditor", report_content=report)
    return report

def run_robustness_agent(url):
    agent = TechnicalRobustnessAuditor()
    report = agent.run_audit(url)
    save_report(repo_url=url, agent_type="technical_robustness_auditor", report_content=report)
    return report

def run_synthesizer_agent(url):
    agent = TechnicalDocumentSynthesizer()
    filtered_data = supabase_client.table("agent_reports").select("*").eq("repo_url", url).order("created_at", desc=False).execute().data
    if len(filtered_data) < 3:
        raise ValueError("Missing agent reports for synthesis")
    report = agent.generate_report(url, filtered_data[0]["report_content"], filtered_data[1]["report_content"], filtered_data[2]["report_content"])
    save_report(repo_url=url, agent_type="technical_document_synthesizer", report_content=report)
    return report


@app.post("/process")
def process_audit(item: Input):
    run_risk_agent(item.url)
    run_data_agent(item.url)
    run_robustness_agent(item.url)
    final_report_text = run_synthesizer_agent(item.url)
    return final_report_text
    

@app.post("/process-multi-repo-graph")
async def process_multi_repo_graph(request: MultiRepoRequest):
    all_nodes, all_edges, seen_ids = [], [], set()
    github_token = os.getenv("GITHUB_TOKEN")
    for url in request.urls:
        repo_id = url.split("/")[-1]
        if repo_id not in seen_ids:
            all_nodes.append({"id": repo_id, "label": repo_id, "type": "Repository"})
            seen_ids.add(repo_id)
        metadata = get_graph_metadata(url, github_token)
        for entry in metadata:
            stakeholder = entry['stakeholder']
            file_path = f"{repo_id}/{entry['file_path']}"
            if stakeholder not in seen_ids:
                all_nodes.append({
                    "id": stakeholder, "label": stakeholder,
                    "type": "Stakeholder", "email": entry['email']
                })
                seen_ids.add(stakeholder)
            all_nodes.append({
                "id": file_path, "label": entry['file_path'].split('/')[-1],
                "type": "Knowledge_Cluster", "version": entry['id']
            })
            all_edges.append({"from": stakeholder, "to": file_path, "label": "Authored"})
            all_edges.append({"from": file_path, "to": repo_id, "label": "Belongs To"})
    return {"nodes": all_nodes, "edges": all_edges}

@app.post("/recommendations")
async def get_talent_recommendations(request: MultiRepoRequest):
    github_token = os.getenv("GITHUB_TOKEN")
    aggregated_metadata = []
    for url in request.urls:
        meta = get_graph_metadata(url, github_token)
        for m in meta[:15]:
            aggregated_metadata.append({
                "repo": url.split('/')[-1],
                "file": m['file_path'],
                "user": m['stakeholder']
            })
    prompt = (
        "You are a AI Chief of Staff. Analyze this metadata to identify knowledge silos and recommend talent moves.\n\n"
        f"METADATA: {aggregated_metadata}\n\n"
        "Identify silos and top talent. Suggest specific cross-repo developer moves."
    )
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are the brain of the company."},
            {"role": "user", "content": prompt}
        ]
    )
    return {
        "summary": "Strategic Personnel Recommendations",
        "recommendations": response.choices[0].message.content,
        "total_repos_analyzed": len(request.urls)
    }