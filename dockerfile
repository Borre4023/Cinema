# Usa una imagen oficial de Python 3.11.9 (versión slim para mantener la imagen ligera)
FROM python:3.11.9-slim

# Establece el directorio de trabajo en /app
WORKDIR /app

# Copia el archivo de requerimientos y lo instala
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto de la aplicación al contenedor
COPY . .

# Render establece la variable de entorno PORT, pero exponemos un puerto (por ejemplo, 8000)
EXPOSE 8000

# Comando de inicio; Render usará este comando para levantar la app
CMD ["python", "app.py"]
