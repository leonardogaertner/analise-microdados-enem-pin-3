"""
Analisador de questões do ENEM com cálculo de taxas de acerto reais.
"""
import pandas as pd
import streamlit as st
from typing import Tuple, Optional


class QuestionAnalyzer:
    """Classe responsável por análises de questões do ENEM com dados reais de participantes."""

    def __init__(self, db_manager):
        """
        Inicializa o analisador de questões.

        Args:
            db_manager: Instância de DatabaseManager para acesso ao banco.
        """
        self.db_manager = db_manager
        self.area_to_respostas = {
            'CH': 'TX_RESPOSTAS_CH',
            'CN': 'TX_RESPOSTAS_CN',
            'LC': 'TX_RESPOSTAS_LC',
            'MT': 'TX_RESPOSTAS_MT'
        }
        self.area_to_gabarito = {
            'CH': 'TX_GABARITO_CH',
            'CN': 'TX_GABARITO_CN',
            'LC': 'TX_GABARITO_LC',
            'MT': 'TX_GABARITO_MT'
        }

    @staticmethod
    def _normalizar_alternativa(valor):
        """
        Converte valores como '1', '2', 'A*', ' a)', '.', ' ' etc. em 'A'...'E'.
        Retorna None se não conseguir normalizar (ou se for branco/ausente).
        """
        if pd.isna(valor):
            return None

        s = str(valor).strip().upper()

        if s in {'.', '', ' ', '-', '_'}:
            return None

        if s in {'1', '2', '3', '4', '5'}:
            return "ABCDE"[int(s) - 1]

        somente_letras = ''.join(ch for ch in s if ch in 'ABCDE')
        if somente_letras:
            return somente_letras[0]

        return None

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
        
        if not df.empty:
            df['taxa_acerto_pct'] = 0.0
            df['taxa_acerto_real'] = 0.0
            df['participantes_amostra'] = 0

        return df

    def load_participants_for_calculation(
        _self,
        ano: int,
        cor_prova: str = None,
        limit: int = 5000
    ) -> pd.DataFrame:
        """
        Carrega dados dos participantes para cálculo de taxas de acerto.

        Args:
            ano: Ano da prova
            cor_prova: Cor da prova 
            limit: Limite de participantes para análise

        Returns:
            DataFrame com dados dos participantes
        """
        try:
            if cor_prova:
                query = f"""
                SELECT 
                    "TX_RESPOSTAS_CH", "TX_RESPOSTAS_CN", "TX_RESPOSTAS_LC", "TX_RESPOSTAS_MT",
                    "TX_GABARITO_CH", "TX_GABARITO_CN", "TX_GABARITO_LC", "TX_GABARITO_MT",
                    "CO_PROVA_CH", "CO_PROVA_CN", "CO_PROVA_LC", "CO_PROVA_MT"
                FROM dados_enem_consolidado 
                WHERE "NU_ANO" = {ano}
                AND ("CO_PROVA_CH" LIKE '%{cor_prova}%' OR "CO_PROVA_CN" LIKE '%{cor_prova}%' 
                     OR "CO_PROVA_LC" LIKE '%{cor_prova}%' OR "CO_PROVA_MT" LIKE '%{cor_prova}%')
                LIMIT {limit}
                """
            else:
                query = f"""
                SELECT 
                    "TX_RESPOSTAS_CH", "TX_RESPOSTAS_CN", "TX_RESPOSTAS_LC", "TX_RESPOSTAS_MT",
                    "TX_GABARITO_CH", "TX_GABARITO_CN", "TX_GABARITO_LC", "TX_GABARITO_MT",
                    "CO_PROVA_CH", "CO_PROVA_CN", "CO_PROVA_LC", "CO_PROVA_MT"
                FROM dados_enem_consolidado 
                WHERE "NU_ANO" = {ano}
                LIMIT {limit}
                """
            
            return _self.db_manager.execute_query_sqlalchemy(query)
        except Exception as e:
            st.error(f"Erro ao carregar dados dos participantes: {e}")
            return pd.DataFrame()
        
    def calculate_real_success_rates(
        self,
        df_questions: pd.DataFrame,
        df_participants: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Calcula taxas de acerto reais baseadas nas respostas dos participantes.

        A lógica é:
        - Criar uma posição sequencial por área (e, se existir, por cor) -> `posicao_area` = 1..N
        - Usar essa posição como índice na string de respostas TX_RESPOSTAS_CH/CN/LC/MT
        - Normalizar alternativas (gabarito e resposta do aluno) para A..E
        - Ignorar respostas em branco / inválidas

        Args:
            df_questions: DataFrame com as questões (já filtrado por ano e, se quiser, por área/cor)
            df_participants: DataFrame com respostas dos participantes

        Returns:
            DataFrame com colunas:
                - taxa_acerto_real
                - taxa_acerto_pct (espelho)
                - participantes_amostra
        """
        if df_questions.empty:
            return df_questions

        if df_participants.empty:
            st.warning("⚠️ Não há dados de participantes para calcular taxas de acerto reais")
            df_questions['taxa_acerto_real'] = 0.0
            df_questions['taxa_acerto_pct'] = 0.0
            df_questions['participantes_amostra'] = 0
            return df_questions

        area_to_respostas_col = self.area_to_respostas

        df_q = df_questions.copy()

        if 'sigla_area' not in df_q.columns:
            st.warning("Coluna 'sigla_area' não encontrada em df_questions; não é possível calcular taxa de acerto real.")
            df_q['taxa_acerto_real'] = 0.0
            df_q['taxa_acerto_pct'] = 0.0
            df_q['participantes_amostra'] = 0
            return df_q

        group_cols = []
        if 'ano' in df_q.columns:
            group_cols.append('ano')
        group_cols.append('sigla_area')
        if 'cor' in df_q.columns:
            group_cols.append('cor')

        df_q = df_q.sort_values(group_cols + ['numero_questao'])
        df_q['posicao_area'] = df_q.groupby(group_cols).cumcount() + 1

        respostas_por_area = {}
        for area_sigla, col in area_to_respostas_col.items():
            if col in df_participants.columns:
                serie = df_participants[col].dropna()
                respostas_por_area[area_sigla] = serie.astype(str).str.strip().tolist()
            else:
                respostas_por_area[area_sigla] = []

        success_rates = []
        sample_sizes = []

        for _, questao in df_q.iterrows():
            area_sigla = questao.get('sigla_area')

            if area_sigla not in respostas_por_area:
                success_rates.append(0.0)
                sample_sizes.append(0)
                continue

            posicao_area = questao.get('posicao_area')
            try:
                posicao = int(posicao_area)
            except Exception:
                success_rates.append(0.0)
                sample_sizes.append(0)
                continue

            if posicao < 1:
                success_rates.append(0.0)
                sample_sizes.append(0)
                continue

            gabarito_oficial = self._normalizar_alternativa(questao.get('gabarito'))

            if gabarito_oficial is None:
                success_rates.append(0.0)
                sample_sizes.append(0)
                continue

            respostas_lista = respostas_por_area.get(area_sigla, [])
            if not respostas_lista:
                success_rates.append(0.0)
                sample_sizes.append(0)
                continue

            acertos = 0
            total_validos = 0

            for respostas in respostas_lista:
                if posicao <= len(respostas):
                    resposta_bruta = respostas[posicao - 1]
                    resposta_aluno = self._normalizar_alternativa(resposta_bruta)

                    if resposta_aluno is not None:
                        if resposta_aluno == gabarito_oficial:
                            acertos += 1
                        total_validos += 1

            taxa_acerto = (acertos / total_validos * 100) if total_validos > 0 else 0.0
            success_rates.append(taxa_acerto)
            sample_sizes.append(total_validos)

        df_q['taxa_acerto_real'] = success_rates
        df_q['taxa_acerto_pct'] = df_q['taxa_acerto_real']
        df_q['participantes_amostra'] = sample_sizes

        return df_q

    def filter_by_year(self, df: pd.DataFrame, year: int) -> pd.DataFrame:
        """Filtra questões por ano."""
        return df[df['ano'] == year].copy()

    def filter_by_color(self, df: pd.DataFrame, color: str) -> pd.DataFrame:
        """Filtra questões por cor da prova."""
        return df[df['cor'] == color].copy()

    def filter_by_area(self, df: pd.DataFrame, area: str) -> pd.DataFrame:
        """Filtra questões por área."""
        if area == "Todas as áreas":
            return df
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
        if 'taxa_acerto_real' in df.columns:
            return df[
                (df['taxa_acerto_real'] >= min_rate) &
                (df['taxa_acerto_real'] <= max_rate)
            ].copy()
        else:
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
        stats = {
            'total_questoes': len(df),
            'itens_abandonados': int(df['item_abandonado'].sum()) if pd.notna(df['item_abandonado'].sum()) else 0,
            'media_dificuldade': df['parametro_b'].mean() if pd.notna(df['parametro_b'].mean()) else None,
        }

        if 'taxa_acerto_real' in df.columns and pd.notna(df['taxa_acerto_real'].mean()):
            stats['taxa_acerto_media'] = df['taxa_acerto_real'].mean()
            stats['participantes_media'] = df['participantes_amostra'].mean() if 'participantes_amostra' in df.columns else 0
        else:
            stats['taxa_acerto_media'] = df['taxa_acerto_pct'].mean() if pd.notna(df['taxa_acerto_pct'].mean()) else None

        return stats

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
                df['parametro_a'].mean() if pd.notna(df['parametro_a'].mean()) else 0,
                df['parametro_b'].mean() if pd.notna(df['parametro_b'].mean()) else 0,
                df['parametro_c'].mean() if pd.notna(df['parametro_c'].mean()) else 0
            ],
            'Mediana': [
                df['parametro_a'].median() if pd.notna(df['parametro_a'].median()) else 0,
                df['parametro_b'].median() if pd.notna(df['parametro_b'].median()) else 0,
                df['parametro_c'].median() if pd.notna(df['parametro_c'].median()) else 0
            ],
            'Desvio Padrão': [
                df['parametro_a'].std() if pd.notna(df['parametro_a'].std()) else 0,
                df['parametro_b'].std() if pd.notna(df['parametro_b'].std()) else 0,
                df['parametro_c'].std() if pd.notna(df['parametro_c'].std()) else 0
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
        habilidades.columns = ['Habilidade', 'Quantidade']
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
        return gabarito_counts.sort_values('Alternativa')
