/* ============================================================
   SLHS Lost & Found - Site-wide JavaScript
   ============================================================ */

document.addEventListener('DOMContentLoaded', function () {
    setupTheme();
    setupMobileMenu();
    setupReportForm();
    setupDemoAutofill();
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
}

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

/* ------------------------------------------------------------
   Live demo autofill (sign-up / login / report / claim forms)
   Shortcuts: Alt+D fill (login=student), Alt+A admin,
   Alt+F / Alt+L found / lost report, Alt+R reset.
   ------------------------------------------------------------ */
function setupDemoAutofill() {
    var $ = function (id) { return document.getElementById(id); };

    var page = $('report_type') ? 'report'
             : ($('full_name') && $('email') && $('password')) ? 'register'
             : $('username') ? 'login'
             : $('claimer_name') ? 'claim' : null;
    if (!page) { return; }

    var anchor = $('report_type') || $('full_name') || $('username') || $('claimer_name');
    var form = anchor.closest('form');
    if (!form) { return; }

    var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var gen = 0;

    var DEMO = {
        loginStudent: { username: 'maria.lopez@students.slhs.edu', password: 'demo1234' },
        loginAdmin:   { username: 'admin', password: 'admin123' },
        register: { full_name: 'Alex Rivera', student_id: 'K1190044', email: 'alex.rivera@students.slhs.edu', password: 'demo1234' },
        found: { title: 'Texas Instruments TI-84 Plus CE', category: 'Electronics',
                 description: 'Black graphing calculator with a blue slide case. Small FBLA sticker on the back and the battery door is missing.',
                 location: 'Library - 2nd Floor Study Tables', contact: 'Maria Lopez - K1180023' },
        lost:  { title: 'Silver MacBook Air 13-inch', category: 'Electronics',
                 description: 'Silver 13-inch MacBook Air with a Seven Lakes sticker and a small dent on one corner. Last had it Tuesday afternoon.',
                 location: 'Room 207 or the Library', contact: 'Maria Lopez - K1180023' },
        claim: { claimer_name: 'Maria Lopez', claimer_contact: 'maria.lopez@students.slhs.edu',
                 proof_description: 'It has a small dent near the base and a faded robotics-club sticker, and my initials "ML" are written on the cap.' }
    };

    function fire(el, type) { el.dispatchEvent(new Event(type, { bubbles: true })); }

    function typeInto(el, text, speed, done) {
        var mine = gen;
        el.focus();
        el.value = '';
        if (reduce) { el.value = text; fire(el, 'input'); if (done) { done(); } return; }
        var i = 0;
        var iv = setInterval(function () {
            if (mine !== gen) { clearInterval(iv); return; }
            el.value += text.charAt(i++);
            if (i >= text.length) { clearInterval(iv); fire(el, 'input'); if (done) { done(); } }
        }, speed);
    }

    function run(seq) {
        gen++;
        var mine = gen, i = 0;
        (function next() {
            if (mine !== gen || i >= seq.length) { return; }
            var s = seq[i++], el = $(s.id);
            if (!el) { next(); return; }
            if (el.tagName === 'SELECT' || el.type === 'date') { el.value = s.value; fire(el, 'change'); next(); }
            else { typeInto(el, s.value, s.speed || 18, next); }
        })();
    }

    function clearForm() {
        gen++;
        form.querySelectorAll('input, textarea').forEach(function (el) {
            if (el.type === 'submit' || el.type === 'button' || el.type === 'hidden') { return; }
            el.value = '';
        });
        var prev = $('imagePreview');
        if (prev) { prev.removeAttribute('src'); prev.classList.remove('show'); }
    }

    function today() { return new Date().toISOString().split('T')[0]; }

    function fill(opt) {
        opt = opt || {};
        clearForm();
        var seq = [];
        if (page === 'report') {
            var t = opt.type || ($('report_type').value || 'found');
            var rt = $('report_type'); rt.value = t; fire(rt, 'change');
            var d = (t === 'lost') ? DEMO.lost : DEMO.found;
            seq = [ { id: 'title', value: d.title }, { id: 'category', value: d.category },
                    { id: 'description', value: d.description, speed: 10 }, { id: 'location', value: d.location },
                    { id: 'date_found', value: today() }, { id: 'contact_info', value: d.contact } ];
        } else if (page === 'register') {
            var r = DEMO.register;
            seq = [ { id: 'full_name', value: r.full_name }, { id: 'student_id', value: r.student_id },
                    { id: 'email', value: r.email }, { id: 'password', value: r.password } ];
        } else if (page === 'login') {
            var l = (opt.role === 'admin') ? DEMO.loginAdmin : DEMO.loginStudent;
            seq = [ { id: 'username', value: l.username }, { id: 'password', value: l.password } ];
        } else if (page === 'claim') {
            var c = DEMO.claim;
            seq = [ { id: 'claimer_name', value: c.claimer_name }, { id: 'claimer_contact', value: c.claimer_contact },
                    { id: 'proof_description', value: c.proof_description, speed: 10 } ];
        }
        run(seq);
    }

    document.addEventListener('keydown', function (e) {
        if (!e.altKey && e.key !== 'PageDown') { return; }
        var k = (e.key || '').toLowerCase();
        if (e.altKey && k === 'r') { e.preventDefault(); clearForm(); return; }
        if (e.key === 'PageDown' || (e.altKey && k === 'd')) {
            e.preventDefault();
            fill(page === 'login' ? { role: 'student' } : {});
        } else if (e.altKey && k === 'a' && page === 'login') {
            e.preventDefault(); fill({ role: 'admin' });
        } else if (e.altKey && k === 'l' && page === 'report') {
            e.preventDefault(); fill({ type: 'lost' });
        } else if (e.altKey && k === 'f' && page === 'report') {
            e.preventDefault(); fill({ type: 'found' });
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
