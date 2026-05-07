// API base URL candidates. Same-origin works when FastAPI serves the frontend;
// localhost fallbacks keep the UI working when opened from a static server.
const API_BASE_CANDIDATES = getApiBaseCandidates();
let activeApiBase = null;

// Global state
let currentSessionId = null;
let activeQueryController = null;
let chatVersion = 0;

// DOM elements
let chatMessages, chatInput, sendButton, newChatButton, totalCourses, courseTitles;

function getApiBaseCandidates() {
    const candidates = [];

    if (window.location.protocol === 'http:' || window.location.protocol === 'https:') {
        candidates.push(`${window.location.origin}/api`);
    }

    candidates.push(
        'http://localhost:8000/api',
        'http://127.0.0.1:8000/api',
        'http://localhost:8001/api',
        'http://127.0.0.1:8001/api'
    );

    return [...new Set(candidates)];
}

function shouldTryNextApiBase(response) {
    return response.status === 404 || response.status === 405;
}

async function apiFetch(path, options = {}) {
    const bases = activeApiBase
        ? [activeApiBase, ...API_BASE_CANDIDATES.filter(base => base !== activeApiBase)]
        : API_BASE_CANDIDATES;
    let lastError = null;

    for (const base of bases) {
        try {
            const response = await fetch(`${base}${path}`, options);

            if (shouldTryNextApiBase(response)) {
                lastError = new Error(`API endpoint unavailable at ${base}`);
                continue;
            }

            activeApiBase = base;
            return response;
        } catch (error) {
            if (error.name === 'AbortError') throw error;
            lastError = error;
        }
    }

    throw lastError || new Error('Failed to connect to the API');
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Get DOM elements after page loads
    chatMessages = document.getElementById('chatMessages');
    chatInput = document.getElementById('chatInput');
    sendButton = document.getElementById('sendButton');
    newChatButton = document.getElementById('newChatButton');
    totalCourses = document.getElementById('totalCourses');
    courseTitles = document.getElementById('courseTitles');
    
    setupEventListeners();
    createNewSession();
    loadCourseStats();
});

// Event Listeners
function setupEventListeners() {
    // Chat functionality
    sendButton.addEventListener('click', sendMessage);
    newChatButton.addEventListener('click', createNewSession);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });
    
    
    // Suggested questions
    document.querySelectorAll('.suggested-item').forEach(button => {
        button.addEventListener('click', (e) => {
            const question = e.target.getAttribute('data-question');
            chatInput.value = question;
            sendMessage();
        });
    });
}


// Chat Functions
async function sendMessage() {
    if (chatInput.disabled || sendButton.disabled) return;

    const query = chatInput.value.trim();
    if (!query) return;
    if (!currentSessionId) {
        try {
            currentSessionId = await startBackendSession(null);
        } catch (error) {
            addMessage(`Error: ${error.message}`, 'assistant');
            return;
        }
    }

    // Disable input
    chatInput.value = '';
    chatInput.disabled = true;
    sendButton.disabled = true;
    const requestSessionId = currentSessionId;
    const requestChatVersion = chatVersion;
    activeQueryController = new AbortController();

    // Add user message
    addMessage(query, 'user');

    // Add loading message - create a unique container for it
    const loadingMessage = createLoadingMessage();
    chatMessages.appendChild(loadingMessage);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    try {
        const response = await apiFetch('/query', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: query,
                session_id: requestSessionId
            }),
            signal: activeQueryController.signal
        });

        if (!response.ok) throw new Error('Query failed');

        const data = await response.json();

        if (requestChatVersion !== chatVersion || data.session_id !== currentSessionId) {
            loadingMessage.remove();
            return;
        }

        // Replace loading message with response
        loadingMessage.remove();
        addMessage(data.answer, 'assistant', data.sources);

    } catch (error) {
        if (error.name === 'AbortError') {
            loadingMessage.remove();
            return;
        }

        if (requestChatVersion !== chatVersion || requestSessionId !== currentSessionId) {
            loadingMessage.remove();
            return;
        }

        // Replace loading message with error
        loadingMessage.remove();
        addMessage(`Error: ${error.message}`, 'assistant');
    } finally {
        if (activeQueryController && activeQueryController.signal.aborted) {
            activeQueryController = null;
        } else if (requestChatVersion === chatVersion && requestSessionId === currentSessionId) {
            activeQueryController = null;
            chatInput.disabled = false;
            sendButton.disabled = false;
            chatInput.focus();
        }
    }
}

function createLoadingMessage() {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant';
    messageDiv.innerHTML = `
        <div class="message-content">
            <div class="loading">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
    `;
    return messageDiv;
}

function addMessage(content, type, sources = null, isWelcome = false) {
    const messageId = Date.now();
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}${isWelcome ? ' welcome-message' : ''}`;
    messageDiv.id = `message-${messageId}`;
    
    // Convert markdown to HTML for assistant messages
    const displayContent = type === 'assistant' ? marked.parse(content) : escapeHtml(content);
    
    let html = `<div class="message-content">${displayContent}</div>`;
    
    if (sources && sources.length > 0) {
        const sourceItems = sources
            .map(source => `<span class="source-chip">${source}</span>`)
            .join('');

        html += `
            <details class="sources-collapsible">
                <summary class="sources-header">Sources</summary>
                <div class="sources-content">${sourceItems}</div>
            </details>
        `;
    }
    
    messageDiv.innerHTML = html;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    return messageId;
}

// Helper function to escape HTML for user messages
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Removed removeMessage function - no longer needed since we handle loading differently

async function startBackendSession(previousSessionId) {
    const response = await apiFetch('/session', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            session_id: previousSessionId
        })
    });

    if (!response.ok) throw new Error('Failed to start new session');

    const data = await response.json();
    return data.session_id;
}

function resetChatWindow() {
    chatMessages.innerHTML = '';
    addMessage('Welcome to the Course Materials Assistant! I can help you with questions about courses, lessons and specific content. What would you like to know?', 'assistant', null, true);
}

async function createNewSession() {
    const previousSessionId = currentSessionId;
    const nextChatVersion = chatVersion + 1;
    chatVersion = nextChatVersion;

    if (activeQueryController) {
        activeQueryController.abort();
        activeQueryController = null;
    }

    chatInput.value = '';
    chatInput.disabled = true;
    sendButton.disabled = true;
    newChatButton.disabled = true;

    try {
        currentSessionId = await startBackendSession(previousSessionId);
    } catch (error) {
        console.error('Error creating new session:', error);
        currentSessionId = null;
    } finally {
        if (nextChatVersion === chatVersion) {
            resetChatWindow();
            chatInput.disabled = false;
            sendButton.disabled = false;
            newChatButton.disabled = false;
            chatInput.focus();
        }
    }
}

// Load course statistics
async function loadCourseStats() {
    try {
        console.log('Loading course stats...');
        const response = await apiFetch('/courses');
        if (!response.ok) throw new Error('Failed to load course stats');
        
        const data = await response.json();
        console.log('Course data received:', data);
        
        // Update stats in UI
        if (totalCourses) {
            totalCourses.textContent = data.total_courses;
        }
        
        // Update course titles
        if (courseTitles) {
            if (data.course_titles && data.course_titles.length > 0) {
                courseTitles.innerHTML = data.course_titles
                    .map(title => `<div class="course-title-item">${title}</div>`)
                    .join('');
            } else {
                courseTitles.innerHTML = '<span class="no-courses">No courses available</span>';
            }
        }
        
    } catch (error) {
        console.error('Error loading course stats:', error);
        // Set default values on error
        if (totalCourses) {
            totalCourses.textContent = '0';
        }
        if (courseTitles) {
            courseTitles.innerHTML = '<span class="error">Failed to load courses</span>';
        }
    }
}
