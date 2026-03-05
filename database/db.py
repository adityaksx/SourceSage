import sqlite3

conn = sqlite3.connect("resources.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS resources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT,
    url TEXT,
    title TEXT,
    summary TEXT,
    content TEXT
)
""")

conn.commit()

def save_resource(source, url, title, summary, content):

    cursor.execute(
        "INSERT INTO resources (source,url,title,summary,content) VALUES (?,?,?,?,?)",
        (source, url, title, summary, content)
    )

    conn.commit()