import sqlite_utils
import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), "cbse_content.db")
print(f"Auditing database: {db_path}")

if not os.path.exists(db_path):
    print("Database file does not exist!")
    exit(1)

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

# Check total counts
counts = {}
for table in ["boards", "subjects", "chapters", "topics", "chunks", "problems"]:
    try:
        row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
        counts[table] = row[0]
    except Exception as e:
        counts[table] = f"Error: {e}"

print("Total Counts:")
for table, cnt in counts.items():
    print(f"  {table}: {cnt}")

# Check for empty content or placeholders
empty_topics = conn.execute("SELECT id, title FROM topics WHERE content IS NULL OR content = '' OR content LIKE '%placeholder%' OR content LIKE '%lorem%'").fetchall()
print(f"\nUnattended/Empty Topics: {len(empty_topics)}")
for t in empty_topics[:15]:
    print(f"  Topic ID: {t['id']} - Title: {t['title']}")

empty_chunks = conn.execute("SELECT id, title, topic_id FROM chunks WHERE content IS NULL OR content = '' OR content LIKE '%placeholder%' OR content LIKE '%lorem%'").fetchall()
print(f"\nUnattended/Empty Chunks: {len(empty_chunks)}")
for c in empty_chunks[:15]:
    print(f"  Chunk ID: {c['id']} - Title: {c['title']} (Topic: {c['topic_id']})")

empty_problems = conn.execute("SELECT id, problem_text, topic_id FROM problems WHERE solution_text IS NULL OR solution_text = '' OR solution_text LIKE '%placeholder%'").fetchall()
print(f"\nUnattended/Empty Problems: {len(empty_problems)}")
for p in empty_problems[:15]:
    print(f"  Problem ID: {p['id']} - Text: {p['problem_text'][:60]}... (Topic: {p['topic_id']})")

conn.close()
