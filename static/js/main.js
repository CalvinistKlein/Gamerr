// Romerr - Main JavaScript

document.addEventListener('DOMContentLoaded', function() {
    console.log('Romerr UI loaded');
    
    // Initialize tooltips
    initTooltips();
    
    // Initialize form validation
    initForms();
    
    // Initialize real-time updates
    initRealTimeUpdates();

    // Initialize header actions
    initHeaderActions();
});

function initHeaderActions() {
    // Global search input
    const searchInput = document.getElementById('global-search-input');
    if (searchInput) {
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                const query = this.value.trim();
                if (query) {
                    window.location.href = `/catalog?q=${encodeURIComponent(query)}`;
                }
            }
        });
    }

    // Notifications button
    const notificationsBtn = document.getElementById('notifications-btn');
    if (notificationsBtn) {
        notificationsBtn.addEventListener('click', function() {
            showNotification('You have no new notifications', 'info');
            // Reset badge
            const badge = document.getElementById('notifications-badge');
            if (badge) {
                badge.style.display = 'none';
            }
        });
    }

    // Activity button
    const activityBtn = document.getElementById('activity-btn');
    if (activityBtn) {
        activityBtn.addEventListener('click', function() {
            window.location.href = '/downloads';
        });
    }
}

function initTooltips() {
    // Add tooltip functionality to elements with data-tooltip attribute
    const tooltipElements = document.querySelectorAll('[data-tooltip]');
    
    tooltipElements.forEach(element => {
        element.addEventListener('mouseenter', function(e) {
            const tooltipText = this.getAttribute('data-tooltip');
            const tooltip = document.createElement('div');
            tooltip.className = 'tooltip';
            tooltip.textContent = tooltipText;
            document.body.appendChild(tooltip);
            
            const rect = this.getBoundingClientRect();
            tooltip.style.position = 'fixed';
            tooltip.style.left = rect.left + rect.width / 2 - tooltip.offsetWidth / 2 + 'px';
            tooltip.style.top = rect.top - tooltip.offsetHeight - 10 + 'px';
            tooltip.style.backgroundColor = 'rgba(26, 26, 26, 0.95)';
            tooltip.style.color = '#f0f0f0';
            tooltip.style.padding = '5px 10px';
            tooltip.style.borderRadius = '4px';
            tooltip.style.fontSize = '12px';
            tooltip.style.zIndex = '1000';
            tooltip.style.border = '1px solid #333';
            
            this._tooltip = tooltip;
        });
        
        element.addEventListener('mouseleave', function() {
            if (this._tooltip) {
                this._tooltip.remove();
                this._tooltip = null;
            }
        });
    });
}

function initForms() {
    // Form validation for search forms
    const searchForms = document.querySelectorAll('form.search-form');
    
    searchForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const input = this.querySelector('input[type="text"]');
            if (input && input.value.trim() === '') {
                e.preventDefault();
                showNotification('Please enter a search term', 'warning');
                input.focus();
            }
        });
    });
}

function initRealTimeUpdates() {
    // Check for updates every 30 seconds
    setInterval(() => {
        updateStats();
    }, 30000);
}

function updateStats() {
    // Fetch updated stats from API
    fetch('/api/stats')
        .then(response => response.json())
        .then(data => {
            // Update any elements with data-stat attributes
            document.querySelectorAll('[data-stat]').forEach(element => {
                const stat = element.getAttribute('data-stat');
                if (data[stat] !== undefined) {
                    element.textContent = data[stat];
                }
            });
        })
        .catch(error => console.error('Error fetching stats:', error));
    
    // Fetch storage info
    fetch('/api/system/storage')
        .then(response => response.json())
        .then(data => {
            const storageElement = document.getElementById('storage-value');
            if (storageElement) {
                storageElement.textContent = `${data.roms_gb} GB`;
            }
        })
        .catch(error => console.error('Error fetching storage stats:', error));
}

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    
    // Style the notification
    notification.style.position = 'fixed';
    notification.style.top = '20px';
    notification.style.right = '20px';
    notification.style.padding = '15px 20px';
    notification.style.borderRadius = '6px';
    notification.style.zIndex = '10000';
    notification.style.fontWeight = '500';
    notification.style.boxShadow = '0 5px 15px rgba(0, 0, 0, 0.3)';
    notification.style.animation = 'slideIn 0.3s ease';
    
    // Set colors based on type
    const colors = {
        info: { bg: '#2d8cf0', text: '#fff' },
        success: { bg: '#3ecf6e', text: '#fff' },
        warning: { bg: '#e8871a', text: '#fff' },
        error: { bg: '#ff4757', text: '#fff' }
    };
    
    notification.style.backgroundColor = colors[type]?.bg || colors.info.bg;
    notification.style.color = colors[type]?.text || colors.info.text;
    
    document.body.appendChild(notification);
    
    // Remove notification after 5 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }, 5000);
}

// Add CSS animations for notifications
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// Utility function for making API calls
async function apiCall(endpoint, method = 'GET', data = null) {
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json',
        },
    };
    
    if (data && (method === 'POST' || method === 'PUT')) {
        options.body = JSON.stringify(data);
    }
    
    try {
        const response = await fetch(`/api${endpoint}`, options);
        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.message || 'API request failed');
        }
        
        return result;
    } catch (error) {
        console.error('API call failed:', error);
        showNotification(`API Error: ${error.message}`, 'error');
        throw error;
    }
}

// Catalog functionality
function initCatalog() {
    const addToWantedButtons = document.querySelectorAll('.add-to-wanted-btn');
    
    addToWantedButtons.forEach(button => {
        button.addEventListener('click', async function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            const catalogId = this.getAttribute('data-catalog-id');
            const gameTitle = this.getAttribute('data-game-title');
            
            if (!catalogId) {
                console.error('No catalog ID found on button');
                return;
            }
            
            // Disable button and show loading state
            const originalText = this.innerHTML;
            this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Adding...';
            this.disabled = true;
            
            try {
                const response = await apiCall(`/api/catalog/${catalogId}/add-to-wanted`, {
                    method: 'POST'
                });
                
                if (response.success) {
                    showNotification(`Added "${gameTitle}" to wanted list`, 'success');
                    
                    // Update button state
                    this.innerHTML = '<i class="fas fa-check"></i> Added';
                    this.style.backgroundColor = '#2da855';
                    this.style.cursor = 'default';
                    
                    // Add a small delay before removing the button
                    setTimeout(() => {
                        this.remove();
                    }, 2000);
                } else {
                    showNotification(response.message || 'Failed to add to wanted list', 'warning');
                    
                    // Reset button
                    this.innerHTML = originalText;
                    this.disabled = false;
                }
            } catch (error) {
                console.error('Failed to add to wanted list:', error);
                showNotification('Failed to add to wanted list. Please try again.', 'error');
                
                // Reset button
                this.innerHTML = originalText;
                this.disabled = false;
            }
        });
    });
}

// Dashboard functionality
function initDashboard() {
    // ellipsis button on activity card
    const activityEllipsis = document.getElementById('activity-ellipsis-btn');
    if (activityEllipsis) {
        activityEllipsis.addEventListener('click', () => {
            showNotification('History log is currently empty. Start searching or downloading games!', 'info');
        });
    }

    // Health badge
    const healthBadge = document.querySelector('.card-header .badge-success');
    if (healthBadge) {
        fetch('/api/health')
            .then(res => res.json())
            .then(data => {
                if (data.status === 'healthy') {
                    healthBadge.textContent = 'All Systems Operational';
                    healthBadge.className = 'badge badge-success';
                }
            })
            .catch(err => {
                healthBadge.textContent = 'System Status Uncertain';
                healthBadge.className = 'badge badge-warning';
            });
    }
}

// Initialize catalog functionality when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('Romerr UI loaded');
    
    // Initialize tooltips
    initTooltips();
    
    // Initialize form validation
    initForms();
    
    // Initialize real-time updates
    initRealTimeUpdates();
    
    // Initialize catalog functionality
    initCatalog();
});