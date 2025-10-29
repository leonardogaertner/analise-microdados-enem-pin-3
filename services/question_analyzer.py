"""
Analisador de questões do ENEM.
"""
import pandas as pd
import streamlit as st
from typing import Tuple


class QuestionAnalyzer:
    """Classe responsável por análises de questões do ENEM."""

    def __init__(self, db_manager):
        """
        Inicializa o analisador de questões.

        Args:
            db_manager: Instância de DatabaseManager para acesso ao banco.
        """
        self.db_manager = db_manager

    @st.cache_data
    def load_questions(_self) -> pd.DataFrame:
        """
        Carrega todas as questões do ENEM do banco de dados.

        Returns:
            DataFrame com as questões.
        """
        query = """
            SELECT
                ano,
                cor,
                numero_questao,
                gabarito,
                sigla_area,
                area,
                lingua,
                habilidade,
                item_abandonado,
                motivo_abandono,
                item_adaptado,
                parametro_a,
                parametro_b,
                parametro_c,
                itens,
                provas,
                versao_digital
            FROM questoes_enem
            ORDER BY ano, cor, numero_questao
        """
        df = _self.db_manager.execute_query_sqlalchemy(query)

        # Calcular taxa de acerto em porcentagem
        if not df.empty:
            df['taxa_acerto_pct'] = 0.0

        return df

    def filter_by_year(self, df: pd.DataFrame, year: int) -> pd.DataFrame:
        """Filtra questões por ano."""
        return df[df['ano'] == year].copy()

    def filter_by_color(self, df: pd.DataFrame, color: str) -> pd.DataFrame:
        """Filtra questões por cor da prova."""
        return df[df['cor'] == color].copy()

    def filter_by_area(self, df: pd.DataFrame, area: str) -> pd.DataFrame:
        """Filtra questões por área."""
        return df[df['area'] == area].copy()

    def filter_by_success_rate(self, df: pd.DataFrame,
                               min_rate: float, max_rate: float) -> pd.DataFrame:
        """
        Filtra questões por taxa de acerto.

        Args:
            df: DataFrame com as questões.
            min_rate: Taxa mínima de acerto (%).
            max_rate: Taxa máxima de acerto (%).

        Returns:
            DataFrame filtrado.
        """
        return df[
            (df['taxa_acerto_pct'] >= min_rate) &
            (df['taxa_acerto_pct'] <= max_rate)
        ].copy()

    def get_statistics(self, df: pd.DataFrame) -> dict:
        """
        Calcula estatísticas das questões.

        Args:
            df: DataFrame com as questões.

        Returns:
            Dicionário com as estatísticas.
        """
        return {
            'total_questoes': len(df),
            'itens_abandonados': int(df['item_abandonado'].sum()) if pd.notna(df['item_abandonado'].sum()) else 0,
            'media_dificuldade': df['parametro_b'].mean() if pd.notna(df['parametro_b'].mean()) else None,
            'taxa_acerto_media': df['taxa_acerto_pct'].mean() if pd.notna(df['taxa_acerto_pct'].mean()) else None
        }

    def get_tri_statistics(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calcula estatísticas dos parâmetros TRI.

        Args:
            df: DataFrame com as questões.

        Returns:
            DataFrame com estatísticas dos parâmetros TRI.
        """
        stats = pd.DataFrame({
            'Parâmetro': ['Discriminação (A)', 'Dificuldade (B)', 'Acerto Casual (C)'],
            'Média': [
                df['parametro_a'].mean(),
                df['parametro_b'].mean(),
                df['parametro_c'].mean()
            ],
            'Mediana': [
                df['parametro_a'].median(),
                df['parametro_b'].median(),
                df['parametro_c'].median()
            ],
            'Desvio Padrão': [
                df['parametro_a'].std(),
                df['parametro_b'].std(),
                df['parametro_c'].std()
            ]
        })
        return stats

    def get_top_skills(self, df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
        """
        Retorna as habilidades mais cobradas.

        Args:
            df: DataFrame com as questões.
            n: Número de habilidades a retornar.

        Returns:
            DataFrame com as top habilidades.
        """
        habilidades = df['habilidade'].value_counts().head(n).reset_index()
        habilidades.columns = ['habilidade', 'Quantidade']
        return habilidades

    def get_abandoned_questions(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Retorna questões abandonadas.

        Args:
            df: DataFrame com as questões.

        Returns:
            DataFrame com questões abandonadas.
        """
        return df[df['item_abandonado'] == 1][[
            'numero_questao', 'gabarito', 'habilidade', 'motivo_abandono'
        ]]

    def get_answer_distribution(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Retorna distribuição de gabaritos.

        Args:
            df: DataFrame com as questões.

        Returns:
            DataFrame com distribuição de gabaritos.
        """
        gabarito_counts = df['gabarito'].value_counts().reset_index()
        gabarito_counts.columns = ['Alternativa', 'Quantidade']
        return gabarito_counts
