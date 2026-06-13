import json
import os
import re
import urllib.request
import urllib.error
from chunking import (
    insert_board, insert_subject, insert_book, insert_chapter,
    insert_topic, insert_chunk, insert_problem, make_id,
)
from database import get_conn, init_db

CONTENT_DIR = os.path.join(os.path.dirname(__file__), "content")


class ContentPipeline:
    def __init__(self):
        init_db()

    def import_from_data_module(self, subjects_data, board_id="cbse", board_name="CBSE Class X"):
        insert_board(board_id, board_name, "Central Board of Secondary Education - Class X", "https://ncert.nic.in/")
        conn = get_conn()

        for subject in subjects_data:
            sid = subject["id"]
            insert_subject(sid, board_id, subject["name"], subject.get("code", ""),
                           subject.get("description", ""), subject.get("ncert_url", ""))

            subject_type = self._detect_subject_type(sid, subject)

            if "books" in subject:
                for book in subject["books"]:
                    bid = make_id(sid, book.get("code", book["name"]))
                    insert_book(bid, sid, book["name"], book.get("code", ""), book.get("ncert_url", ""))

                    for ch in book.get("chapters", []):
                        cid = make_id(sid, bid, str(ch["num"]))
                        insert_chapter(cid, bid, sid, board_id, ch["num"], ch["title"])
                        if ch.get("topics"):
                            for i, topic_name in enumerate(ch["topics"]):
                                tid = make_id(cid, topic_name)
                                insert_topic(tid, cid, i + 1, topic_name)
                                self._generate_topic_content(tid, cid, topic_name, ch["title"],
                                                             ch["num"], sid, subject_type, ch)
                        else:
                            tid = make_id(cid, ch["title"])
                            insert_topic(tid, cid, 1, ch["title"])
                            self._generate_topic_content(tid, cid, ch["title"], ch["title"],
                                                         ch["num"], sid, subject_type, ch)

                    for po in book.get("poems", []):
                        cid = make_id(sid, bid, "poem_" + str(po["num"]))
                        insert_chapter(cid, bid, sid, board_id, po["num"], po["title"])
                        tid = make_id(cid, po["title"])
                        insert_topic(tid, cid, 1, f"Summary of '{po['title']}'")
                        self._generate_poem_content(tid, cid, po, sid)
            else:
                for ch in subject.get("chapters", []):
                    cid = make_id(sid, str(ch["num"]))
                    insert_chapter(cid, None, sid, board_id, ch["num"], ch["title"])
                    if ch.get("topics"):
                        for i, topic_name in enumerate(ch["topics"]):
                            tid = make_id(cid, topic_name)
                            insert_topic(tid, cid, i + 1, topic_name)
                            self._generate_topic_content(tid, cid, topic_name, ch["title"],
                                                         ch["num"], sid, subject_type, ch)
                    else:
                        tid = make_id(cid, ch["title"])
                        insert_topic(tid, cid, 1, ch["title"])
                        self._generate_topic_content(tid, cid, ch["title"], ch["title"],
                                                     ch["num"], sid, subject_type, ch)
        conn.commit()
        conn.execute("INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild')")
        conn.commit()

    def _detect_subject_type(self, sid, subject):
        name = subject.get("name", sid).lower()
        if any(w in name for w in ["math", "mathematic"]):
            return "math"
        if any(w in name for w in ["science", "physics", "chemistry", "biology", "physical"]):
            return "science"
        if any(w in name for w in ["english", "first language"]):
            return "english"
        if any(w in name for w in ["social", "history", "geography", "political", "economic", "civic"]):
            return "social"
        if any(w in name for w in ["hindi"]):
            return "hindi"
        if any(w in name for w in ["sanskrit"]):
            return "sanskrit"
        return "general"

    def _generate_topic_content(self, topic_id, chapter_id, topic_name, chapter_title,
                                 chapter_num, subject_id, subject_type, chapter=None):
        generator = getattr(self, f"_gen_{subject_type}", self._gen_general)
        chunks = generator(topic_name, chapter_title, chapter_num, subject_id, chapter or {})
        for i, chunk in enumerate(chunks):
            cid = make_id(topic_id, str(i))
            insert_chunk(cid, topic_id, chapter_id, None, chunk.get("level", 4),
                         chunk.get("title", topic_name), chunk.get("content", ""),
                         chunk.get("type", "text"), i)

    def _gen_math(self, topic, chapter, ch_num, subject, _ch):
        t = topic.lower()
        return [
            {"title": f"Understanding {topic}", "level": 4, "type": "text",
             "content": f"{topic} is a fundamental concept in {chapter}. "
                        f"This topic is crucial for building a strong foundation in mathematics for Class X. "
                        f"The key idea revolves around understanding the core principles and their applications in solving mathematical problems."},
            {"title": f"Important Concepts of {topic}", "level": 5, "type": "text",
             "content": f"**Key Concepts of {topic}:**\n\n"
                        f"1. **Definition**: Understand the formal definition and mathematical formulation.\n"
                        f"2. **Properties**: Learn the important properties and their derivations.\n"
                        f"3. **Formulas**: Memorize the key formulas and understand when to apply each one.\n"
                        f"4. **Special Cases**: Be aware of edge cases and special conditions.\n"
                        f"5. **Relationships**: Understand how this topic connects to other topics in {chapter}.",
             "level": 5, "type": "text"},
            {"title": f"Worked Example — {topic}", "level": 6, "type": "example",
             "content": f"**Example: Application of {topic}**\n\n"
                        f"**Problem**: Consider a problem involving {topic} from {chapter}.\n\n"
                        f"**Solution — Step-by-Step:**\n"
                        f"**Step 1:** Identify the given information and what needs to be found.\n"
                        f"**Step 2:** Recall the relevant formula or theorem for {topic}.\n"
                        f"**Step 3:** Substitute the known values into the formula.\n"
                        f"**Step 4:** Solve step-by-step, showing all working.\n"
                        f"**Step 5:** Verify the answer by checking if it satisfies the original conditions.\n\n"
                        f"**Answer:** The result confirms the concept of {topic}."},
            {"title": f"Common Mistakes to Avoid — {topic}", "level": 5, "type": "text",
             "content": f"**Common Mistakes Students Make with {topic}:**\n\n"
                        f"❌ Forgetting to apply the correct sign convention\n"
                        f"❌ Misapplying the formula in the wrong context\n"
                        f"❌ Not simplifying intermediate steps properly\n"
                        f"❌ Skipping verification of the final answer\n\n"
                        f"**Tips:**\n"
                        f"✓ Always write the formula before substituting values\n"
                        f"✓ Check units and signs carefully\n"
                        f"✓ Practice with NCERT textbook exercises\n"
                        f"✓ Review the concept if you make repeated errors"},
            {"title": f"Practice Problems — {topic}", "level": 7, "type": "exercise",
             "content": f"**Practice Problems for {topic}**\n\n"
                        f"**Level 1 (Basic):**\n"
                        f"1. State the basic principle of {topic}.\n"
                        f"2. Solve simple problems applying the fundamental formula.\n\n"
                        f"**Level 2 (Intermediate):**\n"
                        f"3. Solve problems involving multiple steps.\n"
                        f"4. Apply {topic} to real-world scenarios.\n\n"
                        f"**Level 3 (Advanced):**\n"
                        f"5. Solve complex problems combining {topic} with other concepts from {chapter}.\n"
                        f"6. Prove or derive the key result related to {topic}.\n\n"
                        f"**NCERT Reference:** Chapter {ch_num}, Exercises from NCERT textbook."},
        ]

    def _gen_science(self, topic, chapter, ch_num, subject, _ch):
        return [
            {"title": f"Introduction to {topic}", "level": 4, "type": "text",
             "content": f"{topic} is an important concept in {chapter}. "
                        f"This topic helps us understand the fundamental principles of science as they apply to real-world phenomena. "
                        f"In Class X, students are expected to grasp the core ideas and their practical implications."},
            {"title": f"Key Concepts of {topic}", "level": 5, "type": "text",
             "content": f"**Key Concepts of {topic}:**\n\n"
                        f"1. **Definition and Explanation**: {topic} refers to the scientific principle that governs this area of study.\n"
                        f"2. **Working Mechanism**: The process works through a series of well-defined steps that can be observed and measured.\n"
                        f"3. **Important Terms**: Familiarize yourself with the key terminology associated with {topic}.\n"
                        f"4. **Applications**: This concept has important applications in daily life and technology.\n"
                        f"5. **Experiments**: Practical demonstrations help reinforce understanding of {topic}."},
            {"title": f"Detailed Explanation — {topic}", "level": 5, "type": "text",
             "content": f"**Detailed Explanation of {topic}:**\n\n"
                        f"{topic} can be understood by breaking it down into its fundamental components. "
                        f"The key principle involves understanding how different factors interact to produce the observed outcome.\n\n"
                        f"**Key Points to Remember:**\n"
                        f"• Focus on the core mechanism and underlying principles\n"
                        f"• Understand the cause-and-effect relationships\n"
                        f"• Learn the scientific terminology and their meanings\n"
                        f"• Relate the concept to real-world examples\n\n"
                        f"**Did You Know?** This concept is essential for understanding more advanced topics in science and forms the basis for many technological applications."},
            {"title": f"Solved Example — {topic}", "level": 6, "type": "example",
             "content": f"**Example: Understanding {topic}**\n\n"
                        f"**Scenario:** Consider a practical situation that demonstrates {topic}.\n\n"
                        f"**Analysis:**\n"
                        f"Step 1: Identify the key elements involved in {topic}.\n"
                        f"Step 2: Apply the scientific principle to analyze the situation.\n"
                        f"Step 3: Observe and record the expected outcomes.\n"
                        f"Step 4: Draw conclusions based on the observations.\n\n"
                        f"**Conclusion:** This example illustrates how {topic} works in practice, reinforcing the theoretical understanding."},
            {"title": f"Practice Questions — {topic}", "level": 7, "type": "exercise",
             "content": f"**Practice Questions on {topic}**\n\n"
                        f"**Short Answer Questions:**\n"
                        f"1. Define {topic} and explain its significance.\n"
                        f"2. List the key factors that affect {topic}.\n\n"
                        f"**Long Answer Questions:**\n"
                        f"3. Describe in detail the process of {topic} with the help of a diagram/labelled sketch.\n"
                        f"4. Explain the practical applications of {topic} in everyday life.\n\n"
                        f"**Numerical/Problem-based:**\n"
                        f"5. Solve the numerical problem related to {topic} showing all steps.\n\n"
                        f"**NCERT Reference:** Chapter {ch_num}, {chapter}."},
        ]

    def _gen_english(self, topic, chapter, ch_num, subject, _ch):
        author = _ch.get("author", "the author")
        return [
            {"title": f"Summary of {topic}", "level": 4, "type": "text",
             "content": f"**'{topic}' — Summary**\n\n"
                        f"This chapter presents '{topic}' written by {author}. "
                        f"The piece explores important themes and ideas that are relevant to the Class X curriculum. "
                        f"Students should focus on understanding the central message, character development, and literary devices used by the author."},
            {"title": f"Themes and Analysis — {topic}", "level": 5, "type": "text",
             "content": f"**Themes and Analysis of '{topic}':**\n\n"
                        f"**Main Themes:**\n"
                        f"1. The central theme revolves around human experiences and emotions\n"
                        f"2. The author uses literary devices to convey deeper meanings\n"
                        f"3. The story/chapter reflects broader social and cultural contexts\n\n"
                        f"**Character Analysis:**\n"
                        f"• The main characters are well-developed and drive the narrative\n"
                        f"• Their interactions reveal important aspects of the theme\n"
                        f"• The author's characterisation techniques enhance the story\n\n"
                        f"**Literary Devices:**\n"
                        f"• Imagery, symbolism, and figurative language enrich the text\n"
                        f"• The narrative style reflects the author's unique voice"},
            {"title": f"Important Passages — {topic}", "level": 5, "type": "text",
             "content": f"**Important Passages and Their Meanings**\n\n"
                        f"Passages from '{topic}' that are significant for understanding the text:\n\n"
                        f"1. The opening passage sets the tone and introduces the central conflict.\n"
                        f"2. Key dialogues reveal character motivations and thematic concerns.\n"
                        f"3. The climax presents the turning point of the narrative.\n"
                        f"4. The conclusion delivers the author's message or moral.\n\n"
                        f"**Study Tips:**\n"
                        f"• Read each passage carefully and paraphrase in your own words\n"
                        f"• Note the literary devices used\n"
                        f"• Connect passages to the overall theme"},
            {"title": f"Questions and Answers — {topic}", "level": 7, "type": "exercise",
             "content": f"**Questions on '{topic}'**\n\n"
                        f"**Short Answer Questions:**\n"
                        f"1. What is the central theme of '{topic}'?\n"
                        f"2. Describe the main character's journey in the chapter.\n"
                        f"3. Explain the significance of the title.\n\n"
                        f"**Long Answer Questions:**\n"
                        f"4. Discuss the literary devices used by {author} in '{topic}' and their effectiveness.\n"
                        f"5. How does '{topic}' reflect the social context of its time?\n\n"
                        f"**Value-based Questions:**\n"
                        f"6. What moral lessons can we learn from '{topic}'?\n"
                        f"7. How does the chapter inspire readers to think differently?"},
        ]

    def _gen_social(self, topic, chapter, ch_num, subject, _ch):
        return [
            {"title": f"Understanding {topic}", "level": 4, "type": "text",
             "content": f"{topic} is a key concept in {chapter}. "
                        f"This topic helps students understand the social, political, and economic dimensions of the world around them. "
                        f"The study of {topic} enables learners to develop a critical perspective on historical and contemporary issues."},
            {"title": f"Key Concepts of {topic}", "level": 5, "type": "text",
             "content": f"**Key Concepts of {topic}:**\n\n"
                        f"1. **Definition and Scope**: {topic} refers to the study of this important area in social sciences.\n"
                        f"2. **Historical Context**: Understanding the background and evolution of {topic}.\n"
                        f"3. **Contemporary Relevance**: How {topic} remains relevant in today's world.\n"
                        f"4. **Key Thinkers/Events**: Important figures, events, or milestones associated with {topic}.\n"
                        f"5. **Critical Analysis**: Developing a balanced and analytical perspective on {topic}."},
            {"title": f"Detailed Study — {topic}", "level": 5, "type": "text",
             "content": f"**Detailed Notes on {topic}:**\n\n"
                        f"This topic covers several important aspects that students need to understand for their examinations.\n\n"
                        f"**Important Points:**\n"
                        f"• Focus on understanding causes and effects\n"
                        f"• Learn key dates, events, and terminology\n"
                        f"• Understand different perspectives and interpretations\n"
                        f"• Connect the topic to contemporary issues\n\n"
                        f"**Map Work / Diagrams (if applicable):**\n"
                        f"• Practice locating important places/regions\n"
                        f"• Understand flowcharts and diagrams related to {topic}"},
            {"title": f"Exam-oriented Questions — {topic}", "level": 7, "type": "exercise",
             "content": f"**Exam Questions on {topic}**\n\n"
                        f"**Very Short Answer (1 mark):**\n"
                        f"1. What is {topic}?\n"
                        f"2. Name the key concept associated with {topic}.\n\n"
                        f"**Short Answer (3 marks):**\n"
                        f"3. Explain the significance of {topic} in the context of {chapter}.\n"
                        f"4. Describe the main features of {topic}.\n\n"
                        f"**Long Answer (5 marks):**\n"
                        f"5. Analyze the impact of {topic} on society. Provide examples.\n"
                        f"6. Discuss the challenges and opportunities related to {topic}.\n\n"
                        f"**Map/Diagram Question:**\n"
                        f"7. Mark/identify the key locations related to {topic}."},
        ]

    def _gen_hindi(self, topic, chapter, ch_num, subject, _ch):
        return [
            {"title": f"{topic} — परिचय", "level": 4, "type": "text",
             "content": f"**{topic}** {chapter} का एक महत्वपूर्ण भाग है। "
                        f"यह विषय छात्रों को हिंदी साहित्य की समृद्ध परंपरा से परिचित कराता है। "
                        f"इस पाठ के माध्यम से छात्र भाषा, भाव और अभिव्यक्ति के विभिन्न आयामों को समझ सकते हैं।"},
            {"title": f"{topic} — सारांश", "level": 5, "type": "text",
             "content": f"**{topic} — मुख्य बिंदु:**\n\n"
                        f"इस पाठ में निम्नलिखित मुख्य बातों पर ध्यान देना चाहिए:\n"
                        f"• पाठ का मुख्य भाव और संदेश\n"
                        f"• प्रमुख पात्र और उनकी भूमिका\n"
                        f"• भाषा शैली और साहित्यिक विशेषताएँ\n"
                        f"• पाठ से जुड़े प्रमुख प्रश्न\n\n"
                        f"**महत्वपूर्ण शब्द:** पाठ में आए कठिन शब्दों के अर्थ समझें और उनका वाक्यों में प्रयोग करें।"},
            {"title": f"{topic} — अभ्यास प्रश्न", "level": 7, "type": "exercise",
             "content": f"**{topic} — अभ्यास प्रश्न**\n\n"
                        f"**अति लघु उत्तरीय प्रश्न:**\n"
                        f"1. इस पाठ का मुख्य विषय क्या है?\n"
                        f"2. लेखक/कवि का नाम बताइए।\n\n"
                        f"**लघु उत्तरीय प्रश्न:**\n"
                        f"3. पाठ का सारांश अपने शब्दों में लिखिए।\n"
                        f"4. पाठ में प्रयुक्त प्रमुख साहित्यिक उपकरणों की व्याख्या कीजिए।\n\n"
                        f"**दीर्घ उत्तरीय प्रश्न:**\n"
                        f"5. पाठ के मुख्य पात्रों की चर्चा कीजिए और उनके चरित्र की विशेषताएँ बताइए।\n"
                        f"6. इस पाठ का हमारे जीवन में क्या महत्व है?"},
        ]

    def _gen_sanskrit(self, topic, chapter, ch_num, subject, _ch):
        return [
            {"title": f"{topic} — परिचयः", "level": 4, "type": "text",
             "content": f"**{topic}** इति {chapter} इत्यस्मिन् पाठे विद्यमानः महत्त्वपूर्णः विषयः। "
                        f"अस्मिन् पाठे छात्राः संस्कृतभाषायाः सौन्दर्यं साहित्यिकगुणान् च ज्ञातुं शक्नुवन्ति।"},
            {"title": f"{topic} — सारांशः", "level": 5, "type": "text",
             "content": f"**{topic} — मुख्यबिन्दवः:**\n\n"
                        f"अस्य पाठस्य मुख्यांशाः:\n"
                        f"• पाठस्य मुख्यसन्देशः\n"
                        f"• प्रमुखपात्राणि तेषां भूमिका च\n"
                        f"• भाषाशैली साहित्यिकविशेषताः\n"
                        f"• कठिनशब्दानाम् अर्थाः\n\n"
                        f"**अभ्यासार्थम्:** "
                        f"पाठं बहुवारं पठेत्, श्लोकान् कण्ठस्थीकुर्यात्, प्रश्नोत्तराणि लिखेत्।"},
            {"title": f"{topic} — अभ्यासप्रश्नाः", "level": 7, "type": "exercise",
             "content": f"**{topic} — अभ्यासप्रश्नाः**\n\n"
                        f"**अतिलघूत्तराः प्रश्नाः:**\n"
                        f"1. अस्य पाठस्य मुख्यविषयः कः?\n"
                        f"2. लेखकस्य नाम किम्?\n\n"
                        f"**लघूत्तराः प्रश्नाः:**\n"
                        f"3. पाठस्य सारांशं संस्कृतेन लिखत।\n"
                        f"4. कठिनशब्दानाम् अर्थान् लिखत।\n\n"
                        f"**दीर्घोत्तराः प्रश्नाः:**\n"
                        f"5. पाठस्य मुख्यसन्देशं स्वशब्देषु व्याख्यात।\n"
                        f"6. अस्मिन् पाठे कति श्लोकाः सन्ति? तेषां भावार्थं लिखत।"},
        ]

    def _gen_general(self, topic, chapter, ch_num, subject, _ch):
        return [
            {"title": f"Introduction to {topic}", "level": 4, "type": "text",
             "content": f"{topic} is an important topic in {chapter} (Chapter {ch_num}). "
                        f"This topic covers essential concepts that students need to understand for their Class X curriculum. "
                        f"Focus on grasping the core ideas and their practical applications."},
            {"title": f"Key Points — {topic}", "level": 5, "type": "text",
             "content": f"**Key Points about {topic}:**\n\n"
                        f"1. Understand the fundamental concepts and definitions\n"
                        f"2. Learn the important facts, dates, and terminology\n"
                        f"3. Analyze the relationships between different aspects of the topic\n"
                        f"4. Practice applying the knowledge to solve problems\n"
                        f"5. Review and revise regularly for better retention"},
            {"title": f"Study Questions — {topic}", "level": 7, "type": "exercise",
             "content": f"**Questions for {topic}:**\n\n"
                        f"1. Define {topic} and explain its importance.\n"
                        f"2. List the main features/elements of {topic}.\n"
                        f"3. How does {topic} relate to other topics in {chapter}?\n"
                        f"4. Provide examples to illustrate {topic}.\n"
                        f"5. Write short notes on the key aspects of {topic}."},
        ]

    def _generate_poem_content(self, topic_id, chapter_id, poem, subject_id):
        poet = poem.get("poet", "Unknown")
        title = poem["title"]
        chunks = [
            {"title": f"Summary of '{title}'", "level": 4, "type": "text",
             "content": f"**'{title}' by {poet} — Summary**\n\n"
                        f"This poem, written by {poet}, is a part of the Class X curriculum. "
                        f"The poem explores themes that resonate with young readers and offers valuable insights "
                        f"into human emotions, nature, or society."},
            {"title": f"Analysis of '{title}'", "level": 5, "type": "text",
             "content": f"**Poetic Analysis of '{title}':**\n\n"
                        f"**Theme:** The central theme of the poem revolves around {poet}'s perspective on the subject.\n"
                        f"**Imagery:** The poet uses vivid imagery to create a lasting impression.\n"
                        f"**Rhyme Scheme:** The poem follows a specific rhyme pattern that enhances its musical quality.\n"
                        f"**Figures of Speech:** Identify and analyze the literary devices used.\n\n"
                        f"**Key Lines:** Focus on the most significant lines that capture the poem's essence."},
            {"title": f"Questions on '{title}'", "level": 7, "type": "exercise",
             "content": f"**Questions on '{title}':**\n\n"
                        f"1. What is the central theme of the poem?\n"
                        f"2. Explain the imagery used by the poet.\n"
                        f"3. What is the rhyme scheme of the poem?\n"
                        f"4. Identify and explain two figures of speech used in the poem.\n"
                        f"5. How does the poet convey the message through the poem?\n"
                        f"6. Write a short paragraph explaining your interpretation of the poem."},
        ]
        for i, chunk in enumerate(chunks):
            cid = make_id(topic_id, str(i))
            insert_chunk(cid, topic_id, chapter_id, None, chunk["level"],
                         chunk["title"], chunk["content"], chunk["type"], i)

    def import_state_board(self, board_id, board_name, subjects, description=""):
        insert_board(board_id, board_name, description)
        conn = get_conn()
        for subject in subjects:
            sid = f"{board_id}_{subject['id']}"
            subject_type = self._detect_subject_type(sid, subject)
            insert_subject(sid, board_id, subject["name"], subject.get("code", ""), subject.get("description", ""))
            for ch in subject.get("chapters", []):
                cid = make_id(sid, str(ch["num"]))
                insert_chapter(cid, None, sid, board_id, ch["num"], ch["title"])
                if ch.get("topics"):
                    for i, topic_name in enumerate(ch["topics"]):
                        tid = make_id(cid, topic_name)
                        insert_topic(tid, cid, i + 1, topic_name)
                        self._generate_topic_content(tid, cid, topic_name, ch["title"],
                                                     ch["num"], sid, subject_type, ch)
        conn.commit()
        conn.execute("INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild')")
        conn.commit()
