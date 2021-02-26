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

import {ZoneViewWidget} from './ZoneViewWidget.js';
import {UI} from './UI.js';


/**
 * Renders a comment widget inside the editor. Based on the CommentThreadWidget
 * of VS code.
 */
export class CommentWidget extends ZoneViewWidget {
  /**
   * @param {!FileComment} comment
   * @param {!monaco.editor.ICodeEditor|monaco.editor.IDiffEditor} editor
   * @param {boolean} isDiffMode
   * @param {boolean} isEditMode
   */
  constructor(comment, editor, isDiffMode, isEditMode) {
    super(
      isDiffMode ? editor.getOriginalEditor() : editor,
      isDiffMode ? editor.getModifiedEditor() : editor,
      {glyphClassName: 'fa fa-comment'});
    this._comment = comment;
    this._isEditMode = isEditMode;
    this._isDiffMode = isDiffMode;
    this._onRemove = new monaco.Emitter();
    this.onRemove = this._onRemove.event;
    this._disposables.push(this._onRemove);
  }

  /**
   * Create the widget content
   * @param {!HTMLElement} container
   */
  _fillContainer(container) {
    this.setCssClass('comment-widget');
    this.setCssClass('comment_widget_wrapper');
    this._headElement = document.createElement('div');
    this._headElement.className = 'head';
    this._bodyElement = document.createElement('div');
    this._bodyElement.className = 'body comment_widget shadow-textarea';
    container.appendChild(this._headElement);
    container.appendChild(this._bodyElement);

    this._fillHead(this._headElement);
    this._fillBody(this._bodyElement);
  }

  /**
   * Creates a header with a label. Not used at the moment.
   * @param {!HTMLElement} container
   */
  _fillHead(container) {
    const titleElement = document.createElement('div');
    titleElement.className = 'comment-title';
    container.appendChild(titleElement);

    this._headingLabel = document.createElement('span');
    if (this._comment.creator) {
      const a = document.createElement('a');
      a.href = this._comment.creator.profile_link;
      a.textContent = '@' + this._comment.creator.name;
      this._headingLabel.appendChild(a);
    } else if (window.CURRENT_USER) {
      const a = document.createElement('a');
      a.href = window.CURRENT_USER.profile_link;
      a.textContent = '@' + window.CURRENT_USER.name;
      this._headingLabel.appendChild(a);
    } else {
      this._headingLabel.textContent = '<unknown creator>';
    }
    if (this._comment.revision) {
      const txt = document.createTextNode(' (rev ' + this._comment.revision + ')');
      this._headingLabel.appendChild(txt);
    }
    titleElement.appendChild(this._headingLabel);
  }

  /**
   * Creates the main part of the widget
   * @param {!HTMLElement} container
   */
  _fillBody(container) {
    const commentArea = container.appendChild(document.createElement('div'));
    commentArea.innerHTML = UI.toMarkdown(this._comment.text);

    if (this._isEditMode) {
      const textarea =
        container.appendChild(document.createElement('textarea'));
      textarea.value = this._comment.text;
      textarea.className = 'form-control z-depth-1';
      textarea.style.display = this._comment.text ? 'none' : null;
      if (!this._comment.text) {
        // focus the textarea after 1/2 seconds
        window.setTimeout(() => {
          textarea.focus();
        }, 500);
      }
      /**
       *
       * @param {!HTMLElement} el
       */
      function resizeTextarea(el) {
        if (el.scrollHeight === el.clientHeight) {
          // No need for resizing
          return;
        }
        const oldHeight = el.style.height;
        const newHeight = Math.ceil(el.scrollHeight + 5) + 'px';
        if (oldHeight !== newHeight) {
          el.style.height = newHeight;
          this._refresh();
        }
      }
      textarea.addEventListener('input', (e) => {
        resizeTextarea.call(this, e.target);
      });
      textarea.addEventListener('change', (e) => {
        this._comment.text = e.target.value;
      });

      const remove = container.appendChild(document.createElement('button'));
      remove.type = 'button';
      remove.className = 'btn btn-danger';
      remove.textContent = 'Remove';
      remove.addEventListener('click', (e) => {
        e.preventDefault();
        this._onRemove.fire(this._comment);
      });

      const render = container.appendChild(document.createElement('button'));
      render.type = 'button';
      render.className = 'btn btn-primary';
      render.textContent = 'Render';
      render.style.display = this._comment.text ? 'none' : null;
      render.addEventListener('click', (e) => {
        e.preventDefault();
        textarea.style.display = 'none';
        render.style.display = 'none';
        edit.style.display = null;
        commentArea.style.display = null;
        commentArea.innerHTML = UI.toMarkdown(textarea.value);
        this._refresh();
      });

      const edit = container.appendChild(document.createElement('button'));
      edit.type = 'button';
      edit.className = 'btn btn-warning';
      edit.textContent = 'Edit';
      edit.style.display = this._comment.text ? null : 'none';
      edit.addEventListener('click', (e) => {
        e.preventDefault();
        edit.style.display = 'none';
        commentArea.style.display = 'none';
        textarea.style.display = null;
        render.style.display = null;
        // _refresh called by resizeTextArea
        resizeTextarea.call(this, textarea);
      });
    }
  }

  /**
   * Refresh the overlay and view zone sizes.
   */
  _refresh() {
    const dimensions = {
      width: this._bodyElement.clientWidth,
      height: this._bodyElement.clientHeight,
    };
    const headHeight =
      Math.ceil(this.overlayEditor.getOption(monaco.editor.EditorOption.lineHeight) * 1.2);
    const lineHeight = this.overlayEditor.getOption(monaco.editor.EditorOption.lineHeight);
    const arrowHeight = Math.round(lineHeight / 3);
    const frameThickness = Math.round(lineHeight / 9) * 2;

    const computedLinesNumber = Math.ceil(
        (headHeight + dimensions.height + arrowHeight + frameThickness) /
      lineHeight);
    this._relayout(computedLinesNumber);
  }

  /**
   * Show the widget at the given position/range
   * @param {!monaco.Range|monaco.Position} rangeOrPos
   * @param {number} heightInLines
   */
  show(rangeOrPos, heightInLines) {
    super.show(rangeOrPos, heightInLines);
    this._refresh();
  }
}
