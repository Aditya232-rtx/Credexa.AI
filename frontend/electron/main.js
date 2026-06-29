import { app, BrowserWindow, dialog, ipcMain } from 'electron'
import { spawn } from 'child_process'
import path from 'path'
import { fileURLToPath } from 'url'
import fs from 'fs'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
let backendProcess = null
let mainWindow = null
let backendReady = false

function startBackend() {
  const backendDir = path.resolve(__dirname, '..', '..', 'backend')
  const venvDir = path.resolve(__dirname, '..', '..', '.venv')
  let backendCommand = process.platform === 'win32' ? 'python' : 'python3.11'
  const venvPythonPath = process.platform === 'win32'
    ? path.join(venvDir, 'Scripts', 'python.exe')
    : path.join(venvDir, 'bin', 'python')
  if (fs.existsSync(venvPythonPath)) {
    backendCommand = venvPythonPath
  }
  backendProcess = spawn(
    backendCommand,
    ['-m', 'uvicorn', 'api.main:app', '--host', '127.0.0.1', '--port', '8765'],
    {
      cwd: backendDir,
      stdio: 'inherit',
      env: { ...process.env, PYTHONPATH: backendDir },
    },
  )
  backendProcess.on('exit', (code) => {
    backendReady = false
  })
  backendProcess.on('spawn', () => {
    backendReady = true
  })
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1500,
    height: 980,
    minWidth: 1280,
    minHeight: 840,
    backgroundColor: '#f7f8fb',
    title: 'Credexa AI',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  })
  const devServerUrl = process.env.VITE_DEV_SERVER_URL || 'http://localhost:5173'
  if (process.env.NODE_ENV === 'development') {
    mainWindow.loadURL(devServerUrl)
    mainWindow.webContents.openDevTools({ mode: 'detach' })
  } else {
    mainWindow.loadFile(path.join(__dirname, '..', 'dist', 'index.html'))
  }
}

// ─── IPC Handlers ──────────────────────────────────────────────────────────

ipcMain.handle('open-file-dialog', async () => {
  const result = await dialog.showOpenDialog({
    properties: ['openFile', 'multiSelections'],
    filters: [
      {
        name: 'Documents',
        extensions: ['pdf', 'png', 'jpg', 'jpeg', 'tiff', 'docx', 'xlsx', 'csv'],
      },
    ],
  })
  return result.filePaths
})

ipcMain.handle('read-file', async (_event, filePath) => {
  const buffer = fs.readFileSync(filePath)
  const ext = path.extname(filePath).toLowerCase()
  const mimeMap = {
    '.pdf': 'application/pdf',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.tiff': 'image/tiff',
    '.tif': 'image/tiff',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    '.csv': 'text/csv',
  }
  return {
    name: path.basename(filePath),
    type: mimeMap[ext] || 'application/octet-stream',
    data: buffer.toString('base64'),
  }
})

ipcMain.handle('get-backend-status', () => {
  return { running: backendProcess !== null && !backendProcess.killed, ready: backendReady }
})

// ─── App Lifecycle ─────────────────────────────────────────────────────────

app.whenReady().then(() => {
  startBackend()
  createWindow()
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
})

app.on('window-all-closed', () => {
  if (backendProcess) {
    backendProcess.kill()
  }
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

app.on('before-quit', () => {
  if (backendProcess) {
    backendProcess.kill()
  }
})
