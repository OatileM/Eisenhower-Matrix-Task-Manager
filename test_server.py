import requests
import time

# Base URL of your server
BASE_URL = 'http://localhost:5000'

def test_create_task():
    print("Testing create task...")
    response = requests.post(f"{BASE_URL}/task", json={"name": "Test Task"})
    print(f"Status Code: {response.status_code}")
    assert response.status_code == 201, f"Expected status code 201, but got {response.status_code}"
    task = response.json()
    print(f"Created task: {task}")
    return task['_id']

def test_get_task(task_id):
    print(f"Testing get task {task_id}...")
    response = requests.get(f"{BASE_URL}/task/{task_id}")
    print(f"Status Code: {response.status_code}")
    assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"
    task = response.json()
    print(f"Retrieved task: {task}")

def test_delete_task(task_id):
    print(f"Testing delete task {task_id}...")
    response = requests.delete(f"{BASE_URL}/task/{task_id}")
    print(f"Status Code: {response.status_code}")
    assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"
    result = response.json()
    print(f"Delete task result: {result}")

def test_create_folder():
    print("Testing create folder...")
    response = requests.post(f"{BASE_URL}/folder", json={"name": "Test Folder"})
    print(f"Status Code: {response.status_code}")
    assert response.status_code == 201, f"Expected status code 201, but got {response.status_code}"
    folder = response.json()
    print(f"Created folder: {folder}")
    return folder['_id']

def test_delete_folder(folder_id):
    print(f"Testing delete folder {folder_id}...")
    response = requests.delete(f"{BASE_URL}/folder/{folder_id}")
    print(f"Status Code: {response.status_code}")
    assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"
    result = response.json()
    print(f"Delete folder result: {result}")

def test_get_folder_tasks(folder_id):
    print(f"Testing get folder tasks for folder {folder_id}...")
    response = requests.get(f"{BASE_URL}/folder/{folder_id}/tasks")
    print(f"Status Code: {response.status_code}")
    assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"
    tasks = response.json()
    print(f"Retrieved tasks: {tasks}")

def test_add_task_to_folder(folder_id):
    print(f"Testing add task to folder {folder_id}...")
    task_data = {"name": "Test Task in Folder"}
    response = requests.post(f"{BASE_URL}/folder/{folder_id}/task", json=task_data)
    print(f"Status Code: {response.status_code}")
    assert response.status_code == 201, f"Expected status code 201, but got {response.status_code}"
    task = response.json()
    print(f"Added task to folder: {task}")
    return task['_id']

def test_move_task_to_folder(task_id, from_folder_id, to_folder_id):
    print(f"Testing move task {task_id} from folder {from_folder_id} to folder {to_folder_id}...")
    response = requests.put(f"{BASE_URL}/task/{task_id}/move", json={"folder_id": to_folder_id})
    print(f"Status Code: {response.status_code}")
    print(f"Response content: {response.text}")
    assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}. Response content: {response.text}"
    result = response.json()
    print(f"Move task to folder result: {result}")


def test_timer_operations(task_id):
    print(f"Testing timer operations for task {task_id}...")
    
    # Start timer
    response = requests.post(f"{BASE_URL}/timer/start", json={"task_id": task_id})
    print(f"Start Timer Status Code: {response.status_code}")
    assert response.status_code == 201, f"Expected status code 201 for start timer, but got {response.status_code}"
    timer = response.json()
    print(f"Started timer: {timer}")
    
    # Wait for 2 seconds
    time.sleep(2)
    
  # Pause timer
    response = requests.post(f"{BASE_URL}/timer/pause", json={"task_id": task_id})
    print(f"Pause Timer Status Code: {response.status_code}")
    assert response.status_code == 200, f"Expected status code 200 for pause timer, but got {response.status_code}"
    timer = response.json()
    print(f"Paused timer: {timer}")
    
    # Wait for 1 second
    time.sleep(1)
    
    # Resume timer
    response = requests.post(f"{BASE_URL}/timer/resume", json={"task_id": task_id})
    print(f"Resume Timer Status Code: {response.status_code}")
    assert response.status_code == 200, f"Expected status code 200 for resume timer, but got {response.status_code}"
    timer = response.json()
    print(f"Resumed timer: {timer}")
    
    # Wait for 2 seconds
    time.sleep(2)
    
    # Stop timer
    response = requests.post(f"{BASE_URL}/timer/stop", json={"task_id": task_id})
    print(f"Stop Timer Status Code: {response.status_code}")
    assert response.status_code == 200, f"Expected status code 200 for stop timer, but got {response.status_code}"
    result = response.json()
    print(f"Stopped timer: {result}")

def run_tests():
    try:
        # Test task operations
        task_id = test_create_task()
        test_get_task(task_id)
        
        # Test folder operations
        folder_id = test_create_folder()
        second_folder_id = test_create_folder()
        
        # Test adding task to folder
        task_in_folder_id = test_add_task_to_folder(folder_id)
        
        # Test getting folder tasks
        test_get_folder_tasks(folder_id)
        
        # Test moving task between folders
        test_move_task_to_folder(task_in_folder_id, folder_id, second_folder_id)
        
        # Test timer operations
        test_timer_operations(task_id)
        
        # Clean up
        test_delete_task(task_id)
        test_delete_task(task_in_folder_id)
        test_delete_folder(folder_id)
        test_delete_folder(second_folder_id)
        
        print("All tests passed successfully!")
    except AssertionError as e:
        print(f"Test failed: {str(e)}")
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while sending requests: {e}")

if __name__ == "__main__":
    run_tests()
