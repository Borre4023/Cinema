# Usa una imagen oficial de Python (en este ejemplo, la versión slim para mantenerla ligera)
FROM python:3.11.9-slim

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copia el archivo de requerimientos y lo instala
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto de la aplicación (app.py, server.conf, start.sh, templates, static, etc.)
COPY . .

# Asegúrate de que start.sh tenga permisos de ejecución
RUN chmod +x start.sh

# Expon el puerto 8080 (debe coincidir con la configuración de CherryPy en server.conf)
EXPOSE 8080

# Define el comando de inicio (Render ejecutará este comando al arrancar el contenedor)
CMD ["./start.sh"]
