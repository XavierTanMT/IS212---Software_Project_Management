# IS212 Task Management System

A comprehensive task management system built with Flask backend and Firebase integration, featuring role-based access control and advanced task management capabilities.

## Features

- **User Authentication**: Firebase Authentication with JWT tokens
- **Role-Based Access Control**: Staff, Manager, Director, Admin hierarchy
- **Task Management**: Create, update, assign, and track tasks with priority buckets (1-10)
- **Project Management**: Organize tasks into projects with team collaboration
- **Recurring Tasks**: Automatic task generation with configurable intervals
- **Subtasks**: Parent-child task relationships
- **Dashboard Analytics**: Task statistics and progress tracking

## Tech Stack

- **Backend**: Flask, Firebase (Firestore + Authentication)
- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **Database**: Firestore (NoSQL)
- **Authentication**: Firebase Auth with JWT tokens

## Project Structure

```
├── backend/                 # Flask API server
│   ├── config/             # Firebase configuration
│   ├── models/             # Data models (User, Task, Project)
│   ├── routes/             # API endpoints
│   ├── services/           # Business logic
│   ├── middleware/         # Authentication & authorization
│   └── utils/              # Utilities and validators
├── frontend_Xavier/        # Frontend web pages
│   ├── js/                 # JavaScript modules
│   └── *.html              # HTML pages
└── plantuml/               # Architecture diagrams
```

## Setup Instructions

1. **Clone the repository**
2. **Set up Firebase project** and configure authentication
3. **Install Python dependencies**: `pip install -r backend/requirements.txt`
4. **Configure environment variables** (see backend/README.md)
5. **Start the backend server**: `cd backend && python app.py`
6. **Open frontend** in your browser

## API Documentation

Complete API documentation is available in `backend/README.md`.

## Architecture

The system follows C4 architecture patterns with PlantUML diagrams in the `plantuml/` directory.

## Security

- All sensitive configuration is stored in environment variables
- Firebase security rules enforce data access control
- JWT token-based authentication
- Role-based permissions throughout the system

## License

Developed for IS212 Software Project Management course.