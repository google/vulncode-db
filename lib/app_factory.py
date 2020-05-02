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
from app.api.routes import bp as api_bp
from app.api.v1.routes import bp as api_v1_bp
from app.auth.routes import bp as auth_bp
from app.auth.routes import is_admin
from app.auth.routes import oauth
from app.frontend.routes import bp as frontend_bp
from app.product.routes import bp as product_bp
from app.vcs_proxy.routes import bp as vcs_proxy_bp
from app.vulnerability.routes import bp as vuln_bp
import cfg
from data.database import init_app as init_db
from flask import Flask
from flask import redirect
from flask import request
from flask import url_for
from flask_bootstrap import Bootstrap  # type: ignore
from flask_debugtoolbar import DebugToolbarExtension  # type: ignore
from flask_wtf.csrf import CSRFProtect  # type: ignore


def create_app(test_config=None):
    """Application factory."""
    app = Flask('main', static_url_path='', template_folder=cfg.TEMPLATES_DIR)

    # Load the Flask configuration parameters from a global config file.
    app.config.from_object(cfg)

    if test_config:
        app.config.update(test_config)

    register_blueprints(app)
    register_extensions(app, test_config=test_config)
    register_route_checks(app)
    register_custom_helpers(app)

    # Connect to the database and initialize SQLAlchemy.
    init_db(app)
    return app


def register_custom_helpers(app):
    def url_for_self(**args):
        return url_for(request.endpoint, **dict(request.view_args, **args))

    app.jinja_env.globals['url_for_self'] = url_for_self


def register_route_checks(app):
    def maintenance_check():
        if not cfg.MAINTENANCE_MODE:
            return None
        allowed_prefixes = ['/about', '/static', '/auth']
        for prefix in allowed_prefixes:
            if request.path.startswith(prefix):
                return None
        if is_admin():
            return None
        if request.path != url_for('frontend.maintenance'):
            return redirect(url_for('frontend.maintenance'))

    @app.before_request
    def before_request():
        # Clear cache to always also reload Jinja template macros.
        if cfg.DEBUG:
            app.jinja_env.cache = {}
        return maintenance_check()


def register_extensions(app, test_config=None):
    """Register Flask extensions."""
    # We use flask_wtf and WTForm with bootstrap for quick form rendering.
    # Note: no JS/CSS or other resources are used from this package though.
    Bootstrap(app)

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


def register_blueprints(app):
    """Register Flask blueprints."""
    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(api_v1_bp)
    app.register_blueprint(frontend_bp)
    app.register_blueprint(product_bp)
    app.register_blueprint(vcs_proxy_bp)
    app.register_blueprint(vuln_bp)
