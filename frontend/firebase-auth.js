/**
 * Firebase Authentication Helper (BACKEND-ONLY MODE)
 * This file handles Firebase Authentication integration for the task manager.
 * 
 * ✅ BACKEND-ONLY MODE (Current Implementation):
 * - Backend handles ALL Firebase Auth operations
 * - No Firebase client SDK required
 * - Works immediately without Firebase config
 * - Backend creates users, verifies passwords, generates JWT tokens
 * 
 * 📦 OPTIONAL: Client-Side Firebase SDK:
 * If you want to use Firebase client SDK, include in your HTML:
 * 
 * <script src="https://www.gstatic.com/firebasejs/10.7.1/firebase-app-compat.js"></script>
 * <script src="https://www.gstatic.com/firebasejs/10.7.1/firebase-auth-compat.js"></script>
 * 
 * And configure Firebase:
 * <script>
 *   const firebaseConfig = {
 *     apiKey: "YOUR_API_KEY",
 *     authDomain: "YOUR_AUTH_DOMAIN",
 *     projectId: "YOUR_PROJECT_ID"
 *   };
 *   firebase.initializeApp(firebaseConfig);
 * </script>
 * 
 * However, this is NOT required - the backend-only mode works perfectly!
 */

const API_BASE = "http://localhost:5000";

// ============================================================================
// Session Management
// ============================================================================

// Flag to prevent multiple redirects
let isRedirecting = false;

// Throttling for verifySession to prevent API spam
let lastVerifyTime = 0;
let verifyPromise = null;
const VERIFY_THROTTLE_MS = 5000; // Only verify once every 5 seconds

/**
 * Get current user from session storage
 * @returns {Object|null} User object or null
 */
function getCurrentUser() {
    try {
        const userData = sessionStorage.getItem("currentUser");
        return userData ? JSON.parse(userData) : null;
    } catch (e) {
        console.error("Error getting current user:", e);
        return null;
    }
}

/**
 * Get Firebase auth token from session storage
 * @returns {string|null} Firebase token or null
 */
function getFirebaseToken() {
    return sessionStorage.getItem("firebaseToken");
}

/**
 * Set current user in session storage
 * @param {Object} user - User object
 * @param {string} token - Firebase auth token
 */
function setCurrentUser(user, token) {
    sessionStorage.setItem("currentUser", JSON.stringify(user));
    sessionStorage.setItem("firebaseToken", token);
}

/**
 * Clear current user from session storage
 */
function clearCurrentUser() {
    sessionStorage.removeItem("currentUser");
    sessionStorage.removeItem("firebaseToken");
    sessionStorage.removeItem("currentProject");

    // Clear verification cache
    lastVerifyTime = 0;
    verifyPromise = null;
    isRedirecting = false;
}

// ============================================================================
// Role-Based Access Control
// ============================================================================

/**
 * Get user role
 * @returns {string} User role (staff, manager, director, hr, admin)
 */
function getUserRole() {
    const user = getCurrentUser();
    return user?.role || 'staff';
}

/**
 * Check if user has specific role
 * @param {string} role - Role to check
 * @returns {boolean}
 */
function hasRole(role) {
    return getUserRole() === role;
}

/**
 * Check if user is manager or above
 * @returns {boolean}
 */
function isManager() {
    const role = getUserRole();
    return ['manager', 'director', 'hr', 'admin'].includes(role);
}

/**
 * Check if user is admin
 * @returns {boolean}
 */
function isAdmin() {
    return getUserRole() === 'admin';
}

/**
 * Get role-based dashboard URL
 * @param {string} role - User role
 * @returns {string} Dashboard URL for role
 */
function getRoleDashboard(role) {
    const dashboards = {
        'admin': 'admin_dashboard.html',
        'manager': 'manager_dashboard.html',
        'director': 'manager_dashboard.html',
        'hr': 'manager_dashboard.html',
        'staff': 'dashboard.html'
    };
    return dashboards[role] || 'dashboard.html';
}

/**
 * Redirect to role-appropriate dashboard
 */
function redirectToRoleDashboard() {
    const user = getCurrentUser();
    if (!user) {
        window.location.href = 'login.html';
        return;
    }

    const dashboardUrl = getRoleDashboard(user.role);
    window.location.href = dashboardUrl;
}

/**
 * Require specific role - redirect if user doesn't have it
 * @param {string|string[]} allowedRoles - Role or array of roles
 * @param {string} redirectTo - Where to redirect if not allowed (optional)
 */
function requireRole(allowedRoles, redirectTo = null) {
    const user = requireAuth(); // First check if authenticated

    const roles = Array.isArray(allowedRoles) ? allowedRoles : [allowedRoles];
    const userRole = user.role || 'staff';

    if (!roles.includes(userRole)) {
        console.warn(`Access denied. Required: ${roles.join(' or ')}, User has: ${userRole}`);

        if (redirectTo) {
            window.location.href = redirectTo;
        } else {
            // Redirect to appropriate dashboard
            redirectToRoleDashboard();
        }

        throw new Error(`Insufficient permissions. Required: ${roles.join(' or ')}`);
    }

    return user;
}

/**
 * Require manager role or above
 */
function requireManager() {
    return requireRole(['manager', 'director', 'hr', 'admin']);
}

/**
 * Require admin role
 */
function requireAdmin() {
    return requireRole('admin');
}

// ============================================================================
// Project Management (unchanged)
// ============================================================================

function getCurrentProject() {
    try {
        return JSON.parse(sessionStorage.getItem("currentProject") || "null");
    } catch (e) {
        return null;
    }
}

function setCurrentProject(p) {
    sessionStorage.setItem("currentProject", JSON.stringify(p));
}

// ============================================================================
// Authentication Functions
// ============================================================================

/**
 * Require authentication - redirect to login if not authenticated
 * @returns {Object} Current user object
 * @throws {Error} If not authenticated
 */
function requireAuth() {
    const u = getCurrentUser();
    const token = getFirebaseToken();

    if (!u || !token) {
        if (!isRedirecting) {
            isRedirecting = true;
            console.log('Not authenticated, redirecting to login');
            window.location.href = "login.html";
        }
        throw new Error("Not authenticated");
    }

    return u;
}

/**
 * Sign out current user
 * Works with or without Firebase client SDK
 */
async function signOut() {
    // Try to sign out from Firebase client SDK if available
    if (typeof firebase !== 'undefined' && firebase.auth && firebase.auth()) {
        try {
            await firebase.auth().signOut();
        } catch (e) {
            console.warn("Firebase client signout not available:", e);
        }
    }

    // Always clear session storage
    clearCurrentUser();
    isRedirecting = false; // Reset redirect flag
    window.location.href = "login.html";
}

/**
 * Register a new user with BACKEND Firebase Authentication
 * This version works WITHOUT Firebase client SDK - backend handles everything
 * @param {Object} userData - {user_id, name, email, password, role}
 * @returns {Promise<Object>} User data and token
 */
async function registerWithFirebase(userData) {
    const { user_id, name, email, password, role = 'staff' } = userData;

    // Validate inputs
    if (!user_id || !name || !email || !password) {
        throw new Error("All fields are required");
    }

    if (password.length < 6) {
        throw new Error("Password must be at least 6 characters");
    }

    try {
        // Call backend to create user - backend handles Firebase Auth creation
        const response = await fetch(`${API_BASE}/api/users/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id, name, email, password, role })
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || 'Registration failed');
        }

        // Store user data and JWT token from backend
        setCurrentUser(result.user, result.firebaseToken);

        return { user: result.user, token: result.firebaseToken };

    } catch (error) {
        console.error("Registration error:", error);
        throw error;
    }
}

/**
 * Login with email and password using BACKEND Firebase Authentication
 * This version works WITHOUT Firebase client SDK - backend handles everything
 * @param {string} email - User email
 * @param {string} password - User password
 * @returns {Promise<Object>} User data and token
 */
async function loginWithFirebase(email, password) {
    if (!email || !password) {
        throw new Error("Email and password are required");
    }

    try {
        // Call backend login endpoint - backend handles Firebase Auth
        const response = await fetch(`${API_BASE}/api/users/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });

        const result = await response.json();

        if (!response.ok) {
            // Extract error message from backend response
            const errorMessage = result.error || 'Login failed';
            throw new Error(errorMessage);
        }

        // Store user data and JWT token from backend
        setCurrentUser(result.user, result.firebaseToken);

        return { user: result.user, token: result.firebaseToken };

    } catch (error) {
        console.error("Login error:", error);

        // Provide user-friendly error messages
        if (error.message.includes('not found') || error.message.includes('User not found')) {
            throw new Error("No account found with this email");
        } else if (error.message.includes('password') || error.message.includes('Invalid credentials')) {
            throw new Error("Incorrect password");
        } else if (error.message.includes('email')) {
            throw new Error("Invalid email address");
        } else {
            throw error;
        }
    }
}

/**
 * Verify current session is valid (with throttling to prevent API spam)
 * @returns {Promise<boolean>} True if session is valid
 */
async function verifySession() {
    const token = getFirebaseToken();

    if (!token) {
        return false;
    }

    const now = Date.now();

    // If we're already verifying or recently verified, return the existing promise or cached result
    if (verifyPromise) {
        return verifyPromise;
    }

    if (now - lastVerifyTime < VERIFY_THROTTLE_MS) {
        // Return cached result if recently verified
        return true; // Assume valid if recently checked
    }

    // Create new verification promise
    verifyPromise = (async () => {
        try {
            const response = await fetch(`${API_BASE}/api/users/auth/verify`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ firebase_token: token })
            });

            const result = await response.json();

            if (response.ok && result.valid) {
                // Update user data if changed
                setCurrentUser(result.user, token);
                lastVerifyTime = now;
                return true;
            }

            return false;

        } catch (error) {
            console.error("Session verification error:", error);
            return false;
        } finally {
            // Clear the promise after completion
            verifyPromise = null;
        }
    })();

    return verifyPromise;
}

// ============================================================================
// Enhanced Fetch with Firebase Token
// ============================================================================

// Patch fetch to add Firebase token and X-User-Id header
(function () {
    const _fetch = window.fetch;
    window.fetch = function (resource, init) {
        init = init || {};
        init.headers = init.headers || {};

        const token = getFirebaseToken();
        const u = getCurrentUser();

        // Add Firebase token to Authorization header
        if (token) {
            if (init.headers instanceof Headers) {
                init.headers.set("Authorization", `Bearer ${token}`);
            } else if (typeof init.headers === "object") {
                init.headers["Authorization"] = `Bearer ${token}`;
            }
        }

        // Add X-User-Id header for backward compatibility
        if (u && u.user_id) {
            if (init.headers instanceof Headers) {
                init.headers.set("X-User-Id", u.user_id);
            } else if (typeof init.headers === "object") {
                init.headers["X-User-Id"] = u.user_id;
            }
        }

        return _fetch(resource, init);
    };
})();

// ============================================================================
// Utility Functions
// ============================================================================

function el(id) {
    return document.getElementById(id);
}

/**
 * Get role badge HTML
 * @param {string} role - User role
 * @returns {string} HTML for role badge
 */
function getRoleBadge(role) {
    const badges = {
        'admin': '<span style="background:#dc3545;color:white;padding:2px 8px;border-radius:12px;font-size:10px;margin-left:4px">👑 ADMIN</span>',
        'manager': '<span style="background:#667eea;color:white;padding:2px 8px;border-radius:12px;font-size:10px;margin-left:4px">👔 MANAGER</span>',
        'director': '<span style="background:#764ba2;color:white;padding:2px 8px;border-radius:12px;font-size:10px;margin-left:4px">💼 DIRECTOR</span>',
        'hr': '<span style="background:#f093fb;color:white;padding:2px 8px;border-radius:12px;font-size:10px;margin-left:4px">👥 HR</span>',
        'staff': '<span style="background:#a8edea;color:#333;padding:2px 8px;border-radius:12px;font-size:10px;margin-left:4px">👤 STAFF</span>'
    };
    return badges[role] || badges['staff'];
}

// ============================================================================
// Navigation Bar (Updated for Role-Based Navigation)
// ============================================================================

async function buildNavbar() {
    const host = document.getElementById("nav");
    if (!host) return;

    const u = getCurrentUser();
    const p = getCurrentProject();
    const userRole = u?.role || 'staff';

    // Show login status badge
    let loginStatus = '';
    if (u) {
        const token = getFirebaseToken();
        if (token) {
            loginStatus = '<span style="background:#28a745;color:white;padding:2px 8px;border-radius:12px;font-size:10px;margin-left:8px">🔒 Authenticated</span>';
        } else {
            loginStatus = '<span style="background:#ffc107;color:black;padding:2px 8px;border-radius:12px;font-size:10px;margin-left:8px">⚠️ Session</span>';
        }
    }

    // Build navigation links based on role
    let navLinks = '';

    // Role-specific dashboard links
    if (userRole === 'admin') {
        navLinks += `
            <a href="admin_dashboard.html">Admin Dashboard</a>
        `;
    } else if (['manager', 'director', 'hr'].includes(userRole)) {
        navLinks += `
            <a href="manager_dashboard.html">Manager Dashboard</a>
            <a href="dashboard.html">My Dashboard</a>
        `;
    } else {
        navLinks += `
            <a href="dashboard.html">Dashboard</a>
        `;
    }

    // Common task/project links
    navLinks += `
        <a href="projects.html">Projects</a>
        <a href="tasks_list.html">Tasks</a>
        <a href="create_task.html">Create Task</a>
    `;

    // Manager-only link
    if (['manager', 'director', 'hr'].includes(userRole)) {
        navLinks += `
            <a href="manager_team_view.html">Team View</a>
        `;
    }

    host.innerHTML = `
    <div style="display:flex;gap:12px;align-items:center;justify-content:space-between;padding:10px;border-bottom:1px solid #eee;background:white">
      <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap">
        ${navLinks}
      </div>
            <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;font-size:12px;color:#333">
                ${p ? `<span style="font-size:12px;color:#666">Project selected <button id=\"clearProjectBtnSmall\" style=\"margin-left:6px;padding:4px 6px;border-radius:6px;border:1px solid #eaeaea;background:#fff;font-size:11px;cursor:pointer\">Clear</button></span>` : ''}
                <span>User: <em>${u ? (u.name || u.user_id || u.email || "signed-in") : "guest"}</em>${u ? getRoleBadge(userRole) : ''}${loginStatus}</span>
        ${u ? '<button id="logoutBtn" style="cursor:pointer;padding:6px 12px;background:#dc3545;color:white;border:none;border-radius:4px">Sign out</button>' : '<a href="login.html" style="padding:6px 12px;background:#667eea;color:white;border-radius:4px;text-decoration:none">Login</a>'}
      </div>
    </div>
  `;

    const btn = document.getElementById("logoutBtn");
    if (btn) btn.addEventListener("click", signOut);
}

document.addEventListener("DOMContentLoaded", buildNavbar);
// Attach clear control handler (if present) after DOM ready
document.addEventListener('click', function (e) {
    if (e.target && e.target.id === 'clearProjectBtnSmall') {
        try { sessionStorage.removeItem('currentProject'); window.location.reload(); } catch (e) { }
    }
});