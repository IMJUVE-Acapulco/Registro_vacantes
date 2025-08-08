from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo import MongoClient
from bson.objectid import ObjectId
import os
from datetime import datetime

def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get('SECRET_KEY', 'dev-key-por-defecto')

    # Configuración de MongoDB (usa variables de entorno en producción)
    mongo_uri = os.environ.get('MONGO_URI', "mongodb://localhost:27017/")
    client = MongoClient(mongo_uri)
    db = client['sistema_vacantes']
    empresas_collection = db['empresas']
    vacantes_collection = db['vacantes']

    # Configuración para subir archivos
    UPLOAD_FOLDER = 'static/images/flayers'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    @app.route('/')
    def index():
        if 'empresa_id' in session:
            if session.get('es_admin'):
                return redirect(url_for('admin_panel'))
            return redirect(url_for('menu'))
        return render_template('index.html')

    @app.route('/login', methods=['POST'])
    def login():
        if request.method == 'POST':
            email = request.form['email']
            password = request.form['password']
            
            empresa = empresas_collection.find_one({'email': email})
            
            if empresa and check_password_hash(empresa['password'], password):
                session['empresa_id'] = str(empresa['_id'])
                session['empresa_nombre'] = empresa['nombre']
                session['es_admin'] = empresa.get('es_admin', False)
                
                if session['es_admin']:
                    return redirect(url_for('admin_panel'))
                return redirect(url_for('menu'))
            else:
                flash('Credenciales incorrectas', 'error')
                return redirect(url_for('index'))
        
        return redirect(url_for('index'))

    @app.route('/logout')
    def logout():
        session.clear()
        return redirect(url_for('index'))

    @app.route('/menu')
    def menu():
        if 'empresa_id' not in session:
            return redirect(url_for('index'))
        return render_template('menu.html')

    @app.route('/registrar', methods=['GET', 'POST'])
    def registrar():
        if 'empresa_id' not in session:
            return redirect(url_for('index'))
        
        if request.method == 'POST':
            titulo = request.form['titulo']
            descripcion = request.form['descripcion']
            requisitos = request.form['requisitos']
            flayer_path = None
            
            if 'flayer' in request.files:
                file = request.files['flayer']
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    flayer_path = os.path.join('images/flayers', filename)
            
            vacante_data = {
                'empresa_id': ObjectId(session['empresa_id']),
                'titulo': titulo,
                'descripcion': descripcion,
                'requisitos': requisitos,
                'flayer_path': flayer_path,
                'activa': True,
                'fecha_creacion': datetime.now()
            }
            
            result = vacantes_collection.insert_one(vacante_data)
            
            if result.inserted_id:
                flash('Vacante registrada exitosamente', 'success')
                return redirect(url_for('administrar'))
            else:
                flash('Error al registrar la vacante', 'error')
        
        return render_template('registrar.html')

    @app.route('/administrar')
    def administrar():
        if 'empresa_id' not in session:
            return redirect(url_for('index'))
        
        vacantes = list(vacantes_collection.find({
            'empresa_id': ObjectId(session['empresa_id'])
        }).sort('fecha_creacion', -1))
        
        for vacante in vacantes:
            vacante['_id'] = str(vacante['_id'])
        
        return render_template('administrar.html', vacantes=vacantes)

    @app.route('/editar/<vacante_id>', methods=['GET', 'POST'])
    def editar(vacante_id):
        if 'empresa_id' not in session:
            return redirect(url_for('index'))
        
        try:
            if not ObjectId.is_valid(vacante_id):
                flash('ID de vacante inválido', 'error')
                return redirect(url_for('administrar'))

            vacante = vacantes_collection.find_one({
                '_id': ObjectId(vacante_id),
                'empresa_id': ObjectId(session['empresa_id'])
            })
            
            if not vacante:
                flash('Vacante no encontrada o no tienes permisos', 'error')
                return redirect(url_for('administrar'))
            
            if request.method == 'POST':
                titulo = request.form['titulo']
                descripcion = request.form['descripcion']
                requisitos = request.form['requisitos']
                activa = 'activa' in request.form
                flayer_path = vacante.get('flayer_path')
                
                if 'flayer' in request.files:
                    file = request.files['flayer']
                    if file and allowed_file(file.filename):
                        if vacante.get('flayer_path'):
                            try:
                                os.remove(os.path.join('static', vacante['flayer_path']))
                            except:
                                pass
                        filename = secure_filename(file.filename)
                        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                        flayer_path = os.path.join('images/flayers', filename)
                
                result = vacantes_collection.update_one(
                    {'_id': ObjectId(vacante_id)},
                    {'$set': {
                        'titulo': titulo,
                        'descripcion': descripcion,
                        'requisitos': requisitos,
                        'flayer_path': flayer_path,
                        'activa': activa
                    }}
                )
                
                if result.modified_count > 0:
                    flash('Vacante actualizada exitosamente', 'success')
                else:
                    flash('No se realizaron cambios en la vacante', 'info')
                
                return redirect(url_for('administrar'))
            
            vacante['_id'] = str(vacante['_id'])
            if isinstance(vacante.get('fecha_creacion'), datetime):
                vacante['fecha_creacion'] = vacante['fecha_creacion'].strftime('%Y-%m-%d %H:%M:%S')
                
            return render_template('editar.html', vacante=vacante)
        
        except Exception as e:
            print(f"Error en editar: {str(e)}")
            flash('Error al procesar la solicitud', 'error')
            return redirect(url_for('administrar'))

    @app.route('/cerrar/<vacante_id>')
    def cerrar_vacante(vacante_id):
        if 'empresa_id' not in session:
            return redirect(url_for('index'))
        
        try:
            result = vacantes_collection.update_one(
                {'_id': ObjectId(vacante_id), 'empresa_id': ObjectId(session['empresa_id'])},
                {'$set': {'activa': False}}
            )
            
            if result.modified_count > 0:
                flash('Vacante marcada como cerrada', 'success')
            else:
                flash('No se encontró la vacante para cerrar', 'error')
        
        except Exception as e:
            flash('Error al cerrar la vacante', 'error')
        
        return redirect(url_for('administrar'))

    @app.route('/admin')
    def admin_panel():
        if 'empresa_id' not in session or not session.get('es_admin'):
            return redirect(url_for('index'))
        
        vacantes = list(vacantes_collection.aggregate([
            {
                '$lookup': {
                    'from': 'empresas',
                    'localField': 'empresa_id',
                    'foreignField': '_id',
                    'as': 'empresa'
                }
            },
            {'$unwind': '$empresa'},
            {'$sort': {'fecha_creacion': -1}}
        ]))
        
        for vacante in vacantes:
            vacante['_id'] = str(vacante['_id'])
            vacante['empresa_id'] = str(vacante['empresa_id'])
            vacante['empresa']['_id'] = str(vacante['empresa']['_id'])
        
        return render_template('admin_panel.html', vacantes=vacantes)

    @app.route('/admin/eliminar/<vacante_id>', methods=['POST'])
    def eliminar_vacante(vacante_id):
        if 'empresa_id' not in session or not session.get('es_admin'):
            flash('Acceso no autorizado', 'error')
            return redirect(url_for('index'))
        
        try:
            if not ObjectId.is_valid(vacante_id):
                flash('ID de vacante inválido', 'error')
                return redirect(url_for('admin_panel'))
            
            vacante = vacantes_collection.find_one({'_id': ObjectId(vacante_id)})
            if not vacante:
                flash('Vacante no encontrada', 'error')
                return redirect(url_for('admin_panel'))
            
            if vacante.get('flayer_path'):
                try:
                    os.remove(os.path.join('static', vacante['flayer_path']))
                except Exception as e:
                    print(f"Error al eliminar flyer: {str(e)}")
            
            result = vacantes_collection.delete_one({'_id': ObjectId(vacante_id)})
            
            if result.deleted_count > 0:
                flash('Vacante eliminada exitosamente', 'success')
            else:
                flash('No se pudo eliminar la vacante', 'error')
        
        except Exception as e:
            print(f"Error al eliminar: {str(e)}")
            flash('Error al eliminar la vacante', 'error')
        
        return redirect(url_for('admin_panel'))

    @app.route('/registro', methods=['GET', 'POST'])
    def registro():
        if request.method == 'POST':
            nombre = request.form['nombre']
            email = request.form['email']
            password = request.form['password']
            confirm_password = request.form['confirm_password']
            
            if password != confirm_password:
                flash('Las contraseñas no coinciden', 'error')
                return redirect(url_for('registro'))
            
            if empresas_collection.find_one({'email': email}):
                flash('Ya existe una cuenta con este correo electrónico', 'error')
                return redirect(url_for('registro'))
            
            empresa_data = {
                'nombre': nombre,
                'email': email,
                'password': generate_password_hash(password),
                'fecha_registro': datetime.now(),
                'es_admin': False
            }
            
            result = empresas_collection.insert_one(empresa_data)
            
            if result.inserted_id:
                flash('Registro exitoso. Por favor inicie sesión.', 'success')
                return redirect(url_for('index'))
            else:
                flash('Error al registrar la empresa', 'error')
        
        return render_template('registro.html')

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
