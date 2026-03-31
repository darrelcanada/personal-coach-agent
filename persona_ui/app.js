const API_BASE = window.location.origin;
const BOT_API_BASE = 'http://localhost:8000';

let personas = {};
let activeSchedules = [];

const PERSONA_TRIGGERS = {
  default: [
    { category: 'General', triggers: [
      { command: 'Any message', description: 'Responds using the LLM with the persona prompt' }
    ]}
  ],
  trainer: [
    { category: 'Workout Logging', triggers: [
      { command: 'Log workout: Jump rope night', description: 'Log jump rope workout (Mon/Wed/Fri)' },
      { command: 'Log workout: Body weight day, push-ups 4x10', description: 'Log bodyweight workout (Tues/Thur/Sat)' },
      { command: 'Log workout: ... only did 20 sets', description: 'Log partial completion' }
    ]},
    { category: 'Workout Queries', triggers: [
      { command: 'How many workouts did I do this week?', description: 'Query workout count for time period' },
      { command: 'How many jump rope workouts this month?', description: 'Query specific workout type' }
    ]},
    { category: 'Workout Info', triggers: [
      { command: "What's tonight's workout?", description: 'Get tonight workout type' }
    ]},
    { category: 'Health Logging', triggers: [
      { command: 'Log health: Weight: 75.5kg', description: 'Log body weight' },
      { command: 'Log health: Walked 10000 steps', description: 'Log steps' }
    ]},
    { category: 'Profile', triggers: [
      { command: 'Set profile: Age: 30, Sex: Male, Height: 175cm', description: 'Create user profile' }
    ]}
  ],
  general_helper: [
    { category: 'General', triggers: [
      { command: 'Any message', description: 'Responds using the LLM with IT/tech persona' }
    ]}
  ],
  math_tutor: [
    { category: 'General', triggers: [
      { command: 'Any math question', description: 'Responds using the LLM with math tutor persona' }
    ]}
  ],
  icelandic_teacher: [
    { category: 'General', triggers: [
      { command: 'Any message', description: 'Responds using the LLM with Icelandic teacher persona' }
    ]}
  ]
};

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
  schedulesList: document.getElementById('schedules-list'),
  noSchedules: document.getElementById('no-schedules'),
  addScheduleBtn: document.getElementById('add-schedule-btn'),
  scheduleModal: document.getElementById('schedule-modal'),
  scheduleForm: document.getElementById('schedule-form'),
  scheduleModalTitle: document.getElementById('schedule-modal-title'),
  editScheduleIndex: document.getElementById('edit-schedule-index'),
  scheduleName: document.getElementById('schedule-name'),
  scheduleInterval: document.getElementById('schedule-interval'),
  scheduleStartHour: document.getElementById('schedule-start-hour'),
  scheduleEndHour: document.getElementById('schedule-end-hour'),
  scheduleMessage: document.getElementById('schedule-message'),
  cancelBtn: document.getElementById('cancel-btn'),
  deleteModal: document.getElementById('delete-modal'),
  deleteName: document.getElementById('delete-name'),
  cancelDelete: document.getElementById('cancel-delete'),
  confirmDelete: document.getElementById('confirm-delete'),
  loading: document.getElementById('loading'),
  error: document.getElementById('error'),
  personaList: document.getElementById('persona-list'),
  triggersList: document.getElementById('triggers-list'),
  reloadSchedulesBtn: document.getElementById('reload-schedules-btn'),
};

let currentSchedules = [];
let deleteTargetId = null;

async function loadConfig() {
  showLoading(true);
  hideError();
  hideEditor();

  try {
    const [configRes, schedulesRes] = await Promise.all([
      fetch(`${API_BASE}/api/config`),
      fetch(`${BOT_API_BASE}/api/schedules`).catch(() => ({ ok: false, json: () => ({}) }))
    ]);

    if (!configRes.ok) throw new Error('Failed to load config');
    const config = await configRes.json();
    personas = config.personas || {};

    if (schedulesRes.ok) {
      activeSchedules = await schedulesRes.json();
    }

    populateSelect();
    renderList();
  } catch (err) {
    showError('Failed to load configuration: ' + err.message);
  } finally {
    showLoading(false);
  }
}

async function fetchActiveSchedules() {
  try {
    const res = await fetch(`${BOT_API_BASE}/api/schedules`);
    if (res.ok) {
      activeSchedules = await res.json();
    }
  } catch (err) {
    console.error('Failed to fetch active schedules:', err);
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
    const schedules = persona.proactive_scheduling || [];
    const enabledCount = schedules.filter(s => s && s.enabled).length;
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
          <span class="dot ${enabledCount > 0 ? '' : 'disabled'}"></span>
          <span>${enabledCount} check-in${enabledCount !== 1 ? 's' : ''} enabled</span>
        </div>
      </div>
    `;
    els.personaList.appendChild(item);
  }
}

function renderSchedules() {
  els.schedulesList.innerHTML = '';
  const hasSchedules = currentSchedules.length > 0;
  els.noSchedules.classList.toggle('hidden', hasSchedules);

  currentSchedules.forEach((schedule, index) => {
    const isActive = activeSchedules.some(s => s.job_id === `proactive_${schedule.id}`);
    const item = document.createElement('div');
    item.className = 'schedule-item';
    item.innerHTML = `
      <div class="schedule-item-header">
        <span class="schedule-item-name">${escapeHtml(schedule.name || 'Unnamed')}</span>
        <div class="schedule-item-status">
          <span class="status-dot ${isActive ? '' : 'paused'}"></span>
          <span>${isActive ? 'Active' : 'Paused'}</span>
        </div>
      </div>
      <div class="schedule-item-details">
        Every ${schedule.interval_seconds || 300}s | ${schedule.time_window?.start_hour ?? 0}:00 - ${schedule.time_window?.end_hour ?? 23}:00
        ${schedule.message_content ? `<br>Message: ${escapeHtml(schedule.message_content.substring(0, 50))}...` : ''}
      </div>
      <div class="schedule-item-actions">
        <button class="btn btn-secondary btn-small" onclick="editSchedule(${index})">Edit</button>
        <button class="btn btn-secondary btn-small" onclick="toggleSchedule('${schedule.id}', ${!isActive})">${isActive ? 'Pause' : 'Resume'}</button>
        <button class="btn btn-danger btn-small" onclick="deleteSchedule(${index})">Delete</button>
      </div>
    `;
    els.schedulesList.appendChild(item);
  });
}

function renderTriggers(personaName) {
  const name = (personaName || '').toLowerCase();
  let triggers = PERSONA_TRIGGERS.default;

  if (name.includes('trainer') || name.includes('fitness') || name.includes('workout')) {
    triggers = PERSONA_TRIGGERS.trainer;
  } else if (name.includes('it') || name.includes('tech') || name.includes('helper')) {
    triggers = PERSONA_TRIGGERS.general_helper;
  } else if (name.includes('math') || name.includes('tutor')) {
    triggers = PERSONA_TRIGGERS.math_tutor;
  } else if (name.includes('icelandic') || name.includes('language') || name.includes('teacher')) {
    triggers = PERSONA_TRIGGERS.icelandic_teacher;
  }

  els.triggersList.innerHTML = triggers.map(category => `
    <div class="trigger-category">${category.category}</div>
    ${category.triggers.map(t => `
      <div class="trigger-item">
        <div class="trigger-command">${escapeHtml(t.command)}</div>
        <div class="trigger-description">${escapeHtml(t.description)}</div>
      </div>
    `).join('')}
  `).join('');
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
  currentSchedules = [];
  renderSchedules();
  renderTriggers('');
  showEditor(true);
}

async function startEdit(channelId) {
  const persona = personas[channelId];
  if (!persona) return;

  await fetchActiveSchedules();

  els.isNew.value = 'false';
  els.editorTitle.textContent = 'Edit Persona';
  els.channelId.value = channelId;
  els.channelId.disabled = true;
  els.name.value = persona.name || '';
  els.description.value = persona.description || '';
  els.prompt.value = persona.prompt || '';
  currentSchedules = persona.proactive_scheduling || [];
  renderSchedules();
  renderTriggers(persona.name || '');
  showEditor(true);
}

function resetForm() {
  els.isNew.value = '';
  els.channelId.value = '';
  els.channelId.disabled = false;
  els.name.value = '';
  els.description.value = '';
  els.prompt.value = '';
  currentSchedules = [];
  hideEditor();
}

function openScheduleModal(index = -1) {
  const isEdit = index >= 0;
  els.scheduleModalTitle.textContent = isEdit ? 'Edit Check-in' : 'Add Check-in';
  els.editScheduleIndex.value = index;

  if (isEdit) {
    const schedule = currentSchedules[index];
    els.scheduleName.value = schedule.name || '';
    els.scheduleInterval.value = schedule.interval_seconds || 300;
    els.scheduleStartHour.value = schedule.time_window?.start_hour ?? 18;
    els.scheduleEndHour.value = schedule.time_window?.end_hour ?? 19;
    els.scheduleMessage.value = schedule.message_content || '';
  } else {
    els.scheduleName.value = '';
    els.scheduleInterval.value = 3600;
    els.scheduleStartHour.value = 18;
    els.scheduleEndHour.value = 19;
    els.scheduleMessage.value = '';
  }

  els.scheduleModal.classList.remove('hidden');
}

function closeScheduleModal() {
  els.scheduleModal.classList.add('hidden');
}

function editSchedule(index) {
  openScheduleModal(index);
}

function deleteSchedule(index) {
  if (confirm('Delete this check-in?')) {
    currentSchedules.splice(index, 1);
    renderSchedules();
  }
}

async function toggleSchedule(scheduleId, enable) {
  const jobId = `proactive_${scheduleId}`;
  try {
    const endpoint = enable ? 'resume' : 'pause';
    const res = await fetch(`${BOT_API_BASE}/api/schedules/${jobId}/${endpoint}`, { method: 'POST' });
    if (res.ok) {
      showToast(enable ? 'Schedule resumed' : 'Schedule paused', 'success');
      await new Promise(r => setTimeout(r, 600));
      await loadConfig();
      startEdit(els.channelId.value);
    } else {
      showToast('Failed to update schedule', 'error');
    }
  } catch (err) {
    showToast('Error: ' + err.message, 'error');
  }
}

async function reloadSchedules() {
  await reloadBotAndRefresh();
}

async function reloadBotAndRefresh() {
  try {
    const res = await fetch(`${API_BASE}/api/config/reload`, { method: 'POST' });
    const data = await res.json();
    if (res.ok && data.status === 'reloaded') {
      showToast('Schedules reloaded', 'success');
    } else {
      showToast(data.message || 'Failed to reload bot schedules', 'error');
    }
    await loadConfig();
    const channelId = els.channelId.value;
    if (channelId) {
      await startEdit(channelId);
    }
  } catch (err) {
    showToast('Cannot connect to bot. Is it running?', 'error');
  }
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
els.addScheduleBtn.addEventListener('click', () => openScheduleModal());
els.reloadSchedulesBtn.addEventListener('click', reloadSchedules);

els.scheduleForm.addEventListener('submit', (e) => {
  e.preventDefault();
  const index = parseInt(els.editScheduleIndex.value);

  const schedule = {
    id: index >= 0 ? (currentSchedules[index].id || generateId()) : generateId(),
    name: els.scheduleName.value.trim(),
    enabled: true,
    interval_seconds: parseInt(els.scheduleInterval.value) || 3600,
    time_window: {
      start_hour: parseInt(els.scheduleStartHour.value) || 18,
      end_hour: parseInt(els.scheduleEndHour.value) || 19
    },
    message_content: els.scheduleMessage.value.trim() || null
  };

  if (index >= 0) {
    currentSchedules[index] = schedule;
  } else {
    currentSchedules.push(schedule);
  }

  closeScheduleModal();
  renderSchedules();
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

els.form.addEventListener('submit', async (e) => {
  e.preventDefault();

  const isNew = els.isNew.value === 'true';
  const channelId = els.channelId.value.trim();

  if (!channelId || !els.name.value.trim() || !els.prompt.value.trim()) {
    showToast('Please fill in all required fields', 'error');
    return;
  }

  const personaData = {
    name: els.name.value.trim(),
    description: els.description.value.trim(),
    prompt: els.prompt.value.trim(),
    proactive_scheduling: currentSchedules
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
    showToast(isNew ? 'Persona created' : 'Persona updated. Click Reload Schedules to apply.', 'success');
    await loadConfig();
  } else {
    const error = await response.json();
    showToast(error.error || 'Failed to save persona', 'error');
  }
});

function generateId() {
  return 'schedule_' + Date.now().toString(36);
}

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
