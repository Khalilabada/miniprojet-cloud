from flask import Flask, request, jsonify
import psycopg2
import redis
import os
import json
from prometheus_flask_exporter import PrometheusMetrics

app = Flask(__name__)
metrics = PrometheusMetrics(app)

def get_db():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "db"),
        database=os.environ.get("DB_NAME", "tasks"),
        user=os.environ.get("DB_USER", "admin"),
        password=os.environ.get("DB_PASSWORD", "admin")
    )

r = redis.Redis(
    host=os.environ.get("REDIS_HOST", "redis"),
    port=6379,
    decode_responses=True
)

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id SERIAL PRIMARY KEY,
            title VARCHAR(200) NOT NULL,
            done BOOLEAN DEFAULT FALSE
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

@app.route("/")
def index():
    visits = r.incr("visit_count")
    return jsonify({
        "message": "Bienvenue sur la TODO API !",
        "visites": visits
    })

@app.route("/tasks", methods=["GET"])
def get_tasks():
    cached = r.get("tasks_cache")
    if cached:
        return jsonify({"source": "cache", "tasks": json.loads(cached)})
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, title, done FROM tasks ORDER BY id")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    tasks = [{"id": row[0], "title": row[1], "done": row[2]} for row in rows]
    r.setex("tasks_cache", 30, json.dumps(tasks))
    return jsonify({"source": "database", "tasks": tasks})

@app.route("/tasks", methods=["POST"])
def create_task():
    data = request.get_json()
    if not data or "title" not in data:
        return jsonify({"error": "Le champ title est requis"}), 400
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO tasks (title, done) VALUES (%s, %s) RETURNING id",
        (data["title"], data.get("done", False))
    )
    task_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    r.delete("tasks_cache")
    return jsonify({"message": "Tache creee", "id": task_id}), 201

@app.route("/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM tasks WHERE id = %s RETURNING id", (task_id,))
    deleted = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    if not deleted:
        return jsonify({"error": f"Tache {task_id} introuvable"}), 404
    r.delete("tasks_cache")
    return jsonify({"message": f"Tache {task_id} supprimee"})

@app.route("/health")
def health():
    status = {"flask": "ok", "redis": "ko", "postgres": "ko"}
    try:
        r.ping()
        status["redis"] = "ok"
    except Exception:
        pass
    try:
        conn = get_db()
        conn.close()
        status["postgres"] = "ok"
    except Exception:
        pass
    code = 200 if all(v == "ok" for v in status.values()) else 503
    return jsonify(status), code

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)
