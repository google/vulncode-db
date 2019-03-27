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
    const repositoryFiles = jsonContent['files'];
    const patchFiles = jsonContent['patched_files'];
    const commitData = jsonContent['commit'];
    // TODO: This should be refactored.
    const editorSettings = window.EDITOR_SETTINGS;
    if (editorSettings) {
      editorSettings.parent_hash = commitData['parent_hash'];
    }
    // Merge the patch files into the other file representation.
    this.mergePatchesToFiles(repositoryFiles, patchFiles);

    const treeData = this.filesToTree(repositoryFiles);
    // Required to allow tree modifications (create, rename, move, delete).
    treeData['core']['check_callback'] = true;
    // Always escape HTML content in node names.
    treeData['core']['force_text'] = true;
    // Init new jstree:
    this._jstree = $('#files').jstree(treeData);

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

        // Load any data stored in the backend or display the first patch entry.
        this._editor.restoreFileBackendData().then(
            (dataAvailable) => {
              if (!dataAvailable) {
                this._editor.loadFirstPatchFile();
              }
            });
        resolve(true);
      });
    });
  }

  /**
   * Takes a set of patch files and merges them to a list of repository files.
   * @param repoFiles
   * @param patchFiles
   * @return {*}
   */
  mergePatchesToFiles(repoFiles, patchFiles) {
    function getFile(path, sha, type, deltas=null, status=null) {
      return {
        'path': path,
        'sha': sha,
        'type': type,
        'deltas': deltas,
        'status': status,
      };
    }

    function replaceInsert(files, newFile, newOffset) {
      // Replace a potentially existing file..
      let pos;
      let replaceFiles = 0;
      for (pos=0; pos < files.length; pos++) {
        const file = files[pos];
        if (file['type'] === newFile['type'] && file['path'] === newFile['path']) {
          replaceFiles = 1;
          newOffset = pos;
          break;
        }
      }
      files.splice(newOffset, replaceFiles, newFile);
    }

    for (const path in patchFiles) {
      if (!patchFiles.hasOwnProperty(path)) {
        continue;
      }

      const subDirectories = path.split('/').slice(0, -1);
      let basePath = '';

      // 1) Find correct offset for first directory.
      const firstDir = subDirectories[0];
      let pos;
      for (pos=0; pos < repoFiles.length; pos++) {
        const file = repoFiles[pos];
        if (file['type'] !== 'tree') {
          continue;
        }
        // If the sub path is already there ignore this
        if (file['path'] === firstDir) {
          basePath = subDirectories.shift() + '/';
          break;
        }
        if (file['path'] > firstDir) {
          break;
        }
      }
      let insertOffset = pos + 1;

      // 2) Insert each component consecutively at that offset.
      subDirectories.forEach((directory_path) => {
        if (!basePath) {
          basePath = directory_path + '/';
        }
        const currentPath = basePath + directory_path;
        basePath = currentPath + '/';
        // create new component as it doesn't exist yet.
        const file = getFile(currentPath, '?', 'tree');
        replaceInsert(repoFiles, file, insertOffset);
        insertOffset++;
      });

      // Attach our patch files to the global file listing.
      const file = getFile(path, patchFiles[path]['sha'], 'blob',
          patchFiles[path]['deltas'], patchFiles[path]['status']);
      replaceInsert(repoFiles, file, insertOffset);
    }
    return repoFiles;
  }

  /**
   * Takes a list of repository files and creates a recursive tree structure from it.
   * @param files
   * @return {} The root node of the tree.
   */
  filesToTree(files) {
    const root = {};
    root['core'] = {};
    root['core']['data'] = [];
    let repo_name = 'repo_name';
    const editorSettings = window.EDITOR_SETTINGS;
    if (editorSettings) {
      repo_name = editorSettings.repo_name;
    }

    const root_node = {
      'text': repo_name,
      'data': {
        'hash': '?',
        'path': '/',
      },
      'state': {
        'opened': true,
      },
      'children': [],
    };
    root['core']['data'].push(root_node);

    function basename(path) {
      return path.split('/').reverse()[0];
    }

    function append(current_root_node, items, last_depth=1) {
      while (items.length > 0) {
        const current_depth = items[0]['path'].split('/').length;
        if (current_depth < last_depth) {
          return;
        }
        const tree_item = items.shift();

        const node = {};
        node['text'] = basename(tree_item['path']);
        node['data'] = {};
        node['data']['path'] = tree_item['path'];
        node['data']['hash'] = tree_item['sha'];


        if ('deltas' in tree_item) {
          node['data']['patch'] = tree_item['deltas'];
        }
        if ('status' in tree_item) {
          node['data']['status'] = tree_item['status'];
        }

        if (tree_item['type'] === 'blob') {
          node['icon'] = 'jstree-file';
          current_root_node['children'].push(node);
        } else {
          node['children'] = [];
          append(node, items, last_depth + 1);
          current_root_node['children'].push(node);
        }
      }
    }
    append(root_node, files);
    function sortme(node) {
      node['children'].sort((x, y) => {
        if ('children' in x) {
          return -1;
        }
        if (x['path'] < y['path']) {
          return 1;
        }
      });

      node['children'].forEach((child) => {
        if ('children' in child) {
          sortme(child);
        }
      });
    }
    sortme(root_node);

    return root;
  }


  redraw() {
    this._jstree.jstree(true).redraw(true);
  }

  renameFileNode(file, newName) {
    this._jstree.jstree('rename_node', file.node, newName);
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
    // Ignore directories.
    if (node.icon === true) return;
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
    const filePath = node.data.path;
    if (node.data.sha) console.log('noda.data.sha found...', node.data);
    const fileHash = node.data.hash;
    if (this.all_files.hasOwnProperty(filePath)) return this.all_files[filePath];

    const fileName = node.text;
    let filePatch = null;
    if (node.data.hasOwnProperty('patch')) {
      filePatch = node.data.patch;
    }
    let status = null;
    if (node.data.hasOwnProperty('status')) {
      status = node.data.status;
    }
    const file = new File(this, fileName, fileHash, filePatch, status);
    file.node = node;

    this.all_files[filePath] = file;
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
    const rootFile = this.all_files['/'];
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
