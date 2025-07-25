import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os
from pathlib import Path
from datetime import datetime
from tablesScript import BuscadorCodeunit
from config import AI_API_KEY, DEFAULT_REPOS_PATH


from ai_helper import AIHelper, create_ai_helper


def inicializar_session_state():
    """Inicializa todas las variables del session state"""
    if 'buscador' not in st.session_state:
        st.session_state.buscador = None
    
    if 'archivos_repetidos' not in st.session_state:
        st.session_state.archivos_repetidos = {}
    
    if 'todos_los_procedures' not in st.session_state:
        st.session_state.todos_los_procedures = {}
    
    if 'analisis_completado' not in st.session_state:
        st.session_state.analisis_completado = False

    if 'ai_helper' not in st.session_state:
        st.session_state.ai_helper = create_ai_helper(AI_API_KEY)
    
    if 'descripciones_procedures' not in st.session_state:
        st.session_state.descripciones_procedures = {}

def obtener_ruta_archivo(nombre_archivo):
    """
    Obtiene la ruta completa de un archivo desde los datos del buscador
    
    Args:
        nombre_archivo (str): Nombre del archivo a buscar
        
    Returns:
        str: Ruta completa del archivo o None si no se encuentra
    """
    if not st.session_state.buscador:
        return None
    
    if nombre_archivo in st.session_state.archivos_repetidos:
        primera_aparicion = st.session_state.archivos_repetidos[nombre_archivo]['archivos'][0]
        return primera_aparicion['archivo']['ruta_completa']
    
    archivos_unicos = getattr(st.session_state.buscador, 'archivos_unicos', {})
    if nombre_archivo in archivos_unicos:
        primera_aparicion = archivos_unicos[nombre_archivo]['archivos'][0]
        return primera_aparicion['archivo']['ruta_completa']
    
    return None

def generar_descripcion_procedure(nombre_procedure: str, info_procedure: dict, archivo_nombre: str) -> str:
    cache_key = f"{archivo_nombre}_{nombre_procedure}"
    
    # Verificar si ya tenemos la descripción en cache
    if cache_key in st.session_state.descripciones_procedures:
        return st.session_state.descripciones_procedures[cache_key]
    
    # Verificar si IA está disponible
    if not st.session_state.ai_helper.is_available():
        descripcion = "❌ IA no disponible"
        st.session_state.descripciones_procedures[cache_key] = descripcion
        return descripcion
    
    # Obtener información del procedure
    apariciones = info_procedure.get('apariciones', [])
    if not apariciones:
        descripcion = "❌ Sin información de apariciones"
        st.session_state.descripciones_procedures[cache_key] = descripcion
        return descripcion
    
    # Para procedures repetidos, usar la primera aparición
    primera_aparicion = apariciones[0]
    linea_procedure = primera_aparicion.get('linea', '')
    ruta_archivo = primera_aparicion.get('ruta_archivo', '')
    numero_linea = primera_aparicion.get('numero_linea', 0)
    
    # Generar descripción con IA
    descripcion = st.session_state.ai_helper.get_procedure_analysis(
        nombre_procedure=nombre_procedure,
        linea_procedure=linea_procedure,
        ruta_archivo=ruta_archivo,
        numero_linea=numero_linea
    )
    
    # Guardar en cache
    st.session_state.descripciones_procedures[cache_key] = descripcion
    return descripcion

def mostrar_procedure_con_descripcion(nombre_procedure: str, info_procedure: dict, archivo_nombre: str, icono: str = "📌"):
    with st.expander(f"{icono} {nombre_procedure}"):
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.write(f"**Estado:** {info_procedure['estado']}")
            if info_procedure['estado'] == 'REPETIDO':
                st.write(f"**Repositorios:** {', '.join(info_procedure['repositorios'])}")
                st.write(f"**Total repositorios:** {info_procedure['total_repositorios']}")
            else:
                st.write(f"**Repositorio:** {info_procedure['repositorios'][0]}")
            
            st.markdown("**Código:**")
            for aparicion in info_procedure['apariciones']:
                modificador_str = f"[{aparicion['modificador']}] " if aparicion.get('modificador', 'public') != 'public' else ""
                if info_procedure['estado'] == 'REPETIDO':
                    st.code(f"{aparicion['repositorio']}: {modificador_str}{aparicion['linea']}")
                else:
                    st.code(f"{modificador_str}{aparicion['linea']}")
        
        with col2:
            if st.button(f"🤖 Analizar", key=f"btn_{archivo_nombre}_{nombre_procedure}"):
                cache_key = f"{archivo_nombre}_{nombre_procedure}"
                if cache_key in st.session_state.descripciones_procedures:
                    del st.session_state.descripciones_procedures[cache_key]
                with st.spinner("Analizando procedure..."):
                    descripcion = generar_descripcion_procedure(nombre_procedure, info_procedure, archivo_nombre)
        
        descripcion = generar_descripcion_procedure(nombre_procedure, info_procedure, archivo_nombre)
        
        if descripcion and not descripcion.startswith("❌"):
            st.success(f"🤖 **¿Qué hace?:** {descripcion}")
        elif descripcion.startswith("❌"):
            st.error(f"🤖 **Análisis:** {descripcion}")
        else:
            st.info("🤖 **Haz clic en 'Analizar' para obtener descripción con IA**")

def mostrar_info_archivo(archivo_seleccionado):
    ruta_archivo = obtener_ruta_archivo(archivo_seleccionado)
    
    if ruta_archivo:
        st.markdown("### 📁 Información del Archivo")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**Nombre:** {archivo_seleccionado}")
            st.write(f"**Ruta:** `{ruta_archivo}`")
        
        with col2:
            try:
                tamaño = os.path.getsize(ruta_archivo)
                st.write(f"**Tamaño:** {tamaño:,} bytes")
                
                modificado = datetime.fromtimestamp(os.path.getmtime(ruta_archivo))
                st.write(f"**Modificado:** {modificado.strftime('%Y-%m-%d %H:%M:%S')}")
            except:
                st.write("**Información adicional no disponible**")

def mostrar_descripcion_ia(archivo_seleccionado):
    st.markdown("### 🤖 Descripción General del Archivo")
    
    # Verificar si la IA está disponible
    if not st.session_state.ai_helper.is_available():
        st.error("❌ IA no disponible. Verifica la configuración de la API.")
        return
    
    # Obtener la ruta del archivo desde los datos del buscador
    ruta_archivo = obtener_ruta_archivo(archivo_seleccionado)
    
    if not ruta_archivo:
        st.error("❌ No se pudo obtener la ruta del archivo")
        return
    
    col_desc1, col_desc2 = st.columns([3, 1])
    
    with col_desc2:
        if st.button("🔄 Generar Descripción", key="btn_descripcion"):
            with st.spinner("Analizando archivo con IA..."):
                # Usar el nuevo método que lee el archivo completo
                descripcion = st.session_state.ai_helper.get_code_analysis_from_file(
                    ruta_archivo, archivo_seleccionado
                )
                st.session_state[f"descripcion_{archivo_seleccionado}"] = descripcion
    
    with col_desc1:
        if f"descripcion_{archivo_seleccionado}" in st.session_state:
            descripcion = st.session_state[f"descripcion_{archivo_seleccionado}"]
            st.info(f"📝 **Análisis de {archivo_seleccionado}:**\n\n{descripcion}")
        else:
            st.info("👆 Haz clic en 'Generar Descripción' para obtener análisis del archivo")

def crear_dashboard():
    st.set_page_config(
        page_title="Análisis de Procedures Codeunit.al",
        page_icon="📊",
        layout="wide"
    )
    
    inicializar_session_state()
    
    st.title("🔍 Análisis de Procedures Codeunit.al")
    st.markdown("---")
    
    st.sidebar.header("⚙️ Configuración")
    
    with st.sidebar.expander("🤖 Estado de IA"):
        if st.session_state.ai_helper.is_available():
            st.success("✅ IA Conectada")
        else:
            st.error("❌ IA No Disponible")
        
        total_descripciones = len(st.session_state.descripciones_procedures)
        st.info(f"📊 Descripciones en cache: {total_descripciones}")
        
        if st.button("🗑️ Limpiar Cache"):
            st.session_state.descripciones_procedures = {}
            st.success("Cache limpiado")
    
    ruta_repositorios = st.sidebar.text_input(
        "Ruta de repositorios:",
        value=DEFAULT_REPOS_PATH
    )
    
    if st.sidebar.button("🚀 Ejecutar Análisis"):
        with st.spinner("Analizando archivos..."):
            try:
                buscador = BuscadorCodeunit(ruta_repositorios)
                buscador.buscar_archivos()
                buscador.filtrar_archivos_repetidos()
                buscador.analizar_todos_los_procedures()
                
                st.session_state.buscador = buscador
                st.session_state.archivos_repetidos = buscador.filtrar_archivos_repetidos()[0]
                st.session_state.todos_los_procedures = buscador.obtener_todos_los_procedures()
                st.session_state.analisis_completado = True
                
                st.session_state.descripciones_procedures = {}
                
                st.success("✅ Análisis completado correctamente!")
            except Exception as e:
                st.error(f"❌ Error durante el análisis: {str(e)}")
                st.session_state.analisis_completado = False
    
    if st.session_state.analisis_completado:
        mostrar_resultados_interactivos()
    else:
        st.info("👆 Haz clic en 'Ejecutar Análisis' para comenzar")

def mostrar_resultados_interactivos():
    archivos_repetidos = st.session_state.archivos_repetidos
    todos_los_procedures = st.session_state.todos_los_procedures
    
    if not archivos_repetidos and not todos_los_procedures:
        st.warning("⚠️ No se encontraron archivos para analizar")
        return
    
    col1, col2, col3, col4 = st.columns(4)
    
    total_archivos = len(todos_los_procedures)
    total_procedures = sum(len(procedures) for procedures in todos_los_procedures.values())
    procedures_repetidos = sum(1 for procedures in todos_los_procedures.values() 
                          for procedure in procedures.values() if procedure['estado'] == 'REPETIDO')
    procedures_unicos = total_procedures - procedures_repetidos
    
    col1.metric("📁 Archivos Analizados", total_archivos)
    col2.metric("⚙️ Total Procedures", total_procedures)
    col3.metric("🔄 Procedures Repetidos", procedures_repetidos)
    col4.metric("⭐ Procedures Únicos", procedures_unicos)
    
    st.markdown("---")
    
    crear_grafico_resumen(todos_los_procedures)
    
    st.header("📄 Análisis Detallado por Archivo")
    
    archivo_seleccionado = st.selectbox(
        "Selecciona un archivo para ver detalles:",
        options=list(todos_los_procedures.keys()),
        key="selector_archivo"
    )
    
    if archivo_seleccionado:
        mostrar_info_archivo(archivo_seleccionado)
        
        mostrar_descripcion_ia(archivo_seleccionado)
        
        st.markdown("---")
        
        mostrar_detalles_archivo_mejorado(archivo_seleccionado, todos_los_procedures[archivo_seleccionado])

def crear_grafico_resumen(todos_los_procedures):
    st.header("📊 Resumen Visual")
    
    datos_resumen = []
    
    for archivo, procedures in todos_los_procedures.items():
        repetidos = sum(1 for c in procedures.values() if c['estado'] == 'REPETIDO')
        unicos = sum(1 for c in procedures.values() if c['estado'] == 'ÚNICO')
        
        datos_resumen.append({
            'Archivo': archivo,
            'Procedures Repetidos': repetidos,
            'Procedures Únicos': unicos,
            'Total': repetidos + unicos
        })
    
    if not datos_resumen:
        st.warning("No hay datos para mostrar en el gráfico")
        return
    
    df_resumen = pd.DataFrame(datos_resumen)
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Procedures Repetidos',
        x=df_resumen['Archivo'],
        y=df_resumen['Procedures Repetidos'],
        marker_color='#FF6B6B'
    ))
    
    fig.add_trace(go.Bar(
        name='Procedures Únicos',
        x=df_resumen['Archivo'],
        y=df_resumen['Procedures Únicos'],
        marker_color='#4ECDC4'
    ))
    
    fig.update_layout(
        title='Distribución de Procedures por Archivo',
        xaxis_title='Archivos',
        yaxis_title='Número de Procedures',
        barmode='stack',
        height=500
    )
    
    st.plotly_chart(fig, use_container_width=True)

def mostrar_detalles_archivo_mejorado(archivo, procedures):
    
    st.subheader(f"📄 {archivo}")
    
    tab1, tab2, tab3 = st.tabs(["🔄 Procedures Repetidos", "⭐ Procedures Únicos", "📊 Visualización"])
    
    with tab1:
        procedures_repetidos = {k: v for k, v in procedures.items() if v['estado'] == 'REPETIDO'}
        
        if procedures_repetidos:
            st.info(f"📊 **{len(procedures_repetidos)} procedures repetidos encontrados**")
            
            for nombre_procedure, info in procedures_repetidos.items():
                mostrar_procedure_con_descripcion(
                    nombre_procedure=nombre_procedure,
                    info_procedure=info,
                    archivo_nombre=archivo,
                    icono="🔄"
                )
        else:
            st.info("No hay procedures repetidos en este archivo")
    
    with tab2:
        procedures_unicos = {k: v for k, v in procedures.items() if v['estado'] == 'ÚNICO'}
        
        if procedures_unicos:
            st.info(f"📊 **{len(procedures_unicos)} procedures únicos encontrados**")
            
            for nombre_procedure, info in procedures_unicos.items():
                mostrar_procedure_con_descripcion(
                    nombre_procedure=nombre_procedure,
                    info_procedure=info,
                    archivo_nombre=archivo,
                    icono="⭐"
                )
        else:
            st.info("No hay procedures únicos en este archivo")
    
    with tab3:
        repetidos = sum(1 for c in procedures.values() if c['estado'] == 'REPETIDO')
        unicos = sum(1 for c in procedures.values() if c['estado'] == 'ÚNICO')
        
        if repetidos + unicos > 0:
            fig = go.Figure(data=[go.Pie(
                labels=['Procedures Repetidos', 'Procedures Únicos'],
                values=[repetidos, unicos],
                hole=0.3,
                marker_colors=['#FF6B6B', '#4ECDC4']
            )])
            
            fig.update_layout(
                title=f'Distribución de Procedures en {archivo}',
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay datos suficientes para crear el gráfico")

if __name__ == "__main__":
    crear_dashboard()
