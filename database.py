import sqlite3
import os
from cryptography.fernet import Fernet

# Generate a key and instantiate a Fernet instance
# In a real app, this key should be stored securely, e.g., as an environment variable
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    ENCRYPTION_KEY = Fernet.generate_key().decode()
    print(f"Generated new encryption key. Please set this in your environment variables: ENCRYPTION_KEY={ENCRYPTION_KEY}")

cipher_suite = Fernet(ENCRYPTION_KEY.encode())

def encrypt_token(token: str) -> str:
    """Encrypts a token."""
    return cipher_suite.encrypt(token.encode()).decode()

def decrypt_token(encrypted_token: str) -> str:
    """Decrypts a token."""
    return cipher_suite.decrypt(encrypted_token.encode()).decode()

def init_db():
    conn = sqlite3.connect('summaries.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS summaries (
            topic TEXT PRIMARY KEY,
            summary TEXT,
            ui_summary TEXT,
            timestamp REAL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            created_at REAL DEFAULT (strftime('%s', 'now'))
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS connected_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            platform TEXT NOT NULL,
            access_token TEXT NOT NULL,
            refresh_token TEXT,
            expires_at REAL,
            scope TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    conn.commit()
    conn.close()

def get_summary_from_db(topic):
    conn = sqlite3.connect('summaries.db')
    c = conn.cursor()
    c.execute("SELECT summary, ui_summary, timestamp FROM summaries WHERE topic=?", (topic,))
    result = c.fetchone()
    conn.close()
    return result

def save_summary_to_db(topic, summary, ui_summary, timestamp):
    conn = sqlite3.connect('summaries.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO summaries (topic, summary, ui_summary, timestamp) VALUES (?, ?, ?, ?)",
              (topic, summary, ui_summary, timestamp))
    conn.commit()
    conn.close()

def create_user(username: str) -> int:
    """Creates a new user and returns the user ID."""
    conn = sqlite3.connect('summaries.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username) VALUES (?)", (username,))
        user_id = c.lastrowid
        conn.commit()
    except sqlite3.IntegrityError:
        c.execute("SELECT id FROM users WHERE username=?", (username,))
        user_id = c.fetchone()[0]
    finally:
        conn.close()
    return user_id

def create_connected_account(user_id: int, platform: str, access_token: str, refresh_token: str, expires_at: float, scope: str):
    """Creates a new connected account."""
    encrypted_access_token = encrypt_token(access_token)
    encrypted_refresh_token = encrypt_token(refresh_token) if refresh_token else None

    conn = sqlite3.connect('summaries.db')
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO connected_accounts
        (user_id, platform, access_token, refresh_token, expires_at, scope)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, platform, encrypted_access_token, encrypted_refresh_token, expires_at, scope))
    conn.commit()
    conn.close()

def get_connected_account(user_id: int, platform: str):
    """Gets a connected account for a user."""
    conn = sqlite3.connect('summaries.db')
    c = conn.cursor()
    c.execute("SELECT access_token, refresh_token, expires_at FROM connected_accounts WHERE user_id=? AND platform=?", (user_id, platform))
    result = c.fetchone()
    conn.close()
    if result:
        access_token, refresh_token, expires_at = result
        return {
            "access_token": decrypt_token(access_token),
            "refresh_token": decrypt_token(refresh_token) if refresh_token else None,
            "expires_at": expires_at,
        }
    return None
