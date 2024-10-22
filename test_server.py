import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:5000"

def test_create_task():
    print("Testing create task...")
    task_data = {
        "name": "Test Task",
        "priority": {"urgent": True, "important": True}
    }
    response = requests.post(f"{BASE_URL}/task", json=task_data)
    print(f"Status Code: {response.status_code}")
    print(f"Response content: {response.text}")
    assert response.status_code == 201, f"Expected status code 201, but got {response.status_code}"
    result = response.json()
    print(f"Create task result: {result}")
    return result['_id']

def test_get_task(task_id):
    print(f"Testing get task {task_id}...")
    response = requests.get(f"{BASE_URL}/task/{task_id}")
    print(f"Status Code: {response.status_code}")
    print(f"Response content: {response.text}")
    assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"
    result = response.json()
    print(f"Get task result: {result}")

def test_delete_task(task_id):
    print(f"Testing delete task {task_id}...")
    response = requests.delete(f"{BASE_URL}/task/{task_id}")
    print(f"Status Code: {response.status_code}")
    print(f"Response content: {response.text}")
    assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"
    result = response.json()
    print(f"Delete task result: {result}")

def test_create_folder():
    print("Testing create folder...")
    folder_data = {"name": "Test Folder"}
    response = requests.post(f"{BASE_URL}/folder", json=folder_data)
    print(f"Status Code: {response.status_code}")
    print(f"Response content: {response.text}")
    assert response.status_code == 201, f"Expected status code 201, but got {response.status_code}"
    result = response.json()
    print(f"Create folder result: {result}")
    return result['_id']

def test_delete_folder(folder_id):
    print(f"Testing delete folder {folder_id}...")
    response = requests.delete(f"{BASE_URL}/folder/{folder_id}")
    print(f"Status Code: {response.status_code}")
    print(f"Response content: {response.text}")
    assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"
    result = response.json()
    print(f"Delete folder result: {result}")

def test_get_folder_tasks(folder_id):
    print(f"Testing get folder tasks for folder {folder_id}...")
    response = requests.get(f"{BASE_URL}/folder/{folder_id}/tasks")
    print(f"Status Code: {response.status_code}")
    print(f"Response content: {response.text}")
    assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"
    result = response.json()
    print(f"Get folder tasks result: {result}")

def test_add_task_to_folder(folder_id):
    print(f"Testing add task to folder {folder_id}...")
    task_data = {"name": "Test Task in Folder"}
    response = requests.post(f"{BASE_URL}/folder/{folder_id}/task", json=task_data)
    print(f"Status Code: {response.status_code}")
    print(f"Response content: {response.text}")
    assert response.status_code == 201, f"Expected status code 201, but got {response.status_code}"
    result = response.json()
    print(f"Add task to folder result: {result}")
    return result['_id']

def test_move_task_to_folder(task_id, from_folder_id, to_folder_id, new_priority=None):
    print(f"Testing move task {task_id} from folder {from_folder_id} to folder {to_folder_id} with priority {new_priority}...")
    data = {"folder_id": to_folder_id}
    if new_priority:
        data["priority"] = new_priority
    response = requests.put(f"{BASE_URL}/task/{task_id}/move", json=data)
    print(f"Status Code: {response.status_code}")
    print(f"Response content: {response.text}")
    assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"
    result = response.json()
    print(f"Move task to folder result: {result}")

def run_tests():
    try:
        # Test task operations
        task_id = test_create_task()
        test_get_task(task_id)
        
        # Test folder operations
        urgent_important_folder_id = test_create_folder()
        not_urgent_important_folder_id = test_create_folder()
        
        # Test adding task to folder
        task_in_folder_id = test_add_task_to_folder(urgent_important_folder_id)
        
        # Test getting folder tasks
        test_get_folder_tasks(urgent_important_folder_id)
        
        # Test moving task between folders with priority change
        test_move_task_to_folder(task_in_folder_id, urgent_important_folder_id, not_urgent_important_folder_id, 
                                 new_priority={"urgent": False, "important": True})
        
        # Clean up
        test_delete_task(task_id)
        test_delete_task(task_in_folder_id)
        test_delete_folder(urgent_important_folder_id)
        test_delete_folder(not_urgent_important_folder_id)
        
        print("All tests passed successfully!")
    except AssertionError as e:
        print(f"Test failed: {str(e)}")
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while sending requests: {e}")

if __name__ == "__main__":
    run_tests()
