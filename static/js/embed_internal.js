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
import {File} from './lib/File.js';
import {Editor} from './lib/Editor.js';
const MAIN_CONTAINER_ID = 'main_container';
const EMBED_FILE_PATH_ID = 'embed_file_path';

/*
Curretly, loading JSquery directly.
function $(id) {
  return document.getElementById(id);
}
function $$(selector, element) {
  return (element || document).querySelectorAll(selector);
}
*/
function getDims(elem) {
  const box = elem[0].getBoundingClientRect();
  return {width: box.width, height: box.height + 5};
}
function sendDims() {
  const sourceFrameId = window.location.hash.slice(1);
  const dims = getDims($('#' + MAIN_CONTAINER_ID));
  window.parent.postMessage(
      {
        type: 'resize',
        source: sourceFrameId,
        payload: dims,
      },
      '*');
}
function receiveMessage(event) {
  if (event.origin !== 'http://example.org:8080') return;
  // ...
}
window.addEventListener('message', receiveMessage, false);
require(['vs/editor/editor.main'], () => {
  const editor = new Editor('editor', false);
  const byFilePath = 'Modules/socketmodule.c';
  const sectionId = EMBED_SETTINGS['section_id'];
  const filesData = EMBED_SETTINGS['entry_data'];

  let startLine = EMBED_SETTINGS['startLine'];
  let endLine = EMBED_SETTINGS['endLine'];
  let filePath = null;

  // let all_comments = [];
  let targetFileData = null;
  filesData.some((fileData) => {
    if (sectionId >= 0) {
      let targetComment = null;
      // Filter by section id.
      fileData.comments.some((comment) => {
        if (comment.id === sectionId) {
          targetComment = comment;
          return true;
        }
        return false;
      });
      if (targetComment === null) return false;
      startLine = targetComment.row_from + 1;
      endLine = targetComment.row_to + 1;
      if (targetComment.row_to === null) {
        // Make up for undefined ranges (old format).
        endLine = startLine + 50;
        startLine = startLine - 50;
        if (startLine < 0) startLine = 0;
      }
    } else if (fileData.file_path !== byFilePath) {
      return false;
    }

    targetFileData = fileData;
    return true;
  });

  let targetFile = null;
  if (targetFileData) {
    targetFile = new File(
        null, targetFileData.file_name, targetFileData.file_hash, null);
    // Overwrite the target file's custom content.
    targetFile.customContent = targetFileData;
    // Drop all comments for now...
    targetFile.comments = [];
    // all_comments = all_comments.concat(target_file.comments);
    filePath = targetFileData.file_path;
  }

  /*
  all_comments.sort(function(a, b) {
    return a.sort_pos - b.sort_pos;
  });
  */
  if (targetFile) {
    const editorSettings = window.EDITOR_SETTINGS;
    if (editorSettings) {
      $('#' + EMBED_FILE_PATH_ID).text('./' + filePath);
      const fileUrl = (
        editorSettings.file_url + filePath);
      $('#' + EMBED_FILE_PATH_ID).attr('href', fileUrl);
    }

    editor.displayFile(targetFile, true).then(() => {
      editor.showOnlyRange(startLine, endLine);
      editor.collapseAllIrrelevantLines();
      editor.fitEditorHeightToContent();
      sendDims();
    });
  }
});
