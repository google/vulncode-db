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

// import {AnnotateInlineToolbar} from './InlineToolbar.js';
import {CommentWidget} from './CommentWidget.js';
import * as constants from './Constants.js';
import {File} from './File.js';
import {FileComment} from './FileComment.js';
import {FileMarker} from './FileMarker.js';


function defaultQueryParameters() {
  const result = {};
  const editorSettings = window.EDITOR_SETTINGS;
  if (editorSettings) {
    result.id = editorSettings.id;
  }
  return result;
}

// General Monaco editor settings.
const MONACO_EDITOR_BASE_SETTINGS = {
  readOnly: true,
  // TODO: use neutral theme? (old theme: vs-dark)
  theme: 'vs-dark',
  glyphMargin: true,
  fontSize: '12px',
  scrollBeyondLastLine: false,
  // Experimental settings:
  // showFoldingControls: "always"
  // smoothScrolling: true
};
// Settings used in the monaco diff editor.
const MONACO_DIFF_EDITOR_SETTINGS = {
  renderSideBySide: false,
  minimap: {
    enabled: true,
  },
};
/**
 * The main Editor class responsible for any displayed code.
 * This class can optionally be connected to a FileTree class and a UI
 * class to display notifications and other meta data.
 */
class Editor {
  /**
   * @param {String} editorDivId target HTML element id of the editor area.
   * @param {Boolean} displayPatches whether to display patch data by default.
   */
  constructor(editorDivId, displayPatches = true) {
    this._editor_container = document.getElementById(editorDivId);
    this._display_patch_data = displayPatches;
    this._createEditor();
    // Can link to FileTree.all_files entries or be autonomously managed.
    this._known_files = {};
    this._currently_open_file = null;
    this._file_tree = null;
    this._ui = null;
    this._selected_marker = null;
    this._hidden_ranges = [];
    this._view_range = {'start': 0, 'end': 9999999};
    this._num_collapsable_ranges = 0;

    // Install an auto resize listener for the editor.
    window.addEventListener('resize', this.updateDimensions.bind(this));
  }
  /**
   * Returns the currently selected area.
   * @return {{row_from: number, row_to: number}}
   * @private
   */
  _getSelection() {
    const selection = {'startRow': 0, 'endRow': 0};
    const sel = this._editor.getSelection();

    const startRow = sel.startLineNumber - 1;
    selection.startRow = startRow;
    const endRow = sel.endLineNumber - 1;
    selection.endRow = endRow;
    if (this._editor.getEditorType() === monaco.editor.EditorType.IDiffEditor) {
      selection.startRow =
        this._editor.getDiffLineInformationForModified(startRow)
            .equivalentLineNumber;
      selection.endRow = this._editor.getDiffLineInformationForModified(endRow)
          .equivalentLineNumber;
    }
    return selection;
  }
  /**
   * Create a new editor based on _display_patch_data.
   * @param allowDiffMode {Boolean} Whether to allow the editor's diff mode.
   * @private
   */
  _createEditor(allowDiffMode = true) {
    // Create the editor based on the current display mode
    if (this._display_patch_data && allowDiffMode) {
      this._diffEditor();
    } else {
      this._normalEditor();
    }
    // Register additional handlers in edit mode
    if (constants.EDIT_MODE_ACTIVE) {
      function addComment() {
        const selection = this._getSelection();
        this.createComment(selection.startRow, selection.endRow, '');
      }
      function toggleVulnerable() {
        const selection = this._getSelection();
        this.toggleMarkerSelection(
            selection.startRow, selection.endRow,
            constants.VULNERABLE_MARKER_CLASS);
      }
      function toggleIrrelevant() {
        const selection = this._getSelection();
        this.toggleMarkerSelection(
            selection.startRow, selection.endRow,
            constants.IRRELEVANT_MARKER_CLASS);
      }
      this._editor.addAction({
        id: 'add_comment',
        contextMenuGroupId: '9_cutcopypaste',
        // keybindings: [monaco.KeyCode.KEY_C],
        label: 'Add comment',
        run: addComment.bind(this),
      });
      this._editor.addAction({
        id: 'toggle_vulnerable',
        contextMenuGroupId: '9_cutcopypaste',
        // keybindings: [monaco.KeyCode.KEY_V],
        label: '(Un)Mark as vulnerable',
        run: toggleVulnerable.bind(this),
      });
      this._editor.addAction({
        id: 'toggle_irrelevant',
        contextMenuGroupId: '9_cutcopypaste',
        // keybindings: [monaco.KeyCode.KEY_I],
        label: '(Un)Mark as irrelevant',
        run: toggleIrrelevant.bind(this),
      });
      function _keydownHandler(e) {
        // Skip any events inside a textarea widget.
        if (e.target.className.includes('form-control')) return;
        // Ignore any ctrl + [?] combinations like copy & paste.
        if (e.ctrlKey) return;
        if (e.key === 'v') toggleVulnerable.call(this);
        if (e.key === 'i') toggleIrrelevant.call(this);
        if (e.key === 'c') addComment.call(this);
        e.preventDefault();
      }
      const editorDiv = $(this._editor_container);
      editorDiv.keydown((e) => {
        _keydownHandler.call(this, e);
      });
    }
  }


  /**
   * Fetches, defines and sets a custom Monaco Editor theme.
   * @param {string} themeName
   * @private
   */
  loadCustomMonacoTheme(themeName) {
    if (themeName === 'vs-dark' || themeName === 'vs-bright') {
      monaco.editor.setTheme(themeName);
      return;
    }
    fetch('/static/monaco/themes/' + themeName + '.json')
        .then((data) => data.json())
        .then((data) => {
          monaco.editor.defineTheme(themeName, data);
          monaco.editor.setTheme(themeName);
        })
        .catch((e) => {
          console.log('Can\'t fetch theme: ' + themeName, e);
        });
  }
  /**
   * Create non-diff editor
   * @param {?string} content
   * @param {?string} fileName
   */
  _normalEditor(content, fileName) {
    this._editor = monaco.editor.create(
        this._editor_container, MONACO_EDITOR_BASE_SETTINGS);
    if (!content) {
      content = 'Editor loaded\nsuccessfully.\n';
    }
    // this.loadCustomMonacoTheme('darcula');
    let uri = null;
    if (fileName) {
      uri = monaco.Uri.file(fileName);
    }
    const model = monaco.editor.createModel(content, null, uri);
    this._editor.setModel(model);
  }
  /**
   * Hides a given range and updates the editor to reflect the change.
   * @param {int} startLine
   * @param {int} endLine
   */
  addHiddenRange(startLine, endLine) {
    const range = new monaco.Range(startLine, 0, endLine, 0);
    this._hidden_ranges.push(range);
    this._editor.setHiddenAreas(this._hidden_ranges);
  }
  /**
   * Displays code inside a previously hidden range again.
   */
  removeHiddenRange() {
    /*
    let hiddenRanges = this._hidden_ranges;
    hiddenRanges.forEach((range) => {
      if(range.startLineNumber <= anyLineInRange && range.endLineNumber >=
    anyLineInRange) this.removeMarker(marker);
    });
    */
  }

  /**
   * Fit the editor to the current container's width and height.
   */
  updateDimensions() {
    this._editor.layout();
  }
  /**
   * Fits the container and editor height to match the visible content.
   */
  fitEditorHeightToContent() {
    // console.log(this._editor.viewModel.getLineCount());
    // console.log(this._editor.model.getLineCount());
    const scrollHeight = this._editor.getScrollHeight();
    // let layoutInfo = this._editor.getLayoutInfo();

    // The codeLens lines / widgets are not considered in the scrollHeight.
    const configuration = this._editor.getOptions();
    const lineHeight = configuration.get(monaco.editor.EditorOption.lineHeight);
    const paddingOffset = lineHeight * this._num_collapsable_ranges;
    const editorContainerHeight = scrollHeight + paddingOffset;
    $(this._editor_container).height(editorContainerHeight);
    this.updateDimensions();
  }
  /**
   * Adds a by default collapsed hidden range that can be expanded on click.
   * @param {int} startLine
   * @param {int} endLine
   */
  addCollapsableHiddenRange(startLine, endLine) {
    // console.log(start_line, end_line);
    this.addHiddenRange(startLine, endLine);

    const usedLanguage = this._editor.getModel().getModeId();
    const commandId = this._editor.addCommand(0, function() {
      // services available in `ctx`
      console.log('Todo: action missing.');
    }, '');

    monaco.languages.registerCodeLensProvider(usedLanguage, {
      provideCodeLenses: function(model, token) {
        return {
          lenses: [{
            range: {
              startLineNumber: endLine + 1,
              startColumn: 1,
              endLineNumber: endLine + 1,
              endColumn: 1,
            },
            id: 'Foobar',
            command: {id: commandId, title: '[...]'},
          }],
        };
      },
      resolveCodeLens: function(model, codeLens, token) {
        return codeLens;
      },
    });
    this._num_collapsable_ranges++;
    // Update the editor layout accordingly.
    /*
    let collapsableZoneDoms = {};
    let viewZoneId = null;
    this._editor.changeViewZones(function(changeAccessor) {
      let domNode = $('<div>');
      //domNode.style.background = 'lightgreen';
      domNode.text("[...]");
      $(domNode).on('click', (e) => {
        console.log("FOO");
        //alert(1);
      });
      console.log(range.startLineNumber - 1);
      viewZoneId = changeAccessor.addZone({
        afterLineNumber: range.startLineNumber - 1,
        heightInLines: 5,
        domNode: domNode.get(0)
      });
      collapsableZoneDoms[viewZoneId] = domNode;
    });

    this._editor.onMouseDown(function (e) {
      // Forward mouse down events to view zone elements accordingly.
      if(e.target.detail !== null) {
        let currentZoneId = e.target.detail.viewZoneId;
        console.log("ID", currentZoneId);
        if(currentZoneId in collapsableZoneDoms) {
          let target = collapsableZoneDoms[currentZoneId];
          target.click();
        }
        //console.log(collapsableZoneDoms[currentZoneId]);
      }
    });
    */

    /*
    monaco.languages.registerFoldingRangeProvider(used_language, {
      provideFoldingRanges: function(model, context, token) {
        return [
          // region1
          {
            start: 2586,
            end: 2590,
            kind: monaco.languages.FoldingRangeKind.Region
          },
        ];
      }
    });
*/
  }
  /**
   * Hide all lines outside the given range.
   * @param {int} startLine
   * @param {int} endLine
   */
  showOnlyRange(startLine, endLine) {
    const ranges = [];
    if (startLine > 1) ranges.push(new monaco.Range(1, 0, startLine - 1, 0));
    if (endLine > startLine) {
      ranges.push(new monaco.Range(endLine + 1, 0, 999999, 0));
    }

    this._hidden_ranges = ranges;
    this._editor.setHiddenAreas(this._hidden_ranges);

    this._view_range.start = startLine;
    this._view_range.end = endLine;
  }

  /**
   * Collapses all sections with lines that have been marked as irrelevant.
   */
  collapseAllIrrelevantLines() {
    const irrelevantMarkers =
      this._getMarkers(constants.IRRELEVANT_MARKER_CLASS);

    const collapseRanges = [];
    irrelevantMarkers.forEach((marker) => {
      if (marker.class !== constants.IRRELEVANT_MARKER_CLASS) return;
      const startLine = marker.row_from + 1;
      const endLine = marker.row_to + 1;

      // Skip markers outside the current view scope.
      if (endLine <= this._view_range.start ||
        startLine >= this._view_range.end) {
        return;
      }
      collapseRanges.push({'start': startLine, 'end': endLine});
    });
    // Merge ranges before collapsing them.
    for (let i = 0; i < collapseRanges.length; i++) {
      const currentRange = collapseRanges[i];
      if (i + 1 in collapseRanges) {
        const nextRange = collapseRanges[i + 1];
        if (currentRange.end === nextRange.start - 1) {
          nextRange.start = currentRange.start;
          continue;
        }
      }
      this.addCollapsableHiddenRange(currentRange.start, currentRange.end);
    }
  }
  /**
   * Create diff editor
   * @param {?string} original
   * @param {?string} modified
   * @param {?string} fileName
   */
  _diffEditor(original, modified, fileName) {
    this._editor = monaco.editor.createDiffEditor(
        this._editor_container,
        {...MONACO_EDITOR_BASE_SETTINGS, ...MONACO_DIFF_EDITOR_SETTINGS});
    if (!original) {
      original = 'Editor loaded\nsuccessfully.\n';
    }
    if (!modified) {
      modified = 'Editor loaded\nsuccessfully.\n';
    }
    let uri = null;
    if (fileName) {
      uri = monaco.Uri.file(fileName);
    }
    original = monaco.editor.createModel(original, null, uri);
    modified = monaco.editor.createModel(modified, null, uri);
    this._editor.setModel({original, modified});
    this._editor.getModifiedEditor().updateOptions({
      minimap: {
        enabled: true,
      },
    });
    this._diffNavi = monaco.editor.createDiffNavigator(this._editor, {
      followsCaret: true, // resets the navigator state when the user selects
      // something in the editor
      ignoreCharChanges: true, // jump from line to line
    });
  }
  /**
   * Returns the currently shown editor instance.
   * @return {?monaco.editor.ICodeEditor}
   */
  _getEditor() {
    if (!this._editor) {
      return null;
    }
    if (this._editor.getEditorType() === monaco.editor.EditorType.ICodeEditor) {
      return this._editor;
    }
    return this._editor.getModifiedEditor();
  }
  /**
   * Resets editor properties so that new content can be loaded.
   */
  cleanup() {
    // TODO: backup / save state??
    this.updatesHandler();
    this.flushMarkers();
    this.flushComments();
    this._editor.setModel(null);
  }
  /**
   * Called by the UI component on annotation updates.
   * @param {string} annotation
   */
  annotationCallback(annotation) {
    if (!this._selected_marker) return;
    this._selected_marker.annotation = annotation;
  }
  /**
   * Registers the UI object for callbacks.
   * @param {UI} ui
   */
  registerUI(ui) {
    this._ui = ui;
    this._ui.registerEditor(this);
  }
  /**
   * Fetches the current filter settings and applies them to the file tree.
   */
  reloadFileFilter() {
    if (!this._file_tree) return;
    // Filter the displayed tree according to the filter settings.
    const currentFilter = this._ui.getCurrentFilter();
    this._file_tree.applyFilter(currentFilter);
  }
  /**
   * Updates information displayed in the metadata UI section.
   */
  updateUIMetadata() {
    if (!this._ui) return;
    // Propagate all changes into the UI metadata DIV container.
    this._ui.updateMetadata(this.metadata);
  }
  /**
   * Propagates changes to involved objects and the UI.
   */
  updatesHandler() {
    // Propagate all changes into the UI metadata DIV container.
    this.updateUIMetadata();
  }
  /**
   * Registers the file tree object for callbacks.
   * @param {FileTree} fileTree
   */
  registerFileTree(fileTree) {
    this._file_tree = fileTree;
  }
  /**
   * Registers the file tree object's files as the main editor files.
   * @param {Object.<String, File>} allFiles
   */
  initKnownFiles(allFiles) {
    this._known_files = allFiles;
  }
  /**
   * Returns the currently (by mouse) selected marker.
   * @return {*}
   * @private
   */
  _getSelectedMarker() {
    const pos = this._editor.getCursorPosition();
    const currentRow = pos.row;
    const markers = this._getMarkers(constants.VULNERABLE_MARKER_CLASS);
    let selectedMarker = null;
    markers.some((marker) => {
      if (currentRow >= marker.row_from && currentRow <= marker.row_to) {
        selectedMarker = marker;
        return true;
      }
    });
    return selectedMarker;
  }
  /**
   * Selects highlighted areas on click for annotation purposes.
   * purposes.
   * @param {Event} e
   * @private
   */
  _clickHandler(e) {
    // TODO: reconsider value of this functionality.
    return;
    // CHeck if a marker is supposed to be selected.
    const highlightMarkers = this._getMarkers(constants.MARKER_HIGHLIGHT_CLASS);
    highlightMarkers.forEach((marker) => {
      this.removeMarker(marker);
    });
    const selectedMarker = this._getSelectedMarker();
    if (!selectedMarker) return;
    // Create a reference for the currently selected marker.
    this._selected_marker = selectedMarker;
    // A marker was clicked. Highlight it with yet another marker ;).
    const startRow = selectedMarker.row_from;
    const endRow = selectedMarker.row_to;
    this.toggleMarkerSelection(
        startRow, endRow, constants.MARKER_HIGHLIGHT_CLASS);
  }
  /**
   * Remove all custom file content from the editor and the file objects.
   */
  flushCustomFileContent() {
    // TODO: Replace file tree dependencies.
    for (const key in this._known_files) {
      const fileCustomContent = this._known_files[key].customContent;
      if (!fileCustomContent) continue;
      const customComments = fileCustomContent.comments.slice();
      customComments.forEach(
          (comment) => {
            this.removeComment(comment, this._known_files[key]);
          });
      const customMarkers = fileCustomContent.markers.slice();
      customMarkers.forEach(
          (marker) => {
            this.removeMarker(marker, this._known_files[key]);
          });
    }
  }
  /**
   * Jsonifies all files with custom data (files with set markers or comments).
   * @return {string}
   */
  serializeFileData() {
    const customFileContents = [];
    for (const key in this._known_files) {
      const fileCustomContent = this._known_files[key].customContent;
      if (!fileCustomContent) continue;
      customFileContents.push(fileCustomContent);
    }
    // TODO: replace this lazy hack with a cleaner data retrieval way?
    function replacer(key, value) {
      if (key.includes('raw') || key === 'file') return undefined;
      return value;
    }
    return JSON.stringify(customFileContents, replacer);
  }

  /**
   * Sends custom file data to the backend for storage.
   * @param data
   * @return {*}
   */
  saveFileDataInBackend(data) {
    const params = defaultQueryParameters();
    const backendTarget = '/api/save_editor_data?' + $.param(params);
    // Using $.ajax here as we need to specify the request contentType.
    const req = $.ajax({
      type: 'POST',
      url: backendTarget,
      data: data,
      contentType: 'application/json;charset=UTF-8',
    });
    return req;
  }
  /**
   * Fetches custom file data from the backend.
   * @return {*|PromiseLike<T>|Promise<T>}
   */
  retrieveFileDataFromBackend() {
    const params = {};
    if (!constants.EDIT_MODE_ACTIVE) params['only_custom_data'] = '1';

    const editorSettings = window.EDITOR_SETTINGS;
    if (editorSettings) {
      const backendTarget = (editorSettings.annotation_data_url);
      const req = $.get({
        url: backendTarget,
        data: params,
      });
      return req;
    } else {
      console.log('[-] No editor settings found to proceed.');
    }
  }
  /**
   * Requests entry removal from the backend.
   * @return {*}
   */
  _deleteEntryFromBackend() {
    const params = defaultQueryParameters();
    const backendTarget = '/api/delete_entry?' + $.param(params);
    const req = $.post(backendTarget);
    return req;
  }
  /**
   * Loads the first file that was changed by a patch if available.
   */
  loadFirstPatchFile() {
    let firstPatchFile;
    if (Object.keys(this._known_files).length === 0) {
      console.log('! No known files ;/...');
      return;
    }
    for (const key in this._known_files) {
      const filePatchData = this._known_files[key].patch;
      if (!filePatchData) continue;
      firstPatchFile = this._known_files[key];
      break;
    }
    if (firstPatchFile) this.displayFile(firstPatchFile);
  }
  /**
   * Retrieves and setups any file data currently stored in the backend.
   * Attention: this will DROP all current custom data like comments etc.
   * @return {Promise<any>}
   */
  restoreFileBackendData() {
    return new Promise((resolve) => {
      $.when(this.retrieveFileDataFromBackend()).then((filesData) => {
        if (!filesData || filesData.length === 0) {
          resolve(false);
        }

        // Reset the editor state.
        this.flushCustomFileContent();
        let allComments = [];
        filesData.forEach((fileData) => {
          const targetFilePath = fileData.file_path;
          if (!(targetFilePath in this._known_files)) {
            console.log('[!] restoreFileBackendData: restoring unknown file:', fileData.file_name);
            const newFile =
              new File(null, fileData.file_name, fileData.file_hash, null);
            this._known_files[targetFilePath] = newFile;
          }
          // TODO: add proper checks here (e.g. does the target id exist?)
          const targetFile = this._known_files[targetFilePath];
          // Overwrite the target file's custom content.
          targetFile.customContent = fileData;
          allComments = allComments.concat(targetFile.comments);
          targetFile.markers.forEach((marker) => {
            // TODO: make the node class support more generic.
            targetFile.highlightNodes(marker.class);
          });
        });
        allComments.sort(function(a, b) {
          return a.sort_pos - b.sort_pos;
        });
        // Render essential UI elements for this custom data.
        allComments.forEach((comment) => {
          this.paintCommentSortable(comment);
        });
        const currentlyOpenFile = this._getCurrentlyOpenFile();
        if (currentlyOpenFile) {
          // Refresh everything that is displayed!
          this.displayFile(currentlyOpenFile, true);
          this.reloadFileFilter();
        }
        // Load the first comment if available.
        this._ui.gotoNextComment();

        resolve(true);
      });
    });
  }
  /**
   * Deletes the entry and all its children like comments and markers.
   * @private
   */
  deleteEntry() {
    this._ui.confirmYesNo(
        'Do you want to delete the complete entry?',
        () => {
          $.when(this._deleteEntryFromBackend()).then((status) => {
            this._ui.showSuccess(status['msg']);
          });
        });
  }
  /**
   * Save all current changes in the backend.
   * @private
   */
  saveState() {
    this._ui.confirmYesNo(
        'Do you want to overwrite the previous state?', () => {
        // delay spinner by 0.5s so it wont show if the save operation is
        // fast.
          const t = window.setTimeout(() => {
            this._ui.showSpinner('Saving');
          }, 500);
          const data = this.serializeFileData();
          $.when(this.saveFileDataInBackend(data))
              .then((status) => {
                window.clearTimeout(t);
                this._ui.hideSpinner();
                this._ui.showSuccess(status['msg']);
              })
              .catch(() => {
                window.clearTimeout(t);
                this._ui.hideSpinner();
                this._ui.showError('Error during save');
              });
        });
  }
  /**
   * Loads the last stored entries and throws away unsaved changes.
   */
  resetState() {
    this._ui.confirmYesNo(
        'Do you want to reset the complete current state?', () => {
          this.restoreFileBackendData();
        });
  }
  /**
   * Fetches metadata from this and other involved objects.
   * Metadata does involve things like number of repository files and marker
   * data.
   */
  get metadata() {
    const metadata = {};
    metadata['file_tree'] = null;
    if (this._file_tree) metadata['file_tree'] = this._file_tree.metadata;
    metadata['editor'] = {};
    const markers = this._getMarkers(constants.VULNERABLE_MARKER_CLASS);
    // console.log(this._ui.getMarkerAnnotation());
    metadata['editor']['vuln_markers'] = markers;
    metadata['editor']['open_file_path'] = '';
    if (this._currently_open_file) {
      metadata['editor']['open_file_path'] = this._currently_open_file.path;
    }
    return metadata;
  }
  /**
   * Add a new comment to the current file and the view
   * @param {int} rowFrom Section start line number.
   * @param {int} rowTo Section end line number.
   * @param {string} text
   * @return {*}
   */
  createComment(rowFrom, rowTo, text) {
    const currentlyOpenFile = this._getCurrentlyOpenFile();
    if (!currentlyOpenFile) return null;
    const comment = new FileComment(currentlyOpenFile, rowFrom, rowTo, text);
    this.paintCommentWidget(comment);
    this.paintCommentSortable(comment);
    return currentlyOpenFile.addComment(comment);
  }
  /**
   * Remove a comment from the given file
   * @param {!FileComment} comment
   * @param {?File} file
   */
  removeComment(comment, file = null) {
    file = file ? file : this._getCurrentlyOpenFile();
    if (!file) return;
    if (comment.raw_sortable) {
      // Remove all corresponding UI elements.
      this._ui.removeSortableItem(comment);
      comment.raw_sortable = null;
    }
    if (comment.raw_widget) comment.raw_widget.dispose();

    if (comment.raw_section_marker) {
      this.removeMarker(comment.raw_section_marker);
    }

    // Detach the comment from the target file.
    file.removeComment(comment);
  }
  /**
   * Adds a sortable entry for a comment.
   * @param {!FileComment} createdComment
   */
  paintCommentSortable(createdComment) {
    if (!createdComment.file) return;
    // Create a UI widget for this, too.
    if (createdComment.raw_sortable) return;
    if (this._ui) this._ui.addSortableItem(createdComment);
  }
  /**
   * Adds a comment/annotation widget (annotation) to the editor canvas.
   * This widget is used for things like displaying lines added by a patch.
   * Use the functions below from the errorMarker.js:
   * https://github.com/ajaxorg/ace/blob/master/lib/ace/ext/error_marker.js
   * @param {!FileComment} createdComment
   */
  paintCommentWidget(createdComment) {
    if (createdComment.raw_widget) return;
    this._editor.trigger('editor.unfold', {
      selectionLines: createdComment.row_from,
    });
    const widget = new CommentWidget(
        createdComment, this._editor, this._display_patch_data,
        constants.EDIT_MODE_ACTIVE);
    widget.create();
    widget.onRemove((comment) => {
      this.removeComment(comment);
    });
    const rowFrom = createdComment.row_from;
    let rowTo = rowFrom;
    if (createdComment.row_to) rowTo = createdComment.row_to;
    widget.show(new monaco.Position(rowTo + 1, 1), 5);
    createdComment.raw_widget = widget;
    createdComment.raw_section_marker =
      this.createMarker(rowFrom, rowTo, constants.SECTION_MARKER_CLASS);
  }
  /**
   * Paints a marker on the editor canvas in a given region and binds it to a
   * given marker object..
   * @param {!FileMarker} marker
   */
  paintMarker(marker) {
    if (marker.raw) return;
    let editor = this._editor;
    let startRow = marker.row_from + 1;
    let endRow = marker.row_to + 1;
    // Adjust the linue number if needed
    if (editor.getEditorType() === monaco.editor.EditorType.IDiffEditor) {
      startRow = editor.getDiffLineInformationForOriginal(startRow)
          .equivalentLineNumber;
      endRow =
        editor.getDiffLineInformationForOriginal(endRow).equivalentLineNumber;
      editor = editor.getModifiedEditor();
    }
    const range = new monaco.Range(
        startRow, marker.colum_from + 1, endRow, marker.column_to + 1);
    const options = {
      isWholeLine: true,
    };
    if (marker.class === constants.IRRELEVANT_MARKER_CLASS) {
      options.inlineClassName = marker.class;
    } else {
      options.className = marker.class;
    }
    marker.raw = editor.deltaDecorations([], [{
      range,
      options,
    }]);
  }
  /**
   * Creates a marker and binds it to the currently used file object.
   * @param {number} startRow
   * @param {number} endRow
   * @param {string} markerClass
   * @return {FileMarker} the newly created marker
   */
  createMarker(startRow, endRow, markerClass) {
    const currentlyOpenFile = this._getCurrentlyOpenFile();
    if (!currentlyOpenFile) return null;
    const marker =
      new FileMarker(currentlyOpenFile, markerClass, startRow, endRow);
    //
    const useMarker = currentlyOpenFile.addMarker(marker);
    this.paintMarker(useMarker);
    currentlyOpenFile.highlightNodes(markerClass);
    return useMarker;
  }
  /**
   * Removes a specific marker from the editor and current file context.
   * @param {!FileMarker} marker
   * @param {?File} file
   * @private
   */
  removeMarker(marker, file = null) {
    file = file ? file : this._getCurrentlyOpenFile();
    if (!file) return;
    if (marker.raw) {
      let editor = this._editor;
      if (editor.getEditorType() === monaco.editor.EditorType.IDiffEditor) {
        editor = editor.getModifiedEditor();
      }
      editor.deltaDecorations(marker.raw, []);
      marker.raw = null;
    }
    file.removeMarker(marker);
    file.highlightNodes(marker.class);
  }
  /**
   * Removes all markers or a filtered subset of them from the editor.
   * N.B.: Not from the file object! Use removeMarker() on file object
   * instead.
   * @param {?string} filterClass
   */
  flushMarkers(filterClass = null) {
    const markerList = this._getMarkers(filterClass);
    for (const marker of markerList) {
      if (marker.raw) {
        let editor = this._editor;
        if (editor.getEditorType() === monaco.editor.EditorType.IDiffEditor) {
          editor = editor.getModifiedEditor();
        }
        editor.deltaDecorations(marker.raw, []);
        marker.raw = null;
      }
    }
  }
  /**
   * Removes all comments from the editor.
   * N.B.: Not from the file object! Use removeComment() on file object
   * instead.
   */
  flushComments() {
    for (const comment of this._getComments()) {
      if (!comment.raw_widget) {
        continue;
      }
      comment.raw_widget.dispose();
      comment.raw_widget = null;
    }
  }
  /**
   * Returns a list of FileMarker (wrapper) objects.
   * @param {?string} filterClazz
   * @return {Array<FileMaker>}
   * @private
   */
  _getMarkers(filterClazz = null) {
    const currentlyOpenFile = this._getCurrentlyOpenFile();
    if (!currentlyOpenFile) return [];
    const allMarkers = currentlyOpenFile.markers;
    const filteredMarkers = [];
    allMarkers.forEach((marker) => {
      if (filterClazz && marker.class !== filterClazz) return;
      filteredMarkers.push(marker);
    });
    // this._ui.getMarkerAnnotation()
    return filteredMarkers;
  }
  /**
   * Returns a list of FileComment (wrapper) objects.
   * @return {Array<FileComment>}
   * @private
   */
  _getComments() {
    const currentlyOpenFile = this._getCurrentlyOpenFile();
    if (!currentlyOpenFile) return [];
    return currentlyOpenFile.comments;
  }
  /**
   * Returns the object for the currently in the file browser selected file.
   * @return {?File}
   * @private
   */
  _getCurrentlyOpenFile() {
    return this._currently_open_file;
  }
  /**
   * Get the model for the given uri or create a new one.
   * @param {string} content
   * @param {!monaco.Uri} uri
   * @return {*}
   * @private
   */
  _getOrCreateModel(content, uri) {
    const model = monaco.editor.getModel(uri);
    if (model) {
      return model;
    }
    return monaco.editor.createModel(content, null, uri);
  }
  /**
   * Restores settings of a previously opened file.
   * @param {!File} file
   * @private
   * @return {*}
   */
  _restoreOldFileState(file) {
    let result = null;

    // TODO: Add proper toggling between diff and non-diff editor.
    // let displayPatches = this._display_patch_data;
    // if (this._display_patch_data && !file.patch) {
    //   this.displayPatches(false);
    // }
    //      this.displayPatches(true);

    if (this._display_patch_data) {
      let useContent = file.content;
      if (file.status === 'added' && file.patch.length > 0) {
        useContent = new Promise((resolve) => {
          resolve('');
        });
      }

      result = useContent.then((content) => {
        const patchedContent = this.applyPatchDeltas(content, file.patch);
        this._editor.setModel({
          original: this._getOrCreateModel(content, monaco.Uri.file(file.path)),
          modified: this._getOrCreateModel(
              patchedContent, monaco.Uri.file('b/' + file.path)),
        });
        return new Promise((resolve) => {
          this._editor.onDidUpdateDiff(() => resolve());
        });
      });
    } else {
      result = file.content.then((content) => {
        const model =
          this._getOrCreateModel(content, monaco.Uri.file(file.path));
        this._editor.setModel(model);
      });
    }
    return result
        .then(() => {
        // Restore any previous markers:
          for (const marker of file.markers) {
            this.paintMarker(marker);
          }
          // Restore any previous comments:
          for (const comment of file.comments) {
            this.paintCommentWidget(comment);
            this.paintCommentSortable(comment);
          }
        });
  }
  /**
   * Determines whether to display patch data (added and removed lines).
   * @param {boolean} state
   */
  displayPatches(state) {
    if (state !== true && state !== false) {
      console.log('displayPatches: non-bool received as new state.');
      return;
    }
    if (state === this._display_patch_data) {
      return;
    }
    const viewState = this._editor.saveViewState();
    this._editor.dispose();
    this._display_patch_data = state;
    this._createEditor();
    // Update new state in the current session.
    if (this._currently_open_file) {
      this.displayFile(this._currently_open_file, true);
    }
    this._editor.restoreViewState(viewState);
  }
  /**
   * Loads the context of a file and scrolls into the given position.
   * @param {?File} file
   * @param {Integer} row
   */
  navigateTo(file, row) {
    $.when(this.displayFile(file)).then(() => {
      // TODO: find a way w/o using the internal function. Might require to open
      // a bug
      const verticalRevealTypeTop = 3;
      this._getEditor()._revealPosition(
          {
            column: 0,
            lineNumber: row,
          },
          verticalRevealTypeTop);
    });
  }
  /**
   * Jumps to the previous/next change introduced by a patch.
   * The jump is executed relative to the current view position.
   * @param {boolean=} gotoNextPatch
   */
  _gotoPatch(gotoNextPatch = false) {
    if (!this._diffNavi || !this._diffNavi.canNavigate()) {
      return;
    }
    if (gotoNextPatch) {
      this._diffNavi.next();
    } else {
      this._diffNavi.previous();
    }
  }
  /**
   * Jumps to the previous change introduced by a patch.
   */
  gotoPreviousPatch() {
    this._gotoPatch(false);
  }
  /**
   * Jumps to the next change introduced by a patch.
   */
  gotoNextPatch() {
    this._gotoPatch(true);
  }
  /**
   * Displays a File object in the editor.
   * @param {!File} file
   * @param {boolean=} forceRefresh
   * @return {!Promise}
   */
  displayFile(file, forceRefresh = false) {
    const currentlyOpenFile = this._getCurrentlyOpenFile();
    if (currentlyOpenFile && file.hash === currentlyOpenFile.hash &&
      !forceRefresh) {
      return Promise.resolve();
    }
    this.cleanup();
    return this._restoreOldFileState(file).then(() => {
      this._currently_open_file = file;
      // Important: update the currently selected files in the file tree.
      if (this._file_tree) this._file_tree.currentlySelectedFile = file;
      this.updatesHandler();
    });
  }
  /**
   * Toggles highlighting for a given code section if the selection does NOT
   * overlap with already highlighted sections.
   * Covers the following cases:
   * 1) Selection has NO overlap with any existing markers
   *    -> Add a new marker.
   * 2) Selection lies on or within one existing marker.
   *    _> Toggle (remove) any marked area for the current selection.
   * 2) Selection overlaps with one or multiple marker/s.
   *    -> Merge all affected markers with filled gaps into a large marker.
   * @param {number} selectionStart
   * @param {number} selectionEnd
   * @param {string} markerClass
   */
  toggleMarkerSelection(selectionStart, selectionEnd, markerClass) {
    const markerList = this._getMarkers(markerClass);
    const delMarkers = [];
    // We assume that the new region was not higlighted yet for now.
    const selectionSize = selectionEnd - selectionStart + 1;
    let alreadySelectedSize = 0;
    markerList.forEach((marker) => {
      const startRow = marker.row_from;
      const endRow = marker.row_to;
      // Ingore this marker if the current selection is outside.
      if (selectionStart > endRow || selectionEnd < startRow) return;
      if (selectionStart > startRow) {
        const rangeOffset = selectionStart - startRow - 1;
        // row_from + range_offset should stay untouched
        this.createMarker(startRow, startRow + rangeOffset, markerClass);
        // TODO: this computation is a bit flawed as the selected region can be
        // within an already marked region. It is possible that
        // "already_selected_size" > selection_size which doesn't make a lot of
        // sense given it is supposed to be a subsection.
        alreadySelectedSize += endRow - selectionStart + 1;
      }
      if (selectionEnd < endRow) {
        const rangeOffset = endRow - selectionEnd - 1;
        // The region [end_row - range_offset] should stay untouched
        this.createMarker(endRow - rangeOffset, endRow, markerClass);
        alreadySelectedSize += selectionEnd - startRow + 1;
      }
      if (selectionStart === startRow && selectionEnd === endRow) {
        alreadySelectedSize += selectionSize;
      }
      delMarkers.push(marker);
    });
    delMarkers.forEach((marker) => {
      this.removeMarker(marker);
    });
    // Add the marker if any non already highlighted lines have been selected.
    if (alreadySelectedSize < selectionSize) {
      this.createMarker(selectionStart, selectionEnd, markerClass);
    }
  }
  /**
   *
   * @param {string} content
   * @param {?Array<{diff_line_no: number, source_line_no: number,
   *     target_line_no: number, value: string, line_type: string}>} patchData
   */
  applyPatchDeltas(content, patchData) {
    if (!patchData) {
      return content;
    }
    let sep = '\n';
    const lineSeparatorMaches = content.match(/\r?\n/);
    if (lineSeparatorMaches) {
      sep = content.match(/\r?\n/)[0];
    }
    const contentLines = content.split(sep);
    let offset = 0;
    patchData.sort((a, b) => a.diff_line_no - b.diff_line_no);
    for (const line of patchData) {
      if (line.line_type === '-') {
        const lineNo = line.source_line_no + offset - 1;
        contentLines.splice(lineNo, 1);
        offset--;
      } else if (line.line_type === '+') {
        const lineNo = line.target_line_no - 1;
        const text = line.value.replace(/\r?\n$/, '');
        contentLines.splice(lineNo, 0, text);
        offset++;
      }
    }
    return contentLines.join(sep);
  }
}
export {Editor};
