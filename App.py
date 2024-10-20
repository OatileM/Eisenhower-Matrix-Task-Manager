from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import uuid

app = Flask(__name__)

# In-memory storage (you might want to use a database in a real application)
tasks = {}
folders = {}
timers = {}

@app.route('/task', methods=['POST'])
def create_task():
    data = request.json
    task_id = str(uuid.uuid4())
    task = {
        'id': task_id,
        'name': data['name'],
        'folder_id': data.get('folder_id'),
        'created_at': datetime.now().isoformat()
    }
    tasks[task_id] = task
    return jsonify(task), 201

@app.route('/task/<task_id>', methods=['GET'])
def get_task(task_id):
    task = tasks.get(task_id)
    if task:
        return jsonify(task)
    return jsonify({'error': 'Task not found'}), 404

@app.route('/folder', methods=['POST'])
def create_folder():
    data = request.json
    folder_id = str(uuid.uuid4())
    folder = {
        'id': folder_id,
        'name': data['name'],
        'created_at': datetime.now().isoformat()
    }
    folders[folder_id] = folder
    return jsonify(folder), 201

@app.route('/folder/<folder_id>/tasks', methods=['GET'])
def get_folder_tasks(folder_id):
    folder_tasks = [task for task in tasks.values() if task['folder_id'] == folder_id]
    return jsonify(folder_tasks)

@app.route('/timer/start', methods=['POST'])
def start_timer():
    data = request.json
    task_id = data['task_id']
    if task_id not in tasks:
        return jsonify({'error': 'Task not found'}), 404
    
    timer = {
        'task_id': task_id,
        'start_time': datetime.now().isoformat(),
        'paused_time': None,
        'total_pause_time': timedelta(0)
    }
    timers[task_id] = timer
    return jsonify(timer), 201

@app.route('/timer/pause', methods=['POST'])
def pause_timer():
    data = request.json
    task_id = data['task_id']
    if task_id not in timers:
        return jsonify({'error': 'Timer not found'}), 404
    
    timer = timers[task_id]
    if timer['paused_time'] is None:
        timer['paused_time'] = datetime.now().isoformat()
    return jsonify(timer)

@app.route('/timer/resume', methods=['POST'])
def resume_timer():
    data = request.json
    task_id = data['task_id']
    if task_id not in timers:
        return jsonify({'error': 'Timer not found'}), 404
    
    timer = timers[task_id]
    if timer['paused_time'] is not None:
        pause_duration = datetime.now() - datetime.fromisoformat(timer['paused_time'])
        timer['total_pause_time'] += pause_duration
        timer['paused_time'] = None
    return jsonify(timer)

@app.route('/timer/stop', methods=['POST'])
def stop_timer():
    data = request.json
    task_id = data['task_id']
    if task_id not in timers:
        return jsonify({'error': 'Timer not found'}), 404
    
    timer = timers[task_id]
    end_time = datetime.now()
    start_time = datetime.fromisoformat(timer['start_time'])
    total_time = end_time - start_time - timer['total_pause_time']
    
    result = {
        'task_id': task_id,
        'total_time': str(total_time)
    }
    del timers[task_id]
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)
