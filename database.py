from pymongo import MongoClient
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash
import os

class Database:
    def __init__(self):
        try:
            # MongoDB connection with your credentials
            self.connection = MongoClient(
                "mongodb+srv://purnyan22:IMJUVE13@cluster0.sbeawa3.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
            )
            self.db = self.connection['sistema_vacantes']
            self.empresas = self.db['empresas']
            self.vacantes = self.db['vacantes']
            print("Conexión a MongoDB establecida")
        except Exception as e:
            print(f"Error al conectar a MongoDB: {e}")

    def get_connection(self):
        return self.connection

    def close_connection(self):
        if self.connection:
            self.connection.close()
            print("Conexión a MongoDB cerrada")

    # Métodos para empresas
    def crear_empresa(self, nombre, email, password, es_admin=False):
        try:
            empresa_data = {
                'nombre': nombre,
                'email': email,
                'password': generate_password_hash(password),  # Hasheamos la contraseña
                'es_admin': es_admin,
                'fecha_registro': datetime.now()
            }
            result = self.empresas.insert_one(empresa_data)
            return str(result.inserted_id)
        except Exception as e:
            print(f"Error al crear empresa: {e}")
            return None

    def obtener_empresa_por_email(self, email):
        try:
            return self.empresas.find_one({'email': email})
        except Exception as e:
            print(f"Error al obtener empresa: {e}")
            return None

    # Métodos para vacantes
    def crear_vacante(self, empresa_id, titulo, descripcion, requisitos, flayer_path=None):
        try:
            vacante_data = {
                'empresa_id': ObjectId(empresa_id),
                'titulo': titulo,
                'descripcion': descripcion,
                'requisitos': requisitos,
                'flayer_path': flayer_path,
                'activa': True,
                'fecha_creacion': datetime.now()
            }
            result = self.vacantes.insert_one(vacante_data)
            return str(result.inserted_id)
        except Exception as e:
            print(f"Error al crear vacante: {e}")
            return None

    def obtener_vacantes_por_empresa(self, empresa_id):
        try:
            return list(self.vacantes.find({'empresa_id': ObjectId(empresa_id)})
                       .sort('fecha_creacion', -1))
        except Exception as e:
            print(f"Error al obtener vacantes: {e}")
            return []

    def obtener_todas_vacantes(self):
        try:
            pipeline = [
                {
                    '$lookup': {
                        'from': 'empresas',
                        'localField': 'empresa_id',
                        'foreignField': '_id',
                        'as': 'empresa'
                    }
                },
                {'$unwind': '$empresa'},
                {'$sort': {'fecha_creacion': -1}},
                {
                    '$project': {
                        'empresa_nombre': '$empresa.nombre',
                        'titulo': 1,
                        'descripcion': 1,
                        'requisitos': 1,
                        'flayer_path': 1,
                        'activa': 1,
                        'fecha_creacion': 1
                    }
                }
            ]
            return list(self.vacantes.aggregate(pipeline))
        except Exception as e:
            print(f"Error al obtener todas las vacantes: {e}")
            return []

    def actualizar_vacante(self, vacante_id, titulo, descripcion, requisitos, flayer_path, activa):
        try:
            result = self.vacantes.update_one(
                {'_id': ObjectId(vacante_id)},
                {'$set': {
                    'titulo': titulo,
                    'descripcion': descripcion,
                    'requisitos': requisitos,
                    'flayer_path': flayer_path,
                    'activa': activa
                }}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"Error al actualizar vacante: {e}")
            return False

    def cambiar_estado_vacante(self, vacante_id, activa):
        try:
            result = self.vacantes.update_one(
                {'_id': ObjectId(vacante_id)},
                {'$set': {'activa': activa}}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"Error al cambiar estado de vacante: {e}")
            return False

    def eliminar_vacante(self, vacante_id):
        try:
            result = self.vacantes.delete_one({'_id': ObjectId(vacante_id)})
            return result.deleted_count > 0
        except Exception as e:
            print(f"Error al eliminar vacante: {e}")
            return False