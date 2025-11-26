"""
Gerenciador de conexões com o banco de dados.
"""
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
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
        self.engine: Engine = self._get_sqlalchemy_engine()

    def _get_sqlalchemy_engine(self) -> Engine:
        """Cria engine do SQLAlchemy a partir da connection string da config."""
        return create_engine(self.config.get_connection_string())

    def test_connection(self) -> bool:
        """
        Testa a conexão com o banco de dados usando o engine SQLAlchemy.

        Returns:
            bool: True se a conexão foi bem-sucedida, False caso contrário.
        """
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            st.error(f"Erro na conexão com o banco: {e}")
            return False

    def execute_query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None
    ) -> pd.DataFrame:
        """
        Executa uma query e retorna um DataFrame, usando SQLAlchemy (sem warning do pandas).

        Args:
            query: Query SQL a ser executada.
                   Use parâmetros nomeados com :nome (ex.: :ano, :limit).
            params: Parâmetros para a query (dict), ex.: {"ano": 2019}.

        Returns:
            DataFrame com os resultados da query.
        """
        try:
            with self.engine.connect() as conn:
                if params is not None:
                    df = pd.read_sql_query(text(query), conn, params=params)
                else:
                    df = pd.read_sql_query(text(query), conn)
            return df
        except Exception as e:
            st.error(f"Erro ao executar query: {e}")
            return pd.DataFrame()

    def execute_non_query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Executa comandos que não retornam DataFrame (INSERT/UPDATE/DELETE),
        usando SQLAlchemy.
        """
        try:
            with self.engine.begin() as conn:  
                if params:
                    conn.execute(text(query), params)
                else:
                    conn.execute(text(query))
        except Exception as e:
            st.error(f"Erro ao executar comando no banco: {e}")


    def execute_query_sqlalchemy(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None
    ) -> pd.DataFrame:
        """
        Mantido por compatibilidade: usa internamente execute_query().
        """
        return self.execute_query(query, params)
