/**
 * Capacitor Page Transitions & Gestures
 * Provides native-feeling page transitions, edge-swipe-back, and
 * enhanced pull-to-refresh when running inside Capacitor.
 * Exits immediately in browser -- zero impact on web.
 */
(function() {
    'use strict';

    // Only run inside Capacitor native shell
    if (!window.Capacitor || !window.Capacitor.isNativePlatform()) {
        return;
    }

    var MRPNative = window.MRPNative || {};
    var mainEl = document.querySelector('main') || document.getElementById('main-content');

    // ========================================
    // 1. Edge Swipe Back Gesture
    // ========================================
    (function initSwipeBack() {
        var EDGE_THRESHOLD = 30;     // px from left edge to begin swipe
        var DISTANCE_THRESHOLD = 80; // px horizontal to trigger back
        var indicator = null;
        var startX = 0;
        var startY = 0;
        var swiping = false;
        var cancelled = false;

        function createIndicator() {
            var el = document.createElement('div');
            el.className = 'swipe-back-indicator';
            el.innerHTML = '<i class="fas fa-chevron-left" aria-hidden="true"></i>';
            document.body.appendChild(el);
            return el;
        }

        document.addEventListener('touchstart', function(e) {
            if (!e.touches || e.touches.length !== 1) return;
            var touch = e.touches[0];

            // Only start if touch begins near left edge and there is history to go back to
            if (touch.clientX > EDGE_THRESHOLD) return;
            if (window.history.length <= 1) return;

            startX = touch.clientX;
            startY = touch.clientY;
            swiping = true;
            cancelled = false;

            if (!indicator) {
                indicator = createIndicator();
            }
        }, { passive: true });

        document.addEventListener('touchmove', function(e) {
            if (!swiping || cancelled) return;
            if (!e.touches || e.touches.length === 0) return;

            var touch = e.touches[0];
            var dx = touch.clientX - startX;
            var dy = touch.clientY - startY;

            // Cancel if vertical movement exceeds horizontal
            if (Math.abs(dy) > Math.abs(dx)) {
                cancelled = true;
                if (indicator) {
                    indicator.classList.remove('visible');
                }
                return;
            }

            // Only show for rightward swipes
            if (dx <= 0) return;

            if (indicator) {
                indicator.style.left = Math.min(dx - 10, 60) + 'px';
                indicator.classList.add('visible');
                // Scale opacity based on progress toward threshold
                indicator.style.opacity = Math.min(dx / DISTANCE_THRESHOLD, 1);
            }
        }, { passive: true });

        document.addEventListener('touchend', function(e) {
            if (!swiping) return;
            swiping = false;

            if (indicator) {
                indicator.classList.remove('visible');
                indicator.style.opacity = '0';
            }

            if (cancelled) return;

            // Calculate final distance from changedTouches
            var touch = e.changedTouches && e.changedTouches[0];
            if (!touch) return;

            var dx = touch.clientX - startX;

            if (dx >= DISTANCE_THRESHOLD) {
                if (MRPNative.hapticLight) {
                    MRPNative.hapticLight();
                }
                navigateBack();
            }
        }, { passive: true });
    })();

    // ========================================
    // 2. Page Transitions (CSS Animations)
    // ========================================

    /**
     * Determine if a click on an anchor should trigger a page transition.
     */
    function shouldTransition(anchor) {
        if (!anchor || !anchor.href) return false;

        // Skip blank targets, downloads, hash-only links, javascript: links
        var target = anchor.getAttribute('target');
        if (target === '_blank') return false;
        if (anchor.hasAttribute('download')) return false;

        var href = anchor.getAttribute('href') || '';
        if (href.charAt(0) === '#') return false;
        if (href.indexOf('javascript:') === 0) return false;

        // Must be same origin
        try {
            var url = new URL(anchor.href, window.location.origin);
            if (url.origin !== window.location.origin) return false;
        } catch (err) {
            return false;
        }

        return true;
    }

    /**
     * Navigate forward to a URL with a slide-out-left transition.
     */
    function navigateForward(url) {
        if (!mainEl) {
            window.location.href = url;
            return;
        }

        // Use View Transition API if available (iOS 18+)
        if (document.startViewTransition) {
            document.startViewTransition(function() {
                window.location.href = url;
            });
            return;
        }

        // Fallback: CSS class-based transition
        mainEl.classList.add('page-exit-left');
        setTimeout(function() {
            window.location.href = url;
        }, 250);
    }

    /**
     * Navigate back with a slide-out-right transition.
     */
    function navigateBack() {
        if (!mainEl) {
            window.history.back();
            return;
        }

        // Use View Transition API if available (iOS 18+)
        if (document.startViewTransition) {
            document.startViewTransition(function() {
                window.history.back();
            });
            return;
        }

        // Fallback: CSS class-based transition
        mainEl.classList.add('page-exit-right');
        setTimeout(function() {
            window.history.back();
        }, 250);
    }

    // Intercept link clicks for forward transitions (event delegation)
    document.addEventListener('click', function(e) {
        var anchor = e.target.closest('a');
        if (!anchor) return;

        if (!shouldTransition(anchor)) return;

        e.preventDefault();
        navigateForward(anchor.href);
    });

    // Entrance animation on page show
    window.addEventListener('pageshow', function() {
        if (!mainEl) return;
        mainEl.classList.add('page-enter');
        setTimeout(function() {
            mainEl.classList.remove('page-enter');
        }, 250);
    });

    // ========================================
    // 3. Enhanced Pull-to-Refresh
    // ========================================
    (function initPullToRefresh() {
        var PULL_THRESHOLD = 120; // px to trigger refresh
        var pullIndicator = null;
        var pullStartY = 0;
        var pulling = false;
        var lastPullDistance = 0;

        function createPullIndicator() {
            var el = document.createElement('div');
            el.className = 'pull-refresh-indicator';
            el.innerHTML = '<i class="fas fa-arrow-down" aria-hidden="true"></i>';
            document.body.appendChild(el);
            return el;
        }

        document.addEventListener('touchstart', function(e) {
            // Only activate when scrolled to the very top
            if (window.scrollY !== 0) return;
            if (!e.touches || e.touches.length !== 1) return;

            pullStartY = e.touches[0].clientY;
            pulling = true;
            lastPullDistance = 0;

            if (!pullIndicator) {
                pullIndicator = createPullIndicator();
            }
        }, { passive: true });

        document.addEventListener('touchmove', function(e) {
            if (!pulling) return;
            if (!e.touches || e.touches.length === 0) return;

            var dy = e.touches[0].clientY - pullStartY;
            lastPullDistance = dy;

            // Only track downward pull
            if (dy <= 0) {
                if (pullIndicator) pullIndicator.classList.remove('visible');
                return;
            }

            // If the page has scrolled, cancel the pull gesture
            if (window.scrollY > 0) {
                pulling = false;
                lastPullDistance = 0;
                if (pullIndicator) pullIndicator.classList.remove('visible');
                return;
            }

            if (pullIndicator) {
                pullIndicator.classList.add('visible');
                // Rotate the arrow based on pull distance (0 to 180 degrees)
                var rotation = Math.min((dy / PULL_THRESHOLD) * 180, 180);
                var icon = pullIndicator.querySelector('i');
                if (icon) {
                    icon.style.transform = 'rotate(' + rotation + 'deg)';
                }
                // Scale opacity with distance
                pullIndicator.style.opacity = Math.min(dy / PULL_THRESHOLD, 1);
                // Move indicator down slightly with pull
                pullIndicator.style.top = 'calc(' + Math.min(dy * 0.3, 60) + 'px + var(--safe-area-inset-top, 0px))';
            }
        }, { passive: true });

        document.addEventListener('touchend', function() {
            if (!pulling) return;
            pulling = false;

            var distance = lastPullDistance;
            lastPullDistance = 0;

            if (pullIndicator) {
                pullIndicator.classList.remove('visible');
                pullIndicator.style.opacity = '0';
            }

            if (distance >= PULL_THRESHOLD) {
                if (MRPNative.hapticMedium) {
                    MRPNative.hapticMedium();
                }
                location.reload();
            }
        }, { passive: true });
    })();

})();
