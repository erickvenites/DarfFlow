from flask import request,jsonify
from functools import wraps
from flask import current_app as app
def verify_token(f):
    @wraps(f)
    def decorated_function(*args,**kwargs):
        token=None
        if 'Authorization' in request.headers:
            token=request.headers['Authorization'].split(" ")[1]

        if not token or token !=app.config['SECRET_KEY']:
            return jsonify({'message': 'Token inváido ou ausente!'}),403
        
        return f(*args,**kwargs)
    return decorated_function