from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
import sqlite3
import json
import uuid

class Priority(Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"

class Status(Enum):
    TODO = "To Do"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    BLOCKED = "Blocked"

class Task:
    def __init__(self, title: str, description: str, created_by, 
                 priority: Priority = Priority.MEDIUM, due_date: Optional[datetime] = None,
                 assigned_to=None, status: Status = Status.TODO):
        
        # Validate inputs
        if not title or len(title.strip()) == 0:
            raise ValueError("Title cannot be empty")
        if len(title.strip()) > 100:
            raise ValueError("Title cannot exceed 100 characters")
        
        if not description or len(description.strip()) == 0:
            raise ValueError("Description cannot be empty")
        if len(description.strip()) > 100:
            raise ValueError("Description cannot exceed 100 characters")
        
        if due_date and due_date <= datetime.now():
            raise ValueError("Due date must be in the future")
        
        # Initialize properties
        self.task_id = self._generate_task_id()
        self.title = title.strip()
        self.description = description.strip()
        self.created_by = created_by
        self.assigned_to = assigned_to
        self.priority = priority
        self.status = status
        self.due_date = due_date
        self.tags = []
        self.notes = ""
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
    
    def _generate_task_id(self) -> str:
        """Generate unique task ID"""
        return f"task_{uuid.uuid4().hex[:8]}"
    
    def update_title(self, title: str) -> None:
        """Update task title with validation"""
        if not title or len(title.strip()) == 0:
            raise ValueError("Title cannot be empty")
        if len(title.strip()) > 100:
            raise ValueError("Title cannot exceed 100 characters")
        
        self.title = title.strip()
        self.updated_at = datetime.now()
    
    def update_description(self, description: str) -> None:
        """Update task description with validation"""
        if not description or len(description.strip()) == 0:
            raise ValueError("Description cannot be empty")
        if len(description.strip()) > 100:
            raise ValueError("Description cannot exceed 100 characters")
        
        self.description = description.strip()
        self.updated_at = datetime.now()
    
    def update_priority(self, priority: Priority) -> None:
        """Update task priority"""
        self.priority = priority
        self.updated_at = datetime.now()
    
    def update_status(self, status: Status) -> None:
        """Update task status"""
        self.status = status
        self.updated_at = datetime.now()
    
    def update_due_date(self, due_date: datetime) -> None:
        """Update due date with validation"""
        if due_date <= datetime.now():
            raise ValueError("Due date must be in the future")
        
        self.due_date = due_date
        self.updated_at = datetime.now()
    
    def add_note(self, note: str) -> None:
        """Add notes with character limit validation"""
        if len(note) > 1000:
            raise ValueError("Notes cannot exceed 1000 characters")
        
        self.notes = note
        self.updated_at = datetime.now()
    
    def add_tag(self, tag: str) -> None:
        """Add hashtag to task"""
        clean_tag = f"#{tag.strip().lstrip('#')}"
        if clean_tag not in self.tags:
            self.tags.append(clean_tag)
            self.updated_at = datetime.now()
    
    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the task"""
        clean_tag = f"#{tag.strip().lstrip('#')}"
        if clean_tag in self.tags:
            self.tags.remove(clean_tag)
            self.updated_at = datetime.now()
    
    def assign_to_user(self, user) -> None:
        """Assign task to a user"""
        self.assigned_to = user
        self.updated_at = datetime.now()
    
    def save(self, db_path: str = "task_manager.db") -> None:
        """Save task to database"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO tasks 
            (task_id, title, description, created_by_id, assigned_to_id, 
             priority, status, due_date, tags, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            self.task_id,
            self.title,
            self.description,
            self.created_by.user_id,
            self.assigned_to.user_id if self.assigned_to else None,
            self.priority.value,
            self.status.value,
            self.due_date.isoformat() if self.due_date else None,
            json.dumps(self.tags),
            self.notes,
            self.created_at.isoformat(),
            self.updated_at.isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    @classmethod
    def find_by_id(cls, task_id: str, db_path: str = "task_manager.db") -> Optional['Task']:
        """Find task by ID from database"""
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM tasks WHERE task_id = ?', (task_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return cls._create_from_row(row, db_path)
        return None
    
    @classmethod
    def find_all(cls, db_path: str = "task_manager.db") -> List['Task']:
        """Get all tasks from database"""
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM tasks ORDER BY created_at DESC')
        rows = cursor.fetchall()
        conn.close()
        
        return [cls._create_from_row(row, db_path) for row in rows]
    
    @classmethod
    def find_by_creator(cls, user_id: str, db_path: str = "task_manager.db") -> List['Task']:
        """Find tasks created by a user"""
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM tasks WHERE created_by_id = ? ORDER BY created_at DESC', (user_id,))
        rows = cursor.fetchall()
        conn.close()
        
        return [cls._create_from_row(row, db_path) for row in rows]
    
    @classmethod
    def find_by_assignee(cls, user_id: str, db_path: str = "task_manager.db") -> List['Task']:
        """Find tasks assigned to a user"""
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM tasks WHERE assigned_to_id = ? ORDER BY created_at DESC', (user_id,))
        rows = cursor.fetchall()
        conn.close()
        
        return [cls._create_from_row(row, db_path) for row in rows]
    
    @classmethod
    def find_by_status(cls, status: Status, db_path: str = "task_manager.db") -> List['Task']:
        """Find tasks by status"""
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM tasks WHERE status = ? ORDER BY created_at DESC', (status.value,))
        rows = cursor.fetchall()
        conn.close()
        
        return [cls._create_from_row(row, db_path) for row in rows]
    
    @classmethod
    def find_by_priority(cls, priority: Priority, db_path: str = "task_manager.db") -> List['Task']:
        """Find tasks by priority"""
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM tasks WHERE priority = ? ORDER BY created_at DESC', (priority.value,))
        rows = cursor.fetchall()
        conn.close()
        
        return [cls._create_from_row(row, db_path) for row in rows]
    
    @classmethod
    def _create_from_row(cls, row, db_path: str) -> 'Task':
        """Helper method to create Task from database row"""
        # Import here to avoid circular imports
        from user import User
        
        # Get users
        created_by = User.find_by_id(row['created_by_id'], db_path)
        assigned_to = User.find_by_id(row['assigned_to_id'], db_path) if row['assigned_to_id'] else None
        
        # Parse due_date
        due_date = datetime.fromisoformat(row['due_date']) if row['due_date'] else None
        
        # Create task
        task = cls(
            title=row['title'],
            description=row['description'],
            created_by=created_by,
            priority=Priority(row['priority']),
            due_date=due_date,
            assigned_to=assigned_to,
            status=Status(row['status'])
        )
        
        # Set additional properties
        task.task_id = row['task_id']
        task.tags = json.loads(row['tags']) if row['tags'] else []
        task.notes = row['notes'] or ""
        task.created_at = datetime.fromisoformat(row['created_at'])
        task.updated_at = datetime.fromisoformat(row['updated_at'])
        
        return task
    
    def delete(self, db_path: str = "task_manager.db") -> None:
        """Delete task from database"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM tasks WHERE task_id = ?', (self.task_id,))
        
        conn.commit()
        conn.close()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary for JSON serialization"""
        return {
            'task_id': self.task_id,
            'title': self.title,
            'description': self.description,
            'created_by': self.created_by.to_dict() if self.created_by else None,
            'assigned_to': self.assigned_to.to_dict() if self.assigned_to else None,
            'priority': self.priority.value,
            'status': self.status.value,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'tags': self.tags,
            'notes': self.notes,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], db_path: str = "task_manager.db") -> 'Task':
        """Create Task instance from dictionary"""
        from user import User
        
        # Get users
        created_by = User.find_by_id(data['created_by_id'], db_path) if 'created_by_id' in data else None
        assigned_to = User.find_by_id(data['assigned_to_id'], db_path) if data.get('assigned_to_id') else None
        
        # Parse due_date
        due_date = datetime.fromisoformat(data['due_date']) if data.get('due_date') else None
        
        # Create task
        task = cls(
            title=data['title'],
            description=data['description'],
            created_by=created_by,
            priority=Priority(data.get('priority', Priority.MEDIUM.value)),
            due_date=due_date,
            assigned_to=assigned_to,
            status=Status(data.get('status', Status.TODO.value))
        )
        
        # Set additional properties if they exist
        if 'task_id' in data:
            task.task_id = data['task_id']
        if 'tags' in data:
            task.tags = data['tags']
        if 'notes' in data:
            task.notes = data['notes']
        if 'created_at' in data:
            task.created_at = datetime.fromisoformat(data['created_at'])
        if 'updated_at' in data:
            task.updated_at = datetime.fromisoformat(data['updated_at'])
        
        return task
    
    def __str__(self) -> str:
        status_emoji = {"To Do": "📋", "In Progress": "⏳", "Completed": "✅", "Blocked": "🚫"}
        priority_emoji = {"Low": "🟢", "Medium": "🟡", "High": "🔴"}
        
        assigned_info = f" → {self.assigned_to.name}" if self.assigned_to else " (Unassigned)"
        return f"{status_emoji.get(self.status.value, '📋')} {self.title} {priority_emoji.get(self.priority.value, '🟡')} (by {self.created_by.name if self.created_by else 'Unknown'}){assigned_info}"
    
    def __repr__(self) -> str:
        return f"Task(id='{self.task_id}', title='{self.title}', status='{self.status.value}', priority='{self.priority.value}')"
    
    def __eq__(self, other) -> bool:
        """Check equality based on task_id"""
        if not isinstance(other, Task):
            return False
        return self.task_id == other.task_id

# Database setup function for tasks table
def setup_tasks_table(db_path: str = "task_manager.db"):
    """Create the tasks table if it doesn't exist"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            created_by_id TEXT NOT NULL,
            assigned_to_id TEXT,
            priority TEXT NOT NULL,
            status TEXT NOT NULL,
            due_date TEXT,
            tags TEXT,
            notes TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (created_by_id) REFERENCES users (user_id),
            FOREIGN KEY (assigned_to_id) REFERENCES users (user_id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"Tasks table setup complete: {db_path}")