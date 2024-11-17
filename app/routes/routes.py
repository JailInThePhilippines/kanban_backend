import os
from flask import Blueprint, jsonify, request, current_app, abort
from werkzeug.security import generate_password_hash, check_password_hash
from ..models import TaskSchema, UserSchema
from datetime import datetime, timedelta
from bson import ObjectId
from functools import wraps
import jwt

bp = Blueprint('routes', __name__, url_prefix='/api')

task_schema = TaskSchema()
task_list_schema = TaskSchema(many=True)
user_schema = UserSchema()

# Helper function to convert MongoDB ObjectIds to strings
def convert_objectid(data):
    if isinstance(data, list):
        for item in data:
            item['_id'] = str(item['_id'])
    elif '_id' in data:
        data['_id'] = str(data['_id'])
    return data

# JWT token generation
def generate_jwt(user_id):
    payload = {
        'user_id': str(user_id),
        'exp': datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')

# JWT authentication decorator
def jwt_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'error': 'Authorization token required'}), 401

        token_parts = auth_header.split()
        if len(token_parts) != 2 or token_parts[0].lower() != 'bearer':
            return jsonify({'error': 'Invalid authorization format. Expected "Bearer <token>"'}), 401

        token = token_parts[1]

        try:
            decoded = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            request.user_id = decoded['user_id']
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401

        return f(*args, **kwargs)
    return wrapper

# Register route for user registration
@bp.route('/register', methods=['POST'])
def register():
    data = request.json

    # Validate and deserialize input data
    errors = user_schema.validate(data)
    if errors:
        return jsonify(errors), 400 

    # Hash the password
    data['password'] = generate_password_hash(data['password'])

    # Add created_at field
    data['created_at'] = datetime.utcnow()

    # Insert into the database
    try:
        result = current_app.db.users.insert_one(data)
        return jsonify({'message': 'User registered successfully', 'id': str(result.inserted_id)}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Login route
@bp.route('/login', methods=['POST'])
def login():
    data = request.json

    # Check for required fields
    email = data.get('email')
    password = data.get('password')
    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400

    # Find user by email
    user = current_app.db.users.find_one({'email': email})
    if not user:
        return jsonify({'error': 'Invalid email or password'}), 401

    # Check password
    if not check_password_hash(user['password'], password):
        return jsonify({'error': 'Invalid email or password'}), 401

    # Generate JWT
    token = generate_jwt(user['_id'])
    return jsonify({'message': 'Login successful', 'token': token}), 200

# Route to get all tasks (protected route)
@bp.route('/tasks', methods=['GET'])
@jwt_required
def get_tasks():
    tasks = list(current_app.db.tasks.find({'user_id': request.user_id}))
    convert_objectid(tasks)
    for task in tasks:
        if 'due_date' in task and isinstance(task['due_date'], str):
            task['due_date'] = datetime.strptime(task['due_date'], "%Y-%m-%d").date()

    tasks_serialized = task_list_schema.dump(tasks)
    return jsonify(tasks_serialized)

# Route to post a new task (protected route)
@bp.route('/postTask', methods=['POST'])
@jwt_required
def post_task():
    data = request.json

    # Validate and deserialize input data
    errors = task_schema.validate(data)
    if errors:
        return jsonify(errors), 400 

    # Add created_at field and user_id from the authenticated user
    data['created_at'] = datetime.utcnow()
    data['user_id'] = request.user_id

    # Insert into the database
    try:
        result = current_app.db.tasks.insert_one(data)
        return jsonify({'message': 'Task added successfully', 'id': str(result.inserted_id)}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
# Route to update a task's status (protected route)
@bp.route('/updateTaskStatus/<task_id>', methods=['PATCH'])
@jwt_required
def update_task_status(task_id):
    data = request.json
    new_status = data.get('status')

    if not new_status:
        return jsonify({'error': 'New status is required'}), 400

    # Check if task exists and belongs to the user
    task = current_app.db.tasks.find_one({'_id': ObjectId(task_id), 'user_id': request.user_id})
    if not task:
        return jsonify({'error': 'Task not found or access denied'}), 404

    # Update the task status
    try:
        current_app.db.tasks.update_one(
            {'_id': ObjectId(task_id)},
            {'$set': {'status': new_status}}
        )
        return jsonify({'message': 'Task status updated successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
# Route to delete a task (protected route)
@bp.route('/deleteTask/<task_id>', methods=['DELETE'])
@jwt_required
def delete_task(task_id):    
    # Check if task exists and belongs to the user
    task = current_app.db.tasks.find_one({'_id': ObjectId(task_id), 'user_id': request.user_id})
    if not task:
        return jsonify({'error': 'Task not found or access denied'}), 404
    
    # Delete the task
    try:
        current_app.db.tasks.delete_one({'_id': ObjectId(task_id)})
        return jsonify({'message': 'Task deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Route to update a task's details (protected route)
@bp.route('/updateTaskDetails/<task_id>', methods=['PATCH'])
@jwt_required
def update_task_details(task_id):
    data = request.json

    new_title = data.get('title')
    new_description = data.get('description')
    new_due_date = data.get('due_date')

    # Validate that at least one field is provided for update
    if not (new_title or new_description or new_due_date):
        return jsonify({'error': 'At least one of title, description, or due_date must be provided'}), 400

    # Check if task exists and belongs to the user
    task = current_app.db.tasks.find_one({'_id': ObjectId(task_id), 'user_id': request.user_id})
    if not task:
        return jsonify({'error': 'Task not found or access denied'}), 404

    # Prepare the update fields dynamically based on provided data
    update_data = {}
    if new_title:
        update_data['title'] = new_title
    if new_description:
        update_data['description'] = new_description
    if new_due_date:
        update_data['due_date'] = new_due_date

    # Update the task details
    try:
        current_app.db.tasks.update_one(
            {'_id': ObjectId(task_id)},
            {'$set': update_data}
        )
        return jsonify({'message': 'Task details updated successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

        