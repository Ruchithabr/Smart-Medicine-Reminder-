if (Notification.permission !== 'granted') Notification.requestPermission();

function playBeep() {
    const audio = new Audio('https://www.soundjay.com/misc/sounds/bell-ringing-05.mp3');
    audio.play();
}

function checkNotifs() {
    fetch('/api/notifications/pending')
        .then(res => res.json())
        .then(notifs => {
            notifs.forEach(n => {
                new Notification("Medicine Reminder", { body: n.message });
                playBeep();
            });
        });
}

setInterval(checkNotifs, 30000);
checkNotifs();

/* ============================================
   HOME PAGE UI/UX ENHANCEMENTS
   ============================================ */
document.addEventListener('DOMContentLoaded', () => {

    // --- Scroll reveal animations ---
    const revealEls = document.querySelectorAll('.reveal');
    if (revealEls.length) {
        const revealObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('active');
                    revealObserver.unobserve(entry.target);
                }
            });
        }, { threshold: 0.15 });
        revealEls.forEach(el => revealObserver.observe(el));
    }

    // --- Animated stat counters ---
    const statEls = document.querySelectorAll('.stat-number[data-count]');
    if (statEls.length) {
        const animateCount = (el) => {
            const target = parseInt(el.getAttribute('data-count'), 10) || 0;
            const duration = 1400;
            const start = performance.now();
            const step = (now) => {
                const progress = Math.min((now - start) / duration, 1);
                const eased = 1 - Math.pow(1 - progress, 3);
                el.textContent = Math.floor(eased * target).toLocaleString();
                if (progress < 1) requestAnimationFrame(step);
                else el.textContent = target.toLocaleString();
            };
            requestAnimationFrame(step);
        };
        const statObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    animateCount(entry.target);
                    statObserver.unobserve(entry.target);
                }
            });
        }, { threshold: 0.4 });
        statEls.forEach(el => statObserver.observe(el));
    }

    // --- Smooth scroll for in-page anchor links (e.g. "Learn More") ---
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const targetId = this.getAttribute('href').slice(1);
            const targetEl = document.getElementById(targetId);
            if (targetEl) {
                e.preventDefault();
                targetEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });

    // --- Subtle nav shadow once the page is scrolled ---
    const nav = document.querySelector('nav');
    if (nav) {
        const onScroll = () => {
            if (window.scrollY > 10) {
                nav.style.boxShadow = '0 4px 20px rgba(0,0,0,0.15)';
            } else {
                nav.style.boxShadow = 'none';
            }
        };
        window.addEventListener('scroll', onScroll, { passive: true });
        onScroll();
    }
});