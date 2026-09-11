const http = require('http');

function httpGet(url) {
  return new Promise((resolve, reject) => {
    http.get(url, res => {
      let d = '';
      res.on('data', c => d += c);
      res.on('end', () => resolve(JSON.parse(d)));
    }).on('error', reject);
  });
}

(async () => {
  const { exec } = require('child_process');
  // launch Chrome with remote debugging
  const chromeProc = exec('"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" --headless --remote-debugging-port=9222 --disable-gpu http://localhost:8000/');
  
  await new Promise(r => setTimeout(r, 2000));
  try {
    const version = await httpGet('http://127.0.0.1:9222/json/version');
    console.log('DevTools active:', version.Browser);
    const pages = await httpGet('http://127.0.0.1:9222/json/list');
    console.log('Pages list length:', pages.length);
    if (pages.length > 0) {
      console.log('Target page URL:', pages[0].url);
      console.log('WebSocket URL:', pages[0].webSocketDebuggerUrl);
    }
  } catch (e) {
    console.error('CDP connect error:', e.message);
  } finally {
    chromeProc.kill();
  }
})();
