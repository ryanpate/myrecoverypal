/**
 * Capacitor In-App Purchase Bridge (RevenueCat + StoreKit 2)
 * Handles iOS subscriptions via RevenueCat, replacing Stripe inside the native app.
 * Exits immediately if not running on iOS native platform.
 */
(function() {
    'use strict';

    // Only run inside iOS Capacitor native app
    if (!window.Capacitor || !window.Capacitor.isNativePlatform() ||
        window.Capacitor.getPlatform() !== 'ios') {
        return;
    }

    var Purchases = window.Capacitor.Plugins.RevenueCatPurchases ||
                    window.Capacitor.Plugins.Purchases;

    if (!Purchases) {
        console.warn('[IAP] RevenueCat plugin not available');
        return;
    }

    // RevenueCat iOS API key — set via Django template or config
    // This will be populated from the server-rendered page
    var RC_API_KEY = document.querySelector('meta[name="revenuecat-api-key"]');
    var apiKey = RC_API_KEY ? RC_API_KEY.getAttribute('content') : '';

    if (!apiKey) {
        console.warn('[IAP] No RevenueCat API key configured');
        return;
    }

    function getCSRFToken() {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = cookies[i].trim();
            if (cookie.startsWith('csrftoken=')) {
                return cookie.substring('csrftoken='.length);
            }
        }
        return '';
    }

    function showIAPToast(message, type) {
        var toast = document.createElement('div');
        toast.className = 'iap-toast iap-toast-' + (type || 'info');
        toast.textContent = message;
        document.body.appendChild(toast);
        // Trigger reflow then add visible class for animation
        toast.offsetHeight;
        toast.classList.add('iap-toast-visible');
        setTimeout(function() {
            toast.classList.remove('iap-toast-visible');
            setTimeout(function() { toast.remove(); }, 300);
        }, 3000);
    }

    var MRPIAP = {
        initialized: false,
        offerings: null,
        customerInfo: null,
        isPremium: false,

        /**
         * Initialize RevenueCat SDK
         */
        init: function() {
            if (MRPIAP.initialized) return Promise.resolve();

            return Purchases.configure({
                apiKey: apiKey
            }).then(function() {
                MRPIAP.initialized = true;
                console.log('[IAP] RevenueCat initialized');
                return MRPIAP.checkEntitlements();
            }).catch(function(err) {
                console.error('[IAP] Init error:', err);
            });
        },

        /**
         * Get available offerings/products
         */
        getOfferings: function() {
            return Purchases.getOfferings().then(function(result) {
                MRPIAP.offerings = result;
                return result;
            });
        },

        /**
         * Purchase a package
         */
        purchase: function(packageToPurchase) {
            return Purchases.purchasePackage({
                aPackage: packageToPurchase
            }).then(function(result) {
                MRPIAP.customerInfo = result.customerInfo;
                MRPIAP.isPremium = MRPIAP._checkPremium(result.customerInfo);
                // Sync with backend
                MRPIAP.syncWithServer(result.customerInfo);
                return result;
            });
        },

        /**
         * Restore previous purchases
         */
        restorePurchases: function() {
            return Purchases.restorePurchases().then(function(result) {
                MRPIAP.customerInfo = result.customerInfo;
                MRPIAP.isPremium = MRPIAP._checkPremium(result.customerInfo);
                MRPIAP.syncWithServer(result.customerInfo);
                return result;
            });
        },

        /**
         * Check current entitlements
         */
        checkEntitlements: function() {
            return Purchases.getCustomerInfo().then(function(result) {
                MRPIAP.customerInfo = result.customerInfo;
                MRPIAP.isPremium = MRPIAP._checkPremium(result.customerInfo);
                return result.customerInfo;
            });
        },

        /**
         * Check if user has premium entitlement
         */
        _checkPremium: function(customerInfo) {
            if (!customerInfo || !customerInfo.entitlements || !customerInfo.entitlements.active) {
                return false;
            }
            return 'premium' in customerInfo.entitlements.active;
        },

        /**
         * Sync subscription state with Django backend
         */
        syncWithServer: function(customerInfo) {
            var csrfToken = getCSRFToken();
            if (!csrfToken) return;

            var isPremium = MRPIAP._checkPremium(customerInfo);
            var premiumInfo = isPremium ? customerInfo.entitlements.active.premium : null;

            fetch('/accounts/api/ios-subscription/sync/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                credentials: 'same-origin',
                body: JSON.stringify({
                    is_premium: isPremium,
                    product_id: premiumInfo ? premiumInfo.productIdentifier : null,
                    expires_date: premiumInfo ? premiumInfo.expirationDate : null,
                    original_purchase_date: premiumInfo ? premiumInfo.originalPurchaseDate : null
                })
            }).then(function(response) {
                if (response.ok) {
                    console.log('[IAP] Subscription synced with server');
                }
            }).catch(function(err) {
                console.error('[IAP] Sync error:', err);
            });
        },

        /**
         * Open iOS subscription management
         */
        manageSubscription: function() {
            if (window.Capacitor.Plugins.Browser) {
                window.Capacitor.Plugins.Browser.open({
                    url: 'https://apps.apple.com/account/subscriptions'
                });
            } else {
                window.open('https://apps.apple.com/account/subscriptions', '_blank');
            }
        },

        /**
         * Show purchase UI — called from pricing page and upgrade prompts
         */
        showPurchaseUI: function() {
            if (!MRPIAP.initialized) {
                MRPIAP.init().then(function() {
                    MRPIAP._displayPurchaseSheet();
                });
            } else {
                MRPIAP._displayPurchaseSheet();
            }
        },

        _displayPurchaseSheet: function() {
            MRPIAP.getOfferings().then(function(offerings) {
                if (!offerings || !offerings.current || !offerings.current.availablePackages ||
                    offerings.current.availablePackages.length === 0) {
                    showIAPToast('No subscription plans available. Please try again later.', 'error');
                    return;
                }

                var packages = offerings.current.availablePackages;

                // Create modal
                var overlay = document.createElement('div');
                overlay.className = 'iap-modal-overlay';
                overlay.innerHTML = MRPIAP._buildModalHTML(packages);
                document.body.appendChild(overlay);

                // Bind events
                overlay.querySelector('.iap-modal-close').addEventListener('click', function() {
                    overlay.remove();
                });
                overlay.addEventListener('click', function(e) {
                    if (e.target === overlay) overlay.remove();
                });

                var buyButtons = overlay.querySelectorAll('.iap-buy-btn');
                buyButtons.forEach(function(btn, index) {
                    btn.addEventListener('click', function() {
                        btn.disabled = true;
                        btn.textContent = 'Processing...';
                        MRPIAP.purchase(packages[index]).then(function() {
                            overlay.remove();
                            // Refresh page to reflect new premium status
                            window.location.reload();
                        }).catch(function(err) {
                            btn.disabled = false;
                            if (err.code === 1 || (err.message && err.message.includes('cancel'))) {
                                // User cancelled — just reset button
                                btn.textContent = 'Subscribe';
                            } else {
                                btn.textContent = 'Subscribe';
                                showIAPToast('Purchase failed. Please try again.', 'error');
                                console.error('[IAP] Purchase error:', err);
                            }
                        });
                    });
                });

                var restoreBtn = overlay.querySelector('.iap-restore-btn');
                if (restoreBtn) {
                    restoreBtn.addEventListener('click', function() {
                        restoreBtn.disabled = true;
                        restoreBtn.textContent = 'Restoring...';
                        MRPIAP.restorePurchases().then(function(result) {
                            if (MRPIAP.isPremium) {
                                overlay.remove();
                                window.location.reload();
                            } else {
                                restoreBtn.disabled = false;
                                restoreBtn.textContent = 'Restore Purchases';
                                showIAPToast('No previous purchases found.', 'info');
                            }
                        }).catch(function() {
                            restoreBtn.disabled = false;
                            restoreBtn.textContent = 'Restore Purchases';
                            showIAPToast('Could not restore purchases. Please try again.', 'error');
                        });
                    });
                }
            }).catch(function(err) {
                console.error('[IAP] Error loading offerings:', err);
                showIAPToast('Could not load subscription plans. Please try again.', 'error');
            });
        },

        _buildModalHTML: function(packages) {
            var html = '<div class="iap-modal">' +
                '<button class="iap-modal-close" aria-label="Close">&times;</button>' +
                '<h2>MyRecoveryPal Premium</h2>' +
                '<p class="iap-subtitle">AI Coach, unlimited groups, advanced analytics & more</p>' +
                '<div class="iap-packages">';

            for (var i = 0; i < packages.length; i++) {
                var pkg = packages[i];
                var product = pkg.product;
                var label = pkg.packageType === 'MONTHLY' ? '/month' :
                            pkg.packageType === 'ANNUAL' ? '/year' : '';
                var badge = pkg.packageType === 'ANNUAL' ? '<span class="iap-save-badge">BEST VALUE</span>' : '';

                html += '<div class="iap-package">' +
                    badge +
                    '<div class="iap-price">' + product.priceString + '<span class="iap-period">' + label + '</span></div>' +
                    '<div class="iap-product-title">' + product.title + '</div>' +
                    '<button class="iap-buy-btn">Subscribe</button>' +
                    '</div>';
            }

            html += '</div>' +
                '<button class="iap-restore-btn">Restore Purchases</button>' +
                '<p class="iap-terms">Payment will be charged to your Apple ID account. ' +
                'Subscription automatically renews unless canceled at least 24 hours before the end of the current period. ' +
                'Manage subscriptions in iOS Settings.</p>' +
                '</div>';

            return html;
        }
    };

    window.MRPIAP = MRPIAP;

    // Initialize RevenueCat on page load
    if (document.readyState === 'complete') {
        MRPIAP.init();
    } else {
        window.addEventListener('load', function() {
            MRPIAP.init();
        });
    }

    // ========================================
    // Intercept Stripe subscribe buttons
    // ========================================
    document.body.addEventListener('click', function(e) {
        var btn = e.target.closest('.subscribe-btn');
        if (btn && !btn.classList.contains('iap-buy-btn')) {
            e.preventDefault();
            e.stopPropagation();
            MRPIAP.showPurchaseUI();
        }
    }, true);

    // ========================================
    // Inject IAP modal styles
    // ========================================
    var style = document.createElement('style');
    style.textContent =
        '.iap-modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 10000; display: flex; align-items: flex-end; justify-content: center; }' +
        '.iap-modal { background: white; border-radius: 20px 20px 0 0; padding: 24px 20px max(20px, env(safe-area-inset-bottom)); width: 100%; max-width: 500px; text-align: center; position: relative; }' +
        '[data-theme="dark"] .iap-modal { background: #1e1e1e; color: #e0e0e0; }' +
        '.iap-modal-close { position: absolute; top: 12px; right: 16px; background: none; border: none; font-size: 28px; color: #999; cursor: pointer; }' +
        '.iap-modal h2 { margin: 0 0 4px; font-size: 1.3rem; color: #1e4d8b; }' +
        '[data-theme="dark"] .iap-modal h2 { color: #8ab4f8; }' +
        '.iap-subtitle { color: #666; font-size: 0.9rem; margin: 0 0 20px; }' +
        '[data-theme="dark"] .iap-subtitle { color: #adb5bd; }' +
        '.iap-packages { display: flex; gap: 12px; justify-content: center; margin-bottom: 16px; }' +
        '.iap-package { background: #f8f9fa; border: 2px solid #e0e0e0; border-radius: 12px; padding: 16px; flex: 1; position: relative; }' +
        '[data-theme="dark"] .iap-package { background: #2d2d2d; border-color: #444; }' +
        '.iap-price { font-size: 1.5rem; font-weight: 700; color: #1e4d8b; }' +
        '[data-theme="dark"] .iap-price { color: #8ab4f8; }' +
        '.iap-period { font-size: 0.8rem; font-weight: 400; color: #666; }' +
        '.iap-product-title { font-size: 0.8rem; color: #888; margin: 4px 0 12px; }' +
        '.iap-save-badge { position: absolute; top: -10px; left: 50%; transform: translateX(-50%); background: linear-gradient(135deg, #52b788, #40916c); color: white; font-size: 0.65rem; padding: 2px 8px; border-radius: 10px; font-weight: 600; white-space: nowrap; }' +
        '.iap-buy-btn { background: linear-gradient(135deg, #1e4d8b, #2d6cb5); color: white; border: none; padding: 10px 20px; border-radius: 8px; font-weight: 600; font-size: 0.95rem; cursor: pointer; width: 100%; }' +
        '.iap-buy-btn:disabled { opacity: 0.6; }' +
        '.iap-restore-btn { background: none; border: none; color: #1e4d8b; font-size: 0.85rem; cursor: pointer; margin: 8px 0; text-decoration: underline; }' +
        '[data-theme="dark"] .iap-restore-btn { color: #8ab4f8; }' +
        '.iap-terms { font-size: 0.7rem; color: #999; margin: 12px 0 0; line-height: 1.4; }' +
        '.iap-toast { position: fixed; top: calc(20px + env(safe-area-inset-top)); left: 50%; transform: translateX(-50%) translateY(-20px); background: #333; color: white; padding: 12px 20px; border-radius: 10px; font-size: 0.9rem; z-index: 10001; opacity: 0; transition: opacity 0.3s, transform 0.3s; pointer-events: none; max-width: 90%; text-align: center; }' +
        '.iap-toast-visible { opacity: 1; transform: translateX(-50%) translateY(0); }' +
        '.iap-toast-error { background: #c0392b; }' +
        '.iap-toast-info { background: #2d6cb5; }' +
        '[data-theme="dark"] .iap-toast { background: #444; }' +
        '[data-theme="dark"] .iap-toast-error { background: #e74c3c; }' +
        '[data-theme="dark"] .iap-toast-info { background: #4a90d9; }';
    document.head.appendChild(style);

})();
