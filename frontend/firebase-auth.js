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
        window.location.href = "login.html";
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
    window.location.href = "login.html";
}

/**
 * Register a new user with BACKEND Firebase Authentication
 * This version works WITHOUT Firebase client SDK - backend handles everything
 * @param {Object} userData - {user_id, name, email, password}
 * @returns {Promise<Object>} User data and token
 */
async function registerWithFirebase(userData) {
    const { user_id, name, email, password } = userData;
    
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
            body: JSON.stringify({ user_id, name, email, password })
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
 * Verify current session is valid
 * @returns {Promise<boolean>} True if session is valid
 */
async function verifySession() {
    const token = getFirebaseToken();
    
    if (!token) {
        return false;
    }
    
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
            return true;
        }
        
        return false;
        
    } catch (error) {
        console.error("Session verification error:", error);
        return false;
    }
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

// ============================================================================
// Navigation Bar
// ============================================================================

async function buildNavbar() {
    const host = document.getElementById("nav");
    if (!host) return;
    
    const u = getCurrentUser();
    const p = getCurrentProject();
    
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
    
    host.innerHTML = `
    <div style="display:flex;gap:12px;align-items:center;justify-content:space-between;padding:10px;border-bottom:1px solid #eee;background:white">
      <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap">
        <a href="index.html"><strong>🔥 TaskMgr</strong></a>
        <a href="dashboard.html">Dashboard</a>
        <a href="projects.html">Projects</a>
        <a href="tasks_list.html">Tasks</a>
        <a href="create_task.html">Create Task</a>
      </div>
      <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;font-size:12px;color:#333">
        <span>Project: <em>${p ? (p.name || p.project_id || "selected") : "none"}</em></span>
        <span>User: <em>${u ? (u.name || u.user_id || u.email || "signed-in") : "guest"}</em>${loginStatus}</span>
        ${u ? '<button id="logoutBtn" style="cursor:pointer;padding:6px 12px;background:#dc3545;color:white;border:none;border-radius:4px">Sign out</button>' : '<a href="login.html" style="padding:6px 12px;background:#667eea;color:white;border-radius:4px;text-decoration:none">Login</a>'}
      </div>
    </div>
  `;
    
    const btn = document.getElementById("logoutBtn");
    if (btn) btn.addEventListener("click", signOut);
}

document.addEventListener("DOMContentLoaded", buildNavbar);
