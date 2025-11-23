from flask import request
from functools import wraps
from flask import current_app as app

def verify_token(f):
    """
    Decorator para verificar token de autenticação.
    Retorna dicionário simples para compatibilidade com Flask-RESTX.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(" ")[1]

        if not token or token != app.config['SECRET_KEY']:
            return {'message': 'Token inválido ou ausente!'}, 403

        return f(*args, **kwargs)
    return decorated_function