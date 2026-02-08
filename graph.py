import os
import dotenv
from github import Github

dotenv.load_dotenv()
def get_graph_metadata(repo_url, token):
    """
    Specifically designed for the 'AI Chief of Staff' Graph.
    Maps every unique file to its stakeholder and latest version.
    """
    
    g = Github(token)
    repo_name = "/".join(repo_url.rstrip("/").split("/")[-2:])
    repo = g.get_repo(repo_name)
    
    graph_metadata = []
    contents = repo.get_contents("")
    
    while contents:
        file_content = contents.pop(0)
        if file_content.type == "dir":
            contents.extend(repo.get_contents(file_content.path))
        else:
            if file_content.path.endswith(('.py', '.js', '.sql', '.md', '.json')):
                commits = repo.get_commits(path=file_content.path)
                if commits.totalCount > 0:
                    last_commit = commits[0]
                    
                    graph_metadata.append({
                        "id": file_content.sha, # Unique ID for versioned memory [cite: 126]
                        "file_path": file_content.path,
                        "stakeholder": last_commit.commit.author.name,
                        "email": last_commit.commit.author.email,
                        "last_modified": last_commit.commit.author.date.isoformat(),
                        "commit_msg": last_commit.commit.message,
                        "github_link": file_content.html_url
                    })
                    
    return graph_metadata


def run_silo_critic(self, graph_metadata):
    """
    An agentic LLM approach to knowledge deconfliction and silo management.
    """
    prompt = (
        "You are the Superhuman AI Chief of Staff. Analyze this organizational metadata "
        "to identify 'Knowledge Silos' (Single Points of Failure). \n\n"
        f"METADATA: {graph_metadata}\n\n"
        "TASK:\n"
        "1. Identify files with only one stakeholder that are 'High Impact' (e.g., core logic).\n"
        "2. Evaluate the commit messages: Are they descriptive or 'blind'?\n"
        "3. RECOMMENDATION: Who else in the stakeholder map should be briefed to ensure "
        "this knowledge isn't lost? Provide a 100x targeted action plan."
    )
    
    response = self.openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": "You are the company brain."},
                  {"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content