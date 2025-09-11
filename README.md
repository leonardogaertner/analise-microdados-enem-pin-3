# 📊 Análise de Microdados do ENEM

Este repositório reúne a aplicação desenvolvida para análise dos **microdados do ENEM (Exame Nacional do Ensino Médio)**, disponibilizados pelo INEP.
O projeto tem como objetivo explorar e interpretar os dados, gerando estatísticas e visualizações.

## 🛠️ Tecnologias

- Python
- Streamlit

## 🎲 Criação do banco de dados
- Acessar o diretório `scripts` e descompactar o arquivo `database-script.zip`;
- O diretório contém uma amostra dos dados de cada ano, juntamente com um README.md explicando as regras aplicadas ao dados e um script.py que, ao ser executado, lê os arquivos .csv dentro da pasta e envia para o banco de dados ;

## ⚙️ Execução
- Para instalar as dependências, execute o comando `pip install -r requirements.txt`;
- Para iniciar a aplicação, execute `streamlit run app.py`;

Observação: ao utilizar novas dependências, execute o comando `pip freeze > requirements.txt` para realizar a sincronização das versões corretas.
