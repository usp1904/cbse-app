import sys
import os
import re
import json
import logging
from pathlib import Path

# Add current directory to path to import local modules
curr_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(curr_dir))

# Configure logging to console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("cbse.harness")

try:
    from json_index import get_index
    from database import get_conn
except ImportError as e:
    logger.error(f"Failed to import local modules: {e}")
    sys.exit(1)

def verify_latex(text, context_path):
    """Audits LaTeX math blocks for balanced delimiters and braces."""
    errors = []
    # Check for unclosed $ or $$
    dollar_count = text.count('$')
    if dollar_count % 2 != 0:
        errors.append(f"Odd number of math delimiters ($): {dollar_count}")
        
    # Find all inline ($...$) and block ($$...$$) math equations
    math_segments = re.findall(r'\$\$(.*?)\$\$|\$(.*?)\$', text, re.DOTALL)
    for seg_tuple in math_segments:
        seg = seg_tuple[0] or seg_tuple[1]
        if not seg:
            continue
        # Check braces matching inside LaTeX
        open_braces = seg.count('{')
        close_braces = seg.count('}')
        if open_braces != close_braces:
            errors.append(f"Unbalanced braces in LaTeX string '{seg}': {open_braces} open vs {close_braces} close")
            
        # Check for truncated commands (e.g. backslash at the end of word or segment)
        if seg.endswith('\\') or re.search(r'\\[a-zA-Z]*$', seg):
            allowed_endings = ['\\\\', '\\theta', '\\alpha', '\\beta', '\\pi', '\\phi', '\\Delta', '\\eta', '\\mu', '\\sigma', '\\infty']
            if not any(seg.endswith(x) for x in allowed_endings):
                errors.append(f"Possible truncated backslash command in LaTeX '{seg}'")
    return errors

def audit_json_index():
    """Audits the in-memory JsonIndex representation of the syllabus data."""
    logger.info("Initializing JsonIndex...")
    try:
        index = get_index()
    except Exception as e:
        logger.error(f"Failed to build JsonIndex: {e}")
        return False

    errors_found = 0
    warnings_found = 0

    # 1. Audit stats & general structure
    stats = index.get_stats()
    logger.info(f"Loaded Index Stats: {json.dumps(stats, indent=2)}")

    if stats["boards"] == 0:
        logger.error("Database/Index has no boards configured.")
        errors_found += 1
    if stats["subjects"] == 0:
        logger.error("Database/Index has no subjects configured.")
        errors_found += 1
    if stats["chapters"] == 0:
        logger.error("Database/Index has no chapters configured.")
        errors_found += 1

    # 2. Schema structure validations
    logger.info("Verifying relationship mapping inside JSON index...")
    boards = index.get_boards()
    for board in boards:
        board_id = board["id"]
        tree = index.get_board_tree(board_id)
        if not tree:
            logger.error(f"Board tree for '{board_id}' returned None.")
            errors_found += 1
            continue

        for subject in tree.get("subjects", []):
            subj_id = subject["id"]
            chapters = index.get_chapters(subject_id=subj_id)
            if not chapters:
                logger.warning(f"Subject '{subj_id}' has 0 chapters mapped.")
                warnings_found += 1

            for ch in chapters:
                ch_id = ch["id"]
                topics = index.get_topics(chapter_id=ch_id)
                if not topics:
                    logger.warning(f"Chapter '{ch['title']}' (ID: {ch_id}) has 0 topics mapped.")
                    warnings_found += 1

                for t in topics:
                    t_id = t["id"]
                    t_detail = index.get_topic(t_id)
                    if not t_detail:
                        logger.error(f"Failed to retrieve detail for topic '{t['title']}' (ID: {t_id})")
                        errors_found += 1
                        continue

                    context_path = f"{board_id} -> {subj_id} -> {ch['title']} -> {t['title']}"

                    # Audit topic content
                    content = t_detail.get("content", "")
                    if content:
                        # Audit LaTeX equations
                        latex_errs = verify_latex(content, context_path)
                        for err in latex_errs:
                            logger.error(f"LaTeX error in {context_path} content: {err}")
                            errors_found += 1
                        
                        # Audit placeholder strings
                        if "placeholder" in content.lower() or "lorem ipsum" in content.lower():
                            logger.warning(f"Placeholder content found in {context_path}")
                            warnings_found += 1

                    # Audit chunks
                    chunks = t_detail.get("chunks", [])
                    if not chunks:
                        logger.warning(f"Topic '{t['title']}' has no content chunks.")
                        warnings_found += 1

                    for idx, chunk in enumerate(chunks):
                        chunk_path = f"{context_path} -> Chunk {idx} ({chunk.get('title', 'No Title')})"
                        c_text = chunk.get("content", "")
                        
                        # Verify chunk LaTeX
                        latex_errs = verify_latex(c_text, chunk_path)
                        for err in latex_errs:
                            logger.error(f"LaTeX error in {chunk_path}: {err}")
                            errors_found += 1

                        if "placeholder" in c_text.lower() or "lorem ipsum" in c_text.lower():
                            logger.warning(f"Placeholder content in {chunk_path}")
                            warnings_found += 1

                    # Audit problems
                    problems = t_detail.get("problems", [])
                    for idx, prob in enumerate(problems):
                        prob_path = f"{context_path} -> Problem {idx} (ID: {prob.get('id', 'N/A')})"
                        p_text = prob.get("problem_text", "")
                        s_text = prob.get("solution_text", "")

                        # Verify problem & solution LaTeX
                        for text, field_name in [(p_text, "problem_text"), (s_text, "solution_text")]:
                            if text:
                                latex_errs = verify_latex(text, prob_path)
                                for err in latex_errs:
                                    logger.error(f"LaTeX error in {prob_path} [{field_name}]: {err}")
                                    errors_found += 1

    # 3. Check physical file output matching
    syllabus_cache_file = curr_dir / "syllabus_index.json"
    if syllabus_cache_file.exists():
        logger.info("Verifying physical syllabus_index.json output consistency...")
        try:
            with open(syllabus_cache_file, "r", encoding="utf-8") as f:
                cached_data = json.load(f)
            if "subjects" not in cached_data or "subject_chapters" not in cached_data:
                logger.error("syllabus_index.json is missing required root keys.")
                errors_found += 1
        except Exception as e:
            logger.error(f"Failed to parse syllabus_index.json: {e}")
            errors_found += 1

    logger.info(f"Harness Audit Completed: {errors_found} Errors, {warnings_found} Warnings found.")
    return errors_found == 0

if __name__ == "__main__":
    success = audit_json_index()
    if success:
        logger.info("🎉 Verification Harness Passed: All indexed educational data structured correctly!")
        sys.exit(0)
    else:
        logger.error("❌ Verification Harness Failed: Educational data has formatting/structure errors.")
        sys.exit(1)
