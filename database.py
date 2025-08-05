import sqlite3

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
