import time
import sys
from sqlalchemy import create_engine, text
from src import app, db

def wait_for_db(max_retries=30, delay=2):
    """Aguarda o PostgreSQL ficar pronto para aceitar conexões"""
    print("Aguardando PostgreSQL ficar disponível...")

    retries = 0
    while retries < max_retries:
        try:
            engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
            with engine.connect() as conn:
                conn.execute(text('SELECT 1'))
            print("PostgreSQL está pronto!")
            engine.dispose()
            return True
        except Exception as e:
            retries += 1
            print(f"Tentativa {retries}/{max_retries}: PostgreSQL ainda não está pronto. Aguardando {delay}s...")
            time.sleep(delay)

    print("Erro: PostgreSQL não ficou disponível a tempo!")
    return False

def init_database():
    """Inicializa o banco de dados criando todas as tabelas"""
    with app.app_context():
        print("Criando tabelas no banco de dados...")
        db.create_all()
        print("Tabelas criadas com sucesso!")

if __name__ == '__main__':
    if not wait_for_db():
        sys.exit(1)

    init_database()
