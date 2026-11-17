/* Declarative event handlers, so templates need no inline on*= attributes
   (a nonce-based Content-Security-Policy blocks those).

   Markup:  <button data-on-click="toggle-theme">
   Script:  mrpAction('toggle-theme', function (event) { ... });

   Inside the function `this` is the element, as in an inline handler, and
   returning false cancels the default action. Handlers are attached to the
   element itself, so event.stopPropagation() behaves as it did inline.
   Elements added later (fetched fragments, innerHTML) are picked up too.
   Only names registered with mrpAction can run. */
(function () {
    'use strict';
    var EVENTS = ['click', 'submit', 'change', 'input', 'blur', 'error', 'mouseover', 'mouseout'];
    var SELECTOR = EVENTS.map(function (e) { return '[data-on-' + e + ']'; }).join(',');
    var actions = {};

    window.mrpAction = function (name, fn) { actions[name] = fn; };

    // Used on many pages.
    actions['print-page'] = function () { window.print(); };
    actions['reload-page'] = function () { window.location.reload(); };

    function run(el, type, event) {
        var name = el.getAttribute('data-on-' + type);
        var fn = actions[name];
        if (!fn) {
            if (window.console) console.warn('No action registered for "' + name + '"');
            return;
        }
        if (fn.call(el, event) === false && event) event.preventDefault();
    }

    function bind(el) {
        if (el.mrpBound) return;
        el.mrpBound = true;
        EVENTS.forEach(function (type) {
            if (!el.hasAttribute('data-on-' + type)) return;
            el.addEventListener(type, function (event) { run(el, type, event); });
            // An image can fail before this runs; its error event is already gone.
            if (type === 'error' && el.tagName === 'IMG' && el.complete && el.naturalWidth === 0) {
                run(el, type, null);
            }
        });
    }

    function scan(root) {
        if (root.nodeType !== 1) return;
        if (root.matches(SELECTOR)) bind(root);
        var found = root.querySelectorAll(SELECTOR);
        for (var i = 0; i < found.length; i++) bind(found[i]);
    }

    new MutationObserver(function (records) {
        records.forEach(function (record) {
            for (var i = 0; i < record.addedNodes.length; i++) scan(record.addedNodes[i]);
        });
    }).observe(document.documentElement, { childList: true, subtree: true });
    scan(document.documentElement);
})();
