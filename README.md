# IS212---Software_Project_Management

# Task Management System

A full-stack web application for managing tasks and projects, built with Flask backend, Firebase/Firestore database, and vanilla HTML/CSS/JavaScript frontend.

## 📋 Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [API Documentation](#api-documentation)
- [Testing](#testing)
- [Development](#development)
- [Contributing](#contributing)

## 🚀 Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package installer)
- Node.js and npm (for Firebase CLI)
- Firebase project with Firestore enabled
- Web browser (Chrome, Firefox, Safari, etc.)

### Setup Steps

1. **Clone the Repository**
   ```bash
   git clone https://github.com/XavierTanMT/IS212---Software_Project_Management.git
   cd IS212---Software_Project_Management
   ```

2. **Set Up Firebase Project**
   - Create a Firebase project at [Firebase Console](https://console.firebase.google.com/)
   - Enable Firestore Database
   - Enable Authentication (Email/Password)
   - Download service account key:
     - Go to Project Settings → Service Accounts
     - Click "Generate New Private Key"
     - Save as `backend/serviceAccountKey.json`

3. **Configure Environment Variables**
   ```bash
   # Copy example env file
   cp env.example backend/.env
   
   # Edit backend/.env and add your configuration
   # See env.example for required variables
   ```

4. **Create Virtual Environment**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # On Windows
   # source venv/bin/activate  # On macOS/Linux
   ```

5. **Install Dependencies**
   ```bash
   pip install --upgrade pip
   pip install -r backend/requirements.txt
   ```

6. **Install Firebase CLI (for emulators)**
   ```bash
   npm install -g firebase-tools
   ```

7. **Start the Backend Server**
   ```bash
   cd backend
   python app.py
   ```
   Server will start on `http://localhost:5000`

8. **Start the Frontend Server**
   ```bash
   # In a new terminal, from the frontend directory
   cd frontend
   python -m http.server 5500
   ```
   Access at `http://localhost:5500`

9. **Access the Application**
   - Open your browser and navigate to: `http://localhost:5500/login.html`

## 🎯 Usage

### Getting Started

1. **First-Time Setup**
   - The first user to register becomes an Admin automatically
   - Admins can create Manager and Staff accounts
   - Use the admin dashboard to set up projects and teams

2. **Login**
   - Navigate to `http://localhost:5500/login.html`
   - Enter your email and password
   - Access your role-specific dashboard

3. **Create Tasks**
   - From dashboard, click "Create New Task"
   - Fill in task details (title, description, priority, due date)
   - Add tags and labels for organization
   - Assign to team members
   - Submit to create the task

4. **Manage Tasks**
   - **Edit**: Click on any task to view details and edit
   - **Add Notes**: Collaborate with team members using task notes
   - **Upload Files**: Attach documents and files to tasks
   - **Update Status**: Track progress through different statuses
   - **Filter & Search**: Use advanced filters to find specific tasks

5. **Project Management** (Manager/Admin)
   - Create and manage projects
   - Assign team members to projects
   - Monitor team workload and capacity
   - Generate reports (PDF/Excel)

6. **Notifications**
   - Receive email notifications for task assignments
   - Get daily reminder emails for pending tasks
   - View notification history in the dashboard

### Role-Specific Features

#### Admin Dashboard
- User management (create, edit, deactivate)
- System-wide analytics
- All projects and tasks visibility
- Report generation

#### Manager Dashboard
- Team overview and workload management
- Project and task assignment
- Team member task tracking
- Performance metrics

#### Staff Dashboard
- Personal task list
- Task details and notes
- File attachments
- Status updates

## ✨ Features

### 🔐 User Management
- Firebase Authentication integration
- Role-based access control (Admin, Manager, Staff)
- User profiles with email, name, and department
- Session management

### 📝 Task Management
- **Create Tasks**: Add new tasks with title, description, priority, due dates, and tags
- **Edit Tasks**: Update task details and status
- **Task Assignment**: Assign tasks to specific users
- **Status Tracking**: Track task progress (To Do, In Progress, Completed, Blocked)
- **Priority Levels**: Set task priorities (High, Medium, Low)
- **Task Labels**: Organize tasks with color-coded labels
- **Task Notes**: Add collaborative notes to tasks
- **File Attachments**: Upload and manage task attachments

### 📊 Dashboard & Analytics
- **Role-based Dashboards**: Customized views for Admin, Manager, and Staff
- **Manager Dashboard**: Team overview and workload management
- **Task Statistics**: Completion rates, priority breakdown, status distribution
- **Recent Tasks**: Quick access to recently created tasks
- **Task Filtering**: Advanced filtering by status, priority, assignee, and labels

### � Project Management
- **Project Organization**: Group tasks into projects
- **Team Memberships**: Manage team members and their roles
- **Project Reports**: Generate PDF and Excel reports
- **Workload Tracking**: Monitor team capacity and assignments

### 🔔 Notifications
- **Email Notifications**: Automated email alerts for task assignments and updates
- **Scheduled Reminders**: Daily reminder emails for pending tasks
- **Notification History**: Track all sent notifications

### 🔒 Security Features
- **Firebase Authentication**: Secure user authentication
- **Authorization**: Role-based access control
- **Data Validation**: Server-side input validation
- **CORS Protection**: Proper cross-origin request handling

## 🛠️ Tech Stack

### Backend
- **Flask** - Python web framework
- **Firebase Admin SDK** - Firebase integration
- **Firestore** - NoSQL cloud database
- **Flask-CORS** - Cross-origin resource sharing
- **APScheduler** - Scheduled task notifications
- **ReportLab** - PDF report generation
- **OpenPyXL** - Excel report generation

### Frontend
- **HTML5** - Markup language
- **CSS3** - Styling with modern layouts and animations
- **Vanilla JavaScript** - No frameworks, pure JS
- **Fetch API** - HTTP requests to backend
- **Firebase JS SDK** - Client-side authentication

### Development Tools
- **Python 3.8+** - Backend runtime
- **Virtual Environment** - Dependency isolation
- **Firebase Emulators** - Local testing environment
- **pytest** - Testing framework with 100% branch coverage

## 📁 Project Structure

```
IS212---Software_Project_Management/
├── backend/                        # Backend API server
│   ├── app.py                      # Main Flask application
│   ├── firebase_utils.py           # Firebase/Firestore utilities
│   ├── email_utils.py              # Email notification utilities
│   ├── resend_notifications.py     # Scheduled notification service
│   ├── requirements.txt            # Python dependencies
│   ├── serviceAccountKey.json      # Firebase credentials (gitignored)
│   └── api/                        # API route modules
│       ├── auth.py                 # Authentication endpoints
│       ├── users.py                # User management
│       ├── tasks.py                # Task management
│       ├── projects.py             # Project management
│       ├── dashboard.py            # Dashboard data
│       ├── notifications.py        # Notification endpoints
│       ├── reports.py              # Report generation
│       ├── attachments.py          # File upload/download
│       ├── notes.py                # Task notes
│       ├── labels.py               # Task labels
│       ├── tags.py                 # Task tags
│       ├── memberships.py          # Project memberships
│       ├── admin.py                # Admin operations
│       ├── manager.py              # Manager operations
│       └── staff.py                # Staff operations
├── frontend/                       # Frontend web pages
│   ├── login.html                  # User authentication page
│   ├── dashboard.html              # Staff dashboard
│   ├── admin_dashboard.html        # Admin dashboard
│   ├── manager_dashboard.html      # Manager dashboard
│   ├── manager_team_view.html      # Team management
│   ├── create_task.html            # Task creation form
│   ├── edit_task.html              # Task editing interface
│   ├── task_detail.html            # Task details view
│   ├── task_notes.html             # Task notes interface
│   ├── attachments.html            # File attachments
│   ├── projects.html               # Project management
│   ├── tasks_list.html             # Task list view
│   ├── css/                        # Stylesheets
│   └── scripts/                    # JavaScript modules
├── tests/                          # Test suites
│   ├── unit/                       # Unit tests (100% coverage)
│   ├── integration/                # Integration tests with emulators
│   └── e2e/                        # End-to-end tests
├── plantuml/                       # Architecture diagrams
├── firebase.json                   # Firebase emulator configuration
├── firestore.rules                 # Firestore security rules
├── start_backend_with_emulators.bat  # Windows startup script
├── start_backend_with_emulators.ps1  # PowerShell startup script
├── start_emulators.ps1             # Emulator startup script
└── README.md                       # Project documentation
```

##  API Documentation

### Authentication Endpoints

```http
POST /api/auth/login              # Login user
POST /api/auth/logout             # Logout user
GET /api/auth/check               # Check auth status
POST /api/auth/register           # Register new user
```

### User Endpoints

```http
GET /api/users                    # Get all users
POST /api/users                   # Create new user (Admin)
GET /api/users/{user_id}          # Get user details
PUT /api/users/{user_id}          # Update user
DELETE /api/users/{user_id}       # Delete user (Admin)
```

### Task Endpoints

```http
GET /api/tasks                    # Get all tasks (with filters)
POST /api/tasks                   # Create new task
GET /api/tasks/{task_id}          # Get specific task
PUT /api/tasks/{task_id}          # Update task
DELETE /api/tasks/{task_id}       # Delete task
GET /api/tasks/user/{user_id}     # Get user's tasks
```

### Project Endpoints

```http
GET /api/projects                 # Get all projects
POST /api/projects                # Create new project
GET /api/projects/{project_id}    # Get project details
PUT /api/projects/{project_id}    # Update project
DELETE /api/projects/{project_id} # Delete project
```

### Dashboard Endpoints

```http
GET /api/dashboard/staff          # Staff dashboard data
GET /api/dashboard/manager        # Manager dashboard data
GET /api/dashboard/admin          # Admin dashboard data
```

### Notification Endpoints

```http
GET /api/notifications            # Get all notifications
POST /api/notifications/send      # Send notification
GET /api/notifications/user/{user_id} # Get user notifications
```

### Report Endpoints

```http
POST /api/reports/pdf             # Generate PDF report
POST /api/reports/excel           # Generate Excel report
```

### Attachment Endpoints

```http
POST /api/attachments             # Upload file
GET /api/attachments/{attachment_id} # Download file
DELETE /api/attachments/{attachment_id} # Delete file
```

### Example API Usage

**Create a Task**
```javascript
const response = await fetch('http://localhost:5000/api/tasks', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({
        title: "Implement user authentication",
        description: "Add Firebase authentication to the login page",
        priority: "High",
        status: "To Do",
        assigned_to: "user123",
        due_date: "2025-12-01T09:00:00",
        tags: ["authentication", "security"],
        labels: ["frontend"]
    })
});
```

**Get Dashboard Data**
```javascript
const response = await fetch('http://localhost:5000/api/dashboard/staff', {
    method: 'GET',
    credentials: 'include'
});
const dashboardData = await response.json();
```

## 🗄️ Database Schema

### Firestore Collections

#### Users Collection
```javascript
{
  user_id: "auto-generated-uid",
  email: "user@example.com",
  name: "John Doe",
  role: "staff", // "admin", "manager", or "staff"
  department: "Engineering",
  is_active: true,
  created_at: Timestamp,
  updated_at: Timestamp
}
```

#### Tasks Collection
```javascript
{
  task_id: "auto-generated-id",
  title: "Task title",
  description: "Task description",
  created_by: "user_id",
  assigned_to: "user_id",
  project_id: "project_id",
  priority: "High", // "High", "Medium", "Low"
  status: "To Do", // "To Do", "In Progress", "Completed", "Blocked"
  due_date: Timestamp,
  tags: ["tag1", "tag2"],
  labels: ["label1"],
  created_at: Timestamp,
  updated_at: Timestamp
}
```

#### Projects Collection
```javascript
{
  project_id: "auto-generated-id",
  name: "Project name",
  description: "Project description",
  created_by: "user_id",
  status: "active", // "active", "completed", "archived"
  created_at: Timestamp,
  updated_at: Timestamp
}
```

#### Memberships Collection
```javascript
{
  membership_id: "auto-generated-id",
  project_id: "project_id",
  user_id: "user_id",
  role: "member", // "owner", "member"
  joined_at: Timestamp
}
```

#### Notifications Collection
```javascript
{
  notification_id: "auto-generated-id",
  user_id: "user_id",
  task_id: "task_id",
  type: "task_assigned", // "task_assigned", "task_updated", "reminder"
  message: "Notification message",
  email_sent: true,
  sent_at: Timestamp,
  created_at: Timestamp
}
```

#### Notes Collection (Subcollection under Tasks)
```javascript
{
  note_id: "auto-generated-id",
  task_id: "parent-task-id",
  user_id: "user_id",
  content: "Note content",
  created_at: Timestamp
}
```

#### Attachments Collection
```javascript
{
  attachment_id: "auto-generated-id",
  task_id: "task_id",
  uploaded_by: "user_id",
  file_name: "document.pdf",
  file_size: 1024000,
  file_type: "application/pdf",
  storage_path: "attachments/task_id/file_name",
  uploaded_at: Timestamp
}
```

## 🧪 Testing

This project has comprehensive unit and integration tests with **100% branch coverage**.

### Unit Tests (Fast, No Setup Required)

Unit tests run without any external dependencies or Firebase setup.

```bash
# Run all unit tests
python -m pytest tests/unit -v

# Run with coverage report
python -m pytest tests/unit --cov=backend --cov-branch --cov-report=html

# Run specific test file
python -m pytest tests/unit/test_specific.py -v

# View coverage report
# Open htmlcov/index.html in browser
```

### Integration Tests (Requires Firebase Emulators)

Integration tests use Firebase Local Emulator Suite - no credentials or quota limits!

**Quick Start with Helper Scripts:**

```powershell
# Windows PowerShell (Recommended)
.\start_backend_with_emulators.ps1

# This single command will:
# 1. Start Firebase emulators
# 2. Wait for emulators to be ready
# 3. Start Flask backend
# 4. Run in separate windows for easy monitoring
```

**Manual Setup:**

```bash
# 1. Install Firebase CLI (one-time setup)
npm install -g firebase-tools

# 2. Start emulators (in separate terminal)
firebase emulators:start
# Or use: .\start_emulators.ps1  (Windows)
# Or use: python start_emulators.py  (Cross-platform)

# 3. Run integration tests (in new terminal)
python -m pytest tests/integration -v

# Run specific integration test suite
python -m pytest tests/integration/test_api_integration_v2.py -v
```

**Benefits of Emulator-Based Testing:**
- ✅ No Firebase credentials needed
- ✅ No quota limits
- ✅ Faster tests (local)
- ✅ Free forever
- ✅ Works offline
- ✅ Consistent test environment

**Emulator Ports:**
- Firestore: `http://localhost:8080`
- Authentication: `http://localhost:9099`
- Emulator UI: `http://localhost:4000`

See `EMULATOR_SETUP.md` for detailed setup instructions.

### Running All Tests

```bash
# Run all tests (unit + integration)
# Make sure emulators are running first!
python -m pytest tests/ -v

# Generate full coverage report
python -m pytest tests/ --cov=backend --cov-branch --cov-report=html
```

### Test Structure

```
tests/
├── unit/                    # Fast unit tests (no external dependencies)
│   ├── test_auth.py
│   ├── test_tasks.py
│   ├── test_projects.py
│   └── ...
├── integration/             # Integration tests with Firebase emulators
│   ├── conftest.py         # Shared fixtures
│   ├── test_api_integration_v2.py
│   ├── test_admin_workflows.py
│   └── ...
└── e2e/                     # End-to-end tests
    └── test_login_file.py
```

## 🔧 Development

### Running in Development Mode

1. **Enable Debug Mode**
   ```python
   # In backend/app.py
   if __name__ == '__main__':
       app.run(debug=True, host='0.0.0.0', port=5000)
   ```

2. **Using Firebase Emulators**
   Always use emulators for local development to avoid affecting production data:
   ```bash
   # Start both emulators and backend
   .\start_backend_with_emulators.ps1
   ```

3. **Environment Variables**
   Configure your `.env` file in the `backend/` directory:
   ```env
   FLASK_ENV=development
   FLASK_DEBUG=True
   USE_EMULATOR=True
   FIRESTORE_EMULATOR_HOST=localhost:8080
   FIREBASE_AUTH_EMULATOR_HOST=localhost:9099
   ```

### Code Structure

- **API Routes**: Organized in `backend/api/` directory by feature
  - `auth.py` - Authentication and authorization
  - `tasks.py` - Task CRUD operations
  - `projects.py` - Project management
  - `dashboard.py` - Dashboard data aggregation
  - `notifications.py` - Notification handling
  - `reports.py` - Report generation (PDF/Excel)

- **Utilities**: 
  - `firebase_utils.py` - Firebase/Firestore helper functions
  - `email_utils.py` - Email notification utilities

- **Frontend**: Static HTML/CSS/JS files with modular structure
  - `scripts/` - JavaScript modules by feature
  - `css/` - Modular stylesheets
  - `firebase-config.js` - Firebase client configuration

### Adding New Features

1. **Backend API Endpoint**
   ```python
   # Create new file in backend/api/ or add to existing
   from flask import Blueprint, request, jsonify
   
   new_feature_bp = Blueprint('new_feature', __name__)
   
   @new_feature_bp.route('/api/new-feature', methods=['GET'])
   def get_new_feature():
       # Your logic here
       return jsonify({'data': 'result'})
   
   # Register in app.py
   app.register_blueprint(new_feature_bp)
   ```

2. **Frontend Integration**
   ```javascript
   // Add to appropriate script file in frontend/scripts/
   async function fetchNewFeature() {
       const response = await fetch('http://localhost:5000/api/new-feature', {
           credentials: 'include'
       });
       const data = await response.json();
       return data;
   }
   ```

3. **Add Tests**
   ```python
   # tests/unit/test_new_feature.py
   def test_new_feature():
       # Your test logic
       assert True
   ```

### Debugging Tips

1. **Check Firebase Emulator UI**: `http://localhost:4000`
   - View Firestore data
   - Check Authentication users
   - Monitor logs

2. **Enable Verbose Logging**
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

3. **Browser DevTools**
   - Network tab for API calls
   - Console for JavaScript errors
   - Application tab for session storage

### Common Development Tasks

```bash
# Format Python code
black backend/

# Lint Python code
flake8 backend/

# Run security checks
bandit -r backend/

# Update dependencies
pip freeze > backend/requirements.txt
```

## 🚀 Deployment

### Production Considerations

1. **Security**
   - Use environment variables for all sensitive data
   - Never commit `serviceAccountKey.json` to version control
   - Enable Firebase Security Rules for Firestore
   - Use HTTPS in production
   - Implement rate limiting
   - Enable CORS only for trusted domains

2. **Firebase Configuration**
   - Set up proper Firestore security rules
   - Configure Firebase Authentication settings
   - Set up backup schedules for Firestore
   - Monitor Firebase usage and quotas

3. **Environment Variables**
   ```bash
   # Production environment
   FLASK_ENV=production
   FLASK_DEBUG=False
   USE_EMULATOR=False
   SECRET_KEY=your-super-secret-key
   FRONTEND_URL=https://your-domain.com
   BACKEND_URL=https://api.your-domain.com
   ```

4. **Performance**
   - Implement caching for frequently accessed data
   - Optimize Firestore queries with proper indexes
   - Use CDN for static frontend assets
   - Enable gzip compression
   - Monitor API response times

5. **Monitoring**
   - Set up Firebase Performance Monitoring
   - Configure error logging and alerting
   - Monitor API endpoint usage
   - Track user activity and errors

### Deployment Options

#### Option 1: Deploy to Google Cloud Platform
```bash
# Deploy Flask backend to Cloud Run
gcloud run deploy task-management-backend \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated

# Deploy frontend to Firebase Hosting
firebase deploy --only hosting
```

#### Option 2: Deploy to Heroku
```bash
# Create Procfile
echo "web: gunicorn backend.app:app" > Procfile

# Deploy to Heroku
heroku create your-app-name
git push heroku main
```

#### Option 3: Deploy to AWS
- Use AWS Elastic Beanstalk for Flask backend
- Use AWS S3 + CloudFront for frontend hosting
- Configure environment variables in Elastic Beanstalk

## 🤝 Contributing

We welcome contributions! Please follow these guidelines:

1. **Fork the Repository**
   ```bash
   git clone https://github.com/XavierTanMT/IS212---Software_Project_Management.git
   cd IS212---Software_Project_Management
   ```

2. **Create a Feature Branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```

3. **Make Your Changes**
   - Write clean, documented code
   - Follow the existing code style
   - Add unit tests for new features
   - Ensure all tests pass

4. **Test Your Changes**
   ```bash
   # Run all tests
   python -m pytest tests/ -v
   
   # Check coverage
   python -m pytest tests/ --cov=backend --cov-branch
   ```

5. **Commit Your Changes**
   ```bash
   git add .
   git commit -m 'Add some amazing feature'
   ```

6. **Push to Your Fork**
   ```bash
   git push origin feature/amazing-feature
   ```

7. **Open a Pull Request**
   - Provide a clear description of changes
   - Reference any related issues
   - Ensure CI/CD checks pass

### Development Guidelines

- **Python Code**: Follow PEP 8 style guide
- **JavaScript Code**: Use ES6+ features, consistent formatting
- **Commit Messages**: Use clear, descriptive messages
- **Documentation**: Update README and code comments
- **Testing**: Maintain 100% branch coverage
- **Code Review**: All changes require review before merge

### Testing Requirements

- All new features must include unit tests
- Integration tests for API endpoints
- Maintain existing coverage levels
- Test with Firebase emulators locally

### Code Style

```python
# Python - Follow PEP 8
def create_task(title, description, **kwargs):
    """
    Create a new task in Firestore.
    
    Args:
        title (str): Task title
        description (str): Task description
        **kwargs: Additional task fields
        
    Returns:
        dict: Created task data
    """
    # Implementation
```

```javascript
// JavaScript - Modern ES6+
async function createTask(taskData) {
    try {
        const response = await fetch('/api/tasks', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(taskData)
        });
        return await response.json();
    } catch (error) {
        console.error('Error creating task:', error);
        throw error;
    }
}
```

## 📄 License

This project is developed for IS212 Software Project Management course.

## 🆘 Support

If you encounter any issues or have questions:

1. **Check Existing Documentation**
   - Review this README
   - Check `EMULATOR_SETUP.md` for Firebase setup
   - Review `backend/README.md` for backend details

2. **Common Issues**
   
   **Firebase Emulator Not Starting**
   ```bash
   # Kill existing processes
   taskkill /F /IM java.exe
   # Restart emulators
   .\start_emulators.ps1
   ```
   
   **CORS Errors**
   - Ensure backend is running on port 5000
   - Ensure frontend is running on port 5500
   - Check CORS configuration in `app.py`
   
   **Authentication Issues**
   - Verify Firebase configuration
   - Check `serviceAccountKey.json` is present
   - Ensure emulators are running (for local dev)

3. **Get Help**
   - Check the [Issues](https://github.com/XavierTanMT/IS212---Software_Project_Management/issues) page
   - Create a new issue with:
     - Detailed description of the problem
     - Error messages and stack traces
     - Screenshots if applicable
     - Steps to reproduce

4. **Contact**
   - Course: IS212 Software Project Management
   - For urgent issues, contact the development team

## 📊 Project Statistics

- **Backend**: Python/Flask with Firebase
- **Frontend**: Vanilla HTML/CSS/JavaScript
- **Test Coverage**: 100% branch coverage
- **API Endpoints**: 40+ RESTful endpoints
- **Database**: Cloud Firestore (NoSQL)

## 🎯 Future Enhancements

### Planned Features
- [ ] Real-time task updates using WebSockets
- [ ] Mobile responsive design improvements
- [ ] Advanced analytics and reporting
- [ ] Task dependencies and Gantt charts
- [ ] Time tracking integration
- [ ] Calendar view for tasks
- [ ] Task templates for common workflows
- [ ] Bulk task operations
- [ ] Advanced search with filters
- [ ] Export data to various formats
- [ ] API rate limiting and throttling
- [ ] Two-factor authentication
- [ ] Dark mode theme
- [ ] Internationalization (i18n)
- [ ] Integration with external tools (Slack, Jira, etc.)

### Technical Improvements
- [ ] Implement Redis caching
- [ ] Add GraphQL API option
- [ ] Containerize with Docker
- [ ] CI/CD pipeline with GitHub Actions
- [ ] Performance monitoring
- [ ] Automated database backups
- [ ] API versioning
- [ ] OpenAPI/Swagger documentation

## 📝 Changelog

### Version 2.0.0 (Current)
- Migrated from SQLite to Firebase/Firestore
- Implemented role-based access control
- Added project management features
- Email notifications system
- File attachment support
- Task notes and collaboration
- Report generation (PDF/Excel)
- Comprehensive test suite with 100% coverage

### Version 1.0.0
- Initial release with SQLite
- Basic task management
- User authentication
- Simple dashboard

## 📄 License

This project is developed for educational purposes as part of the IS212 Software Project Management course at Singapore Management University.

## 🙏 Acknowledgments

- **Course**: IS212 Software Project Management
- **Institution**: Singapore Management University
- **Technologies**: Flask, Firebase, Firestore
- **Testing**: pytest, Firebase Emulators
- **Contributors**: Development team and course instructors

---

**Built with ❤️ for IS212 Software Project Management**

For more information, visit the [GitHub Repository](https://github.com/XavierTanMT/IS212---Software_Project_Management)