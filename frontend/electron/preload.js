import { contextBridge, ipcRenderer } from 'electron'

contextBridge.exposeInMainWorld('credexa', {
  backendBaseUrl: 'http://127.0.0.1:8765',
  openFiles: () => ipcRenderer.invoke('open-file-dialog'),
  readFile: (filePath) => ipcRenderer.invoke('read-file', filePath),
  getBackendStatus: () => ipcRenderer.invoke('get-backend-status'),
})
