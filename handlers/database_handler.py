import sqlite3
import json
from langchain_core.messages import HumanMessage, AIMessage
from logger import app_logger
class DatabaseHandler:
    def __init__(self, db_path='chat_history.db'):
        self.conn = sqlite3.connect(db_path)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                content TEXT,
                is_user BOOLEAN,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chat_id) REFERENCES chats (id)
            )
        ''')
        self.conn.commit()

    def save_chat(self, title, messages):
        cursor = self.conn.cursor()
        cursor.execute('INSERT INTO chats (title) VALUES (?)', (title,))
        chat_id = cursor.lastrowid
        for message in messages:
            cursor.execute('INSERT INTO messages (chat_id, content, is_user) VALUES (?, ?, ?)',
                           (chat_id, message.content, isinstance(message, HumanMessage)))
        self.conn.commit()
        return chat_id

    def load_chat(self, chat_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT title FROM chats WHERE id = ?', (chat_id,))
        title = cursor.fetchone()[0]
        cursor.execute('SELECT DISTINCT content, is_user FROM messages WHERE chat_id = ? ORDER BY timestamp', (chat_id,))
        messages = []
        seen = set()
        for row in cursor.fetchall():
            content = row[0]
            if content not in seen:
                seen.add(content)
                messages.append(HumanMessage(content=content) if row[1] else AIMessage(content=content))
        return title, messages

    def get_chat_list(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT id, title, updated_at FROM chats ORDER BY updated_at DESC')
        return cursor.fetchall()

    def search_chats(self, query):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT DISTINCT c.id, c.title, c.updated_at
            FROM chats c
            JOIN messages m ON c.id = m.chat_id
            WHERE c.title LIKE ? OR m.content LIKE ?
            ORDER BY c.updated_at DESC
        ''', (f'%{query}%', f'%{query}%'))
        return cursor.fetchall()

    def delete_chat(self, chat_id):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM messages WHERE chat_id = ?', (chat_id,))
        cursor.execute('DELETE FROM chats WHERE id = ?', (chat_id,))
        self.conn.commit()

    def clear_all_chats(self):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM messages')
        cursor.execute('DELETE FROM chats')
        self.conn.commit()

    def close(self):
        self.conn.close()