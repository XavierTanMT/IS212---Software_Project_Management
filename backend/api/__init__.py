from flask import Blueprint

# Core blueprints
users_bp = Blueprint("users", __name__, url_prefix="/api/users")
tasks_bp = Blueprint("tasks", __name__, url_prefix="/api/tasks")
dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api")
manager_bp = Blueprint("manager", __name__, url_prefix="/api/manager")

# Additional domain blueprints
projects_bp = Blueprint("projects", __name__, url_prefix="/api/projects")
notes_bp = Blueprint("notes", __name__, url_prefix="/api/notes")
labels_bp = Blueprint("labels", __name__, url_prefix="/api/labels")
memberships_bp = Blueprint("memberships", __name__, url_prefix="/api/memberships")
attachments_bp = Blueprint("attachments", __name__, url_prefix="/api/attachments")

# Import modules so routes attach
from . import users  # noqa
from . import auth  # noqa - Firebase Authentication endpoints
from . import admin  # noqa - Admin/diagnostic endpoints
from . import tasks  # noqa
from . import dashboard  # noqa
from . import manager  # noqa
from . import projects  # noqa
from . import notes  # noqa
from . import labels  # noqa
from . import memberships  # noqa
from . import attachments  # noqa

__all__ = [
    "users_bp",
    "tasks_bp",
    "dashboard_bp",
    "manager_bp",
    "projects_bp",
    "notes_bp",
    "labels_bp",
    "memberships_bp",
    "attachments_bp",
]
