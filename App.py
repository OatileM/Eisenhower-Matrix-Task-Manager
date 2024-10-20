from flask import Flask, request, jsonify, current_app
from datetime import datetime, timedelta
import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure
from bson.objectid import ObjectId
from bson.errors import InvalidId
from functools import wraps

app = Flask(__name__)

# MongoDB Atlas connection string
mongo_uri = os.environ.get('MONGO_URI')

# Flag to indicate if the database is available
db_available = False
try:
    # Connect to MongoDB Atlas
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    # Ping the server to check the connection
    client.admin.command('ping')
    print("Connected successfully to MongoDB!")
    db_available = True
except ConnectionFailure as e:
    print(f"Failed to connect to MongoDB. Error: {e}")
    print("Please check your connection string, network, and MongoDB Atlas settings.")
except Exception as e:
    print(f"An unexpected error occurred while connecting to MongoDB: {e}")

# Only set up database and collections if connection was successful
if db_available:
    db = client['Time2Learn']
    tasks_collection = db['tasks']
    folders_collection = db['folders']
    timers_collection = db['timers']

def handle_db_error(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not db_available:
            return jsonify({'error': 'Database is currently unavailable'}), 503
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
    current_app.logger.info("start_timer function called")
    try:
        data = request.json
        current_app.logger.info(f"Received data: {data}")
        task_id = data['task_id']
        current_app.logger.info(f"Searching for task with id: {task_id}")
        task = tasks_collection.find_one({'_id': ObjectId(task_id)})
        if not task:
            current_app.logger.warning(f"Task not found: {task_id}")
            return jsonify({'error': 'Task not found'}), 404
        
        current_app.logger.info(f"Task found: {task}")
        timer = {
            'task_id': task_id,
            'start_time': datetime.now(),
            'paused_time': None,
            'total_pause_time': 0  # Store as seconds instead of timedelta
        }
        current_app.logger.info(f"Inserting timer: {timer}")
        result = timers_collection.insert_one(timer)
        timer['_id'] = str(result.inserted_id)
        timer['start_time'] = timer['start_time'].isoformat()  # Convert datetime to string
        current_app.logger.info(f"Timer inserted successfully: {timer}")
        return jsonify(timer), 201
    except Exception as e:
        current_app.logger.error(f"Error in start_timer: {str(e)}")
        return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500

@app.route('/timer/pause', methods=['POST'])
@handle_db_error
def pause_timer():
    data = request.json
    task_id = data['task_id']
    timer = timers_collection.find_one({'task_id': task_id, 'paused_time': None})
    if not timer:
        return jsonify({'error': 'Active timer not found'}), 404
    
    pause_time = datetime.now()
    timers_collection.update_one(
        {'_id': timer['_id']},
        {'$set': {'paused_time': pause_time}}
    )
    timer['paused_time'] = pause_time.isoformat()
    timer['_id'] = str(timer['_id'])
    return jsonify(timer)

@app.route('/timer/resume', methods=['POST'])
@handle_db_error
def resume_timer():
    current_app.logger.info("resume_timer function called")
    try:
        data = request.json
        current_app.logger.info(f"Received data: {data}")
        task_id = data['task_id']
        current_app.logger.info(f"Searching for paused timer with task_id: {task_id}")
        timer = timers_collection.find_one({'task_id': task_id, 'paused_time': {'$ne': None}})
        if not timer:
            current_app.logger.warning(f"Paused timer not found for task_id: {task_id}")
            return jsonify({'error': 'Paused timer not found'}), 404
        
        current_app.logger.info(f"Paused timer found: {timer}")
        current_time = datetime.now()
        current_app.logger.info(f"Current time: {current_time}")
        current_app.logger.info(f"Paused time from DB: {timer['paused_time']}")
        
        # Check if paused_time is already a datetime object
        if isinstance(timer['paused_time'], datetime):
            paused_time = timer['paused_time']
        else:
            # If it's a string, parse it
            paused_time = datetime.fromisoformat(timer['paused_time'])
        
        current_app.logger.info(f"Parsed paused time: {paused_time}")
        pause_duration = (current_time - paused_time).total_seconds()
        
        current_app.logger.info(f"Calculating pause duration: {pause_duration} seconds")
        
        update_result = timers_collection.update_one(
            {'_id': timer['_id']},
            {
                '$set': {'paused_time': None},
                '$inc': {'total_pause_time': pause_duration}
            }
        )
        current_app.logger.info(f"Update result: {update_result.modified_count} document(s) modified")
        
        timer['paused_time'] = None
        timer['total_pause_time'] += pause_duration
        timer['_id'] = str(timer['_id'])
        current_app.logger.info(f"Timer resumed: {timer}")
        return jsonify(timer)
    except Exception as e:
        current_app.logger.error(f"Error in resume_timer: {str(e)}")
        return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500

@app.route('/timer/stop', methods=['POST'])
@handle_db_error
def stop_timer():
    current_app.logger.info("stop_timer function called")
    try:
        data = request.json
        current_app.logger.info(f"Received data: {data}")
        task_id = data['task_id']
        current_app.logger.info(f"Searching for timer with task_id: {task_id}")
        timer = timers_collection.find_one({'task_id': task_id})
        if not timer:
            current_app.logger.warning(f"Timer not found for task_id: {task_id}")
            return jsonify({'error': 'Timer not found'}), 404
        
        current_app.logger.info(f"Timer found: {timer}")
        end_time = datetime.now()
        current_app.logger.info(f"End time: {end_time}")

        # Convert start_time to datetime if it's a string
        start_time = timer['start_time']
        if isinstance(start_time, str):
            start_time = datetime.fromisoformat(start_time.rstrip('Z'))
        
        current_app.logger.info(f"Start time: {start_time}")

        total_time = end_time - start_time - timedelta(seconds=timer['total_pause_time'])
        current_app.logger.info(f"Calculated total time: {total_time}")
        
        result = {
            'task_id': task_id,
            'total_time': str(total_time)
        }
        delete_result = timers_collection.delete_one({'_id': timer['_id']})
        current_app.logger.info(f"Delete result: {delete_result.deleted_count} document(s) deleted")
        
        current_app.logger.info(f"Timer stopped: {result}")
        return jsonify(result)
    except Exception as e:
        current_app.logger.error(f"Error in stop_timer: {str(e)}")
        return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500

@app.route('/health', methods=['GET'])
def health_check():
    if db_available:
        return jsonify({'status': 'healthy', 'database': 'connected'}), 200
    else:
        return jsonify({'status': 'unhealthy', 'database': 'disconnected'}), 503

if __name__ == '__main__':
    app.run(debug=True)
