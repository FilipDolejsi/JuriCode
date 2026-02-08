import os
import datetime
import supabase
import dotenv
from typing import List
from io import BytesIO
from fastapi import FastAPI, Response,HTTPException
from pydantic import BaseModel
from openai import OpenAI
from agents.data_governace_auditor import DataEthicsAuditor
from agents.risk_classifier import RiskClassifier
from agents.technical_robustness_auditor import TechnicalRobustnessAuditor
from agents.technical_document_synthesizer import TechnicalDocumentSynthesizer
from graph import get_graph_metadata
from fastapi.responses import StreamingResponse
import json
import asyncio
from urllib.parse import urlparse 
from github import Github


dotenv.load_dotenv()

app = FastAPI()

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

supabase_client = supabase.create_client(
    os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY")
)
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class Input(BaseModel):
    url: str = None

class MultiRepoRequest(BaseModel):
    urls: List[str]
    
class NodeRequest(BaseModel):
    repo_url: str
    node_id: str 


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


@app.post("/node-owner")
def get_node_owner(request: NodeRequest):
    """
    Forensic Deep-Dive: Resolves a specific Knowledge Cluster node 
    to its human Stakeholder and their contact details.
    """
    github_token = os.getenv("GITHUB_TOKEN")
    
    metadata = get_graph_metadata(request.url, github_token)
    owner_info = next((item for item in metadata if item["file_path"] in request.node_id), None)
    
    if not owner_info:
        raise HTTPException(
            status_code=404, 
            detail="Stakeholder data for this node could not be resolved."
        )

    reports = supabase_client.table("agent_reports").select("*").eq("repo_url", request.repo_url).execute().data
    relevant_violations = [
        r["agent_type"] for r in reports 
        if owner_info["file_path"] in r["report_content"]
    ]

    return {
        "file": owner_info["file_path"],
        "responsible_person": owner_info["stakeholder"],
        "email": owner_info["email"],
        "last_commit": owner_info["last_modified"],
        "commit_message": owner_info["commit_msg"],
        "active_violations": relevant_violations,
        "github_link": owner_info["github_link"]
    }

@app.get("/audit-stream")
async def audit_stream_endpoint(url: str):
    """
    This endpoint streams updates to the frontend in real-time.
    """
    def event_generator():
        yield f"data: {json.dumps({'step': 1, 'message': 'Activating Risk Classifier Agent...'})}\n\n"
        risk_report = run_risk_agent(url) # Your existing function
        yield f"data: {json.dumps({'step': 1, 'status': 'done', 'preview': 'Risk Analysis Complete'})}\n\n"
        
        yield f"data: {json.dumps({'step': 2, 'message': 'Scanning for PII & Bias (Article 10)...'})}\n\n"
        data_report = run_data_agent(url)
        yield f"data: {json.dumps({'step': 2, 'status': 'done', 'preview': 'Data Governance Audit Complete'})}\n\n"

        yield f"data: {json.dumps({'step': 3, 'message': 'Testing API Robustness (Article 15)...'})}\n\n"
        robust_report = run_robustness_agent(url)
        yield f"data: {json.dumps({'step': 3, 'status': 'done', 'preview': 'Robustness Check Complete'})}\n\n"

        yield f"data: {json.dumps({'step': 4, 'message': 'Compiling Annex IV Technical File...'})}\n\n"
        final_doc = run_synthesizer_agent(url)
        
        yield f"data: {json.dumps({'step': 5, 'status': 'complete', 'report': final_doc})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/graph-stream")
async def graph_stream(request: MultiRepoRequest):
    """
    Streams progress of knowledge graph generation to the frontend.
    """
    async def event_generator():
        all_nodes = []
        all_edges = []
        seen_ids = set()
        github_token = os.getenv("GITHUB_TOKEN")
        total_repos = len(request.urls)

        for i, url in enumerate(request.urls):
            repo_name = url.split("/")[-1]
            
            progress_msg = f"Scanning repository {i+1}/{total_repos}: {repo_name}..."
            yield f"data: {json.dumps({'type': 'progress', 'message': progress_msg, 'percent': int((i / total_repos) * 100)})}\n\n"

            try:
                metadata = await asyncio.to_thread(get_graph_metadata, url, github_token)
            except Exception as e:
                error_msg = f"Error scanning {repo_name}: {str(e)}"
                yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"
                continue

            repo_id = repo_name
            if repo_id not in seen_ids:
                all_nodes.append({"id": repo_id, "label": repo_id, "type": "Repository"})
                seen_ids.add(repo_id)

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

            yield f"data: {json.dumps({'type': 'progress', 'message': f'Processed {repo_name}', 'percent': int(((i + 1) / total_repos) * 100)})}\n\n"

        final_payload = {"nodes": all_nodes, "edges": all_edges}
        yield f"data: {json.dumps({'type': 'complete', 'data': final_payload})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.post("/dashboard-stats")
def get_dashboard_stats(request: MultiRepoRequest):
    """
    Fast aggregation for the Dashboard 'Organization Overview'.
    """
    github_token = os.getenv("GITHUB_TOKEN")
    g = Github(github_token)
    
    unique_contributors = set()
    risky_repos = []
    repo_statuses = []
    
    for url in request.urls:
        try:
            path_parts = urlparse(url).path.strip("/").split("/")
            if len(path_parts) >= 2:
                repo_name = "/".join(path_parts[:2])
                if repo_name.endswith(".git"): repo_name = repo_name[:-4]
                
                repo = g.get_repo(repo_name)
                for contributor in repo.get_contributors().get_page(0):
                    unique_contributors.add(contributor.login)
        except Exception as e:
            print(f"Could not fetch contributors for {url}: {e}")

        try:
            response = supabase_client.table("agent_reports")\
                .select("report_content")\
                .eq("repo_url", url)\
                .eq("agent_type", "risk_classifier")\
                .order("created_at", desc=True)\
                .limit(1)\
                .execute()
            
            status = "LOW_RISK"
            category = "General Purpose"
            
            if response.data:
                content = str(response.data[0]['report_content'])
                
                if "Prohibited" in content or "Unacceptable Risk" in content:
                    status = "PROHIBITED"
                    category = "Article 5 Violation"
                
                elif "High Risk" in content:
                    status = "HIGH_RISK"
                    if "Biometric" in content:
                        category = "Biometrics and Biometric Identification"
                    elif "Infrastructure" in content:
                        category = "Critical Infrastructure"
                    elif "Education" in content:
                        category = "Education and Vocational Training"
                    elif "Employment" in content:
                        category = "Employment and Workers Management"
                    elif "Credit" in content:
                        category = "Essential Private and Public Services"
                    elif "Police" in content or "Law Enforcement" in content:
                        category = "Law Enforcement"
                    elif "Border" in content:
                        category = "Migration, Asylum and Border Control"
                    elif "Justice" in content:
                        category = "Administration of Justice and Democratic Processes"
                    else: category = "Annex III"
                    risky_repos.append(url)

            repo_statuses.append({
                "url": url,
                "status": status,
                "category": category
            })
        except Exception as e:
            print(f"Error checking risks for {url}: {e}")

    return {
        "contributor_count": len(unique_contributors),
        "risk_count": len(risky_repos),
        "active_repos": len(request.urls),
        "risky_repo_urls": risky_repos,
        "repo_details": repo_statuses,
    }


def run_explanatory_agent(url):

    try:
        reports = supabase_client.table("agent_reports")\
            .select("*")\
            .eq("repo_url", url)\
            .in_("agent_type", ["risk_classifier", "data_ethics_auditor", "technical_robustness_auditor"])\
            .execute().data
        
        risk_content = next((r["report_content"] for r in reports if r["agent_type"] == "risk_classifier"), "No Data")
        data_content = next((r["report_content"] for r in reports if r["agent_type"] == "data_ethics_auditor"), "No Data")
        robust_content = next((r["report_content"] for r in reports if r["agent_type"] == "technical_robustness_auditor"), "No Data")
        
    except Exception as e:
        print(f"Error fetching sub-reports: {e}")
        return "Error: Could not retrieve agent reports for analysis."

    prompt = (
        "You are the AI Chief of Technical Staff. Your goal is to provide a 'Deep Dive' explanatory analysis "
        "of the target software repository based on findings from three specialized auditing agents.\n\n"
        
        "**INPUT DATA:**\n"
        f"1. RISK AGENT FINDINGS: {risk_content}\n"
        f"2. DATA GOVERNANCE FINDINGS: {data_content}\n"
        f"3. ROBUSTNESS FINDINGS: {robust_content}\n\n"
        
        "**TASK:**\n"
        "Synthesize these findings into a narrative Technical Reasoning Report. "
        "Do NOT use strict legal formatting (Annex IV). Instead, focus on engineering causality.\n\n"
        
        "**STRUCTURE:**\n"
        "Write in paragraph based, where for each agent below it describes what part of code (if access or possible) violates such AI EU acts (given the agents) and recommend a improvement."
        "**The Risk Chain:** Explain specifically *why* the system was flagged. Connect the dots between code features (e.g., 'Face Recognition lib') and the risk classification.\n"
        "**Vulnerability Correlation:** Analyze if the technical weaknesses (found by Robustness Agent) worsen the data risks (found by Data Agent). (e.g., 'The lack of input validation in API endpoints makes the PII data susceptible to injection attacks.')\n"
        "**Architectural Recommendations:** Provide high-level advice on fixing the *root cause*, not just patching bugs."
    )

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a senior technical architect explaining complex risks to an engineering team."},
                {"role": "user", "content": prompt}
            ]
        )
        report_text = response.choices[0].message.content
        
        save_report(repo_url=url, agent_type="explanatory_analyst", report_content=report_text)
        
        return report_text

    except Exception as e:
        print(f"Error generating explanatory report: {e}")
        return f"Error generating report: {str(e)}"


@app.post("/explanatory-report")
def get_explanatory_report(item: Input):
    """
    Returns a narrative 'Reasoning Report' focusing on architectural analysis
    instead of legal documentation.
    """
    return run_explanatory_agent(item.url)
