from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'clave-secreta-segura'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///productos.db'
db = SQLAlchemy(app)

# Modelos
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    es_admin = db.Column(db.Boolean, default=False)

class Producto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100))
    precio = db.Column(db.Integer)
    imagen = db.Column(db.String(200))
    stock_S = db.Column(db.Integer)
    stock_M = db.Column(db.Integer)
    stock_L = db.Column(db.Integer)
    stock_XL = db.Column(db.Integer)
    categoria = db.Column(db.String(50))
    activo = db.Column(db.Boolean, default=True)

class Venta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    producto = db.Column(db.String(100), nullable=False)
    talle = db.Column(db.String(10), nullable=False)
    precio = db.Column(db.Integer, nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

# Redirección inicial a categoría por defecto
@app.route('/')
def home():
    return redirect(url_for('ver_categoria', categoria='remeras'))

# Página por categoría
@app.route('/<categoria>')
def ver_categoria(categoria):
    categorias_validas = ['remeras', 'pantalones', 'abrigos', 'otros']
    if categoria not in categorias_validas:
        return redirect(url_for('home'))
    productos = Producto.query.filter_by(categoria=categoria, activo=True).all()
    return render_template('tienda_categoria.html', productos=productos, categoria=categoria)

# Panel admin
@app.route('/admin')
def admin():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    usuario = Usuario.query.filter_by(username=session['usuario']).first()
    if not usuario or not usuario.es_admin:
        return redirect(url_for('home'))

    productos = Producto.query.all()
    return render_template('admin.html', productos=productos)

# Agregar producto
@app.route('/agregar', methods=['POST'])
def agregar():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    usuario = Usuario.query.filter_by(username=session['usuario']).first()
    if not usuario or not usuario.es_admin:
        return redirect(url_for('home'))

    nuevo = Producto(
        nombre=request.form['nombre'],
        precio=request.form['precio'],
        imagen=request.form['imagen'],
        stock_S=request.form['stock_S'],
        stock_M=request.form['stock_M'],
        stock_L=request.form['stock_L'],
        stock_XL=request.form['stock_XL'],
        categoria=request.form['categoria'],
        activo=True
    )
    db.session.add(nuevo)
    db.session.commit()
    return redirect(url_for('admin'))

# Eliminar producto
@app.route('/eliminar/<int:id>')
def eliminar(id):
    if 'usuario' not in session:
        return redirect(url_for('login'))

    usuario = Usuario.query.filter_by(username=session['usuario']).first()
    if not usuario or not usuario.es_admin:
        return redirect(url_for('home'))

    producto = Producto.query.get(id)
    db.session.delete(producto)
    db.session.commit()
    return redirect(url_for('admin'))

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = Usuario.query.filter_by(username=request.form['usuario']).first()
        if usuario and check_password_hash(usuario.password, request.form['clave']):
            session['usuario'] = usuario.username
            return redirect(url_for('admin' if usuario.es_admin else 'home'))
        return "Usuario o contraseña incorrectos"
    return render_template('login.html')

# Registro
@app.route('/registro', methods=['POST'])
def registro():
    usuario = request.form['usuario']
    clave = request.form['clave']
    admin_key = request.form.get('admin_key')
    if Usuario.query.filter_by(username=usuario).first():
        return "El usuario ya existe"

    es_admin = True if admin_key == "clave-secreta-admin" else False
    hashed = generate_password_hash(clave)
    nuevo = Usuario(username=usuario, password=hashed, es_admin=es_admin)
    db.session.add(nuevo)
    db.session.commit()
    return redirect(url_for('login'))

# Logout
@app.route('/logout')
def logout():
    session.pop('usuario', None)
    return redirect(url_for('login'))

# Finalizar pedido (actualiza stock y guarda venta)
@app.route('/finalizar_pedido', methods=['POST'])
def finalizar_pedido():
    datos = request.json
    for item in datos:
        nombre = item['nombre']
        talle = item['talle']
        precio = item['precio']

        producto = Producto.query.filter_by(nombre=nombre).first()
        if not producto:
            continue

        if talle == 'S' and producto.stock_S > 0:
            producto.stock_S -= 1
        elif talle == 'M' and producto.stock_M > 0:
            producto.stock_M -= 1
        elif talle == 'L' and producto.stock_L > 0:
            producto.stock_L -= 1
        elif talle == 'XL' and producto.stock_XL > 0:
            producto.stock_XL -= 1

        venta = Venta(producto=nombre, talle=talle, precio=precio)
        db.session.add(venta)

    db.session.commit()
    return jsonify({'mensaje': 'Stock actualizado'}), 200

# Historial de ventas
@app.route('/admin/ventas')
def historial_ventas():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    usuario = Usuario.query.filter_by(username=session['usuario']).first()
    if not usuario or not usuario.es_admin:
        return redirect(url_for('home'))

    ventas = Venta.query.order_by(Venta.fecha.desc()).all()
    return render_template('ventas.html', ventas=ventas)

# Inicialización
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
