const connectBtn = document.getElementById('connectBtn');
const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const toggleDirectionBtn = document.getElementById('toggleDirectionBtn');
const directionLabel = document.getElementById('directionLabel');
const statusEl = document.getElementById('status');
const eventsEl = document.getElementById('events');
const transcriptsEl = document.getElementById('transcripts');
const translationProgress = document.getElementById('translationProgress');
const inputLanguageSelect = document.getElementById('inputLanguage');
const outputLanguageSelect = document.getElementById('outputLanguage');

let ws = null;
let audioContext = null;
let processor = null;
let stream = null;
let source = null;
let directionMode = 0;

const languages = [
  { code: 'auto', name: 'Auto detect' },
  { code: 'en', name: 'English' },
  { code: 'es', name: 'Spanish' },
  { code: 'fr', name: 'French' },
  { code: 'de', name: 'German' },
  { code: 'zh', name: 'Chinese' },
  { code: 'ja', name: 'Japanese' },
  { code: 'ru', name: 'Russian' },
  { code: 'pt', name: 'Portuguese' },
  { code: 'it', name: 'Italian' },
  { code: 'ar', name: 'Arabic' },
  { code: 'hi', name: 'Hindi' },
];

function buildLanguageOptions() {
  languages.forEach((lang) => {
    const optionA = document.createElement('option');
    optionA.value = lang.code;
    optionA.textContent = lang.name;
    inputLanguageSelect.appendChild(optionA);

    const optionB = document.createElement('option');
    optionB.value = lang.code;
    optionB.textContent = lang.name;
    outputLanguageSelect.appendChild(optionB);
  });
  inputLanguageSelect.value = 'en';
  outputLanguageSelect.value = 'es';
}

function getLanguageState() {
  return {
    sourceLanguage: inputLanguageSelect.value,
    targetLanguage: outputLanguageSelect.value,
    direction: directionMode === 0 ? 'user1-to-user2' : 'user2-to-user1',
  };
}

function updateDirectionLabel() {
  const inputText = directionMode === 0 ? 'User 1' : 'User 2';
  const outputText = directionMode === 0 ? 'User 2' : 'User 1';
  const inputLang = inputLanguageSelect.options[inputLanguageSelect.selectedIndex].text;
  const outputLang = outputLanguageSelect.options[outputLanguageSelect.selectedIndex].text;
  directionLabel.textContent = `${inputText} (${inputLang}) → ${outputText} (${outputLang})`;
}

function notifyServerLanguageChange() {
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    return;
  }
  const languageState = getLanguageState();
  ws.send(JSON.stringify({ type: 'language.update', ...languageState }));
}

function updateProgress(value) {
  translationProgress.value = value;
}

function setStatus(text) {
  statusEl.textContent = text;
}

function appendEvent(message) {
  const item = document.createElement('li');
  item.textContent = message;
  eventsEl.prepend(item);
}

function appendTranscript(text) {
  const item = document.createElement('li');
  item.textContent = text;
  transcriptsEl.prepend(item);
}

function setStatus(text) {
  statusEl.textContent = text;
}

function floatTo16BitPCM(float32Array) {
  const buffer = new ArrayBuffer(float32Array.length * 2);
  const view = new DataView(buffer);
  for (let i = 0; i < float32Array.length; i++) {
    let s = Math.max(-1, Math.min(1, float32Array[i]));
    view.setInt16(i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }
  return new Int16Array(buffer);
}

function encodeBase64(buffer) {
  let binary = '';
  const bytes = new Uint8Array(buffer);
  const chunkSize = 0x8000;
  for (let i = 0; i < bytes.length; i += chunkSize) {
    const slice = bytes.subarray(i, i + chunkSize);
    binary += String.fromCharCode.apply(null, slice);
  }
  return btoa(binary);
}

async function connectWebSocket() {
  if (ws && ws.readyState === WebSocket.OPEN) return;

  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
  const url = `${protocol}://${window.location.host}/ws/live`;
  ws = new WebSocket(url);

  ws.onopen = () => {
    setStatus('Connected');
    appendEvent('WebSocket connected');
    connectBtn.disabled = true;
    startBtn.disabled = false;
    stopBtn.disabled = true;
    updateDirectionLabel();
    notifyServerLanguageChange();
    ws.send(JSON.stringify({ type: 'hello' }));
  };

  ws.onmessage = (event) => {
    try {
      const payload = JSON.parse(event.data);
      if (payload.type === 'transcript.final') {
        appendTranscript(`${payload.text} ${payload.translated ? '→ ' + payload.translated : ''}`);
        setStatus('Final transcript received');
        updateProgress(100);
      } else if (payload.type === 'state.update') {
        setStatus(payload.stateLabel || payload.state || 'Working');
        if (payload.progress !== undefined) {
          updateProgress(payload.progress);
        }
      } else if (payload.type === 'info' || payload.type === 'welcome' || payload.type === 'ack') {
        appendEvent(`${payload.type}: ${payload.message || payload.status || ''}`);
      } else {
        appendEvent(`received: ${JSON.stringify(payload)}`);
      }
    } catch (err) {
      appendEvent('Malformed message from server');
    }
  };

  ws.onclose = () => {
    setStatus('Disconnected');
    appendEvent('WebSocket disconnected');
    connectBtn.disabled = false;
    startBtn.disabled = true;
    stopBtn.disabled = true;
  };

  ws.onerror = () => {
    appendEvent('WebSocket error');
  };
}

async function stopMicrophone() {
  if (processor) {
    processor.disconnect();
    processor.onaudioprocess = null;
    processor = null;
  }
  if (source) {
    source.disconnect();
    source = null;
  }
  if (audioContext) {
    await audioContext.close();
    audioContext = null;
  }
  if (stream) {
    stream.getTracks().forEach((track) => track.stop());
    stream = null;
  }
  stopBtn.disabled = true;
  startBtn.disabled = false;
  appendEvent('Microphone stopped');
}

async function startMicrophone() {
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    appendEvent('Please connect before starting the microphone');
    return;
  }

  stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  audioContext = new AudioContext();
  source = audioContext.createMediaStreamSource(stream);
  processor = audioContext.createScriptProcessor(4096, 1, 1);

  processor.onaudioprocess = (event) => {
    const channelData = event.inputBuffer.getChannelData(0);
    const pcm = floatTo16BitPCM(channelData);
    const payload = {
      type: 'audio.raw',
      data: encodeBase64(pcm.buffer),
      format: 'int16',
      sample_rate: audioContext.sampleRate,
    };
    ws.send(JSON.stringify(payload));
  };

  source.connect(processor);
  processor.connect(audioContext.destination);
  startBtn.disabled = true;
  stopBtn.disabled = false;
  appendEvent('Microphone started');
}

function toggleDirection() {
  const currentSource = inputLanguageSelect.value;
  const currentTarget = outputLanguageSelect.value;
  inputLanguageSelect.value = currentTarget;
  outputLanguageSelect.value = currentSource;
  directionMode = directionMode === 0 ? 1 : 0;
  updateDirectionLabel();
  notifyServerLanguageChange();
  appendEvent('Direction switched');
}

function onLanguageChange() {
  updateDirectionLabel();
  notifyServerLanguageChange();
}

connectBtn.addEventListener('click', connectWebSocket);
startBtn.addEventListener('click', startMicrophone);
stopBtn.addEventListener('click', stopMicrophone);
toggleDirectionBtn.addEventListener('click', toggleDirection);
inputLanguageSelect.addEventListener('change', onLanguageChange);
outputLanguageSelect.addEventListener('change', onLanguageChange);

buildLanguageOptions();
updateDirectionLabel();

window.addEventListener('beforeunload', async () => {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.close();
  }
  await stopMicrophone();
});
