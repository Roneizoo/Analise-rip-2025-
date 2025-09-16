# -*- coding: utf-8 -*-
"""
Análise de RIP 2025
App Streamlit para exibir 'rip.xlsx' com:
- Tabela com estilo Excel listrado (Zebu azul claro, Híbrido laranja claro)
- Números com 2 casas decimais e centralização
- Seleção múltipla de indicadores para a tabela
- Gráfico com apenas os dois primeiros indicadores (linha + barras)
"""

import os
import unicodedata
import pandas as pd
import streamlit as st
import altair as alt
from streamlit.components.v1 import html

st.set_page_config(page_title="Análise de RIP 2025", layout="wide")
st.title("📊 Análise de RIP 2025")

# ===== funções utilitárias =====
def _strip_accents(s: str) -> str:
    s = unicodedata.normalize("NFD", s)
    return "".join(ch for ch in s if unicodedata.category(ch) != "Mn")

def canonical_month(name: str) -> str:
    if not isinstance(name, str):
        return str(name)
    s = _strip_accents(name).strip().lower()
    key = s[:3]
    mapa = {
        "jan": "Janeiro","fev": "Fevereiro","mar": "Marco","abr": "Abril",
        "mai": "Maio","jun": "Junho","jul": "Julho","ago": "Agosto",
        "set": "Setembro","out": "Outubro","nov": "Novembro","dez": "Dezembro"
    }
    return mapa.get(key, name)

# ===== caminho do arquivo =====
base_dir = os.path.dirname(os.path.abspath(__file__))
arquivo_excel = os.path.join(base_dir, "rip.xlsx")
if not os.path.isfile(arquivo_excel):
    st.error("Arquivo 'rip.xlsx' não foi encontrado na pasta do app.")
    st.stop()

# ===== ler planilha =====
df = pd.read_excel(arquivo_excel, sheet_name=0, header=0)
df.dropna(how="all", inplace=True)
df.dropna(axis=1, how="all", inplace=True)
df.reset_index(drop=True, inplace=True)

# ===== renomear colunas em pares (Mês.Hibrido / Mês.Zebu) =====
orig = list(df.columns)
indicador_col = orig[0]
mes_cols = list(orig[1:])
if len(mes_cols) % 2 != 0:
    st.warning("Número de colunas de meses é ímpar. A última coluna será ignorada.")
    mes_cols = mes_cols[:-1]

novos_nomes = [indicador_col]
for i in range(0, len(mes_cols), 2):
    mes_canon = canonical_month(mes_cols[i])
    novos_nomes.append(f"{mes_canon}.Hibrido")
    novos_nomes.append(f"{mes_canon}.Zebu")
df.columns = novos_nomes

# ===== converter para formato longo =====
id_vars = [indicador_col]
df_long = df.melt(id_vars=id_vars, var_name="Mes_Raca", value_name="Valor")
df_long[["Mes_nome","Raca"]] = df_long["Mes_Raca"].str.split(".", n=1, expand=True)
df_long.drop(columns=["Mes_Raca"], inplace=True)

# manter apenas Zebu e Hibrido
df_final = df_long[df_long["Raca"].isin(["Zebu","Hibrido"])].copy()

# ===== ordem natural dos meses =====
ordem_meses = [
    "Janeiro","Fevereiro","Marco","Abril","Maio","Junho",
    "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"
]
meses_disponiveis = [m for m in ordem_meses if m in df_final["Mes_nome"].unique()]

# ===== filtros =====
indicadores = sorted(df_final[indicador_col].dropna().unique())
racas = ["Zebu","Hibrido"]

indicadores_selec = st.multiselect(
    "Escolha indicadores para a tabela (os 2 primeiros serão usados no gráfico)",
    indicadores,
    default=[indicadores[0], indicadores[1]]
)

meses_escolhidos = st.multiselect("Meses", meses_disponiveis, default=meses_disponiveis)
racas_escolhidas = st.multiselect("Raças", racas, default=racas)

if len(indicadores_selec) < 2:
    st.warning("Selecione pelo menos dois indicadores para gerar o gráfico.")
    st.stop()

# ===== montar tabela com N indicadores =====
df_merge = None
for ind in indicadores_selec:
    df_ind = df_final[
        (df_final[indicador_col] == ind) &
        (df_final["Mes_nome"].isin(meses_escolhidos)) &
        (df_final["Raca"].isin(racas_escolhidas))
    ][["Mes_nome","Raca","Valor"]].rename(columns={"Valor":f"Valor_{ind}"})
    df_merge = df_ind if df_merge is None else pd.merge(df_merge, df_ind,
                    on=["Mes_nome","Raca"], how="outer")

if df_merge is None or df_merge.empty:
    st.warning("Nenhum dado corresponde aos filtros selecionados.")
    st.stop()

df_merge["Mes_nome"] = pd.Categorical(df_merge["Mes_nome"],
                                      categories=meses_escolhidos, ordered=True)
df_merge.sort_values(["Mes_nome","Raca"], inplace=True)

# ===== arredondar valores e garantir 2 casas decimais =====
df_show = df_merge.copy()
for col in df_show.columns:
    if pd.api.types.is_numeric_dtype(df_show[col]):
        df_show[col] = df_show[col].apply(lambda x: round(x, 2) if pd.notnull(x) else x)

st.subheader("Tabela comparativa com múltiplos indicadores")

def color_row_by_race(row):
    if row["Raca"] == "Zebu":
        return ["background-color: #e6f2ff;" for _ in row]
    elif row["Raca"] == "Hibrido":
        return ["background-color: #fff2e6;" for _ in row]
    else:
        return ["" for _ in row]

format_dict = {
    col: "{:.2f}".format
    for col in df_show.columns
    if pd.api.types.is_numeric_dtype(df_show[col])
}

# ===== gerar HTML com CSS completo (centralização + 2 casas) =====
html_table = (
    df_show
    .style
    .format(format_dict, precision=2)
    .apply(color_row_by_race, axis=1)
    .set_table_styles([
        {"selector": "th", "props": [("text-align", "center"),
                                     ("background-color", "#f2f2f2"),
                                     ("color", "black")]},
        {"selector": "td", "props": [("text-align", "center"),
                                     ("color", "black")]}
    ])
    .to_html()
)

# exibir a tabela já com o CSS aplicado
html(html_table, height=600, scrolling=True)

# ===== gráfico apenas com os 2 primeiros indicadores selecionados =====
indicador1, indicador2 = indicadores_selec[:2]
st.subheader(f"Gráfico: {indicador1} (linha de tendência) + {indicador2} (barras)")

df_line = df_show[["Mes_nome","Raca",f"Valor_{indicador1}"]].rename(
    columns={f"Valor_{indicador1}":"Valor"}
)
df_bar = df_show[["Mes_nome","Raca",f"Valor_{indicador2}"]].rename(
    columns={f"Valor_{indicador2}":"Valor"}
)

cores_raca = alt.Scale(domain=["Zebu","Hibrido"], range=["#6BAED6", "#FDAE6B"])

bars = (
    alt.Chart(df_bar)
    .mark_bar(opacity=0.7)
    .encode(
        x=alt.X("Mes_nome:N", sort=meses_escolhidos, title="Mês"),
        xOffset=alt.XOffset("Raca:N", scale=alt.Scale(padding=0.2)),
        y=alt.Y("Valor:Q", title=f"{indicador2} (barras)"),
        color=alt.Color("Raca:N", scale=cores_raca, legend=alt.Legend(title="Raça")),
        tooltip=["Mes_nome","Raca","Valor"]
    )
)

line = (
    alt.Chart(df_line)
    .mark_line(point=True, size=3)
    .encode(
        x=alt.X("Mes_nome:N", sort=meses_escolhidos),
        y=alt.Y("Valor:Q", title=f"{indicador1} (linha)"),
        color=alt.Color("Raca:N", scale=cores_raca, legend=None),
        tooltip=["Mes_nome","Raca","Valor"]
    )
)

chart = alt.layer(bars, line).resolve_scale(y='independent')
st.altair_chart(chart, use_container_width=True)
