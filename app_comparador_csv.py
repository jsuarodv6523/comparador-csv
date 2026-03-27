import io
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Comparador de CSV", layout="wide")
st.title("Comparador de archivos CSV")
st.caption("Sube dos archivos CSV, elige el separador y descarga un Excel con las diferencias.")

def read_csv_with_option(uploaded_file, sep_option):
    raw = uploaded_file.getvalue()
    encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]
    last_error = None

    for enc in encodings:
        try:
            if sep_option == "Automático":
                df = pd.read_csv(io.BytesIO(raw), encoding=enc, sep=None, engine="python")
            elif sep_option == "Punto y coma (;)":
                df = pd.read_csv(io.BytesIO(raw), encoding=enc, sep=";")
            else:
                df = pd.read_csv(io.BytesIO(raw), encoding=enc, sep=",")
            return df
        except Exception as e:
            last_error = e

    raise last_error

def normalize_df(df):
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = (
                df[col]
                .astype(str)
                .str.strip()
                .replace({"nan": "", "None": "", "<NA>": ""})
            )
    return df

def compare_dataframes(df1, df2, key):
    df1 = df1.copy()
    df2 = df2.copy()

    df1[key] = df1[key].astype(str).str.strip()
    df2[key] = df2[key].astype(str).str.strip()

    df1 = df1.drop_duplicates(subset=[key], keep="first").set_index(key)
    df2 = df2.drop_duplicates(subset=[key], keep="first").set_index(key)

    only_1 = df1.loc[~df1.index.isin(df2.index)].reset_index()
    only_2 = df2.loc[~df2.index.isin(df1.index)].reset_index()

    common_ids = df1.index.intersection(df2.index)
    common_cols = sorted(set(df1.columns).intersection(df2.columns))

    iguales = []
    cambios = []

    for idx in common_ids:
        row1 = df1.loc[idx]
        row2 = df2.loc[idx]
        diferencias = {}

        for col in common_cols:
            v1 = "" if pd.isna(row1[col]) else str(row1[col])
            v2 = "" if pd.isna(row2[col]) else str(row2[col])

            if v1 != v2:
                diferencias[f"{col}_archivo_1"] = v1
                diferencias[f"{col}_archivo_2"] = v2

        if diferencias:
            diferencias[key] = idx
            cambios.append(diferencias)
        else:
            iguales.append({key: idx})

    return pd.DataFrame(iguales), pd.DataFrame(cambios), only_1, only_2

def to_excel_bytes(resumen, iguales, cambios, solo1, solo2):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        resumen.to_excel(writer, sheet_name="Resumen", index=False)
        iguales.to_excel(writer, sheet_name="Iguales", index=False)
        cambios.to_excel(writer, sheet_name="Cambios", index=False)
        solo1.to_excel(writer, sheet_name="Solo_archivo_1", index=False)
        solo2.to_excel(writer, sheet_name="Solo_archivo_2", index=False)
    output.seek(0)
    return output.getvalue()

file1 = st.file_uploader("Archivo 1", type=["csv"])
sep1 = st.selectbox("Separador archivo 1", ["Automático", "Punto y coma (;)", "Coma (,)"], index=0)

file2 = st.file_uploader("Archivo 2", type=["csv"])
sep2 = st.selectbox("Separador archivo 2", ["Automático", "Punto y coma (;)", "Coma (,)"], index=0)

if file1 and file2:
    try:
        df1 = normalize_df(read_csv_with_option(file1, sep1))
        df2 = normalize_df(read_csv_with_option(file2, sep2))
    except Exception as e:
        st.error(f"No pude leer alguno de los archivos: {e}")
        st.stop()

    st.subheader("Vista previa")
    c1, c2 = st.columns(2)
    with c1:
        st.write(f"Archivo 1: {len(df1)} filas y {len(df1.columns)} columnas")
        st.dataframe(df1.head(10), use_container_width=True)
    with c2:
        st.write(f"Archivo 2: {len(df2)} filas y {len(df2.columns)} columnas")
        st.dataframe(df2.head(10), use_container_width=True)

    comunes = [c for c in df1.columns if c in df2.columns]

    if not comunes:
        st.error("No encontré columnas en común entre ambos archivos.")
        st.stop()

    key = st.selectbox("Columna clave para comparar", comunes)

    if st.button("Comparar"):
        iguales, cambios, solo1, solo2 = compare_dataframes(df1, df2, key)

        resumen = pd.DataFrame([
            {"Métrica": "Coincidencias exactas", "Valor": len(iguales)},
            {"Métrica": "Registros con cambios", "Valor": len(cambios)},
            {"Métrica": "Solo en archivo 1", "Valor": len(solo1)},
            {"Métrica": "Solo en archivo 2", "Valor": len(solo2)},
        ])

        st.success("Comparación completada")

        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Coincidencias", len(iguales))
        r2.metric("Con cambios", len(cambios))
        r3.metric("Solo archivo 1", len(solo1))
        r4.metric("Solo archivo 2", len(solo2))

        if not cambios.empty:
            st.subheader("Cambios detectados")
            st.dataframe(cambios, use_container_width=True)

        excel_data = to_excel_bytes(resumen, iguales, cambios, solo1, solo2)

        st.download_button(
            "Descargar informe en Excel",
            data=excel_data,
            file_name="resultado_comparacion.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
else:
    st.info("Sube los dos archivos CSV para empezar.")
