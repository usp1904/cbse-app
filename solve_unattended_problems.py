import sqlite3
import os
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("cbse.solver")

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from llm_client import get_client
    from database import get_conn, init_db
    from server import rebuild_syllabus_cache
except ImportError as e:
    logger.error(f"Failed to import local modules: {e}")
    sys.exit(1)

def solve_unattended_problems():
    db_path = os.path.join(os.path.dirname(__file__), "cbse_content.db")
    logger.info(f"Opening database: {db_path}")
    
    if not os.path.exists(db_path):
        logger.error("Database file does not exist!")
        return
        
    conn = get_conn()
    
    # Query all problems that have no solution or have placeholder solutions
    unsolved = conn.execute("""
        SELECT p.id, p.problem_text, p.topic_id, p.chapter_id, t.title as topic_title, ch.title as chapter_title
        FROM problems p
        LEFT JOIN topics t ON p.topic_id = t.id
        LEFT JOIN chapters ch ON p.chapter_id = ch.id
        WHERE p.solution_text IS NULL 
           OR p.solution_text = '' 
           OR LOWER(p.solution_text) LIKE '%placeholder%' 
           OR LOWER(p.solution_text) LIKE '%lorem ipsum%'
    """).fetchall()
    
    logger.info(f"Found {len(unsolved)} unattended/unsolved problems in the database.")
    
    if not unsolved:
        logger.info("All problems are already solved and attended to!")
        return
        
    client = get_client()
    if not client.available:
        logger.warning("AI Client (Gemini/Mistral API key) is not set. We will generate standard solutions using structural rules.")
        
    updated_count = 0
    
    for row in unsolved:
        p_id = row["id"]
        prob_text = row["problem_text"]
        topic_id = row["topic_id"]
        topic_title = row["topic_title"] or "General Mathematics"
        chapter_title = row["chapter_title"] or "General"
        
        logger.info(f"Attending to problem {p_id} (Topic: {topic_title})...")
        
        # Call LLM or generate fallback solution
        context = f"Chapter: {chapter_title}. Topic: {topic_title}."
        try:
            solution = client.solve_problem(prob_text, topic_title, context)
        except Exception as ex:
            logger.error(f"AI solver failed for problem {p_id}: {ex}")
            continue
            
        # Update the database
        conn.execute("UPDATE problems SET solution_text = ? WHERE id = ?", (solution, p_id))
        updated_count += 1
        
        if updated_count % 10 == 0:
            conn.commit()
            logger.info(f"Committed {updated_count} solved problems so far...")
            
    conn.commit()
    logger.info(f"Finished solving problems. Total updated: {updated_count}")
    
    # Rebuild the syllabus cache to reflect newly populated solutions
    logger.info("Rebuilding syllabus cache JSON...")
    rebuild_syllabus_cache()
    logger.info("Done!")

if __name__ == "__main__":
    solve_unattended_problems()
