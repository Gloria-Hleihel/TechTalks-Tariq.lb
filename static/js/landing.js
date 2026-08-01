(function () {
  const body = document.body;
  const header = document.querySelector('.landing-header');
  const backdrop = document.querySelector('[data-modal-backdrop]');
  const openers = document.querySelectorAll('[data-modal-target]');
  const closeButtons = document.querySelectorAll('[data-modal-close]');
  let activeModal = null;
  let previousFocus = null;

  function updateHeaderState() {
    if (!header) {
      return;
    }

    if (body.classList.contains('upload-page')) {
      header.classList.remove('scrolled');
      return;
    }

    header.classList.toggle('scrolled', window.scrollY > 8);
  }

  function getFocusableElements(modal) {
    return Array.from(
      modal.querySelectorAll(
        'a[href], button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'
      )
    );
  }

  function openModal(modalId) {
    const modal = document.getElementById(modalId);

    if (!modal || !backdrop) {
      return;
    }

    previousFocus = document.activeElement;
    activeModal = modal;
    modal.hidden = false;
    backdrop.hidden = false;
    body.classList.add('modal-open');

    const focusable = getFocusableElements(modal);
    const panel = modal.querySelector('.modal-panel');
    const firstFocusable = focusable[0] || panel || modal;
    firstFocusable.focus({ preventScroll: true });
  }

  function closeModal() {
    if (!activeModal || !backdrop) {
      return;
    }

    activeModal.hidden = true;
    backdrop.hidden = true;
    body.classList.remove('modal-open');
    activeModal = null;

    if (previousFocus && typeof previousFocus.focus === 'function') {
      previousFocus.focus({ preventScroll: true });
    }
  }

  openers.forEach((opener) => {
    opener.addEventListener('click', () => {
      openModal(opener.dataset.modalTarget);
    });
  });

  closeButtons.forEach((button) => {
    button.addEventListener('click', closeModal);
  });

  if (backdrop) {
    backdrop.addEventListener('click', closeModal);
  }

  window.addEventListener('scroll', updateHeaderState, { passive: true });
  updateHeaderState();

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      closeModal();
      return;
    }

    if (event.key !== 'Tab' || !activeModal) {
      return;
    }

    const focusable = getFocusableElements(activeModal);

    if (focusable.length === 0) {
      event.preventDefault();
      return;
    }

    const first = focusable[0];
    const last = focusable[focusable.length - 1];

    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  });
})();
// Landing page interaction polish
(function () {
  const body = document.body;

  if (!body || !body.classList.contains('landing-page')) {
    return;
  }

  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const finePointer = window.matchMedia('(pointer: fine)').matches;
  const interactiveCards = document.querySelectorAll(
    '.hero-visual-card, .feature-card, .impact-card, .impact-stat, .modal-info-card, .process-step, .contact-card'
  );
  const pressableItems = document.querySelectorAll(
    '.primary-cta, .secondary-cta, .learn-link, .nav-button'
  );
  const revealItems = document.querySelectorAll(
    '.hero-copy-block, .hero-visual-card, .feature-card, .impact-card, .impact-stat, .modal-info-card, .process-step, .contact-card'
  );

  if (!reduceMotion && 'IntersectionObserver' in window) {
    const revealObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible');
            revealObserver.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.14 }
    );

    revealItems.forEach((item, index) => {
      item.classList.add('landing-reveal');
      item.style.setProperty('--landing-delay', `${Math.min(index * 45, 260)}ms`);
      revealObserver.observe(item);
    });
  } else {
    revealItems.forEach((item) => item.classList.add('is-visible'));
  }

  pressableItems.forEach((item) => {
    item.addEventListener('pointerdown', () => item.classList.add('is-pressed'));
    item.addEventListener('pointerup', () => item.classList.remove('is-pressed'));
    item.addEventListener('pointerleave', () => item.classList.remove('is-pressed'));
    item.addEventListener('blur', () => item.classList.remove('is-pressed'));
  });

  if (!finePointer || reduceMotion) {
    return;
  }

  let cursorFrame = 0;
  document.addEventListener(
    'pointermove',
    (event) => {
      if (cursorFrame) {
        return;
      }

      cursorFrame = window.requestAnimationFrame(() => {
        body.style.setProperty('--landing-cursor-x', `${event.clientX}px`);
        body.style.setProperty('--landing-cursor-y', `${event.clientY}px`);
        cursorFrame = 0;
      });
    },
    { passive: true }
  );

  interactiveCards.forEach((card) => {
    card.addEventListener(
      'pointermove',
      (event) => {
        const rect = card.getBoundingClientRect();
        const x = ((event.clientX - rect.left) / rect.width) * 100;
        const y = ((event.clientY - rect.top) / rect.height) * 100;
        card.style.setProperty('--landing-spot-x', `${x.toFixed(2)}%`);
        card.style.setProperty('--landing-spot-y', `${y.toFixed(2)}%`);
      },
      { passive: true }
    );
  });

})();
