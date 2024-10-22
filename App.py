from flask import Flask, request, jsonify, current_app, render_template
from datetime import datetime, timedelta
import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure
from bson.objectid import ObjectId
from bson.errors import InvalidId
from functools import wraps
from flask_cors import CORS

app = Flask(__name__)

# Enable CORS
cors = CORS(app)    

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

#  Decorator that's designed to handle database-related errors in application
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

def get_eisenhower_quadrant(priority):
    if priority['urgent'] and priority['important']:
        return "urgent_important"
    elif not priority['urgent'] and priority['important']:
        return "not_urgent_important"
    elif priority['urgent'] and not priority['important']:
        return "urgent_not_important"
    else:
        return "not_urgent_not_important"


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/task', methods=['POST'])
@handle_db_error
def create_task():
    data = request.json
    priority = data['priority']
    quadrant = get_eisenhower_quadrant(priority)
    
    # Check if the quadrant folder exists, if not create it
    folder = folders_collection.find_one({'name': quadrant})
    if not folder:
        folder_result = folders_collection.insert_one({'name': quadrant, 'created_at': datetime.now()})
        folder_id = str(folder_result.inserted_id)
    else:
        folder_id = str(folder['_id'])
    
    task = {
        'name': data['name'],
        'folder_id': folder_id,
        'priority': priority,
        'created_at': datetime.now()
    }
    result = tasks_collection.insert_one(task)
    task['_id'] = str(result.inserted_id)
    task['created_at'] = task['created_at'].isoformat()
    return jsonify(task), 201


@app.route('/task/<task_id>', methods=['GET'])
@handle_db_error
def get_task(task_id):
    task = tasks_collection.find_one({'_id': ObjectId(task_id)})
    if task:
        task['_id'] = str(task['_id'])
        task['created_at'] = task['created_at'].isoformat()
        return jsonify(task)
    return jsonify({'error': 'Task not found'}), 404

@app.route('/task', methods=['GET'])
@handle_db_error
def get_all_tasks():
    tasks = list(tasks_collection.find())
    for task in tasks:
        task['_id'] = str(task['_id'])
        task['created_at'] = task['created_at'].isoformat()
    return jsonify(tasks)



@app.route('/task/<task_id>', methods=['DELETE'])
@handle_db_error
def delete_task(task_id):
    current_app.logger.info(f"delete_task function called for task_id: {task_id}")
    try:
        result = tasks_collection.delete_one({'_id': ObjectId(task_id)})
        if result.deleted_count == 0:
            current_app.logger.warning(f"Task not found: {task_id}")
            return jsonify({'error': 'Task not found'}), 404
        
        # Also delete any associated timers
        timers_collection.delete_many({'task_id': task_id})
        
        current_app.logger.info(f"Task {task_id} deleted successfully")
        return jsonify({'message': 'Task deleted successfully'}), 200
    except Exception as e:
        current_app.logger.error(f"Error in delete_task: {str(e)}")
  


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
    folder['created_at'] = folder['created_at'].isoformat()
    return jsonify(folder), 201

@app.route('/folder/<folder_id>', methods=['DELETE'])
@handle_db_error
def delete_folder(folder_id):
    current_app.logger.info(f"delete_folder function called for folder_id: {folder_id}")
    try:
        # First, delete all tasks in the folder
        current_app.logger.info(f"Deleted {tasks_collection.deleted_count} tasks from folder {folder_id}")
        
        # Then delete the folder
        folder_result = folders_collection.delete_one({'_id': ObjectId(folder_id)})
        if folder_result.deleted_count == 0:
            current_app.logger.warning(f"Folder not found: {folder_id}")
            return jsonify({'error': 'Folder not found'}), 404
        
        current_app.logger.info(f"Folder {folder_id} deleted successfully")
        return jsonify({'message': 'Folder and all its tasks deleted successfully'}), 200
    except Exception as e:
        current_app.logger.error(f"Error in delete_folder: {str(e)}")
        return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500

@app.route('/folder/<folder_id>/tasks', methods=['GET'])
@handle_db_error
def get_folder_tasks(folder_id):
    folder_tasks = list(tasks_collection.find({'folder_id': folder_id}))
    for task in folder_tasks:
        task['_id'] = str(task['_id'])
        task['created_at'] = task['created_at'].isoformat()
    return jsonify(folder_tasks)

@app.route('/folder/<folder_id>/task', methods=['POST'])
@handle_db_error
def add_task_to_folder(folder_id):
    current_app.logger.info(f"add_task_to_folder function called for folder_id: {folder_id}")
    try:
        data = request.json
        current_app.logger.info(f"Received data: {data}")
        
        # Check if the folder exists
        folder = folders_collection.find_one({'_id': ObjectId(folder_id)})
        if not folder:
            current_app.logger.warning(f"Folder not found: {folder_id}")
            return jsonify({'error': 'Folder not found'}), 404
        
        task = {
            'name': data['name'],
            'folder_id': folder_id,
            'created_at': datetime.now()
        }
        result = tasks_collection.insert_one(task)
        task['_id'] = str(result.inserted_id)
        task['created_at'] = task['created_at'].isoformat()
        
        current_app.logger.info(f"Task added to folder: {task}")
        return jsonify(task), 201
    except Exception as e:
        current_app.logger.error(f"Error in add_task_to_folder: {str(e)}")
        return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500

@app.route('/task/<task_id>/move', methods=['PUT'])
@handle_db_error
def move_task_to_folder(task_id):
    current_app.logger.info(f"move_task_to_folder function called for task_id: {task_id}")
    try:
        data = request.json
        new_priority = data.get('priority')
        current_app.logger.info(f"Received data: {data}")

        # Check if the task exists
        task = tasks_collection.find_one({'_id': ObjectId(task_id)})
        if not task:
            current_app.logger.warning(f"Task not found: {task_id}")
            return jsonify({'error': 'Task not found'}), 404

        # Determine new quadrant based on priority
        if new_priority:
            new_quadrant = get_eisenhower_quadrant(new_priority)
            folder = folders_collection.find_one({'name': new_quadrant})
            if not folder:
                folder_result = folders_collection.insert_one({'name': new_quadrant, 'created_at': datetime.now()})
                folder_id = str(folder_result.inserted_id)
            else:
                folder_id = str(folder['_id'])
        else:
            folder_id = data.get('folder_id')

        # Create the update_data dictionary
        update_data = {"$set": {"folder_id": folder_id}}
        if new_priority:
            update_data["$set"]["priority"] = new_priority

        # Perform the update operation
        update_result = tasks_collection.update_one({'_id': ObjectId(task_id)}, update_data)

        if update_result.modified_count == 0:
            current_app.logger.warning(f"Task not found or no changes made: {task_id}")
            return jsonify({'message': 'Task not found or no changes made'}), 404

        current_app.logger.info(f"Task {task_id} moved to folder {folder_id} successfully")
        return jsonify({'message': 'Task moved successfully'}), 200
    except Exception as e:
        current_app.logger.error(f"Error in move_task_to_folder: {str(e)}")
        return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500

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
        start_time = datetime.now()
        timer = {
            'task_id': task_id,
            'start_time': start_time,
            'paused_time': None,
            'total_pause_time': 0
        }
        current_app.logger.info(f"Inserting timer: {timer}")
        result = timers_collection.insert_one(timer)
        timer['_id'] = str(result.inserted_id)
        timer['start_time'] = start_time.isoformat()
        current_app.logger.info(f"Timer inserted successfully: {timer}")
        return jsonify(timer), 201
    except Exception as e:
        current_app.logger.error(f"Error in start_timer: {str(e)}")
        return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500

@app.route('/timer/pause', methods=['POST'])
@handle_db_error
def pause_timer():
    current_app.logger.info("pause_timer function called")
    try:
        data = request.json
        current_app.logger.info(f"Received data: {data}")
        task_id = data['task_id']
        current_app.logger.info(f"Searching for active timer with task_id: {task_id}")
        timer = timers_collection.find_one({'task_id': task_id, 'paused_time': None})
        if not timer:
            current_app.logger.warning(f"Active timer not found for task_id: {task_id}")
            return jsonify({'error': 'Active timer not found'}), 404
        
        current_app.logger.info(f"Active timer found: {timer}")
        pause_time = datetime.now()
        update_result = timers_collection.update_one(
            {'_id': timer['_id']},
            {'$set': {'paused_time': pause_time}}
        )
        current_app.logger.info(f"Update result: {update_result.modified_count} document(s) modified")
        
        timer['paused_time'] = pause_time.isoformat()
        timer['_id'] = str(timer['_id'])
        current_app.logger.info(f"Timer paused: {timer}")
        return jsonify(timer)
    except Exception as e:
        current_app.logger.error(f"Error in pause_timer: {str(e)}")
        return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500

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
