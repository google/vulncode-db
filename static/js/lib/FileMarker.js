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

class FileMarker {
  constructor(
      file, markerClass, rowFrom, rowTo, columnFrom = 0, columnTo = 0) {
    this.file = file;
    this.class = markerClass;
    this.row_from = rowFrom;
    this.row_to = rowTo;
    this.column_from = columnFrom;
    this.column_to = columnTo;
    this.raw = null;
  }

  set annotation(newAnnotation) {
    this._annotation = newAnnotation;
  }

  Serialize() {
    const data = [
      this.class, this.row_from, this.row_to, this.column_from, this.column_to,
    ];
    return data.join('|');
  }
}

export {FileMarker};
