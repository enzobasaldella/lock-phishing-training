(() => {
  const panel = document.querySelector('[data-decision-panel]');
  const launcher = document.querySelector('[data-open-decision]');
  const closeButton = document.querySelector('[data-close-decision]');
  const guideForm = document.querySelector('[data-guide-complete]');

  if (panel && launcher) {
    document.body.classList.add('js-enabled');
    const content = panel.querySelector('[data-decision-content]');

    function openDecision() {
      document.body.classList.add('decision-open');
      launcher.setAttribute('aria-expanded', 'true');
      panel.setAttribute('role', 'dialog');
      panel.setAttribute('aria-modal', 'true');
      const focusTarget = panel.querySelector('[data-result-heading], input, button');
      if (focusTarget) focusTarget.focus({ preventScroll: true });
    }

    function closeDecision() {
      document.body.classList.remove('decision-open');
      launcher.setAttribute('aria-expanded', 'false');
      panel.removeAttribute('role');
      panel.removeAttribute('aria-modal');
      launcher.focus({ preventScroll: true });
    }

    launcher.addEventListener('click', openDecision);
    closeButton.addEventListener('click', closeDecision);
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && document.body.classList.contains('decision-open')) {
        closeDecision();
      }
    });

    // Delegate events because a successful answer replaces the panel markup.
    content.addEventListener('submit', async (event) => {
      const form = event.target.closest('[data-answer-form]');
      if (!form) return;
      event.preventDefault();
      const submit = form.querySelector('button[type="submit"]');
      const errorBox = form.querySelector('[data-form-error]');
      submit.disabled = true;
      submit.textContent = 'Conferindo...';
      errorBox.hidden = true;
      try {
        const response = await fetch(form.action, {
          method: 'POST',
          body: new FormData(form),
          headers: { 'X-Requested-With': 'XMLHttpRequest', 'Accept': 'application/json' },
          credentials: 'same-origin',
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Não foi possível conferir. Tente novamente.');
        content.innerHTML = data.html;
        launcher.textContent = 'Ver minha resposta ↑';
        // Remove ?refazer=1 so a refresh shows the newly saved attempt.
        window.history.replaceState({}, '', window.location.pathname);
        const heading = content.querySelector('[data-result-heading]');
        if (heading) heading.focus({ preventScroll: true });
      } catch (error) {
        errorBox.textContent = error.message || 'Falha de conexão. Tente novamente.';
        errorBox.hidden = false;
        submit.disabled = false;
        submit.textContent = 'Conferir resposta';
      }
    });
  }

  if (guideForm) {
    guideForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      const submit = guideForm.querySelector('button[type="submit"]');
      submit.disabled = true;
      try {
        const response = await fetch(guideForm.action, {
          method: 'POST',
          body: new FormData(guideForm),
          headers: { 'X-Requested-With': 'XMLHttpRequest', 'Accept': 'application/json' },
          credentials: 'same-origin',
        });
        if (!response.ok) throw new Error('Não foi possível salvar a leitura.');
        guideForm.outerHTML = '<div class="guide-done" role="status">✓ Leitura concluída. Você pode voltar a esta cartilha quando quiser.</div>';
      } catch (error) {
        submit.disabled = false;
        submit.textContent = 'Tentar novamente';
      }
    });
  }
})();
