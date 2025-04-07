import cherrypy
from pymongo import MongoClient
import os
import html
import re
from urllib.parse import quote

 #VALIDACION DE DATOS
def sanitize_input(data, field_type="text", min_length=0, max_length=1000):
    # Escapar caracteres HTML para evitar XSS
    escaped_data = html.escape(data.strip())

    # Validar longitud de caracteres
    if len(escaped_data) < min_length:
        raise ValueError(f"El texto debe tener al menos {min_length} caracteres.")
    if len(escaped_data) > max_length:
        raise ValueError(f"El texto no puede tener más de {max_length} caracteres.")

    # Validaciones específicas por tipo de campo
    if field_type == "url":
        # Validar URL (usar expresión regular)
        url_regex = re.compile(r'^https?://[^\s]+$')
        if not url_regex.match(escaped_data):
            raise ValueError("La URL no es válida")
    return escaped_data

# Configuración de la conexión a MongoDB
MONGO_URI = "mongodb+srv://borre:6olTZBewuycjg5wI@borre.tnerw.mongodb.net/?retryWrites=true&w=majority&appName=Borre"
DB_NAME = "cartelera_db"
COLLECTION_NAME = "peliculas"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

# Activar sesiones
cherrypy.config.update({'tools.sessions.on': True})

def check_admin():
    if not cherrypy.session.get("admin"):
        raise cherrypy.HTTPRedirect("/admin_login")

class CineApp:

    # LOGIN
    @cherrypy.expose
    def admin_login(self, error=None):
        html = open("templates/admin_login.html", "r", encoding="utf-8").read()
        if error:
            html = html.replace("{{error}}", f"<div class='alert alert-danger'>{error}</div>")
        else:
            html = html.replace("{{error}}", "")
        return html

    @cherrypy.expose
    def do_login(self, username, password):
        if username == "admin" and password == "admin123":
            cherrypy.session['admin'] = True
            raise cherrypy.HTTPRedirect("/admin")
        else:
            error_msg = quote("Credenciales inválidas")
            raise cherrypy.HTTPRedirect(f"/admin_login?error={error_msg}")

    @cherrypy.expose
    def admin_logout(self):
        cherrypy.session.pop('admin', None)
        raise cherrypy.HTTPRedirect("/")

    # INDEX
    @cherrypy.expose
    def index(self, search=None, genre=None):
        query = {}

        if search:
            query["$or"] = [
                {"title": {"$regex": search, "$options": "i"}},
                {"description": {"$regex": search, "$options": "i"}}           
            ]

        if genre and genre != "Todos":
            query["genre"] = {"$regex": f"^{genre}$", "$options": "i"}

        movies = collection.find(query)
        html = open("templates/index.html", "r", encoding="utf-8").read()

        # Admin controls
        if cherrypy.session.get("admin"):
            admin_controls = """
            <div class="d-flex justify-content-end mb-3">
                <a href="/admin" class="btn btn-outline-warning me-2">Panel Admin</a>
                <a href="/admin_logout" class="btn btn-outline-light">Cerrar sesión</a>
            </div>
            """
        else:
            admin_controls = """
            <div class="d-flex justify-content-end mb-3">
                <a href="/admin_login" class="btn btn-outline-warning">Admin</a>
            </div>
            """

        html = html.replace("{{admin_controls}}", admin_controls)
        html = html.replace("{{search}}", search or "")
        html = html.replace("{{genre}}", genre or "Todos")

        movie_cards = ""
        for m in movies:
            movie_cards += f"""
            <div class="col-md-4 d-flex">
                <div class="card h-100">
                    <img src="{m["image"]}" class="card-img-top" alt="{m["title"]}">
                    <div class="card-body d-flex flex-column">
                        <h5 class="card-title">{m["title"]}</h5>
                        <p class="card-text">{m["description"][:100]}...</p>
                        <p class="text-muted">Duración: {m["duration"]}</p>
                        <p class="badge bg-secondary">{m["genre"]}</p>
                        <a href="/movie?title={m["title"]}" class="btn btn-primary mt-auto">Ver más</a>
                    </div>
                </div>
            </div>
            """

        return html.replace("{{movies}}", movie_cards)

    # DETALLES DE PELÍCULA
    @cherrypy.expose
    def movie(self, title):
        movie = collection.find_one({"title": title})
        if not movie:
            return "Película no encontrada"

        def convert_to_embed(youtube_url):
            if "watch?v=" in youtube_url:
                return youtube_url.replace("watch?v=", "embed/")
            return youtube_url

        trailer_embed = convert_to_embed(movie["trailer"])

        html = open("templates/movie.html", "r", encoding="utf-8").read()
        html = html.replace("{{title}}", movie["title"])
        html = html.replace("{{description}}", movie["description"])
        html = html.replace("{{duration}}", movie["duration"])
        html = html.replace("{{genre}}", movie["genre"])
        html = html.replace("{{image}}", movie["image"])
        html = html.replace("{{trailer}}", trailer_embed)

        return html

    # PANEL ADMINISTRADOR
    @cherrypy.expose
    def admin(self):
        check_admin()      
        movies = collection.find()
        html = open("templates/admin_panel.html", "r", encoding="utf-8").read()

        movie_rows = ""
        for m in movies:
            movie_rows += f"""
            <tr>
                <td>{m['title']}</td>
                <td>{m['genre']}</td>
                <td>{m['duration']}</td>
                <td>
                    <a href="/edit_movie?title={m['title']}" class="btn btn-sm btn-warning">Editar</a>
                    <a href="/delete_movie?title={m['title']}" class="btn btn-sm btn-danger" onclick="return confirm('¿Estás seguro?')">Eliminar</a>
                </td>
            </tr>
            """

        return html.replace("{{movie_rows}}", movie_rows)
    
    #---------------CRUD---------------#
    @cherrypy.expose
    def add_movie(self):
        check_admin()

        html = open("templates/add_movie.html", "r", encoding="utf-8").read()
        return html

    @cherrypy.expose
    def save_movie(self, title, description, duration, genre, image, trailer):
        check_admin()
        try:
            # Validar y escapar cada campo con longitud
            title = sanitize_input(title, "text", min_length=3, max_length=100)  # Título: mínimo 3 caracteres, máximo 100
            description = sanitize_input(description, "text", min_length=10, max_length=500)  # Descripción: mínimo 10, máximo 500
            duration = sanitize_input(duration, "text", min_length=1, max_length=10)  # Duración: mínimo 1 carácter, máximo 10
            genre = sanitize_input(genre, "text", min_length=3, max_length=50)  # Género: mínimo 3 caracteres, máximo 50
            image = sanitize_input(image, "url")
            trailer = sanitize_input(trailer, "url")
        except ValueError as e:
            return f"Error: {str(e)}"

        # Guardar en la base de datos
        collection.insert_one({
            "title": title,
            "description": description,
            "duration": duration,
            "genre": genre,
            "image": image,
            "trailer": trailer
        })

        raise cherrypy.HTTPRedirect("/admin")
    
    @cherrypy.expose
    def edit_movie(self, title, error=None):
        check_admin()
        movie = collection.find_one({"title": title})
        if not movie:
            return "Película no encontrada"

        html = open("templates/edit_movie.html", "r", encoding="utf-8").read()

        if error:
            html = html.replace("{{error}}", f"<div class='alert alert-danger'>{error}</div>")
        else:
            html = html.replace("{{error}}", "")

        for key in ["title", "description", "duration", "genre", "image", "trailer"]:
            html = html.replace(f"{{{{{key}}}}}", movie.get(key, ""))

        return html
    
    @cherrypy.expose
    def update_movie(self, original_title, title, description, duration, genre, image, trailer):
        check_admin()
        if not all([title.strip(), description.strip(), duration.strip(), genre.strip()]):
            raise cherrypy.HTTPRedirect(f"/edit_movie?title={original_title}&error=Todos+los+campos+son+requeridos")

        collection.update_one(
            {"title": original_title},
            {"$set": {
                "title": title.strip(),
                "description": description.strip(),
                "duration": duration.strip(),
                "genre": genre.strip(),
                "image": image.strip(),
                "trailer": trailer.strip()
            }}
        )
        raise cherrypy.HTTPRedirect("/admin")
    
    @cherrypy.expose
    def delete_movie(self, title):
        check_admin()

        collection.delete_one({"title": title})
        raise cherrypy.HTTPRedirect("/admin")
        
# SERVIDOR
if __name__ == "__main__":
    # Cargar configuración del servidor
    cherrypy.config.update("server.conf")
    
    cherrypy.quickstart(CineApp(), "/", {
        "/": {
            "tools.sessions.on": True,
            "tools.staticdir.root": os.path.abspath(os.getcwd())
        },
        "/static": {
            "tools.staticdir.on": True,
            "tools.staticdir.dir": "static"
        }
    })
