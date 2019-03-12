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


const ui = new UI();
let editor = null;
let fileTree = null;
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
  $('#id').bind('input', function() {
    const currentUrl = this.value;
    let customRepoUrl = false;

    $('#repo_url').val('');
    $('#commit_hash').val('');
    $('#id_type').text('');

    $('#unknown_input_msg').hide();
    $('#repository_information').hide();
    $('#commit_information').hide();
    $('#id_type').hide();

    const cgitRegex = /[^\/]+.git\/commit\/?.*id=(.+)$/;
    let matches = cgitRegex.exec(currentUrl);
    if (matches) {
      $('#id_type').text('Cgit');
      $('#commit_hash').val(matches[1]);
      customRepoUrl = true;
    }

    const gitwebRegex = /\?p=[^\/]+.git;a=commit;h=(.+)$/;
    matches = gitwebRegex.exec(currentUrl);
    if (matches) {
      $('#id_type').text('Gitweb');
      $('#commit_hash').val(matches[1]);
      customRepoUrl = true;
    }

    const gitlesRegex = /\/\+\/(.+)$/;
    matches = gitlesRegex.exec(currentUrl);
    if (matches) {
      $('#id_type').text('Gitles');
      $('#commit_hash').val(matches[1]);
      customRepoUrl = true;
    }

    const gitRepoRegex = /[^\/]+.git$/;
    matches = gitRepoRegex.exec(currentUrl);
    if (!customRepoUrl && matches) {
      $('#id_type').text('GIT repo');
      $('#repo_url').val(this.value);
      $('#commit_information').show();
      customRepoUrl = true;
    }

    const gitRepoHashRegex = /^(.*[^\/]+.git)[@#]([a-fA-F0-9]{7,})$/;
    matches = gitRepoHashRegex.exec(currentUrl);
    if (!customRepoUrl && matches) {
      $('#id_type').text('Pinned GIT repo');
      $('#repo_url').val(matches[1]);
      $('#commit_hash').val(matches[2]);
      $('#repository_information').show();
      $('#commit_information').show();
    }

    if (this.value.toLowerCase().startsWith('cve-')) {
      $('#id_type').text('CVE-ID');
    }

    if ($('#id_type').text().length === 0 &&
        this.value.toLowerCase().includes('github.com/')) {
      $('#id_type').text('Github Commit');
    }

    if (customRepoUrl) {
      $('#repository_information').show();
      $('#commit_information').show();
    }

    $('#id_type').removeClass('has-success has-error');
    $('#id_type').addClass('has-success');
    if (this.value.length > 0) $('#id_type').show();

    if ($('#id_type').text().length === 0) {
      $('#id_type').text('?');
      $('#id_type').removeClass('has-success');
      $('#id_type').addClass('has-error');
      $('#id_type').show();
      $('#unknown_input_msg').show();
    }
  });


  $('#fetchGitCommitBtn').bind('click', function() {
    const commitLink = $('#id').val();
    // Forward to the correct main page.
    const repoUrl = $('#repo_url').val();
    const commitHash = $('#commit_hash').val();

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
    $('#id').val(useUrl);
    if (this.dataset.url) $('#id').val(this.dataset.url);
    $('#id').trigger('input');

    if (this.dataset.hash) $('#commit_hash').val(this.dataset.hash);

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
        const win = window.open($(this).data('href'), '_blank');
        win.focus();
      }
    });
  }

  // Enable all tooltips in the document.
  $(document).ready(function() {
    initClickableElements();
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
          // TODO: Refactor .html usage and AJAX handling to use JSON instead.
          $('#vulnEntries').html(response);
          initClickableElements();
        },
      });
    }, 500);
  });
});

function fetchGitCommitLink(commitLink, commitHash, repoUrl) {
  if (!$('#editor').length) return;

  /*
  // Skip the file tree data for the view only mode.
  if (!constants.EDIT_MODE_ACTIVE) {
    initEditor(null).then(editor => editor.restoreFileBackendData());
    return;
  }
  */

  // Fetch the file tree data and initialize the editor after that.
  $.getJSON(
      '/api/git',
      {commit_link: commitLink, commit_hash: commitHash, repo_url: repoUrl},
      function(jsonContent) {
        initEditor(jsonContent).then((editor) => editor.loadFirstPatchFile());
      })
      .fail(function(jqXHR) {
        ui.showError(
            'Status (' + jqXHR.status +
            ') when fetching /api/git (see console)!');
        console.log(jqXHR.responseText);
      });
}

const editorSettings = window.EDITOR_SETTINGS;
if (editorSettings) {
  const commitLink = editorSettings.commit_link;
  const commitHash = editorSettings.commit_hash;
  const repoUrl = editorSettings.repo_url;
  // Default commit link.
  fetchGitCommitLink(commitLink, commitHash, repoUrl);
} else {
  console.log('[-] No editor settings found to proceed.');
}
