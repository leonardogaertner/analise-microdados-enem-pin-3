"""
Configuração centralizada do banco de dados.
"""

class DatabaseConfig:
    """Classe para armazenar configurações do banco de dados."""

    def __init__(self, user='postgres', password='postgres', host='localhost',
                 database='microdados', port=5432):
        self.user = user
        self.password = password
        self.host = host
        self.database = database
        self.port = port
        self.table_name = 'dados_enem_consolidado'

    def get_connection_string(self, driver='postgresql'):
        """Retorna a string de conexão para SQLAlchemy."""
        return f"{driver}://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"

    def get_psycopg2_params(self):
        """Retorna dicionário com parâmetros para psycopg2."""
        return {
            'host': self.host,
            'port': self.port,
            'user': self.user,
            'password': self.password,
            'dbname': self.database
        }
