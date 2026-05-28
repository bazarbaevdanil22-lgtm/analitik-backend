import bcrypt
import jwt
import datetime
from flask import Blueprint, request, jsonify, current_app
from functools import wraps
from database.db import add_user, get_user_by_username, get_user_by_id, update_user, update_password, log_activity

auth_bp = Blueprint('auth', __name__)

def generate_token(user_id, username, role='user'):
    payload = {
        'user_id': user_id,
        'username': username,
        'role': role,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7),
        'iat': datetime.datetime.utcnow(),
    }
    return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        try:
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = get_user_by_id(data['user_id'])
            if not current_user:
                return jsonify({'message': 'User not found'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token'}), 401
        return f(current_user, *args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        try:
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = get_user_by_id(data['user_id'])
            if not current_user:
                return jsonify({'message': 'User not found'}), 401
            if current_user['role'] != 'admin':
                return jsonify({'message': 'Admin access required'}), 403
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token'}), 401
        return f(current_user, *args, **kwargs)
    return decorated

@auth_bp.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data:
        return jsonify({'message': 'No data provided'}), 400

    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '')

    if not username or not email or not password:
        return jsonify({'message': 'All fields are required'}), 400

    if len(username) < 3:
        return jsonify({'message': 'Username must be at least 3 characters'}), 400

    if len(password) < 6:
        return jsonify({'message': 'Password must be at least 6 characters'}), 400

    if '@' not in email:
        return jsonify({'message': 'Invalid email format'}), 400

    existing = get_user_by_username(username)
    if existing:
        return jsonify({'message': 'Username already exists'}), 409

    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    try:
        user_id = add_user(username, email, password_hash)
        role = 'user'
        token = generate_token(user_id, username, role)
        log_activity(user_id, username, 'register', 'User registered', request.remote_addr)
        return jsonify({
            'message': 'User registered successfully',
            'token': token,
            'user': {'id': user_id, 'username': username, 'email': email, 'role': role}
        }), 201
    except Exception as e:
        return jsonify({'message': f'Registration failed: {str(e)}'}), 500

@auth_bp.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data:
        return jsonify({'message': 'No data provided'}), 400

    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'message': 'Username and password are required'}), 400

    user = get_user_by_username(username)
    if not user:
        return jsonify({'message': 'Invalid credentials'}), 401

    if not bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
        return jsonify({'message': 'Invalid credentials'}), 401

    token = generate_token(user['id'], user['username'], user['role'])
    return jsonify({
        'message': 'Login successful',
        'token': token,
        'user': {'id': user['id'], 'username': user['username'], 'email': user['email'], 'role': user['role']}
    }), 200

@auth_bp.route('/api/profile', methods=['GET'])
@token_required
def get_profile(current_user):
    return jsonify({
        'user': {
            'id': current_user['id'],
            'username': current_user['username'],
            'email': current_user['email'],
            'role': current_user['role'],
            'created_at': current_user['created_at'],
        }
    }), 200

@auth_bp.route('/api/profile', methods=['PUT'])
@token_required
def update_profile(current_user):
    data = request.get_json()
    if not data:
        return jsonify({'message': 'No data provided'}), 400

    username = data.get('username', '').strip()
    email = data.get('email', '').strip()

    if not username or not email:
        return jsonify({'message': 'Username and email are required'}), 400

    if len(username) < 3:
        return jsonify({'message': 'Username must be at least 3 characters'}), 400

    if '@' not in email:
        return jsonify({'message': 'Invalid email format'}), 400

    if username != current_user['username']:
        existing = get_user_by_username(username)
        if existing:
            return jsonify({'message': 'Username already taken'}), 409

    try:
        update_user(current_user['id'], username, email)
        new_token = generate_token(current_user['id'], username, current_user['role'])
        return jsonify({
            'message': 'Profile updated successfully',
            'user': {
                'id': current_user['id'],
                'username': username,
                'email': email,
                'role': current_user['role'],
            },
            'token': new_token,
        }), 200
    except Exception as e:
        return jsonify({'message': f'Update failed: {str(e)}'}), 500

@auth_bp.route('/api/profile/change-password', methods=['PUT'])
@token_required
def change_password(current_user):
    data = request.get_json()
    if not data:
        return jsonify({'message': 'No data provided'}), 400

    current_password = data.get('current_password', '')
    new_password = data.get('new_password', '')
    confirm_password = data.get('confirm_password', '')

    if not current_password or not new_password or not confirm_password:
        return jsonify({'message': 'All password fields are required'}), 400

    if new_password != confirm_password:
        return jsonify({'message': 'New passwords do not match'}), 400

    if len(new_password) < 6:
        return jsonify({'message': 'New password must be at least 6 characters'}), 400

    if not bcrypt.checkpw(current_password.encode('utf-8'), current_user['password_hash'].encode('utf-8')):
        return jsonify({'message': 'Current password is incorrect'}), 401

    new_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    try:
        update_password(current_user['id'], new_hash)
        return jsonify({'message': 'Password changed successfully'}), 200
    except Exception as e:
        return jsonify({'message': f'Password change failed: {str(e)}'}), 500

@auth_bp.route('/api/me', methods=['GET'])
@token_required
def get_me(current_user):
    return jsonify({
        'user': {
            'id': current_user['id'],
            'username': current_user['username'],
            'email': current_user['email'],
            'role': current_user['role'],
        }
    }), 200
