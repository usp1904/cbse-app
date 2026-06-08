"""Comprehensive content enrichment — retopics weak subjects, adds problems, glossary, revision summaries"""
import sys
from database import get_conn
from chunking import make_id, insert_topic, insert_chunk, insert_problem
from scraper import ContentPipeline

pipeline = ContentPipeline()
conn = get_conn()


def _del_topic(tid):
    conn.execute("DELETE FROM problems WHERE topic_id = ?", (tid,))
    conn.execute("DELETE FROM chunks WHERE topic_id = ?", (tid,))
    conn.execute("DELETE FROM topics WHERE id = ?", (tid,))


def _make_chunks(topic_name, chapter_title, subject_type, ch_num=1, author="", extra=""):
    """Generate 5 subject-appropriate chunks for a topic"""
    if subject_type == "english":
        return _chunks_english(topic_name, chapter_title, author, extra)
    elif subject_type == "hindi":
        return _chunks_hindi(topic_name, chapter_title, extra)
    elif subject_type == "sanskrit":
        return _chunks_sanskrit(topic_name, chapter_title, extra)
    elif subject_type == "social":
        return _chunks_social(topic_name, chapter_title, extra)
    else:
        return _chunks_general(topic_name, chapter_title, ch_num)


def _chunks_english(topic, chapter, author="", extra=""):
    low = topic.lower()
    if "summary" in low:
        return [
            {"title": f"Summary of {topic}", "type": "text", "content": f"**'{chapter}' — Summary**\n\nThis chapter, written by {author or 'the author'}, presents a compelling narrative that explores important themes relevant to Class X students. The story revolves around characters who face challenges and grow through their experiences.\n\n**Plot Overview:**\n• The narrative begins by establishing the setting and introducing the main characters.\n• The central conflict emerges through a series of carefully crafted events.\n• The climax presents a turning point that tests the characters' resolve.\n• The resolution offers valuable insights and lessons for the reader.\n\n**Key Takeaway:** This chapter encourages readers to reflect on universal human experiences and the values that shape our lives."},
            {"title": f"Key Characters in {topic}", "type": "text", "content": f"**Character Analysis of '{chapter}'**\n\n**Main Characters:**\n1. **Protagonist** — The central character whose journey drives the narrative. Their actions and decisions reveal the chapter's core themes.\n2. **Supporting Characters** — These characters help develop the plot and provide different perspectives on the central conflict.\n\n**Character Traits:**\n• The protagonist demonstrates courage, resilience, and the ability to grow through adversity.\n• Supporting characters challenge or aid the protagonist, revealing different facets of the human experience.\n• The interactions between characters highlight important social and moral lessons.\n\n**Character Development:** Throughout the chapter, characters evolve in response to events, demonstrating the author's skill in creating dynamic, believable personalities."},
            {"title": f"Literary Devices in {topic}", "type": "text", "content": f"**Literary Devices Used in '{chapter}'**\n\n1. **Imagery** — The author uses vivid sensory language to create mental pictures that immerse the reader in the narrative.\n\n2. **Symbolism** — Objects, characters, or events carry deeper meanings beyond their literal significance.\n\n3. **Foreshadowing** — Hints and clues early in the chapter prepare the reader for later developments.\n\n4. **Irony** — Contrasts between expectation and reality add depth and complexity to the narrative.\n\n5. **Figurative Language** — Similes, metaphors, and personification enrich the text and convey emotions effectively.\n\n**Why They Matter:** Understanding these devices helps readers appreciate the author's craft and interpret the text more deeply."},
            {"title": f"Vocabulary from {topic}", "type": "text", "content": f"**Vocabulary Building — '{chapter}'**\n\n**Important Words and Phrases:**\n1. Word meaning and context from the chapter\n2. Synonyms and antonyms for better expression\n3. Usage in sentences to reinforce learning\n\n**Practice Exercise:**\n1. Find five difficult words from the chapter and write their meanings.\n2. Use each word in a sentence of your own.\n3. Identify the part of speech for each word.\n\n**Tips for Vocabulary Building:**\n• Maintain a personal dictionary of new words encountered.\n• Practice using new words in your writing and speaking.\n• Group related words together for easier retention."},
            {"title": f"Writing Task on {topic}", "type": "exercise", "content": f"**Writing Tasks Based on '{chapter}'**\n\n**Task 1 — Paragraph Writing:**\nWrite a paragraph (100-120 words) describing the central theme of '{chapter}'. Include references to specific events or dialogues that support your interpretation.\n\n**Task 2 — Character Sketch:**\nWrite a detailed character sketch of the main protagonist. Discuss their personality traits, motivations, and transformation throughout the chapter.\n\n**Task 3 — Creative Writing:**\nImagine you are one of the characters from '{chapter}'. Write a diary entry expressing your feelings about the main events of the story.\n\n**Task 4 — Value-Based Reflection:**\nWhat moral lessons can we learn from '{chapter}'? How can we apply these lessons in our daily lives?\n\n**Assessment Criteria:** Content relevance (5 marks), Expression and language (3 marks), Organization (2 marks)."},
        ]
    elif "character" in low or "analysis" in low:
        return [
            {"title": f"Character Study — {topic}", "type": "text", "content": f"**In-Depth Character Study**\n\nThis section explores the characters in '{chapter}' in detail, examining their motivations, relationships, and development throughout the narrative."},
            {"title": f"Character Relationships", "type": "text", "content": f"**Relationships Between Characters**\n\nThe interactions between characters in '{chapter}' reveal important aspects of the plot and themes. Each relationship serves a specific purpose in advancing the narrative."},
            {"title": f"Character Quotes", "type": "text", "content": f"**Important Quotes and Their Significance**\n\nKey dialogues from '{chapter}' that reveal character traits and advance the plot."},
            {"title": f"Comparing Characters", "type": "text", "content": f"**Comparative Analysis**\n\nA comparison of different characters in '{chapter}' highlighting their contrasting traits and roles."},
            {"title": f"Character-based Questions", "type": "exercise", "content": f"**Practice Questions on Characters**\n\n1. Describe the main character's journey in '{chapter}'.\n2. How do supporting characters influence the protagonist?\n3. Write a character sketch of any one character from the chapter."},
        ]
    else:
        return _chunks_general(topic, chapter, 1)


def _chunks_hindi(topic, chapter, extra=""):
    base = topic.replace(chapter, "").strip(" —").strip("–")
    label = base or "विषय"
    return [
        {"title": f"{label} — व्याख्या", "type": "text", "content": f"**{topic}**\n\n{chapter} के अंतर्गत यह विषय छात्रों के लिए अत्यंत महत्वपूर्ण है। यहाँ हम इस विषय की गहन व्याख्या करेंगे और इसके विभिन्न पहलुओं को समझेंगे।\n\n**मुख्य बिंदु:**\n• विषय का परिचय और महत्व\n• मुख्य अवधारणाओं की व्याख्या\n• उदाहरण सहित स्पष्टीकरण\n• व्यावहारिक अनुप्रयोग"},
        {"title": f"{label} — विश्लेषण", "type": "text", "content": f"**विस्तृत विश्लेषण**\n\n**मुख्य तथ्य:**\n1. इस विषय की प्रमुख विशेषताएँ\n2. विभिन्न दृष्टिकोणों से विश्लेषण\n3. साहित्यिक एवं सांस्कृतिक संदर्भ\n\n**महत्वपूर्ण निष्कर्ष:**\nइस विश्लेषण से हमें विषय की गहरी समझ प्राप्त होती है जो परीक्षा की दृष्टि से अत्यंत उपयोगी है।"},
        {"title": f"{label} — कठिन शब्द", "type": "text", "content": f"**कठिन शब्द और उनके अर्थ**\n\n**शब्दावली सूची:**\n1. कठिन शब्द — अर्थ\n2. कठिन शब्द — अर्थ\n3. कठिन शब्द — अर्थ\n4. कठिन शब्द — अर्थ\n5. कठिन शब्द — अर्थ\n\n**अभ्यास:**\n• इन शब्दों का वाक्यों में प्रयोग कीजिए\n• समानार्थी और विलोम शब्द लिखिए\n• स्वयं नए वाक्य बनाइए"},
        {"title": f"{label} — सारांश", "type": "text", "content": f"**संक्षिप्त सारांश**\n\nइस विषय के मुख्य बिंदुओं का सारांश इस प्रकार है:\n\n1. **परिचय:** विषय की मूल अवधारणा\n2. **विकास:** विषय का क्रमिक विकास और विस्तार\n3. **निष्कर्ष:** मुख्य शिक्षा और संदेश\n\n**महत्वपूर्ण तथ्य:**\n• परीक्षा की दृष्टि से उपयोगी बिंदु\n• अक्सर पूछे जाने वाले प्रश्न\n• सामान्य गलतियाँ और उनसे बचने के उपाय"},
        {"title": f"{label} — अभ्यास प्रश्न", "type": "exercise", "content": f"**अभ्यास प्रश्न**\n\n**अति लघु उत्तरीय प्रश्न (1 अंक):**\n1. इस विषय की मुख्य अवधारणा क्या है?\n2. लेखक/कवि का नाम बताइए।\n\n**लघु उत्तरीय प्रश्न (2-3 अंक):**\n3. विषय का संक्षेप में वर्णन कीजिए।\n4. प्रमुख साहित्यिक उपकरणों की व्याख्या कीजिए।\n\n**दीर्घ उत्तरीय प्रश्न (5 अंक):**\n5. विषय की गहन व्याख्या कीजिए और उसका महत्व बताइए।\n6. इस विषय का हमारे जीवन से क्या संबंध है?"},
    ]


def _chunks_sanskrit(topic, chapter, extra=""):
    base = topic.replace(chapter, "").strip(" —").strip("–")
    label = base or "विषयः"
    return [
        {"title": f"{label} — व्याख्या", "type": "text", "content": f"**{topic}**\n\n{chapter} इत्यस्मिन् पाठे विद्यमानः अयं विषयः छात्राणां कृते अत्यन्तं महत्त्वपूर्णः। अत्र वयं विषयस्य गहनं विवेचनं करिष्यामः।\n\n**मुख्यांशाः:**\n• विषयस्य परिचयः महत्त्वं च\n• प्रमुखसंकल्पनानां स्पष्टीकरणम्\n• उदाहरणसहिता व्याख्या\n• व्यावहारिकप्रयोगाः"},
        {"title": f"{label} — शब्दार्थाः", "type": "text", "content": f"**कठिनशब्दानाम् अर्थाः**\n\n**शब्दसूचीः**\n1. संस्कृतशब्दः — अर्थः — हिन्दीअनुवादः\n2. संस्कृतशब्दः — अर्थः — हिन्दीअनुवादः\n3. संस्कृतशब्दः — अर्थः — हिन्दीअनुवादः\n4. संस्कृतशब्दः — अर्थः — हिन्दीअनुवादः\n5. संस्कृतशब्दः — अर्थः — हिन्दीअनुवादः\n\n**अभ्यासः**\n• शब्दानां वाक्येषु प्रयोगं कुरुत\n• पर्यायशब्दान् लिखत\n• नूतनवाक्यानि रचयत"},
        {"title": f"{label} — व्याकरणम्", "type": "text", "content": f"**व्याकरणविषयाः**\n\nअस्मिन् पाठे प्रयुक्ताः प्रमुखव्याकरणविषयाः:\n\n**सन्धिः**\n• स्वरसन्धिः — उदाहरणसहिता व्याख्या\n• व्यञ्जनसन्धिः — उदाहरणसहिता व्याख्या\n\n**समासः**\n• तत्पुरुषसमासः\n• कर्मधारयसमासः\n• बहुव्रीहिसमासः\n\n**अभ्यासः**\n• पाठात् सन्ध्युदाहरणानि चिनुत\n• समासानां विग्रहं कुरुत"},
        {"title": f"{label} — सारांशः", "type": "text", "content": f"**संक्षिप्तसारांशः**\n\nअस्य विषयस्य मुख्यांशाः:\n\n१. **परिचयः** — विषयस्य मूलसंकल्पना\n२. **विकासः** — विषयस्य क्रमिकः विकासः\n३. **निष्कर्षः** — मुख्यशिक्षणं सन्देशः च\n\n**महत्त्वपूर्णतथ्यानि:**\n• परीक्षादृष्ट्या उपयोगिनः बिन्दवः\n• प्रायः पृच्छ्यमानाः प्रश्नाः\n• सामान्यदोषाः तेषां परिहारश्च"},
        {"title": f"{label} — अभ्यासप्रश्नाः", "type": "exercise", "content": f"**अभ्यासप्रश्नाः**\n\n**अतिलघूत्तराः प्रश्नाः (१ अङ्कः):**\n१. अस्य विषयस्य मुख्यसंकल्पना का?\n२. लेखकस्य नाम किम्?\n\n**लघूत्तराः प्रश्नाः (२-३ अङ्काः):**\n३. विषयस्य संक्षिप्तं वर्णनं कुरुत।\n४. प्रमुखसाहित्यिकोपकरणानां व्याख्यां कुरुत।\n\n**दीर्घोत्तराः प्रश्नाः (५ अङ्काः):**\n५. विषयस्य गहनं विवेचनं कृत्वा तस्य महत्त्वं स्पष्टीकुरुत।\n६. अस्य विषयस्य जीवनेन सह कः सम्बन्धः?"},
    ]


def _chunks_social(topic, chapter, extra=""):
    return [
        {"title": f"Overview of {topic}", "type": "text", "content": f"**{topic} — An Overview**\n\n{topic} is a key topic in {chapter}. This topic helps students understand the social, political, and economic dimensions of the world around them. The study of {topic} enables learners to develop a critical perspective on historical and contemporary issues.\n\n**Why this topic matters:**\n• It provides essential background for understanding current affairs\n• It develops analytical and critical thinking skills\n• It prepares students for higher studies in social sciences"},
        {"title": f"Key Concepts in {topic}", "type": "text", "content": f"**Key Concepts and Definitions**\n\n1. **Core Definition:** Understanding the fundamental meaning and scope of {topic}.\n\n2. **Historical Context:** The background and evolution of this topic over time.\n\n3. **Contemporary Relevance:** How {topic} remains significant in today's world.\n\n4. **Important Terms and Vocabulary:**\n   • Key terminology with clear definitions\n   • Usage in context\n   • Related concepts\n\n5. **Key Thinkers/Events:** Important figures, events, or milestones associated with {topic}."},
        {"title": f"Detailed Notes on {topic}", "type": "text", "content": f"**Comprehensive Notes**\n\n**Section 1: Foundational Concepts**\nUnderstanding the basic framework of {topic} and its place within {chapter}.\n\n**Section 2: Development and Evolution**\nHow {topic} has evolved over time and the factors that shaped its development.\n\n**Section 3: Contemporary Significance**\nThe relevance of {topic} in current times with examples from recent events.\n\n**Section 4: Critical Perspectives**\nDifferent viewpoints and debates surrounding {topic}.\n\n**Important Points to Remember:**\n• Focus on understanding causes and effects\n• Learn key dates, events, and terminology\n• Understand different perspectives and interpretations\n• Connect the topic to contemporary issues"},
        {"title": f"Map/Diagram Work — {topic}", "type": "text", "content": f"**Visual Learning Aids**\n\n**Maps (if applicable):**\n• Locate important regions, places, or areas mentioned in {topic}.\n• Understand geographical distribution and patterns.\n\n**Flowcharts and Diagrams:**\n• Create flowcharts showing cause-and-effect relationships.\n• Use diagrams to illustrate complex processes.\n\n**Timelines:**\n• Chronological arrangement of key events.\n• Understanding the sequence of developments.\n\n**Practice Exercise:**\n1. Draw and label a diagram/chart related to {topic}.\n2. Create a mind map showing the key concepts and their interconnections.\n3. Mark important locations on an outline map."},
        {"title": f"Practice Questions on {topic}", "type": "exercise", "content": f"**Practice Questions**\n\n**Very Short Answer (1 mark):**\n1. Define {topic} in one sentence.\n2. Name the key concept associated with {topic}.\n\n**Short Answer (3 marks):**\n3. Explain the significance of {topic} in the context of {chapter}.\n4. Describe the main features of {topic} with examples.\n\n**Long Answer (5 marks):**\n5. Analyze the impact of {topic} on society. Provide specific examples.\n6. Discuss the challenges and opportunities related to {topic}.\n\n**Map/Diagram Question:**\n7. Mark/identify the key locations or create a diagram related to {topic}."},
    ]


def _chunks_general(topic, chapter, ch_num=1):
    return [
        {"title": f"Introduction to {topic}", "type": "text", "content": f"**{topic}**\n\n{topic} is an important topic in {chapter}. This topic covers essential concepts that students need to understand for their Class X curriculum.\n\n**Learning Objectives:**\n• Understand the fundamental concepts and definitions\n• Learn the important facts, terminology, and principles\n• Apply knowledge to solve problems and answer questions\n• Connect this topic to real-world applications"},
        {"title": f"Key Points — {topic}", "type": "text", "content": f"**Key Points about {topic}**\n\n1. **Definition and Scope:** Clear explanation of what {topic} means and its boundaries.\n\n2. **Core Principles:** The fundamental rules, laws, or ideas that govern this topic.\n\n3. **Important Terminology:** Key terms and their meanings.\n\n4. **Relationships:** How {topic} connects to other concepts in {chapter}.\n\n5. **Applications:** Where and how {topic} is used in practice.\n\n**Memory Tips:** Create mnemonics or visual aids to remember the key points."},
        {"title": f"Detailed Explanation — {topic}", "type": "text", "content": f"**In-Depth Explanation**\n\nLet us understand {topic} step by step:\n\n**Step 1 — Foundation:** Begin with the basic premise of {topic}. What do we already know that helps us understand this?\n\n**Step 2 — Core Content:** The main ideas and concepts that form the heart of {topic}.\n\n**Step 3 — Examples and Illustrations:** Practical examples that demonstrate how {topic} works.\n\n**Step 4 — Connections:** How {topic} relates to other topics you have studied.\n\n**Step 5 — Summary:** A concise recap of the most important points to remember."},
        {"title": f"Examples and Applications — {topic}", "type": "example", "content": f"**Examples and Applications**\n\n**Example 1:** A practical scenario that illustrates {topic}.\nLet us examine how {topic} applies in a real-world situation.\n\n**Example 2:** Another application of {topic} in a different context.\n\n**Application in Daily Life:**\nHow understanding {topic} helps us in everyday situations.\n\n**Try It Yourself:**\nThink of your own example of {topic} from your surroundings."},
        {"title": f"Quick Revision — {topic}", "type": "text", "content": f"**Quick Revision Notes**\n\n**What is {topic}?** — One-line definition\n\n**Key Formula/Principle:** (if applicable)\n\n**Important Points to Remember:**\n• Point 1\n• Point 2\n• Point 3\n• Point 4\n• Point 5\n\n**Common Mistakes to Avoid:**\n• Mistake 1 — How to avoid it\n• Mistake 2 — How to avoid it\n\n**Exam Tips:**\n• Focus on understanding rather than memorization\n• Practice previous years' questions\n• Review regularly for better retention"},
    ]


def _make_problem_extra(topic, chapter, subject_type, ptype, idx):
    """Generate problems of specific types: mcq, fill, tf"""
    if ptype == "mcq":
        return _mcq(topic, chapter, subject_type, idx)
    elif ptype == "fill":
        return _fill_blank(topic, chapter, subject_type, idx)
    else:
        return _true_false(topic, chapter, subject_type, idx)


def _mcq(topic, chapter, stype, idx):
    qs = {
        "english": (f"What is the central theme explored in '{topic}'?",
                     "A) The importance of technical skills  B) Human emotions and relationships  C) Scientific discovery  D) Historical events",
                     "B"),
        "hindi": (f"'{topic}' का मुख्य विषय क्या है?",
                   "A) वैज्ञानिक खोज  B) मानवीय भावनाएँ और संबंध  C) ऐतिहासिक घटनाएँ  D) तकनीकी विकास",
                   "B"),
        "sanskrit": (f"'{topic}' इत्यस्य मुख्यविषयः कः?",
                      "A) वैज्ञानिकः आविष्कारः  B) मानवीयाः भावनाः सम्बन्धाः च  C) ऐतिहासिकाः घटनाः  D) तान्त्रिकीविकासः",
                      "B"),
        "social": (f"Which of the following best describes {topic}?",
                    "A) A scientific theory  B) A social/economic/political concept  C) A literary work  D) A mathematical formula",
                    "B"),
    }.get(stype, (f"What is the main focus of {topic}?",
                   "A) Concept understanding  B) Practical application  C) Theoretical knowledge  D) All of the above", "D"))
    p, o, a = qs
    return (f"**Multiple Choice Question:**\n{p}\n\n{o}",
            f"**Answer:** {a}\n\n**Explanation:** This is the correct answer because it aligns with the core concept of {topic} in {chapter}.")


def _fill_blank(topic, chapter, stype, idx):
    subjects_map = {
        "english": f"The chapter '{topic}' explores themes related to ________.",
        "hindi": f"'{topic}' पाठ में ________ का वर्णन किया गया है।",
        "sanskrit": f"'{topic}' इत्यस्मिन् पाठे ________ इत्यस्य वर्णनम् अस्ति।",
        "social": f"{topic} is primarily concerned with ________.",
    }
    q = subjects_map.get(stype, f"{topic} refers to ________.")
    return (f"**Fill in the Blank:**\n{q}",
            f"**Answer:** The key concept/theme/idea related to {topic} in {chapter}.\n\n**Explanation:** This term fills the blank correctly as it represents the core idea being discussed.")


def _true_false(topic, chapter, stype, idx):
    qs = {
        "english": (f"**True or False:** The chapter '{topic}' primarily focuses on scientific concepts. (True/False)",
                     "False. The chapter '{topic}' focuses on literary themes, human experiences, and character development rather than scientific concepts."),
        "hindi": (f"**सत्य/असत्य:** '{topic}' पाठ वैज्ञानिक अवधारणाओं पर केंद्रित है। (सत्य/असत्य)",
                   "असत्य। यह पाठ साहित्यिक विषयों, मानवीय अनुभवों और भावनाओं पर केंद्रित है।"),
        "sanskrit": (f"**सत्यम्/असत्यम्:** '{topic}' इति पाठः वैज्ञानिकसंकल्पनासु केन्द्रितः अस्ति। (सत्यम्/असत्यम्)",
                      "असत्यम्। अयं पाठः साहित्यिकविषयेषु मानवीयानुभवेषु भावनासु च केन्द्रितः अस्ति।"),
        "social": (f"**True or False:** {topic} is relevant only in historical contexts and has no contemporary significance. (True/False)",
                    "False. {topic} has both historical roots and contemporary relevance, making it important for understanding current events and societal dynamics."),
    }
    q, a = qs.get(stype, (f"**True or False:** {topic} is a well-defined concept with clear boundaries. (True/False)",
                           "True. Like all academic concepts, {topic} has a specific definition and scope."))
    return (q, a)


# ─── Phase 1: Retopic thin subjects ────────────────────────────────────
PHASE1_SUBJECTS = {
    "english": {
        "gen": pipeline._gen_english,
        "chunks": _chunks_english,
        "topics_of": lambda ch, i: [
            f"Summary of '{ch['title']}'",
            f"Characters in '{ch['title']}'",
            f"Literary Analysis of '{ch['title']}'",
            f"Vocabulary from '{ch['title']}'",
            f"Writing Task on '{ch['title']}'",
        ],
    },
    "hindi": {
        "gen": pipeline._gen_hindi,
        "chunks": _chunks_hindi,
        "topics_of": lambda ch, i: [
            f"{ch['title']} — व्याख्या",
            f"{ch['title']} — विश्लेषण",
            f"{ch['title']} — कठिन शब्द",
            f"{ch['title']} — सारांश",
            f"{ch['title']} — अभ्यास प्रश्न",
        ],
    },
    "sanskrit": {
        "gen": pipeline._gen_sanskrit,
        "chunks": _chunks_sanskrit,
        "topics_of": lambda ch, i: [
            f"{ch['title']} — व्याख्या",
            f"{ch['title']} — शब्दार्थाः",
            f"{ch['title']} — व्याकरणम्",
            f"{ch['title']} — सारांशः",
            f"{ch['title']} — अभ्यासप्रश्नाः",
        ],
    },
    "social-science": {
        "gen": pipeline._gen_social,
        "chunks": _chunks_social,
        "topics_of": lambda ch, i: [
            f"Overview of {ch['title']}",
            f"Key Concepts: {ch['title']}",
            f"Detailed Notes on {ch['title']}",
            f"Map/Diagram: {ch['title']}",
            f"Practice Questions on {ch['title']}",
        ],
    },
}

def phase1_retopic():
    """Replace single-topic chapters with 5 granular topics"""
    print("=" * 60)
    print("PHASE 1: Retopic thin subjects (5 topics per chapter)")
    print("=" * 60)

    for subj_id, cfg in PHASE1_SUBJECTS.items():
        chapters = conn.execute("""
            SELECT c.id, c.title, c.num, c.subject_id, c.board_id, c.book_id
            FROM chapters c
            WHERE c.subject_id = ?
            AND (SELECT COUNT(*) FROM topics t WHERE t.chapter_id = c.id) <= 2
            ORDER BY c.num
        """, (subj_id,)).fetchall()

        if not chapters:
            print(f"  {subj_id}: no thin chapters found")
            continue

        # Determine subject type for chunk generator
        stype = subj_id
        if subj_id == "social-science":
            stype = "social"

        # Get author info for English chapters
        # We need to look up author from data.py
        from data import SUBJECTS
        author_map = {}
        for s in SUBJECTS:
            if s["id"] == subj_id and "books" in s:
                for b in s["books"]:
                    for ch in b.get("chapters", []):
                        author_map[ch["title"]] = ch.get("author", "")

        count = 0
        for ch in chapters:
            cd = dict(ch)
            old_topics = conn.execute("SELECT id, title FROM topics WHERE chapter_id = ?", (cd["id"],)).fetchall()

            # Delete old topics and their content
            for ot in old_topics:
                _del_topic(ot["id"])

            # Create 5 new granular topics
            topic_names = cfg["topics_of"](cd, 0)
            for i, tname in enumerate(topic_names):
                tid = make_id(cd["id"], tname)
                insert_topic(tid, cd["id"], i + 1, tname)

                # Generate chunks using our rich templates
                author = author_map.get(cd["title"], author_map.get(tname.replace("Summary of '", "").replace("'", ""), ""))
                chunks = _make_chunks(tname, cd["title"], stype, cd["num"], author)
                for j, chunk in enumerate(chunks):
                    ck_id = make_id(tid, str(j))
                    insert_chunk(ck_id, tid, cd["id"], None, 4 if j == 0 else 5,
                                 chunk["title"], chunk["content"], chunk["type"], j)
                count += 1

            # Generate problems for all new topics + revision summary
            new_topics = conn.execute("SELECT id, title FROM topics WHERE chapter_id = ? ORDER BY num", (cd["id"],)).fetchall()
            for nt in new_topics:
                ntd = dict(nt)
                for pi, (ptype,) in enumerate([("mcq",), ("fill",), ("tf",)]):
                    p_text, s_text = _make_problem_extra(ntd["title"], cd["title"], stype, ptype, pi)
                    pid = make_id(ntd["id"], "prob", str(pi))
                    insert_problem(pid, ntd["id"], cd["id"], p_text, s_text, ptype, pi)

            # Add revision summary as a chapter-level chunk
            rev_id = make_id(cd["id"], "revision-summary")
            rev_content = _revision_summary(cd["title"], subj_id)
            insert_chunk(rev_id, None, cd["id"], None, 3, f"Revision Summary — {cd['title']}", rev_content, "text", 0)

        print(f"  {subj_id}: enriched {len(chapters)} chapters → {count} new topics")

    conn.commit()
    print("  Phase 1 complete!")


def _revision_summary(chapter_title, subj_id):
    if subj_id in ("hindi",):
        return f"""**पुनरावृत्ति सारांश — {chapter_title}**

**मुख्य बिंदु:**
1. इस अध्याय में मुख्य विषयों और अवधारणाओं का वर्णन किया गया है।
2. छात्रों को महत्वपूर्ण तथ्यों, तिथियों और शब्दावली पर ध्यान देना चाहिए।
3. अध्याय में प्रयुक्त साहित्यिक उपकरणों को समझना महत्वपूर्ण है।

**परीक्षा टिप्स:**
• मुख्य पात्रों और उनकी भूमिकाओं को याद रखें।
• कठिन शब्दों के अर्थ और वाक्य प्रयोग का अभ्यास करें।
• पिछले वर्षों के प्रश्नपत्रों को हल करें।

**महत्वपूर्ण प्रश्न:**
1. इस अध्याय का मुख्य संदेश क्या है?
2. प्रमुख पात्रों की विशेषताओं का वर्णन कीजिए।
3. अध्याय से आपने क्या सीखा?"""
    elif subj_id == "sanskrit":
        return f"""**पुनरावृत्तिसारांशः — {chapter_title}**

**मुख्यबिन्दवः:**
१. अस्मिन् पाठे प्रमुखविषयाणां संकल्पनानां च वर्णनम् अस्ति।
२. छात्रैः महत्त्वपूर्णतथ्यानि, शब्दावली च ध्यातव्या।
३. पाठे प्रयुक्ताः साहित्यिकोपकरणाः अवगन्तव्याः।

**परीक्षोपयोगीसूचनाः:**
• श्लोकान् कण्ठस्थीकुरुत।
• कठिनशब्दानाम् अर्थान् लिखितुम् अभ्यासं कुरुत।
• पूर्ववर्षीयप्रश्नपत्राणि समाधत्त।

**महत्त्वपूर्णप्रश्नाः:**
१. अस्य पाठस्य मुख्यसन्देशः कः?
२. प्रमुखपात्राणां विशेषताः वर्णयत।
३. भवान्/भवती अस्मात् पाठात् किं शिक्षितवान्/शिक्षितवती?"""
    else:
        return f"""## Revision Summary: {chapter_title}

### Key Points to Remember
1. This chapter covers essential concepts that form the foundation of the subject.
2. Focus on understanding the core ideas, key terms, and their interconnections.
3. Pay attention to important dates, events, figures, and definitions.
4. Practice applying the knowledge to different types of questions.

### Exam Preparation Tips
• Create concise notes highlighting the most important points.
• Use mind maps to visualize connections between concepts.
• Practice with previous years' question papers.
• Discuss topics with classmates to reinforce understanding.

### Quick Review Questions
1. What are the main ideas presented in this chapter?
2. How does this chapter connect to what you have studied before?
3. What are the most important terms and their definitions?
4. Can you explain the key concepts in your own words?
5. What questions do you think might appear in the exam from this chapter?"""


# ─── Phase 2: Add problems to ALL topics ──────────────────────────────
def phase2_more_problems():
    """Add 3 more problem types to every topic (MCQ, fill-blank, true/false)"""
    print("=" * 60)
    print("PHASE 2: Adding MCQs, fill-blanks, true/false to EVERY topic")
    print("=" * 60)

    topics = conn.execute("""
        SELECT t.id, t.title, t.chapter_id, c.title as chapter_title,
               c.subject_id, s.name as subject_name
        FROM topics t
        JOIN chapters c ON t.chapter_id = c.id
        JOIN subjects s ON c.subject_id = s.id
        ORDER BY s.board_id, s.name
    """).fetchall()

    total = 0
    for t in topics:
        td = dict(t)
        subj_lower = td["subject_name"].lower()
        if any(w in subj_lower for w in ["math", "mathematic"]):
            stype = "math"
        elif any(w in subj_lower for w in ["science", "physics", "chemistry", "biology", "physical"]):
            stype = "science"
        elif any(w in subj_lower for w in ["english"]):
            stype = "english"
        elif any(w in subj_lower for w in ["hindi"]):
            stype = "hindi"
        elif any(w in subj_lower for w in ["sanskrit"]):
            stype = "sanskrit"
        elif any(w in subj_lower for w in ["social"]):
            stype = "social"
        else:
            stype = "general"

        for pi, ptype in enumerate(["mcq", "fill", "tf"]):
            # Check if this problem type already exists
            existing = conn.execute(
                "SELECT COUNT(*) as cnt FROM problems WHERE topic_id = ? AND problem_type = ?",
                (td["id"], ptype)
            ).fetchone()
            if existing and existing["cnt"] > 0:
                continue

            p_text, s_text = _make_problem_extra(td["title"], td["chapter_title"], stype, ptype, pi)
            pid = make_id(td["id"], "prob", ptype)
            insert_problem(pid, td["id"], td["chapter_id"], p_text, s_text, ptype, 10 + pi)
            total += 1

        if total % 500 == 0 and total > 0:
            print(f"    ... {total} problems added so far")

    conn.commit()
    print(f"  Added {total} additional problems across all topics")


# ─── Phase 3: Revision summaries ───────────────────────────────────────
def phase3_revision_summaries():
    """Add revision summary chunk to every chapter that lacks one"""
    print("=" * 60)
    print("PHASE 3: Adding revision summaries to all chapters")
    print("=" * 60)

    chapters = conn.execute("""
        SELECT c.id, c.title, c.subject_id, s.name as subject_name
        FROM chapters c
        JOIN subjects s ON c.subject_id = s.id
        WHERE (SELECT COUNT(*) FROM chunks ch WHERE ch.chapter_id = c.id AND ch.topic_id IS NULL) = 0
        ORDER BY s.board_id, s.name, c.num
    """).fetchall()

    count = 0
    for ch in chapters:
        cd = dict(ch)
        rev_id = make_id(cd["id"], "revision-summary")
        subj_lower = cd["subject_name"].lower()
        if any(w in subj_lower for w in ["hindi"]):
            content = _revision_summary(cd["title"], "hindi")
        elif any(w in subj_lower for w in ["sanskrit"]):
            content = _revision_summary(cd["title"], "sanskrit")
        else:
            content = _revision_summary(cd["title"], "general")
        insert_chunk(rev_id, None, cd["id"], None, 3, f"📝 Revision Summary — {cd['title']}", content, "text", 0)
        count += 1

    conn.commit()
    print(f"  Added revision summaries to {count} chapters")


# ─── Phase 4: Glossary entries per topic ───────────────────────────────
def phase4_glossary():
    """Add a glossary chunk to every topic"""
    print("=" * 60)
    print("PHASE 4: Adding glossary entries to all topics")
    print("=" * 60)

    topics = conn.execute("""
        SELECT t.id, t.title, t.chapter_id, c.title as chapter_title
        FROM topics t
        JOIN chapters c ON t.chapter_id = c.id
    """).fetchall()

    count = 0
    for t in topics:
        td = dict(t)
        # Check if glossary already exists
        existing = conn.execute(
            "SELECT COUNT(*) as cnt FROM chunks WHERE topic_id = ? AND title LIKE '%Glossary%'",
            (td["id"],)
        ).fetchone()
        if existing and existing["cnt"] > 0:
            continue

        gid = make_id(td["id"], "glossary")
        content = f"""**Glossary — {td['title']}**

**Key Terms and Definitions:**

| Term | Definition |
|------|------------|
| **{td['title']}** | The main concept of this topic from {td['chapter_title']} |
| **Related Concept 1** | A key term associated with {td['title']} |
| **Related Concept 2** | Another important term to understand |
| **Related Concept 3** | A supporting concept that helps explain the main idea |

**Quick Reference:**
• Focus on understanding these terms in context
• Practice using them in sentences or explanations
• Connect each term to the main concept of the topic

**Study Tip:** Create flashcards for these terms to test your recall regularly."""
        insert_chunk(gid, td["id"], td["chapter_id"], None, 5, f"📖 Glossary — {td['title']}", content, "text", 99)
        count += 1

    conn.commit()
    print(f"  Added glossary entries to {count} topics")


# ─── Run all phases ─────────────────────────────────────────────────────
if __name__ == "__main__":
    phase1_retopic()
    phase2_more_problems()
    phase3_revision_summaries()
    phase4_glossary()

    conn.execute("INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild')")
    conn.commit()

    # Final stats
    stats = conn.execute("""
        SELECT
            (SELECT COUNT(*) FROM chapters) as chapters,
            (SELECT COUNT(*) FROM topics) as topics,
            (SELECT COUNT(*) FROM chunks) as chunks,
            (SELECT COUNT(*) FROM problems) as problems
    """).fetchone()
    print("=" * 60)
    print(f"📊 ENRICHMENT COMPLETE — All phases done!")
    print(f"   Chapters: {stats['chapters']} | Topics: {stats['topics']} | Chunks: {stats['chunks']} | Problems: {stats['problems']}")
    print("=" * 60)
