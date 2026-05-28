import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data', 'app.db')

def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            emotion TEXT,
            emotion_score REAL,
            sentiment TEXT,
            sentiment_score REAL,
            complaint_category TEXT,
            category TEXT,
            priority TEXT,
            keywords TEXT,
            summary TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            action TEXT NOT NULL,
            details TEXT,
            ip_address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    ''')

    try:
        cursor.execute('ALTER TABLE users ADD COLUMN role TEXT DEFAULT \'user\'')
    except Exception:
        pass

    for col in ['category', 'priority', 'keywords', 'summary']:
        try:
            cursor.execute(f'ALTER TABLE messages ADD COLUMN {col} TEXT')
        except Exception:
            pass

    conn.commit()
    conn.close()

def seed_admin():
    import bcrypt
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        pw_hash = bcrypt.hashpw('27032005'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cursor.execute("INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, 'admin')",
                       ('admin', 'admin@mail.com', pw_hash))
        conn.commit()
        print("Admin user created: admin / 27032005")
    conn.close()

def add_user(username, email, password_hash):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
                   (username, email, password_hash))
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()
    return user_id

def get_user_by_username(username):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    conn.close()
    return user

def get_user_by_id(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def update_user(user_id, username, email):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET username = ?, email = ? WHERE id = ?',
                   (username, email, user_id))
    conn.commit()
    conn.close()

def update_password(user_id, new_password_hash):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET password_hash = ? WHERE id = ?',
                   (new_password_hash, user_id))
    conn.commit()
    conn.close()

def add_message(user_id, text, emotion, emotion_score, sentiment, sentiment_score, complaint_category,
                category=None, priority=None, keywords=None, summary=None):
    conn = get_connection()
    cursor = conn.cursor()
    keywords_json = ','.join(keywords) if keywords else None
    cursor.execute('''
        INSERT INTO messages (user_id, text, emotion, emotion_score, sentiment, sentiment_score,
                              complaint_category, category, priority, keywords, summary)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, text, emotion, emotion_score, sentiment, sentiment_score,
          complaint_category, category, priority, keywords_json, summary))
    conn.commit()
    msg_id = cursor.lastrowid
    conn.close()
    return msg_id

def get_messages(user_id=None, sentiment_filter=None, limit=50):
    conn = get_connection()
    cursor = conn.cursor()
    query = '''
        SELECT m.id, m.text, m.emotion, m.emotion_score, m.sentiment, m.sentiment_score,
               m.complaint_category, m.category, m.priority, m.keywords, m.summary,
               m.created_at, u.username
        FROM messages m JOIN users u ON m.user_id = u.id
        WHERE 1=1
    '''
    params = []
    if user_id:
        query += ' AND m.user_id = ?'
        params.append(user_id)
    if sentiment_filter and sentiment_filter != 'all':
        query += ' AND m.sentiment = ?'
        params.append(sentiment_filter)
    query += ' ORDER BY m.created_at DESC LIMIT ?'
    params.append(limit)
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_all_users(search=None, limit=50, offset=0):
    conn = get_connection()
    cursor = conn.cursor()
    query = 'SELECT id, username, email, role, created_at FROM users WHERE 1=1'
    params = []
    if search:
        query += ' AND (username LIKE ? OR email LIKE ?)'
        params.extend([f'%{search}%', f'%{search}%'])
    query += ' ORDER BY created_at DESC LIMIT ? OFFSET ?'
    params.extend([limit, offset])
    cursor.execute(query, params)
    rows = cursor.fetchall()
    cursor.execute('SELECT COUNT(*) as total FROM users' + (f' WHERE username LIKE ? OR email LIKE ?' if search else ''), params[:2] if search else [])
    total = cursor.fetchone()['total']
    conn.close()
    return [dict(row) for row in rows], total

def update_user_role(user_id, role):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET role = ? WHERE id = ?', (role, user_id))
    conn.commit()
    conn.close()

def delete_user_by_id(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM messages WHERE user_id = ?', (user_id,))
    cursor.execute('DELETE FROM activity_logs WHERE user_id = ?', (user_id,))
    cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()

def get_admin_stats():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) as total FROM users')
    total_users = cursor.fetchone()['total']
    cursor.execute("SELECT COUNT(*) as total FROM users WHERE role = 'admin'")
    total_admins = cursor.fetchone()['total']
    cursor.execute('SELECT COUNT(*) as total FROM messages')
    total_messages = cursor.fetchone()['total']
    cursor.execute('SELECT COUNT(*) as total FROM activity_logs')
    total_activities = cursor.fetchone()['total']
    cursor.execute('SELECT COUNT(*) as total FROM messages WHERE sentiment = \'positive\'')
    pos_count = cursor.fetchone()['total']
    cursor.execute('SELECT COUNT(*) as total FROM messages WHERE sentiment = \'negative\'')
    neg_count = cursor.fetchone()['total']
    cursor.execute('SELECT COUNT(*) as total FROM messages WHERE sentiment = \'neutral\'')
    neu_count = cursor.fetchone()['total']
    cursor.execute('SELECT DATE(created_at) as date, COUNT(*) as count FROM messages GROUP BY DATE(created_at) ORDER BY date DESC LIMIT 7')
    daily = [dict(row) for row in cursor.fetchall()]
    daily.reverse()
    conn.close()
    return {
        'total_users': total_users,
        'total_admins': total_admins,
        'total_messages': total_messages,
        'total_activities': total_activities,
        'positive': pos_count,
        'negative': neg_count,
        'neutral': neu_count,
        'daily': daily,
    }

def log_activity(user_id, username, action, details=None, ip_address=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO activity_logs (user_id, username, action, details, ip_address) VALUES (?, ?, ?, ?, ?)',
                   (user_id, username, action, details, ip_address))
    conn.commit()
    conn.close()

def get_activity_logs(limit=50, offset=0):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM activity_logs ORDER BY created_at DESC LIMIT ? OFFSET ?', (limit, offset))
    rows = cursor.fetchall()
    cursor.execute('SELECT COUNT(*) as total FROM activity_logs')
    total = cursor.fetchone()['total']
    conn.close()
    return [dict(row) for row in rows], total

def get_setting(key):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
    row = cursor.fetchone()
    conn.close()
    return row['value'] if row else None

def set_setting(key, value):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
    conn.commit()
    conn.close()

def get_all_settings():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM settings')
    rows = cursor.fetchall()
    conn.close()
    return {row['key']: row['value'] for row in rows}

def delete_message_by_id(message_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM messages WHERE id = ?', (message_id,))
    conn.commit()
    conn.close()

def get_stats():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT COUNT(*) as total FROM messages')
    total = cursor.fetchone()['total']

    cursor.execute('''
        SELECT sentiment, COUNT(*) as count
        FROM messages GROUP BY sentiment
    ''')
    sentiment_counts = {row['sentiment']: row['count'] for row in cursor.fetchall()}

    cursor.execute('''
        SELECT emotion, COUNT(*) as count
        FROM messages GROUP BY emotion
        ORDER BY count DESC
    ''')
    emotion_counts = [dict(row) for row in cursor.fetchall()]

    cursor.execute('''
        SELECT complaint_category, COUNT(*) as count
        FROM messages GROUP BY complaint_category
        ORDER BY count DESC
    ''')
    category_counts = [dict(row) for row in cursor.fetchall()]

    cursor.execute('''
        SELECT DATE(created_at) as date, COUNT(*) as count
        FROM messages
        GROUP BY DATE(created_at)
        ORDER BY date
    ''')
    daily_counts = [dict(row) for row in cursor.fetchall()]

    cursor.execute('SELECT AVG(sentiment_score) as avg_score FROM messages')
    avg_row = cursor.fetchone()
    avg_sentiment = avg_row['avg_score'] if avg_row['avg_score'] else 0

    conn.close()

    pos = sentiment_counts.get('positive', 0)
    neg = sentiment_counts.get('negative', 0)
    neu = sentiment_counts.get('neutral', 0)

    return {
        'total': total,
        'positive': pos,
        'negative': neg,
        'neutral': neu,
        'positive_pct': round(pos / total * 100, 1) if total else 0,
        'negative_pct': round(neg / total * 100, 1) if total else 0,
        'neutral_pct': round(neu / total * 100, 1) if total else 0,
        'avg_sentiment': round(avg_sentiment, 2),
        'emotions': emotion_counts,
        'categories': category_counts,
        'daily': daily_counts,
    }
