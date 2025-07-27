#!/bin/bash

USUARIO="$1"
CLAVE="$2"
IP="$3"

if [ -z "$USUARIO" ] || [ -z "$CLAVE" ] || [ -z "$IP" ]; then
  echo "Uso: $0 <usuario> <contraseña> <ip>"
  exit 1
fi

tail -n +2 media/registros.csv | while IFS=',' read -r fecha documento; do
  archivo="media/$documento"
  echo "📤 Enviando archivo: $archivo con fecha: $fecha"

  if [ ! -f "$archivo" ]; then
    echo "⚠️  Archivo no encontrado: $archivo"
    continue
  fi

  respuesta=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
    -u "$USUARIO:$CLAVE" \
    -X POST \
    -F "usuario=1" \
    -F "creado_en=$fecha" \
    -F "archivo=@$archivo;type=text/csv" \
    http://"$IP":9000/anexo/documento/)

  cuerpo=$(echo "$respuesta" | sed -e '/HTTP_STATUS:/d')
  status=$(echo "$respuesta" | grep HTTP_STATUS | cut -d':' -f2)

  echo "🔁 Respuesta HTTP $status"
  echo "$cuerpo"
done
