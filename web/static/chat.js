const chatRoot = document.getElementById('chat');
const chatBase = `/chat/${chatRoot.dataset.investor}`;
const form = document.getElementById('chat-form');
const input = document.getElementById('message');
const send = document.getElementById('send');
const messages = document.getElementById('messages');
const scroll = document.getElementById('scroll');

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

// Reads the answer in progress from its first event. The answer runs on the server,
// so this also works after a page change or a reload.
async function followAnswer(parts) {
  setBusy(true);
  refreshChatStatus();
  try {
    const res = await fetch(`${chatBase}/stream`);
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
  } catch (error) {
    console.error('chat stream failed', error);
  } finally {
    const stick = isNearBottom();
    // swaps the streamed plain text for the markdown rendered by the server
    await refreshMessages();
    setBusy(false);
    refreshChatStatus();
    if (stick) scrollToBottom();
    input.focus();
  }
}

function appendLiveAnswer() {
  const assistant = fromTemplate('tpl-assistant');
  messages.appendChild(assistant);
  return assistant.querySelector('[data-parts]');
}

async function sendMessage(message) {
  setBusy(true);

  const emptyState = messages.querySelector('[data-empty]');
  if (emptyState) emptyState.remove();

  const user = fromTemplate('tpl-user');
  user.querySelector('[data-user-text]').textContent = message;
  messages.appendChild(user);
  const parts = appendLiveAnswer();
  scrollToBottom();

  const payload = new FormData();
  payload.append('message', message);
  const res = await fetch(`${chatBase}/send`, { method: 'POST', body: payload });
  if (!res.ok) {
    console.error('chat send rejected', res.status);
    input.value = message;
  }
  await followAnswer(parts);
}

function stopAnswer() {
  // the server cancels the answer and closes the stream, then followAnswer renders the partial answer
  return fetch(`${chatBase}/stop`, { method: 'POST' });
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

// typing anywhere on the page goes to the message input
document.addEventListener('keydown', (event) => {
  if (document.activeElement === input || event.defaultPrevented) return;
  if (event.target.closest('input, textarea, select, [contenteditable]')) return;
  const paste = (event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'v';
  const printable = event.key.length === 1 && !event.metaKey && !event.ctrlKey && !event.altKey;
  // the focus moves before the browser inserts the character, so the key is not lost
  if (printable || paste) input.focus();
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

renderCharts(messages);
scrollToBottom();
input.focus();

if (chatRoot.dataset.streaming === 'true') {
  // the server rendered the partial answer; the event replay builds it again, live
  const partial = [...messages.querySelectorAll('[data-assistant]')].pop();
  if (partial) partial.remove();
  followAnswer(appendLiveAnswer());
}
