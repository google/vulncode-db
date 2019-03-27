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
import {FileComment} from './FileComment.js';
import {FileMarker} from './FileMarker.js';

/**
 * The File class contains information regarding a file object ranging from its
 * content to custom data like comments and markers.
 */
class File {
  /**
   *
   * @param fileTree
   * @param fileName
   * @param fileHash
   * @param filePatch
   * @param status {?String} Whether this file was added, modified or removed.
   */
  constructor(fileTree, fileName, fileHash, filePatch, status=null) {
    this._file_tree = fileTree;
    this.name = fileName;
    this.hash = fileHash;
    this.patch = filePatch;
    this.status = status;

    // File content usually pulled from the Github API.
    this._content = null;

    // Relationship data.
    this._children = [];
    this._parents = [];
    this._path = null;

    // Custom data which is add/removed during editing.
    this._markers = [];
    this._comments = [];

    // Dom element.
    this.node = null;
  }

  _getFileContent() {
    let fileProviderUrl = null;
    let fileRefProviderUrl = null;
    let parentHashRef = null;

    const editorSettings = window.EDITOR_SETTINGS;
    if (editorSettings) {
      if (editorSettings.hasOwnProperty('file_provider_url')) {
        fileProviderUrl = editorSettings.file_provider_url;
      }
      if (editorSettings.hasOwnProperty('file_ref_provider_url')) {
        fileRefProviderUrl = editorSettings.file_ref_provider_url;
      }
      if (editorSettings.hasOwnProperty('parent_hash')) {
        parentHashRef = editorSettings.parent_hash;
      }
    }

    if (!fileProviderUrl && !fileRefProviderUrl) {
      console.log('No file provider url given for _getFileContent!');
      return null;
    }
    let targetUrl = fileProviderUrl.replace(
        editorSettings.HASH_PLACEHOLDER, this.hash);

    // If this is a patched file we will fetch the previous file state.
    if (this.patch && this.status !== 'added' ) {
      if (!fileProviderUrl || !parentHashRef) {
        console.log('No reference file provider given. Can not fetch previous file state.');
        return null;
      }
      targetUrl = fileRefProviderUrl.replace(
          editorSettings.PATH_PLACEHOLDER, encodeURIComponent(this.path));
      targetUrl = targetUrl.replace(editorSettings.HASH_PLACEHOLDER, parentHashRef);
    }

    // Check if the file is already cached and serve it if so.
    const req = $.get({
      url: targetUrl,
      beforeSend: function(xhr) {
        xhr.setRequestHeader('Accept', 'application/vnd.github-blob.raw');
      },
    });
    console.log('Fetching file from Github:', this.name);

    return req.then(function(fileContent) {
      return fileContent;
    });
  }

  get path() {
    if (this._path) return this._path;

    let path = '';
    this._parents.slice(1).forEach(
        (parentFile) => {
          path += parentFile.name + '/';
        });
    path += this.name;
    return path;
  }

  // Getter
  get content() {
    if (this._content) return this._content;
    this._content = this._getFileContent();
    return this._content;
  }

  set content(newContent) {
    this._content = newContent;
  }

  get children() {
    return this._children;
  }

  set children(children) {
    this._children = children;
  }

  get parents() {
    return this._parents;
  }

  set parents(children) {
    this._parents = children;
  }

  get markers() {
    return this._markers;
  }

  set markers(markers) {
    this._markers = markers;
  }

  get comments() {
    return this._comments;
  }

  set comments(comments) {
    this._comments = comments;
  }

  get customContent() {
    if (this._markers.length === 0 && this._comments.length === 0) return null;

    if (!this.node) {
      console.log('File:get customContent - invalid node detected...');
      return null;
    }

    const data = {};
    data.name = this.name;
    data.hash = this.hash;
    data.path = this.path;
    data.patch = this.patch;

    // Skip all section markers (they are saved in the FileComment already).
    const markers = [];
    this._markers.forEach((marker) => {
      if (marker.class === constants.SECTION_MARKER_CLASS) return;
      markers.push(marker);
    });
    data.markers = markers;

    // Update the current comment positions.
    this._comments.forEach((comment) => {
      // TODO: improve this impressively ugly hack to get the UI object...
      comment.sort_pos = this._file_tree._editor._ui.getCommentSortPos(comment);
    });
    data.comments = this._comments;
    return data;
  }

  set customContent(data) {
    if (!data.comments || !data.markers) {
      console.log('File:set customContent - received invalid custom content');
      return null;
    }

    this._markers = [];
    data.markers.forEach((marker) => {
      const newMarker = new FileMarker(
          this, marker.marker_class, marker.row_from, marker.row_to);
      this._markers.push(newMarker);
    });

    this._comments = [];
    data.comments.forEach((comment) => {
      const rowFrom = comment.row_from;
      const rowTo = comment.row_to;
      const newComment = new FileComment(
          this, rowFrom, rowTo, comment.text, comment.sort_pos,
          comment.creator, comment.revision);
      this._comments.push(newComment);
    });
    if (data.file_path) this._path = data.file_path;
    // TODO: Removed deprecated patch storing for editor data.
    if (data.file_patch && data.file_patch !== 'DEPRECATED') {
      this.patch = data.file_patch;
    }
  }

  addComment(newComment) {
    const overlappingComment = this._comments.some((comment) => {
      return (
        newComment.row_from <= comment.row_to &&
              newComment.row_from >= comment.row_from ||
          newComment.row_to <= comment.row_to &&
              newComment.row_to >= comment.row_from);
    });
    if (overlappingComment) return null;

    this._comments.push(newComment);
    return newComment;
  }

  removeComment(comment) {
    const pos = this._comments.indexOf(comment);
    if (pos <= -1) return false;
    this._comments.splice(pos, 1);
    return true;
  }

  /**
   * Adds a marker only if it or an equivalent marker doesn't already exist.
   * In any other case this will return the existing/equivalent marker.
   * @param {FileMarker} marker
   * @return {*} The new marker or an equivalent that already existed.
   */
  addMarker(marker) {
    const pos = this._markers.indexOf(marker);
    if (pos > -1) return marker;
    // Duplicate detection.
    let equivalentMarker = null;
    const markerExists = this._markers.some((existingMarker) => {
      if (existingMarker.Serialize() === marker.Serialize()) {
        equivalentMarker = existingMarker;
        return true;
      }
    });
    if (markerExists) return equivalentMarker;

    this._markers.push(marker);
    return marker;
  }

  removeMarker(marker) {
    const pos = this._markers.indexOf(marker);
    if (pos <= -1) return false;
    this._markers.splice(pos, 1);
    return true;
  }

  // TODO: remove?
  getCommentByID(id) {
    let targetComment = null;
    this._comments.some((comment) => {
      if (comment.id !== id) return false;
      targetComment = comment;
      return true;
    });
    return targetComment;
  }

  /**
   * Toggles a class name for a given file object's DOM node.
   * @param {String} cssClass
   * @param {Boolean} active
   * @private
   */
  _toggleFileClass(cssClass, active = true) {
    const node = this.node;
    if (!node) return;

    if (!node.li_attr['class']) node.li_attr['class'] = '';

    node.li_attr['class'] = node.li_attr['class'].replace(cssClass, '');
    node.li_attr['class'] = node.li_attr['class'].replace(/\s+/g, ' ');
    if (active) node.li_attr['class'] += cssClass + ' ';
  }

  /**
   * Return true if there exists any marker of the given class.
   * @param {String} markerClass
   * @return {boolean}
   */
  hasMarkersWithClass(markerClass) {
    return this._markers.some((marker) => {
      if (marker.class.includes(markerClass)) return true;
    });
  }

  /**
   * Returns a list of child files whose DOM node contains a specific marker
   * class.
   * @param {String} cssClass
   * @return {Array}
   */
  getMarkedChildrenFiles(cssClass) {
    const markedChildrenFiles = [];
    this._children.forEach((childFile) => {
      if (!childFile.node.li_attr['class'] ||
          !childFile.node.li_attr['class'].includes(cssClass)) {
        return;
      }
      markedChildrenFiles.push(childFile);
    });
    return markedChildrenFiles;
  }

  /**
   * Sets the className properties for this file's node and all of its parents'
   * nodes.
   * @param {String} markerClass
   */
  highlightNodes(markerClass) {
    if (!this._file_tree) return;

    // For now we are only interested in vulnerable marker for node
    // highlighting.
    if (markerClass !== constants.VULNERABLE_MARKER_CLASS) return;
    const useCssClass = constants.VULNERABLE_NODE_CLASS;


    let applyClass = false;
    if (this.hasMarkersWithClass(markerClass)) applyClass = true;
    this._toggleFileClass(useCssClass, applyClass);

    // We have to traverse the parents in reverse order since we make changes
    // to the children elements which are in turn checked for containing markers
    // of a specific class.
    this._parents.slice().reverse().forEach((parentFile) => {
      const markedChildrenFiles =
          parentFile.getMarkedChildrenFiles(useCssClass);
      const numMarkedChildrenFiles = markedChildrenFiles.length;

      let newName = parentFile.name;
      if (numMarkedChildrenFiles > 0) {
        newName += ' (' + numMarkedChildrenFiles + ')';
      }
      this._file_tree.renameFileNode(parentFile, newName);
      const newClassStateApplied = (numMarkedChildrenFiles > 0);
      parentFile._toggleFileClass(useCssClass, newClassStateApplied);
    });
    this._file_tree.redraw();
  }

  /**
   * Highlights a File object and all of its parents if it contains patch data.
   */
  highlightIfPatched() {
    if (!this._file_tree) return;

    if (!this.node.hasOwnProperty('data') ||
        !this.node.data.hasOwnProperty('patch')) {
      return;
    }

    this._toggleFileClass(constants.PATCHED_NODE_CLASS, true);
    this._parents.forEach((parentFile) => {
      parentFile._toggleFileClass(constants.PATCHED_NODE_CLASS, true);
    });
    this._file_tree.redraw();
  }
}

export {File};
