import altair as alt
import pandas as pd

# ===================================================================
# PASSO 1: MAPEAMENTO DE COLUNAS POR TIPO DE DADO
# ===================================================================
# Baseado na sua solicitação, 'Certificado?' (IN_CERTIFICADO) foi movido
# para QUALITATIVE e 'Tempo Fora da Escola' (TEMPO_FORA_ESCOLA) para TEMPORAL.

def get_column_lists():
    """
    Retorna um dicionário com as listas de colunas (nomes amigáveis) 
    categorizadas por tipo de dado para uso nos gráficos.
    (Esta função foi ATUALIZADA com todas as colunas)
    """
    
    # 🔢 QUANTITATIVO (Contínuo): Variáveis numéricas que podem ser agregadas
    quantitative_cols = [
        "Média Geral",
        "Média Questões Objetivas",
        "Nota de História",
        "Nota de Ciências da Natureza",
        "Nota Competência 1",
        "Nota Competência 2",
        "Nota Competência 3",
        "Nota Competência 4",
        "Nota Competência 5",
        "Nota de Linguagens e Códigos",
        "Nota de Matemática",
        "Nota da Redação",
    ]

    # 🏷️ QUALITATIVO (Nominal e Ordinal): Categorias, grupos, tags
    qualitative_cols = [
        # Nominais
        "Adulto?",
        "Candidato realizou a prova na capital do estado?",
        "Presença",
        "Redação Zerada?",
        "Treineiro?",
        "Nome Entidade Certificação",
        "Nome do Município da Escola",
        "Nome do Município da Prova",
        "Região do Candidato",
        "Região da Escola do Candidato",
        "UF Entidade Certificação",
        "Sigla da UF da Escola",
        "Sigla da UF da Prova",
        "Tipo da Escola", # (TIPO_ESCOLA_AGRUPADO)
        "Cor/Raça",
        "Tipo de Dependência Administrativa da Escola",
        "Tipo de Ensino",
        "Tipo de Escola", # (TP_ESCOLA)
        "Estado Civil",
        "Tipo de Língua",
        "Localização da Escola",
        "Nacionalidade",
        "Presença em História",
        "Presença em Ciências da Natureza",
        "Presença em Linguagens e Códigos",
        "Presença em Matemática",
        "Sexo",
        "Situação Funcional da Escola",
        "Status da Redação",
        "Situação de Conclusão",
        "Certificado?",
        
        # Ordinais (podem ser tratados como qualitativos)
        "Escolaridade dos Pais",
        "Acesso à Tecnologia",
        "Renda Familiar",
        "Faixa Etária",
    ]

    # ⏳ TEMPORAL: Anos ou datas
    temporal_cols = [
        "Ano",
        "Ano de Conclusão",
        "Tempo Fora da Escola",
    ]

    # 🆔 IDENTIFICADOR: Úteis para contagens
    id_cols = [
        "Nº de Inscrição",
        "Cód. Município Escola",
        "Cód. do Município da Prova",
        # --- Campos Adicionados ---
        "Cód. da Prova de História",
        "Cód. da Prova de Ciências da Natureza",
        "Cód. da Prova de Linguagens e Códigos",
        "Cód. da Prova de Matemática",
        "Cód. UF Certificação",
        "Cód. da UF da Escola",
        "Cód. da UF da Prova",
    ]

    return {
        "quantitative": sorted(quantitative_cols),
        "qualitative": sorted(qualitative_cols),
        "temporal": sorted(temporal_cols),
        "id_for_count": sorted(id_cols) # Ordenado para consistência
    }


# ===================================================================
# PASSO 2: FUNÇÕES DE GERAÇÃO DE GRÁFICOS (ALTAIR)
# ===================================================================
# Estas funções recebem os nomes das colunas (amigáveis) e criam os gráficos

def create_scatter_plot(df: pd.DataFrame, x_col: str, y_col: str, color_col: str = None):
    """Gera um gráfico de dispersão (Quantitativo vs Quantitativo)."""
    
    # Base do gráfico
    chart = alt.Chart(df).mark_circle(opacity=0.7).encode(
        x=alt.X(x_col, title=x_col, scale=alt.Scale(zero=False)),
        y=alt.Y(y_col, title=y_col, scale=alt.Scale(zero=False)),
        tooltip=[x_col, y_col]
    ).interactive() # Permite zoom e pan

    # Adiciona cor se selecionado
    if color_col and color_col != "Nenhum":
        chart = chart.encode(
            color=alt.Color(color_col, title=color_col),
            tooltip=[x_col, y_col, color_col]
        )
        
    return chart

def create_bar_chart(df: pd.DataFrame, x_col: str, y_col: str, aggregation: str, color_col: str = None):
    """Gera um gráfico de barras (Qualitativo vs Quantitativo Agregado).
    (CORRIGIDO para controlar a largura das barras e evitar rolagem)
    """
    
    # Define a agregação para o eixo Y
    if aggregation == 'Contagem':
        y_encoding = alt.Y('count()', title='Contagem')
        tooltip_y = alt.Tooltip('count()', title='Contagem')
    elif aggregation == 'Média':
        y_encoding = alt.Y(f'mean({y_col})', title=f'Média de {y_col}')
        tooltip_y = alt.Tooltip(f'mean({y_col})', title=f'Média de {y_col}')
    elif aggregation == 'Soma':
        y_encoding = alt.Y(f'sum({y_col})', title=f'Soma de {y_col}')
        tooltip_y = alt.Tooltip(f'sum({y_col})', title=f'Soma de {y_col}')
    else: # Fallback para média
        y_encoding = alt.Y(f'mean({y_col})', title=f'Média de {y_col}')
        tooltip_y = alt.Tooltip(f'mean({y_col})', title=f'Média de {y_col}')

    # Tooltip básico
    tooltip = [alt.Tooltip(x_col, title=x_col), tooltip_y]

    # Adiciona cor (barras agrupadas)
    if color_col and color_col != "Nenhum":
        tooltip.append(alt.Tooltip(color_col, title=color_col))
        
        # --- AJUSTE DE LARGURA ---
        # Define a largura de CADA barra individual (ex: 'Acesso à Tecnologia')
        # como 20 pixels.
        # Se você tem 4 categorias de 'Acesso', cada 'Região' terá 4*20 = 80px.
        # 5 Regiões * 80px = 400px de largura total, o que cabe na tela.
        bar_width = alt.Step(20)
        # --- FIM DO AJUSTE ---

        chart = alt.Chart(df).mark_bar().encode(
            # X-axis: Usa a variável de COR (ex: 'Acesso à Tecnologia').
            # 'axis=None' esconde os rótulos repetidos de 'Acesso'
            x=alt.X(color_col, title="", axis=None),
            
            # Y-axis: A métrica (ex: Média da Nota)
            y=y_encoding,
            
            # Cor: Baseada na variável de cor (ex: 'Acesso à Tecnologia')
            color=alt.Color(color_col, title=color_col),
            
            # Colunas: Usa a variável X (ex: 'Região') para criar os GRUPOS.
            # O header é movido para baixo para agir como o Eixo X principal.
            column=alt.Column(
                x_col,
                title=x_col, # Título principal do grupo (ex: "Região do Candidato")
                header=alt.Header(
                    titleOrient="bottom", 
                    labelOrient="bottom",
                    titlePadding=10, # Adiciona um espaço
                    labelPadding=5
                )
            ),
            tooltip=tooltip
        ).properties(
            # Aplica a propriedade de largura ao gráfico
            width=bar_width
        )
    else:
        # Gráfico simples (sem cor) - Lógica original
        chart = alt.Chart(df).mark_bar().encode(
            # Ordena da maior barra para a menor
            x=alt.X(x_col, title=x_col, sort='-y'), 
            y=y_encoding,
            tooltip=tooltip
        )

    return chart.interactive()


def create_line_chart(df: pd.DataFrame, x_col: str, y_col: str, aggregation: str, color_col: str = None):
    """Gera um gráfico de linha (Temporal vs Quantitativo Agregado)."""

    # Define a agregação para o eixo Y
    if aggregation == 'Contagem':
        y_encoding = alt.Y('count()', title='Contagem')
        tooltip_y = alt.Tooltip('count()', title='Contagem')
    elif aggregation == 'Média':
        y_encoding = alt.Y(f'mean({y_col})', title=f'Média de {y_col}')
        tooltip_y = alt.Tooltip(f'mean({y_col})', title=f'Média de {y_col}')
    else: # Soma
        y_encoding = alt.Y(f'sum({y_col})', title=f'Soma de {y_col}')
        tooltip_y = alt.Tooltip(f'sum({y_col})', title=f'Soma de {y_col}')

    # Tooltip básico
    tooltip = [alt.Tooltip(x_col, title=x_col), tooltip_y]

    # Base do gráfico
    base = alt.Chart(df).encode(
        x=alt.X(x_col, title=x_col),
        y=y_encoding
    )
    
    # Adiciona cor (múltiplas linhas)
    if color_col and color_col != "Nenhum":
        base = base.encode(
            color=alt.Color(color_col, title=color_col),
            tooltip=tooltip + [alt.Tooltip(color_col, title=color_col)]
        )
    else:
        base = base.encode(tooltip=tooltip)

    # Combina linha e pontos
    line = base.mark_line()
    points = base.mark_point()

    return (line + points).interactive()


def create_histogram(df: pd.DataFrame, x_col: str, color_col: str = None):
    """Gera um histograma (Distribuição de 1 variável Quantitativa)."""
    
    base = alt.Chart(df).mark_bar(opacity=0.7).encode(
        x=alt.X(x_col, bin=True, title=x_col),
        y=alt.Y('count()', title='Contagem'),
        tooltip=[alt.Tooltip(x_col, bin=True, title=x_col), 'count()']
    )
    
    if color_col and color_col != "Nenhum":
        base = base.encode(
            color=alt.Color(color_col, title=color_col)
        )
    
    return base.interactive()

def create_boxplot(df: pd.DataFrame, x_col: str, y_col: str):
    """Gera um boxplot (Qualitativo vs Distribuição Quantitativa)."""
    
    chart = alt.Chart(df).mark_boxplot().encode(
        x=alt.X(x_col, title=x_col),
        y=alt.Y(y_col, title=y_col),
        tooltip=[
            alt.Tooltip(x_col, title=x_col),
            alt.Tooltip(f'q1({y_col})', title=f'1º Quartil {y_col}'),
            alt.Tooltip(f'median({y_col})', title=f'Mediana {y_col}'),
            alt.Tooltip(f'q3({y_col})', title=f'3º Quartil {y_col}'),
        ]
    ).interactive()
    
    return chart