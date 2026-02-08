from github import Github


import base64
from github import Github
from datetime import datetime

def fetch_file_with_metadata(repo_obj, file_path):
    """
    Fetches a specific file's content AND its 'Chief of Staff' metadata.
    Returns None if file doesn't exist.
    """
    try:
        # 1. Get Content
        file_content = repo_obj.get_contents(file_path)
        decoded_str = base64.b64decode(file_content.content).decode("utf-8")
        
        # 2. Get Metadata (Git Blame / History)
        # We take the most recent commit for this file to know who touched it last.
        commits = repo_obj.get_commits(path=file_path)
        last_commit = commits[0]
        
        return {
            "file_name": file_path,
            "content": decoded_str,
            "timestamp": last_commit.commit.author.date.isoformat(), # <--- The Timestamp you asked for
            "author": last_commit.commit.author.name,               # <--- For the 'Chief of Staff' Graph
            "email": last_commit.commit.author.email,
            "link": last_commit.html_url
        }
    except Exception:
        return None

def get_relevant_content_for_agent(agent_type: str, repo_url: str, token: str):
    """
    Orchestrates fetching the RIGHT files for the RIGHT agent.
    Returns:
      1. combined_text_context: The string variable for the LLM.
      2. stakeholder_metadata: The list of people involved (for the Graph).
    """
    g = Github(token)
    repo_name = "/".join(repo_url.rstrip("/").split("/")[-2:])
    repo = g.get_repo(repo_name)
    
    files_to_fetch = []

    # --- LOGIC FROM REGUBOTS.PDF ---
    
    # 1. RISK CLASSIFIER AGENT (The Gatekeeper)
    # Source: ReguBots.pdf Step 1 [cite: 1024]
    # "Scans README.md, metadata... for keywords like Hiring, Credit"
    if agent_type == "risk_classifier":
        files_to_fetch = ["README.md", "package.json", "requirements.txt", "pyproject.toml"]

    # 2. DATA GOVERNANCE AUDITOR (The Intelligence Officer)
    # Source: ReguBots.pdf Step 2 [cite: 1029]
    # "Scans sql, csv and data-processing scripts... for sensitive headers"
    elif agent_type == "data_auditor":
        # We need to scan the tree to find these files, as we don't know their names
        contents = repo.get_contents("")
        while contents:
            file_content = contents.pop(0)
            if file_content.type == "dir":
                contents.extend(repo.get_contents(file_content.path))
            else:
                # Target .sql, .csv or python scripts that look like preprocessing/data handlers
                lower_path = file_content.path.lower()
                if lower_path.endswith((".sql", ".csv")) or ("preprocess" in lower_path):
                    files_to_fetch.append(file_content.path)
        # Limit to first 5 to prevent overload in hackathon
        files_to_fetch = files_to_fetch[:5]

    # 3. TECHNICAL ROBUSTNESS AUDITOR (The Sentinel)
    # Source: ReguBots.pdf Step 3 [cite: 1032]
    # "Scans FastAPI routes and model inference logic for try/except blocks"
    elif agent_type == "robustness_auditor":
        contents = repo.get_contents("")
        while contents:
            file_content = contents.pop(0)
            if file_content.type == "dir":
                contents.extend(repo.get_contents(file_content.path))
            else:
                # Look for API routes or inference logic
                if ("main" in file_content.path or "app" in file_content.path or "index" in file_content.path) and not file_content.path.lower().endswith(".ipynb"):
                    files_to_fetch.append(file_content.path)

    elif agent_type == "synthesizer":
        files_to_fetch = ["README.md", "package.json", "requirements.txt", "pyproject.toml"]
        contents = repo.get_contents("")
        while contents:
            file_content = contents.pop(0)
            if file_content.type == "dir":
                contents.extend(repo.get_contents(file_content.path))
            else:
                # Look for "admin", "config", or specific logic files
                lower_path = file_content.path.lower()
                if "admin" in lower_path or "config" in lower_path or "utils" in lower_path:
                    files_to_fetch.append(file_content.path)

    # --- EXECUTE FETCH ---
    combined_text_context = ""
    stakeholder_metadata = []

    for file_path in files_to_fetch:
        data = fetch_file_with_metadata(repo, file_path)
        if data:
            # 1. Build the Variable for the LLM
            if data['content'] and data['content'].strip():
                combined_text_context += f"\n--- FILE: {data['file_name']} ---\n{data['content']}\n"
            else:
                combined_text_context += f"\n--- FILE: {data['file_name']} ---\n[NO CONTENT] there wasnt any relevant data to extract here.\n"
            
            # 2. Collect Metadata for 'Chief of Staff' Graph
            stakeholder_metadata.append({
                "file": data['file_name'],
                "author": data['author'],
                "timestamp": data['timestamp'], # <--- The timestamp you requested
                "link": data['link']
            })

    return combined_text_context, stakeholder_metadata