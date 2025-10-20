# IS212---Software_Project_Management

# Task Management System

A full-stack web application for managing tasks and projects, built with Flask backend and vanilla HTML/CSS/JavaScript frontend.

## 📋 Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Database Schema](#database-schema)
- [Screenshots](#screenshots)
- [Development](#development)
- [Contributing](#contributing)

## ✨ Features

### 🔐 User Management
- User registration and authentication
- Session-based login system
- User profiles with email and name

### 📝 Task Management
- **Create Tasks**: Add new tasks with title, description, priority, and due dates
- **Edit Tasks**: Update task details and status
- **Soft Delete (Archive)**: Archive tasks instead of permanent deletion
- **Task Assignment**: Assign tasks to specific users
- **Status Tracking**: Track task progress (To Do, In Progress, Completed, Blocked)
- **Priority Levels**: Set task priorities (High, Medium, Low)

### 📊 Dashboard & Analytics
- **Personal Dashboard**: Overview of user's tasks and statistics
- **Task Statistics**: Completion rates, priority breakdown, status distribution
- **Recent Tasks**: Quick access to recently created tasks
- **Task Filtering**: View tasks by status categories

### 🗃️ Archive Management
- **Audit Trail**: Track who archived tasks and when
- **Restore Functionality**: Restore archived tasks back to active status
- **Archive Reasons**: Record why tasks were archived

### 🔒 Security Features
- **Authentication**: Session-based user authentication
- **Authorization**: Users can only edit/delete their own tasks
- **Data Validation**: Server-side input validation
- **CORS Protection**: Proper cross-origin request handling

## 🛠️ Tech Stack

### Backend
- **Flask** - Python web framework
- **SQLite** - Lightweight database
- **Flask-CORS** - Cross-origin resource sharing

### Frontend
- **HTML5** - Markup language
- **CSS3** - Styling with modern layouts and animations
- **Vanilla JavaScript** - No frameworks, pure JS
- **Fetch API** - HTTP requests to backend

### Development Tools
- **Python 3.8+** - Backend runtime
- **Virtual Environment** - Dependency isolation
- **SQLite Browser** - Database management (recommended)

## 📁 Project Structure

```
IS212---Software_Project_Management/
├── Flask/                          # Backend API server
│   ├── app.py                      # Main Flask application
│   ├── user.py                     # User model and database operations
│   ├── task.py                     # Task model and database operations
│   ├── task_manager.db             # SQLite database file
│   └── __pycache__/               # Python compiled files
├── frontend/                       # Frontend web pages
│   ├── login.html                  # User authentication page
│   ├── create_user.html           # User registration page
│   ├── dashboard.html             # Main dashboard interface
│   ├── create_task.html           # Task creation form
│   ├── edit_task.html             # Task editing interface
│   └── archive.html               # Archived tasks management
├── venv/                          # Python virtual environment
└── README.md                      # Project documentation
```

## 🚀 Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package installer)
- Web browser (Chrome, Firefox, Safari, etc.)

### Setup Steps

1. **Clone the Repository**
   ```bash
   git clone https://github.com/yourusername/IS212---Software_Project_Management.git
   cd IS212---Software_Project_Management
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Initialize Database and Start the Server**
   ```bash
   cd Flask
   python app.py
   ```
   The database will be automatically created on first run.
   Server will start on `http://localhost:5000`

5. ** Start the HTML Server**
    # In frontend directory
    cd frontend
    python -m http.server 5000

    # Access at http://localhost:5000
    # But you'll need CORS for API calls to Flask at port 5000

5. **Start the HTML Server**
   Open your browser and navigate to:
   - Login: `http://localhost:5000/login.html`

## 🎯 Usage

### Getting Started

1. **Create a User Account**
   - Navigate to `create_user.html`
   - Enter user ID, name, and email
   - Click "Create User"

2. **Login**
   - Go to `login.html`
   - Enter your user ID
   - Access the dashboard

3. **Create Tasks**
   - From dashboard, click "Create New Task"
   - Fill in task details (title, description, priority, due date)
   - Submit to create the task

4. **Manage Tasks**
   - **Edit**: Click the edit button on any task
   - **Archive**: Click archive button to soft-delete
   - **Complete**: Update task status to "Completed"
   - **Assign**: Assign tasks to other users (if implemented)

5. **View Archives**
   - Navigate to `archive.html` to see archived tasks
   - Restore tasks if needed
   - View audit trail of who archived what

### Dashboard Features

- **Statistics Panel**: View task completion rates and priority breakdown
- **Task Lists**: Organized by status (To Do, In Progress, Completed, Blocked)
- **Quick Actions**: Fast access to create new tasks
- **Search & Filter**: Find specific tasks quickly

## 📚 API Documentation

### Authentication Endpoints

```http
POST /api/auth/login
POST /api/auth/logout
GET /api/auth/check
```

### User Endpoints

```http
POST /api/users                    # Create new user
GET /api/users/{user_id}          # Get user details
GET /api/users/{user_id}/dashboard # Get dashboard data
```

### Task Endpoints

```http
GET /api/tasks                     # Get all tasks
POST /api/tasks                    # Create new task
GET /api/tasks/{task_id}          # Get specific task
PUT /api/tasks/{task_id}          # Update task
PUT /api/tasks/{task_id}/archive  # Archive task (soft delete)
PUT /api/tasks/{task_id}/restore  # Restore archived task
GET /api/tasks/archived           # Get all archived tasks
```

### Audit Endpoints

```http
GET /api/tasks/{task_id}/audit    # Get task audit log
GET /api/audit/archives           # Get all archive activity
```

### Example API Usage

**Create a Task**
```javascript
const response = await fetch('http://localhost:5000/api/tasks', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({
        title: "Fix login bug",
        description: "Users can't login with special characters",
        priority: "High",
        due_date: "2025-10-01T09:00:00"
    })
});
```

**Archive a Task**
```javascript
const response = await fetch(`http://localhost:5000/api/tasks/${taskId}/archive`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({
        reason: "Task no longer needed"
    })
});
```

## 🗄️ Database Schema

### Users Table
```sql
CREATE TABLE users (
    user_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Tasks Table
```sql
CREATE TABLE tasks (
    task_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    created_by_id TEXT NOT NULL,
    assigned_to_id TEXT,
    priority TEXT DEFAULT 'Medium',
    status TEXT DEFAULT 'To Do',
    due_date TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_archived INTEGER DEFAULT 0,
    archived_at TIMESTAMP,
    archived_by_id TEXT,
    archive_reason TEXT,
    FOREIGN KEY (created_by_id) REFERENCES users (user_id),
    FOREIGN KEY (assigned_to_id) REFERENCES users (user_id),
    FOREIGN KEY (archived_by_id) REFERENCES users (user_id)
);
```

## 🖥️ Screenshots

### Dashboard Interface
The main dashboard shows task statistics, recent tasks, and quick actions for task management.

### Task Creation
Clean, intuitive form for creating new tasks with all necessary fields and validation.

### Archive Management
View and restore archived tasks with full audit trail information.

## 🔧 Development

### Running in Development Mode

1. **Enable Debug Mode**
   ```python
   # In app.py
   if __name__ == '__main__':
       app.run(debug=True, host='0.0.0.0', port=5000)
   ```

2. **Database Reset**
   The database automatically resets on server restart for clean development cycles.

3. **Adding Sample Data**
   Sample users and tasks are created automatically for testing.

### Code Structure

- **Models**: `user.py` and `task.py` contain data models and database operations
- **API Routes**: `app.py` contains all REST API endpoints
- **Frontend**: Static HTML/CSS/JS files with modular JavaScript functions
- **Database**: SQLite with foreign key constraints and proper indexing

### Adding New Features

1. **Backend**: Add new routes to `app.py` and update models as needed
2. **Frontend**: Create new HTML pages or update existing ones
3. **Database**: Modify schema in model files (will auto-update on restart)

## 🚀 Deployment

### Production Considerations

1. **Security**
   - Change `app.secret_key` to a secure random value
   - Disable database reset in production
   - Add proper password authentication
   - Enable HTTPS

2. **Database**
   - Consider PostgreSQL or MySQL for production
   - Add proper backup strategies
   - Implement database migrations

3. **Performance**
   - Add database indexes for frequently queried fields
   - Implement caching for dashboard data
   - Optimize frontend assets

### Environment Variables
```bash
export FLASK_ENV=production
export SECRET_KEY=your-super-secret-key
export DATABASE_URL=your-database-url
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow PEP 8 for Python code
- Use meaningful commit messages
- Add comments for complex functionality
- Test all new features thoroughly
- Update documentation as needed

## 📄 License

This project is developed for IS212 Software Project Management course.

## 🆘 Support

If you encounter any issues or have questions:

1. Check the [Issues](https://github.com/yourusername/IS212---Software_Project_Management/issues) page
2. Create a new issue with detailed description
3. Include error messages and screenshots if applicable

## 🎯 Future Enhancements

- [ ] Real-time notifications
- [ ] File attachments for tasks
- [ ] Team collaboration features
- [ ] Mobile responsive design
- [ ] Email notifications
- [ ] Advanced search and filtering
- [ ] Task templates
- [ ] Time tracking
- [ ] Reporting and analytics
- [ ] API rate limiting
- [ ] Password-based authentication
- [ ] Role-based permissions

---

**Built with ❤️ for IS212 Software Project Management**