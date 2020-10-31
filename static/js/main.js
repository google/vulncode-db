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


import {Editor} from './lib/Editor.js';
import {FileTree} from './lib/FileTree.js';
import {UI} from './lib/UI.js';
import {File} from './lib/File.js';

const ui = new UI();
let editor = null;
let fileTree = null;
const commitLinkID = '#commits-0-commit_link';
/*
  We use two main elements:
    1) A file tree on the left side
    2) The main area on the right side.
*/
function initEditor(jsonContent) {
  return new Promise((resolve) => {
    require(['vs/editor/editor.main'], () => {
      resolve(_initEditorInternal(jsonContent));
    });
  });
}

/**
 *
 * @param {String} jsonContent
 * @return {Promise<any>}
 * @private
 */
function _initEditorInternal(jsonContent) {
  if (!editor) {
    editor = new Editor('editor');
  } else {
    editor.cleanup();
  }
  // Completely destroy any previously used file tree.
  if (fileTree) fileTree.destroy();
  if (jsonContent) {
    fileTree = new FileTree(editor, jsonContent);
    // Link main with the file tree navigation.
    editor.registerFileTree(fileTree);
  }
  editor.registerUI(ui);

  $('#reset_changes_btn').bind('click', () => editor.resetState());
  $('#save_changes_btn').bind('click', () => editor.saveState());
  $('#delete_entry').bind('click', () => editor.deleteEntry());

  return new Promise((resolve) => {
    if (fileTree) {
      // Wait for the file tree to finish loading.
      fileTree.loaded_promise.then(() => {
        resolve(editor);
      });
    } else {
      resolve(editor);
    }
  });
}

$(function() {
  $(commitLinkID).bind('input', function() {
    const currentUrl = this.value;
    let customRepoUrl = false;

    const repoNameID = '#commits-0-repo_name';
    const repoUrlID = '#commits-0-repo_url';
    const repoCommitHashID = '#commits-0-commit_hash';

    $(repoUrlID).val('');
    $(repoNameID).val('');
    $(repoCommitHashID).val('');
    $('#id_type').text('');

    $('#unknown_input_msg').hide();
    // $('#repository_information').hide();
    $('#commit_information').hide();
    $('#id_type').hide();

    const cgitRegex = /[^\/]+.git\/commit\/?.*id=(.+)$/;
    let matches = cgitRegex.exec(currentUrl);
    if (matches) {
      $('#id_type').text('Cgit');
      $(repoCommitHashID).val(matches[1]);
      customRepoUrl = true;
    }

    const gitwebRegex = /\?p=[^\/]+.git;a=commit;h=(.+)$/;
    matches = gitwebRegex.exec(currentUrl);
    if (matches) {
      $('#id_type').text('Gitweb');
      $(repoCommitHashID).val(matches[1]);
      customRepoUrl = true;
    }

    const gitlesRegex = /\/\+\/(.+)$/;
    matches = gitlesRegex.exec(currentUrl);
    if (matches) {
      $('#id_type').text('Gitles');
      $(repoCommitHashID).val(matches[1]);
      customRepoUrl = true;
    }

    const gitRepoRegex = /[^\/]+.git$/;
    matches = gitRepoRegex.exec(currentUrl);
    if (!customRepoUrl && matches) {
      $('#id_type').text('GIT repo');
      $(repoUrlID).val(this.value);
      $('#commit_information').show();
      customRepoUrl = true;
    }

    const gitRepoHashRegex = /^(.*[^\/]+.git)[@#]([a-fA-F0-9]{7,})$/;
    matches = gitRepoHashRegex.exec(currentUrl);
    if (!customRepoUrl && matches) {
      $('#id_type').text('Pinned GIT repo');
      $(repoUrlID).val(matches[1]);
      $(repoCommitHashID).val(matches[2]);
      // $('#repository_information').show();
      $('#commit_information').show();
    }

    const githubRegex = /^.*github.com\/([^\/]+)\/([^\/]+)\/commit\/([^\/]+)\/?$/;
    matches = githubRegex.exec(currentUrl);
    if ($('#id_type').text().length === 0 && matches) {
      // $(repoUrlID).val(matches[1]);
      // $(repoNameID).val(matches[2]);
      // $(repoCommitHashID).val(matches[3]);
      $('#id_type').text('GitHub commit');
    }

    if (customRepoUrl) {
      $('#repository_information').show();
      $('#commit_information').show();
    }

    $('#id_type').removeClass('has-success has-error');
    $('#id_type').addClass('has-success');
    if (this.value.length > 0) $('#id_type').show();

    if ($('#id_type').text().length === 0 && currentUrl.length > 0) {
      $('#id_type').text('?');
      $('#id_type').removeClass('has-success');
      $('#id_type').addClass('has-error');
      $('#id_type').show();
      $('#unknown_input_msg').show();
    }
  });


  $('#fetchGitCommitBtn').bind('click', function() {
    const commitLink = $(commitLinkID).val();
    // Forward to the correct main page.
    const repoUrl = $(repoUrlID).val();
    const commitHash = $(repoCommitHashID).val();

    const postData = [];
    postData.push(['csrf_token', CSRF_TOKEN]);
    postData.push(['id', commitLink]);
    if (repoUrl) {
      // preserve original commit link
      postData.push(['commit_link', commitLink]);
      postData.push(['repo_url', repoUrl]);
    }
    if (commitHash) postData.push(['commit_hash', commitHash]);
    // Send POST request to /vuln endpoint.
    const form = $('<form>', {'action': '/vuln', 'method': 'POST'});
    postData.forEach((keyVal) => {
      form.append(
          $('<input/>', {type: 'hidden', name: keyVal[0], value: keyVal[1]}));
    });
    form.appendTo(document.body).submit();

    return false;
  });

  $('#commitLinkSelection a').bind('click', function() {
    const useUrl = this.innerHTML;
    $(commitLinkID).val(useUrl);
    if (this.dataset.url) $(commitLinkID).val(this.dataset.url);
    $(commitLinkID).trigger('input');

    if (this.dataset.hash) $(repoCommitHashID).val(this.dataset.hash);

    return false;
  });

  $('input[name=\'jstree_filter\']').change(function() {
    const newFilter = this.id.replace('jstree_filter_', '');
    fileTree.applyFilter(newFilter);
  });
  // Set the "relevant" filter by default.
  $('#jstree_filter_relevant').prop('checked', true);


  function initClickableElements() {
    $('[data-toggle="tooltip"]').tooltip();
    $('.clickable-row .link').click(function(e) {
      e.stopPropagation();
    });
    $('.clickable-row').click(function() {
      if (!getSelection().toString()) {
        const win = window.open($(this).data('href'), '_top');
        win.focus();
      }
    });
  }

  // Enable all tooltips in the document.
  $(document).ready(function() {
    initClickableElements();
    // Convert all markdown comments.
    $('.markdown_comment').each(function(index) {
      const comment = $(this).text();
      const markdown_comment = UI.toMarkdown(comment);
      $(this).html(markdown_comment);
    });
  });

  let searchTimeout;
  $('#searchKeyword').on('input', function() {
    const value = $(this).val();
    clearTimeout(searchTimeout);

    searchTimeout = setTimeout(function() {
      $.ajax({
        url: '/list_entries',
        type: 'get',
        data: {
          keyword: value,
        },
        success: (response) => {
          const filtered_response = response.replace(/list_entries/g, '');
          // TODO: Refactor .html usage and AJAX handling to use JSON instead.
          $('#vulnEntries').html(filtered_response);
          initClickableElements();
        },
      });
    }, 500);
  });
});

function fetchGitCommitLink(treeUrl) {
  if (!$('#editor').length) return;

  // Fetch the file tree data and initialize the editor after that.
  $.getJSON(
      treeUrl,
      function(jsonContent) {
        initEditor(jsonContent);
      })
      .fail(function(jqXHR) {
        ui.showError(
            'Status (' + jqXHR.status +
        ') when fetching ' + treeUrl + ' (see console)!');
        console.log(jqXHR.responseText);
      });
}

const editorSettings = window.EDITOR_SETTINGS;
if (editorSettings) {
  const treeUrl = editorSettings.tree_url;
  // Default commit link.
  fetchGitCommitLink(treeUrl);

  // TODO: Refcator this section (unify with embed_internal.js).
  // Check the simplified view editors and load their files + content.
  require(['vs/editor/editor.main'], () => {
    const fileCache = {};

    $('.mutli-editor').each(function(index) {
      const targetElement = $(this);
      const targetEditorId = targetElement.attr('id');
      const targetData = targetElement.data();

      if (!editorSettings.hasOwnProperty('custom_data')) {
        return;
      }

      const sectionId = targetData.section_id;
      let startLine = targetData.row_from + 1;
      let endLine = targetData.row_to + 1;
      // TODO: Refactor this whole area.
      if (targetData.row_to === 'None') {
        // Make up for undefined ranges (old format).
        endLine = startLine + 5;
        startLine = startLine - 5;
        if (startLine < 0) startLine = 0;
      }

      if (startLine === endLine) {
        endLine += 1;
      }

      const filePath = targetData.path;
      const fileHash = targetData.hash;

      const customDataAll = editorSettings.custom_data;
      let targetFileData = null;
      customDataAll.some((customData) => {
        if (sectionId >= 0) {
          let targetComment = null;
          // Filter by section id.
          customData.comments.some((comment) => {
            if (comment.id === sectionId) {
              targetComment = comment;
              return true;
            }
            return false;
          });
          if (targetComment === null) return false;
        }
        targetFileData = customData;
        return true;
      });

      const targetEditor = new Editor(targetEditorId, false);

      const targetFile = new File(null, filePath, fileHash, null);
      // Make sure to share the same file cache to avoid redundant requests.
      if (filePath in fileCache) {
        targetFile.content = fileCache[filePath].content;
      } else {
        fileCache[filePath] = targetFile;
      }

      // Overwrite the target file's custom content.
      targetFile.customContent = targetFileData;
      targetFile.comments = [];

      targetEditor.displayFile(targetFile, true).then(() => {
        targetEditor.showOnlyRange(startLine, endLine);
        targetEditor.collapseAllIrrelevantLines();
        targetEditor.fitEditorHeightToContent();
      });
    });
  });
} else {
  console.log('[-] No editor settings found to proceed.');
}

$(function() {
  $('div[data-toggle=fieldset]').each(function() {
    const $this = $(this);

    // Allow dynamically adding/removing form fields as per
    // https://gist.github.com/jb-l/466eb6a96e39bf2d92500fe8d6909b14#file-test_fieldlist-py
    // Note: This requires at least one (hidden) template input to exist.
    $this.find('button[data-toggle=fieldset-add-row]').click(function() {
      const target = $($(this).data('target'));
      const oldrow = target.find('[data-toggle=fieldset-entry]:last');
      const row = oldrow.clone(true, true);
      const elem_id = row.find(':input')[0].id;
      const elem_num = parseInt(elem_id.match(/-(-?\d{1,4})(?!.*\d)/m)[1]) + 1;
      row.children(':input').each(function() {
        const id = $(this).attr('id').replace((elem_num - 1), elem_num);
        $(this).attr('name', id).attr('id', id).val('').removeAttr('checked');
      });
      row.children('label').each(function() {
        const id = $(this).attr('for').replace((elem_num - 1), elem_num);
        $(this).attr('for', id);
      });
      row.show();
      oldrow.after(row);
    });
    $this.find('button[data-toggle=fieldset-remove-row]').click(function() {
      if ($this.find('[data-toggle=fieldset-entry]').length > 1) {
        const thisRow = $(this).closest('[data-toggle=fieldset-entry]');
        thisRow.remove();
      }
    });
  });
});
