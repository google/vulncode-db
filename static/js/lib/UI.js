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

const METADATA_DOM_ID = 'metadata';
const MARKER_ANNOTATION_DOM_ID = 'marker_annotation';
const PREVIOUS_COMMENT_BUTTON_DOM_ID = 'prev_comment';
const NEXT_COMMENT_BUTTON_DOM_ID = 'next_comment';
const PREVIOUS_PATCH_BUTTON_DOM_ID = 'prev_patch';
const NEXT_PATCH_BUTTON_DOM_ID = 'next_patch';
const TOGGLE_PATCH_VISIBILITY_DOM_ID = 'toggle_patch_visibility';
const EDITOR_MODE_DOM_ID = 'editor_mode';
const UI_ALERT_PLACEHOLDER_ID = 'alert_placeholder';
const UI_DIALOG_PLACEHOLDER_ID = 'dialog_placeholder';
const EDITOR_THEME_SELECTION_ID = 'editor_theme';

/**
 * This class is responsible for providing easy access to relevant UI elements.
 *
 * This includes metadata elements, notifications, the comment navigation and
 * more.
 */
class UI {
  constructor() {
    this._editor = null;
    this._sortable_comments = [];

    const editorMode =
        (constants.EDIT_MODE_ACTIVE ? 'Changes allowed' : 'View only');
    $('#' + EDITOR_MODE_DOM_ID).text(editorMode);

    this._sortable = $('#sortable');
    if (constants.EDIT_MODE_ACTIVE) {
      this._sortable.sortable();
      this._sortable.disableSelection();
      this._sortable.sortable({
        start: function(event, ui) {
          ui.item.startPos = ui.item.index();
        },
        stop: (event, ui) => this._sortableUpdateHandler(event, ui),
      });
    }

    this._patch_previous_button = $('#' + PREVIOUS_PATCH_BUTTON_DOM_ID);
    this._patch_next_button = $('#' + NEXT_PATCH_BUTTON_DOM_ID);
    this._patch_previous_button.click(() => this.gotoPreviousPatch());
    this._patch_next_button.click(() => this.gotoNextPatch());

    this._alert_placeholder = $('#' + UI_ALERT_PLACEHOLDER_ID);
    this._dialog_placeholder = $('#' + UI_DIALOG_PLACEHOLDER_ID);
    this._comment_previous_button = $('#' + PREVIOUS_COMMENT_BUTTON_DOM_ID);
    this._comment_next_button = $('#' + NEXT_COMMENT_BUTTON_DOM_ID);

    this._comment_previous_button.click(() => this.gotoPreviousComment());
    this._comment_next_button.click(() => this.gotoNextComment());

    this._toggle_patch_visibility_button =
        ($('#' + TOGGLE_PATCH_VISIBILITY_DOM_ID + ' button'));
    this._toggle_patch_visibility_button.click((event) => {
      const target = $(event.target);
      if (target.hasClass('locked_active') ||
          target.hasClass('unlocked_inactive')) {
        this._editor.displayPatches(true);
      } else {
        this._editor.displayPatches(false);
      }
      /* reverse locking status */
      this._toggle_patch_visibility_button.eq(0).toggleClass(
          'locked_inactive locked_active btn-info btn-light');
      this._toggle_patch_visibility_button.eq(1).toggleClass(
          'unlocked_inactive unlocked_active btn-light btn-info');
    });

    this.editor_theme_selection =
        $('#' + EDITOR_THEME_SELECTION_ID + ' :radio');
    this.editor_theme_selection.on('change', (el) => {
      const useTheme = el.target.id;
      this._editor.loadCustomMonacoTheme(useTheme);
    });

    this._current_comment = null;
    this._updateNavigation();
  }

  /**
   * Converts a given message to its markdown representation.
   * @param message
   * @return {*}
   */
  static toMarkdown(message) {
    if (typeof showdown !== 'undefined') {
      // Open all links in new tabs!
      showdown.extension('targetlink', function() {
        return [{
          type: 'html',
          filter: function(text) {
            return ('' + text).replace(/<a\s+href=/gi, '<a target="_blank" href=');
          },
        }];
      });
      const converter = new showdown.Converter({extensions: ['targetlink']});
      return converter.makeHtml(message);
    }
    return null;
  }

  /**
   * Displays a notification that can be clicked away.
   * @param message
   * @param type
   * @param dismissAfter dismiss the alert box after `dismissAfter`
   *     milliseconds.
   * @private
   */
  _showAlert(message, type, dismissAfter = 15000) {
    if (type !== 'danger' && type !== 'success' && type !== 'warning' &&
        type !== 'info') {
      console.log('Invalid type passed to _showAlert...');
      return;
    }
    const alertBox =
        $('<div>')
            .addClass('alert alert-' + type + ' alert-dismissible')
            .attr('role', 'alert');

    const closeBoxBtn =
        $('<button>')
            .addClass('close')
            .attr('type', 'button')
            .attr('data-dismiss', 'alert')
            .attr('aria-label', 'Close')
            .html($('<span aria-hidden="true"/>').html('&times;'));

    const dismissProgress = $('<div>').addClass('dismiss-progress');

    let perc = 100;
    const interval = 100.0;
    const step = 100.0 / (dismissAfter / interval);
    dismissProgress.css('width', perc + '%');
    const intv = window.setInterval(() => {
      perc -= step;
      if (perc < 0) {
        perc = 0;
        window.clearInterval(intv);
        this._alert_placeholder.html('');
      }
      dismissProgress.css('width', perc + '%');
    }, interval);

    closeBoxBtn.click(() => {
      window.clearInterval(intv);
    });

    const msg = $('<b>');
    msg.text(message);

    alertBox.append(msg);
    alertBox.append(closeBoxBtn);
    alertBox.append(dismissProgress);

    this._alert_placeholder.html('');
    this._alert_placeholder.append(alertBox);
  }

  showError(message) {
    this._showAlert(message, 'danger');
  }

  showSuccess(message) {
    this._showAlert(message, 'success');
  }

  showWarning(message) {
    this._showAlert(message, 'warning');
  }

  showInfo(message) {
    this._showAlert(message, 'info');
  }

  showBackdrop() {
    const backdrop = document.createElement('div');
    backdrop.id = 'backdrop';

    document.body.appendChild(backdrop);
    return backdrop;
  }

  showSpinner(text) {
    const backdrop = this.showBackdrop();

    const spinner = document.createElement('div');
    spinner.id = 'spinner';
    backdrop.appendChild(spinner);

    const p = document.createElement('p');
    p.className = 'animate-dots';
    p.textContent = text;
    spinner.appendChild(p);

    for (let i = 0; i < 3; i++) {
      const dot = document.createElement('span');
      dot.textContent = '.';
      p.appendChild(dot);
    }
  }

  hideSpinner() {
    this.hideBackdrop();
  }

  hideBackdrop() {
    const backdrop = document.getElementById('backdrop');
    if (backdrop) {
      backdrop.parentElement.removeChild(backdrop);
    }
  }

  /**
   * Displays a JQuery Modal confirmation box.
   * @param message
   * @param callback
   */
  confirmYesNo(message, callback) {
    this._dialog_placeholder.dialog({
      autoOpen: false,
      modal: true,
      title: 'Please confirm.',
      buttons: [
        {
          text: 'Yes',
          click: function() {
            callback();
            $(this).dialog('close');
          },
          class: 'btn btn-sm btn-primary',
        },
        {
          text: 'No',
          click: function() {
            $(this).dialog('close');
          },
          class: 'btn btn-sm btn-secondary',
        },
      ],
    });
    this._dialog_placeholder.dialog('widget')
        .find('.ui-dialog-titlebar-close')
        .hide();
    this._dialog_placeholder.dialog('widget')
        .find('.ui-icon ui-icon-closethick')
        .hide();

    const alertBox = $('<div>');
    alertBox.addClass('alert');
    alertBox.attr('role', 'alert');
    const msg = $('<b>');
    msg.text(message);
    alertBox.append(msg);
    this._dialog_placeholder.html('');
    this._dialog_placeholder.append(alertBox);
    this._dialog_placeholder.dialog('open');
  }

  getCommentSortPos(comment) {
    return this._sortable_comments.indexOf(comment);
  }

  _sortableUpdateHandler(event, ui) {
    const startPos = ui.item.startPos;
    const endPos = ui.item.index();
    const comment = this._sortable_comments[startPos];
    this._sortable_comments.splice(startPos, 1);
    this._sortable_comments.splice(endPos, 0, comment);
    this._updateNavigation();
  }

  _updateNavigation() {
    if (this._sortable_comments.length === 0) {
      this._comment_previous_button.prop('disabled', true);
      this._comment_next_button.prop('disabled', true);
      return;
    }
    if (this._sortable_comments.length > 0) {
      this._comment_next_button.prop('disabled', false);
    }

    if (!this._current_comment) return;
    const currentCommentPos =
        this._sortable_comments.indexOf(this._current_comment);
    if (currentCommentPos < 0) {
      console.log('Can\'t find pos. This shouldn\'t happen!');
    }

    this._comment_previous_button.prop('disabled', false);
    if (currentCommentPos === 0) {
      this._comment_previous_button.prop('disabled', true);
    }

    this._comment_next_button.prop('disabled', false);
    if (this._sortable_comments.length > 1 &&
        currentCommentPos === this._sortable_comments.length - 1) {
      this._comment_next_button.prop('disabled', true);
    }


    this._sortable_comments.forEach((comment) => {
      comment.raw_sortable.css('background-color', '');
    });
    this._current_comment.raw_sortable.css('background-color', 'green');
  }

  _chooseAndNavigateToComment(comment) {
    const newCommentPos =
        this._sortable_comments.indexOf(this._current_comment);
    if (newCommentPos < 0) console.log('Can\'t find given comment :/.');

    this._current_comment = this._sortable_comments[newCommentPos];
    this.navigateToComment(this._current_comment);
  }

  _chooseAndNavigateToCommentOffset(offset) {
    const currentCommentPos =
        this._sortable_comments.indexOf(this._current_comment);
    const newPos = currentCommentPos + offset;
    if (typeof this._sortable_comments[newPos] === 'undefined') return;
    this._current_comment = this._sortable_comments[newPos];
    this.navigateToComment(this._current_comment);
  }

  gotoPreviousPatch() {
    if (!this._editor) return;
    this._editor.gotoPreviousPatch();
  }

  gotoNextPatch() {
    if (!this._editor) return;

    this._editor.gotoNextPatch();
  }

  gotoPreviousComment() {
    if (this._sortable_comments.length === 0) return;
    if (!this._current_comment) return;
    this._chooseAndNavigateToCommentOffset(-1);
    this._updateNavigation();
  }

  gotoNextComment() {
    if (this._sortable_comments.length === 0) return;

    if (!this._current_comment) {
      this._current_comment = this._sortable_comments[0];
      this.navigateToComment(this._current_comment);
      this._updateNavigation();
      return;
    }
    this._chooseAndNavigateToCommentOffset(+1);
    this._updateNavigation();
  }

  _annotationHandler(e) {
    const content = e.target.value;
    if (this._editor && this._editor.annotationCallback) {
      this._editor.annotationCallback(content);
    }
  }

  registerEditor(editorObj) {
    this._editor = editorObj;
  }

  removeSortableItem(comment) {
    if (!comment.raw_sortable) return false;

    const pos = this._sortable_comments.indexOf(comment);
    if (pos < 0) return false;
    this._sortable_comments.splice(pos, 1);
    comment.raw_sortable.remove();
    comment.raw_sortable = null;

    if (this._current_comment === comment) {
      if (typeof this._sortable_comments[pos - 1] !== 'undefined') {
        this._current_comment = this._sortable_comments[pos - 1];
      } else {
        this._current_comment = null;
      }
      this._updateNavigation();
    }
    return true;
  }

  getCurrentFilter() {
    const targetEl = $('input[name=\'jstree_filter\']:checked')[0];
    return targetEl.id.replace('jstree_filter_', '');
  }

  navigateToComment(comment) {
    this._editor.navigateTo(comment.file, comment.row_from);
  }

  /**
   * Adds a drag & droppable item to the comment navigation.
   * @param newComment
   * @return {*|jQuery|HTMLElement}
   */
  addSortableItem(newComment) {
    let commentSortableText = newComment.file.name;
    let range = newComment.row_from + 1;
    if (newComment.row_to && newComment.row_from !== newComment.row_to) {
      range += '-' + (newComment.row_to + 1);
    }
    commentSortableText += ':' + range;

    const parentUl = this._sortable;

    const listItem = $('<li>');
    listItem.addClass('ui-state-default');

    if (constants.EDIT_MODE_ACTIVE) {
      const spanItem = $('<span>');
      spanItem.addClass('ui-icon ui-icon-arrowthick-2-n-s');
      listItem.append(spanItem);
    }

    const textItem = $('<b>');
    textItem.text(commentSortableText);
    listItem.append(textItem);


    let gotoItem = null;
    if (constants.EDIT_MODE_ACTIVE) {
      gotoItem = $('<pre>');
      gotoItem.html('<a>(goto)</a>');
      listItem.append(gotoItem);
    } else {
      gotoItem = textItem;
    }
    gotoItem.css({'cursor': 'pointer', 'display': 'inline'});
    $(gotoItem).on('click', (e) => {
      this._current_comment = newComment;
      this.navigateToComment(newComment);
      this._updateNavigation();
    });

    if (constants.EDIT_MODE_ACTIVE) {
      const removeItem = $('<pre>');
      removeItem.text('(remove)');
      removeItem.css({'cursor': 'pointer', 'display': 'inline'});
      $(removeItem).on('click', (e) => {
        this._editor.removeComment(newComment, newComment.file);
      });
      listItem.append(removeItem);
    }

    parentUl.append(listItem);

    newComment.raw_sortable = listItem;
    // Restore the comment's sort order if it has one set.
    this._sortable_comments.push(newComment);

    if (this._current_comment === null) this._updateNavigation();

    return listItem;
  }

  updateMarkerAnnotation(newText) {
    $('#' + MARKER_ANNOTATION_DOM_ID).val(newText);
  }

  getMarkerAnnotation() {
    return $('#' + MARKER_ANNOTATION_DOM_ID).val();
  }

  /**
   * Updates fields like the number of available files in metadata sections.
   * @param newMetadata
   */
  updateMetadata(newMetadata) {
    const fileTreeMetadata = newMetadata['file_tree'];
    if (fileTreeMetadata) {
      $('#num_files').text(fileTreeMetadata['num_files']);
    }

    const editorMetadata = newMetadata['editor'];
    // TODO: Decide if / where we want to display the number of modified lines.
    // const sectionsEl = $('#' + METADATA_DOM_ID + ' #vulnerable_sections');
    // sectionsEl.text(editorMetadata['vuln_markers'].length);

    const editorSettings = window.EDITOR_SETTINGS;
    if (editorSettings) {
      $('#open_file_path').text('./' + editorMetadata['open_file_path']);
      const fileUrl = (
        editorSettings.file_url + editorMetadata['open_file_path']);
      $('#open_file_path').attr('href', fileUrl);
    }
  }
}

export {UI};
