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

export const ERROR_MARKER_CLASS = 'errorMarker';
export const MARKER_HIGHLIGHT_CLASS = 'highlightMarker';
export const IRRELEVANT_MARKER_CLASS = 'irrelevantMarker';
export const PATCHED_NODE_CLASS = 'patched_node_class';
export const VULNERABLE_NODE_CLASS = 'vulnerable_node_class';
export const VULNERABLE_MARKER_CLASS = 'vulnerableMarker';
export const SECTION_MARKER_CLASS = 'sectionMarker';


// Go into view only mode if no valid editor URL is present.
export const EDIT_MODE_ACTIVE = window.location.href.includes('/editor');
