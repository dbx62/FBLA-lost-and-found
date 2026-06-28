/* ============================================================
   SLHS Lost & Found - Site-wide JavaScript
   All interactivity lives here so HTML, CSS, and JS stay in
   separate files. Each feature checks that its elements exist
   before running, so this one file can load safely on every page.
   ============================================================ */

document.addEventListener('DOMContentLoaded', function () {
    setupTheme();
    setupMobileMenu();
    setupReportForm();
    setupSearchToggle();
    setupFilters();
    setupDashboardModal();
    setupConfirmLinks();
    setupShare();
    setupBackToTop();
    setupReveal();
});

/* ------------------------------------------------------------
   Theme (light / dark) toggle
   The <head> already applied the saved theme before paint; here
   we wire the toggle buttons and persist the user's choice.
   ------------------------------------------------------------ */
function setupTheme() {
    var root = document.documentElement;

    function label() {
        return root.getAttribute('data-theme') === 'dark' ? 'Light mode' : 'Dark mode';
    }

    function syncLabels() {
        document.querySelectorAll('[data-theme-label]').forEach(function (el) {
            el.textContent = label();
        });
    }

    function toggle() {
        var next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
        root.setAttribute('data-theme', next);
        try { localStorage.setItem('slhs-theme', next); } catch (e) {}
        syncLabels();
    }

    ['themeToggle', 'drawerThemeToggle'].forEach(function (id) {
        var btn = document.getElementById(id);
        if (btn) { btn.addEventListener('click', toggle); }
    });
    syncLabels();
}

/* ------------------------------------------------------------
   0. Confirmation links
   ------------------------------------------------------------ */
function setupConfirmLinks() {
    document.querySelectorAll('.js-confirm').forEach(function (el) {
        el.addEventListener('click', function (e) {
            var message = el.getAttribute('data-confirm') || 'Are you sure?';
            if (!window.confirm(message)) {
                e.preventDefault();
            }
        });
    });
}

/* ------------------------------------------------------------
   1. Mobile navigation drawer
   ------------------------------------------------------------ */
function setupMobileMenu() {
    var toggleBtn = document.getElementById('menuToggle');
    var closeBtn = document.getElementById('menuClose');
    var menu = document.getElementById('sideMenu');
    var overlay = document.getElementById('menuOverlay');

    if (!toggleBtn || !menu || !overlay) {
        return;
    }

    function openMenu() {
        menu.classList.add('active');
        overlay.classList.add('active');
        toggleBtn.classList.add('open');
        menu.setAttribute('aria-hidden', 'false');
        toggleBtn.setAttribute('aria-expanded', 'true');
        document.body.style.overflow = 'hidden';
        if (closeBtn) { closeBtn.focus(); }
    }

    function closeMenu() {
        menu.classList.remove('active');
        overlay.classList.remove('active');
        toggleBtn.classList.remove('open');
        menu.setAttribute('aria-hidden', 'true');
        toggleBtn.setAttribute('aria-expanded', 'false');
        document.body.style.overflow = '';
        toggleBtn.focus();
    }

    function isOpen() {
        return menu.classList.contains('active');
    }

    toggleBtn.addEventListener('click', function () {
        if (isOpen()) { closeMenu(); } else { openMenu(); }
    });

    if (closeBtn) { closeBtn.addEventListener('click', closeMenu); }
    overlay.addEventListener('click', closeMenu);

    // Close the drawer after tapping any link inside it.
    menu.querySelectorAll('a').forEach(function (link) {
        link.addEventListener('click', closeMenu);
    });

    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && isOpen()) { closeMenu(); }
    });
}

/* ------------------------------------------------------------
   2. Report form
   ------------------------------------------------------------ */
function setupReportForm() {
    var typeSelect = document.getElementById('report_type');
    if (!typeSelect) {
        return;
    }

    function updateForm() {
        var type = typeSelect.value;
        var locLabel = document.getElementById('location_label');
        var dateLabel = document.getElementById('date_label');
        var imgGroup = document.getElementById('image_group');
        var descInput = document.getElementById('description');

        if (type === 'lost') {
            locLabel.textContent = 'Last Known Location (Where did you leave it?)';
            dateLabel.textContent = 'Date Lost (When did you last have it?)';
            imgGroup.style.display = 'none';
            descInput.placeholder = 'Brand, color, identifiable marks...';
        } else {
            locLabel.textContent = 'Location Found (Where did you find it?)';
            dateLabel.textContent = 'Date Found (When did you find it?)';
            imgGroup.style.display = 'block';
            descInput.placeholder = 'Brand, contents, color, specific scratches...';
        }
    }

    typeSelect.addEventListener('change', updateForm);
    updateForm();

    setupImagePreview();
    setupDemoAutofill();
}

/* Shows a thumbnail of the chosen photo before the form is submitted. */
function setupImagePreview() {
    var input = document.getElementById('image');
    var preview = document.getElementById('imagePreview');
    if (!input || !preview) {
        return;
    }
    input.addEventListener('change', function () {
        var file = input.files && input.files[0];
        if (file) {
            preview.src = URL.createObjectURL(file);
            preview.classList.add('show');
        } else {
            preview.removeAttribute('src');
            preview.classList.remove('show');
        }
    });
}

/* Presentation helper: press Alt+D (or PageDown) to auto-type a
   sample "found" report. Used to demo the form quickly to judges. */
function setupDemoAutofill() {
    var demoStep = 0;
    var isTyping = false;

    function typeText(elementId, text, speed, callback) {
        var el = document.getElementById(elementId);
        if (!el) {
            if (callback) { callback(); }
            return;
        }
        el.value = '';
        var i = 0;
        var interval = setInterval(function () {
            el.value += text.charAt(i);
            i++;
            if (i >= text.length) {
                clearInterval(interval);
                if (callback) { callback(); }
            }
        }, speed);
    }

    document.addEventListener('keydown', function (e) {
        if (!((e.key === 'PageDown' || (e.altKey && e.key === 'd')) && !isTyping)) {
            return;
        }
        e.preventDefault();

        var demoTitle = 'Texas Instruments TI-84 Plus CE';
        var demoDesc = 'Black graphing calculator with a blue case. Has a small FBLA sticker on the back cover and is missing the battery door.';
        var demoLoc = 'Library - 2nd Floor Study Tables';
        var demoContact = 'Aditya Aggarwal - 1424500';

        if (demoStep === 0) {
            isTyping = true;
            var typeSelect = document.getElementById('report_type');
            if (typeSelect) {
                typeSelect.value = 'found';
                typeSelect.dispatchEvent(new Event('change'));
            }
            typeText('title', demoTitle, 30, function () { isTyping = false; demoStep++; });
        } else if (demoStep === 1) {
            isTyping = true;
            typeText('description', demoDesc, 15, function () { isTyping = false; demoStep++; });
        } else if (demoStep === 2) {
            isTyping = true;
            typeText('location', demoLoc, 30, function () { isTyping = false; demoStep++; });
        } else if (demoStep === 3) {
            var today = new Date().toISOString().split('T')[0];
            var dateField = document.getElementById('date_found');
            if (dateField) { dateField.value = today; }
            demoStep++;
        } else if (demoStep === 4) {
            isTyping = true;
            typeText('contact_info', demoContact, 30, function () { isTyping = false; demoStep++; });
        }
    });
}

/* ------------------------------------------------------------
   3. Browse page search toggle (small screens)
   ------------------------------------------------------------ */
function setupSearchToggle() {
    var form = document.getElementById('searchForm');
    var header = document.querySelector('.browse-header');
    var openBtn = document.querySelector('.mobile-search-toggle');
    var closeBtn = document.querySelector('.mobile-search-close');

    if (!form || !header || !openBtn) {
        return;
    }

    function toggleSearch() {
        var nowActive = form.classList.toggle('active');
        header.classList.toggle('search-active');
        openBtn.setAttribute('aria-expanded', nowActive ? 'true' : 'false');
        if (nowActive) {
            var input = form.querySelector('input[name="q"]');
            if (input) { input.focus(); }
        }
    }

    openBtn.addEventListener('click', toggleSearch);
    if (closeBtn) { closeBtn.addEventListener('click', toggleSearch); }
}

/* ------------------------------------------------------------
   4. Browse filters: auto-submit the form when a select changes
   ------------------------------------------------------------ */
function setupFilters() {
    document.querySelectorAll('.js-autosubmit').forEach(function (select) {
        select.addEventListener('change', function () {
            var form = select.closest('form');
            if (form) { form.submit(); }
        });
    });
}

/* ------------------------------------------------------------
   5. Admin dashboard preview modal
   ------------------------------------------------------------ */
function setupDashboardModal() {
    var modal = document.getElementById('previewModal');
    if (!modal) {
        return;
    }

    var modalImg = document.getElementById('modalImg');
    var modalTitle = document.getElementById('modalTitle');
    var modalDesc = document.getElementById('modalDesc');
    var modalLoc = document.getElementById('modalLoc');
    var modalDate = document.getElementById('modalDate');
    var modalContact = document.getElementById('modalContact');
    var closeBtn = modal.querySelector('.close-modal');
    var lastFocused = null;

    function openPreview(btn) {
        lastFocused = btn;
        modalTitle.textContent = btn.getAttribute('data-title');
        modalDesc.textContent = btn.getAttribute('data-desc');
        modalLoc.textContent = btn.getAttribute('data-location');
        modalDate.textContent = btn.getAttribute('data-date');
        modalContact.textContent = btn.getAttribute('data-contact');

        var imgFile = btn.getAttribute('data-img');
        if (imgFile && imgFile !== 'None' && imgFile !== '') {
            modalImg.src = imgFile;
            modalImg.style.display = 'block';
        } else {
            modalImg.removeAttribute('src');
            modalImg.style.display = 'none';
        }

        modal.style.display = 'block';
        if (closeBtn) { closeBtn.focus(); }
    }

    function closePreview() {
        modal.style.display = 'none';
        if (lastFocused) { lastFocused.focus(); }
    }

    document.querySelectorAll('.btn-preview').forEach(function (btn) {
        btn.addEventListener('click', function () { openPreview(btn); });
    });

    if (closeBtn) { closeBtn.addEventListener('click', closePreview); }

    modal.addEventListener('click', function (event) {
        if (event.target === modal) { closePreview(); }
    });

    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && modal.style.display === 'block') { closePreview(); }
    });
}

/* ------------------------------------------------------------
   6. Share / copy item link
   ------------------------------------------------------------ */
function setupShare() {
    document.querySelectorAll('.js-share').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var url = btn.getAttribute('data-url') || window.location.href;
            var title = btn.getAttribute('data-title') || document.title;
            if (navigator.share) {
                navigator.share({ title: title, url: url }).catch(function () {});
                return;
            }
            var done = function () {
                var original = btn.getAttribute('data-label') || btn.textContent;
                btn.textContent = 'Link copied!';
                setTimeout(function () { btn.textContent = original; }, 1800);
            };
            if (navigator.clipboard) {
                navigator.clipboard.writeText(url).then(done).catch(done);
            } else {
                done();
            }
        });
    });
}

/* ------------------------------------------------------------
   7. Back-to-top button
   ------------------------------------------------------------ */
function setupBackToTop() {
    var btn = document.getElementById('backToTop');
    if (!btn) {
        return;
    }
    function onScroll() {
        if (window.pageYOffset > 400) {
            btn.classList.add('show');
        } else {
            btn.classList.remove('show');
        }
    }
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();

    btn.addEventListener('click', function () {
        var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        window.scrollTo({ top: 0, behavior: reduce ? 'auto' : 'smooth' });
    });
}

/* ------------------------------------------------------------
   8. Scroll-reveal animations (progressive enhancement)
   ------------------------------------------------------------ */
function setupReveal() {
    var els = document.querySelectorAll('.reveal');
    if (!els.length) {
        return;
    }
    var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reduce || !('IntersectionObserver' in window)) {
        els.forEach(function (el) { el.classList.add('is-visible'); });
        return;
    }
    var observer = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
            if (entry.isIntersecting) {
                entry.target.classList.add('is-visible');
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.12 });
    els.forEach(function (el) { observer.observe(el); });
}
