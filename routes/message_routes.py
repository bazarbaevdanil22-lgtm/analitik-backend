from flask import Blueprint, request, jsonify
from database.db import add_message, get_messages, get_stats
from routes.auth_routes import token_required
from ai.analyzer import analyze_full

message_bp = Blueprint('messages', __name__)

@message_bp.route('/api/analyze', methods=['POST'])
@token_required
def analyze_message(current_user):
    data = request.get_json()
    if not data or not data.get('text'):
        return jsonify({'message': 'Text is required'}), 400

    text = data['text'].strip()
    if len(text) < 2:
        return jsonify({'message': 'Text must be at least 2 characters'}), 400

    try:
        result = analyze_full(text)
        msg_id = add_message(
            user_id=current_user['id'],
            text=result['text'],
            emotion=result['emotion'],
            emotion_score=result['emotion_score'],
            sentiment=result['sentiment'],
            sentiment_score=result['sentiment_score'],
            complaint_category=result['complaint_category'],
            category=result['category'],
            priority=result['priority'],
            keywords=result['keywords'],
            summary=result['summary'],
        )
        result['id'] = msg_id
        result['user_id'] = current_user['id']
        return jsonify(result), 201
    except Exception as e:
        return jsonify({'message': f'Analysis failed: {str(e)}'}), 500


@message_bp.route('/api/messages', methods=['GET'])
@token_required
def get_messages_route(current_user):
    sentiment = request.args.get('sentiment', 'all')
    limit = request.args.get('limit', 50, type=int)
    try:
        messages = get_messages(
            user_id=current_user['id'],
            sentiment_filter=sentiment,
            limit=limit
        )
        return jsonify({'messages': messages}), 200
    except Exception as e:
        return jsonify({'message': f'Failed to fetch messages: {str(e)}'}), 500


@message_bp.route('/api/stats', methods=['GET'])
@token_required
def get_stats_route(current_user):
    try:
        stats = get_stats()
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({'message': f'Failed to fetch stats: {str(e)}'}), 500


@message_bp.route('/api/messages/all', methods=['GET'])
@token_required
def get_all_messages_admin(current_user):
    sentiment = request.args.get('sentiment', 'all')
    limit = request.args.get('limit', 100, type=int)
    try:
        messages = get_messages(sentiment_filter=sentiment, limit=limit)
        return jsonify({'messages': messages}), 200
    except Exception as e:
        return jsonify({'message': f'Failed to fetch messages: {str(e)}'}), 500
