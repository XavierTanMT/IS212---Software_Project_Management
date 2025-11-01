from flask import Blueprint

# Core blueprints
users_bp = Blueprint("users", __name__, url_prefix="/api/users")
tasks_bp = Blueprint("tasks", __name__, url_prefix="/api/tasks")
dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api")
manager_bp = Blueprint("manager", __name__, url_prefix="/api/manager")
admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")
staff_bp = Blueprint("staff", __name__, url_prefix="/api/staff")
notifications_bp = Blueprint("notifications", __name__, url_prefix="/api/notifications")

# Additional domain blueprints
projects_bp = Blueprint("projects", __name__, url_prefix="/api/projects")
notes_bp = Blueprint("notes", __name__, url_prefix="/api/notes")
labels_bp = Blueprint("labels", __name__, url_prefix="/api/labels")
memberships_bp = Blueprint("memberships", __name__, url_prefix="/api/memberships")
attachments_bp = Blueprint("attachments", __name__, url_prefix="/api/attachments")
reports_bp = Blueprint("reports", __name__, url_prefix="/api/reports")

# Import modules so routes attach
from . import users  # noqa
from . import auth  # noqa - Firebase Authentication endpoints
from . import admin  # noqa - Admin/diagnostic endpoints
from . import tasks  # noqa
from . import dashboard  # noqa
from . import manager  # noqa
from . import staff  # noqa
from . import projects  # noqa
from . import notes  # noqa
from . import labels  # noqa
from . import memberships  # noqa
from . import attachments  # noqa
from . import notifications  # noqa - Notifications endpoints
from . import reports  # noqa - Reports endpoints

__all__ = [
    "users_bp",
    "tasks_bp",
    "dashboard_bp",
    "manager_bp",
    "admin_bp",
    "staff_bp",
    "projects_bp",
    "notes_bp",
    "labels_bp",
    "memberships_bp",
    "attachments_bp",
    "notifications_bp",
    "reports_bp",
]