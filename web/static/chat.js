const chatRoot = document.getElementById('chat');
const chatBase = `/chat/${chatRoot.dataset.investor}`;
const form = document.getElementById('chat-form');
const input = document.getElementById('message');
const send = document.getElementById('send');
const messages = document.getElementById('messages');
const scroll = document.getElementById('scroll');

let controller = null;

const isBusy = () => send.dataset.busy === 'true';
const fromTemplate = (id) => document.getElementById(id).content.firstElementChild.cloneNode(true);
const scrollToBottom = () => { scroll.scrollTop = scroll.scrollHeight; };
// keeps the view at the bottom during an answer, but not after the user scrolls up to read
const isNearBottom = () => scroll.scrollHeight - scroll.scrollTop - scroll.clientHeight < 120;

function setBusy(busy) {
  send.dataset.busy = String(busy);
  send.setAttribute('aria-label', busy ? 'Parar' : 'Enviar');
}

async function refreshMessages() {
  const res = await fetch(`${chatBase}/messages`);
  messages.innerHTML = await res.text();
  renderCharts(messages);
}

function appendText(parts, delta) {
  let el = parts.lastElementChild;
  if (!el || !el.hasAttribute('data-text')) {
    el = document.createElement('div');
    el.className = 'mb-3 whitespace-pre-wrap break-words text-[13px] leading-relaxed';
    el.setAttribute('data-text', '');
    parts.appendChild(el);
  }
  el.textContent += delta;
}

function appendTool(parts, event) {
  const el = fromTemplate('tpl-tool');
  el.dataset.tool = event.id;
  el.querySelector('[data-tool-label]').textContent = event.label;
  el.querySelector('[data-tool-summary]').textContent = event.summary;
  el.querySelector('[data-tool-name]').textContent = event.name;
  el.querySelector('[data-tool-args]').textContent = event.args;
  parts.appendChild(el);
}

function finishTool(parts, event) {
  const el = [...parts.querySelectorAll('[data-tool]')].find((tool) => tool.dataset.tool === event.id);
  if (!el) return;
  el.dataset.status = event.status;
  el.querySelector('[data-tool-result]').textContent = event.result;
}

function appendChart(parts, event) {
  const el = document.createElement('figure');
  el.className = 'mb-3';
  el.dataset.chart = JSON.stringify(event.spec);
  parts.appendChild(el);
  renderCharts(parts);
}

function handleEvent(parts, event) {
  if (event.type === 'text') appendText(parts, event.delta);
  else if (event.type === 'tool') appendTool(parts, event);
  else if (event.type === 'tool_done') finishTool(parts, event);
  else if (event.type === 'chart') appendChart(parts, event);
  else if (event.type === 'error') console.error('chat error', event.message);
}

async function readStream(res, parts) {
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop();
    const stick = isNearBottom();
    lines.filter(Boolean).forEach((line) => handleEvent(parts, JSON.parse(line)));
    if (stick) scrollToBottom();
  }
}

async function sendMessage(message) {
  setBusy(true);
  controller = new AbortController();

  const emptyState = messages.querySelector('[data-empty]');
  if (emptyState) emptyState.remove();

  const user = fromTemplate('tpl-user');
  user.querySelector('[data-user-text]').textContent = message;
  messages.appendChild(user);
  const assistant = fromTemplate('tpl-assistant');
  messages.appendChild(assistant);
  scrollToBottom();

  try {
    const payload = new FormData();
    payload.append('message', message);
    const res = await fetch(`${chatBase}/send`, { method: 'POST', body: payload, signal: controller.signal });
    if (!res.ok) {
      console.error('chat send rejected', res.status);
      input.value = message;
      return;
    }
    await readStream(res, assistant.querySelector('[data-parts]'));
  } catch (error) {
    if (error.name !== 'AbortError') console.error('chat stream failed', error);
  } finally {
    controller = null;
    const stick = isNearBottom();
    // swaps the streamed plain text for the markdown rendered by the server
    await refreshMessages();
    setBusy(false);
    if (stick) scrollToBottom();
    input.focus();
  }
}

async function stopAnswer() {
  if (!controller) return;
  // the server records the stop before the connection closes, so the next render shows the partial answer
  await fetch(`${chatBase}/stop`, { method: 'POST' });
  if (controller) controller.abort();
}

input.addEventListener('input', () => {
  input.style.height = 'auto';
  input.style.height = `${input.scrollHeight}px`;
});

input.addEventListener('keydown', (event) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    if (!isBusy()) form.requestSubmit();
  }
});

form.addEventListener('submit', (event) => {
  event.preventDefault();
  if (isBusy()) {
    stopAnswer();
    return;
  }
  const message = input.value.trim();
  if (!message || send.disabled) return;
  input.value = '';
  input.style.height = 'auto';
  sendMessage(message);
});

// an answer cannot continue without the page that reads it
window.addEventListener('pagehide', () => {
  if (isBusy()) navigator.sendBeacon(`${chatBase}/stop`);
});

renderCharts(messages);
scrollToBottom();
input.focus();
