// =============================================
// Dark Mode Theme System
// =============================================

/**
 * Initialize theme on page load
 * Priority: localStorage > system preference > light mode default
 */
function initTheme() {
    const savedTheme = localStorage.getItem('theme');
    const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

    if (savedTheme) {
        document.documentElement.setAttribute('data-theme', savedTheme);
    } else if (systemDark) {
        document.documentElement.setAttribute('data-theme', 'dark');
    } else {
        document.documentElement.setAttribute('data-theme', 'light');
    }

    updateThemeIcon();
    updateMetaThemeColor();
}

/**
 * Toggle between light and dark themes
 */
function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);

    updateThemeIcon();
    updateMetaThemeColor();
}

/**
 * Update theme toggle icon (sun/moon)
 */
function updateThemeIcon() {
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';

    // Update desktop icon
    const themeIcon = document.getElementById('themeIcon');
    if (themeIcon) {
        themeIcon.className = isDark ? 'fas fa-moon' : 'fas fa-sun';
    }

    // Update mobile icon and label
    const mobileThemeIcon = document.getElementById('mobileThemeIcon');
    const mobileThemeLabel = document.getElementById('mobileThemeLabel');
    if (mobileThemeIcon) {
        mobileThemeIcon.className = isDark ? 'fas fa-sun' : 'fas fa-moon';
    }
    if (mobileThemeLabel) {
        mobileThemeLabel.textContent = isDark ? 'Light Mode' : 'Dark Mode';
    }
}

/**
 * Update the browser theme color meta tag
 */
function updateMetaThemeColor() {
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    const metaThemeColor = document.querySelector('meta[name="theme-color"]');
    if (metaThemeColor) {
        metaThemeColor.content = isDark ? '#111827' : '#1e4d8b';
    }
}

// Initialize theme immediately (before DOM fully loads to prevent flash)
initTheme();

// Listen for system preference changes
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
    // Only auto-switch if user hasn't set a preference
    if (!localStorage.getItem('theme')) {
        document.documentElement.setAttribute('data-theme', e.matches ? 'dark' : 'light');
        updateThemeIcon();
        updateMetaThemeColor();
    }
});

// Also run on DOMContentLoaded to ensure icons are updated
document.addEventListener('DOMContentLoaded', function() {
    updateThemeIcon();
});

// =============================================
// End Dark Mode Theme System
// =============================================

// =============================================
// Skeleton Loader Management
// =============================================

/**
 * Show skeleton loaders in a container
 * @param {string} containerId - ID of the skeleton container
 */
function showSkeletons(containerId) {
    const container = document.getElementById(containerId);
    if (container) {
        container.classList.remove('hidden');
        container.style.display = 'block';
    }
}

/**
 * Hide skeleton loaders
 * @param {string} containerId - ID of the skeleton container
 */
function hideSkeletons(containerId) {
    const container = document.getElementById(containerId);
    if (container) {
        container.classList.add('hidden');
        setTimeout(() => {
            container.style.display = 'none';
        }, 300); // Match CSS transition duration
    }
}

/**
 * Show content container
 * @param {string} containerId - ID of the content container
 */
function showContent(containerId) {
    const container = document.getElementById(containerId);
    if (container) {
        container.classList.remove('loading');
        container.style.display = 'block';
    }
}

/**
 * Generate skeleton comment HTML
 * @param {number} count - Number of skeleton comments to generate
 * @returns {string} HTML string of skeleton comments
 */
function generateSkeletonComments(count = 2) {
    let html = '';
    for (let i = 0; i < count; i++) {
        html += `
            <div class="skeleton-comment">
                <div class="skeleton skeleton-avatar-sm"></div>
                <div class="skeleton-comment-content">
                    <div class="skeleton skeleton-text skeleton-text-short" style="height: 12px;"></div>
                    <div class="skeleton skeleton-text" style="height: 12px;"></div>
                </div>
            </div>
        `;
    }
    return html;
}

/**
 * Initialize skeleton loading behavior on page load
 * Automatically transitions from skeletons to content
 */
function initSkeletonLoaders() {
    const skeletonContainer = document.getElementById('skeletonContainer');
    const postsContainer = document.getElementById('postsContainer');

    if (skeletonContainer && postsContainer) {
        // Show skeletons initially
        skeletonContainer.style.display = 'block';
        postsContainer.classList.add('loading');

        // Transition to actual content after brief delay
        // This gives a consistent loading feel even on fast connections
        setTimeout(() => {
            hideSkeletons('skeletonContainer');
            showContent('postsContainer');
        }, 150);
    }
}

// Initialize skeleton loaders on DOMContentLoaded
document.addEventListener('DOMContentLoaded', function() {
    initSkeletonLoaders();
});

// =============================================
// End Skeleton Loader Management
// =============================================

// Smooth scrolling for navigation links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// Add scroll effect to navigation (theme-aware)
window.addEventListener('scroll', function() {
    const nav = document.querySelector('nav');
    if (nav) {
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        if (window.scrollY > 50) {
            nav.style.background = isDark ? 'rgba(17, 24, 39, 0.98)' : 'rgba(255, 255, 255, 0.98)';
            nav.style.boxShadow = isDark ? '0 2px 20px rgba(0,0,0,0.3)' : '0 2px 20px rgba(0,0,0,0.1)';
        } else {
            nav.style.background = isDark ? 'rgba(17, 24, 39, 0.95)' : 'rgba(255, 255, 255, 0.95)';
            nav.style.boxShadow = isDark ? '0 2px 10px rgba(0,0,0,0.2)' : '0 2px 10px rgba(0,0,0,0.1)';
        }
    }
});

// Add hover effect to feature cards
const featureCards = document.querySelectorAll('.feature-card');
featureCards.forEach(card => {
    card.addEventListener('mouseenter', function() {
        this.style.transform = 'translateY(-5px) scale(1.02)';
    });
    card.addEventListener('mouseleave', function() {
        this.style.transform = 'translateY(0) scale(1)';
    });
});