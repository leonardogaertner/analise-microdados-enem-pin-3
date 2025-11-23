import os
import json
import streamlit as st

@st.cache_data(show_spinner=False)
def carregar_geojson_local(filename):
    """ Carrega dados GeoJSON de um arquivo local. """
    try:
        script_dir = os.path.dirname(__file__) if "__file__" in locals() else os.getcwd()
        filepath = os.path.join(script_dir, 'Dashboards', 'resources', filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error(f"Arquivo GeoJSON '{filename}' não encontrado na pasta do script ({script_dir}). Faça o download e salve-o lá.")

        try:
             with open(filename, 'r', encoding='utf-8') as f:
                  st.info(f"Carregado GeoJSON de: {os.path.abspath(filename)}")
                  return json.load(f)
        except Exception:
             return None
    except json.JSONDecodeError as e:
        st.error(f"Erro ao decodificar GeoJSON local '{filename}': {e}")
        return None
    except Exception as e:
        st.error(f"Erro inesperado ao carregar GeoJSON local '{filename}': {e}")
        return None