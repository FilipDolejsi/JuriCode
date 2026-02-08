from fastapi import FastAPI, Response
from fastapi.responses import StreamingResponse
from io import BytesIO
from fpdf import FPDF
import os
from agents.data_governace_auditor import DataEthicsAuditor
import datetime
app = FastAPI()

# --- Agent Wrappers ---
def save_report(self, repo_url, agent_type, report_content):
    try:
        # Prepare the data object matching your schema
        report_data = {
            "repo_url": repo_url,
            "agent_type": agent_type,
            "report_content": report_content,
            "timestamp": datetime.utcnow().isoformat()}
        response = self.supabase_client.table("agent_reports").insert(report_data).execute()
    except Exception as e:
        print(f"Error saving report to Supabase: {e}")
        raise
    
def run_risk_agent(url, auditor):
    report = auditor.run_risk_classifier(url) 
    auditor.save_report(url, "risk_classifier", report)
    return report

def run_data_agent(url, auditor):
    report = auditor.run_audit(url)
    auditor.save_report(url, "data_auditor", report)
    return report

def run_robustness_agent(url, auditor):
    # Specialized logic for technical robustness
    report = auditor.run_robustness_audit(url)
    auditor.save_report(url, "robustness_auditor", report)
    return report

def run_synthesizer_agent(url, auditor):
    # Fetches all previous reports from Supabase to create the final summary
    final_report = auditor.generate_final_summary(url)
    auditor.save_report(url, "synthesizer", final_report)
    return final_report

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
    auditor = DataEthicsAuditor()
    
    # 1. Execute agents in sequence
    run_risk_agent(item.url, auditor)
    run_data_agent(item.url, auditor)
    run_robustness_agent(item.url, auditor)
    
    # 2. Final Synthesis
    final_report_text = run_synthesizer_agent(item.url, auditor)
    
    # 3. Generate PDF and stream to user
    pdf_buffer = generate_pdf(final_report_text)
    return StreamingResponse(
        pdf_buffer, 
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=audit_{item.url.split('/')[-1]}.pdf"}
    )