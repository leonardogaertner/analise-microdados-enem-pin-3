"""
Gerenciador de conexões com o banco de dados.
"""
import pandas as pd
import psycopg2
from psycopg2 import sql
from sqlalchemy import create_engine
from contextlib import closing
from typing import Optional, Dict, Any
import streamlit as st


class DatabaseManager:
    """Classe responsável por gerenciar conexões e operações com o banco de dados."""

    def __init__(self, config):
        """
        Inicializa o gerenciador de banco de dados.

        Args:
            config: Instância de DatabaseConfig com as configurações de conexão.
        """
        self.config = config

    def test_connection(self) -> bool:
        """
        Testa a conexão com o banco de dados.

        Returns:
            bool: True se a conexão foi bem-sucedida, False caso contrário.
        """
        try:
            with closing(self._connect_psycopg2()) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1;")
                    return True
        except Exception as e:
            st.error(f"Erro na conexão com o banco: {e}")
            return False

    def _connect_psycopg2(self):
        """Cria conexão usando psycopg2."""
        return psycopg2.connect(**self.config.get_psycopg2_params())

    def _get_sqlalchemy_engine(self):
        """Cria engine do SQLAlchemy."""
        return create_engine(self.config.get_connection_string())

    def execute_query(self, query: str, params: Optional[list] = None) -> pd.DataFrame:
        """
        Executa uma query e retorna um DataFrame.

        Args:
            query: Query SQL a ser executada.
            params: Parâmetros para a query (opcional).

        Returns:
            DataFrame com os resultados da query.
        """
        try:
            with closing(self._connect_psycopg2()) as conn:
                df = pd.read_sql_query(query, conn, params=params)
            return df
        except Exception as e:
            st.error(f"Erro ao executar query: {e}")
            return pd.DataFrame()

    def execute_query_sqlalchemy(self, query: str) -> pd.DataFrame:
        """
        Executa uma query usando SQLAlchemy e retorna um DataFrame.

        Args:
            query: Query SQL a ser executada.

        Returns:
            DataFrame com os resultados da query.
        """
        try:
            engine = self._get_sqlalchemy_engine()
            df = pd.read_sql_query(query, engine)
            engine.dispose()
            return df
        except Exception as e:
            st.error(f"Erro ao executar query: {e}")
            return pd.DataFrame()
