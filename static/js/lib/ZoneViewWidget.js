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

const WIDGET_ID = 'vs.editor.contrib.zoneWidget';

const defaultColor = 'rgb(0, 122, 204)';
const defaultOptions = {
  showArrow: false,
  showFrame: true,
  className: '',
  frameColor: defaultColor,
  arrowColor: defaultColor,
  keepEditorSelection: false,
  glyphClassName: '',
};

export class OverlayWidgetDelegate {
  constructor(id, domNode) {
    this._id = id;
    this._domNode = domNode;
  }

  getId() {
    return this._id;
  }

  getDomNode() {
    return this._domNode;
  }

  getPosition() {
    return null;
  }
}

/**
 * Base class for all line widgets. Based on the ZoneViewWidget of VS code.
 * (mostly c&p with adoptions to the diff mode).
 */
export class ZoneViewWidget {
  /**
   * @param {!monaco.editor.IEditor} viewZoneEditor
   * @param overlayEditor
   * @param options
   */
  constructor(viewZoneEditor, overlayEditor, options) {
    this._disposables = [];
    this._positionMarkerId = [];
    this._isShowing = false;
    this.options = Object.assign({}, defaultOptions, options || {});
    this.viewZoneEditor = viewZoneEditor;
    this.overlayEditor = overlayEditor;
    this.domNode = document.createElement('div');
    this._disposables.push(viewZoneEditor.onDidLayoutChange((info) => {
      const width = this._getWidth(info);
      this.domNode.style.width = width + 'px';
      this.domNode.style.left = this._getLeft(info) + 'px';
      this._onWidth(width);
    }));
  }

  dispose() {
    this._disposables.forEach((d) => d.dispose());

    if (this._overlayWidget) {
      this.overlayEditor.removeOverlayWidget(this._overlayWidget);
      this._overlayWidget = null;
    }

    if (this._viewZone) {
      this.viewZoneEditor.changeViewZones((accessor) => {
        accessor.removeZone(this._viewZone.id);
        this._viewZone = null;
      });
    }

    this.viewZoneEditor.deltaDecorations(this._positionMarkerId, []);
    this._positionMarkerId = [];
  }

  _getWidth(info) {
    return info.width - info.minimapWidth - info.verticalScrollbarWidth;
  }

  _getLeft(info) {
    // If minimap is to the left, we move beyond it
    if (info.minimapWidth > 0 && info.minimapLeft === 0) {
      return info.minimapWidth;
    }
    return 0;
  }

  create() {
    this.domNode.classList.add('zone-widget');
    if (this.options.className) {
      this.domNode.classList.add(this.options.className);
    }

    this.container = document.createElement('div');
    this.container.classList.add('zone-widget-container');
    this.domNode.appendChild(this.container);
    if (this.options.showArrow && false) {
      this._arrow = new Arrow(this.overlayEditor);
      this._disposables.push(this._arrow);
    }
    this._fillContainer(this.container);
    this._applyStyles();
  }

  _applyStyles() {
    if (this.container) {
      const frameColor = this.options.frameColor.toString();
      this.container.style.borderTopColor = frameColor;
      this.container.style.borderBottomColor = frameColor;
    }
    if (this._arrow) {
      const arrowColor = this.options.arrowColor.toString();
      this._arrow.color = arrowColor;
    }
  }

  style(styles) {
    if (styles.frameColor) {
      this.options.frameColor = styles.frameColor;
    }
    if (styles.arrowColor) {
      this.options.arrowColor = styles.arrowColor;
    }
    this._applyStyles();
  }

  _onViewZoneTop(top) {
    this.domNode.style.top = top + 'px';
  }

  _onViewZoneHeight(height) {
    this.domNode.style.height = `${height}px`;

    const containerHeight = height - this._decoratingElementsHeight();
    this.container.style.height = `${containerHeight}px`;
    const layoutInfo = this.viewZoneEditor.getLayoutInfo();
    this._doLayout(containerHeight, this._getWidth(layoutInfo));
  }

  get position() {
    const [id] = this._positionMarkerId;
    if (!id) {
      return undefined;
    }
    const range = this.viewZoneEditor.getModel().getDecorationRange(id);
    if (!range) {
      return undefined;
    }
    return range.getStartPosition();
  }

  show(rangeOrPos, heightInLines) {
    const range = monaco.Range.isIRange(rangeOrPos) ?
      rangeOrPos :
      new monaco.Range(
          rangeOrPos.lineNumber, rangeOrPos.column, rangeOrPos.lineNumber,
          rangeOrPos.column);

    this._isShowing = true;
    this._showImpl(range, heightInLines);
    this._isShowing = false;
    this._positionMarkerId = this.viewZoneEditor.deltaDecorations(
        this._positionMarkerId, [{
          range,
          options: {
            glyphMarginClassName: this.options.glyphClassName,
            overviewRuler: true,
          },
        }]);
  }

  hide() {
    if (this._viewZone) {
      this.viewZoneEditor.changeViewZones((accessor) => {
        accessor.removeZone(this._viewZone.id);
      });
      this._viewZone = null;
    }
    if (this._overlayWidget) {
      this.overlayEditor.removeOverlayWidget(this._overlayWidget);
      this._overlayWidget = null;
    }
    if (this._arrow) {
      this._arrow.hide();
    }
  }

  _decoratingElementsHeight() {
    const lineHeight = this.viewZoneEditor.getOption(monaco.editor.EditorOption.lineHeight);
    let result = 0;

    if (this.options.showArrow) {
      const arrowHeight = Math.round(lineHeight / 3);
      result += 2 * arrowHeight;
    }

    if (this.options.showFrame) {
      const frameThickness = Math.round(lineHeight / 9);
      result += 2 * frameThickness;
    }

    return result;
  }

  _showImpl(where, heightInLines) {
    const position = {
      lineNumber: where.startLineNumber,
      column: where.startColumn,
    };

    const layoutInfo = this.overlayEditor.getLayoutInfo();
    const width = this._getWidth(layoutInfo);
    this.domNode.style.width = `${width}px`;
    this.domNode.style.left = this._getLeft(layoutInfo) + 'px';

    // Render the widget as zone (rendering) and widget (lifecycle)
    const viewZoneDomNode = document.createElement('div');
    viewZoneDomNode.style.overflow = 'hidden';
    const lineHeight = this.viewZoneEditor.getOption(monaco.editor.EditorOption.lineHeight);

    // adjust heightInLines to viewport
    const maxHeightInLines =
      (this.viewZoneEditor.getLayoutInfo().height / lineHeight) * .8;
    if (heightInLines >= maxHeightInLines) {
      heightInLines = maxHeightInLines;
    }

    let arrowHeight = 0;
    let frameThickness = 0;

    // Render the arrow one 1/3 of an editor line height
    if (this.options.showArrow) {
      arrowHeight = Math.round(lineHeight / 3);
      this._arrow.height = arrowHeight;
      this._arrow.show(position);
    }

    // Render the frame as 1/9 of an editor line height
    if (this.options.showFrame) {
      frameThickness = Math.round(lineHeight / 9);
    }

    // insert zone widget
    this.viewZoneEditor.changeViewZones((accessor) => {
      if (this._viewZone) {
        accessor.removeZone(this._viewZone.id);
      }
      if (this._overlayWidget) {
        this.overlayEditor.removeOverlayWidget(this._overlayWidget);
        this._overlayWidget = null;
      }
      this.domNode.style.top = '-1000px';
      this._viewZone = {
        domNode: viewZoneDomNode,
        afterLineNumber: position.lineNumber,
        afterColumn: position.column,
        heightInLines: heightInLines,
        onDomNodeTop: (top) => this._onViewZoneTop(top),
        onComputedHeight: (height) => this._onViewZoneHeight(height),
      };
      this._viewZone.id = accessor.addZone(this._viewZone);
      this._overlayWidget = new OverlayWidgetDelegate(
          WIDGET_ID + this._viewZone.id, this.domNode);
      this.overlayEditor.addOverlayWidget(this._overlayWidget);
    });

    if (this.options.showFrame) {
      const width =
        this.options.frameWidth ? this.options.frameWidth : frameThickness;
      this.container.style.borderTopWidth = width + 'px';
      this.container.style.borderBottomWidth = width + 'px';
    }

    const containerHeight =
      heightInLines * lineHeight - this._decoratingElementsHeight();
    this.container.style.top = arrowHeight + 'px';
    this.container.style.height = containerHeight + 'px';
    this.container.style.overflow = 'hidden';


    this._doLayout(containerHeight, width);

    if (!this.options.keepEditorSelection) {
      this.overlayEditor.setSelection(where);
    }

    // Reveal the line above or below the zone widget, to get the zone widget in
    // the viewport
    const revealLineNumber = Math.min(
        this.viewZoneEditor.getModel().getLineCount(),
        Math.max(1, where.endLineNumber + 1));
    this.revealLine(revealLineNumber);
  }

  revealLine(lineNumber) {
    this.viewZoneEditor.revealLine(lineNumber, monaco.editor.ScrollType.Smooth);
  }

  setCssClass(className, classToReplace) {
    if (classToReplace) {
      this.container.classList.remove(classToReplace);
    }

    this.container.classList.add(className);
  }

  _fillContainer(container) {
    // implement in subclass
  }

  _onWidth(widthInPixel) {
    // implement in subclass
  }

  _doLayout(heightInPixel, widthInPixel) {
    // implement in subclass
  }

  _relayout(newHeightInLines) {
    if (this._viewZone.heightInLines !== newHeightInLines) {
      this.viewZoneEditor.changeViewZones((accessor) => {
        this._viewZone.heightInLines = newHeightInLines;
        accessor.layoutZone(this._viewZone.id);
      });
    }
  }

  _calcHeightInLines(height) {
    const lines = height / this.viewZoneEditor.getOption(monaco.editor.EditorOption.lineHeight);
    return Math.floor(lines);
  }

  getHorizontalSashLeft() {
    return 0;
  }

  getHorizontalSashTop() {
    return parseInt(this.domNode.style.height) -
      (this._decoratingElementsHeight() / 2);
  }

  getHorizontalSashWidth() {
    const layoutInfo = this.viewZoneEditor.getLayoutInfo();
    return layoutInfo.width - layoutInfo.minimapWidth;
  }
}
