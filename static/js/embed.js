/**
 * Copyright 2019 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

'use strict';
if (typeof window.availableFrames === 'undefined') {
  // Add support for multiple frames (including this file multiple times).
  window.availableFrames = {};
  window.VALID_ORIGINS = [
    'http://localhost:8080',
    'http://127.0.0.1:8080',
    'http://[::1]:8080',
  ];
  // TODO: remove message below once origins can be defined in a cleaner way.
  console.log(
      '[embed.js] - Temporarily disabled message origin checking. Please fix.');
  window.addEventListener('message', receiveMessage, false);
}
function generateId() {
  return 'vcdb-' + Math.floor(Math.random() * 1e6);
}

function receiveMessage(event) {
  /*
  // Skipping for now, see log message further above.
  if (window.VALID_ORIGINS.indexOf(event.origin) === -1) {
    console.log('Denied origin: ' + event.origin + ' for security reasons!\n');
    return;
  }
  */

  if (event.data.type === 'resize') {
    const editorDimensions = event.data.payload;
    const targetFrameId = event.data.source;
    // Resize iframe accordingly.
    if (targetFrameId in availableFrames) {
      availableFrames[targetFrameId].style.height =
          Number(editorDimensions.height) + 'px';
    } else {
      console.log('receiveMessage(): Unknown target frame.');
    }
  }
}
function getUrl() {
  const scripts = document.getElementsByTagName('script');
  for (let i = scripts.length - 1; i >= 0; i--) {
    const script = scripts[i];
    const u = new URL(script.src);
    if (u.pathname === '/static/js/embed.js') {
      return {
        origin: u.origin,
        params: u.search.substr(1),
      };
    }
  }
  alert('Unable find backend');
}

function appendIframe() {
  const frameId = generateId();
  document.write(`<iframe id="${frameId}"></iframe>`);
  const iframe = document.getElementById(frameId);
  const {origin, params} = getUrl();

  let embedUrl = '';
  let embedParams = '';
  const vars = params.split('&');
  for (let i = 0; i < vars.length; i++) {
    const pair = vars[i].split('=');
    if (decodeURIComponent(pair[0]) === 'vcdb_id') {
      embedUrl += pair[1] + '/embed?';
    } else {
      embedParams += pair[0] + '=' + pair[1] + '&';
    }
  }
  embedParams = embedParams.replace(/&+$/, '');

  iframe.src = `${origin}/${embedUrl}${embedParams}#` + frameId;
  iframe.setAttribute('frameborder', '0');
  iframe.style.position = 'relative';
  iframe.style.width = '100%';
  iframe.style.height = '0px';
  window.availableFrames[frameId] = iframe;
}
appendIframe();
