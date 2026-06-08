import sys
import os
import json

sys.path.insert(0, os.path.dirname(__file__))

from database import get_conn


TOPIC_CONTENT = {}

_data_dir = os.path.join(os.path.dirname(__file__), "seed_data")
if os.path.isdir(_data_dir):
    for _fn in sorted(os.listdir(_data_dir)):
        if _fn.endswith(".json"):
            with open(os.path.join(_data_dir, _fn)) as _f:
                TOPIC_CONTENT.update(json.load(_f))


def seed_content():
    conn = get_conn()
    cur = conn.cursor()

    # Get all CBSE Math and Science topics with their chunk info
    rows = cur.execute("""
        SELECT t.id as topic_id, t.title as topic_title, ch.title as ch_title, s.name as subj_name
        FROM topics t
        JOIN chapters ch ON t.chapter_id = ch.id
        JOIN subjects s ON ch.subject_id = s.id
        WHERE ch.board_id = 'cbse' AND s.name IN ('Mathematics', 'Science')
        ORDER BY s.name, ch.num, t.num
    """).fetchall()

    topic_count = 0
    chapter_set = set()
    subject_set = set()
    updated_topics = 0
    updated_chunks = 0

    for row in rows:
        d = dict(row)
        tid = d['topic_id']
        subject_set.add(d['subj_name'])
        chapter_set.add((d['subj_name'], d['ch_title']))

        if tid not in TOPIC_CONTENT:
            print(f"  WARNING: No content for topic '{d['topic_title']}' (id: {tid})")
            continue

        data = TOPIC_CONTENT[tid]

        # Update topic content field
        cur.execute("UPDATE topics SET content = ? WHERE id = ?", (data['summary'], tid))
        updated_topics += 1

        # Get this topic's chunks ordered by seq
        chunks = cur.execute(
            "SELECT id, content_type, seq FROM chunks WHERE topic_id = ? ORDER BY seq",
            (tid,)
        ).fetchall()

        if len(chunks) != 5:
            print(f"  WARNING: Topic '{d['topic_title']}' has {len(chunks)} chunks (expected 5)")

        for i, chunk_row in enumerate(chunks):
            cd = dict(chunk_row)
            chunk_id = cd['id']
            seq = cd['seq']
            ctype = cd['content_type']

            if i < len(data['chunks']):
                chunk_data = data['chunks'][i]
                cur.execute(
                    "UPDATE chunks SET title = ?, content = ? WHERE id = ?",
                    (chunk_data['title'], chunk_data['content'], chunk_id)
                )
                updated_chunks += 1

        topic_count += 1

    conn.commit()

    print(f"Content seeded for {topic_count} topics across {len(chapter_set)} chapters in {len(subject_set)} subjects")
    print(f"  Updated {updated_topics} topic summaries")
    print(f"  Updated {updated_chunks} chunks")


if __name__ == "__main__":
    seed_content()
