from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure
from bson.objectid import ObjectId
from bson.errors import InvalidId

app = Flask(__name__)

# MongoDB Atlas connection string
mongo_uri = os.environ.get('MONGO_URI')

try:
    # Connect to MongoDB Atlas
    client = MongoClient(mongo_uri)
    # Ping the server to check the connection
    client.admin.command('ping')
    print("Connected successfully to MongoDB!")
except ConnectionFailure:
    print("Failed to connect to MongoDB. Please check your connection string and network.")
    # In a production environment, you might want to exit the application or implement a retry mechanism
    # sys.exit(1)

db = client['Time2Learn']

# Collections
tasks_collection = db['tasks']
folders_collection = db['folders']
timers_collection = db['timers']

def handle_db_error(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ConnectionFailure:
            return jsonify({'error': 'Database connection error'}), 500
        except OperationFailure as e:
            return jsonify({'error': f'Database operation failed: {str(e)}'}), 500
        except InvalidId:
            return jsonify({'error': 'Invalid ID format'}), 400
        except Exception as e:
            return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500
    return wrapper

@app.route('/task', methods=['POST'])
@handle_db_error
def create_task():
    data = request.json
    task = {
        'name': data['name'],
        'folder_id': data.get('folder_id'),
        'created_at': datetime.now()
    }
    result = tasks_collection.insert_one(task)
    task['_id'] = str(result.inserted_id)
    return jsonify(task), 201

@app.route('/task/<task_id>', methods=['GET'])
@handle_db_error
def get_task(task_id):
    task = tasks_collection.find_one({'_id': ObjectId(task_id)})
    if task:
        task['_id'] = str(task['_id'])
        return jsonify(task)
    return jsonify({'error': 'Task not found'}), 404

@app.route('/folder', methods=['POST'])
@handle_db_error
def create_folder():
    data = request.json
    folder = {
        'name': data['name'],
        'created_at': datetime.now()
    }
    result = folders_collection.insert_one(folder)
    folder['_id'] = str(result.inserted_id)
    return jsonify(folder), 201

@app.route('/folder/<folder_id>/tasks', methods=['GET'])
@handle_db_error
def get_folder_tasks(folder_id):
    folder_tasks = list(tasks_collection.find({'folder_id': folder_id}))
    for task in folder_tasks:
        task['_id'] = str(task['_id'])
    return jsonify(folder_tasks)

@app.route('/timer/start', methods=['POST'])
@handle_db_error
def start_timer():
    data = request.json
    task_id = data['task_id']
    task = tasks_collection.find_one({'_id': ObjectId(task_id)})
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    
    timer = {
        'task_id': task_id,
        'start_time': datetime.now(),
        'paused_time': None,
        'total_pause_time': timedelta(0)
    }
    result = timers_collection.insert_one(timer)
    timer['_id'] = str(result.inserted_id)
    return jsonify(timer), 201

@app.route('/timer/pause', methods=['POST'])
@handle_db_error
def pause_timer():
    data = request.json
    task_id = data['task_id']
    timer = timers_collection.find_one({'task_id': task_id, 'paused_time': None})
    if not timer:
        return jsonify({'error': 'Active timer not found'}), 404
    
    timers_collection.update_one(
        {'_id': timer['_id']},
        {'$set': {'paused_time': datetime.now()}}
    )
    timer['paused_time'] = datetime.now()
    timer['_id'] = str(timer['_id'])
    return jsonify(timer)

@app.route('/timer/resume', methods=['POST'])
@handle_db_error
def resume_timer():
    data = request.json
    task_id = data['task_id']
    timer = timers_collection.find_one({'task_id': task_id, 'paused_time': {'$ne': None}})
    if not timer:
        return jsonify({'error': 'Paused timer not found'}), 404
    
    pause_duration = datetime.now() - timer['paused_time']
    timers_collection.update_one(
        {'_id': timer['_id']},
        {
            '$set': {'paused_time': None},
            '$inc': {'total_pause_time': pause_duration.total_seconds()}
        }
    )
    timer['paused_time'] = None
    timer['total_pause_time'] += pause_duration
    timer['_id'] = str(timer['_id'])
    return jsonify(timer)

@app.route('/timer/stop', methods=['POST'])
@handle_db_error
def stop_timer():
    data = request.json
    task_id = data['task_id']
    timer = timers_collection.find_one({'task_id': task_id})
    if not timer:
        return jsonify({'error': 'Timer not found'}), 404
    
    end_time = datetime.now()
    total_time = end_time - timer['start_time'] - timedelta(seconds=timer['total_pause_time'])
    
    result = {
        'task_id': task_id,
        'total_time': str(total_time)
    }
    timers_collection.delete_one({'_id': timer['_id']})
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)
