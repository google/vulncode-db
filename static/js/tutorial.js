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

function download(filename, text) {
  const element = document.createElement('a');
  element.setAttribute(
      'href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(text));
  element.setAttribute('download', filename);

  element.style.display = 'none';
  document.body.appendChild(element);

  element.click();

  document.body.removeChild(element);
}


function getCoords(elem) { // crossbrowser version
  const box = elem.getBoundingClientRect();

  const body = document.body;
  const docEl = document.documentElement;

  const scrollTop = window.pageYOffset || docEl.scrollTop || body.scrollTop;
  const scrollLeft = window.pageXOffset || docEl.scrollLeft || body.scrollLeft;

  const clientTop = docEl.clientTop || body.clientTop || 0;
  const clientLeft = docEl.clientLeft || body.clientLeft || 0;

  const top = box.top + scrollTop - clientTop;
  const left = box.left + scrollLeft - clientLeft;

  return {top: Math.round(top), left: Math.round(left)};
}

function getDims(elem) {
  const box = elem.getBoundingClientRect();
  return {width: box.width, height: box.height};
}

function getStylesWithoutDefaults(element) {
  // creating an empty dummy object to compare with
  // const dummy = document.createElement( 'element-' + ( new Date().getTime() )
  // );
  const dummy = document.createElement(element.tagName);
  document.body.appendChild(dummy);

  // getting computed styles for both elements
  const defaultStyles = window.getComputedStyle(dummy);
  const elementStyles = window.getComputedStyle(element);

  // calculating the difference
  const diff = {};
  for (const key in elementStyles) {
    if (elementStyles.hasOwnProperty(key) &&
        defaultStyles[key] !== elementStyles[key]) {
      diff[key] = elementStyles[key];
    }
  }

  // clear dom
  dummy.remove();

  return diff;
}

function isDescendant(parent, child) {
  let node = child.parentNode;
  while (node !== null) {
    if (node === parent) {
      return true;
    }
    node = node.parentNode;
  }
  return false;
}

function getSelectorPath(elem) {
  if (!elem) debugger;
  const parent = elem.parentElement;
  if (!parent || elem === document.body) {
    return 'body';
  }
  let path = elem.tagName.toLowerCase();
  if (elem.id) {
    path += '#' + elem.id;
  }
  const classes = Array.from(elem.classList).join('.');
  if (classes) {
    path += '.' + classes;
    path = path.replace('.tutorial-highlight', '');
  }
  let childs = Array.from(parent.querySelectorAll(':scope > ' + path));
  if (childs.length > 1) {
    let i = 0;
    for (; i < childs.length; i++) {
      if (childs[i] === elem) {
        path += `:nth-of-type(${i + 1})`;
        break;
      }
    }
  }
  childs = Array.from(parent.querySelectorAll(':scope > ' + path));
  if (childs.length !== 1) {
    alert('Invalid path');
    console.log('Invalid path ', path, ' for ', elem);
    return '';
  }
  return getSelectorPath(parent) + ' > ' + path;
}

class Tutorial {
  constructor() {
    this.steps = [];
    this.stepIdx = window.localStorage['tutorialStep'] || 0;
    this._handlers = [];
    this.unserializeSteps();
  }

  resetSteps() {
    this.stepIdx = 0;
    window.localStorage['tutorialStep'] = 0;
  }

  serializeSteps() {
    return window.localStorage['tutorial'] =
               JSON.stringify(this.steps.map((s) => {
                 const r = Object.assign({}, s);
                 r.targetPath = getSelectorPath(r.target);
                 r.target = null;
                 return r;
               }));
  }

  unserializeSteps(steps) {
    if (!steps) return;
    this.steps = steps.map((s) => {
      const r = Object.assign({}, s);
      r.target = document.querySelector(r.targetPath);
      return r;
    });
    if (this.stepIdx > this.steps.length) {
      this.stepIdx = this.steps.length;
    }
  }

  buildBackdrop() {
    this.backdrop = document.createElement('div');
    this.backdrop.id = 'tutorial-backdrop';
    document.body.appendChild(this.backdrop);
  }

  removeBackdrop() {
    this.backdrop.remove();
  }

  addEventListener(element, type, listener, options) {
    if (typeof options === 'boolean') {
      options = {capture: options};
    }
    element.addEventListener(type, listener, options);
    this._handlers.push([element, type, listener, options]);
    console.log('Added', type, listener, 'to', element);
  }

  start() {
    this.buildBackdrop();
    this.addEventListener(window, 'click', this, true);
  }

  removeListeners(options) {
    if (options) {
      const removed = [];
      let i = -1;
      for (const [element, type, listener, options] of this._handlers) {
        i++;
        if (options.element && options.element !== element) continue;
        if (options.type && options.type !== type) continue;
        element.removeEventListener(type, listener, options);
        removed.push(i);
        console.log('Removed', type, listener, 'from', element);
      }
      this._handlers = this._handlers.filter((h, i) => {
        return removed.indexOf(i) !== -1;
      });
    } else {
      for (const [element, type, listener, options] of this._handlers) {
        element.removeEventListener(type, listener, options);
        console.log('Removed', type, listener, 'from', element);
      }
      this._handlers = [];
    }
  }

  stop() {
    this.removeBackdrop();
    this.clearSteps();
    this.unhighlightAll();
    this.removeListeners();
  }

  handleEvent(e) {
    switch (e.type) {
      case 'click': {
        this.onClick(e);
      }
    }
  }

  onClick(event) {
    if (event.detail && event.detail.custom ||
        event.target.style.display === 'none') {
      return;
    }
    event.stopPropagation();
    event.preventDefault();
  }

  _highlight(el) {
    if (this.currentElement === el) {
      return false;
    }

    if (this.currentElement) {
      this.currentElement.style['z-index'] =
          this.currentElement.dataset.oldZIndex;
      this.currentElement.style.position =
          this.currentElement.dataset.oldPosition;
    }
    this.currentElement = el;
    const oldZIndex = el.style.zIndex;
    el.dataset.oldZIndex = oldZIndex;
    el.style['z-index'] = '2100';
    if (!getStylesWithoutDefaults(el).position) {
      const oldPosition = el.style.position;
      el.dataset.oldPosition = oldPosition;
      el.style.position = 'relative';
    }
    return true;
  }

  highlight(el) {
    this.backdrop.style.display = 'none';
    if (this.currentElement === el) {
      return false;
    }

    this.unhighlightAll();
    this.currentElement = el;
    el.classList.add('tutorial-highlight');
    return true;
  }

  unhighlightAll() {
    const lastEls =
        Array.from(document.querySelectorAll('.tutorial-highlight'));
    for (const lastEl of lastEls) {
      lastEl.classList.remove('tutorial-highlight');
    }
  }

  clearSteps() {
    const textBox = document.getElementById('tutorial-text');
    if (textBox) {
      textBox.style.display = 'none';
    }
  }

  showStep(step) {
    if (!step || step.target !== this.currentElement) {
      this.clearSteps();
    }
    if (!step) return false;
    this.highlight(step.target);
    const handlers = {
      text: this.showText,
      sleep: this.sleep,
      event: this.triggerEvent,
    };
    handlers[step.type].call(this, step);
    return true;
  }

  showText(step) {
    let textBox = document.getElementById('tutorial-text');
    if (!textBox) {
      textBox = document.createElement('div');
      textBox.id = 'tutorial-text';
      document.body.appendChild(textBox);
    }
    textBox.textContent = step.text;
    if (step.text) {
      textBox.style.display = 'block';
      this.placeElement(step.target, textBox);
    } else {
      textBox.style.display = 'none';
    }
    this.nextStep();
  }

  sleep(step) {
    window.setTimeout(() => this.nextStep(), step.time * 1000);
  }

  triggerEvent(step) {
    step.target.dispatchEvent(new CustomEvent(step.eventType, {
      detail: {custom: true},
      bubbles: true,
      composed: true,
    }));
    this.nextStep();
  }

  placeElement(targetEl, el, offset) {
    offset = offset || 0;
    const mh = getDims(el).height;
    const coords = getCoords(targetEl);
    let top = coords.top - mh + offset;
    if (top < 0) {
      const eh = getDims(targetEl).height;
      top = coords.top + eh - offset;
    }
    el.style.top = top + 'px';
    el.style.left = coords.left + 'px';
  }

  nextStep() {
    const step = this.steps[this.stepIdx++];
    window.sessionStorage['tutorialStep'] = this.stepIdx;
    if (!this.showStep(step)) {
      this.tutorialFinished();
    }
  }

  tutorialFinished() {
    delete window.sessionStorage['tutorial'];
  }
}

class TutorialRecorder extends Tutorial {
  build() {
    this.tutorialRecorder = document.createElement('div');
    document.body.appendChild(this.tutorialRecorder);
    this.buildToolbar();
    this.buildMenu();
  }

  buildMenu() {
    this.menuDiv = document.createElement('div');
    this.menuDiv.style.display = 'none';
    this.menuDiv.style.position = 'absolute';
    this.menuDiv.id = 'tutorial-menu';

    const handlers = [
      ['Show text', this.addText],
      ['Add timeout', this.addTimeout],
      ['Dispatch event', this.addJSEvent],
    ];
    const ul = document.createElement('ul');
    this.menuDiv.appendChild(ul);

    for (const h of handlers) {
      const li = document.createElement('li');
      li.textContent = h[0];
      li.style.cursor = 'pointer';
      li.addEventListener('click', ((handler) => () => {
        handler.call(this, this.currentElement);
        this.nextStep();
      })(h[1]));
      ul.appendChild(li);
    }

    this.tutorialRecorder.appendChild(this.menuDiv);
  }

  buildToolbar() {
    this.toolbar = document.createElement('div');
    this.toolbar.id = 'tutorial-toolbar';
    this.tutorialRecorder.appendChild(this.toolbar);

    const playBtn = document.createElement('button');
    playBtn.className = 'btn btn-primary';
    playBtn.textContent = 'Play';
    playBtn.addEventListener('click', (event) => {
      event.stopPropagation();
      event.preventDefault();
      this.unregisterHandlers();
      this.stepIdx = 0;
      this.nextStep();
    });
    this.toolbar.appendChild(playBtn);

    const exportBtn = document.createElement('button');
    exportBtn.className = 'btn btn-primary';
    exportBtn.textContent = 'Export';
    exportBtn.addEventListener('click', (event) => {
      event.stopPropagation();
      event.preventDefault();
      const steps = this.serializeSteps();
      download('tutorial.json', steps);
    });
    this.toolbar.appendChild(exportBtn);
  }

  addText(el) {
    const text = prompt('Text to show');
    this.steps.push({
      type: 'text',
      target: el,
      text,
    });
  }

  addTimeout(el) {
    let time = undefined;
    let sec;
    do {
      if (time === NaN) {
        sec = prompt('Invalid float\n.Enter Seconds to wait');
      } else {
        sec = prompt('Enter Seconds to wait');
      }
      time = parseFloat(sec);
    } while (time === NaN);
    this.steps.push({
      type: 'sleep',
      target: el,
      time,
    });
  }

  addJSEvent(el) {
    const eventType = prompt('Event type (e.g. click)');
    this.steps.push({
      type: 'event',
      target: el,
      eventType,
    });
  }

  showMenu(el) {
    this.menuDiv.style.display = 'block';
    this.placeElement(el, this.menuDiv, 1);
  }

  hideMenu() {
    this.menuDiv.style.display = 'none';
  }

  onMouseOver(event) {
    const el = event.target;
    if (isDescendant(this.tutorialRecorder, el)) {
      console.log('Part of recorder. Cancel');
      event.stopPropagation();
      event.preventDefault();
    } else {
      this.highlight(el);
    }
  }

  registerHandlers() {
    this.addEventListener(
        window, 'mouseover', this.onMouseOver.bind(this), false);
    this.handlerRegistered = true;
  }

  unregisterHandlers() {
    this.removeListeners(window, 'mouseover');
    this.handlerRegistered = false;
  }

  start() {
    super.start();
    this.build();
    this.registerHandlers();
  }

  highlight(el) {
    const r = super.highlight(el);
    if (r) {
      this.hideMenu();
    }
    return r;
  }

  onClick(event) {
    if (isDescendant(this.tutorialRecorder, event.target)) {
      return;
    }
    super.onClick(event);
    if (this.handlerRegistered) {
      this.showMenu(event.target);
    }
  }

  tutorialFinished() {
    super.tutorialFinished();
    this.registerHandlers();
  }
}

class TutorialPlayer extends Tutorial {
  constructor(recordFilename) {
    super();
    if (recordFilename && recordFilename.endsWith('.json')) {
      const parts = recordFilename.replace('\\', '/').split('/');
      recordFilename = parts[parts.length - 1];
      this.tutorialName = recordFilename;
      this.stepsPromise =
          fetch(`/static/tutorial/${recordFilename}`).then((r) => {
            if (!r.ok) {
              throw new Error('Couldn\'t fetch tutorial');
            }
            return r.json();
          });
    } else if (window.localStorage['tutorial']) {
      this.stepsPromise =
          Promise.resolve(window.localStorage['tutorial']).then((r) => {
            return JSON.parse(r);
          });
    } else {
      this.stepsPromise = Promise.reject(new Error('No tutorial provided'));
    }
  }

  start() {
    super.start();
    this.stepsPromise
        .then((steps) => {
          window.localStorage['tutorial'] = JSON.stringify(steps);
          this.unserializeSteps(steps);
          this.nextStep();
        })
        .catch((err) => {
          console.log(err);
          this.unregisterHandlers();
        });
  }

  tutorialFinished() {
    super.tutorialFinished();
    this.stop();
  }
}


const tutorial = /\btutorial=(.+\.json)($|&)/.exec(window.location.search);
if (tutorial) {
  if (tutorial[1] === 'RECORD') {
    const recorder = new TutorialRecorder();
    recorder.start();
  } else {
    const player = new TutorialPlayer(tutorial && tutorial[1]);
    player.start();
  }
}
