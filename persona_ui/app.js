const API_BASE = window.location.origin;

let personas = {};
let deleteTargetId = null;

async function loadConfig() {
  showLoading(true);
  hideError();

  try {
    const response = await fetch(`${API_BASE}/api/config`);
    if (!response.ok) throw new Error('Failed to load config');
    const config = await response.json();
    personas = config.personas || {};
    renderPersonas();
  } catch (error) {
    showError('Failed to load configuration: ' + error.message);
  } finally {
    showLoading(false);
  }
}

function renderPersonas() {
  const container = document.getElementById('persona-list');
  container.innerHTML = '';
  container.classList.remove('hidden');

  const channelIds = Object.keys(personas).sort((a, b) => {
    if (a === 'default') return -1;
    if (b === 'default') return 1;
    return a.localeCompare(b);
  });

  channelIds.forEach(channelId => {
    const persona = personas[channelId];
    const isDefault = channelId === 'default';
    const scheduling = persona.proactive_scheduling;
    const schedulingEnabled = scheduling && scheduling.enabled;

    const card = document.createElement('div');
    card.className = 'persona-card' + (isDefault ? ' is-default' : '');
    card.innerHTML = `
      <div class="persona-card-header">
        <span class="persona-name">${escapeHtml(persona.name || 'Unnamed')}</span>
      </div>
      <div class="persona-channel-id">Channel: ${escapeHtml(channelId)}</div>
      <p class="persona-description">${escapeHtml(persona.description || 'No description')}</p>
      <div class="persona-status">
        <span class="status-dot ${schedulingEnabled ? '' : 'disabled'}"></span>
        <span>${schedulingEnabled ? 'Check-ins enabled' : 'Check-ins disabled'}</span>
      </div>
      <div class="persona-actions">
        <button class="btn btn-primary btn-small" onclick="editPersona('${channelId}')">Edit</button>
        ${!isDefault ? `<button class="btn btn-danger btn-small" onclick="confirmDelete('${channelId}')">Delete</button>` : ''}
      </div>
    `;
    container.appendChild(card);
  });
}

function openEditModal(isNew = false) {
  const modal = document.getElementById('edit-modal');
  const title = document.getElementById('modal-title');
  const channelInput = document.getElementById('channel-id-input');

  title.textContent = isNew ? 'Add New Persona' : 'Edit Persona';
  channelInput.disabled = !isNew;

  document.getElementById('edit-channel-id').value = '';
  channelInput.value = '';
  document.getElementById('name-input').value = '';
  document.getElementById('description-input').value = '';
  document.getElementById('prompt-input').value = '';
  document.getElementById('scheduling-enabled').checked = false;
  document.getElementById('interval-input').value = '300';
  document.getElementById('start-hour-input').value = '19';
  document.getElementById('end-hour-input').value = '22';
  document.getElementById('message-content-input').value = '';

  updateSchedulingOptions();
  modal.classList.remove('hidden');
}

function closeEditModal() {
  document.getElementById('edit-modal').classList.add('hidden');
}

function editPersona(channelId) {
  const persona = personas[channelId];
  const scheduling = persona.proactive_scheduling || {};

  document.getElementById('edit-channel-id').value = channelId;
  document.getElementById('channel-id-input').value = channelId;
  document.getElementById('channel-id-input').disabled = true;
  document.getElementById('name-input').value = persona.name || '';
  document.getElementById('description-input').value = persona.description || '';
  document.getElementById('prompt-input').value = persona.prompt || '';

  const enabled = scheduling.enabled || false;
  document.getElementById('scheduling-enabled').checked = enabled;
  document.getElementById('interval-input').value = scheduling.interval_seconds || 300;
  document.getElementById('start-hour-input').value = scheduling.time_window?.start_hour ?? 19;
  document.getElementById('end-hour-input').value = scheduling.time_window?.end_hour ?? 22;
  document.getElementById('message-content-input').value = scheduling.message_content || '';

  updateSchedulingOptions();
  document.getElementById('modal-title').textContent = 'Edit Persona';
  document.getElementById('edit-modal').classList.remove('hidden');
}

function updateSchedulingOptions() {
  const enabled = document.getElementById('scheduling-enabled').checked;
  const options = document.getElementById('scheduling-options');
  options.classList.toggle('hidden', !enabled);
}

function confirmDelete(channelId) {
  deleteTargetId = channelId;
  document.getElementById('delete-persona-name').textContent = personas[channelId]?.name || channelId;
  document.getElementById('delete-modal').classList.remove('hidden');
}

function closeDeleteModal() {
  deleteTargetId = null;
  document.getElementById('delete-modal').classList.add('hidden');
}

document.getElementById('scheduling-enabled').addEventListener('change', updateSchedulingOptions);

document.getElementById('persona-form').addEventListener('submit', async (e) => {
  e.preventDefault();

  const editChannelId = document.getElementById('edit-channel-id').value;
  const channelId = document.getElementById('channel-id-input').value.trim();
  const name = document.getElementById('name-input').value.trim();
  const description = document.getElementById('description-input').value.trim();
  const prompt = document.getElementById('prompt-input').value.trim();

  if (!channelId || !name || !prompt) {
    showToast('Please fill in all required fields', 'error');
    return;
  }

  const schedulingEnabled = document.getElementById('scheduling-enabled').checked;
  const proactive_scheduling = schedulingEnabled ? {
    enabled: true,
    interval_seconds: parseInt(document.getElementById('interval-input').value) || 300,
    time_window: {
      start_hour: parseInt(document.getElementById('start-hour-input').value) || 19,
      end_hour: parseInt(document.getElementById('end-hour-input').value) || 22
    },
    message_content: document.getElementById('message-content-input').value.trim() || null
  } : null;

  const personaData = {
    name,
    description,
    prompt,
    proactive_scheduling
  };

  let response;
  let isNew = !editChannelId;

  if (isNew) {
    personaData.channel_id = channelId;
    response = await fetch(`${API_BASE}/api/config/persona`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(personaData)
    });
  } else {
    response = await fetch(`${API_BASE}/api/config/persona/${editChannelId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(personaData)
    });
  }

  if (response.ok) {
    closeEditModal();
    showToast(isNew ? 'Persona created' : 'Persona updated', 'success');
    loadConfig();
  } else {
    const error = await response.json();
    showToast(error.error || 'Failed to save persona', 'error');
  }
});

document.getElementById('confirm-delete-btn').addEventListener('click', async () => {
  if (!deleteTargetId) return;

  const response = await fetch(`${API_BASE}/api/config/persona/${deleteTargetId}`, {
    method: 'DELETE'
  });

  if (response.ok) {
    closeDeleteModal();
    showToast('Persona deleted', 'success');
    loadConfig();
  } else {
    const error = await response.json();
    showToast(error.error || 'Failed to delete persona', 'error');
  }
});

document.getElementById('add-persona-btn').addEventListener('click', () => openEditModal(true));

function showLoading(show) {
  document.getElementById('loading').classList.toggle('hidden', !show);
}

function showError(message) {
  const el = document.getElementById('error');
  el.textContent = message;
  el.classList.remove('hidden');
}

function hideError() {
  document.getElementById('error').classList.add('hidden');
}

function showToast(message, type = 'success') {
  const existing = document.querySelector('.toast');
  if (existing) existing.remove();

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  document.body.appendChild(toast);

  setTimeout(() => toast.remove(), 3000);
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

loadConfig();
