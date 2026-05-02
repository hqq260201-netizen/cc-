const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('api', {
  // Window movement
  movePet: (pos) => ipcRenderer.invoke('move-pet', pos),
  getPetPosition: () => ipcRenderer.invoke('get-pet-position'),

  // Translation features
  startScreenshot: () => ipcRenderer.invoke('start-screenshot'),
  screenshotSelected: (data) => ipcRenderer.invoke('screenshot-selected', data),
  cancelScreenshot: () => ipcRenderer.invoke('cancel-screenshot'),
  translateClipboard: () => ipcRenderer.invoke('translate-clipboard'),
  startRealtime: () => ipcRenderer.invoke('start-realtime'),
  stopRealtime: () => ipcRenderer.invoke('stop-realtime'),

  // Translation window
  closeTranslation: () => ipcRenderer.invoke('close-translation'),
  copyTranslation: (text) => ipcRenderer.invoke('copy-translation', text),
  quitApp: () => ipcRenderer.invoke('quit-app'),
  toggleDirection: () => ipcRenderer.invoke('toggle-direction'),

  // Events from main → renderer
  onUpdateTranslation: (cb) => ipcRenderer.on('update-translation', (_, d) => cb(d)),
  onSetScreenshot: (cb) => ipcRenderer.on('set-screenshot', (_, d) => cb(d)),
  onRealtimeStatus: (cb) => ipcRenderer.on('realtime-status', (_, d) => cb(d)),
  onSetMode: (cb) => ipcRenderer.on('set-mode', (_, mode) => cb(mode)),

  removeListener: (ch) => ipcRenderer.removeAllListeners(ch),
});
