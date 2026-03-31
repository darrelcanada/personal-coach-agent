const API_BASE = window.location.origin;

let personas = {};

const els = {
  select: document.getElementById('persona-select'),
  newBtn: document.getElementById('new-btn'),
  editor: document.getElementById('editor'),
  editorTitle: document.getElementById('editor-title'),
  deleteBtn: document.getElementById('delete-btn'),
  form: document.getElementById('persona-form'),
  isNew: document.getElementById('is-new'),
  channelId: document.getElementById('channel-id'),
  name: document.getElementById('name'),
  description: document.getElementById('description'),
  prompt: document.getElementById('prompt'),
  schedulingEnabled: document.getElementById('scheduling-enabled'),
  schedulingPanel: document.getElementById('scheduling-panel'),
  interval: document.getElementById('interval'),
  startHour: document.getElementById('start-hour'),
  endHour: document.getElementById('end-hour'),
  messageContent: document.getElementById('message-content'),
  cancelBtn: document.getElementById('cancel-btn'),
  deleteModal: document.getElementById('delete-modal'),
  deleteName: document.getElementById('delete-name'),
  cancelDelete: document.getElementById('cancel-delete'),
  confirmDelete: document.getElementById('confirm-delete'),
  loading: document.getElementById('loading'),
  error: document.getElementById('error'),
  personaList: document.getElementById('persona-list'),
};

let deleteTargetId = null;

async function loadConfig() {
  showLoading(true);
  hideError();
  hideEditor();

  try {
    const response = await fetch(`${API_BASE}/api/config`);
    if (!response.ok) throw new Error('Failed to load config');
    const config = await response.json();
    personas = config.personas || {};
    populateSelect();
    renderList();
  } catch (err) {
    showError('Failed to load configuration: ' + err.message);
  } finally {
    showLoading(false);
  }
}

function populateSelect() {
  els.select.innerHTML = '<option value="">-- Choose a persona --</option>';
  const sorted = Object.entries(personas).sort(([a], [b]) => {
    if (a === 'default') return -1;
    if (b === 'default') return 1;
    return a.localeCompare(b);
  });
  for (const [id, persona] of sorted) {
    const opt = document.createElement('option');
    opt.value = id;
    opt.textContent = `${persona.name || 'Unnamed'} (${id})`;
    els.select.appendChild(opt);
  }
}

function renderList() {
  els.personaList.innerHTML = '';
  const sorted = Object.entries(personas).sort(([a], [b]) => {
    if (a === 'default') return -1;
    if (b === 'default') return 1;
    return a.localeCompare(b);
  });
  for (const [id, persona] of sorted) {
    const scheduling = persona.proactive_scheduling;
    const enabled = scheduling && scheduling.enabled;
    const item = document.createElement('div');
    item.className = 'persona-item' + (id === 'default' ? ' is-default' : '');
    item.innerHTML = `
      <div class="persona-info">
        <div class="persona-name">
          ${escapeHtml(persona.name || 'Unnamed')}
          ${id === 'default' ? '<span class="default-badge">Default</span>' : ''}
        </div>
        <div class="persona-channel">${escapeHtml(id)}</div>
        <div class="persona-status">
          <span class="dot ${enabled ? '' : 'disabled'}"></span>
          <span>${enabled ? 'Check-ins enabled' : 'Check-ins disabled'}</span>
        </div>
      </div>
    `;
    els.personaList.appendChild(item);
  }
}

function showEditor(isNew = false) {
  els.editor.classList.remove('hidden');
  els.deleteBtn.classList.toggle('hidden', isNew);
}

function hideEditor() {
  els.editor.classList.add('hidden');
  els.select.value = '';
}

function startNew() {
  els.isNew.value = 'true';
  els.editorTitle.textContent = 'New Persona';
  els.channelId.value = '';
  els.channelId.disabled = false;
  els.name.value = '';
  els.description.value = '';
  els.prompt.value = '';
  els.schedulingEnabled.checked = false;
  els.interval.value = '300';
  els.startHour.value = '19';
  els.endHour.value = '22';
  els.messageContent.value = '';
  updateSchedulingPanel();
  showEditor(true);
}

function startEdit(channelId) {
  const persona = personas[channelId];
  if (!persona) return;

  const scheduling = persona.proactive_scheduling || {};

  els.isNew.value = 'false';
  els.editorTitle.textContent = 'Edit Persona';
  els.channelId.value = channelId;
  els.channelId.disabled = true;
  els.name.value = persona.name || '';
  els.description.value = persona.description || '';
  els.prompt.value = persona.prompt || '';
  els.schedulingEnabled.checked = scheduling.enabled || false;
  els.interval.value = scheduling.interval_seconds || 300;
  els.startHour.value = scheduling.time_window?.start_hour ?? 19;
  els.endHour.value = scheduling.time_window?.end_hour ?? 22;
  els.messageContent.value = scheduling.message_content || '';
  updateSchedulingPanel();
  showEditor(true);
}

function updateSchedulingPanel() {
  els.schedulingPanel.classList.toggle('hidden', !els.schedulingEnabled.checked);
}

function resetForm() {
  els.isNew.value = '';
  els.channelId.value = '';
  els.channelId.disabled = false;
  els.name.value = '';
  els.description.value = '';
  els.prompt.value = '';
  els.schedulingEnabled.checked = false;
  els.interval.value = '300';
  els.startHour.value = '19';
  els.endHour.value = '22';
  els.messageContent.value = '';
  hideEditor();
}

// Event listeners
els.select.addEventListener('change', (e) => {
  if (e.target.value) {
    startEdit(e.target.value);
  } else {
    resetForm();
  }
});

els.newBtn.addEventListener('click', startNew);

els.cancelBtn.addEventListener('click', resetForm);

els.schedulingEnabled.addEventListener('change', updateSchedulingPanel);

els.form.addEventListener('submit', async (e) => {
  e.preventDefault();

  const isNew = els.isNew.value === 'true';
  const channelId = els.channelId.value.trim();

  if (!channelId || !els.name.value.trim() || !els.prompt.value.trim()) {
    showToast('Please fill in all required fields', 'error');
    return;
  }

  const schedulingEnabled = els.schedulingEnabled.checked;
  const proactive_scheduling = schedulingEnabled ? {
    enabled: true,
    interval_seconds: parseInt(els.interval.value) || 300,
    time_window: {
      start_hour: parseInt(els.startHour.value) || 19,
      end_hour: parseInt(els.endHour.value) || 22
    },
    message_content: els.messageContent.value.trim() || null
  } : null;

  const personaData = {
    name: els.name.value.trim(),
    description: els.description.value.trim(),
    prompt: els.prompt.value.trim(),
    proactive_scheduling
  };

  let response;
  if (isNew) {
    personaData.channel_id = channelId;
    response = await fetch(`${API_BASE}/api/config/persona`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(personaData)
    });
  } else {
    response = await fetch(`${API_BASE}/api/config/persona/${channelId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(personaData)
    });
  }

  if (response.ok) {
    showToast(isNew ? 'Persona created' : 'Persona updated', 'success');
    await loadConfig();
  } else {
    const error = await response.json();
    showToast(error.error || 'Failed to save persona', 'error');
  }
});

els.deleteBtn.addEventListener('click', () => {
  const channelId = els.channelId.value;
  if (!channelId) return;
  deleteTargetId = channelId;
  els.deleteName.textContent = personas[channelId]?.name || channelId;
  els.deleteModal.classList.remove('hidden');
});

els.cancelDelete.addEventListener('click', () => {
  deleteTargetId = null;
  els.deleteModal.classList.add('hidden');
});

els.confirmDelete.addEventListener('click', async () => {
  if (!deleteTargetId) return;

  const response = await fetch(`${API_BASE}/api/config/persona/${deleteTargetId}`, {
    method: 'DELETE'
  });

  if (response.ok) {
    els.deleteModal.classList.add('hidden');
    showToast('Persona deleted', 'success');
    deleteTargetId = null;
    await loadConfig();
  } else {
    const error = await response.json();
    showToast(error.error || 'Failed to delete persona', 'error');
  }
});

function showLoading(show) {
  els.loading.classList.toggle('hidden', !show);
}

function showError(msg) {
  els.error.textContent = msg;
  els.error.classList.remove('hidden');
}

function hideError() {
  els.error.classList.add('hidden');
}

function showToast(msg, type = 'success') {
  const existing = document.querySelector('.toast');
  if (existing) existing.remove();

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = msg;
  document.body.appendChild(toast);

  setTimeout(() => toast.remove(), 3000);
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

loadConfig();
