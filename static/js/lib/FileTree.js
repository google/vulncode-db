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

import * as constants from './Constants.js';
import {File} from './File.js';

/**
 * The FileTree class maintains File objects to allow repository exploration.
 */
class FileTree {
  constructor(editor, jsonContent) {
    const treeData = jsonContent['files'];
    // Required to allow tree modifications (create, rename, move, delete).
    treeData['core']['check_callback'] = true;
    // Always escape HTML content in node names.
    treeData['core']['force_text'] = true;
    // Init new jstree:
    this._jstree = $('#files').jstree(treeData);
    this.file_provider_url = jsonContent['file_provider_url'];

    this._editor = editor;
    this.all_files = {};

    this._currentlySelectedFile = null;
    // Create a dummy file for testing...
    const dummyNode = {};
    dummyNode.li_attr = {};
    this._currentlySelectedFile =
        new File(this, 'dummy_file.js', 'none', null);
    this._currentlySelectedFile.content = '// Please load a file.\n';
    this._currentlySelectedFile.content += 'Test\nContent\nFoo\nBar\n';
    this._currentlySelectedFile.node = dummyNode;

    this.loaded_promise = new Promise((resolve) => {
      // Setup action hooks.
      this._jstree.on(
          'activate_node.jstree',
          (e, data) => this._treeClickedCallback(e, data));
      this._jstree.on('ready.jstree', (e, data) => {
        const rootNodeId = this._jstree.jstree(true).get_node('#').children[0];
        this._buildFileTree(rootNodeId);
        this._walkTree((file) => {
          file.highlightIfPatched();
        });

        this._editor.initKnownFiles(this.all_files);

        this._editor.reloadFileFilter();
        this._editor.updateUIMetadata();

        // Load any data stored in the backend.
        this._editor.restoreFileBackendData();
        resolve(true);
      });
    });
  }

  redraw() {
    this._jstree.jstree(true).redraw(true);
  }

  renameFileNode(file, newName) {
    this._jstree.jstree('rename_node', file.node, newName);
  }

  /**
   * A file provider url can for example point to GitHub or the VCS proxy.
   * @return {*}
   */
  getFileProviderUrl() {
    return this.file_provider_url;
  }

  destroy() {
    // TODO: backup / save state??
    this._jstree = this._jstree.jstree('destroy');
  }

  set currentlySelectedFile(file) {
    this._jstree.jstree(true).deselect_node(
        '#' + this._currentlySelectedFile.node.id);
    this._jstree.jstree(true).select_node('#' + file.node.id);
    this._currentlySelectedFile = file;
  }

  get currentlySelectedFile() {
    return this._currentlySelectedFile;
  }

  get metadata() {
    const metadata = {};
    metadata['num_files'] = this.numFiles;
    return metadata;
  }

  get numFiles() {
    return Object.keys(this.all_files).length - 1;
  }

  /**
   * Applies a filter to the displayed file tree.
   * Such a filter could be to only display files that contain patch data or
   * which were marked as vulnerable.
   * @param {String} filter
   */
  applyFilter(filter) {
    let requiredClasses = [];
    let expandFiles = false;
    switch (filter) {
      case 'relevant': {
        requiredClasses =
            [constants.PATCHED_NODE_CLASS, constants.VULNERABLE_NODE_CLASS];
        expandFiles = true;
      } break;

      case 'vulnerable': {
        requiredClasses = [constants.VULNERABLE_NODE_CLASS];
        expandFiles = true;
      } break;

      case 'patched': {
        requiredClasses = [constants.PATCHED_NODE_CLASS];
        expandFiles = true;
      } break;

      case 'all':
      default:
    }

    /**
     * Hides nodes that don't have any of the required classes and returns
     * whether to keep filtering the node's children.
     * @param {File} file
     * @return {boolean}
     */
    const applyFileFilter = function(file) {
      this._jstree.jstree(true).show_node(file.node, true);

      if (requiredClasses.length === 0) return true;

      const displayFile = requiredClasses.some((allowedClass) => {
        if (file.node.li_attr['class'] &&
            file.node.li_attr['class'].includes(allowedClass)) {
          return true;
        }
      });

      if (!displayFile) {
        this._jstree.jstree(true).hide_node(file.node, true);
        return false;
      }

      if (expandFiles) this._jstree.jstree('open_node', file.node);

      return true;
    };
    this._walkTree(applyFileFilter, true);
    this._jstree.jstree(true).redraw(true);
  }

  /**
   * Updates the internal state once a new file was clicked in the file browser.
   * @param {Event} e
   * @param data
   * @private
   */
  _treeClickedCallback(e, data) {
    const node = data.instance.get_node(data.node);
    // Ignore parent nodes...
    if (node.children && node.children.length > 0) return;
    const file = this._nodeToFile(node);
    this._editor.displayFile(file);
  }

  /**
   * Creates a File object wrapper for a given JStree node.
   * @param node
   * @return {*}
   * @private
   */
  _nodeToFile(node) {
    const fileId = node.data.id;
    if (node.data.sha) console.log('noda.data.sha found...', node.data);
    const fileHash = node.data.hash;
    if (this.all_files.hasOwnProperty(fileId)) return this.all_files[fileId];

    const fileName = node.text;
    let filePatch = null;
    if (node.data.hasOwnProperty('patch')) {
      filePatch = node.data.patch;
    }
    const file = new File(this, fileName, fileHash, filePatch);
    file.node = node;

    this.all_files[fileId] = file;
    return file;
  }

  /**
   * Calls a callback function for all tree elements in a given order.
   * @param currentFile
   * @param callback
   * @param inverseOrder
   * @private
   */
  _walkSubTree(currentFile, callback, inverseOrder = false) {
    if (inverseOrder) {
      const result = callback.call(this, currentFile);
      if (!result) return;
    }

    if (currentFile.children.length > 0) {
      currentFile.children.forEach((childFile) => {
        this._walkSubTree(childFile, callback, inverseOrder);
      });
    }

    if (!inverseOrder) callback.call(this, currentFile);
  }

  /**
   * Walks the File objects tree from leaves to root or the other way around.
   * @param callback
   * @param inverseOrder
   * @private
   */
  _walkTree(callback, inverseOrder = false) {
    const rootFile = this.all_files[0];
    this._walkSubTree(rootFile, callback, inverseOrder);
  }

  /**
   * Creates a File objects tree from a given JStree tree structure.
   * @param currentNodeId
   * @param parentNodes
   * @private
   */
  _buildFileTree(currentNodeId, parentNodes = []) {
    const currentNode = this._jstree.jstree(true).get_node(currentNodeId);
    const file = this._nodeToFile(currentNode);
    if (currentNode.children.length > 0) {
      const childrenFiles = [];
      currentNode.children.forEach((childNodeId) => {
        const childNode = this._jstree.jstree(true).get_node(childNodeId);
        const childFile = this._nodeToFile(childNode);
        childrenFiles.push(childFile);
        this._buildFileTree(childNodeId, parentNodes.concat([currentNode]));
      });
      file.children = childrenFiles;
      return;
    }
    // Leaf node
    let fileParents = [];
    parentNodes.forEach((parentNode) => {
      const parentFile = this._nodeToFile(parentNode);
      fileParents = fileParents.concat([parentFile]);
    });
    file.parents = fileParents;
  }
}

export {FileTree};
