import requests
import os
import json

# SonarCloud configuration
SONAR_URL = os.getenv('SONAR_URL', 'https://sonarcloud.io')
SONAR_API_KEY = os.getenv('SONAR_API_KEY')
SONAR_ORG_KEY = os.getenv('SONAR_ORG_KEY')
PROJECT_KEY = 'olegkizima01_System2'

def get_critical_issues():
    url = f"{SONAR_URL}/api/issues/search"
    params = {
        'componentKeys': PROJECT_KEY,
        'severities': 'CRITICAL,BLOCKER',
        'resolved': 'false',
    }
    
    response = requests.get(url, params=params, auth=(SONAR_API_KEY, ''))
    
    if response.status_code == 200:
        data = response.json()
        print(f"Total Critical/Blocker Issues: {data.get('total', 0)}")
        
        with open('critical_issues_v3.json', 'w') as f:
            json.dump(data, f, indent=2)
            
        return data.get('issues', [])
    else:
        print(f"Failed to fetch issues: {response.status_code}")
        print(response.text)
        return []

if __name__ == "__main__":
    if not SONAR_API_KEY:
        print("SONAR_API_KEY not set")
    else:
        issues = get_critical_issues()
        for issue in issues[:5]:
            print(f"- {issue.get('severity')}: {issue.get('message')} ({issue.get('component')})")
