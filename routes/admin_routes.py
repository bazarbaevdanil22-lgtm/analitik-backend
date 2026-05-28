from flask import Blueprint, request, jsonify
from database.db import (
    get_all_users, update_user_role, delete_user_by_id,
    get_admin_stats, log_activity, get_activity_logs,
    get_all_settings, set_setting, get_setting,
    delete_message_by_id, get_messages
)
from routes.auth_routes import admin_required

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/api/admin/stats', methods=['GET'])
@admin_required
def admin_stats(current_user):
    try:
        stats = get_admin_stats()
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({'message': f'Failed to fetch stats: {str(e)}'}), 500


@admin_bp.route('/api/admin/users', methods=['GET'])
@admin_required
def admin_users(current_user):
    search = request.args.get('search', '')
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)
    try:
        users, total = get_all_users(search=search, limit=limit, offset=offset)
        return jsonify({'users': users, 'total': total}), 200
    except Exception as e:
        return jsonify({'message': f'Failed to fetch users: {str(e)}'}), 500


@admin_bp.route('/api/admin/users/<int:user_id>/role', methods=['PUT'])
@admin_required
def admin_update_role(current_user, user_id):
    data = request.get_json()
    if not data or 'role' not in data:
        return jsonify({'message': 'Role is required'}), 400
    role = data['role']
    if role not in ('user', 'admin', 'moderator'):
        return jsonify({'message': 'Invalid role. Must be user, admin, or moderator'}), 400
    try:
        update_user_role(user_id, role)
        log_activity(
            current_user['id'], current_user['username'],
            'update_role', f'Changed user {user_id} role to {role}',
            request.remote_addr
        )
        return jsonify({'message': 'Role updated successfully'}), 200
    except Exception as e:
        return jsonify({'message': f'Failed to update role: {str(e)}'}), 500


@admin_bp.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@admin_required
def admin_delete_user(current_user, user_id):
    if user_id == current_user['id']:
        return jsonify({'message': 'Cannot delete yourself'}), 400
    try:
        delete_user_by_id(user_id)
        log_activity(
            current_user['id'], current_user['username'],
            'delete_user', f'Deleted user {user_id}',
            request.remote_addr
        )
        return jsonify({'message': 'User deleted successfully'}), 200
    except Exception as e:
        return jsonify({'message': f'Failed to delete user: {str(e)}'}), 500


@admin_bp.route('/api/admin/messages', methods=['GET'])
@admin_required
def admin_messages(current_user):
    sentiment = request.args.get('sentiment', 'all')
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)
    try:
        messages = get_messages(sentiment_filter=sentiment, limit=limit + offset)
        messages = messages[offset:offset + limit]
        return jsonify({
            'messages': messages,
            'total': len(messages)
        }), 200
    except Exception as e:
        return jsonify({'message': f'Failed to fetch messages: {str(e)}'}), 500


@admin_bp.route('/api/admin/messages/<int:message_id>', methods=['DELETE'])
@admin_required
def admin_delete_message(current_user, message_id):
    try:
        delete_message_by_id(message_id)
        log_activity(
            current_user['id'], current_user['username'],
            'delete_message', f'Deleted message {message_id}',
            request.remote_addr
        )
        return jsonify({'message': 'Message deleted successfully'}), 200
    except Exception as e:
        return jsonify({'message': f'Failed to delete message: {str(e)}'}), 500


@admin_bp.route('/api/admin/activity', methods=['GET'])
@admin_required
def admin_activity(current_user):
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)
    try:
        logs, total = get_activity_logs(limit=limit, offset=offset)
        return jsonify({'logs': logs, 'total': total}), 200
    except Exception as e:
        return jsonify({'message': f'Failed to fetch activity logs: {str(e)}'}), 500


@admin_bp.route('/api/admin/settings', methods=['GET'])
@admin_required
def admin_get_settings(current_user):
    try:
        settings = get_all_settings()
        return jsonify({'settings': settings}), 200
    except Exception as e:
        return jsonify({'message': f'Failed to fetch settings: {str(e)}'}), 500


@admin_bp.route('/api/admin/settings', methods=['PUT'])
@admin_required
def admin_update_settings(current_user):
    data = request.get_json()
    if not data:
        return jsonify({'message': 'No data provided'}), 400
    try:
        for key, value in data.items():
            set_setting(key, str(value))
        log_activity(
            current_user['id'], current_user['username'],
            'update_settings', f'Updated {len(data)} settings',
            request.remote_addr
        )
        return jsonify({'message': 'Settings updated successfully'}), 200
    except Exception as e:
        return jsonify({'message': f'Failed to update settings: {str(e)}'}), 500


@admin_bp.route('/api/admin/check', methods=['GET'])
@admin_required
def admin_check(current_user):
    return jsonify({
        'is_admin': True,
        'user': {
            'id': current_user['id'],
            'username': current_user['username'],
            'email': current_user['email'],
            'role': current_user['role'],
        }
    }), 200
