const {
  app, BrowserWindow, ipcMain, clipboard,
  screen, desktopCapturer, nativeImage, Menu, Tray
} = require('electron');
const path = require('path');
const { OpenAI } = require('openai');
const { uIOhook } = require('uiohook-napi');

const qwen = new OpenAI({
  apiKey: 'sk-a911b5d2dab44dccb01d168083ed8100',
  baseURL: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
});

let petWindow, translationWindow, screenshotWindow, tray;
let realtimeInterval = null;
let lastClipboardText = '';
let isRealtimeOn = false;

// ─── Keyboard/sleep detection ────────────────────────────────────────────────
let typingTimer = null;
let sleepTimer = null;
let isTyping = false;
let isSleeping = false;
const TYPING_STOP_MS = 2000;  // return to idle after 2s no keypress
const SLEEP_IDLE_MS  = 5 * 60 * 1000; // sleep after 5 min no input

function onKeyActivity() {
  if (isSleeping) {
    isSleeping = false;
    sendPetMode('idle');
  }
  // Reset sleep timer
  clearTimeout(sleepTimer);
  sleepTimer = setTimeout(() => {
    isSleeping = true;
    sendPetMode('sleeping');
  }, SLEEP_IDLE_MS);

  // Typing animation
  if (!isTyping) {
    isTyping = true;
    sendPetMode('typing');
  }
  clearTimeout(typingTimer);
  typingTimer = setTimeout(() => {
    isTyping = false;
    if (!isSleeping) sendPetMode('idle');
  }, TYPING_STOP_MS);
}

function sendPetMode(mode) {
  if (petWindow && !petWindow.isDestroyed()) {
    petWindow.webContents.send('set-mode', mode);
  }
}

// ─── Window factories ────────────────────────────────────────────────────────

function createPetWindow() {
  petWindow = new BrowserWindow({
    width: 120,
    height: 140,
    transparent: true,
    frame: false,
    alwaysOnTop: true,
    resizable: false,
    skipTaskbar: true,
    hasShadow: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  petWindow.loadFile('src/pet.html');
  petWindow.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });

  // Start in bottom-right corner
  const { width, height } = screen.getPrimaryDisplay().workAreaSize;
  petWindow.setPosition(width - 140, height - 160);
}

function createTranslationWindow() {
  translationWindow = new BrowserWindow({
    width: 440,
    height: 320,
    transparent: true,
    frame: false,
    alwaysOnTop: true,
    show: false,
    resizable: true,
    hasShadow: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  translationWindow.loadFile('src/translation.html');
}

function createScreenshotWindow() {
  const { width, height } = screen.getPrimaryDisplay().size;
  screenshotWindow = new BrowserWindow({
    width,
    height,
    transparent: true,
    frame: false,
    alwaysOnTop: true,
    show: false,
    fullscreen: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  screenshotWindow.loadFile('src/screenshot.html');
}

// ─── Show translation result near the pet ───────────────────────────────────

function showTranslation(text, loading = false) {
  const [px, py] = petWindow.getPosition();
  const { width: sw, height: sh } = screen.getPrimaryDisplay().workAreaSize;
  let tx = px + 130;
  let ty = py;
  if (tx + 440 > sw) tx = px - 450;
  if (ty + 320 > sh) ty = sh - 320;
  translationWindow.setPosition(Math.max(0, tx), Math.max(0, ty));
  translationWindow.webContents.send('update-translation', { text, loading });
  if (!translationWindow.isVisible()) translationWindow.show();
}

// ─── Qwen API helpers ────────────────────────────────────────────────────────

async function translateText(text) {
  const res = await qwen.chat.completions.create({
    model: 'qwen-plus',
    messages: [
      {
        role: 'system',
        content: '你是专业翻译助手，请将用户输入的英文翻译成中文，只返回翻译结果，不需要解释或前缀。',
      },
      { role: 'user', content: text },
    ],
  });
  return res.choices[0].message.content.trim();
}

async function translateImage(base64Png) {
  const res = await qwen.chat.completions.create({
    model: 'qwen-vl-plus',
    messages: [
      {
        role: 'user',
        content: [
          {
            type: 'image_url',
            image_url: { url: `data:image/png;base64,${base64Png}` },
          },
          {
            type: 'text',
            text: '请识别图片中的所有英文文字，然后将其翻译成中文。格式：\n【原文】\n...\n【译文】\n...',
          },
        ],
      },
    ],
  });
  return res.choices[0].message.content.trim();
}

// ─── IPC handlers ────────────────────────────────────────────────────────────

ipcMain.handle('move-pet', (_, { x, y }) => petWindow.setPosition(x, y));
ipcMain.handle('get-pet-position', () => petWindow.getPosition());

ipcMain.handle('start-screenshot', async () => {
  try {
    const { width, height } = screen.getPrimaryDisplay().size;
    const sources = await desktopCapturer.getSources({
      types: ['screen'],
      thumbnailSize: { width, height },
    });
    if (!sources.length) return;
    const imgData = sources[0].thumbnail.toDataURL();
    screenshotWindow.setSize(width, height);
    screenshotWindow.setPosition(0, 0);
    screenshotWindow.webContents.send('set-screenshot', imgData);
    screenshotWindow.show();
    screenshotWindow.focus();
  } catch (e) {
    showTranslation('截屏失败：' + e.message);
  }
});

ipcMain.handle('screenshot-selected', async (_, { x, y, w, h, imgData }) => {
  screenshotWindow.hide();
  if (w < 5 || h < 5) return;
  showTranslation('正在识别并翻译…', true);
  try {
    const img = nativeImage.createFromDataURL(imgData);
    const cropped = img.crop({ x: Math.round(x), y: Math.round(y), width: Math.round(w), height: Math.round(h) });
    const base64 = cropped.toPNG().toString('base64');
    const result = await translateImage(base64);
    showTranslation(result);
  } catch (e) {
    showTranslation('翻译失败：' + e.message);
  }
});

ipcMain.handle('cancel-screenshot', () => screenshotWindow.hide());

ipcMain.handle('translate-clipboard', async () => {
  const text = clipboard.readText().trim();
  if (!text) { showTranslation('剪贴板为空'); return; }
  showTranslation('正在翻译…', true);
  try {
    const result = await translateText(text);
    showTranslation(result);
  } catch (e) {
    showTranslation('翻译失败：' + e.message);
  }
});

ipcMain.handle('start-realtime', () => {
  if (isRealtimeOn) return { status: 'already' };
  isRealtimeOn = true;
  lastClipboardText = clipboard.readText();
  realtimeInterval = setInterval(async () => {
    const cur = clipboard.readText().trim();
    if (cur && cur !== lastClipboardText) {
      lastClipboardText = cur;
      try {
        const result = await translateText(cur);
        showTranslation(result);
      } catch { /* silent fail */ }
    }
  }, 1200);
  petWindow.webContents.send('realtime-status', { on: true });
  return { status: 'started' };
});

ipcMain.handle('stop-realtime', () => {
  if (realtimeInterval) { clearInterval(realtimeInterval); realtimeInterval = null; }
  isRealtimeOn = false;
  petWindow.webContents.send('realtime-status', { on: false });
  return { status: 'stopped' };
});

ipcMain.handle('close-translation', () => translationWindow.hide());

ipcMain.handle('copy-translation', (_, text) => clipboard.writeText(text));

// ─── App lifecycle ───────────────────────────────────────────────────────────

app.whenReady().then(() => {
  createPetWindow();
  createTranslationWindow();
  createScreenshotWindow();

  // Global keyboard & mouse hook
  try {
    uIOhook.on('keydown', onKeyActivity);
    uIOhook.on('mouseclick', onKeyActivity);
    uIOhook.start();
  } catch (e) {
    console.warn('uIOhook failed to start:', e.message);
  }

  // Start sleep timer immediately
  sleepTimer = setTimeout(() => {
    isSleeping = true;
    sendPetMode('sleeping');
  }, SLEEP_IDLE_MS);
});

app.on('before-quit', () => {
  try { uIOhook.stop(); } catch {}
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
