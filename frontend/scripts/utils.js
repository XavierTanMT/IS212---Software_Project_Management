/* ============================================
   UTILITY FUNCTIONS - Shared helper functions
   ============================================ */

// Common DOM manipulation utilities
function q(selector) {
    return document.querySelector(selector);
}

function qAll(selector) {
    return document.querySelectorAll(selector);
}

function ce(tagName) {
    return document.createElement(tagName);
}

function hide(element) {
    if (typeof element === 'string') element = q(element);
    if (element) element.style.display = 'none';
}

function show(element, displayType = 'block') {
    if (typeof element === 'string') element = q(element);
    if (element) element.style.display = displayType;
}

function toggleVisibility(element) {
    if (typeof element === 'string') element = q(element);
    if (element) {
        element.style.display = element.style.display === 'none' ? 'block' : 'none';
    }
}

// Date/Time formatting utilities
function fmtDate(dateString) {
    try {
        return new Date(dateString).toLocaleString();
    } catch (e) {
        return dateString;
    }
}

function fmtDateShort(dateString) {
    try {
        return new Date(dateString).toLocaleDateString();
    } catch (e) {
        return dateString;
    }
}

function fmtTime(dateString) {
    try {
        return new Date(dateString).toLocaleTimeString();
    } catch (e) {
        return dateString;
    }
}

function isDatePast(dateString) {
    try {
        return new Date(dateString) < new Date();
    } catch (e) {
        return false;
    }
}

// String utilities
function capitalize(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
}

function truncate(str, maxLength = 50) {
    return str.length > maxLength ? str.substring(0, maxLength) + '...' : str;
}

// Number utilities
function formatNumber(num) {
    return new Intl.NumberFormat().format(num);
}

// API utilities
async function fetchJSON(url, options = {}) {
    try {
        const response = await fetch(url, options);
        const data = await response.json();
        return { ok: response.ok, status: response.status, data };
    } catch (error) {
        console.error('Fetch error:', error);
        return { ok: false, error: error.message };
    }
}

async function postJSON(url, payload) {
    return fetchJSON(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
}

async function putJSON(url, payload) {
    return fetchJSON(url, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
}

async function deleteJSON(url) {
    return fetchJSON(url, {
        method: 'DELETE'
    });
}

// Form utilities
function getFormData(formId) {
    const form = typeof formId === 'string' ? q(formId) : formId;
    if (!form) return {};
    
    const formData = new FormData(form);
    const data = {};
    for (let [key, value] of formData.entries()) {
        data[key] = value;
    }
    return data;
}

function resetForm(formId) {
    const form = typeof formId === 'string' ? q(formId) : formId;
    if (form) form.reset();
}

function disableForm(formId, disabled = true) {
    const form = typeof formId === 'string' ? q(formId) : formId;
    if (!form) return;
    
    const elements = form.querySelectorAll('input, select, textarea, button');
    elements.forEach(el => el.disabled = disabled);
}

// Button state management
function setButtonLoading(button, loading = true, originalText = null) {
    if (typeof button === 'string') button = q(button);
    if (!button) return;
    
    if (loading) {
        button.dataset.originalText = originalText || button.textContent;
        button.textContent = 'Loading...';
        button.disabled = true;
    } else {
        button.textContent = button.dataset.originalText || originalText || 'Submit';
        button.disabled = false;
    }
}

// Message/Alert utilities
function showMessage(message, type = 'info', containerId = 'message') {
    const container = q('#' + containerId);
    if (!container) {
        alert(message);
        return;
    }
    
    container.textContent = message;
    container.className = `message ${type}`;
    container.style.display = 'block';
}

function hideMessage(containerId = 'message') {
    const container = q('#' + containerId);
    if (container) {
        container.style.display = 'none';
    }
}

function showSuccess(message, containerId = 'message') {
    showMessage(message, 'success', containerId);
}

function showError(message, containerId = 'message') {
    showMessage(message, 'error', containerId);
}

function showInfo(message, containerId = 'message') {
    showMessage(message, 'info', containerId);
}

function showWarning(message, containerId = 'message') {
    showMessage(message, 'warning', containerId);
}

// Loading spinner utilities
function showLoading(containerId = 'loading') {
    show('#' + containerId);
}

function hideLoading(containerId = 'loading') {
    hide('#' + containerId);
}

// Validation utilities
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

function isValidUrl(url) {
    try {
        new URL(url);
        return true;
    } catch (e) {
        return false;
    }
}

function isEmpty(value) {
    return value === null || value === undefined || value === '' || 
           (Array.isArray(value) && value.length === 0) ||
           (typeof value === 'object' && Object.keys(value).length === 0);
}

// Storage utilities
function saveToLocalStorage(key, value) {
    try {
        localStorage.setItem(key, JSON.stringify(value));
        return true;
    } catch (e) {
        console.error('LocalStorage save error:', e);
        return false;
    }
}

function getFromLocalStorage(key, defaultValue = null) {
    try {
        const item = localStorage.getItem(key);
        return item ? JSON.parse(item) : defaultValue;
    } catch (e) {
        console.error('LocalStorage get error:', e);
        return defaultValue;
    }
}

function removeFromLocalStorage(key) {
    try {
        localStorage.removeItem(key);
        return true;
    } catch (e) {
        console.error('LocalStorage remove error:', e);
        return false;
    }
}

// Debounce utility
function debounce(func, wait = 300) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Throttle utility
function throttle(func, limit = 300) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// Array utilities
function groupBy(array, key) {
    return array.reduce((result, item) => {
        const group = item[key];
        if (!result[group]) {
            result[group] = [];
        }
        result[group].push(item);
        return result;
    }, {});
}

function sortBy(array, key, ascending = true) {
    return [...array].sort((a, b) => {
        const aVal = a[key];
        const bVal = b[key];
        if (aVal < bVal) return ascending ? -1 : 1;
        if (aVal > bVal) return ascending ? 1 : -1;
        return 0;
    });
}

function uniqueBy(array, key) {
    const seen = new Set();
    return array.filter(item => {
        const val = item[key];
        if (seen.has(val)) return false;
        seen.add(val);
        return true;
    });
}

// Export utilities for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        q, qAll, ce, hide, show, toggleVisibility,
        fmtDate, fmtDateShort, fmtTime, isDatePast,
        capitalize, truncate, formatNumber,
        fetchJSON, postJSON, putJSON, deleteJSON,
        getFormData, resetForm, disableForm,
        setButtonLoading,
        showMessage, hideMessage, showSuccess, showError, showInfo, showWarning,
        showLoading, hideLoading,
        isValidEmail, isValidUrl, isEmpty,
        saveToLocalStorage, getFromLocalStorage, removeFromLocalStorage,
        debounce, throttle,
        groupBy, sortBy, uniqueBy
    };
}
