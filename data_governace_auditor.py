import supabase
from github import Github
import os
import dotenv   

dotenv.load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

supabase_client = supabase.create_client(SUPABASE_URL, SUPABASE_KEY)
github_client = Github(GITHUB_TOKEN)


