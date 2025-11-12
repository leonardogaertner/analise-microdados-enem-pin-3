import pandas as pd
import numpy as np
from fpdf import FPDF

def dataframe_to_pdf_bytes(df: pd.DataFrame) -> bytes:
    """
    Converte um DataFrame do Pandas em um PDF formatado de forma elegante.
    
    Recursos:
    - Orientação Paisagem (Landscape)
    - Título do Relatório
    - Larguras de coluna proporcionais e inteligentes
    - Cabeçalhos repetidos em cada página
    - Cores de linha alternadas
    - Alinhamento de texto (Números à direita, Texto à esquerda)
    - Truncamento de texto longo ("...")
    """
    
    # --- 1. Inicialização e Configurações de Layout ---
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(True, margin=15) # Margem inferior para o page break
    pdf.add_page()
    
    # Define fontes e alturas
    title_font_size = 16
    header_font_size = 10
    body_font_size = 9
    
    # Alturas de linha baseadas no tamanho da fonte (com um pouco de preenchimento)
    header_line_height = header_font_size * 1.3
    body_line_height = body_font_size * 1.3
    
    page_width = pdf.w - 2 * pdf.l_margin
    bottom_margin = 15 # Margem inferior (igual ao auto_page_break)
    
    df_str = df.fillna('N/A').astype(str)

    # --- 2. Cálculo Inteligente da Largura das Colunas ---
    char_widths = {}
    for col in df_str.columns:
        header_len = len(col)
        
        sample_rows = min(len(df_str), 100)
        if sample_rows > 0:
            max_content_len = df_str[col].sample(sample_rows, random_state=1).apply(len).max()
        else:
            max_content_len = 0
        
        base_char_len = max(header_len + 2, max_content_len) 
        char_widths[col] = max(8, min(base_char_len, 40))

    total_char_width = sum(char_widths.values())
    col_width_mm = {}
    for col in df_str.columns:
        proportion = char_widths[col] / total_char_width
        col_width_mm[col] = proportion * page_width

    # --- 3. Função Auxiliar para Truncar Texto ---
    def truncate_text(text, width_mm):
        text_width = pdf.get_string_width(text)
        padding = 2 
        
        if text_width <= (width_mm - padding):
            return text
        
        text += "..."
        while pdf.get_string_width(text) > (width_mm - padding):
            if len(text) <= 4: 
                text = "..." 
                break
            text = text[:-4] + "..." 
        return text

    # --- 4. Função Auxiliar para Renderizar o Cabeçalho ---
    def render_header():
        pdf.set_font("Arial", "B", header_font_size)
        pdf.set_fill_color(220, 220, 220) 
        pdf.set_text_color(0, 0, 0)
        for col_header in df.columns:
            pdf.cell(col_width_mm[col_header], header_line_height, col_header, border=1, align='C', fill=True)
        pdf.ln(header_line_height)

    # --- 5. Renderizar o Título ---
    pdf.set_font("Arial", "B", title_font_size)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, "Relatório de Dados Filtrados", 0, 1, 'C')
    pdf.ln(5) 

    # --- 6. Renderizar o Primeiro Cabeçalho ---
    render_header()
    
    # --- 7. Renderizar o Corpo da Tabela ---
    pdf.set_font("Arial", "", body_font_size)
    fill_row = False 

    for _, row in df.iterrows(): 
        
        if pdf.get_y() > (pdf.h - bottom_margin - body_line_height):
            pdf.add_page()
            render_header()
            pdf.set_font("Arial", "", body_font_size) 
            fill_row = False 
            
        if fill_row:
            pdf.set_fill_color(245, 245, 245) 
        else:
            pdf.set_fill_color(255, 255, 255) 
        
        for col in df.columns:
            val = row[col]
            w = col_width_mm[col]
            
            align = 'L' 
            if pd.isna(val):
                display_val = 'N/A'
            elif isinstance(val, (int, float, complex, np.number)):
                align = 'R' 
                try:
                    if float(val) == int(val):
                        display_val = f"{int(val):}"
                    else:
                        display_val = f"{float(val):,.2f}" 
                except (ValueError, TypeError):
                    display_val = f"{val:,.2f}" 
            else:
                display_val = str(val)
            
            text_to_render = truncate_text(display_val, w)
            pdf.cell(w, body_line_height, text_to_render, border=1, align=align, fill=True)
        
        pdf.ln(body_line_height)
        fill_row = not fill_row 

    # --- 8. Retorna o PDF como bytes ---
    return pdf.output(dest='S').encode('latin-1')