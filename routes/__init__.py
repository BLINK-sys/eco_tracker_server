from flask import Blueprint
from .auth import auth_bp
from .locations import locations_bp
from .containers import containers_bp
from .reports import reports_bp
from .companies import companies_bp


def register_blueprints(app):
    """Регистрирует все blueprints в приложении"""
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(locations_bp, url_prefix='/api/locations')
    app.register_blueprint(containers_bp, url_prefix='/api/containers')
    app.register_blueprint(reports_bp, url_prefix='/api/reports')
    app.register_blueprint(companies_bp, url_prefix='/api/companies')

