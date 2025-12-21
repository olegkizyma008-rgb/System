import os
import json
import subprocess
from dotenv import load_dotenv

def test_sonarqube_connection():
    load_dotenv()
    
    token = os.getenv("SONAR_API_KEY")
    org = os.getenv("SONAR_ORG_KEY")
    url = os.getenv("SONAR_URL")
    
    print(f"Тестування підключення до: {url}")
    print(f"Організація: {org}")
    
    # Спробуємо виконати простий запит через Docker, як це робить MCP
    # Використовуємо інструмент 'search_my_sonarqube_projects' як приклад (якщо він є у образі)
    # Але для тесту простіше просто спробувати ping або перевірити версію через API безпосередньо
    
    import requests
    
    api_url = f"{url}/api/organizations/search?organizations={org}"
    # SonarQube використовує Basic Auth з токеном замість імені користувача (без пароля)
    try:
        response = requests.get(api_url, auth=(token, ""))
        if response.status_code == 200:
            print("✅ УСПІХ: Підключення до SonarCloud встановлено!")
            print(f"Дані організації: {json.dumps(response.json(), indent=2)}")
        else:
            print(f"❌ ПОМИЛКА: Сервер повернув статус {response.status_code}")
            print(f"Відповідь: {response.text}")
    except Exception as e:
        print(f"❌ ПОМИЛКА: Не вдалося з'єднатися з сервером: {e}")

if __name__ == "__main__":
    test_sonarqube_connection()
