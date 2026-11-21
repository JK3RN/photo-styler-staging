import { mkdir, readFile, readdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';

const [mediaDir, outputDir, profileDir, appUrl] = process.argv.slice(2);
const activePort = (await readFile(resolve(profileDir, 'DevToolsActivePort'), 'utf8')).split('\n')[0];
const targets = await (await fetch(`http://127.0.0.1:${activePort}/json/list`)).json();
const ws = new WebSocket(targets.find(target => target.type === 'page').webSocketDebuggerUrl);
await new Promise((ok, fail) => {
  ws.addEventListener('open', ok, {once:true});
  ws.addEventListener('error', fail, {once:true});
});
let seq = 0;
const pending = new Map();
const errors = [];
const requests = [];
const networkStatuses = [];
ws.addEventListener('message', ({data}) => {
  const {id, method, params, error, result} = JSON.parse(data);
  if (method === 'Runtime.exceptionThrown') errors.push(params.exceptionDetails);
  if (method === 'Network.requestWillBeSent') requests.push(params.request.url);
  if (method === 'Network.responseReceived') networkStatuses.push(params.response.status);
  if (!pending.has(id)) return;
  const {ok, fail} = pending.get(id);
  pending.delete(id);
  if (error) fail(new Error(JSON.stringify(error)));
  else ok(result);
});
function call(method, params = {}) {
  const id = ++seq;
  return new Promise((ok, fail) => {
    pending.set(id, {ok, fail});
    ws.send(JSON.stringify({id, method, params}));
  });
}
async function evaluate(expression) {
  const result = await call('Runtime.evaluate', {expression, returnByValue:true, awaitPromise:true});
  if (result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails));
  return result.result.value;
}
async function waitFor(expression) {
  for (let attempt = 0; attempt < 100; attempt++) {
    if (await evaluate(expression)) return;
    await new Promise(ok => setTimeout(ok, 100));
  }
  throw new Error(`Timed out: ${expression}`);
}
try {
  await mkdir(outputDir, {recursive:true});
  await call('Runtime.enable');
  await call('Page.enable');
  await call('Network.enable');
  await call('Emulation.setDeviceMetricsOverride', {width:1440,height:1000,deviceScaleFactor:1,mobile:false});
  await call('Browser.setDownloadBehavior', {behavior:'allow',downloadPath:outputDir});
  await call('Page.navigate', {url:appUrl});
  await waitFor("document.querySelector('#preset-select')?.options.length >= 2");
  const root = await call('DOM.getDocument');
  const {nodeId} = await call('DOM.querySelector', {nodeId:root.root.nodeId,selector:'#image-input'});
  await call('DOM.setFileInputFiles', {nodeId,files:[resolve(mediaDir,'signal-valley.png')]});
  await waitFor("document.querySelector('#preview').naturalWidth === 1200 && document.querySelector('#busy').hidden");
  const firstPreview = await evaluate("document.querySelector('#preview').src");
  await evaluate(`(() => {
    const select = document.querySelector('#preset-select');
    select.value = [...select.options].find(option => option.textContent === 'Dusk Cyan Artwork').value;
    document.querySelector('#load-preset').click();
  })()`);
  await waitFor(`document.querySelector('#preview').src !== ${JSON.stringify(firstPreview)} && document.querySelector('#preview').naturalHeight === 750 && document.querySelector('#busy').hidden`);
  const cyanPreview = await evaluate("document.querySelector('#preview').src");
  await evaluate(`(() => {
    const select = document.querySelector('#preset-select');
    select.value = [...select.options].find(option => option.textContent === 'Red CRT').value;
    document.querySelector('#load-preset').click();
  })()`);
  await waitFor(`document.querySelector('#preview').src !== ${JSON.stringify(cyanPreview)} && document.querySelector('#busy').hidden`);
  await evaluate("document.querySelector('#preview').decode()");
  if (!(await evaluate("document.querySelector('aside').scrollWidth === document.querySelector('aside').clientWidth"))) {
    throw new Error("Preset panel overflows horizontally");
  }
  const screenshot = await call('Page.captureScreenshot', {format:'png',captureBeyondViewport:false});
  await writeFile(resolve(outputDir,'application.png'), Buffer.from(screenshot.data,'base64'));
  await evaluate(`(() => {
    const format = document.querySelector('#output-format');
    format.value = 'png';
    format.dispatchEvent(new Event('change', {bubbles:true}));
    document.querySelector('#export').click();
  })()`);
  await waitFor("document.querySelector('#status').textContent.startsWith('EXPORT READY')");
  for (let i = 0; i < 30; i++) {
    if ((await readdir(outputDir)).includes('signal-valley-styled.png')) break;
    if (i === 29) throw new Error('Download missing');
    await new Promise(ok => setTimeout(ok,100));
  }
  const redPreview = await evaluate("document.querySelector('#preview').src");
  await evaluate(`(() => {
    const color = document.querySelector('#palette input');
    color.value = '#102030';
    color.dispatchEvent(new Event('input', {bubbles:true}));
    document.querySelector('[name=dithering]').click();
    const scanlines = document.querySelector('[name=scanline_opacity]');
    scanlines.value = '0.42';
    scanlines.dispatchEvent(new Event('input', {bubbles:true}));
  })()`);
  await waitFor(`document.querySelector('#preview').src !== ${JSON.stringify(redPreview)} && document.querySelector('#preview').naturalWidth === 1200 && document.querySelector('#busy').hidden`);
  await evaluate(`(() => {
    document.querySelector('#preset-name').value = 'Browser QA CRT';
    document.querySelector('#save-preset').click();
  })()`);
  await waitFor("document.querySelector('#status').textContent === 'PRESET SAVED // Browser QA CRT'");
  await call('Page.reload');
  await waitFor("[...document.querySelectorAll('#preset-select option')].some(option => option.textContent === 'Browser QA CRT')");
  const origin = new URL(appUrl).origin;
  if (errors.length || networkStatuses.some(status => status >= 400) ||
      requests.some(url => !(url.startsWith(origin + '/') || url.startsWith('blob:' + origin)))) {
    throw new Error(JSON.stringify({errors, requests, networkStatuses}));
  }
  console.log(JSON.stringify({preview:'1200x750',export:'signal-valley-styled.png',preset:'round-trip',externalRequests:0,pageErrors:0}, null,2));
} finally {
  ws.close();
}
