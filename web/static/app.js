// custom select

function closeSelect(root) {
  const list = root.querySelector('[data-select-list]');
  const chevron = root.querySelector('[data-select-chevron]');
  list.hidden = true;
  chevron.classList.remove('rotate-180');
}

function openSelect(root) {
  document.querySelectorAll('[data-select]').forEach((other) => {
    if (other !== root) closeSelect(other);
  });
  const list = root.querySelector('[data-select-list]');
  const chevron = root.querySelector('[data-select-chevron]');
  list.hidden = false;
  chevron.classList.add('rotate-180');
}

function setupSelect(root) {
  const input = root.querySelector('[data-select-input]');
  const button = root.querySelector('[data-select-button]');
  const label = root.querySelector('[data-select-label]');
  const list = root.querySelector('[data-select-list]');

  button.addEventListener('click', () => {
    if (list.hidden) openSelect(root);
    else closeSelect(root);
  });

  list.querySelectorAll('[data-value]').forEach((option) => {
    option.addEventListener('click', () => {
      const value = option.dataset.value;
      if (value !== input.value) {
        input.value = value;
        label.textContent = option.querySelector('span').textContent;
        list.querySelectorAll('[data-value]').forEach((other) => {
          const on = other === option;
          other.dataset.selected = String(on);
          other.querySelector('svg').dataset.on = String(on);
        });
        input.dispatchEvent(new Event('change', { bubbles: true }));
        if (root.hasAttribute('data-auto-submit')) root.closest('form').requestSubmit();
      }
      closeSelect(root);
    });
  });

  root.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') closeSelect(root);
  });
}

document.querySelectorAll('[data-select]').forEach(setupSelect);

document.addEventListener('click', (event) => {
  document.querySelectorAll('[data-select]').forEach((root) => {
    if (!root.contains(event.target)) closeSelect(root);
  });
});

// mobile sidebar

const sidebar = document.getElementById('sidebar');
const overlay = document.getElementById('overlay');
const menuButton = document.getElementById('menu-button');

function toggleSidebar(open) {
  sidebar.classList.toggle('-translate-x-full', !open);
  overlay.classList.toggle('hidden', !open);
}

if (menuButton) {
  menuButton.addEventListener('click', () => toggleSidebar(sidebar.classList.contains('-translate-x-full')));
  overlay.addEventListener('click', () => toggleSidebar(false));
}
