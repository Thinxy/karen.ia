from flask import Flask, request, render_template, redirect, url_for, jsonify
import requests
import sqlite3

app = Flask(__name__)


def init_db(db_name):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS topics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic_id INTEGER,
            message TEXT,
            sender TEXT,
            FOREIGN KEY (topic_id) REFERENCES topics(id)
        )
    ''')
    conn.commit()
    conn.close()


api_url = 'https://chatgpt.apinepdev.workers.dev/?question='


@app.route('/')
def index():
    user_ip = request.remote_addr
    db_name = f'topics_{user_ip}.db'
    init_db(db_name)

    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute('SELECT topic FROM topics ORDER BY id DESC LIMIT 5')
    topics = cursor.fetchall()
    conn.close()
    return render_template('index.html', topics=topics)


@app.route('/responder', methods=['POST'])
def responder():
    try:
        question = request.form['prompt']

        response = requests.get(api_url + question)

        if response.status_code == 200:
            data = response.json()
            answer = data.get('answer', 'Erro ao obter resposta do chatbot')

            user_ip = request.remote_addr
            db_name = f'topics_{user_ip}.db'
            conn = sqlite3.connect(db_name)
            cursor = conn.cursor()
            cursor.execute('INSERT INTO topics (topic) VALUES (?)',
                           (question, ))
            cursor.execute(
                'INSERT INTO messages (message, topic_id, sender) VALUES (?, (SELECT id FROM topics WHERE topic = ?), "User")',
                (question, question))  # Salva a pergunta do usuário
            cursor.execute(
                'INSERT INTO messages (message, topic_id, sender) VALUES (?, (SELECT id FROM topics WHERE topic = ?), "Chatbot")',
                (answer, question))  # Salva a resposta do chatbot
            conn.commit()
            conn.close()

            return answer
        else:
            return "Erro ao obter resposta do chatbot"
    except Exception as e:
        return f"Erro ao processar a solicitação: {str(e)}"


@app.route('/delete_topics', methods=['POST'])
def delete_topics():
    try:
        user_ip = request.remote_addr
        db_name = f'topics_{user_ip}.db'
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM topics')
        cursor.execute('DELETE FROM messages')
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    except Exception as e:
        return f"Erro ao processar a solicitação: {str(e)}"


@app.route('/view_topic', methods=['POST'])
def view_topic():
    try:
        selected_topic = request.form['selected_topic']

        print(f"Tópico selecionado: {selected_topic}")

        return redirect(url_for('view_messages', topic=selected_topic))
    except Exception as e:
        return f"Erro ao processar a solicitação: {str(e)}"


@app.route('/view_messages/<topic>')
def view_messages(topic):
    try:
        user_ip = request.remote_addr
        db_name = f'topics_{user_ip}.db'
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()

        cursor.execute(
            '''
            SELECT message FROM messages 
            WHERE topic_id = (SELECT id FROM topics WHERE topic = ?)
                AND sender = 'User'
            ORDER BY id ASC
        ''', (topic, ))
        user_messages = cursor.fetchall()

        cursor.execute(
            '''
            SELECT message FROM messages 
            WHERE topic_id = (SELECT id FROM topics WHERE topic = ?)
                AND sender = 'Chatbot'
            ORDER BY id ASC
        ''', (topic, ))
        chatbot_messages = cursor.fetchall()

        conn.close()

        zipped_messages = zip(user_messages, chatbot_messages)

        return render_template('view_messages.html',
                               topic=topic,
                               messages=zipped_messages)
    except Exception as e:
        return f"Erro ao processar a solicitação: {str(e)}"


@app.route('/api/question=<question>', methods=['GET'])
def question(question):
    try:
        if not question:
            return jsonify({'error': 'Nenhuma pergunta fornecida'})

        response = requests.get(api_url + question)

        if response.status_code == 200:
            data = response.json()
            answer = data.get('answer')

            if answer:
                return jsonify({'answer': answer})
            else:
                return jsonify({'error': 'Resposta vazia do chatbot'})

        else:
            return jsonify({'error': 'Erro ao obter resposta do chatbot'})
    except Exception as e:
        return jsonify({'error': f"Erro ao processar a solicitação: {str(e)}"})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
