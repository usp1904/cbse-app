from database import get_conn

QUESTION_BANK = {
    "cbse": {
        "mathematics": [
            {"id": "cbse-math-001", "year": 2024, "board": "cbse", "subject": "mathematics", "chapter": "Real Numbers", "topic": "Euclid's Division Algorithm", "type": "mcq", "marks": 1, "question_text": "Using Euclid's division algorithm, the HCF of 405 and 2520 is:", "options": ["45", "15", "9", "135"], "correct_answer": "45", "explanation": "2520 = 405\u00d76 + 90, 405 = 90\u00d74 + 45, 90 = 45\u00d72 + 0. HCF = 45.", "difficulty": "easy"},
            {"id": "cbse-math-002", "year": 2023, "board": "cbse", "subject": "mathematics", "chapter": "Real Numbers", "topic": "Fundamental Theorem of Arithmetic", "type": "vsa", "marks": 1, "question_text": "Express 156 as a product of its prime factors.", "options": None, "correct_answer": "2\u00b2 \u00d7 3 \u00d7 13", "explanation": "156 = 2\u00d778 = 2\u00d72\u00d739 = 2\u00b2 \u00d7 3 \u00d7 13.", "difficulty": "easy"},
            {"id": "cbse-math-003", "year": 2022, "board": "cbse", "subject": "mathematics", "chapter": "Real Numbers", "topic": "Irrational Numbers", "type": "sa", "marks": 2, "question_text": "Prove that \u221a3 is irrational.", "options": None, "correct_answer": "Assume \u221a3 = p/q in lowest terms. Then 3q\u00b2 = p\u00b2, so 3 divides p, then 3 divides q, contradiction.", "explanation": "By contradiction: let \u221a3 = p/q (coprime). Squaring: 3q\u00b2 = p\u00b2. So 3|p\u00b2 \u21d2 3|p. Let p=3k. Then 3q\u00b2 = 9k\u00b2 \u21d2 q\u00b2 = 3k\u00b2 \u21d2 3|q. Contradiction since p,q coprime.", "difficulty": "medium"},
            {"id": "cbse-math-004", "year": 2023, "board": "cbse", "subject": "mathematics", "chapter": "Real Numbers", "topic": "Decimal Expansions", "type": "vsa", "marks": 1, "question_text": "Without division, state whether 17/8 will have a terminating or non-terminating decimal expansion.", "options": None, "correct_answer": "Terminating", "explanation": "8 = 2\u00b3, which is of the form 2\u207f5\u1d50, so it terminates.", "difficulty": "easy"},
            {"id": "cbse-math-005", "year": 2024, "board": "cbse", "subject": "mathematics", "chapter": "Real Numbers", "topic": "LCM and HCF", "type": "sa", "marks": 2, "question_text": "If LCM(336, 54) = 3024, find HCF(336, 54).", "options": None, "correct_answer": "6", "explanation": "Product = LCM \u00d7 HCF. 336\u00d754 = 18144. HCF = 18144/3024 = 6.", "difficulty": "easy"},

            {"id": "cbse-math-006", "year": 2023, "board": "cbse", "subject": "mathematics", "chapter": "Polynomials", "topic": "Zeroes of Polynomial", "type": "mcq", "marks": 1, "question_text": "The zeroes of the polynomial x\u00b2 - 3 are:", "options": ["\u00b1\u221a3", "\u00b13", "3, -3", "None"], "correct_answer": "\u00b1\u221a3", "explanation": "x\u00b2 - 3 = 0 \u21d2 x = \u00b1\u221a3", "difficulty": "easy"},
            {"id": "cbse-math-007", "year": 2022, "board": "cbse", "subject": "mathematics", "chapter": "Polynomials", "topic": "Relationship between Zeroes and Coefficients", "type": "sa", "marks": 2, "question_text": "Find a quadratic polynomial whose sum and product of zeroes are -3 and 2 respectively.", "options": None, "correct_answer": "x\u00b2 + 3x + 2", "explanation": "Required polynomial = x\u00b2 - (sum)x + product = x\u00b2 - (-3)x + 2 = x\u00b2 + 3x + 2.", "difficulty": "easy"},
            {"id": "cbse-math-008", "year": 2024, "board": "cbse", "subject": "mathematics", "chapter": "Polynomials", "topic": "Division Algorithm", "type": "sa", "marks": 3, "question_text": "Divide 2x\u00b2 + 3x + 1 by x + 2 and find the quotient and remainder.", "options": None, "correct_answer": "Quotient = 2x - 1, Remainder = 3", "explanation": "Using polynomial division: (2x\u00b2 + 3x + 1) \u00f7 (x + 2). 2x\u00b2/x = 2x, (2x)(x+2) = 2x\u00b2+4x, subtract: -x+1. -x/x = -1, (-1)(x+2) = -x-2, subtract: 3. So quotient = 2x - 1, remainder = 3.", "difficulty": "medium"},
            {"id": "cbse-math-009", "year": 2023, "board": "cbse", "subject": "mathematics", "chapter": "Polynomials", "topic": "Geometrical Meaning of Zeroes", "type": "mcq", "marks": 1, "question_text": "The graph of a quadratic polynomial ax\u00b2 + bx + c (a \u2260 0) is a:", "options": ["Straight line", "Parabola", "Circle", "Hyperbola"], "correct_answer": "Parabola", "explanation": "The graph of any quadratic polynomial is a parabola. If a > 0, it opens upward; if a < 0, it opens downward.", "difficulty": "easy"},

            {"id": "cbse-math-010", "year": 2024, "board": "cbse", "subject": "mathematics", "chapter": "Quadratic Equations", "topic": "Solution by Factorisation", "type": "sa", "marks": 2, "question_text": "Solve: x\u00b2 - 5x + 6 = 0.", "options": None, "correct_answer": "x = 2, 3", "explanation": "x\u00b2 - 5x + 6 = (x - 2)(x - 3) = 0 \u21d2 x = 2 or x = 3.", "difficulty": "easy"},
            {"id": "cbse-math-011", "year": 2023, "board": "cbse", "subject": "mathematics", "chapter": "Quadratic Equations", "topic": "Nature of Roots", "type": "mcq", "marks": 1, "question_text": "The discriminant of 2x\u00b2 - 4x + 3 = 0 is:", "options": ["8", "-8", "16", "4"], "correct_answer": "-8", "explanation": "D = b\u00b2 - 4ac = (-4)\u00b2 - 4(2)(3) = 16 - 24 = -8.", "difficulty": "easy"},
            {"id": "cbse-math-012", "year": 2022, "board": "cbse", "subject": "mathematics", "chapter": "Quadratic Equations", "topic": "Quadratic Formula", "type": "sa", "marks": 3, "question_text": "Find the roots of 2x\u00b2 + x - 4 = 0 using the quadratic formula.", "options": None, "correct_answer": "x = (-1 \u00b1 \u221a33)/4", "explanation": "Using x = [-b \u00b1 \u221a(b\u00b2 - 4ac)]/2a. Here a=2, b=1, c=-4. D = 1 + 32 = 33. Roots = (-1 \u00b1 \u221a33)/4.", "difficulty": "medium"},
            {"id": "cbse-math-013", "year": 2024, "board": "cbse", "subject": "mathematics", "chapter": "Quadratic Equations", "topic": "Word Problems", "type": "la", "marks": 4, "question_text": "A train travels 360 km at a uniform speed. If the speed had been 5 km/h more, it would have taken 1 hour less. Find the speed of the train.", "options": None, "correct_answer": "40 km/h", "explanation": "Let speed = x km/h. Time = 360/x. New speed = x+5, time = 360/(x+5). Given 360/x - 360/(x+5) = 1. \u21d2 360(x+5-x) = x(x+5) \u21d2 1800 = x\u00b2 + 5x \u21d2 x\u00b2 + 5x - 1800 = 0 \u21d2 (x+45)(x-40) = 0 \u21d2 x = 40 (since speed > 0).", "difficulty": "hard"},

            {"id": "cbse-math-014", "year": 2024, "board": "cbse", "subject": "mathematics", "chapter": "Introduction to Trigonometry", "topic": "Trigonometric Ratios", "type": "mcq", "marks": 1, "question_text": "The value of sin 60\u00b0 \u00d7 cos 30\u00b0 is:", "options": ["1/2", "3/4", "1/4", "1"], "correct_answer": "3/4", "explanation": "sin 60\u00b0 = \u221a3/2, cos 30\u00b0 = \u221a3/2. Product = (\u221a3/2)(\u221a3/2) = 3/4.", "difficulty": "easy"},
            {"id": "cbse-math-015", "year": 2023, "board": "cbse", "subject": "mathematics", "chapter": "Introduction to Trigonometry", "topic": "Trigonometric Identities", "type": "vsa", "marks": 1, "question_text": "Simplify: sin\u00b2A + cos\u00b2A.", "options": None, "correct_answer": "1", "explanation": "By the Pythagorean trigonometric identity, sin\u00b2A + cos\u00b2A = 1 for any angle A.", "difficulty": "easy"},
            {"id": "cbse-math-016", "year": 2022, "board": "cbse", "subject": "mathematics", "chapter": "Introduction to Trigonometry", "topic": "Trigonometric Ratios of Complementary Angles", "type": "sa", "marks": 2, "question_text": "If sin 3A = cos(A - 26\u00b0), where 3A is acute, find the value of A.", "options": None, "correct_answer": "29\u00b0", "explanation": "sin 3A = cos(A - 26\u00b0) \u21d2 sin 3A = sin(90\u00b0 - (A - 26\u00b0)) \u21d2 3A = 90\u00b0 - A + 26\u00b0 \u21d2 4A = 116\u00b0 \u21d2 A = 29\u00b0.", "difficulty": "medium"},
            {"id": "cbse-math-017", "year": 2024, "board": "cbse", "subject": "mathematics", "chapter": "Introduction to Trigonometry", "topic": "Trigonometric Identities", "type": "sa", "marks": 3, "question_text": "Prove that (1 + tan\u00b2A)/(1 + cot\u00b2A) = tan\u00b2A.", "options": None, "correct_answer": "LHS = sec\u00b2A/cosec\u00b2A = (1/cos\u00b2A)/(1/sin\u00b2A) = sin\u00b2A/cos\u00b2A = tan\u00b2A = RHS", "explanation": "1 + tan\u00b2A = sec\u00b2A, 1 + cot\u00b2A = cosec\u00b2A. LHS = sec\u00b2A/cosec\u00b2A = (1/cos\u00b2A)\u00d7(sin\u00b2A/1) = sin\u00b2A/cos\u00b2A = tan\u00b2A.", "difficulty": "medium"},

            {"id": "cbse-math-018", "year": 2023, "board": "cbse", "subject": "mathematics", "chapter": "Statistics", "topic": "Mean of Grouped Data", "type": "vsa", "marks": 1, "question_text": "In the formula x\u0304 = a + (\u2211f\u1d62d\u1d62)/(\u2211f\u1d62), what does 'a' represent?", "options": None, "correct_answer": "Assumed mean", "explanation": "'a' is the assumed mean used in the step-deviation method for calculating the mean of grouped data.", "difficulty": "easy"},
            {"id": "cbse-math-019", "year": 2024, "board": "cbse", "subject": "mathematics", "chapter": "Statistics", "topic": "Mode of Grouped Data", "type": "sa", "marks": 2, "question_text": "Find the mode of the following data: Class 0-10 (f=5), 10-20 (f=8), 20-30 (f=12), 30-40 (f=7), 40-50 (f=3).", "options": None, "correct_answer": "24.44", "explanation": "Modal class = 20-30 (highest f=12). Mode = L + [(f1-f0)/(2f1-f0-f2)]\u00d7h = 20 + [(12-8)/(24-8-7)]\u00d710 = 20 + (4/9)\u00d710 = 20 + 4.44 = 24.44.", "difficulty": "medium"},
            {"id": "cbse-math-020", "year": 2022, "board": "cbse", "subject": "mathematics", "chapter": "Statistics", "topic": "Median of Grouped Data", "type": "sa", "marks": 3, "question_text": "Find the median of: CI 0-10 (f=5), 10-20 (f=8), 20-30 (f=12), 30-40 (f=7), 40-50 (f=3).", "options": None, "correct_answer": "24.17", "explanation": "N=35. N/2=17.5. Median class = 20-30 (cf=13, f=12). Median = L + [(N/2-cf)/f]\u00d7h = 20 + [(17.5-13)/12]\u00d710 = 20 + (4.5/12)\u00d710 = 20 + 3.75 = 23.75.", "difficulty": "medium"},
            {"id": "cbse-math-021", "year": 2023, "board": "cbse", "subject": "mathematics", "chapter": "Statistics", "topic": "Ogive", "type": "la", "marks": 4, "question_text": "Draw a less than ogive for the data: Marks 0-10 (5), 10-20 (8), 20-30 (12), 30-40 (7), 40-50 (3). Find the median.", "options": None, "correct_answer": "23.75", "explanation": "Less than cumulative frequencies: <10:5, <20:13, <30:25, <40:32, <50:35. Plot points (10,5), (20,13), (30,25), (40,32), (50,35). At y=N/2=17.5, draw horizontal to curve, then vertical to x-axis to get median \u2248 23.75.", "difficulty": "medium"},

            {"id": "cbse-math-022", "year": 2024, "board": "cbse", "subject": "mathematics", "chapter": "Arithmetic Progressions", "topic": "nth Term of AP", "type": "mcq", "marks": 1, "question_text": "The nth term of the AP 5, 9, 13, 17, ... is:", "options": ["4n+1", "4n-1", "n+4", "5n"], "correct_answer": "4n+1", "explanation": "a=5, d=4. a\u2099 = a + (n-1)d = 5 + (n-1)4 = 5 + 4n - 4 = 4n + 1.", "difficulty": "easy"},
            {"id": "cbse-math-023", "year": 2023, "board": "cbse", "subject": "mathematics", "chapter": "Arithmetic Progressions", "topic": "Sum of n Terms", "type": "sa", "marks": 2, "question_text": "Find the sum of the first 20 terms of the AP: 2, 5, 8, 11, ...", "options": None, "correct_answer": "610", "explanation": "a=2, d=3, n=20. S\u2099 = n/2[2a + (n-1)d] = 20/2[4 + 19\u00d73] = 10[4 + 57] = 10\u00d761 = 610.", "difficulty": "easy"},
        ],
        "science": [
            {"id": "cbse-sci-001", "year": 2024, "board": "cbse", "subject": "science", "chapter": "Chemical Reactions and Equations", "topic": "Types of Reactions", "type": "mcq", "marks": 1, "question_text": "The reaction 2Mg + O\u2082 \u2192 2MgO is an example of:", "options": ["Combination", "Decomposition", "Displacement", "Double displacement"], "correct_answer": "Combination", "explanation": "Two reactants combine to form a single product, making it a combination reaction.", "difficulty": "easy"},
            {"id": "cbse-sci-002", "year": 2023, "board": "cbse", "subject": "science", "chapter": "Chemical Reactions and Equations", "topic": "Balancing Equations", "type": "vsa", "marks": 1, "question_text": "Balance: Fe + H\u2082O \u2192 Fe\u2083O\u2084 + H\u2082.", "options": None, "correct_answer": "3Fe + 4H\u2082O \u2192 Fe\u2083O\u2084 + 4H\u2082", "explanation": "Three Fe atoms on RHS, so 3Fe. Four O atoms on RHS, so 4H\u2082O. Then 8 H on LHS, so 4H\u2082.", "difficulty": "medium"},
            {"id": "cbse-sci-003", "year": 2022, "board": "cbse", "subject": "science", "chapter": "Chemical Reactions and Equations", "topic": "Oxidation and Reduction", "type": "vsa", "marks": 1, "question_text": "In ZnO + C \u2192 Zn + CO, which substance is reduced?", "options": None, "correct_answer": "ZnO (zinc oxide)", "explanation": "ZnO loses oxygen (is reduced) to form Zn. C gains oxygen (is oxidized) to form CO.", "difficulty": "easy"},
            {"id": "cbse-sci-004", "year": 2024, "board": "cbse", "subject": "science", "chapter": "Chemical Reactions and Equations", "topic": "Corrosion", "type": "sa", "marks": 2, "question_text": "What is rust? Write the chemical equation for rusting of iron.", "options": None, "correct_answer": "Rust is hydrated iron(III) oxide, Fe\u2082O\u2083\u00b7xH\u2082O. 4Fe + 3O\u2082 + 2xH\u2082O \u2192 2Fe\u2082O\u2083\u00b7xH\u2082O", "explanation": "Iron reacts with oxygen and water to form hydrated iron(III) oxide, commonly known as rust. The process requires both oxygen and water.", "difficulty": "medium"},

            {"id": "cbse-sci-005", "year": 2024, "board": "cbse", "subject": "science", "chapter": "Acids, Bases and Salts", "topic": "pH Scale", "type": "mcq", "marks": 1, "question_text": "A solution turns blue litmus red. Its pH is likely:", "options": ["2", "7", "10", "13"], "correct_answer": "2", "explanation": "Acids turn blue litmus red and have pH < 7. pH 2 indicates a strong acid.", "difficulty": "easy"},
            {"id": "cbse-sci-006", "year": 2023, "board": "cbse", "subject": "science", "chapter": "Acids, Bases and Salts", "topic": "Neutralisation", "type": "sa", "marks": 2, "question_text": "Write the reaction between HCl and NaOH. Name the salt formed.", "options": None, "correct_answer": "HCl + NaOH \u2192 NaCl + H\u2082O. Sodium chloride (NaCl) is formed.", "explanation": "This is a neutralisation reaction between a strong acid (HCl) and strong base (NaOH) producing salt and water. The salt formed is sodium chloride (common salt).", "difficulty": "easy"},
            {"id": "cbse-sci-007", "year": 2022, "board": "cbse", "subject": "science", "chapter": "Acids, Bases and Salts", "topic": "Common Salts", "type": "vsa", "marks": 1, "question_text": "What is the chemical name and formula of washing soda?", "options": None, "correct_answer": "Sodium carbonate decahydrate, Na\u2082CO\u2083\u00b710H\u2082O", "explanation": "Washing soda is sodium carbonate decahydrate (Na\u2082CO\u2083\u00b710H\u2082O), obtained by heating baking soda.", "difficulty": "easy"},
            {"id": "cbse-sci-008", "year": 2024, "board": "cbse", "subject": "science", "chapter": "Acids, Bases and Salts", "topic": "Importance of pH", "type": "sa", "marks": 3, "question_text": "Explain the importance of pH in everyday life with two examples.", "options": None, "correct_answer": "See explanation.", "explanation": "1) pH of soil: Plants grow best at specific pH ranges. 2) pH in digestive system: HCl in stomach helps digestion but excess causes acidity. 3) pH of rain water: pH < 5.6 indicates acid rain. 4) Tooth decay: Bacteria produce acids (pH < 5.5) that demineralise tooth enamel.", "difficulty": "medium"},

            {"id": "cbse-sci-009", "year": 2024, "board": "cbse", "subject": "science", "chapter": "Life Processes", "topic": "Nutrition", "type": "mcq", "marks": 1, "question_text": "The enzyme pepsin acts in:", "options": ["Mouth", "Stomach", "Small intestine", "Large intestine"], "correct_answer": "Stomach", "explanation": "Pepsin is secreted in the stomach and breaks down proteins into peptones in acidic medium (pH 1.5-2.5).", "difficulty": "easy"},
            {"id": "cbse-sci-010", "year": 2023, "board": "cbse", "subject": "science", "chapter": "Life Processes", "topic": "Respiration", "type": "vsa", "marks": 1, "question_text": "What is the site of aerobic respiration in a cell?", "options": None, "correct_answer": "Mitochondria", "explanation": "Mitochondria are the powerhouse of the cell where aerobic respiration occurs, producing ATP.", "difficulty": "easy"},
            {"id": "cbse-sci-011", "year": 2022, "board": "cbse", "subject": "science", "chapter": "Life Processes", "topic": "Transportation", "type": "sa", "marks": 2, "question_text": "What is the function of the left ventricle in the human heart?", "options": None, "correct_answer": "It pumps oxygenated blood to all parts of the body through the aorta.", "explanation": "The left ventricle receives oxygenated blood from the left atrium and pumps it into the aorta, which distributes it to the entire body. It has the thickest walls because it needs to pump blood the farthest.", "difficulty": "medium"},
            {"id": "cbse-sci-012", "year": 2024, "board": "cbse", "subject": "science", "chapter": "Life Processes", "topic": "Excretion", "type": "sa", "marks": 3, "question_text": "Describe the structure and function of the nephron.", "options": None, "correct_answer": "See explanation.", "explanation": "Nephron is the functional unit of the kidney. Structure: Bowman's capsule, glomerulus (filtration), PCT (reabsorption), loop of Henle (water reabsorption), DCT and collecting duct. Function: filters blood to remove nitrogenous wastes (urea), reabsorbs water, glucose, amino acids, and maintains water-electrolyte balance.", "difficulty": "medium"},

            {"id": "cbse-sci-013", "year": 2024, "board": "cbse", "subject": "science", "chapter": "Electricity", "topic": "Ohm's Law", "type": "mcq", "marks": 1, "question_text": "Ohm's law states the relationship between:", "options": ["V and I", "V and R", "I and R", "P and I"], "correct_answer": "V and I", "explanation": "Ohm's law states that the potential difference (V) across a conductor is directly proportional to the current (I) flowing through it, at constant temperature: V \u221d I or V = IR.", "difficulty": "easy"},
            {"id": "cbse-sci-014", "year": 2023, "board": "cbse", "subject": "science", "chapter": "Electricity", "topic": "Resistance", "type": "vsa", "marks": 1, "question_text": "State the SI unit of resistance.", "options": None, "correct_answer": "Ohm (\u03a9)", "explanation": "Resistance is measured in ohms (\u03a9). 1 \u03a9 = 1 V/A.", "difficulty": "easy"},
            {"id": "cbse-sci-015", "year": 2022, "board": "cbse", "subject": "science", "chapter": "Electricity", "topic": "Resistors in Series and Parallel", "type": "sa", "marks": 3, "question_text": "Three resistors of 2\u03a9, 3\u03a9 and 5\u03a9 are connected in parallel. Find the total resistance.", "options": None, "correct_answer": "0.97 \u03a9", "explanation": "For parallel: 1/R = 1/2 + 1/3 + 1/5 = 15/30 + 10/30 + 6/30 = 31/30. R = 30/31 \u2248 0.97 \u03a9.", "difficulty": "medium"},
            {"id": "cbse-sci-016", "year": 2024, "board": "cbse", "subject": "science", "chapter": "Electricity", "topic": "Heating Effect", "type": "sa", "marks": 2, "question_text": "A current of 2 A flows through a resistor of 10 \u03a9 for 5 minutes. Find the heat produced.", "options": None, "correct_answer": "12000 J", "explanation": "H = I\u00b2Rt = 2\u00b2 \u00d7 10 \u00d7 (5\u00d760) = 4 \u00d7 10 \u00d7 300 = 12000 J.", "difficulty": "medium"},

            {"id": "cbse-sci-017", "year": 2023, "board": "cbse", "subject": "science", "chapter": "Light \u2013 Reflection and Refraction", "topic": "Reflection of Light", "type": "mcq", "marks": 1, "question_text": "The angle of incidence equals the angle of reflection. This is the law of:", "options": ["Reflection", "Refraction", "Dispersion", "Diffraction"], "correct_answer": "Reflection", "explanation": "The first law of reflection states that the angle of incidence equals the angle of reflection.", "difficulty": "easy"},
            {"id": "cbse-sci-018", "year": 2024, "board": "cbse", "subject": "science", "chapter": "Light \u2013 Reflection and Refraction", "topic": "Spherical Mirrors", "type": "vsa", "marks": 1, "question_text": "What is the focal length of a spherical mirror whose radius of curvature is 30 cm?", "options": None, "correct_answer": "15 cm", "explanation": "f = R/2 = 30/2 = 15 cm. For a concave mirror, f is positive; for convex, negative.", "difficulty": "easy"},
            {"id": "cbse-sci-019", "year": 2022, "board": "cbse", "subject": "science", "chapter": "Light \u2013 Reflection and Refraction", "topic": "Refractive Index", "type": "sa", "marks": 2, "question_text": "Light enters from air to water (refractive index = 4/3). Find the speed of light in water. (c = 3\u00d710\u2078 m/s)", "options": None, "correct_answer": "2.25\u00d710\u2078 m/s", "explanation": "n = c/v \u21d2 v = c/n = (3\u00d710\u2078)/(4/3) = (3\u00d710\u2078)\u00d7(3/4) = 2.25\u00d710\u2078 m/s.", "difficulty": "medium"},
            {"id": "cbse-sci-020", "year": 2023, "board": "cbse", "subject": "science", "chapter": "Light \u2013 Reflection and Refraction", "topic": "Lens Formula", "type": "la", "marks": 4, "question_text": "An object is placed at a distance of 15 cm from a convex lens of focal length 10 cm. Find the position, nature, and size of the image.", "options": None, "correct_answer": "Image at 30 cm, real and inverted, twice the size", "explanation": "Using lens formula: 1/v - 1/u = 1/f. u = -15 cm, f = +10 cm. 1/v = 1/f + 1/u = 1/10 + 1/(-15) = 3/30 - 2/30 = 1/30. v = +30 cm. m = v/u = 30/(-15) = -2. Image is real (v positive), inverted (m negative), and magnified 2\u00d7.", "difficulty": "hard"},
        ],
    },
    "ap": {
        "ap-mathematics": [
            {"id": "ap-math-001", "year": 2024, "board": "ap", "subject": "ap-mathematics", "chapter": "Real Numbers", "topic": "Euclid's Division Lemma", "type": "mcq", "marks": 1, "question_text": "The HCF of 84 and 144 using Euclid's algorithm is:", "options": ["12", "24", "6", "36"], "correct_answer": "12", "explanation": "144 = 84\u00d71 + 60, 84 = 60\u00d71 + 24, 60 = 24\u00d72 + 12, 24 = 12\u00d72 + 0. HCF = 12.", "difficulty": "easy"},
            {"id": "ap-math-002", "year": 2023, "board": "ap", "subject": "ap-mathematics", "chapter": "Real Numbers", "topic": "Fundamental Theorem of Arithmetic", "type": "vsa", "marks": 1, "question_text": "Express 500 as a product of its prime factors.", "options": None, "correct_answer": "2\u00b2 \u00d7 5\u00b3", "explanation": "500 = 5\u00d7100 = 5\u00d710\u00d710 = 5\u00d72\u00d75\u00d72\u00d75 = 2\u00b2 \u00d7 5\u00b3.", "difficulty": "easy"},
            {"id": "ap-math-003", "year": 2022, "board": "ap", "subject": "ap-mathematics", "chapter": "Real Numbers", "topic": "Irrational Numbers", "type": "sa", "marks": 2, "question_text": "Prove that 5 + \u221a2 is irrational.", "options": None, "correct_answer": "Assume 5+\u221a2 = p/q. Then \u221a2 = p/q - 5 = (p-5q)/q, rational. Contradiction since \u221a2 is irrational.", "explanation": "If 5+\u221a2 were rational = p/q, then \u221a2 = p/q - 5 which is rational. But \u221a2 is irrational. Hence 5+\u221a2 is irrational.", "difficulty": "medium"},
            {"id": "ap-math-004", "year": 2024, "board": "ap", "subject": "ap-mathematics", "chapter": "Real Numbers", "topic": "Decimal Expansions", "type": "vsa", "marks": 1, "question_text": "Is the decimal expansion of 23/50 terminating?", "options": None, "correct_answer": "Yes", "explanation": "50 = 2\u00d75\u00b2, which is of the form 2\u207f5\u1d50, so it terminates.", "difficulty": "easy"},

            {"id": "ap-math-005", "year": 2024, "board": "ap", "subject": "ap-mathematics", "chapter": "Polynomials", "topic": "Zeroes of Polynomial", "type": "mcq", "marks": 1, "question_text": "The graph of p(x) = x\u00b2 - 4x + 3 intersects the x-axis at:", "options": ["(1,0),(3,0)", "(0,1),(0,3)", "(-1,0),(-3,0)", "(0,-1),(0,-3)"], "correct_answer": "(1,0),(3,0)", "explanation": "x\u00b2 - 4x + 3 = (x-1)(x-3) = 0 \u21d2 x = 1, 3. So points are (1,0) and (3,0).", "difficulty": "easy"},
            {"id": "ap-math-006", "year": 2023, "board": "ap", "subject": "ap-mathematics", "chapter": "Polynomials", "topic": "Relationship between Zeroes and Coefficients", "type": "sa", "marks": 2, "question_text": "If \u03b1 and \u03b2 are zeroes of x\u00b2 - 7x + 12, find \u03b1 + \u03b2 and \u03b1\u03b2.", "options": None, "correct_answer": "\u03b1+\u03b2 = 7, \u03b1\u03b2 = 12", "explanation": "For ax\u00b2+bx+c, sum = -b/a = -(-7)/1 = 7, product = c/a = 12/1 = 12.", "difficulty": "easy"},
            {"id": "ap-math-007", "year": 2022, "board": "ap", "subject": "ap-mathematics", "chapter": "Polynomials", "topic": "Division Algorithm", "type": "sa", "marks": 3, "question_text": "Find all zeroes of 2x\u2074 - 3x\u00b3 - 5x\u00b2 + 9x - 3, given two of its zeroes are \u221a3 and -\u221a3.", "options": None, "correct_answer": "\u221a3, -\u221a3, 1, 1/2", "explanation": "(x-\u221a3)(x+\u221a3) = x\u00b2-3 divides the polynomial. Dividing: (2x\u2074-3x\u00b3-5x\u00b2+9x-3)/(x\u00b2-3) = 2x\u00b2-3x+1. Solving 2x\u00b2-3x+1=0: (2x-1)(x-1)=0 \u21d2 x=1, x=1/2.", "difficulty": "hard"},

            {"id": "ap-math-008", "year": 2024, "board": "ap", "subject": "ap-mathematics", "chapter": "Progressions", "topic": "Arithmetic Progressions", "type": "mcq", "marks": 1, "question_text": "The 10th term of the AP: 3, 7, 11, 15, ... is:", "options": ["39", "43", "35", "47"], "correct_answer": "39", "explanation": "a=3, d=4. a\u2081\u2080 = a + 9d = 3 + 36 = 39.", "difficulty": "easy"},
            {"id": "ap-math-009", "year": 2023, "board": "ap", "subject": "ap-mathematics", "chapter": "Progressions", "topic": "Sum of n Terms", "type": "sa", "marks": 2, "question_text": "Find the sum of first 15 terms of AP: 5, 9, 13, 17, ...", "options": None, "correct_answer": "495", "explanation": "a=5, d=4, n=15. S = n/2[2a+(n-1)d] = 15/2[10+56] = 15/2\u00d766 = 15\u00d733 = 495.", "difficulty": "easy"},
            {"id": "ap-math-010", "year": 2022, "board": "ap", "subject": "ap-mathematics", "chapter": "Progressions", "topic": "Geometric Progressions", "type": "vsa", "marks": 1, "question_text": "Find the common ratio of GP: 2, 6, 18, 54, ...", "options": None, "correct_answer": "3", "explanation": "Common ratio r = 6/2 = 18/6 = 54/18 = 3.", "difficulty": "easy"},
            {"id": "ap-math-011", "year": 2024, "board": "ap", "subject": "ap-mathematics", "chapter": "Progressions", "topic": "Word Problems in AP", "type": "sa", "marks": 3, "question_text": "How many terms of AP: 24, 21, 18, ... must be taken so that their sum is 78?", "options": None, "correct_answer": "4 or 13", "explanation": "a=24, d=-3, S=78. S = n/2[48+(n-1)(-3)] = n/2[51-3n] = 78. \u21d2 51n - 3n\u00b2 = 156 \u21d2 3n\u00b2 - 51n + 156 = 0 \u21d2 n\u00b2 - 17n + 52 = 0 \u21d2 (n-4)(n-13)=0 \u21d2 n=4 or 13.", "difficulty": "hard"},

            {"id": "ap-math-012", "year": 2024, "board": "ap", "subject": "ap-mathematics", "chapter": "Trigonometry", "topic": "Trigonometric Ratios", "type": "mcq", "marks": 1, "question_text": "If sin A = 3/5, then cos A is:", "options": ["4/5", "3/5", "5/4", "2/5"], "correct_answer": "4/5", "explanation": "sin\u00b2A + cos\u00b2A = 1 \u21d2 cos\u00b2A = 1 - 9/25 = 16/25 \u21d2 cos A = 4/5.", "difficulty": "easy"},
            {"id": "ap-math-013", "year": 2023, "board": "ap", "subject": "ap-mathematics", "chapter": "Trigonometry", "topic": "Trigonometric Identities", "type": "vsa", "marks": 1, "question_text": "Simplify: sec\u00b2A - tan\u00b2A.", "options": None, "correct_answer": "1", "explanation": "By the identity 1 + tan\u00b2A = sec\u00b2A, so sec\u00b2A - tan\u00b2A = 1.", "difficulty": "easy"},
            {"id": "ap-math-014", "year": 2022, "board": "ap", "subject": "ap-mathematics", "chapter": "Trigonometry", "topic": "Heights and Distances", "type": "la", "marks": 4, "question_text": "The angle of elevation of the top of a tower from a point 30 m away is 60\u00b0. Find the height of the tower.", "options": None, "correct_answer": "30\u221a3 m", "explanation": "tan 60\u00b0 = h/30 \u21d2 \u221a3 = h/30 \u21d2 h = 30\u221a3 m.", "difficulty": "medium"},

            {"id": "ap-math-015", "year": 2024, "board": "ap", "subject": "ap-mathematics", "chapter": "Mensuration", "topic": "Surface Area of Solids", "type": "mcq", "marks": 1, "question_text": "The curved surface area of a cylinder with radius r and height h is:", "options": ["2\u03c0rh", "\u03c0r\u00b2h", "2\u03c0r(r+h)", "\u03c0rl"], "correct_answer": "2\u03c0rh", "explanation": "CSA of cylinder = 2\u03c0rh, where r is radius and h is height.", "difficulty": "easy"},
            {"id": "ap-math-016", "year": 2023, "board": "ap", "subject": "ap-mathematics", "chapter": "Mensuration", "topic": "Volume of Solids", "type": "sa", "marks": 2, "question_text": "Find the volume of a sphere of radius 7 cm.", "options": None, "correct_answer": "1437.33 cm\u00b3", "explanation": "V = (4/3)\u03c0r\u00b3 = (4/3)\u00d7(22/7)\u00d7343 = (4/3)\u00d722\u00d749 = (4/3)\u00d71078 = 4312/3 = 1437.33 cm\u00b3.", "difficulty": "medium"},
        ],
        "ap-physical-science": [
            {"id": "ap-ps-001", "year": 2024, "board": "ap", "subject": "ap-physical-science", "chapter": "Chemical Reactions and Equations", "topic": "Types of Reactions", "type": "mcq", "marks": 1, "question_text": "The reaction CaCO\u2083 \u2192 CaO + CO\u2082 is:", "options": ["Decomposition", "Combination", "Displacement", "Double displacement"], "correct_answer": "Decomposition", "explanation": "A single compound (calcium carbonate) breaks down into two simpler substances.", "difficulty": "easy"},
            {"id": "ap-ps-002", "year": 2023, "board": "ap", "subject": "ap-physical-science", "chapter": "Chemical Reactions and Equations", "topic": "Balancing Equations", "type": "vsa", "marks": 1, "question_text": "Balance: Na + H\u2082O \u2192 NaOH + H\u2082.", "options": None, "correct_answer": "2Na + 2H\u2082O \u2192 2NaOH + H\u2082", "explanation": "Two Na atoms on each side. 4 H on LHS, 2+2=4 H on RHS. 2 O on each side.", "difficulty": "medium"},
            {"id": "ap-ps-003", "year": 2022, "board": "ap", "subject": "ap-physical-science", "chapter": "Chemical Reactions and Equations", "topic": "Redox Reactions", "type": "sa", "marks": 2, "question_text": "In CuO + H\u2082 \u2192 Cu + H\u2082O, identify the oxidising agent.", "options": None, "correct_answer": "CuO (copper oxide)", "explanation": "CuO gives oxygen to H\u2082, so CuO is the oxidising agent. H\u2082 gains oxygen and is oxidised.", "difficulty": "medium"},

            {"id": "ap-ps-004", "year": 2024, "board": "ap", "subject": "ap-physical-science", "chapter": "Acids, Bases and Salts", "topic": "pH Scale", "type": "mcq", "marks": 1, "question_text": "The pH of pure water at 25\u00b0C is:", "options": ["0", "7", "14", "1"], "correct_answer": "7", "explanation": "Pure water is neutral with pH = 7 at 25\u00b0C because [H\u207a] = [OH\u207b] = 10\u207b\u2077 M.", "difficulty": "easy"},
            {"id": "ap-ps-005", "year": 2023, "board": "ap", "subject": "ap-physical-science", "chapter": "Acids, Bases and Salts", "topic": "Neutralisation", "type": "vsa", "marks": 1, "question_text": "What is the pH range of acids?", "options": None, "correct_answer": "0 to less than 7", "explanation": "Acids have pH values ranging from 0 (strong acid) to just below 7 (weak acid). pH 7 is neutral and pH > 7 is basic.", "difficulty": "easy"},

            {"id": "ap-ps-006", "year": 2024, "board": "ap", "subject": "ap-physical-science", "chapter": "Light \u2013 Reflection and Refraction", "topic": "Reflection", "type": "mcq", "marks": 1, "question_text": "The image formed by a plane mirror is:", "options": ["Virtual and erect", "Real and inverted", "Real and erect", "Virtual and inverted"], "correct_answer": "Virtual and erect", "explanation": "Plane mirrors always produce virtual, erect, and laterally inverted images of the same size as the object.", "difficulty": "easy"},
            {"id": "ap-ps-007", "year": 2023, "board": "ap", "subject": "ap-physical-science", "chapter": "Light \u2013 Reflection and Refraction", "topic": "Spherical Mirrors", "type": "sa", "marks": 2, "question_text": "A concave mirror produces a real image at 20 cm when object is at 10 cm. Find the focal length.", "options": None, "correct_answer": "6.67 cm", "explanation": "u = -10 cm, v = -20 cm (real image). Mirror formula: 1/f = 1/u + 1/v = -1/10 + (-1/20) = -3/20. f = -20/3 \u2248 -6.67 cm.", "difficulty": "medium"},

            {"id": "ap-ps-008", "year": 2024, "board": "ap", "subject": "ap-physical-science", "chapter": "Electricity", "topic": "Ohm's Law", "type": "mcq", "marks": 1, "question_text": "A potential difference of 12 V across a resistor produces 3 A current. The resistance is:", "options": ["4 \u03a9", "36 \u03a9", "0.25 \u03a9", "15 \u03a9"], "correct_answer": "4 \u03a9", "explanation": "R = V/I = 12/3 = 4 \u03a9.", "difficulty": "easy"},
            {"id": "ap-ps-009", "year": 2023, "board": "ap", "subject": "ap-physical-science", "chapter": "Electricity", "topic": "Resistance", "type": "sa", "marks": 2, "question_text": "A wire of resistance 5\u03a9 is stretched to double its length. Find the new resistance.", "options": None, "correct_answer": "20 \u03a9", "explanation": "When length doubles, cross-sectional area halves. R \u221d l/A. New R = 2l/(A/2) \u00d7 \u03c1 = 4 \u00d7 5 = 20 \u03a9.", "difficulty": "medium"},

            {"id": "ap-ps-010", "year": 2024, "board": "ap", "subject": "ap-physical-science", "chapter": "Carbon and its Compounds", "topic": "Covalent Bonding", "type": "mcq", "marks": 1, "question_text": "How many covalent bonds does carbon typically form?", "options": ["2", "3", "4", "5"], "correct_answer": "4", "explanation": "Carbon has 4 valence electrons and forms 4 covalent bonds to achieve a stable octet configuration.", "difficulty": "easy"},
            {"id": "ap-ps-011", "year": 2023, "board": "ap", "subject": "ap-physical-science", "chapter": "Carbon and its Compounds", "topic": "Functional Groups", "type": "vsa", "marks": 1, "question_text": "What is the functional group of alcohols?", "options": None, "correct_answer": "-OH (hydroxyl group)", "explanation": "Alcohols contain the hydroxyl functional group (-OH) attached to a carbon atom.", "difficulty": "easy"},
        ],
    },
    "ts": {
        "ts-mathematics": [
            {"id": "ts-math-001", "year": 2024, "board": "ts", "subject": "ts-mathematics", "chapter": "Real Numbers", "topic": "Euclid's Division Lemma", "type": "mcq", "marks": 1, "question_text": "For any positive integer a, a(a\u00b2-1) is always divisible by:", "options": ["6", "12", "18", "24"], "correct_answer": "6", "explanation": "a(a\u00b2-1) = (a-1)a(a+1), product of three consecutive integers, always divisible by 6.", "difficulty": "medium"},
            {"id": "ts-math-002", "year": 2023, "board": "ts", "subject": "ts-mathematics", "chapter": "Real Numbers", "topic": "Prime Factorisation", "type": "vsa", "marks": 1, "question_text": "Find the LCM of 12 and 18.", "options": None, "correct_answer": "36", "explanation": "12 = 2\u00b2\u00d73, 18 = 2\u00d73\u00b2. LCM = 2\u00b2 \u00d7 3\u00b2 = 4 \u00d7 9 = 36.", "difficulty": "easy"},
            {"id": "ts-math-003", "year": 2022, "board": "ts", "subject": "ts-mathematics", "chapter": "Real Numbers", "topic": "Irrational Numbers", "type": "sa", "marks": 2, "question_text": "Prove that \u221a5 is irrational.", "options": None, "correct_answer": "Assume \u221a5 = p/q in lowest terms. Then 5q\u00b2 = p\u00b2, so 5 divides p, then 5 divides q, contradiction.", "explanation": "Let \u221a5 = p/q, gcd(p,q)=1. Then 5 = p\u00b2/q\u00b2 \u21d2 p\u00b2 = 5q\u00b2. So 5|p\u00b2 \u21d2 5|p. Let p=5k. Then 25k\u00b2 = 5q\u00b2 \u21d2 q\u00b2 = 5k\u00b2 \u21d2 5|q. Contradiction as p,q coprime.", "difficulty": "medium"},

            {"id": "ts-math-004", "year": 2024, "board": "ts", "subject": "ts-mathematics", "chapter": "Polynomials", "topic": "Zeroes of Polynomial", "type": "mcq", "marks": 1, "question_text": "If one zero of 2x\u00b2 - 8x + k is 3, then k =:", "options": ["6", "-6", "12", "18"], "correct_answer": "6", "explanation": "p(3) = 2(9) - 8(3) + k = 18 - 24 + k = 0 \u21d2 k = 6.", "difficulty": "medium"},
            {"id": "ts-math-005", "year": 2023, "board": "ts", "subject": "ts-mathematics", "chapter": "Polynomials", "topic": "Sum and Product of Zeroes", "type": "vsa", "marks": 1, "question_text": "Find the sum of zeroes of 3x\u00b2 - 5x + 2.", "options": None, "correct_answer": "5/3", "explanation": "Sum = -b/a = -(-5)/3 = 5/3.", "difficulty": "easy"},
            {"id": "ts-math-006", "year": 2022, "board": "ts", "subject": "ts-mathematics", "chapter": "Polynomials", "topic": "Division Algorithm", "type": "sa", "marks": 3, "question_text": "Divide x\u00b3 - 3x\u00b2 + 3x - 5 by x - 1 and find the remainder.", "options": None, "correct_answer": "-4", "explanation": "Using remainder theorem: p(1) = 1 - 3 + 3 - 5 = -4. So remainder is -4.", "difficulty": "medium"},

            {"id": "ts-math-007", "year": 2024, "board": "ts", "subject": "ts-mathematics", "chapter": "Progressions", "topic": "Arithmetic Progressions", "type": "mcq", "marks": 1, "question_text": "The 15th term of AP: -3, 1, 5, 9, ... is:", "options": ["53", "57", "49", "61"], "correct_answer": "53", "explanation": "a = -3, d = 4. a\u2081\u2085 = -3 + 14\u00d74 = -3 + 56 = 53.", "difficulty": "easy"},
            {"id": "ts-math-008", "year": 2023, "board": "ts", "subject": "ts-mathematics", "chapter": "Progressions", "topic": "Sum of n Terms", "type": "sa", "marks": 2, "question_text": "Find the sum of first 10 terms of AP: 4, 7, 10, 13, ...", "options": None, "correct_answer": "175", "explanation": "a=4, d=3, n=10. S = 10/2[8 + 9\u00d73] = 5[8+27] = 5\u00d735 = 175.", "difficulty": "easy"},

            {"id": "ts-math-009", "year": 2024, "board": "ts", "subject": "ts-mathematics", "chapter": "Trigonometry", "topic": "Trigonometric Ratios", "type": "mcq", "marks": 1, "question_text": "If tan A = 1, then the value of 2 sin A cos A is:", "options": ["0", "1", "1/2", "2"], "correct_answer": "1", "explanation": "tan A = 1 \u21d2 A = 45\u00b0. 2 sin 45\u00b0 cos 45\u00b0 = 2(1/\u221a2)(1/\u221a2) = 2(1/2) = 1.", "difficulty": "medium"},
            {"id": "ts-math-010", "year": 2023, "board": "ts", "subject": "ts-mathematics", "chapter": "Trigonometry", "topic": "Heights and Distances", "type": "la", "marks": 4, "question_text": "A kite is flying at a height of 60 m above ground. The string makes an angle of 30\u00b0 with the ground. Find the length of the string.", "options": None, "correct_answer": "120 m", "explanation": "sin 30\u00b0 = opposite/hypotenuse = 60/length. 1/2 = 60/l \u21d2 l = 120 m.", "difficulty": "medium"},

            {"id": "ts-math-011", "year": 2024, "board": "ts", "subject": "ts-mathematics", "chapter": "Statistics", "topic": "Mean", "type": "vsa", "marks": 1, "question_text": "In the assumed mean method, d\u1d62 = x\u1d62 - a. What does 'a' denote?", "options": None, "correct_answer": "Assumed mean", "explanation": "d\u1d62 = x\u1d62 - a where a is the assumed mean, used to simplify calculations.", "difficulty": "easy"},
            {"id": "ts-math-012", "year": 2023, "board": "ts", "subject": "ts-mathematics", "chapter": "Statistics", "topic": "Mode", "type": "sa", "marks": 2, "question_text": "Find the mode of: 10, 12, 14, 12, 15, 12, 10, 14, 12, 13.", "options": None, "correct_answer": "12", "explanation": "Frequency: 10 appears 2, 12 appears 4, 13 appears 1, 14 appears 2, 15 appears 1. Mode = 12 (highest frequency).", "difficulty": "easy"},
        ],
        "ts-physical-science": [
            {"id": "ts-ps-001", "year": 2024, "board": "ts", "subject": "ts-physical-science", "chapter": "Chemical Reactions and Equations", "topic": "Types of Reactions", "type": "mcq", "marks": 1, "question_text": "Zn + CuSO\u2084 \u2192 ZnSO\u2084 + Cu is a:", "options": ["Displacement", "Combination", "Decomposition", "Double displacement"], "correct_answer": "Displacement", "explanation": "Zinc displaces copper from copper sulphate solution since Zn is more reactive than Cu.", "difficulty": "easy"},
            {"id": "ts-ps-002", "year": 2023, "board": "ts", "subject": "ts-physical-science", "chapter": "Chemical Reactions and Equations", "topic": "Balancing", "type": "vsa", "marks": 1, "question_text": "Balance: N\u2082 + H\u2082 \u2192 NH\u2083.", "options": None, "correct_answer": "N\u2082 + 3H\u2082 \u2192 2NH\u2083", "explanation": "2 N atoms on RHS need 2 NH\u2083, then 6 H on RHS need 3 H\u2082 on LHS.", "difficulty": "easy"},

            {"id": "ts-ps-003", "year": 2024, "board": "ts", "subject": "ts-physical-science", "chapter": "Electricity", "topic": "Ohm's Law", "type": "mcq", "marks": 1, "question_text": "The SI unit of electric current is:", "options": ["Volt", "Ampere", "Ohm", "Watt"], "correct_answer": "Ampere", "explanation": "Electric current is measured in amperes (A), named after Andr\u00e9-Marie Amp\u00e8re.", "difficulty": "easy"},
            {"id": "ts-ps-004", "year": 2023, "board": "ts", "subject": "ts-physical-science", "chapter": "Electricity", "topic": "Resistance", "type": "sa", "marks": 2, "question_text": "Two resistors of 6\u03a9 and 3\u03a9 are connected in series. Find the total resistance.", "options": None, "correct_answer": "9 \u03a9", "explanation": "R_series = R\u2081 + R\u2082 = 6 + 3 = 9 \u03a9.", "difficulty": "easy"},
            {"id": "ts-ps-005", "year": 2022, "board": "ts", "subject": "ts-physical-science", "chapter": "Electricity", "topic": "Power", "type": "sa", "marks": 3, "question_text": "A 100 W bulb is used for 10 hours daily. Find the energy consumed in 30 days in kWh.", "options": None, "correct_answer": "30 kWh", "explanation": "Daily consumption = 100 \u00d7 10 = 1000 Wh = 1 kWh. For 30 days: 1 \u00d7 30 = 30 kWh.", "difficulty": "medium"},

            {"id": "ts-ps-006", "year": 2024, "board": "ts", "subject": "ts-physical-science", "chapter": "Light \u2013 Reflection and Refraction", "topic": "Refraction", "type": "mcq", "marks": 1, "question_text": "When light travels from rarer to denser medium, it bends:", "options": ["Towards normal", "Away from normal", "Does not bend", "Along the normal"], "correct_answer": "Towards normal", "explanation": "When light enters a denser medium, its speed decreases and it bends towards the normal.", "difficulty": "easy"},
            {"id": "ts-ps-007", "year": 2023, "board": "ts", "subject": "ts-physical-science", "chapter": "Light \u2013 Reflection and Refraction", "topic": "Lenses", "type": "vsa", "marks": 1, "question_text": "What type of lens converges light rays?", "options": None, "correct_answer": "Convex lens", "explanation": "A convex (converging) lens is thicker in the middle and converges parallel light rays to a focal point.", "difficulty": "easy"},

            {"id": "ts-ps-008", "year": 2024, "board": "ts", "subject": "ts-physical-science", "chapter": "Human Eye and Colourful World", "topic": "Defects of Vision", "type": "mcq", "marks": 1, "question_text": "Myopia is corrected by using:", "options": ["Concave lens", "Convex lens", "Cylindrical lens", "Bifocal lens"], "correct_answer": "Concave lens", "explanation": "Myopia (nearsightedness) is corrected using a concave lens that diverges light rays before they enter the eye.", "difficulty": "easy"},

            {"id": "ts-ps-009", "year": 2023, "board": "ts", "subject": "ts-physical-science", "chapter": "Carbon and its Compounds", "topic": "Covalent Bonding", "type": "mcq", "marks": 1, "question_text": "The bond formed by sharing of electrons is called:", "options": ["Ionic bond", "Covalent bond", "Metallic bond", "Hydrogen bond"], "correct_answer": "Covalent bond", "explanation": "A covalent bond is formed when two atoms share one or more pairs of electrons.", "difficulty": "easy"},
        ],
    },
}


def get_questions(board_id, subject_id, chapter=None, year=None, question_type=None, limit=50):
    """Filter questions by board, subject, chapter, year, and/or question type."""
    board = QUESTION_BANK.get(board_id)
    if not board:
        raise ValueError(f"Board '{board_id}' not found. Valid: {list(QUESTION_BANK.keys())}")
    questions = board.get(subject_id)
    if not questions:
        raise ValueError(f"Subject '{subject_id}' not found under board '{board_id}'.")

    result = list(questions)
    if chapter:
        result = [q for q in result if q["chapter"].lower() == chapter.lower()]
    if year:
        result = [q for q in result if q["year"] == year]
    if question_type:
        result = [q for q in result if q["type"] == question_type.lower()]
    return result[:limit]


def _pick_balanced(questions, type_needs):
    """Pick questions matching type/marks requirements without duplicates."""
    pool = {t: [q for q in questions if q["type"] == t] for t in type_needs}
    selected = []
    used_ids = set()
    for t, count in type_needs.items():
        avail = [q for q in pool.get(t, []) if q["id"] not in used_ids]
        picked = avail[:count]
        for q in picked:
            used_ids.add(q["id"])
        selected.extend(picked)
        if len(picked) < count:
            fill = [q for q in questions if q["id"] not in used_ids][:count - len(picked)]
            for q in fill:
                used_ids.add(q["id"])
            selected.extend(fill)
    return selected


def generate_model_paper(board_id, subject_id, num_questions=30):
    """Generate a balanced model paper following standard exam pattern.

    Pattern: MCQ 1m x6, VSA 1m x6, SA2 2m x4, SA3 3m x4, LA 4m x4, CBQ 4m x2
    Total: 30 questions, 80 marks.
    """
    questions = QUESTION_BANK.get(board_id, {}).get(subject_id)
    if not questions:
        raise ValueError(f"No questions for {board_id}/{subject_id}")

    type_needs = {
        "mcq": 6,
        "vsa": 6,
        "sa": 8,
        "la": 6,
        "cbq": 4,
    }
    if num_questions != 30:
        total = sum(type_needs.values())
        factor = num_questions / total
        type_needs = {t: max(1, round(c * factor)) for t, c in type_needs.items()}

    paper = _pick_balanced(questions, type_needs)
    total_marks = sum(q["marks"] for q in paper)
    chapters_covered = list(dict.fromkeys(q["chapter"] for q in paper))

    return {
        "board": board_id,
        "subject": subject_id,
        "total_questions": len(paper),
        "total_marks": total_marks,
        "chapters_covered": chapters_covered,
        "questions": paper,
    }


def get_past_year_patterns(board_id, subject_id):
    """Analyse question patterns by chapter, type, and year."""
    questions = QUESTION_BANK.get(board_id, {}).get(subject_id)
    if not questions:
        raise ValueError(f"No questions for {board_id}/{subject_id}")

    total = len(questions)
    total_marks = sum(q["marks"] for q in questions)
    chapters = {}
    for q in questions:
        ch = q["chapter"]
        chapters.setdefault(ch, {"count": 0, "marks": 0, "topics": set(), "years": set()})
        chapters[ch]["count"] += 1
        chapters[ch]["marks"] += q["marks"]
        chapters[ch]["topics"].add(q["topic"])
        chapters[ch]["years"].add(q["year"])

    year_counts = {}
    for q in questions:
        year_counts[q["year"]] = year_counts.get(q["year"], 0) + 1

    type_dist = {}
    for q in questions:
        type_dist[q["type"]] = type_dist.get(q["type"], 0) + 1

    most_asked_ch = max(chapters, key=lambda c: chapters[c]["count"])
    insights = {
        "board": board_id,
        "subject": subject_id,
        "total_questions": total,
        "total_marks_analysed": total_marks,
        "chapter_wise": {},
        "year_wise_counts": year_counts,
        "type_distribution": type_dist,
        "top_chapter": f"Most asked in: {most_asked_ch} ({chapters[most_asked_ch]['count']} questions, {chapters[most_asked_ch]['marks']} marks)",
    }
    for ch, data in chapters.items():
        weightage = round(data["marks"] / total_marks * 100, 1) if total_marks else 0
        insights["chapter_wise"][ch] = {
            "count": data["count"],
            "marks": data["marks"],
            "weightage": f"{weightage}%",
            "topics": sorted(data["topics"]),
            "years_covered": sorted(data["years"]),
        }
    return insights


def get_explanation(question_id):
    """Return detailed step-by-step explanation for a question by its ID."""
    for board in QUESTION_BANK.values():
        for questions in board.values():
            for q in questions:
                if q["id"] == question_id:
                    return {
                        "id": q["id"],
                        "question": q["question_text"],
                        "correct_answer": q["correct_answer"],
                        "explanation": q["explanation"],
                        "chapter": q["chapter"],
                        "topic": q["topic"],
                        "difficulty": q["difficulty"],
                        "marks": q["marks"],
                        "type": q["type"],
                        "year": q["year"],
                    }
    return None
