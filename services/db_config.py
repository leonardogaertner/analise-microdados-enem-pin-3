# config/db_config.py
import os
from dataclasses import dataclass

@dataclass
class DatabaseConfig:
    host: str = os.getenv("DB_HOST", "localhost")
    port: int = int(os.getenv("DB_PORT", 5432))
    database: str = os.getenv("DB_NAME", "enem")
    user: str = os.getenv("DB_USER", "postgres")
    password: str = os.getenv("DB_PASSWORD", "postgres")

    def sqlalchemy_url(self) -> str:
        """
        Monta a URL de conexão no formato aceito pelo SQLAlchemy.
        Exemplo: postgresql+psycopg2://user:pass@host:port/dbname
        """
        return (
            f"postgresql+psycopg2://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.database}"
        )
