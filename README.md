# JuriCode

**The AI Operating System for Collective Intelligence & EU AI Act Compliance**

![JuriCode Banner](https://img.shields.io/badge/EU_AI_Act-Compliant-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-green) ![License](https://img.shields.io/badge/license-MIT-blue)

---

## 🎯 The Problem

Most AI companies are flying blind. They have thousands of files, dozens of developers, and a looming deadline for EU AI Act compliance. Right now, a founder has no way of knowing if a specific developer in a remote office just committed a "High-Risk" Article 10 violation. 

**Knowledge is siloed. Risks are hidden. Compliance is a manual, expensive post-mortem.**

---

## 💡 The Solution

**JuriCode** isn't just a scanner—it's a **Superhuman AI Chief of Staff**. It transforms messy codebases into living Knowledge Graphs, connecting:
- **The "What"** (the code)
- **The "Who"** (the stakeholder) 
- **The "Why"** (the legal requirement)

---

## 🚀 How It Works

### 1. **Multi-Agent Forensic Pipeline**
Four specialized AI agents conduct deep audits of your repositories:

- **Risk Classifier Agent** 🛡️  
  Scans README.md and metadata for high-risk keywords (Biometrics, Credit Scoring, Law Enforcement). Classifies systems as "High Risk," "Prohibited," or "Low Risk" per EU AI Act Annex III.

- **Data Ethics Auditor** 🔍  
  Examines database schemas and processing scripts for Article 10 compliance. Identifies protected attributes (gender, race) without bias-mitigation logic.

- **Technical Robustness Auditor** ⚡  
  Scans API routes and inference logic for Article 15 compliance. Detects missing input validation, error handling, and cybersecurity vulnerabilities.

- **Technical Document Synthesizer** 📋  
  Compiles findings into an **Annex IV Technical Documentation File**, the legal standard for EU AI Act compliance.

### 2. **The Company Knowledge Graph**
JuriCode builds an **interactive organizational map**:
- Files, stakeholders, and repositories visualized as connected nodes
- "High Risk" files glow red—one click reveals the responsible developer, their email, and the specific violation
- Real-time tracking of who touched what, when, and why

### 3. **Communication Intelligence**
When a crisis is detected, JuriCode doesn't just log it:
- Routes information to the right stakeholders
- Emails the responsible developer with specific remediation code
- CCs leadership with 3-step technical fixes
- Activates "War Room" protocols for critical violations

### 4. **Talent Scouting & Silo Management**
- Identifies your most compliant and robust developers
- Recommends talent moves to break "Knowledge Silos"
- Secures your most dangerous projects with the right expertise

---

## 🌐 Live Demo

**Frontend Platform:** [https://juricode.lovable.app](https://juricode.lovable.app)

---

## 🛠️ Tech Stack

- **Backend:** FastAPI, Python 3.9+
- **AI Models:** OpenAI GPT-4o, text-embedding-3-small
- **Database:** Supabase (PostgreSQL + Vector Storage)
- **GitHub Integration:** PyGithub
- **Document Processing:** PyMuPDF, LangChain Text Splitters
- **Frontend:** Lovable (Full-stack web platform)

---

## 📦 Installation

### Prerequisites
- Python 3.9+
- GitHub Personal Access Token
- OpenAI API Key
- Supabase Account

### Setup

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/juricode.git
cd juricode
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure environment variables**
Create a `.env` file in the root directory:
```env
OPENAI_API_KEY=your_openai_api_key
GITHUB_TOKEN=your_github_token
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

4. **Preprocess EU AI Act documents**
```bash
python preprocessing.py path/to/eu_ai_act.pdf
```

5. **Run the FastAPI server**
```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

---

## 🔧 API Endpoints

### Audit & Compliance

**`POST /process`**  
Run full compliance audit on a single repository
```json
{
  "url": "https://github.com/username/repo"
}
```

**`GET /audit-stream`**  
Stream real-time audit progress
```
?url=https://github.com/username/repo
```

### Knowledge Graph

**`POST /process-multi-repo-graph`**  
Generate organizational knowledge graph
```json
{
  "urls": [
    "https://github.com/org/repo1",
    "https://github.com/org/repo2"
  ]
}
```

**`POST /graph-stream`**  
Stream knowledge graph generation progress

### Intelligence & Insights

**`POST /recommendations`**  
Get AI-powered talent and silo management recommendations

**`POST /dashboard-stats`**  
Aggregate compliance statistics across repositories

**`POST /node-owner`**  
Deep-dive forensics on specific knowledge cluster nodes
```json
{
  "repo_url": "https://github.com/username/repo",
  "node_id": "file_path"
}
```

---

## 📊 Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    JuriCode Platform                     │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ Risk         │  │ Data Ethics  │  │ Robustness   │ │
│  │ Classifier   │  │ Auditor      │  │ Auditor      │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘ │
│         │                  │                  │          │
│         └──────────────────┴──────────────────┘          │
│                            │                             │
│                  ┌─────────▼─────────┐                  │
│                  │   Synthesizer     │                  │
│                  │  (Annex IV Gen)   │                  │
│                  └─────────┬─────────┘                  │
│                            │                             │
│         ┌──────────────────┴──────────────────┐         │
│         │                                      │         │
│  ┌──────▼───────┐                   ┌─────────▼──────┐ │
│  │  Knowledge   │                   │  Supabase DB   │ │
│  │    Graph     │◄──────────────────┤  (Reports +    │ │
│  │  Generator   │                   │   Vectors)     │ │
│  └──────────────┘                   └────────────────┘ │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## 🎯 Key Features

✅ **Automated EU AI Act Compliance** - Annex IV technical documentation generation  
✅ **Multi-Repository Analysis** - Scan entire organizations at once  
✅ **Real-Time Streaming** - Watch audits happen live  
✅ **Stakeholder Mapping** - Know exactly who owns what code  
✅ **Legal Citation Engine** - Every violation linked to specific EU AI Act articles  
✅ **Remediation Code Generation** - Not just problems—solutions  
✅ **Knowledge Silo Detection** - AI-powered organizational intelligence  

---

## 📚 EU AI Act Coverage

JuriCode currently implements compliance checking for:

- **Article 5** - Prohibited AI practices
- **Article 10** - Data governance and bias mitigation
- **Article 15** - Technical robustness and cybersecurity
- **Annex III** - High-risk AI system classification
- **Annex IV** - Technical documentation requirements

---

## 🤝 Contributing

We welcome contributions! Please see our contributing guidelines for:
- Adding new audit agents
- Expanding EU AI Act coverage
- Improving knowledge graph algorithms
- Frontend enhancements

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 🔗 Links

- **Live Platform:** [https://juricode.lovable.app](https://juricode.lovable.app)
- **API Documentation:** `http://localhost:8000/docs` (when running locally)
- **EU AI Act Reference:** [Official EU Documentation](https://artificialintelligenceact.eu/)

---

## 👥 Team

Built with ❤️ for the future of responsible AI development.

---

## 🆘 Support

For issues, questions, or feature requests, please open an issue on GitHub or contact us through the platform.

---

**JuriCode: Because every line of code has a stakeholder, and every stakeholder deserves clarity.**
