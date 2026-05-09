"""Probe JIRA to discover projects, issue types, and create a test ticket."""
import os, requests, json
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

AUTH   = (os.environ["JIRA_EMAIL"], os.environ["JIRA_API_TOKEN"])
SERVER = os.environ["JIRA_SERVER"]
PROJ   = os.environ.get("JIRA_PROJECT_KEY", "SCRUM")


def get(path):
    r = requests.get(f"{SERVER}{path}", auth=AUTH, timeout=10)
    if not r.content:
        print(f"  [WARN] Empty response body for GET {path} (HTTP {r.status_code})")
        return r.status_code, {}
    try:
        return r.status_code, r.json()
    except Exception:
        print(f"  [WARN] Non-JSON response: {r.text[:200]}")
        return r.status_code, {}


def post(path, body):
    r = requests.post(f"{SERVER}{path}", auth=AUTH, json=body, timeout=10)
    if not r.content:
        return r.status_code, {}
    try:
        return r.status_code, r.json()
    except Exception:
        print(f"  [WARN] Non-JSON response: {r.text[:200]}")
        return r.status_code, {}


# 1. Who am I?
status, me = get("/rest/api/3/myself")
print(f"\n=== Authenticated User (HTTP {status}) ===")
print(f"  Name      : {me.get('displayName')}")
print(f"  Email     : {me.get('emailAddress')}")
print(f"  AccountId : {me.get('accountId')}")

# 2. Projects
status, data = get("/rest/api/3/project/search")
projects = data.get("values", [])
print(f"\n=== Projects (HTTP {status}) ===")
if projects:
    for p in projects:
        print(f"  key={p['key']:<12} name={p['name']:<30} id={p['id']}")
else:
    print("  (none returned)")

# 3. Issue types for configured project
status, pdata = get(f"/rest/api/3/project/{PROJ}")
issue_types = pdata.get("issueTypes", [])
print(f"\n=== Issue Types for '{PROJ}' (HTTP {status}) ===")
if issue_types:
    for t in issue_types:
        print(f"  id={t['id']:<8} name={t['name']}")
    chosen_type = issue_types[0]["name"]
else:
    print(f"  error: {pdata.get('errorMessages', pdata)}")
    chosen_type = "Task"

# 4. Create test ticket
print(f"\n=== Creating ticket (issuetype='{chosen_type}') ===")
status, result = post("/rest/api/3/issue", {
    "fields": {
        "project":     {"key": PROJ},
        "summary":     "[CrewOps] TEST — P1 payment-service CrashLoopBackOff",
        "issuetype":   {"name": chosen_type},
        "description": {
            "type": "doc", "version": 1,
            "content": [{"type": "paragraph", "content": [
                {"type": "text", "text": "Automated test ticket from CrewOps CLI runner."}
            ]}]
        },
        "priority": {"name": "Highest"},
    }
})
print(f"  HTTP {status}")
if status in (200, 201):
    key = result.get("key", "?")
    print(f"  Ticket: {key}  ->  {SERVER}/browse/{key}")
else:
    print(f"  {json.dumps(result, indent=2)}")

# --- remove old code below this line ---

auth   = (os.environ["JIRA_EMAIL"], os.environ["JIRA_API_TOKEN"])
server = os.environ["JIRA_SERVER"]
proj   = os.environ.get("JIRA_PROJECT_KEY", "SCRUM")

print(f"Server : {server}")
print(f"Project: {proj}\n")

# 1. List projects
r = requests.get(f"{server}/rest/api/3/project/search", auth=auth, timeout=10)
print(f"Projects ({r.status_code}):")
for p in r.json().get("values", []):
    print(f"  {p['key']:15} — {p['name']}")

# 2. Issue types for this project
r2 = requests.get(f"{server}/rest/api/3/project/{proj}", auth=auth, timeout=10)
if r2.ok:
    it = r2.json().get("issueTypes", [])
    print(f"\nIssue types for {proj}:")
    for t in it:
        print(f"  {t['id']:6}  {t['name']}")
    first_type = it[0]["name"] if it else "Task"
else:
    print(f"\nProject {proj} not found ({r2.status_code}): {r2.text[:200]}")
    first_type = "Task"

# 3. Create a test ticket
print(f"\nCreating test issue with issuetype='{first_type}'...")
r3 = requests.post(
    f"{server}/rest/api/3/issue",
    auth=auth,
    timeout=10,
    json={
        "fields": {
            "project":     {"key": proj},
            "summary":     "[CrewOps] TEST — P1 payment-service CrashLoopBackOff",
            "issuetype":   {"name": first_type},
            "description": {
                "type": "doc", "version": 1,
                "content": [{"type": "paragraph", "content": [
                    {"type": "text", "text": "Automated test ticket from CrewOps CLI runner."}
                ]}]
            }
        }
    }
)
print(f"Create status: {r3.status_code}")
if r3.ok:
    data = r3.json()
    print(f"✅  Ticket created: {data['key']}  →  {server}/browse/{data['key']}")
else:
    print(f"❌  Error: {r3.text[:400]}")
