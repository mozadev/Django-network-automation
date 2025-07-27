import streamlit as st
from data import autenticar, upload_file, get_datetime, filtro, registros_analisis, get_anexos_missing, get_change_status_of_anexos
import pandas as pd
import config
import re
from time import sleep

def mostrar_login():
    st.title("🔐 Iniciar sesión")

    usuario = st.text_input("Usuario")
    contrasena = st.text_input("Contraseña", type="password")

    if st.button("Iniciar sesión", type="primary"):
        if autenticar(usuario, contrasena):
            st.success("✅ Login exitoso")
            st.session_state["logueado"] = True
            st.session_state["usuario"] = usuario
            st.session_state["password"] = contrasena
            st.rerun()
        else:
            st.error("❌ Usuario o contraseña incorrectos")

def principal():
    ahora = get_datetime()
    st.title(":material/fax: ANEXOS - MINPUB")

    if "subiendo" not in st.session_state:
        st.session_state.subiendo = False
    if "subido" not in st.session_state:
        st.session_state.subido = False
    if "documento_inicial" not in st.session_state:
        st.session_state.documento_inicial = None
    if "documento_final" not in st.session_state:
        st.session_state.documento_final = None
    if "documentos_filtrados" not in st.session_state:
        st.session_state.documentos_filtrados = None
    if "documentos_id" not in st.session_state:
        st.session_state.documentos_id = ""
    if "search" not in st.session_state:
        st.session_state.search = False
    if "list_documentos" not in st.session_state:
        st.session_state.list_documentos = []
    if "location" not in st.session_state:
        st.session_state.location = ""
    if "anexo" not in st.session_state:
        st.session_state.anexo = ""

    if st.session_state.subido:
        st.toast("Archivo subido con exito. Cerrando dialogo ...")
        st.session_state.subido = False
        st.rerun()

    with st.sidebar:
        st.image("logo_anexos.png")
        st.markdown("## :material/fax: ANEXOS - MINPUB")
        st.success("🟢 Sistema en línea")

        with st.container(border=True):
            sidebar1, sidebar2 = st.columns(2)
            with sidebar1:
                st.write("Filtra Datos")
                if st.button("FILTRAR", type="secondary", icon=":material/tune:", use_container_width=True):
                    st.session_state.search = False
                    filtro()

            with sidebar2:
                st.write("Ingresar datos")
                if st.button("UPLOAD", type="secondary", icon=":material/upload_file:", use_container_width=True):
                    upload_file()
        st.success(f"👤 Sesión iniciada como: **{st.session_state.usuario}**")
        st.caption(f"📅 Última actualización: {ahora.strftime('%d %b %Y, %H:%M:%S')}")
        if st.sidebar.button("Cerrar sesión"):
            st.session_state.clear()
            st.cache_data.clear()
            st.rerun()
    sleep(0.5)
    if st.session_state.search:
        datos = st.session_state.documentos_filtrados
        if datos is not None:
            datos = pd.DataFrame(datos)
            datos["creado_en"] = pd.to_datetime(datos["creado_en"]).dt.tz_convert(config.TZ)

            registros_filtros = f"/anexo/registro/?anexo__in={st.session_state.anexo}&documento__in={st.session_state.documentos_id}&location={st.session_state.location}"
            if st.session_state.location != "":
                if not re.fullmatch(r"[\w ]+", st.session_state.location):
                    st.error(icon=":material/error:", body="Solo se permite una location")
                    st.stop()


            st.markdown(f"## :small_blue_diamond: Lista de Documentos Filtrados {st.session_state.location.upper()}")

            with st.expander("Ver Documentos Filtrados"):
                st.metric(label="Cantidad de Documentos Filtrados", value=datos.shape[0], delta=None, border=True)
                st.dataframe(datos,
                            height=200, 
                            use_container_width=True, 
                            hide_index=True,
                            column_order=["id", "creado_en", "archivo", "usuario_nombre"],
                            column_config={
                                "archivo": st.column_config.LinkColumn("Archivo", help="Link de los archivos"),
                                "creado_en": st.column_config.DatetimeColumn("Fecha", format="D MMM YYYY, h:mm a", help="Fecha del archivo subido"),
                                "usuario_nombre": st.column_config.TextColumn("Usuario", help="Usuario que subió el archivo"),
                                "id": st.column_config.TextColumn("N°", help="ID del Documento subido"),
                                },
                            )
            
            st.markdown("## :small_blue_diamond: Lista de Anexos Filtrados")
            registros_analisis(filtros=registros_filtros)
            st.divider()
            st.markdown("## :small_blue_diamond: Lista de Anexos Faltantes por documento")
            get_anexos_missing(filtro_registros=registros_filtros)
            st.divider()
            st.markdown("## :small_blue_diamond: Anexos que cambiaron de status por documento")
            get_change_status_of_anexos(filtro_registros=registros_filtros)
        else:
            st.info("No se encontraron documentos")
    else:
        st.info(
            """
            No se ha filtrado ningún DATO   
            **Ir al boton :material/tune: Filtrar**  
            :point_left:
            """
            , icon="ℹ️"
        )
        st.session_state.search = False


st.set_page_config(page_title="ANEXOS - MINPUB", page_icon="claro.svg", layout="centered")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    [data-testid="stDeployButton"] {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)



if "logueado" not in st.session_state or not st.session_state["logueado"]:
    mostrar_login()
else:
    principal()