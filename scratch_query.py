import sqlite3
conn = sqlite3.connect('cbse_content.db')
rows = conn.execute("SELECT id, problem_text, solution_text FROM problems WHERE problem_text LIKE '%bulb%'").fetchall()
for r in rows:
    print("ID:", r[0])
    print("TEXT:", r[1])
    print("SOL:", r[2])
    print("-" * 50)
