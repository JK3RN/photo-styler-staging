const defaultSettings = {
  contrast: 1.35, brightness: 1, gamma: 1, dithering: true,
  scanline_opacity: 0.12, scanline_spacing: 3, scanline_width: 1,
  vignette_strength: 0.18,
  palette: ['#080303', '#230606', '#4a0e0c', '#942419', '#da4328', '#ff7648', '#ffc4a3'],
  output_format: 'webp', quality: 92,
};
const numericControls = ['contrast', 'brightness', 'gamma', 'scanline_opacity', 'scanline_spacing', 'vignette_strength'];
const state = { settings: loadLastSettings(), file: null, previewUrl: null, timer: null, revision: 0, rendering: false, previewQueued: false, presets: [] };
const $ = (selector) => document.querySelector(selector);

function loadLastSettings() {
  try { return { ...defaultSettings, ...JSON.parse(localStorage.getItem('photo-styler-settings')) }; }
  catch { return structuredClone(defaultSettings); }
}
function persist() {
  try { localStorage.setItem('photo-styler-settings', JSON.stringify(state.settings)); }
  catch { /* Settings still work when the browser blocks storage. */ }
}
function showSettings() {
  numericControls.forEach((name) => {
    const input = document.querySelector(`[name="${name}"]`);
    input.value = state.settings[name];
    document.querySelector(`[data-for="${name}"]`).value = state.settings[name];
  });
  $('[name="dithering"]').checked = state.settings.dithering;
  $('#output-format').value = state.settings.output_format;
  $('#quality').value = state.settings.quality;
  $('#palette').replaceChildren(...state.settings.palette.map((color, index) => {
    const input = document.createElement('input');
    input.type = 'color'; input.value = color; input.title = `Palettenstufe ${index + 1}`;
    input.addEventListener('input', () => { state.settings.palette[index] = input.value; changed(); });
    return input;
  }));
  persist();
}
function changed() {
  persist(); state.revision++;
  clearTimeout(state.timer); state.timer = setTimeout(renderPreview, 180);
}

numericControls.forEach((name) => {
  document.querySelector(`[name="${name}"]`).addEventListener('input', (event) => {
    const integer = ['scanline_spacing'].includes(name);
    state.settings[name] = integer ? Number.parseInt(event.target.value, 10) : Number.parseFloat(event.target.value);
    document.querySelector(`[data-for="${name}"]`).value = state.settings[name]; changed();
  });
});
$('[name="dithering"]').addEventListener('change', (event) => { state.settings.dithering = event.target.checked; changed(); });
$('#output-format').addEventListener('change', (event) => { state.settings.output_format = event.target.value; persist(); });
$('#quality').addEventListener('change', (event) => { state.settings.quality = Number(event.target.value); persist(); });
$('#image-input').addEventListener('change', (event) => {
  state.file = event.target.files[0] ?? null;
  state.revision++;
  clearTimeout(state.timer);
  if (state.previewUrl) URL.revokeObjectURL(state.previewUrl);
  state.previewUrl = null;
  $('#preview').removeAttribute('src'); $('#preview').hidden = true;
  $('#empty-state').hidden = Boolean(state.file);
  $('#file-label').textContent = state.file?.name ?? 'Bild auswählen';
  if (state.file) renderPreview();
  else $('#status').textContent = 'READY // NO IMAGE LOADED';
});

function setRendering(active) {
  state.rendering = active;
  $('#busy').hidden = !active;
  $('#export').disabled = active || !state.file;
}

function finishRender() {
  setRendering(false);
  if (!state.previewQueued) return;
  state.previewQueued = false;
  renderPreview();
}

async function renderPreview() {
  if (!state.file) return;
  if (state.rendering) { state.previewQueued = true; return; }
  const revision = state.revision;
  setRendering(true); $('#status').textContent = 'RENDERING PREVIEW…';
  try {
    const response = await sendRender('preview');
    if (!response.ok) throw new Error((await response.json()).detail);
    const blob = await response.blob();
    if (revision !== state.revision) return;
    if (state.previewUrl) URL.revokeObjectURL(state.previewUrl);
    state.previewUrl = URL.createObjectURL(blob); $('#preview').src = state.previewUrl; $('#preview').hidden = false;
    $('#status').textContent = `${state.file.name} // PREVIEW ${Math.round(blob.size / 1024)} KiB`;
  } catch (error) {
    if (revision === state.revision) $('#status').textContent = `ERROR // ${error.message}`;
  } finally { finishRender(); }
}
function sendRender(mode) {
  const data = new FormData(); data.append('image', state.file); data.append('settings', JSON.stringify(state.settings));
  return fetch(`/api/render/${mode}`, { method: 'POST', body: data });
}
$('#export').addEventListener('click', async () => {
  if (!state.file || state.rendering) return;
  setRendering(true); $('#status').textContent = 'RENDERING FULL RESOLUTION…';
  try {
    const response = await sendRender('export');
    if (!response.ok) throw new Error((await response.json()).detail);
    const blob = await response.blob(); const url = URL.createObjectURL(blob); const link = document.createElement('a');
    const disposition = response.headers.get('Content-Disposition') || '';
    link.href = url; link.download = disposition.match(/filename="([^"]+)"/)?.[1] || `styled.${state.settings.output_format}`;
    link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); $('#status').textContent = `EXPORT READY // ${Math.round(blob.size / 1024)} KiB`;
  } catch (error) { $('#status').textContent = `ERROR // ${error.message}`; }
  finally { finishRender(); }
});

async function loadPresets() {
  const response = await fetch('/api/presets');
  if (!response.ok) throw new Error((await response.json()).detail);
  state.presets = await response.json();
  $('#preset-select').replaceChildren(...state.presets.map((preset, index) => {
    const option = document.createElement('option'); option.value = index; option.textContent = preset.name; return option;
  }));
}
$('#load-preset').addEventListener('click', () => {
  const preset = state.presets[Number($('#preset-select').value)]; if (!preset) return;
  state.settings = structuredClone(preset.settings); showSettings(); changed();
});
$('#save-preset').addEventListener('click', async () => {
  const name = $('#preset-name').value.trim(); if (!name) { $('#status').textContent = 'ENTER A PRESET NAME'; return; }
  try {
    const response = await fetch('/api/presets', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name, settings: state.settings }) });
    if (!response.ok) throw new Error((await response.json()).detail);
    await loadPresets(); $('#status').textContent = `PRESET SAVED // ${name}`;
  } catch (error) { $('#status').textContent = `ERROR // ${error.message}`; }
});

showSettings();
loadPresets().catch((error) => { $('#status').textContent = `ERROR // ${error.message}`; });
