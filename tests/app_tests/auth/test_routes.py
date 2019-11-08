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
import pytest
from app.auth.routes import google
from tests.conftest import as_user
from tests.conftest import regular_user_info


def test_authenticated_users_get_redirected_to_home(client_without_db):
    client = client_without_db
    as_user(client)

    resp = client.get('/auth/login')
    assert resp.status_code == 302
    assert resp.headers.get('Location') == 'http://localhost/'


def test_unauthenticated_users_get_redirected_to_oauth_consent_screen(client_without_db):
    client = client_without_db
    resp = client.get('/auth/login')
    assert resp.status_code == 302
    assert resp.headers.get('Location').startswith('https://accounts.google.com/o/oauth2/auth')


def test_logout_clears_the_session(client_without_db):
    client = client_without_db
    as_user(client)

    with client.session_transaction() as session:
        session['something_else'] = True
    resp = client.get('/auth/logout')
    assert resp.status_code == 302
    assert resp.headers.get('Location') == 'http://localhost/'
    with client.session_transaction() as session:
        assert 'user_info' not in session
        assert 'something_else' not in session


def test_authorization_callback_success(mocker, client_without_db):
    client = client_without_db
    mocker.patch('app.auth.routes.google.authorized_response')
    mocker.patch('app.auth.routes.google.get')

    google.authorized_response.return_value = {
        'access_token': 'TOKEN'
    }
    class Resp:
        data = regular_user_info()
    google.get.return_value = Resp()

    resp = client.get('/auth/authorized')

    assert resp.status_code == 302
    assert resp.headers.get('Location') == 'http://localhost/'

    assert google.authorized_response.called_once()
    assert google.get.called_once_with("getuserinfo", token='TOKEN')
    with client.session_transaction() as session:
        assert 'user_info' in session


def test_authorization_callback_access_denied(mocker, client_without_db):
    client = client_without_db
    mocker.patch('app.auth.routes.google.authorized_response')
    mocker.patch('app.auth.routes.google.get')
    google.authorized_response.return_value = None

    resp = client.get('/auth/authorized')

    assert resp.status_code == 200
    assert b'Access denied' in resp.data

    assert google.authorized_response.called_once()
    with client.session_transaction() as session:
        assert 'user_info' not in session


def test_authorization_callback_access_denied_with_reason(mocker, client_without_db):
    client = client_without_db
    mocker.patch('app.auth.routes.google.authorized_response')
    mocker.patch('app.auth.routes.google.get')
    google.authorized_response.return_value = None

    resp = client.get('/auth/authorized?error_reason=testing_unauthenticated&error_description=just+testing')

    assert resp.status_code == 200
    assert b'Access denied' in resp.data
    assert b'testing_unauthenticated' in resp.data
    assert b'just testing' in resp.data

    assert google.authorized_response.called_once()
    with client.session_transaction() as session:
        assert 'user_info' not in session


def test_authorization_callback_redirect(mocker, client_without_db):
    client = client_without_db
    mocker.patch('app.auth.routes.google.authorized_response')
    mocker.patch('app.auth.routes.google.get')

    google.authorized_response.return_value = {
        'access_token': 'TOKEN'
    }
    class Resp:
        data = regular_user_info()
    google.get.return_value = Resp()

    with client.session_transaction() as session:
        session['redirect_path'] = '/FOO'

    resp = client.get('/auth/authorized')

    assert resp.status_code == 302
    assert resp.headers.get('Location') == 'http://localhost/FOO'

    assert google.authorized_response.called_once()
    assert google.get.called_once_with("getuserinfo", token='TOKEN')
    with client.session_transaction() as session:
        assert 'user_info' in session
        assert 'redirect_path' not in session
