# Copyright 2019 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import logging
from typing import Any, Dict, Optional

from urllib.parse import urljoin
from urllib.parse import urlparse

import jinja2
import pygments  # type: ignore
import pygments.formatters  # type: ignore
import pygments.lexers  # type: ignore

from flask import Flask
from flask import g
from flask import redirect
from flask import request
from flask import url_for
from flask_bootstrap import Bootstrap  # type: ignore
from flask_bouncer import can as bouncer_can  # type: ignore
from flask_debugtoolbar import DebugToolbarExtension  # type: ignore
from flask_debugtoolbar import module as debug_toolbar_bp
from flask_wtf.csrf import CSRFProtect  # type: ignore
from werkzeug import Response
from werkzeug.exceptions import Forbidden

import cfg

from app.admin.routes import bp as admin_bp
from app.api.routes import bp as api_bp
from app.api.v1.routes import bp as api_v1_bp
from app.auth.acls import bouncer
from app.auth.routes import bp as auth_bp
from app.auth.routes import is_admin
from app.auth.routes import oauth
from app.frontend.routes import bp as frontend_bp
from app.product.routes import bp as product_bp
from app.profile.routes import bp as profile_bp
from app.review.routes import bp as review_bp
from app.vcs_proxy.routes import bp as vcs_proxy_bp
from app.vulnerability.routes import bp as vuln_bp
from data.database import init_app as init_db
from data.models import Vulnerability


def create_app(test_config: Optional[Dict[str, Any]] = None, *, with_db: bool = True):
    """Application factory."""
    app = Flask("main", static_url_path="", template_folder=cfg.TEMPLATES_DIR)

    # Load the Flask configuration parameters from a global config file.
    app.config.from_object(cfg)

    if test_config:
        app.config.update(test_config)

    if app.debug:
        app.logger.propagate = True

    register_blueprints(app)
    register_extensions(app, test_config=test_config)
    register_route_checks(app)
    register_custom_helpers(app)

    app.jinja_env.lstrip_blocks = True
    app.jinja_env.trim_blocks = True

    if with_db:
        # Connect to the database and initialize SQLAlchemy.
        init_db(app)
    return app


def register_custom_helpers(app):
    def url_for_self(**args):
        return url_for(request.endpoint, **dict(request.view_args, **args))

    def url_for_no_querystring(endpoint, **args):
        full_url = url_for(endpoint, **args)
        return urljoin(full_url, urlparse(full_url).path)

    def is_admin_user():
        return bool(getattr(g, "user") and g.user.is_admin())

    def is_reviewer():
        return getattr(g, "user") and g.user.is_reviewer()

    def highlight(value, language="python"):
        formatter = pygments.formatters.HtmlFormatter(style="colorful")
        lexer = pygments.lexers.get_lexer_by_name(language)
        result = pygments.highlight(value, lexer, formatter)
        result += "<style>{}</style>".format(formatter.get_style_defs())
        result = jinja2.Markup(result)
        return result

    def can_do(action, subject):
        return bouncer_can(action, subject)

    def template_exists(name):
        return name in app.jinja_loader.list_templates()

    app.jinja_env.globals["url_for_self"] = url_for_self
    app.jinja_env.globals["template_exists"] = template_exists
    app.jinja_env.globals["is_admin"] = is_admin_user
    app.jinja_env.globals["is_reviewer"] = is_reviewer
    app.jinja_env.globals["url_for_no_querystring"] = url_for_no_querystring
    app.jinja_env.globals["vuln_helper"] = Vulnerability
    app.jinja_env.globals["can"] = can_do
    app.jinja_env.filters["highlight"] = highlight


def register_route_checks(app):
    def maintenance_check():
        if not cfg.MAINTENANCE_MODE:
            return None
        allowed_prefixes = ["/about", "/static", "/auth"]
        for prefix in allowed_prefixes:
            if request.path.startswith(prefix):
                return None
        if is_admin():
            return None
        if request.path != url_for("frontend.maintenance"):
            return redirect(url_for("frontend.maintenance"))

    @app.before_request
    def before_request():  # pylint: disable=unused-variable
        # Clear cache to always also reload Jinja template macros.
        if cfg.DEBUG:
            app.jinja_env.cache = {}
        return maintenance_check()


def register_extensions(app, test_config=None):
    """Register Flask extensions."""
    # We use flask_wtf and WTForm with bootstrap for quick form rendering.
    # Note: no JS/CSS or other resources are used from this package though.
    Bootstrap(app)

    public_paths = ["/favicon.ico", "/static/"]

    # Setup CSRF protection.
    csrf = CSRFProtect()
    csrf.init_app(app)

    # Setup OAuth.
    oauth.init_app(app)

    if not cfg.IS_PROD and not test_config:
        # Activate a port of the django-debug-toolbar for Flask applications.
        # Shows executed queries + their execution time, allows profiling and
        # more.
        # See: https://flask-debugtoolbar.readthedocs.io/en/latest/
        DebugToolbarExtension(app)
        csrf.exempt(debug_toolbar_bp)
        public_paths.append("/_debug_toolbar/")

    def always_authorize():
        for path in public_paths:
            if request.path.startswith(path):
                logging.warning(
                    "Bypassing ACL check for %s (matches %s)", request.path, path
                )
                request._authorized = True  # pylint: disable=protected-access
                return

    # Setup Acls
    app.before_request(always_authorize)
    bouncer.init_app(app)

    def check_or_404(response: Response):
        if response.status_code // 100 != 2:
            return response
        try:
            return bouncer.check_authorization(response)
        except Forbidden:
            logging.warning(
                "Automatically denied access to response %d of %s",
                response.status_code,
                request.path,
            )
            raise

    app.after_request(check_or_404)


def register_blueprints(app):
    """Register Flask blueprints."""
    app.register_blueprint(admin_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(api_v1_bp)
    app.register_blueprint(frontend_bp)
    app.register_blueprint(product_bp)
    app.register_blueprint(vcs_proxy_bp)
    app.register_blueprint(vuln_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(review_bp)
