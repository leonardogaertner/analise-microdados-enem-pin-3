# ===================================================================
# DICIONÁRIO DOS NOMES DAS COLUNAS
# ===================================================================
COLUMN_MAPPING = {
    "CO_MUNICIPIO_ESC": "Cód. Município Escola", # Valor tipo ID
    "CO_MUNICIPIO_PROVA": "Cód. do Município da Prova", # Valor tipo ID
    "CO_PROVA_CH": "Cód. da Prova de História", # Valor tipo ID
    "CO_PROVA_CN": "Cód. da Prova de Ciências da Natureza", # Valor tipo ID
    "CO_PROVA_LC": "Cód. da Prova de Linguagens e Códigos", # Valor tipo ID
    "CO_PROVA_MT": "Cód. da Prova de Matemática", # Valor tipo ID
    "CO_UF_ENTIDADE_CERTIFICACAO": "Cód. UF Certificação", # Valor tipo ID
    "CO_UF_ESC": "Cód. da UF da Escola", # Valor tipo ID
    "CO_UF_PROVA": "Cód. da UF da Prova", # Valor tipo ID
    "ESCOLARIDADE_PAIS_AGRUPADO": "Escolaridade dos Pais",  # Um conjunto de 9 opções: completou a 4a série; completou a 8a série; completou a faculdade; completou a pós graduação; completou o ensino médio; não completou a 4a serie; não informado; não sabe.
    "FLAG_CANDIDATO_ADULTO": "Adulto?", # tipo: SIM ou NÂO
    "FLAG_CAPITAL": "Candidato realizou a prova na capital do estado?",# tipo: SIM ou NÂO
    "INDICADOR_ABSENTEISMO": "Presença", # Ausente em 1 ou mais dias; Eliminado; Presente
    "INDICADOR_REDACAO_ZERADA": "Redação Zerada?", # N/A; Não; Sim
    "INDICE_ACESSO_TECNOLOGIA": "Acesso à Tecnologia", # Select com 4 opções: Acesso completo, apenas computador, apenas internet; nenhum acesso
    "IN_CERTIFICADO": "Certificado?", # tipo: 0 ou 1
    "IN_TREINEIRO": "Treineiro?", # tipo: 0 ou 1
    "MEDIA_GERAL": "Média Geral", # numérico
    "MEDIA_OBJETIVAS": "Média Questões Objetivas", # numérico
    "NO_ENTIDADE_CERTIFICACAO": "Nome Entidade Certificação", # um ID na forma de Texto
    "NOME_MUNICIPIO_ESC": "Nome do Município da Escola", # numérico
    "NOME_MUNICIPIO_PROVA": "Nome do Município da Prova", # um ID na forma de Texto, um para cada estado do Brasil
    "NU_ANO": "Ano", # numérico, de 2014 até 2023
    "NU_INSCRICAO": "Nº de Inscrição", # Id, um para cada candidato
    "NU_NOTA_CH": "Nota de História", # numérico
    "NU_NOTA_CN": "Nota de Ciências da Natureza",# numérico
    "NU_NOTA_COMP1": "Nota Competência 1", # numérico
    "NU_NOTA_COMP2": "Nota Competência 2", # numérico
    "NU_NOTA_COMP3": "Nota Competência 3", # numérico
    "NU_NOTA_COMP4": "Nota Competência 4", # numérico
    "NU_NOTA_COMP5": "Nota Competência 5", # numérico
    "NU_NOTA_LC": "Nota de Linguagens e Códigos", # numérico
    "NU_NOTA_MT": "Nota de Matemática", # numérico
    "NU_NOTA_REDACAO": "Nota da Redação", # numérico
    "REGIAO_CANDIDATO": "Região do Candidato", # select com 5 opções: Centro-oeste, nordeste, norte, sudeste, sul
    "REGIAO_ESCOLA": "Região da Escola do Candidato", # select com 5 opções: Centro-oeste, nordeste, norte, sudeste, sul
    "RENDA_FAMILIAR": "Renda Familiar", # Faixa de renda: até 1 salário; de 1-1,5 salário;...;de 9-10 salário; mais de 20 salários mínimos;
    "SG_UF_ENTIDADE_CERTIFICACAO": "UF Entidade Certificação", # select: um para cada estado do Brasil
    "SG_UF_ESC": "Sigla da UF da Escola", # select: um para cada estado do Brasil
    "SG_UF_PROVA": "Sigla da UF da Prova", # select: um para cada estado do Brasil
    "TEMPO_FORA_ESCOLA": "Tempo Fora da Escola", # select com intervalos assim como no salário mínimo
    "TIPO_ESCOLA_AGRUPADO": "Tipo da Escola", # select
    "TP_ANO_CONCLUIU": "Ano de Conclusão", # Ano de conclusão
    "TP_COR_RACA": "Cor/Raça", # tipo: 1 a 6
    "TP_DEPENDENCIA_ADM_ESC": "Tipo de Dependência Administrativa da Escola", # tipo: 1,2,3,4
    "TP_ENSINO": "Tipo de Ensino", # tipo: 1 a 4
    "TP_ESCOLA": "Tipo de Escola", # tipo: 1 a 4
    "TP_ESTADO_CIVIL": "Estado Civil", # tipo: 0 a 4
    "TP_FAIXA_ETARIA": "Faixa Etária", # tipo: 1 a 20
    "TP_LINGUA": "Tipo de Língua",  # tipo: 0 ou 1
    "TP_LOCALIZACAO_ESC": "Localização da Escola",  # tipo: 1 ou 2
    "TP_NACIONALIDADE": "Nacionalidade",  # tipo: 0 a 4
    "TP_PRESENCA_CH": "Presença em História", # tipo: 0 a 2
    "TP_PRESENCA_CN": "Presença em Ciências da Natureza", # tipo: 0 a 2
    "TP_PRESENCA_LC": "Presença em Linguagens e Códigos", # tipo: 0 a 2
    "TP_PRESENCA_MT": "Presença em Matemática", # tipo: 0 a 2
    "TP_SEXO": "Sexo",  # tipo: M ou F
    "TP_SIT_FUNC_ESC": "Situação Funcional da Escola",  # tipo: 1 a 4
    "TP_STATUS_REDACAO": "Status da Redação",  # tipo: 1 a 98
    "TP_ST_CONCLUSAO": "Situação de Conclusão",  # tipo: 1 a 4
    "TX_GABARITO_CH": "Gabarito de História", #desconsidere
    "TX_GABARITO_CN": "Gabarito de Ciências da Natureza", #desconsidere
    "TX_GABARITO_LC": "Gabarito de Linguagens e Códigos", #desconsidere
    "TX_GABARITO_MT": "Gabarito de Matemática", #desconsidere
    "TX_RESPOSTAS_CH": "Respostas de História", #desconsidere
    "TX_RESPOSTAS_CN": "Respostas de Ciências da Natureza", #desconsidere
    "TX_RESPOSTAS_LC": "Respostas de Linguagens e Códigos", #desconsidere
    "TX_RESPOSTAS_MT": "Respostas de Matemática", #desconsidere
}