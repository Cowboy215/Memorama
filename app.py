import random
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, g

app = Flask(__name__)
app.secret_key = '123459384'  # Necesario para manejar sesiones
_OK = '', 200

DATABASE = "memoramaDB.db"

# Función para conectar a la base de datos
def get_db():
    """Conexión a la base de datos SQLite."""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row  # Permite acceder a los datos como diccionarios
    return db

@app.teardown_appcontext
def close_connection(exception):
    """Cerrar conexión a la base de datos."""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# Definir las cartas para cada dificultad
difficulties = {
    'easy':   [f'imagen{i}.png' for i in range(1,4)],
    'medium': [f'imagen{i}.png' for i in range(1,7)],
    'hard':   [f'imagen{i}.png' for i in range(1,11)],
}

initial_scores = {'easy': 30, 'medium': 60, 'hard': 100}

messages = {
    'win': "¡Felicidades! Has encontrado todos los pares.",
    'loss': "Lo siento, has perdido. Se acabaron tus intentos."
}

default_values = ["result", "player", "final_score", "difficulty", "count"]

@app.route('/')
def index():
    return render_template('home.html')

@app.route('/difficulty')
def difficulty():
    session.clear()
    return render_template('difficulty.html')


@app.route('/play', methods=['GET', 'POST'])
def play():
    if request.method == 'POST':
        difficulty = request.form.get('difficulty')
        session['difficulty'] = difficulty

        cards = difficulties[difficulty] * 2  # Crear pares
        random.shuffle(cards)  # Mezclar las cartas

        session['cards'] = cards
        session['score'] = initial_scores[difficulty]

        return redirect(url_for('play'))
    
    if request.method == 'GET':
        return render_template('index.html', cards=session['cards'])


@app.route('/end', methods=['GET', 'POST'])
def end():
    if request.method == 'POST':
        data = request.get_json()

        for type in default_values:
            information = data.get(type)
            if information is not None:
                session[type] = session.get(type, information)

        return _OK

    if request.method == 'GET':
        result = session.get('result')

        if not result:
            return redirect(url_for('index'))

        return render_template('end.html', message=messages[result])

@app.route('/scores', methods=['GET', 'POST'])
def show_scores():
    if request.method == 'POST':
        info = request.get_json()

        player = info.get("player")

        if player:
            session["player"] = player

            required_keys = ['player', 'final_score', 'count', 'difficulty']
            data = {key: session.get(key) for key in required_keys}

            if any(value is None for value in data.values()):
                return redirect(url_for('index'))
            
            if data['difficulty'] in ['easy', 'medium', 'hard']:
                session["curr_difficulty"] = data['difficulty']
            else:
                return redirect(url_for('index'))  
            
            db = get_db()

            table_name = session.get('curr_difficulty')

            db.execute(
                f'INSERT INTO {table_name} (nombre, puntuacion, tiempo) VALUES (?, ?, ?)',
                (data['player'], data['final_score'], data['count'])
            )

            db.commit()

        curr_difficulty = info.get("change")
        if curr_difficulty:
            session["curr_difficulty"] = curr_difficulty

        return _OK

        
    if request.method == "GET":
        """Mostrar los 10 mejores puntajes y la posición del último puntaje del usuario."""
        db = get_db()

        curr_difficulty = session.get('curr_difficulty')

        if not curr_difficulty or curr_difficulty not in ['easy', 'medium', 'hard']:
            return redirect(url_for('index'))

        cursor = db.execute(
            f'SELECT nombre, puntuacion, tiempo FROM {curr_difficulty} ORDER BY puntuacion DESC, tiempo ASC LIMIT 10'
        )
        top_scores = cursor.fetchall()

        # Obtener el puntaje de la última partida
        last_score_id = None
        last_score = None
        last_position = None

        player_name = session.get('player')  
        if player_name:
            cursor = db.execute(f'SELECT MAX(id) FROM {curr_difficulty} WHERE nombre = ?;',
                                (player_name,))
            last_score_id = cursor.fetchone()[0]

        if last_score_id:
            # Obtener los detalles del último puntaje
            cursor = db.execute(
                f'SELECT nombre, puntuacion, tiempo FROM {curr_difficulty} WHERE id = ?',
                (last_score_id,)
            )

            last_score = cursor.fetchone()
            print(last_score_id, curr_difficulty)

            cursor = db.execute(
                f'''
                SELECT COUNT(*) + 1
                FROM {curr_difficulty}
                WHERE puntuacion > (SELECT puntuacion FROM {curr_difficulty} WHERE id = ?)
                OR (puntuacion = (SELECT puntuacion FROM {curr_difficulty} WHERE id = ?) AND tiempo < (SELECT tiempo FROM {curr_difficulty} WHERE id = ?))
                ''',
                (last_score_id, last_score_id, last_score_id)
            )

            last_position = cursor.fetchone()[0]

        return render_template(
            'scores.html',
            top_scores=top_scores,
            last_score=last_score,
            last_position=last_position
        )
    
#Insertando lo nuevo

# @app.route('/easy', methods=['GET'])
# def show_scores_easy():
#     """Mostrar los 10 mejores puntajes y la posición del último puntaje del usuario."""
#     db = get_db()

#     difficulty = session.get('difficulty')

#     if not difficulty or difficulty not in ['easy', 'medium', 'hard']:
#         return redirect(url_for('index'))

    
#     cursor = db.execute(
#         f'SELECT nombre, puntuacion, tiempo FROM easy ORDER BY puntuacion DESC, tiempo ASC LIMIT 10'
#     )
#     top_scores = cursor.fetchall()

#     # Obtener el puntaje de la última partida
#     last_score_id = session.get('last_score_id')  # Guarda el ID del puntaje al insertar
#     last_score = None
#     last_position = None

#     if last_score_id:
#         # Obtener los detalles del último puntaje
#         cursor = db.execute(
#             f'SELECT nombre, puntuacion, tiempo FROM easy WHERE id = ?',
#             (last_score_id,)
#         )

#         last_score = cursor.fetchone()

#         cursor = db.execute(
#             f'''
#             SELECT COUNT(*) + 1
#             FROM easy
#             WHERE puntuacion > (SELECT puntuacion FROM easy WHERE id = ?)
#             OR (puntuacion = (SELECT puntuacion FROM easy WHERE id = ?) AND tiempo < (SELECT tiempo FROM easy WHERE id = ?))
#             ''',
#             (last_score_id, last_score_id, last_score_id)
#         )

#         last_position = cursor.fetchone()[0]

#     return render_template(
#         'scores_easy.html',
#         top_scores=top_scores,
#         last_score=last_score,
#         last_position=last_position
#     )

# # MEdio

# @app.route('/media', methods=['GET'])
# def show_scores_media():
#     """Mostrar los 10 mejores puntajes y la posición del último puntaje del usuario."""
#     db = get_db()

#     difficulty = session.get('difficulty')

#     if not difficulty or difficulty not in ['easy', 'medium', 'hard']:
#         return redirect(url_for('index'))

    
#     cursor = db.execute(
#         f'SELECT nombre, puntuacion, tiempo FROM medium ORDER BY puntuacion DESC, tiempo ASC LIMIT 10'
#     )
#     top_scores = cursor.fetchall()

#     # Obtener el puntaje de la última partida
#     last_score_id = session.get('last_score_id')  # Guarda el ID del puntaje al insertar
#     last_score = None
#     last_position = None

#     if last_score_id:
#         # Obtener los detalles del último puntaje
#         cursor = db.execute(
#             f'SELECT nombre, puntuacion, tiempo FROM medium WHERE id = ?',
#             (last_score_id,)
#         )

#         last_score = cursor.fetchone()

#         cursor = db.execute(
#             f'''
#             SELECT COUNT(*) + 1
#             FROM medium
#             WHERE puntuacion > (SELECT puntuacion FROM medium WHERE id = ?)
#             OR (puntuacion = (SELECT puntuacion FROM medium WHERE id = ?) AND tiempo < (SELECT tiempo FROM medium WHERE id = ?))
#             ''',
#             (last_score_id, last_score_id, last_score_id)
#         )

#         last_position = cursor.fetchone()[0]

#     return render_template(
#         'scores_media.html',
#         top_scores=top_scores,
#         last_score=last_score,
#         last_position=last_position
#     )
    
# #Dificil
# @app.route('/alta', methods=['GET'])
# def show_scores_alta():
#     """Mostrar los 10 mejores puntajes y la posición del último puntaje del usuario."""
#     db = get_db()

#     difficulty = session.get('difficulty')

#     if not difficulty or difficulty not in ['easy', 'medium', 'hard']:
#         return redirect(url_for('index'))

    
#     cursor = db.execute(
#         f'SELECT nombre, puntuacion, tiempo FROM hard ORDER BY puntuacion DESC, tiempo ASC LIMIT 10'
#     )
#     top_scores = cursor.fetchall()

#     # Obtener el puntaje de la última partida
#     last_score_id = session.get('last_score_id')  # Guarda el ID del puntaje al insertar
#     last_score = None
#     last_position = None

#     if last_score_id:
#         # Obtener los detalles del último puntaje
#         cursor = db.execute(
#             f'SELECT nombre, puntuacion, tiempo FROM hard WHERE id = ?',
#             (last_score_id,)
#         )

#         last_score = cursor.fetchone()

#         cursor = db.execute(
#             f'''
#             SELECT COUNT(*) + 1
#             FROM hard
#             WHERE puntuacion > (SELECT puntuacion FROM hard WHERE id = ?)
#             OR (puntuacion = (SELECT puntuacion FROM hard WHERE id = ?) AND tiempo < (SELECT tiempo FROM hard WHERE id = ?))
#             ''',
#             (last_score_id, last_score_id, last_score_id)
#         )

#         last_position = cursor.fetchone()[0]

#     return render_template(
#         'scores_alta.html',
#         top_scores=top_scores,
#         last_score=last_score,
#         last_position=last_position
#     )


# @app.route('/usuarios', methods=['GET'])
# def listar_usuarios():
#     usuarios = obtener_usuarios()
#     usuarios_json = [{"nombre": u.nombre, "puntuacion": u.puntuacion,
#                       "tiempo": u.tiempo, "dificultad": u.dificultad} for u in usuarios]
#     return jsonify(usuarios_json), 200


# @app.route('/usuarios', methods=['POST'])
# def crear_usuario():
#     data = request.get_json()
#     insertar_usuario(data['nombre'], data.get('puntuacion', 0), data.get(
#         'tiempo', 0), data.get('dificultad', 'easy'))
#     return jsonify({"mensaje": "Usuario creado exitosamente"}), 201


# @app.route('/usuarios/<int:id_usuario>', methods=['DELETE'])
# def eliminar_usuario(id_usuario):
#     borrar_usuario(id_usuario)
#     return jsonify({"mensaje": "Usuario eliminado exitosamente"}), 200


# @app.route('/usuarios/<int:id_usuario>', methods=['PUT'])
# def modificar_usuario(id_usuario):
#     data = request.get_json()
#     actualizar_usuario(id_usuario, data['nombre'], data.get(
#         'puntuacion', 0), data.get('tiempo', 0), data.get('dificultad', 'easy'))
#     return jsonify({"mensaje": "Usuario actualizado exitosamente"}), 200


if __name__ == '__main__':
    app.run(debug=True)