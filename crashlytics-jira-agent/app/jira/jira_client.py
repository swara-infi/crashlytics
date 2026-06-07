import os
import requests

class JiraClient:
    def __init__(self):
        self.jira_url = os.getenv("JIRA_URL")
        if not self.jira_url:
            raise ValueError("Missing JIRA_URL environment variable. Please configure it in your settings.")
        self.jira_username = os.getenv("JIRA_USERNAME")
        self.jira_api_token = os.getenv("JIRA_API_TOKEN")

        if not self.jira_username or not self.jira_api_token:
            raise ValueError("JIRA_USERNAME or JIRA_API_TOKEN environment variables are not set")
        
        self.headers = {
            "Content-Type": "application/json"
        }
        self.auth = (self.jira_username, self.jira_api_token)

    def create_issue(self, summary, description, project_key="CRASH"):
        url = f"{self.jira_url}/rest/api/2/issue"
        data = {
            "fields": {
                "project": {
                    "key": project_key
                },
                "summary": summary,
                "description": description,
                "issuetype": {
                    "name": "Bug"
                }
            }
        }
        response = requests.post(url, headers=self.headers, json=data, auth=self.auth)
        response.raise_for_status()  # Raise an exception for bad status codes
        return response.json()

    def get_issue(self, issue_key):
        url = f"{self.jira_url}/rest/api/2/issue/{issue_key}"
        response = requests.get(url, headers=self.headers, auth=self.auth)
        response.raise_for_status()
        return response.json()