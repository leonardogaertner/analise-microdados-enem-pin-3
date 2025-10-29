"""
Analisador de desempenho pessoal no ENEM.
"""
import pandas as pd
import numpy as np
from psycopg2 import sql
from typing import Dict, Tuple, Optional, List
import streamlit as st


class PerformanceAnalyzer:
    """Classe responsável por análises de desempenho pessoal no ENEM."""

    def __init__(self, db_manager):
        """
        Inicializa o analisador de desempenho.

        Args:
            db_manager: Instância de DatabaseManager para acesso ao banco.
        """
        self.db_manager = db_manager
        self.mapa_areas = {
            "CH": (1, 45),
            "CN": (46, 90),
            "LC": (91, 135),
            "MT": (136, 180)
        }
        self.areas_nomes = {
            "CH": "Ciências Humanas",
            "CN": "Ciências da Natureza",
            "LC": "Linguagens e Códigos",
            "MT": "Matemática"
        }

    def buscar_gabaritos_db(self, ano: int) -> pd.DataFrame:
        """
        Busca gabaritos oficiais do banco de dados para um ano específico.

        Args:
            ano: Ano da prova.

        Returns:
            DataFrame com os gabaritos.
        """
        query = f"""
            SELECT DISTINCT
                "CO_PROVA_CH", "TX_GABARITO_CH",
                "CO_PROVA_CN", "TX_GABARITO_CN",
                "CO_PROVA_LC", "TX_GABARITO_LC",
                "CO_PROVA_MT", "TX_GABARITO_MT"
            FROM {self.db_manager.config.table_name}
            WHERE "NU_ANO" = %s
            AND (
                "TX_GABARITO_CH" IS NOT NULL OR
                "TX_GABARITO_CN" IS NOT NULL OR
                "TX_GABARITO_LC" IS NOT NULL OR
                "TX_GABARITO_MT" IS NOT NULL
            )
            LIMIT 20;
        """
        try:
            df = self.db_manager.execute_query(query, [ano])
            return df
        except Exception as e:
            st.error(f"Erro ao buscar gabaritos no DB: {e}")
            return pd.DataFrame()

    def identificar_melhor_prova(self, df_gabs: pd.DataFrame,
                                 respostas_usuario: Dict[int, str]) -> Tuple[Optional[pd.Series], int]:
        """
        Identifica qual gabarito melhor corresponde às respostas do usuário.

        Args:
            df_gabs: DataFrame com gabaritos disponíveis.
            respostas_usuario: Dicionário com respostas do usuário {questao: resposta}.

        Returns:
            Tupla com (melhor_row, melhor_score).
        """
        if df_gabs.empty:
            return None, 0

        def combinar_gabarito(row):
            completo = []
            for area in ["CH", "CN", "LC", "MT"]:
                col = f"TX_GABARITO_{area}"
                gab = row.get(col)
                if gab is None:
                    completo.extend([None] * 45)
                else:
                    gab_list = list(gab.strip())
                    gab_list = (gab_list + [None] * 45)[:45]
                    completo.extend(gab_list)
            return completo

        melhor_score = -1
        melhor_row = None

        for _, row in df_gabs.iterrows():
            gabarito_comb = combinar_gabarito(row)
            score = 0
            for q_index in range(180):
                user_resp = respostas_usuario.get(q_index + 1)
                gab_resp = gabarito_comb[q_index]
                if user_resp is not None and user_resp != "-" and gab_resp is not None:
                    if user_resp == gab_resp:
                        score += 1
            if score > melhor_score:
                melhor_score = score
                melhor_row = row

        return melhor_row, melhor_score

    def carregar_medias_db(self, ano: int, estado: Optional[str] = None) -> Dict[str, Optional[float]]:
        """
        Carrega médias nacionais ou regionais do banco de dados.

        Args:
            ano: Ano da prova.
            estado: Sigla do estado (opcional).

        Returns:
            Dicionário com as médias por área.
        """
        query = f"""
            SELECT
                AVG("NU_NOTA_CH") AS "MEDIA_CH",
                AVG("NU_NOTA_CN") AS "MEDIA_CN",
                AVG("NU_NOTA_LC") AS "MEDIA_LC",
                AVG("NU_NOTA_MT") AS "MEDIA_MT"
            FROM {self.db_manager.config.table_name}
            WHERE "NU_ANO" = %s
            AND "TP_PRESENCA_CH" = 1
            AND "TP_PRESENCA_CN" = 1
            AND "TP_PRESENCA_LC" = 1
            AND "TP_PRESENCA_MT" = 1
        """
        params = [ano]
        if estado:
            query += ' AND "SG_UF_PROVA" = %s'
            params.append(estado)

        try:
            df = self.db_manager.execute_query(query, params)
            if df.empty:
                return {"MEDIA_CH": None, "MEDIA_CN": None, "MEDIA_LC": None, "MEDIA_MT": None}
            row = df.iloc[0].to_dict()
            return {k: (None if pd.isna(v) else float(v)) for k, v in row.items()}
        except Exception as e:
            st.error(f"Erro ao carregar médias do DB: {e}")
            return {"MEDIA_CH": None, "MEDIA_CN": None, "MEDIA_LC": None, "MEDIA_MT": None}

    def extrair_respostas_por_area(self, respostas_dict: Dict[int, str]) -> Dict[str, List]:
        """
        Extrai respostas organizadas por área de conhecimento.

        Args:
            respostas_dict: Dicionário com todas as respostas.

        Returns:
            Dicionário com respostas por área.
        """
        respostas_por_area = {}
        for area, (inicio, fim) in self.mapa_areas.items():
            respostas_area = []
            for q in range(inicio, fim + 1):
                resp = respostas_dict.get(q)
                if resp is not None and resp != "-" and resp in ["A", "B", "C", "D", "E"]:
                    respostas_area.append(resp)
                else:
                    respostas_area.append(None)
            respostas_por_area[area] = respostas_area
        return respostas_por_area

    def calcular_acertos(self, respostas_usuario: List, gabarito_oficial: List) -> Tuple[int, int]:
        """
        Calcula o número de acertos e questões respondidas.

        Args:
            respostas_usuario: Lista com respostas do usuário.
            gabarito_oficial: Lista com gabarito oficial.

        Returns:
            Tupla com (acertos, total_respondidas).
        """
        acertos = 0
        total_respondidas = 0
        for resp_usuario, resp_gabarito in zip(respostas_usuario, gabarito_oficial):
            if resp_usuario is not None:
                total_respondidas += 1
                if resp_gabarito is not None and resp_usuario == resp_gabarito:
                    acertos += 1
        return acertos, total_respondidas

    def estimar_nota_tri(self, acertos: int, total_questoes: int, media_area: Optional[float]) -> float:
        """
        Estima nota TRI baseada em acertos e média da área.

        Args:
            acertos: Número de acertos.
            total_questoes: Total de questões.
            media_area: Média da área para referência.

        Returns:
            Nota estimada.
        """
        if total_questoes == 0:
            return 0
        proporcao_acertos = acertos / total_questoes
        desvio_padrao = 100
        base_media = media_area if media_area is not None else 500
        nota_estimada = base_media + (proporcao_acertos - 0.5) * desvio_padrao * 2
        return max(0, min(1000, nota_estimada))

    def analisar_desempenho(self, respostas_dict: Dict[int, str], ano: int,
                           cor_prova: str, estado: Optional[str] = None) -> Dict:
        """
        Realiza análise completa do desempenho do usuário.

        Args:
            respostas_dict: Dicionário com respostas {questao: resposta}.
            ano: Ano da prova.
            cor_prova: Cor do caderno.
            estado: Estado para comparação regional (opcional).

        Returns:
            Dicionário com todos os resultados da análise.
        """
        df_gabs = self.buscar_gabaritos_db(ano)
        if df_gabs.empty:
            return {"erro": f"Nenhum gabarito encontrado para o ano {ano} no banco."}

        melhor_row, melhor_score = self.identificar_melhor_prova(df_gabs, respostas_dict)
        if melhor_row is None:
            return {"erro": "Não foi possível identificar um gabarito adequado com as respostas fornecidas."}

        gabarito_oficial = {}
        for area in ["CH", "CN", "LC", "MT"]:
            txt = melhor_row.get(f"TX_GABARITO_{area}")
            if txt is None:
                txt = " " * 45
            txt = (txt.strip() + " " * 45)[:45]
            gabarito_oficial[area] = list(txt)

        medias_nacionais = self.carregar_medias_db(ano, estado=None)
        medias_regionais = self.carregar_medias_db(ano, estado) if estado else None

        respostas_por_area = self.extrair_respostas_por_area(respostas_dict)
        resultados_areas = {}

        for area in ["CH", "CN", "LC", "MT"]:
            respostas = respostas_por_area[area]
            gabarito = gabarito_oficial.get(area, [None] * 45)
            acertos, respondidas = self.calcular_acertos(respostas, gabarito)
            percentual = (acertos / 45) * 100 if respondidas > 0 else 0
            key_media_map = {"CH": "MEDIA_CH", "CN": "MEDIA_CN", "LC": "MEDIA_LC", "MT": "MEDIA_MT"}

            media_nacional = medias_nacionais.get(key_media_map[area], None)
            nota_estimada = self.estimar_nota_tri(acertos, 45, media_nacional if media_nacional else 500)

            if medias_regionais:
                media_regional = medias_regionais.get(key_media_map[area], None)
                diferenca_regional = nota_estimada - media_regional if media_regional else None
            else:
                media_regional = None
                diferenca_regional = None

            resultados_areas[area] = {
                "acertos": acertos,
                "total_questoes": 45,
                "respondidas": respondidas,
                "percentual": percentual,
                "nota_estimada": round(nota_estimada, 1),
                "media_nacional": round(media_nacional, 1) if media_nacional else None,
                "media_regional": round(media_regional, 1) if media_regional else None,
                "diferenca_nacional": round(nota_estimada - media_nacional, 1) if media_nacional else None,
                "diferenca_regional": round(diferenca_regional, 1) if diferenca_regional else None
            }

        total_acertos = sum(r["acertos"] for r in resultados_areas.values())
        nota_geral = sum(r["nota_estimada"] for r in resultados_areas.values()) / 4
        info_prova = {
            "CO_PROVA_CH": melhor_row.get("CO_PROVA_CH"),
            "CO_PROVA_CN": melhor_row.get("CO_PROVA_CN"),
            "CO_PROVA_LC": melhor_row.get("CO_PROVA_LC"),
            "CO_PROVA_MT": melhor_row.get("CO_PROVA_MT"),
            "match_score": int(melhor_score)
        }

        return {
            "resultados_areas": resultados_areas,
            "total_acertos": total_acertos,
            "total_questoes": 180,
            "percentual_geral": round((total_acertos / 180) * 100, 1),
            "nota_geral": round(nota_geral, 1),
            "ano": ano,
            "cor_prova": cor_prova,
            "estado": estado,
            "info_prova": info_prova,
            "gabarito_oficial": gabarito_oficial
        }
