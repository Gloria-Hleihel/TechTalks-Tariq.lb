(function () {
  const body = document.body;
  const backdrop = document.querySelector('[data-modal-backdrop]');
  const openers = document.querySelectorAll('[data-modal-target]');
  const closeButtons = document.querySelectorAll('[data-modal-close]');
  let activeModal = null;
  let previousFocus = null;

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
    const firstFocusable = focusable[0] || modal;
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
