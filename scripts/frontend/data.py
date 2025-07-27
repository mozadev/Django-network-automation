import socket
import streamlit as st
import requests
from requests.auth import HTTPBasicAuth
import pandas as pd
import config
from datetime import datetime, timedelta
import time
import re


@st.cache_data(show_spinner=":material/search: Cargando la IPv4 del servidor ...")
def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()


@st.cache_data(show_spinner=":material/search: Obteniendo fecha ...")
def get_datetime():
    return datetime.now(config.TZ)


st.cache_data(show_spinner="Login ...")
def autenticar(usuario, contrasena):
    try:
        if "ip_server" not in st.session_state:
            st.session_state.ip_server = get_ip()
        
        response = requests.get(f"http://{st.session_state.ip_server}:{config.PORT}/anexo/anexo/", auth=HTTPBasicAuth(usuario, contrasena))

        if response.status_code == 200:
            return True
        else:
            return False
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return False
    

@st.cache_data(show_spinner=":material/pending: Cargando Todos los Documentos ...")
def get_all_documentos():
    archivos = []
    with st.spinner(":material/pending: Cargando documentos ..."):
        pag = 1
        while True:
            response_documentos = requests.get(f"http://{st.session_state.ip_server}:{config.PORT}/anexo/documento/?page={pag}", auth=HTTPBasicAuth(st.session_state.usuario, st.session_state.password))
            if response_documentos.status_code == 200:
                datos = response_documentos.json()
                item = datos.get("results", [])
                archivos.extend(item)
            else:
                break
            pag += 1

    if len(archivos) > 0:
        return pd.DataFrame(archivos, columns=["id", "usuario_nombre", "creado_en", "archivo"])
    else:
        return None
    

@st.cache_data(show_spinner=":material/search: Cargando Documentos Filtrados...")
def get_documentos(filter):
    archivos = []
    with st.spinner("Cargando documentos ... 1"):
        pag = 1
        while True:
            response_documentos = requests.get(f"http://{st.session_state.ip_server}:{config.PORT}/anexo/documento/?{filter}&page={pag}", auth=HTTPBasicAuth(st.session_state.usuario, st.session_state.password))
            if response_documentos.status_code == 200:
                datos = response_documentos.json()
                item = datos.get("results", [])
                archivos.extend(item)
            else:
                break
            pag += 1

    if len(archivos) > 0:
        return pd.DataFrame(archivos, columns=["id", "usuario_nombre", "creado_en", "archivo"])
    else:
        return None


@st.cache_data(show_spinner=":material/search: Cargando registros ...")
def get_registros(registros_filtros):
    registros_filtrados_list = []
    with st.spinner("Cargando documentos ... 3"):
        pag = 1
        while True:
            registros_response_filter = requests.get(f"http://{st.session_state.ip_server}:{config.PORT}{registros_filtros}&page={pag}&page_size=50000", auth=HTTPBasicAuth(st.session_state.usuario, st.session_state.password))
            if registros_response_filter.status_code == 200:
                datos = registros_response_filter.json()
                item = datos.get("results", [])
                registros_filtrados_list.extend(item)
            else:
                break
            pag += 1

    if len(registros_filtrados_list) > 0:
        registros = pd.DataFrame(registros_filtrados_list)
        registros["anexo_ip_address"] = registros["anexo_ip_address"].apply(lambda x: re.sub(r":\d+", "", str(x)) if pd.notnull(x) else x)
        return registros
    else:
        return None
    
@st.cache_data(show_spinner="GET ANEXOS")
def get_all_anexos():
    anexos_list = []
    with st.spinner("Cargando Anexos ... "):
        pag = 1
        while True:
            anexos_response_filter = requests.get(f"http://{st.session_state.ip_server}:{config.PORT}/anexo/anexo/?pk__in=&key__in={st.session_state.anexo}&location={st.session_state.location}&page={pag}&page_size=5000", auth=HTTPBasicAuth(st.session_state.usuario, st.session_state.password))
            if anexos_response_filter.status_code == 200:
                datos = anexos_response_filter.json()
                item = datos.get("results", [])
                anexos_list.extend(item)
            else:
                break
            pag += 1

    if len(anexos_list) > 0:
        return pd.DataFrame(anexos_list)
    else:
        return None
    

@st.dialog("Subir Archivo")
def upload_file():
    st.write("Subir el archivo")
    ahora = get_datetime()
    fecha = st.date_input(label="Fecha de ingreso", value=ahora.date(), format="DD/MM/YYYY")
    hora = st.time_input(label="Ingresar la hora", value=ahora.time())
    file = st.file_uploader("Ingresar Archivo")

    if st.button("Subir", icon=":material/upload_file:", type="primary"):
        if file:
            st.session_state.subiendo = True
            with st.spinner("Subiendo archivo ..."):
                try:
                    fecha_str = fecha.strftime("%Y-%m-%d")
                    hora_str = hora.strftime("%H:%M:%S")

                    files = {"archivo": (file.name, file, file.type)}
                    data = {"creado_en": f"{fecha_str} {hora_str}", "usuario": 1}
                    response = requests.post(f"http://{st.session_state.ip_server}:9000/anexo/documento/", data=data, files=files, auth=HTTPBasicAuth(st.session_state.usuario, st.session_state.password))

                    if response.status_code >= 200 and response.status_code < 300:
                        st.success("Archivo subido correctamente")
                        time.sleep(3)
                        st.session_state.subido = True
                        st.rerun()
                    else:
                        st.error(f"Error al subir: {response.status_code}, Detalles: {response.text}")
                        st.stop()
                except Exception as e:
                    st.error(f"Error de conexión: {e}")
                    st.session_state.subiendo = False
                    st.stop()
                    st.rerun()
            
            st.session_state.subiendo = False
            st.rerun()
        else:
            st.warning("Debes Seleccionar el archivo")



@st.dialog("Filtro")
def filtro():
    ahora = get_datetime()

    with st.container(border=True):
        st.write("Filtro de busqueda")
        tipo = st.radio("Tipo de busqueda", ["Fecha", "Documento"])
        st.write(f"Filtro por: **{tipo}**")

    if tipo == "Fecha":

        with st.container(border=True):
            left1, right1 = st.columns(2, vertical_alignment="top")
            with left1:
                fecha_inicial = st.date_input("Fecha Inicial", value=ahora.date() - timedelta(days=1), format="DD/MM/YYYY")
            with right1:
                hora_inicial = st.time_input(label="Ingresar la hora inicial", value=ahora.time())

        with st.container(border=True):
            left2, right2 = st.columns(2, vertical_alignment="top")
            with left2:
                fecha_final = st.date_input("Fecha Final", value=ahora.today(), format="DD/MM/YYYY")
            with right2:
                hora_final = st.time_input(label="Ingresar la hora final", value=ahora.time())


        st.session_state.documento_inicial = f"{fecha_inicial.strftime('%Y-%m-%d')} {hora_inicial.strftime('%H:%M:%S')}"
        st.session_state.documento_final = f"{fecha_final.strftime('%Y-%m-%d')} {hora_final.strftime('%H:%M:%S')}"
    else:
        archivos = get_all_documentos()
        if archivos is not None:
            df = pd.DataFrame(archivos, columns=["id", "usuario_nombre", "creado_en", "archivo"])

            df["creado_en"] = pd.to_datetime(df["creado_en"]).dt.tz_convert(config.TZ)

            on = st.toggle("Seleccionar todos", key="all_documentos")
            if on:
                df["Select"] = True
            else:
                df["Select"] = False

            seleccionados = st.data_editor(
                df,
                column_config={
                    "Select": st.column_config.CheckboxColumn("Select", help="Seleccionar los documentos"),
                    "archivo": st.column_config.LinkColumn("Archivo", help="Link de los archivos"),
                    "creado_en": st.column_config.DatetimeColumn("Fecha", format="D MMM YYYY, h:mm a"),
                    "usuario_nombre": st.column_config.TextColumn("Usuario", help="Usuario que subió el archivo"),
                },
                hide_index=True, 
                height=250, 
                use_container_width=True, 
                key="documentos",
                column_order=["Select", "id", "creado_en", "archivo", "usuario_nombre"],
                disabled=["id", "creado_en", "archivo", "usuario_nombre"],
                )

        else:
            st.info("No se encontraron datos Documentos")
    
    with st.container(border=True):
        st.text_input("Filtro por location", max_chars=30, key="location", placeholder="Solo se permite una sola location")
        st.text_input("Filtro por Anexo", max_chars=100, key="anexo", placeholder="Ingresar el Anexo, si son varios separalos por comas")

    if st.button("Buscar", type="primary", icon=":material/search:"):
        st.session_state.search = True
        if tipo == "Fecha":
            filtro_documento = f"pk__in=&creado_en_after={st.session_state.documento_inicial}&creado_en_before={st.session_state.documento_final}"
            st.session_state.documentos_id = ""
        else:
            if st.session_state.all_documentos:
                filtro_documento = f"pk__in=&creado_en_after=&creado_en_before="
                st.session_state.documentos_id = ""
            else:
                select = seleccionados[seleccionados["Select"]]
                ids = ",".join(map(str, select["id"].tolist()))
                st.session_state.documentos_id = ids
                filtro_documento = f"pk__in={ids}&creado_en_after=&creado_en_before="

        documentos_filtrados_list = get_documentos(filtro_documento)

        if documentos_filtrados_list is not None:
            st.session_state.documentos_filtrados = documentos_filtrados_list
        else:
            st.session_state.documentos_filtrados = None

        st.cache_data.clear()
        st.rerun()


def duration_caida(times, status):

    df = pd.DataFrame({'Tiempo': times, 'Status': status})
    if df.iloc[-1]['Status'] == False:
        true_indices = df[df['Status'] == True].index

        if len(true_indices) > 0:
            ultimo_true_idx = true_indices.max()
            if (ultimo_true_idx + 1) < len(df):
                tiempo_inicio_caida = df.loc[ultimo_true_idx + 1, 'Tiempo']
            else:
                tiempo_inicio_caida = df.iloc[-1]['Tiempo']
        else:
            tiempo_inicio_caida = df.iloc[0]['Tiempo']

        tiempo_actual = pd.Timestamp.now(tz=config.TZ)

        duracion_caida = tiempo_actual - tiempo_inicio_caida

        return tiempo_inicio_caida.strftime("%d %b %Y, %-I:%M %p").lower(), str(duracion_caida).split('.')[0]
    else:
        return "", ""


def get_caidas(historia, fechas):
    caidas = [{}]
    pares_historia = [ (historia[i], historia[i+1]) for i in range(len(historia)-1) ]

    for i, par in enumerate(pares_historia):
        if par == (1, 0):
            caidas.append({"inicio": i})
        elif par == (0, 1):
            caidas[-1]["final"] = i
    del caidas[0]

    result = []

    for caida in caidas:
        item = {}
        if "inicio" in caida and "final" in caida:
            inicio = caida["inicio"]
            final = caida["final"]
            fecha_inicio = fechas[inicio + 1]
            fecha_final = fechas[final + 1]
            item["fecha_inicio"] = fecha_inicio.strftime("%d %b %Y, %I:%M %p")
            item["fecha_final"] = fecha_final.strftime("%d %b %Y, %I:%M %p")
            item["duration"] = str(fecha_final - fecha_inicio)
            result.append(item)

    return result

@st.cache_data(show_spinner=":material/process_chart: Procesando DATA")
def registros_analisis(filtros):
    ahora = get_datetime()
    registros = get_registros(registros_filtros=filtros)
    if registros is None:
        st.info("No se encontraron registros")
        e = RuntimeError("No se encontraron registros")
        raise st.exception(e)
    
    registros = registros[["anexo_key", "anexo_login", "anexo_location", "anexo_ip_address", "anexo_device_mac", "anexo_device_serial", "documento_creado_en", "usuario", "status", "anexo", "documento"]]
    anexos = []

    for anexo, datos in registros.groupby('anexo'):
        item = {}
        datos["documento_creado_en"] = pd.to_datetime(datos["documento_creado_en"])
        datos.sort_values(by="documento_creado_en", ascending=True, inplace=True)
        item["anexo"]= datos["anexo_key"].iloc[-1]
        item["login"] = datos["anexo_login"].iloc[-1]
        item["location"] = datos["anexo_location"].iloc[-1]
        item["ip_address"] = datos["anexo_ip_address"].iloc[-1]
        item["device_mac"] = datos["anexo_device_mac"].iloc[-1]
        item["device_serial"] = datos["anexo_device_serial"].iloc[-1]
        item["last_status"] = datos["status"].iloc[-1]
        item["last_date"] = datos["documento_creado_en"].iloc[-1]
        item["fechas"] = datos["documento_creado_en"].tolist()
        item["historia"] = datos["status"].tolist()
        item["caida_inicio"], item["caida_duracion"] = duration_caida(item["fechas"], item["historia"])
        item["last_status"] = '✅' if item["last_status"] else '❌'
        item["caidas"] = get_caidas(item["historia"], item["fechas"]) 
        anexos.append(item)

    anexos_df = pd.DataFrame(anexos)
    anexos_df["historia"] = anexos_df["historia"].apply(lambda lista: [int(x) for x in lista])
    col1, col2, col3 = st.columns(3)
    col1.metric(label="Total de Anexos", 
                value="{value}".format(value=anexos_df.shape[0]),
                border=True
                )
    col2.metric(label="Cantidad en ✅",
                value="{value}".format(value=anexos_df[anexos_df["last_status"] == '✅'].shape[0]),
                border=True
                )
    col3.metric(label="Cantidad en ❌",
                value="{value}".format(value=anexos_df[anexos_df["last_status"] == '❌'].shape[0]),
                border=True
                )
    
    st.dataframe(
        anexos_df,
        height=400,
        hide_index=True,
        use_container_width=True,
        column_order=["anexo", "location", "caida_inicio", "caida_duracion", "last_status", "historia", "caidas", "ip_address", "device_mac", "device_serial"],
        column_config={
            "caida_inicio": st.column_config.TextColumn("Inicio", help="Inicio de la Caída del Anexo"),
            "caida_duracion": st.column_config.TextColumn("Caida", help=f"Duración de la Caída del Anexo hasta **{ahora.strftime('%d %b %Y, %H:%M:%S')}**"),
            "ip_address": st.column_config.TextColumn("IPv4", help="**IPv4**"),
            "device_mac": st.column_config.TextColumn("MAC", help="**MAC**"),
            "device_serial": st.column_config.TextColumn("Serial", help="**Serial**"),
            "login": st.column_config.TextColumn("Login", help="Login"),
            "location": st.column_config.TextColumn("Location", help="Location del Anexo"),
            "last_status": st.column_config.TextColumn("Status", help="Status del Anexo"),
            "historia": st.column_config.AreaChartColumn(
                "Historia",
                width="medium",
                help="Gráfico histórico de los anexos",
                y_max=1,
                y_min=0,
            ),
            "caidas": st.column_config.JsonColumn("Caidas", help="Caidas del Anexo", width="small"),
        },
    )
    return


@st.cache_data(show_spinner=":material/process_chart: Procesando DATA")
def get_anexos_missing(filtro_registros):
    registros = get_registros(registros_filtros=filtro_registros)
    anexos = get_all_anexos()

    anexos.rename(columns={"key": "anexo"}, inplace=True)
    anexos["ip_address"] = anexos["ip_address"].apply(lambda x: re.sub(r":\d+", "", str(x)) if pd.notnull(x) else x)
    registros.drop(columns=["anexo"], inplace=True)
    registros.rename(columns={"anexo_key": "anexo"}, inplace=True)
    
    documento_list = []
    with st.expander("Ver lista de Anexos Faltantes"):
        for documento, datos in registros.groupby(by=["documento", "documento_creado_en"]):
            fecha_str = documento[1]
            fecha_dt = datetime.fromisoformat(fecha_str)
            fecha_formateada = fecha_dt.strftime("%d %b %Y, %I:%M %p")
            documento_list.append({"sin_format": fecha_str, "format": fecha_formateada})
            datos.sort_values(by="anexo", ascending=True, inplace=True)
            anexos_df = anexos.merge(datos, how="left", on="anexo")
            datos_nulos = anexos_df[anexos_df['status'].isna()]
            st.write(":material/arrow_right:ID: **{id}** - Documento creado el **{creado}**".format(id=documento[0], creado=fecha_formateada))
            if len(datos_nulos) > 0:
                st.dataframe(
                    anexos_df[anexos_df['status'].isna()],
                    hide_index=True,
                    height=200,
                    use_container_width=True,
                    column_order=["anexo", "location", "ip_address", "device_mac"],
                    column_config={
                        "anexo": st.column_config.TextColumn("Anexo", help="Anexo"),
                        "location": st.column_config.TextColumn("Location", help="Location"),
                        "ip_address": st.column_config.TextColumn("IPv4", help="IPv4"),
                        "device_mac": st.column_config.TextColumn("MAC", help="MAC"),
                    }
                    ) 
            else:
                st.warning("No se encontrados Anexos faltantes")
            
    st.session_state.list_documentos = documento_list
    return


@st.cache_data(show_spinner="")
def get_change_status(filtro_registros):
    registros = get_registros(registros_filtros=filtro_registros)
    data = None
    for anexo, datos in registros.groupby(by=["anexo"]):
        datos.sort_values(by="documento_creado_en", ascending=True, inplace=True)
        datos['status_anterior'] = datos['status'].shift(1)
        datos["change"] = (datos["status"] != datos["status_anterior"]) & datos["status_anterior"].notna()
        datos["change_active"] = (datos["status_anterior"] == False) & (datos["status"] == True)
        datos["change_inactive"] = (datos["status_anterior"] == True) & (datos["status"] == False)
        data = datos[datos["change"]] if data is None else pd.concat([data, datos[datos["change"]]])
    return data 


def get_change_status_of_anexos(filtro_registros):
    data = get_change_status(filtro_registros)
    for creado in st.session_state.list_documentos:
        with st.expander("{fecha}".format(fecha=creado["format"])):
            change_active = data[(data['documento_creado_en'] == creado["sin_format"]) & (data['change_active'] == True)].copy()
            change_inactive = data[(data['documento_creado_en'] == creado["sin_format"]) & (data['change_inactive'] == True)].copy()
            change_all = data[(data['documento_creado_en'] == creado["sin_format"]) & (data['change'] == True)].copy()
            change_active["documento_creado_en"] = pd.to_datetime(change_active["documento_creado_en"]).dt.strftime("%d %b %Y, %I:%M %p")
            change_inactive["documento_creado_en"] = pd.to_datetime(change_inactive["documento_creado_en"]).dt.strftime("%d %b %Y, %I:%M %p")
            
            col1, col2, col3 = st.columns(3)
            col1.metric(label="Anexos cambiados de status", 
                        value="{value}".format(value=change_all.shape[0]),
                        border=True
                        )
            col2.metric(label="Anexos Activos",
                        value="{value}".format(value=change_active.shape[0]),
                        border=True
                        )
            col3.metric(label="Anexos Inactivos",
                        value="{value}".format(value=change_inactive.shape[0]),
                        border=True
                        )
            st.write("**Activos**")
            st.dataframe(
                change_active,
                hide_index=True,
                height=200,
                use_container_width=True,
                column_order=["anexo_key", "anexo_login", "anexo_location", "documento_creado_en"],
                column_config={
                    "anexo_key": st.column_config.TextColumn("Anexo", help="Anexo"),
                    "anexo_location": st.column_config.TextColumn("Location", help="Location"),
                    "documento_creado_en": st.column_config.TextColumn("Fecha", help="Fecha"),
                }
                )
            st.write("**Inactivos**")
            st.dataframe(
                change_inactive,
                hide_index=True,
                height=200,
                use_container_width=True,
                column_order=["anexo_key", "anexo_login", "anexo_location", "documento_creado_en"],
                column_config={
                    "anexo_key": st.column_config.TextColumn("Anexo", help="Anexo"),
                    "anexo_location": st.column_config.TextColumn("Location", help="Location"),
                    "documento_creado_en": st.column_config.TextColumn("Fecha", help="Fecha"),
                }
                )
            

