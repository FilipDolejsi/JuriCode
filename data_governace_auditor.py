import supabase
from google import genai
from google.genai import types
import dotenv   
import os 
from github import Github

client = genai.Client()
dotenv.load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

supabase_client = supabase.create_client(SUPABASE_URL, SUPABASE_KEY)
github_client = Github(GITHUB_TOKEN)


response = client.models.generate_content(
    model="gemini-3-flash-preview",
    config=types.GenerateContentConfig(
        system_instruction=""""You are an expert in EU AI Act legal classification. Analyze the repository's metadata and README. Determine if the system is 'High-Risk' per Annex III. MANDATORY: You must cite the specific Annex III category (e.g., Annex III, Point 4 for Education). If the README mentions a prohibited use, cite Article 5 and flag it immediately"""
    ,contents=""
))
print(response.text)