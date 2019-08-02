# Copyright 2019 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Tests for the main.py script."""

import unittest
import mock

from lib.utils import get_file_contents


class TestUtils(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    @mock.patch("builtins.open", create=True)
    def test_get_file_contents(self, mock_open):
        dummy_data = "data"
        dummy_path = "/var/path/file.txt"

        mock_open.side_effect = [mock.mock_open(read_data=dummy_data).return_value]
        actual_data = get_file_contents(dummy_path)
        self.assertEqual(actual_data, dummy_data)
        mock_open.assert_called_once_with(dummy_path)


if __name__ == '__main__':
    unittest.main()
