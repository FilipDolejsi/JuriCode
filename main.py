from fastapi import FastAPI, Response
from fastapi.responses import StreamingResponse
from io import BytesIO
from fpdf import FPDF
import os
from agents.data_governace_auditor import DataEthicsAuditor
from agents.risk_classifier import RiskClassifier
from agents.technical_robustness_auditor import TechnicalRobustnessAuditor
from agents.technical_document_synthesizer import TechnicalDocumentSynthesizer
import datetime
from pydantic import BaseModel
import supabase
app = FastAPI()
supabase_client = supabase.create_client(
    os.getenv("SUPABASE_URL"),os.getenv("SUPABASE_KEY")
)

class Input(BaseModel):
    url: str =None
# --- Agent Wrappers ---
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
                "report_content": report_content        }
            response = supabase_client.table("agent_reports").insert(report_data).execute()
    except Exception as e:
        print(f"Error saving report to Supabase: {e}")
        raise
    
def run_risk_agent(url):
    agent = RiskClassifier()
    report = agent.run_audit(url)
    response = save_report(repo_url=url, agent_type="risk_classifier", report_content=report)
    return report

def run_data_agent(url):
    agent = DataEthicsAuditor()
    report = agent.run_audit(url)
    response = save_report(repo_url=url, agent_type="data_ethics_auditor", report_content=report)
    return report

def run_robustness_agent(url):
    agent = TechnicalRobustnessAuditor()
    report = agent.run_audit(url)
    response = save_report(repo_url=url, agent_type="technical_robustness_auditor", report_content=  report)
    return report

def run_synthesizer_agent(url):
    response =supabase_client.table("agent_reports").select("*").eq("repo_url", url).execute()
    agent = TechnicalDocumentSynthesizer() 
    filtered_data = supabase_client.table("agent_reports").select("*").eq("repo_url", url).order("created_at", desc=False).execute().data
    report = agent.generate_report(url, filtered_data[0]["report_content"], filtered_data[1]["report_content"], filtered_data[2]["report_content"])
    response = save_report(repo_url=url, agent_type="technical_document_synthesizer", report_content=report)
    return report

# --- PDF Generation Utility ---

def generate_pdf(report_text):
    """Converts a string into a formatted PDF byte stream."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", "B", 16)
    pdf.cell(0, 10, "JuriCode Compliance Report", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("helvetica", "", 12)
    # multi_cell handles text wrapping for long reports
    pdf.multi_cell(0, 10, report_text)
    
    # Return as in-memory bytes
    return BytesIO(pdf.output())

# --- Main API Endpoint ---

@app.post("/process")
def process_audit(item: Input): 
    run_risk_agent(item.url)
    run_data_agent(item.url)
    run_robustness_agent(item.url)
    
    final_report_text = run_synthesizer_agent(item.url)
    
    # 3. Generate PDF and stream to user
    pdf_buffer = generate_pdf(final_report_text)
    return StreamingResponse(
        pdf_buffer, 
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=audit_{item.url.split('/')[-1]}.pdf"}
    )