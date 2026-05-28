import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, send_from_directory
from flask_cors import CORS
from database.db import init_db, seed_admin
from routes.auth_routes import auth_bp
from routes.message_routes import message_bp
from routes.admin_routes import admin_bp

app = Flask(__name__, static_folder='../frontend', static_url_path='')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')

CORS(app, resources={r"/api/*": {"origins": "*"}})

app.register_blueprint(auth_bp)
app.register_blueprint(message_bp)
app.register_blueprint(admin_bp)

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'frontend')

@app.route('/')
def serve_index():
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/<path:path>')
def serve_frontend(path):
    file_path = os.path.join(FRONTEND_DIR, path)
    if os.path.isfile(file_path):
        return send_from_directory(FRONTEND_DIR, path)
    if path.endswith('.html'):
        return send_from_directory(FRONTEND_DIR, path)
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/api/health')
def health():
    return {'status': 'ok', 'message': 'AI Analyzer API is running'}

if __name__ == '__main__':
    print("Initializing database...")
    init_db()
    seed_admin()
    print("Database initialized successfully!")
    print("Starting server on http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
