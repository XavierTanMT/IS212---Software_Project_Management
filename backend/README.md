# IS212 Task Management - Firebase Backend

A Flask-based REST API backend for the IS212 Task Management System, implementing Firebase Firestore and Authentication.

## Features Implemented

### ✅ Core First Release Requirements
- **User Authorization and Authentication** - Firebase Auth with role-based access
- **Task Management** - CRUD operations with subtasks and priority buckets (1-10)
- **Recurring Tasks** - Automatic task generation with configurable frequency
- **Task Grouping and Organisation** - Projects with collaborators
- **Priority Buckets** - 1-10 scale (NEW requirement)
- **Deadline and Schedule Tracking** - Due dates and overdue detection
- **Role-based Access Control** - Staff, Manager, Director, Admin roles

### 🔧 Technical Features
- Firebase Firestore (NoSQL database)
- Firebase Authentication (JWT tokens)
- RESTful API design
- Input validation and error handling
- CORS support for frontend integration
- Soft delete (archiving) for tasks
- Comprehensive logging and error responses

## Architecture

### Backend Components (C3 Design)
- **Authentication Service** - Firebase Auth integration
- **User Management** - Role-based user operations
- **Task Management** - CRUD with subtasks and recurrence
- **Project Management** - Project creation and collaboration
- **Recurrence Service** - Automatic recurring task generation
- **Dashboard Service** - Analytics and statistics
- **Middleware** - Authentication and authorization

### Data Models (Firestore Collections)
- `users/` - User profiles with roles
- `tasks/` - Tasks with priority buckets and recurrence
- `projects/` - Projects with members
- `notifications/` - In-app notifications (ready for implementation)
- `reports/` - Generated reports (ready for implementation)

## Quick Start

### 1. Prerequisites
- Python 3.8+
- Firebase project with Firestore and Authentication enabled

### 2. Setup
```bash
cd backend
python setup.py
```

The setup script will:
- Install dependencies
- Create environment configuration
- Guide you through Firebase setup
- Test the connection
- Start the server

### 3. Manual Setup (Alternative)

#### Install Dependencies
```bash
pip install -r requirements.txt
```

#### Configure Environment
1. Copy `env.example` to `.env`
2. Update Firebase configuration:
   ```bash
   FIREBASE_PROJECT_ID=your-project-id
   FIREBASE_CREDENTIALS_PATH=./serviceAccountKey.json
   ```

#### Firebase Setup
1. Create Firebase project at https://console.firebase.google.com/
2. Enable Firestore Database
3. Enable Authentication (Email/Password)
4. Generate service account key:
   - Go to Project Settings > Service Accounts
   - Click "Generate new private key"
   - Save as `serviceAccountKey.json` in backend directory

#### Run Server
```bash
python app.py
```

Server will start at `http://localhost:5000`

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login (verify token)
- `POST /api/auth/verify` - Verify Firebase token
- `POST /api/auth/reset-password` - Send password reset

### Users
- `GET /api/users/{user_id}` - Get user details
- `PUT /api/users/{user_id}` - Update user
- `GET /api/users/{user_id}/dashboard` - Get dashboard data
- `GET /api/users/role/{role}` - Get users by role (manager+)
- `GET /api/users/team/{manager_id}` - Get team members

### Tasks
- `GET /api/tasks` - Get user's tasks
- `POST /api/tasks` - Create task
- `GET /api/tasks/{task_id}` - Get specific task
- `PUT /api/tasks/{task_id}` - Update task
- `DELETE /api/tasks/{task_id}` - Delete task (archive)
- `POST /api/tasks/{task_id}/subtasks` - Create subtask
- `GET /api/tasks/{task_id}/subtasks` - Get subtasks
- `PUT /api/tasks/{task_id}/assign` - Assign task (manager+)
- `PUT /api/tasks/{task_id}/complete` - Complete task (handles recurrence)
- `PUT /api/tasks/{task_id}/recurrence` - Update recurrence settings
- `GET /api/tasks/overdue` - Get overdue tasks

### Projects
- `GET /api/projects` - Get user's projects
- `POST /api/projects` - Create project
- `GET /api/projects/{project_id}` - Get specific project
- `PUT /api/projects/{project_id}` - Update project
- `DELETE /api/projects/{project_id}` - Delete project
- `POST /api/projects/{project_id}/members` - Add member
- `DELETE /api/projects/{project_id}/members/{member_id}` - Remove member
- `GET /api/projects/{project_id}/members` - Get project members
- `GET /api/projects/{project_id}/statistics` - Get project statistics
- `GET /api/projects/{project_id}/tasks` - Get project tasks

## Key Features

### Priority Buckets (1-10)
- Tasks now use a 1-10 priority scale instead of High/Medium/Low
- 1 = Least important, 10 = Most important
- Color coding: Green(1-3) → Yellow(4-7) → Red(8-10)

### Recurring Tasks
- Set frequency: daily, weekly, monthly
- Set interval: every N days/weeks/months
- Optional end date
- Automatic next occurrence generation when task is completed

### Role-Based Access
- **Staff**: Create/manage own tasks
- **Manager**: Assign tasks to staff, manage projects
- **Director**: Full project management
- **Admin**: System-wide access

### Subtasks
- Tasks can have subtasks (parent_task_id relationship)
- Subtasks inherit project context
- Full CRUD operations for subtasks

## Data Models

### Task Document Structure
```javascript
{
  task_id: string,
  title: string,
  description: string,
  status: 'todo'|'in_progress'|'done'|'review',
  priority_bucket: number (1-10),
  due_date: timestamp,
  created_by: string (user_id),
  assigned_to: [user_ids],
  project_id: string (optional),
  parent_task_id: string (optional),
  recurrence: {
    enabled: boolean,
    frequency: 'daily'|'weekly'|'monthly',
    interval: number,
    end_date: timestamp (optional),
    next_occurrence: timestamp (calculated)
  },
  tags: [strings],
  is_archived: boolean,
  archived_at: timestamp,
  archived_by_id: string,
  created_at: timestamp,
  updated_at: timestamp
}
```

### Project Document Structure
```javascript
{
  project_id: string,
  name: string,
  description: string,
  created_by: string (user_id),
  members: [user_ids],
  created_at: timestamp,
  updated_at: timestamp
}
```

## Error Handling

All API endpoints return standardized responses:

### Success Response
```json
{
  "success": true,
  "data": { ... },
  "message": "Operation successful",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### Error Response
```json
{
  "error": "Error message",
  "code": 400,
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## Development

### Project Structure
```
backend/
├── config/
│   ├── firebase_config.py    # Firebase initialization
│   └── settings.py           # App configuration
├── models/
│   ├── user_model.py         # User CRUD operations
│   ├── task_model.py         # Task CRUD operations
│   └── project_model.py      # Project CRUD operations
├── services/
│   ├── auth_service.py       # Authentication logic
│   └── recurrence_service.py # Recurring task logic
├── routes/
│   ├── auth_routes.py        # Authentication endpoints
│   ├── user_routes.py        # User endpoints
│   ├── task_routes.py        # Task endpoints
│   └── project_routes.py     # Project endpoints
├── middleware/
│   └── auth_middleware.py    # Authentication & authorization
├── utils/
│   └── validators.py         # Input validation & helpers
├── app.py                    # Main Flask application
├── setup.py                  # Setup script
└── requirements.txt          # Dependencies
```

### Adding New Features
1. Create model in `models/`
2. Create service in `services/` (if needed)
3. Create routes in `routes/`
4. Register blueprint in `app.py`
5. Add tests and documentation

## Deployment

### Environment Variables
```bash
FIREBASE_PROJECT_ID=your-production-project-id
FIREBASE_CREDENTIALS_PATH=./serviceAccountKey.json
FLASK_ENV=production
SECRET_KEY=your-secure-secret-key
CORS_ORIGINS=https://your-frontend-domain.com
```

### Production Considerations
- Use production Firebase project
- Set secure SECRET_KEY
- Configure proper CORS origins
- Enable Firestore security rules
- Set up monitoring and logging
- Use HTTPS in production

## Testing

### Manual Testing
1. Start the server: `python app.py`
2. Test health endpoint: `curl http://localhost:5000/api/health`
3. Use Postman or similar tool to test API endpoints

### Frontend Integration
The backend is designed to work with the existing frontend HTML files. Update the frontend to:
1. Use Firebase Auth SDK for authentication
2. Send Firebase ID tokens to backend
3. Handle new priority bucket (1-10) UI
4. Add recurrence settings UI
5. Integrate project management features

## Troubleshooting

### Common Issues
1. **Firebase connection failed**: Check project ID and credentials file
2. **CORS errors**: Verify CORS_ORIGINS in .env file
3. **Authentication errors**: Ensure Firebase Auth is enabled
4. **Permission denied**: Check Firestore security rules

### Debug Mode
Set `FLASK_ENV=development` in .env file for detailed error messages.

## Contributing

1. Follow the existing code structure
2. Add proper error handling
3. Include input validation
4. Update documentation
5. Test all endpoints

## License

This project is developed for IS212 Software Project Management course.
