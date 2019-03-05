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

class FileComment {
  constructor(
      file, rowFrom, rowTo, text, sortPos = -1, creator = null,
      revision = 0) {
    this.file = file;
    this.row_from = rowFrom;
    this.row_to = rowTo;
    this.text = text;
    this.sort_pos = sortPos;
    this.creator = creator;
    this.revision = revision;
    this.raw_widget = null;
    this.raw_section_marker = null;
    this.raw_sortable = null;
  }
}

export {FileComment};
