import json
import os
import logging
from mcp_integration.modes.dev_project_mode import DevProjectMode
from mcp_integration.utils.sonarqube_context7_helper import SonarQubeContext7Helper

# Mock MCP Manager for demonstration
class MockMCPManager:
    def __init__(self):
        self.clients = {
            "sonarqube": MockClient("sonarqube"),
            "context7": MockClient("context7"),
            "context7-docs": MockClient("context7-docs")
        }
    
    def get_client(self, name):
        return self.clients.get(name)

class MockClient:
    def __init__(self, name):
        self.name = name
    
    def execute_command(self, command, **kwargs):
        print(f"DEBUG: Calling MCP {self.name} -> {command} with {kwargs}")
        if self.name == "sonarqube" and command == "analyze":
            return {
                "success": True, 
                "data": {
                    "status": "OK",
                    "issues": [
                        {"key": "issue1", "message": "Potential resource leak", "severity": "HIGH"},
                        {"key": "issue2", "message": "Use of raw types", "severity": "MEDIUM"}
                    ]
                }
            }
        return {"success": True, "data": {}}
    
    def store_context(self, data):
        print(f"DEBUG: Storing in Context7 -> {data['type']}")
        return {"success": True}

    def retrieve_context(self, query):
        print(f"DEBUG: Retrieving from Context7 -> {query}")
        # Extract project_id from query if possible
        p_id = query.split("project_id:")[-1] if "project_id:" in query else "unknown"
        root = getattr(self, 'current_project_root', './demo')
        return {
            "success": True, 
            "data": {
                "metadata": {
                    "name": "SecureAPI", 
                    "description": "Фінансовий API з високими вимогами до безпеки", 
                    "root_path": root
                }
            }
        }

def demonstrate_atlas_sonarqube():
    print("=== Демонстрація інтеграції Atlas + SonarQube ===\n")
    
    # 1. Ініціалізація менеджерів
    mcp_manager = MockMCPManager()
    dev_mode = DevProjectMode(mcp_manager)
    helper = SonarQubeContext7Helper(mcp_manager)
    
    # 2. Створення проекту
    print("1. Atlas створює новий проект...")
    # Використовуємо реальну тимчасову директорію для тесту
    os.makedirs("projects", exist_ok=True)
    
    project_info = dev_mode.create_project({
        "name": "SecureAPI",
        "type": "api",
        "description": "Фінансовий API з високими вимогами до безпеки"
    })
    project_id = project_info['project_id']
    print(f"   Проект створено: {project_id}")
    print(f"   Шлях: {project_info['project_root']}\n")
    
    # Оновлюємо mock, щоб він повертав реальний шлях
    mcp_manager.clients["context7"].current_project_root = project_info['project_root']
    
    # 3. Налаштування SonarQube
    print("2. Атлас налаштовує аналіз SonarQube...")
    sq_setup = dev_mode.setup_sonarqube_analysis(project_id)
    print(f"   Конфігурація SonarQube: {json.dumps(sq_setup['sonarqube_config'], indent=2, ensure_ascii=False)}\n")
    
    # 4. Виклик аналізу з документацією
    print("3. Виконання аналізу коду з підключенням бази знань Context7...")
    analysis = helper.get_analysis_with_docs(sq_setup['sonarqube_config']['project_key'])
    
    print("\n   Результати аналізу:")
    print(f"   Статус: {analysis['analysis']['status']}")
    for issue in analysis['analysis']['issues']:
        print(f"   - [{issue['severity']}] {issue['message']}")
    
    print("\n4. Рекомендації з документації (через Context7):")
    for topic, info in analysis['documentation']['topics'].items():
        print(f"   - {topic}: {info}")

if __name__ == "__main__":
    demonstrate_atlas_sonarqube()
