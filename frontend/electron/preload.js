import { contextBridge } from 'electron'

contextBridge.exposeInMainWorld('credexa', {
  backendBaseUrl: 'http://127.0.0.1:8765',
})
