import os
from src import app

if __name__ == '__main__':
    # Em produção, use Gunicorn ao invés de executar diretamente
    # Comando: gunicorn --bind 0.0.0.0:5000 --workers 4 run:app

    # Para desenvolvimento local apenas
    debug_mode = os.getenv('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=5000, debug=debug_mode)
