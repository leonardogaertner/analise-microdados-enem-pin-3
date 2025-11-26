from typing import Dict, Tuple, Optional, List

import numpy as np
import pandas as pd
import streamlit as st


class PerformanceAnalyzer:
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.mapa_areas: Dict[str, Tuple[int, int]] = {}
        self.areas_nomes = {
            "CH": "Ciências Humanas",
            "CN": "Ciências da Natureza",
            "LC": "Linguagens e Códigos",
            "MT": "Matemática",
        }

    def normalizar_lingua(self, lingua: str) -> str:
        if not isinstance(lingua, str):
            return "Inglês"

        lingua_lower = lingua.lower().strip()
        if lingua_lower in ["inglês", "ingles", "inglãªs", "inglã©s"]:
            return "Inglês"
        elif lingua_lower in ["espanhol", "espanã³l", "espanol"]:
            return "Espanhol"
        else:
            return lingua

    def normalizar_cor_prova(self, cor_prova: str) -> str:
        if not isinstance(cor_prova, str):
            return ""

        cor_lower = cor_prova.lower().strip()
        if cor_lower in ["branca", "branco"]:
            return "BRANCO"
        elif cor_lower == "azul":
            return "AZUL"
        elif cor_lower in ["amarela", "amarelo"]:
            return "AMARELO"
        elif cor_lower == "rosa":
            return "ROSA"
        elif cor_lower == "cinza":
            return "CINZA"
        else:
            return cor_prova.upper()

    def get_qtd_questoes(self, ano: int, cor_prova: str, lingua: str = "INGLES") -> int:
        return 180

    def obter_cores_disponiveis(self, ano: int, lingua: str = "INGLES") -> List[str]:
        lingua_normalizada = self.normalizar_lingua(lingua)

        query = """
            SELECT DISTINCT cor
            FROM questoes_enem 
            WHERE ano = :ano 
              AND lingua = :lingua
            ORDER BY cor
        """
        params = {"ano": int(ano), "lingua": lingua_normalizada}

        try:
            df = self.db_manager.execute_query(query, params)
            if not df.empty:
                return df["cor"].tolist()
            return []
        except Exception as e:
            st.error(f"Erro ao buscar cores disponíveis: {e}")
            return []

    def obter_linguas_disponiveis(self, ano: int, cor_prova: str) -> List[str]:
        cor_normalizada = self.normalizar_cor_prova(cor_prova)

        query = """
            SELECT DISTINCT lingua
            FROM questoes_enem 
            WHERE ano = :ano 
              AND cor = :cor
            ORDER BY lingua
        """
        params = {"ano": int(ano), "cor": cor_normalizada}

        try:
            df = self.db_manager.execute_query(query, params)
            if not df.empty:
                return df["lingua"].tolist()
            return []
        except Exception as e:
            st.error(f"Erro ao buscar línguas disponíveis: {e}")
            return []

    def _aplicar_mapa_padrao_se_faltar(
        self, mapeamento: Dict[str, Tuple[int, int]]
    ) -> Dict[str, Tuple[int, int]]:
        mapa_padrao = {
            "LC": (1, 45),
            "CH": (46, 90),
            "CN": (91, 135),
            "MT": (136, 180),
        }

        if not mapeamento:
            return mapa_padrao.copy()

        for area, intervalo in mapa_padrao.items():
            if area not in mapeamento:
                mapeamento[area] = intervalo

        return mapeamento

    def obter_mapeamento_areas(
        self, ano: int, cor_prova: str, lingua: str = "INGLES"
    ) -> Dict[str, Tuple[int, int]]:
        return self._aplicar_mapa_padrao_se_faltar({})

    def buscar_provas_com_lingua(
        self, ano: int, cor_prova: str, lingua: str = "INGLES"
    ) -> pd.DataFrame:
        cor_normalizada = self.normalizar_cor_prova(cor_prova)
        lingua_normalizada = self.normalizar_lingua(lingua)

        query = """
            SELECT DISTINCT 
                provas, sigla_area, cor, ano, lingua
            FROM questoes_enem 
            WHERE ano   = :ano
              AND cor   = :cor
              AND lingua = :lingua
        """
        params = {
            "ano": int(ano),
            "cor": cor_normalizada,
            "lingua": lingua_normalizada,
        }

        try:
            df = self.db_manager.execute_query(query, params)

            if df.empty:
                st.warning(
                    f"⚠️ Nenhuma prova encontrada para {ano}, {cor_normalizada}, {lingua_normalizada}. Buscando alternativas..."
                )

                query_alt = """
                    SELECT DISTINCT 
                        provas, sigla_area, cor, ano, lingua
                    FROM questoes_enem 
                    WHERE ano   = :ano 
                      AND lingua = :lingua
                    LIMIT 10
                """
                df_alt = self.db_manager.execute_query(
                    query_alt, {"ano": int(ano), "lingua": lingua_normalizada}
                )
                if not df_alt.empty:
                    st.info(
                        f"✅ Encontradas {len(df_alt)} provas alternativas para {ano}, {lingua_normalizada}"
                    )
                    return df_alt

                query_alt2 = """
                    SELECT DISTINCT 
                        provas, sigla_area, cor, ano, lingua
                    FROM questoes_enem 
                    WHERE ano = :ano 
                      AND cor = :cor
                    LIMIT 10
                """
                df_alt2 = self.db_manager.execute_query(
                    query_alt2, {"ano": int(ano), "cor": cor_normalizada}
                )
                if not df_alt2.empty:
                    st.info(
                        f"✅ Encontradas {len(df_alt2)} provas alternativas para {ano}, {cor_normalizada}"
                    )
                    return df_alt2

                query_alt3 = """
                    SELECT DISTINCT 
                        provas, sigla_area, cor, ano, lingua
                    FROM questoes_enem 
                    WHERE ano = :ano
                    LIMIT 10
                """
                df_alt3 = self.db_manager.execute_query(
                    query_alt3, {"ano": int(ano)}
                )
                if not df_alt3.empty:
                    st.info(
                        f"✅ Encontradas {len(df_alt3)} provas alternativas para {ano}"
                    )
                    return df_alt3

                st.error(f"❌ Nenhuma prova encontrada para o ano {ano}")
                return pd.DataFrame()

            return df

        except Exception as e:
            st.error(f"Erro ao buscar provas na tabela questoes_enem: {e}")
            return pd.DataFrame()

    def buscar_gabaritos_por_provas(self, codigos_list: List[str]) -> pd.DataFrame:
        if not codigos_list:
            return pd.DataFrame()

        codigos_limpos = [c for c in codigos_list if str(c).isdigit()]
        if not codigos_limpos:
            return pd.DataFrame()

        condicoes_codigos = []
        for codigo in codigos_limpos:
            condicoes_codigos.append(
                f'"CO_PROVA_CH" = {codigo} OR '
                f'"CO_PROVA_CN" = {codigo} OR '
                f'"CO_PROVA_LC" = {codigo} OR '
                f'"CO_PROVA_MT" = {codigo}'
            )

        where_clause = " OR ".join(condicoes_codigos)

        query = f"""
            SELECT DISTINCT
                "CO_PROVA_CH",
                "CO_PROVA_CN",
                "CO_PROVA_LC",
                "CO_PROVA_MT",
                "TX_GABARITO_CH",
                "TX_GABARITO_CN",
                "TX_GABARITO_LC",
                "TX_GABARITO_MT"
            FROM dados_enem_consolidado
            WHERE {where_clause}
        """

        try:
            df = self.db_manager.execute_query(query)
            return df
        except Exception as e:
            st.error(f"❌ Erro ao buscar gabaritos em dados_enem_consolidado: {e}")
            return pd.DataFrame()

    def carregar_medias_db(
        self,
        codigos_list: List[str],
        ano: int,
    ) -> Dict[str, Dict]:
        if not codigos_list:
            return {}

        codigos_validos = [int(c) for c in codigos_list if str(c).isdigit()]
        if not codigos_validos:
            return {}

        codigos_str = ", ".join(str(c) for c in codigos_validos)
        where_exam = (
            f'"CO_PROVA_CH" IN ({codigos_str}) OR '
            f'"CO_PROVA_CN" IN ({codigos_str}) OR '
            f'"CO_PROVA_LC" IN ({codigos_str}) OR '
            f'"CO_PROVA_MT" IN ({codigos_str})'
        )

        medias = {"nacional": {}, "por_estado": {}}

        query_nacional = f"""
            SELECT
                AVG("NU_NOTA_CH") AS media_ch,
                AVG("NU_NOTA_CN") AS media_cn,
                AVG("NU_NOTA_LC") AS media_lc,
                AVG("NU_NOTA_MT") AS media_mt
            FROM dados_enem_consolidado
            WHERE "NU_ANO" = :ano
              AND ({where_exam})
        """
        try:
            df_nac = self.db_manager.execute_query(
                query_nacional, {"ano": int(ano)}
            )
            if not df_nac.empty:
                row = df_nac.loc[0]
                medias["nacional"] = {
                    "CH": float(row["media_ch"]) if not pd.isna(row["media_ch"]) else None,
                    "CN": float(row["media_cn"]) if not pd.isna(row["media_cn"]) else None,
                    "LC": float(row["media_lc"]) if not pd.isna(row["media_lc"]) else None,
                    "MT": float(row["media_mt"]) if not pd.isna(row["media_mt"]) else None,
                }
        except Exception as e:
            st.error(f"Erro ao carregar médias nacionais: {e}")

        query_uf = f"""
            SELECT
                "SG_UF_PROVA" AS uf,
                AVG("NU_NOTA_CH") AS media_ch,
                AVG("NU_NOTA_CN") AS media_cn,
                AVG("NU_NOTA_LC") AS media_lc,
                AVG("NU_NOTA_MT") AS media_mt
            FROM dados_enem_consolidado
            WHERE "NU_ANO" = :ano
              AND ({where_exam})
            GROUP BY "SG_UF_PROVA"
        """
        try:
            df_uf = self.db_manager.execute_query(
                query_uf, {"ano": int(ano)}
            )
            for _, row in df_uf.iterrows():
                uf = row["uf"]
                medias["por_estado"][uf] = {
                    "CH": float(row["media_ch"]) if not pd.isna(row["media_ch"]) else None,
                    "CN": float(row["media_cn"]) if not pd.isna(row["media_cn"]) else None,
                    "LC": float(row["media_lc"]) if not pd.isna(row["media_lc"]) else None,
                    "MT": float(row["media_mt"]) if not pd.isna(row["media_mt"]) else None,
                }
        except Exception as e:
            st.error(f"Erro ao carregar médias por estado (UF): {e}")

        return medias

    def extrair_respostas_por_area(
        self, respostas_dict: Dict[int, str], mapa_areas: Dict[str, Tuple[int, int]]
    ) -> Dict[str, List[str]]:
        respostas_por_area: Dict[str, List[str]] = {}

        for area, (inicio, fim) in mapa_areas.items():
            lista = []
            for q_num in range(inicio, fim + 1):
                resp = respostas_dict.get(q_num, "-")
                if resp is None:
                    resp = "-"
                lista.append(str(resp).upper())
            respostas_por_area[area] = lista

        return respostas_por_area

    def calcular_acertos_por_area(
        self, respostas_area: List[str], gabarito_area: List[str]
    ) -> Tuple[int, int]:
        if not respostas_area or not gabarito_area:
            return 0, 0

        n = min(len(respostas_area), len(gabarito_area))
        acertos = 0
        respondidas = 0

        for i in range(n):
            r = respostas_area[i]
            g = gabarito_area[i]

            if r in ["A", "B", "C", "D", "E"]:
                respondidas += 1
                if g in ["A", "B", "C", "D", "E"] and r == g:
                    acertos += 1

        return acertos, respondidas

    def estimar_nota_tri(
        self, acertos: int, total_questoes_area: int, media_nacional: Optional[float]
    ) -> float:
        if total_questoes_area <= 0:
            return 0.0

        perc = acertos / total_questoes_area
        nota_base = 300 + perc * 500

        if media_nacional is not None:
            return 0.7 * nota_base + 0.3 * media_nacional

        return nota_base

    def identificar_melhor_prova(
        self,
        df_gabs: pd.DataFrame,
        respostas_dict: Dict[int, str],
        mapa_areas: Dict[str, Tuple[int, int]],
    ):
        if df_gabs.empty:
            return None, 0

        melhor_row = None
        melhor_score = -1

        for _, row in df_gabs.iterrows():
            score = 0

            for area, (inicio, fim) in mapa_areas.items():
                if area == "CH":
                    gab_str = row.get("TX_GABARITO_CH")
                elif area == "CN":
                    gab_str = row.get("TX_GABARITO_CN")
                elif area == "LC":
                    gab_str = row.get("TX_GABARITO_LC")
                elif area == "MT":
                    gab_str = row.get("TX_GABARITO_MT")
                else:
                    gab_str = None

                if not isinstance(gab_str, str) or not gab_str:
                    continue

                gab_str = gab_str.strip()
                for q_num in range(inicio, fim + 1):
                    idx_local = q_num - inicio
                    if idx_local < 0 or idx_local >= len(gab_str):
                        continue

                    resposta_aluno = respostas_dict.get(q_num, "-")
                    if resposta_aluno in ["A", "B", "C", "D", "E"]:
                        if resposta_aluno.upper() == gab_str[idx_local].upper():
                            score += 1

            if score > melhor_score:
                melhor_score = score
                melhor_row = row

        return melhor_row, melhor_score

    def construir_gabarito_oficial(
        self, melhor_row: pd.Series, mapa_areas: Dict[str, Tuple[int, int]]
    ) -> Dict[str, List[str]]:
        gabarito_oficial: Dict[str, List[str]] = {}

        for area, (inicio, fim) in mapa_areas.items():
            if area == "CH":
                gab_str = melhor_row.get("TX_GABARITO_CH")
            elif area == "CN":
                gab_str = melhor_row.get("TX_GABARITO_CN")
            elif area == "LC":
                gab_str = melhor_row.get("TX_GABARITO_LC")
            elif area == "MT":
                gab_str = melhor_row.get("TX_GABARITO_MT")
            else:
                gab_str = None

            if not isinstance(gab_str, str) or not gab_str:
                gabarito_oficial[area] = []
                continue

            gab_str = gab_str.strip()
            questoes_area = fim - inicio + 1

            lista_area = []
            for i in range(questoes_area):
                if i < len(gab_str):
                    lista_area.append(gab_str[i].upper())
                else:
                    lista_area.append("-")

            gabarito_oficial[area] = lista_area

        return gabarito_oficial

    def gerar_detalhes_questoes(
        self,
        respostas_por_area: Dict[str, List[str]],
        gabarito_oficial: Dict[str, List[str]],
        mapa_areas: Dict[str, Tuple[int, int]],
    ) -> List[Dict]:
        detalhes = []

        for area, (inicio, fim) in mapa_areas.items():
            respostas_area = respostas_por_area.get(area, [])
            gabarito_area = gabarito_oficial.get(area, [])

            for idx in range(len(gabarito_area)):
                numero_questao = inicio + idx
                resposta_usuario = (
                    respostas_area[idx] if idx < len(respostas_area) else "-"
                )
                resposta_oficial = (
                    gabarito_area[idx] if idx < len(gabarito_area) else "-"
                )

                acertou = False
                if (
                    resposta_usuario in ["A", "B", "C", "D", "E"]
                    and resposta_oficial in ["A", "B", "C", "D", "E"]
                ):
                    acertou = resposta_usuario == resposta_oficial

                detalhes.append(
                    {
                        "numero": numero_questao,
                        "area": area,
                        "area_nome": self.areas_nomes.get(area, area),
                        "resposta_usuario": resposta_usuario,
                        "resposta_oficial": resposta_oficial,
                        "acertou": acertou,
                        "status": "✅" if acertou else "❌",
                    }
                )

        return sorted(detalhes, key=lambda x: x["numero"])

    def analisar_padroes_erro(self, detalhes_questoes: List[Dict]) -> Dict:
        erros = [
            q
            for q in detalhes_questoes
            if not q["acertou"] and q["resposta_usuario"] != "-"
        ]

        analise = {
            "total_erros": len(erros),
            "distancias": [],
            "erros_por_area": {},
        }

        if erros:
            distancias = []
            for erro in erros:
                resp_usuario = erro["resposta_usuario"]
                resp_oficial = erro["resposta_oficial"]

                if resp_usuario in "ABCDE" and resp_oficial in "ABCDE":
                    dist = abs(ord(resp_usuario) - ord(resp_oficial))
                    distancias.append(dist)

            if distancias:
                analise["distancias"] = distancias
                analise["distancia_media"] = sum(distancias) / len(distancias)

        for area in ["CH", "CN", "LC", "MT"]:
            erros_area = [q for q in erros if q["area"] == area]
            analise["erros_por_area"][area] = len(erros_area)

        return analise

    def estimar_nota_tri_parametrizada(
        self,
        respostas_area: List[str],
        gabarito_area: List[str],
        intervalo: Tuple[int, int],
        ano: int,
        cor_prova: str,
        lingua: str,
        sigla_area: str,
    ) -> float:
        from math import isfinite

        inicio, fim = intervalo
        cor_norm = self.normalizar_cor_prova(cor_prova)
        lingua_norm = self.normalizar_lingua(lingua)

        query = """
            SELECT 
                numero_questao,
                AVG(parametro_a) AS a,
                AVG(parametro_b) AS b,
                AVG(parametro_c) AS c
            FROM questoes_enem
            WHERE ano = :ano
              AND cor = :cor
              AND lingua = :lingua
              AND sigla_area = :sigla_area
              AND numero_questao BETWEEN :inicio AND :fim
              AND parametro_a IS NOT NULL
              AND parametro_b IS NOT NULL
              AND parametro_c IS NOT NULL
            GROUP BY numero_questao
            ORDER BY numero_questao
        """
        params = {
            "ano": int(ano),
            "cor": cor_norm,
            "lingua": lingua_norm,
            "sigla_area": sigla_area,
            "inicio": int(inicio),
            "fim": int(fim),
        }

        try:
            df_par = self.db_manager.execute_query(query, params)
        except Exception as e:
            st.error(f"Erro ao buscar parâmetros TRI para {sigla_area}: {e}")
            acertos = sum(
                1
                for r, g in zip(respostas_area, gabarito_area)
                if r in "ABCDE" and g in "ABCDE" and r == g
            )
            return self.estimar_nota_tri(acertos, len(gabarito_area), None)

        if df_par.empty:
            acertos = sum(
                1
                for r, g in zip(respostas_area, gabarito_area)
                if r in "ABCDE" and g in "ABCDE" and r == g
            )
            return self.estimar_nota_tri(acertos, len(gabarito_area), None)

        itens = []
        for _, row in df_par.iterrows():
            qnum = int(row["numero_questao"])
            idx = qnum - inicio

            if idx < 0 or idx >= len(gabarito_area):
                continue

            resp = respostas_area[idx]
            gab = gabarito_area[idx]

            if resp not in ["A", "B", "C", "D", "E"] or gab not in ["A", "B", "C", "D", "E"]:
                continue

            u = 1 if resp == gab else 0

            try:
                a = float(row["a"])
                b = float(row["b"])
                c = float(row["c"])
            except Exception:
                continue

            if not (isfinite(a) and isfinite(b) and isfinite(c)):
                continue

            itens.append({"a": a, "b": b, "c": c, "u": u})

        if len(itens) < 3:
            acertos = sum(i["u"] for i in itens)
            return self.estimar_nota_tri(acertos, len(gabarito_area), None)

        theta = 0.0
        for _ in range(10):
            num = 0.0
            den = 0.0

            for item in itens:
                a = item["a"]
                b = item["b"]
                c = item["c"]
                u = item["u"]

                exp_term = np.exp(-a * (theta - b))
                P = c + (1.0 - c) / (1.0 + exp_term)
                P = float(np.clip(P, 1e-6, 1.0 - 1e-6))

                dP = (1.0 - c) * a * exp_term / (1.0 + exp_term) ** 2

                w = dP / (P * (1.0 - P))
                num += (u - P) * w

                den += (dP ** 2) / (P * (1.0 - P))

            if den <= 1e-8:
                break

            delta = num / den
            theta += float(delta)
            theta = float(np.clip(theta, -4.0, 4.0))

            if abs(delta) < 1e-3:
                break

        nota = 500.0 + 100.0 * theta
        nota = float(np.clip(nota, 0.0, 1000.0))
        return nota

    def calcular_desempenho_areas(
        self,
        respostas_por_area: Dict[str, List[str]],
        gabarito_oficial: Dict[str, List[str]],
        mapa_areas: Dict[str, Tuple[int, int]],
        ano: int,
        cor_prova: str,
        lingua: str,
        medias: Optional[Dict] = None,
        estado: Optional[str] = None,
    ) -> Dict[str, Dict]:
        resultados_areas: Dict[str, Dict] = {}
        medias = medias or {}
        medias_nac = medias.get("nacional", {})
        medias_estados = medias.get("por_estado", {})

        for area in ["CH", "CN", "LC", "MT"]:
            if area not in mapa_areas:
                continue

            respostas_area = respostas_por_area.get(area, [])
            gabarito_area = gabarito_oficial.get(area, [])
            total_questoes_area = len(gabarito_area)

            if total_questoes_area == 0:
                resultados_areas[area] = {
                    "acertos": 0,
                    "total_questoes": 0,
                    "respondidas": 0,
                    "percentual": 0.0,
                    "nota_estimada": 0.0,
                    "media_nacional": medias_nac.get(area),
                    "media_regional": None,
                }
                continue

            acertos, respondidas = self.calcular_acertos_por_area(
                respostas_area, gabarito_area
            )
            percentual = (
                (acertos / total_questoes_area) * 100
                if total_questoes_area > 0
                else 0
            )

            media_nacional = medias_nac.get(area)
            media_regional = None
            if estado and estado in medias_estados:
                media_regional = medias_estados[estado].get(area)

            try:
                nota_estimada = self.estimar_nota_tri_parametrizada(
                    respostas_area,
                    gabarito_area,
                    mapa_areas[area],
                    ano,
                    cor_prova,
                    lingua,
                    area,
                )
            except Exception as e:
                st.error(f"Erro ao estimar nota TRI para {area}: {e}")
                nota_estimada = self.estimar_nota_tri(
                    acertos, total_questoes_area, media_nacional
                )

            resultados_areas[area] = {
                "acertos": acertos,
                "total_questoes": total_questoes_area,
                "respondidas": respondidas,
                "percentual": round(percentual, 1),
                "nota_estimada": round(nota_estimada, 1),
                "media_nacional": media_nacional,
                "media_regional": media_regional,
            }

        return resultados_areas

    def analisar_desempenho(
        self,
        respostas_dict: Dict[int, str],
        ano: int,
        cor_prova: str,
        estado: Optional[str] = None,
        lingua: str = "INGLES",
    ) -> Dict:
        lingua_normalizada = self.normalizar_lingua(lingua)

        mapa_areas = self.obter_mapeamento_areas(ano, cor_prova, lingua)
        self.mapa_areas = mapa_areas

        df_provas = self.buscar_provas_com_lingua(ano, cor_prova, lingua)
        if df_provas.empty:
            return {
                "erro": f"Nenhuma prova encontrada para {ano}, cor {cor_prova}, língua {lingua_normalizada} na tabela questoes_enem."
            }

        todos_codigos = set()
        for provas_str in df_provas["provas"].dropna():
            if provas_str:
                codigos = [
                    codigo.strip()
                    for codigo in str(provas_str).split(",")
                    if codigo.strip().isdigit()
                ]
                todos_codigos.update(codigos)

        if not todos_codigos:
            return {"erro": "Nenhum código de prova válido encontrado."}

        codigos_list = list(todos_codigos)

        df_gabs = self.buscar_gabaritos_por_provas(codigos_list)
        if df_gabs.empty:
            return {
                "erro": f"Nenhum gabarito encontrado para os códigos de prova: {codigos_list}"
            }

        melhor_row, melhor_score = self.identificar_melhor_prova(
            df_gabs, respostas_dict, mapa_areas
        )
        if melhor_row is None:
            return {
                "erro": "Não foi possível identificar um gabarito adequado com as respostas fornecidas."
            }

        gabarito_oficial = self.construir_gabarito_oficial(melhor_row, mapa_areas)

        respostas_por_area = self.extrair_respostas_por_area(
            respostas_dict, mapa_areas
        )

        detalhes_questoes = self.gerar_detalhes_questoes(
            respostas_por_area, gabarito_oficial, mapa_areas
        )

        medias = self.carregar_medias_db(codigos_list, ano)

        resultados_areas = self.calcular_desempenho_areas(
            respostas_por_area,
            gabarito_oficial,
            mapa_areas,
            ano,
            cor_prova,
            lingua,
            medias=medias,
            estado=estado,
        )

        total_acertos = sum(r["acertos"] for r in resultados_areas.values())
        total_questoes_geral = sum(
            r["total_questoes"] for r in resultados_areas.values()
        )
        nota_geral = (
            sum(r["nota_estimada"] for r in resultados_areas.values())
            / len(resultados_areas)
            if resultados_areas
            else 0
        )

        info_prova = {
            "CO_PROVA_CH": melhor_row.get("CO_PROVA_CH"),
            "CO_PROVA_CN": melhor_row.get("CO_PROVA_CN"),
            "CO_PROVA_LC": melhor_row.get("CO_PROVA_LC"),
            "CO_PROVA_MT": melhor_row.get("CO_PROVA_MT"),
            "match_score": int(melhor_score),
            "lingua": lingua_normalizada,
            "descricao": f"ENEM {ano} - {cor_prova} - {lingua_normalizada}",
            "codigos_disponiveis": codigos_list,
        }

        return {
            "resultados_areas": resultados_areas,
            "total_acertos": total_acertos,
            "total_questoes": total_questoes_geral,
            "percentual_geral": round(
                (total_acertos / total_questoes_geral) * 100, 1
            )
            if total_questoes_geral > 0
            else 0,
            "nota_geral": round(nota_geral, 1),
            "ano": ano,
            "cor_prova": cor_prova,
            "estado": estado,
            "lingua": lingua_normalizada,
            "info_prova": info_prova,
            "gabarito_oficial": gabarito_oficial,
            "mapa_areas": mapa_areas,
            "detalhes_questoes": detalhes_questoes,
            "medias": medias,
        }
