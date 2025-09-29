from datetime import datetime
from typing import Optional, List
import sqlite3

class User:
    def __init__(self, user_id: str, name: str, email: str):
        self.user_id = user_id
        self.name = name
        self.email = email
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
    
    def update_name(self, name: str) -> None:
        """Update the user's name"""
        self.name = name
        self.updated_at = datetime.now()
    
    def update_email(self, email: str) -> None:
        """Update the user's email"""
        self.email = email
        self.updated_at = datetime.now()
    
    def save(self, db_path: str = "task_manager.db") -> None:
        """Save user to database"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO users 
            (user_id, name, email, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            self.user_id,
            self.name,
            self.email,
            self.created_at.isoformat(),
            self.updated_at.isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    @classmethod
    def find_by_id(cls, user_id: str, db_path: str = "task_manager.db") -> Optional['User']:
        """Find user by ID from database"""
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Returns rows as dictionaries
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            user = cls(row['user_id'], row['name'], row['email'])
            user.created_at = datetime.fromisoformat(row['created_at'])
            user.updated_at = datetime.fromisoformat(row['updated_at'])
            return user
        return None
    
    @classmethod
    def find_all(cls, db_path: str = "task_manager.db") -> List['User']:
        """Get all users from database"""
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users ORDER BY created_at DESC')
        rows = cursor.fetchall()
        conn.close()
        
        users = []
        for row in rows:
            user = cls(row['user_id'], row['name'], row['email'])
            user.created_at = datetime.fromisoformat(row['created_at'])
            user.updated_at = datetime.fromisoformat(row['updated_at'])
            users.append(user)
        
        return users
    
    @classmethod
    def find_by_email(cls, email: str, db_path: str = "task_manager.db") -> Optional['User']:
        """Find user by email from database"""
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            user = cls(row['user_id'], row['name'], row['email'])
            user.created_at = datetime.fromisoformat(row['created_at'])
            user.updated_at = datetime.fromisoformat(row['updated_at'])
            return user
        return None
    
    def delete(self, db_path: str = "task_manager.db") -> None:
        """Delete user from database"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM users WHERE user_id = ?', (self.user_id,))
        
        conn.commit()
        conn.close()
    
    def to_dict(self) -> dict:
        """Convert user to dictionary for JSON serialization"""
        return {
            'user_id': self.user_id,
            'name': self.name,
            'email': self.email,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'User':
        """Create User instance from dictionary"""
        user = cls(
            user_id=data['user_id'],
            name=data['name'],
            email=data['email']
        )
        if 'created_at' in data:
            user.created_at = datetime.fromisoformat(data['created_at'])
        if 'updated_at' in data:
            user.updated_at = datetime.fromisoformat(data['updated_at'])
        return user
    
    def __str__(self) -> str:
        return f"User(id={self.user_id}, name={self.name}, email={self.email})"
    
    def __eq__(self, other) -> bool:
        """Check equality based on user_id"""
        if not isinstance(other, User):
            return False
        return self.user_id == other.user_id

# Database setup function
def setup_database(db_path: str = "task_manager.db"):
    """Create the users table if it doesn't exist"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"Database setup complete: {db_path}")