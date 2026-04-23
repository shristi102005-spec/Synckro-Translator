from flask import Flask, render_template_string, request, redirect, url_for
import os
from datetime import datetime, timedelta

app = Flask(__name__)

LOG_FILE = "conversation_history.txt"
TRASH_FILE = "trash_history.txt"
LANG_FOLDER = "lang_conversations"
PURGE_DAYS = 7

TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Synckro Translator Dashboard</title>
    <style>
        body {
            font-family: 'Segoe UI', sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #d9fdd3 0%, #ece5dd 100%);
            background-attachment: fixed;
            background-image: radial-gradient(circle at 20px 20px, rgba(255,255,255,0.25) 2%, transparent 0),
                              radial-gradient(circle at 60px 60px, rgba(255,255,255,0.25) 2%, transparent 0);
            background-size: 80px 80px;
        }
        h1 { color: #075e54; text-align: center; margin-bottom: 20px; }
        h2 { text-align:center; color:#075e54; font-size:1.6em; margin-bottom:20px; letter-spacing:1px; text-transform:uppercase; }
        .chat-container {
            max-width: 900px;
            margin: auto;
            background: #ffffffee;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 6px 18px rgba(0,0,0,0.2);
            font-size: 1.1em;
            backdrop-filter: blur(6px);
        }
        .chat-bubble {
            padding: 12px 18px;
            border-radius: 20px;
            margin: 10px 0;
            display: inline-block;
            max-width: 70%;
            position: relative;
            transition: all 0.25s ease-in-out;
            animation: fadeIn 0.6s ease;
        }
        .chat-bubble:hover {
            transform: translateY(-4px);
            box-shadow: 0 6px 14px rgba(0,0,0,0.25);
            background-color: #fefefe;
        }
        .chat-left {
            background: #f0f0f0;
            border: 1px solid #ccc;
            color: #333;
            float: left;
            clear: both;
        }
        .chat-right {
            background: #dcf8c6;
            color: #000;
            float: right;
            clear: both;
        }
        .timestamp {
            font-size: 0.8em;
            color: #999;
            margin-top: 4px;
        }
        .actions { margin-top: 6px; }
        .btn {
            padding: 6px 10px;
            margin: 2px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.8em;
        }
        .cut { background: #e74c3c; color: #fff; }
        .copy { background: #3498db; color: #fff; }
        .save { background: #27ae60; color: #fff; }
        .panel {
            margin-top: 30px;
            background: #fafafa;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.1);
        }
        .clearfix::after { content: ""; clear: both; display: table; }
        ul { list-style: none; padding: 0; }
        li { margin: 6px 0; }
        a { text-decoration: none; color: #075e54; font-weight: bold; }
        a:hover { text-decoration: underline; }
        .badge {
            position:absolute; top:-10px; font-size:0.7em; padding:2px 6px; border-radius:10px; color:#fff;
        }
        .badge-left { left:10px; background:#999; }
        .badge-right { right:10px; background:#075e54; }
        @keyframes fadeIn {
            from { opacity:0; transform: translateY(10px); }
            to { opacity:1; transform: translateY(0); }
        }
    </style>
</head>
<body>
    <h1>🌐 Synckro Translator Dashboard</h1>
    <div class="chat-container">
        <h2>Conversation Logs</h2>
        <form method="post" action="/delete_all">
            <button class="btn cut">Delete All → Trash</button>
        </form>
        <div class="clearfix">
            {% for line in logs %}
                {% if "→" in line %}
                    <!-- Left bubble: original -->
                    <div class="chat-bubble chat-left">
                        <span class="badge badge-left">{{ line.split("]")[0].split()[1] }}</span>
                        {{ line.split("|")[0].split("→")[0].split("]")[-1].strip() }}
                        <div class="timestamp">{{ line.split("]")[0].strip("[") }}</div>
                        <div class="actions">
                            <button class="btn copy" onclick="navigator.clipboard.writeText('{{ line }}')">Copy</button>
                            <button class="btn save">Save</button>
                            <form method="post" action="/delete_line" style="display:inline;">
                                <input type="hidden" name="line" value="{{ line }}">
                                <button class="btn cut" onclick="return confirm('Delete this entry?')">Delete</button>
                            </form>
                        </div>
                    </div>
                    <!-- Right bubble: translated -->
                    <div class="chat-bubble chat-right">
                        <span class="badge badge-right">{{ line.split("]")[0].split()[3] }}</span>
                        {{ line.split("|")[1].strip() }}
                        <div class="timestamp">{{ line.split("]")[0].strip("[") }}</div>
                        <div class="actions">
                            <button class="btn copy" onclick="navigator.clipboard.writeText('{{ line }}')">Copy</button>
                            <button class="btn save">Save</button>
                            <form method="post" action="/delete_line" style="display:inline;">
                                <input type="hidden" name="line" value="{{ line }}">
                                <button class="btn cut" onclick="return confirm('Delete this entry?')">Delete</button>
                            </form>
                        </div>
                    </div>
                {% else %}
                    <div class="chat-bubble chat-left">{{ line }}</div>
                {% endif %}
            {% endfor %}
        </div>
    </div>

    <div class="panel">
        <h2>Trash</h2>
        <form method="post" action="/purge">
            <button class="btn cut">Purge Trash ({{ purge_days }} days)</button>
        </form>
        <form method="post" action="/restore_all">
            <button class="btn save">Restore All</button>
        </form>
        <pre>{{ trash }}</pre>
    </div>

    <div class="panel">
        <h2>Language Archives</h2>
        <ul>
            {% for folder in lang_folders %}
                <li><a href="/lang/{{ folder }}">{{ folder }}</a></li>
            {% endfor %}
        </ul>
    </div>
</body>
</html>
"""

def read_lines(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return f.readlines()

def write_file(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def append_file(path, content):
    with open(path, "a", encoding="utf-8") as f:
        f.write(content)

def purge_trash():
    if not os.path.exists(TRASH_FILE):
        return
    lines = []
    cutoff = datetime.now() - timedelta(days=PURGE_DAYS)
    with open(TRASH_FILE, "r", encoding="utf-8") as f:
        for line in f:
            try:
                ts = line.split("]")[0].strip("[")
                dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
                if dt > cutoff:
                    lines.append(line)
            except:
                pass
    write_file(TRASH_FILE, "".join(lines))

@app.route("/")
def index():
    purge_trash()
    logs = read_lines(LOG_FILE)
    trash = "".join(read_lines(TRASH_FILE))
    lang_folders = os.listdir(LANG_FOLDER) if os.path.exists(LANG_FOLDER) else []
    return render_template_string(TEMPLATE, logs=logs, trash=trash, purge_days=PURGE_DAYS, lang_folders=lang_folders)

@app.route("/delete_all", methods=["POST"])
def delete_all():
    logs = "".join(read_lines(LOG_FILE))
    if logs.strip():
        append_file(TRASH_FILE, logs)
        write_file(LOG_FILE, "")
    return redirect(url_for("index"))

@app.route("/restore_all", methods=["POST"])
def restore_all():
    trash = "".join(read_lines(TRASH_FILE))
    if trash.strip():
        append_file(LOG_FILE, trash)
        write_file(TRASH_FILE, "")
    return redirect(url_for("index"))

@app.route("/purge", methods=["POST"])
def purge():
    purge_trash()
    return redirect(url_for("index"))

@app.route("/lang/<folder>")
def lang_folder(folder):
    path = os.path.join(LANG_FOLDER, folder)
    files = os.listdir(path) if os.path.exists(path) else []
    return "<h2>Language Folder: {}</h2><ul>{}</ul>".format(folder, "".join([f"<li>{f}</li>" for f in files]))

@app.route("/delete_line", methods=["POST"])
def delete_line():
    line = request.form.get("line")
    logs = read_lines(LOG_FILE)
    if line in logs:
        # Move to trash
        append_file(TRASH_FILE, line)
        # Remove from logs
        logs.remove(line)
        write_file(LOG_FILE, "".join(logs))
    return redirect(url_for("index"))

if __name__ == "__main__":
    os.makedirs(LANG_FOLDER, exist_ok=True)
    app.run(debug=True, port=5000)






