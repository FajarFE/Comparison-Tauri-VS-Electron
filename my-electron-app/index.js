const { app, BrowserWindow, ipcMain } = require('electron/main');
const path = require('node:path');
const createWindow = () => {
  const win = new BrowserWindow({
    width: 800,
    height: 600,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
    },
  });

  win.loadFile('index.html');
  console.time('electron-app-ready');
  app.on('ready', () => {
    console.timeEnd('electron-app-ready');
    console.time('electron-window-ready-to-show');
    const mainWindow = new BrowserWindow({ show: false /* ... */ });
    mainWindow.loadFile('index.html');
    mainWindow.once('ready-to-show', () => {
      console.timeEnd('electron-window-ready-to-show');
      mainWindow.show();
    });
  });
};

app.whenReady().then(() => {
  ipcMain.handle('ping', () => 'pong');
  createWindow();
});
