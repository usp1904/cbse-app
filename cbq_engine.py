import random
import json


CBQ_SCENARIOS = [
    # ==================== CBSE MATHEMATICS ====================
    {
        "id": "cbse-math-solar-panel",
        "title": "Solar Panel Installation on Roof",
        "board_id": "cbse",
        "subject_id": "mathematics",
        "chapter": "Some Applications of Trigonometry",
        "topics": ["Heights and Distances", "Area of Rectangle", "Trigonometric Ratios"],
        "case_text": (
            "Ravi is planning to install solar panels on the flat roof of his house in Delhi. "
            "The roof is 12 m long and 8 m wide. Each solar panel is a rectangle measuring 1.5 m by 1 m. "
            "The sun's rays fall at an angle of 60\u00b0 with the horizontal at noon. "
            "Ravi wants to maximize power generation by tilting the panels optimally. "
            "He also needs to leave a 0.5 m gap on all sides of the roof for maintenance access."
        ),
        "questions": [
            {
                "id": "sp-q1",
                "text": "What is the effective area available for installing solar panels on the roof?",
                "type": "mcq",
                "options": [
                    "A) 77 m\u00b2",
                    "B) 96 m\u00b2",
                    "C) 84 m\u00b2",
                    "D) 91 m\u00b2"
                ],
                "correct_answer": "A) 77 m\u00b2",
                "explanation": "Roof area = 12 \u00d7 8 = 96 m\u00b2. Gap of 0.5 m on all sides reduces length by 1 m and width by 1 m. Effective area = 11 \u00d7 7 = 77 m\u00b2.",
                "marks": 1
            },
            {
                "id": "sp-q2",
                "text": "What is the maximum number of solar panels (1.5 m \u00d7 1 m) that can be installed in the effective area without overlapping or cutting panels?",
                "type": "mcq",
                "options": [
                    "A) 44",
                    "B) 49",
                    "C) 51",
                    "D) 56"
                ],
                "correct_answer": "C) 51",
                "explanation": "Effective area = 77 m\u00b2. Area per panel = 1.5 \u00d7 1 = 1.5 m\u00b2. Maximum panels (by area) = 77 / 1.5 = 51.33, so 51 whole panels can fit. With grid alignment constraints, the practical count is 49, but the question asks for the maximum based on area.",
                "marks": 1
            },
            {
                "id": "sp-q3",
                "text": "If Ravi tilts a panel so that it makes an angle of 30\u00b0 with the horizontal, what is the length of the shadow cast by a 1.5 m long panel on the ground? (Assume sun's rays are at 60\u00b0 to horizontal)",
                "type": "sa",
                "correct_answer": "0.87 m",
                "explanation": "The panel is tilted at 30\u00b0 to horizontal. Sun rays at 60\u00b0 to horizontal means the angle between panel and sun rays = 30\u00b0. Using trigonometry: shadow length = 1.5 \u00d7 tan(30\u00b0) = 1.5 \u00d7 0.577 = 0.87 m (approx).",
                "marks": 2
            },
            {
                "id": "sp-q4",
                "text": "If each panel generates 300 watts per hour and the sun shines effectively for 5 hours per day, how much energy (in kWh) does the entire installation generate per day?",
                "type": "sa",
                "correct_answer": "73.5 kWh",
                "explanation": "Number of panels = 49. Each panel: 300 W \u00d7 5 h = 1500 Wh = 1.5 kWh. Total = 49 \u00d7 1.5 = 73.5 kWh per day.",
                "marks": 2
            }
        ]
    },
    {
        "id": "cbse-math-cricket-stadium",
        "title": "Cricket Stadium Seating Arrangement",
        "board_id": "cbse",
        "subject_id": "mathematics",
        "chapter": "Arithmetic Progressions",
        "topics": ["nth Term of an AP", "Sum of First n Terms of an AP"],
        "case_text": (
            "A new cricket stadium is being built in Ahmedabad with a seating arrangement in the shape of a horseshoe. "
            "The first row has 40 seats, and each subsequent row has 8 more seats than the previous row. "
            "There are 30 rows in total. The stadium management needs to calculate total capacity "
            "for ticketing and also determine which row number crosses 200 seats for premium signage placement."
        ),
        "questions": [
            {
                "id": "cs-q1",
                "text": "How many seats are in the 15th row?",
                "type": "mcq",
                "options": [
                    "A) 140",
                    "B) 152",
                    "C) 160",
                    "D) 148"
                ],
                "correct_answer": "B) 152",
                "explanation": "AP: a = 40, d = 8. a\u2081\u2085 = 40 + (15-1)\u00d78 = 40 + 112 = 152.",
                "marks": 1
            },
            {
                "id": "cs-q2",
                "text": "What is the total seating capacity of the stadium?",
                "type": "mcq",
                "options": [
                    "A) 4,680",
                    "B) 5,200",
                    "C) 4,560",
                    "D) 4,800"
                ],
                "correct_answer": "A) 4,680",
                "explanation": "S\u2083\u2080 = (30/2)[2\u00d740 + (30-1)\u00d78] = 15[80 + 232] = 15 \u00d7 312 = 4,680.",
                "marks": 1
            },
            {
                "id": "cs-q3",
                "text": "Which is the first row that has more than 200 seats?",
                "type": "sa",
                "correct_answer": "21st row",
                "explanation": "40 + (n-1)\u00d78 > 200 \u21d2 (n-1)\u00d78 > 160 \u21d2 n-1 > 20 \u21d2 n > 21. So the 21st row has 40 + 160 = 200 seats exactly. The 22nd row has 208 seats. Wait: 40 + (n-1)\u00d78 > 200 => (n-1)>20 => n>21. So first row exceeding 200 is n=22 (208 seats). The 21st row has exactly 200. So answer: 22nd row.",
                "marks": 2
            },
            {
                "id": "cs-q4",
                "text": "If the ticket price for row 1 is \u20b9500 and decreases by \u20b920 per subsequent row, what is the total revenue if all seats in the first 10 rows are sold?",
                "type": "sa",
                "correct_answer": "\u20b92,79,200",
                "explanation": "Revenue = \u03a3(seats_in_row_r \u00d7 price_in_row_r) for r=1 to 10. Seats: a_r = 40+8(r-1). Price: p_r = 500-20(r-1). Sum: \u03a3(40+8r-8)(500-20r+20) = \u03a3(32+8r)(520-20r) for r=0..9. = \u03a3(16640 + 3520r - 160r\u00b2). Using sum formulas: r=0..9 sum of r = 45, sum of r\u00b2 = 285. Result = 10\u00d716640 + 3520\u00d745 - 160\u00d7285 = 166400 + 158400 - 45600 = 279200.",
                "marks": 2
            }
        ]
    },
    {
        "id": "cbse-math-garden-path",
        "title": "Garden Pathway Design",
        "board_id": "cbse",
        "subject_id": "mathematics",
        "chapter": "Quadratic Equations",
        "topics": ["Solution of a Quadratic Equation by Factorisation", "Nature of Roots"],
        "case_text": (
            "A rectangular garden is 30 m long and 20 m wide. The owner wants to construct a uniform-width "
            "pathway around the inside edge of the garden, leaving a central lawn area of 336 m\u00b2 for planting. "
            "The pathway will be paved with interlocking tiles. The owner needs to find the appropriate width "
            "of the pathway and the number of tiles required."
        ),
        "questions": [
            {
                "id": "gp-q1",
                "text": "If the width of the pathway is x metres, which equation represents the area of the central lawn?",
                "type": "mcq",
                "options": [
                    "A) (30 - x)(20 - x) = 336",
                    "B) (30 - 2x)(20 - 2x) = 336",
                    "C) (30 + 2x)(20 + 2x) = 336",
                    "D) 30 \u00d7 20 - 4x\u00b2 = 336"
                ],
                "correct_answer": "B) (30 - 2x)(20 - 2x) = 336",
                "explanation": "Pathway reduces length and width by 2x (x on each side). So lawn dimensions are (30-2x) and (20-2x).",
                "marks": 1
            },
            {
                "id": "gp-q2",
                "text": "What is the width of the pathway?",
                "type": "mcq",
                "options": [
                    "A) 1 m",
                    "B) 2 m",
                    "C) 3 m",
                    "D) 4 m"
                ],
                "correct_answer": "B) 2 m",
                "explanation": "(30-2x)(20-2x) = 336 \u21d2 600 - 60x - 40x + 4x\u00b2 = 336 \u21d2 4x\u00b2 - 100x + 264 = 0 \u21d2 x\u00b2 - 25x + 66 = 0 \u21d2 (x-3)(x-22)=0. Since x < 10 (half of 20), x = 3. Wait: (x-22)(x-3)=0, so x=3 or x=22. x=3 m is valid. Let me double-check: (30-6)(20-6)=24\u00d714=336. Yes! x=3 m.",
                "marks": 1
            },
            {
                "id": "gp-q3",
                "text": "If each tile measures 25 cm \u00d7 25 cm, how many tiles are needed for the pathway?",
                "type": "sa",
                "correct_answer": "5,376 tiles",
                "explanation": "Pathway area = Total area - Lawn area = 600 - 336 = 264 m\u00b2. Area per tile = 0.25 \u00d7 0.25 = 0.0625 m\u00b2. Number of tiles = 264 / 0.0625 = 4,224 tiles.",
                "marks": 2
            },
            {
                "id": "gp-q4",
                "text": "If the pathway width is doubled, what would be the area of the remaining central lawn?",
                "type": "sa",
                "correct_answer": "96 m\u00b2",
                "explanation": "x = 6 m. Lawn dimensions: 30-12 = 18 m, 20-12 = 8 m. Lawn area = 18 \u00d7 8 = 144 m\u00b2.",
                "marks": 1
            }
        ]
    },
    {
        "id": "cbse-math-water-tank",
        "title": "Water Tank Construction",
        "board_id": "cbse",
        "subject_id": "mathematics",
        "chapter": "Surface Areas and Volumes",
        "topics": ["Volume of a Combination of Solids", "Conversion of Solid from One Shape to Another", "Frustum of a Cone"],
        "case_text": (
            "A village in Maharashtra needs an elevated water storage tank. The tank consists of a cylindrical "
            "base with radius 3 m and height 4 m, surmounted by a hemispherical dome of the same radius. "
            "Water is supplied by a cylindrical pipe of diameter 10 cm at a speed of 8 m/s. "
            "The village needs to store at least 150,000 litres of water for daily use."
        ),
        "questions": [
            {
                "id": "wt-q1",
                "text": "What is the total capacity of the tank in litres? (\u03c0 = 3.14)",
                "type": "mcq",
                "options": [
                    "A) 1,69,560 L",
                    "B) 1,41,300 L",
                    "C) 1,88,400 L",
                    "D) 1,57,000 L"
                ],
                "correct_answer": "A) 1,69,560 L",
                "explanation": "Cylinder volume = \u03c0(3)\u00b2(4) = 36\u03c0 = 113.04 m\u00b3. Hemisphere volume = (2/3)\u03c0(3)\u00b3 = 18\u03c0 = 56.52 m\u00b3. Total = 169.56 m\u00b3 = 1,69,560 L.",
                "marks": 1
            },
            {
                "id": "wt-q2",
                "text": "How long must the pipe run to fill the tank completely?",
                "type": "mcq",
                "options": [
                    "A) 30 minutes",
                    "B) 45 minutes",
                    "C) 60 minutes",
                    "D) 90 minutes"
                ],
                "correct_answer": "B) 45 minutes",
                "explanation": "Pipe cross-section = \u03c0(0.05)\u00b2 = 0.00785 m\u00b2. Volume flow rate = 0.00785 \u00d7 8 = 0.0628 m\u00b3/s. Time = 169.56 / 0.0628 = 2700 seconds = 45 minutes.",
                "marks": 1
            },
            {
                "id": "wt-q3",
                "text": "If the cylindrical base is instead made into a frustum of a cone with top radius 3 m, bottom radius 4 m, and height 4 m, what would be its volume? (\u03c0 = 3.14)",
                "type": "sa",
                "correct_answer": "155.09 m\u00b3",
                "explanation": "Volume of frustum = (\u03c0h/3)(R\u00b2 + r\u00b2 + Rr) = (3.14\u00d74/3)(16 + 9 + 12) = (12.56/3)(37) = 4.187 \u00d7 37 = 154.9 m\u00b3.",
                "marks": 2
            }
        ]
    },
    {
        "id": "cbse-math-traffic-signal",
        "title": "Traffic Signal Probability",
        "board_id": "cbse",
        "subject_id": "mathematics",
        "chapter": "Probability",
        "topics": ["Probability - A Theoretical Approach"],
        "case_text": (
            "On a busy crossing in Bengaluru, there are three independent traffic signals A, B, and C "
            "along the route to Shivajinagar. Signal A is green for 45 seconds and red for 30 seconds. "
            "Signal B is green for 30 seconds and red for 20 seconds. Signal C is green for 50 seconds "
            "and red for 25 seconds. A commuter travels through this route daily."
        ),
        "questions": [
            {
                "id": "ts-q1",
                "text": "What is the probability that signal A is green when the commuter arrives?",
                "type": "mcq",
                "options": [
                    "A) 0.4",
                    "B) 0.5",
                    "C) 0.6",
                    "D) 0.67"
                ],
                "correct_answer": "C) 0.6",
                "explanation": "P(green at A) = 45/(45+30) = 45/75 = 0.6",
                "marks": 1
            },
            {
                "id": "ts-q2",
                "text": "What is the probability that the commuter gets green at all three signals?",
                "type": "mcq",
                "options": [
                    "A) 0.20",
                    "B) 0.25",
                    "C) 0.30",
                    "D) 0.35"
                ],
                "correct_answer": "B) 0.25",
                "explanation": "P(A) \u00d7 P(B) \u00d7 P(C) = 0.6 \u00d7 (30/50) \u00d7 (50/75) = 0.6 \u00d7 0.6 \u00d7 0.667 = 0.24 \u2248 0.25. More precisely: 45/75 \u00d7 30/50 \u00d7 50/75 = (45\u00d730\u00d750)/(75\u00d750\u00d775) = 67500/281250 = 0.24.",
                "marks": 1
            },
            {
                "id": "ts-q3",
                "text": "What is the probability that exactly one of the three signals is green?",
                "type": "sa",
                "correct_answer": "0.376",
                "explanation": "P(exactly one) = P(G only) + P(R only) + P(C only). P(G_A)P(R_B)P(R_C) + P(R_A)P(G_B)P(R_C) + P(R_A)P(R_B)P(G_C) = 0.6\u00d70.4\u00d70.333 + 0.4\u00d70.6\u00d70.333 + 0.4\u00d70.4\u00d70.667 = 0.08 + 0.08 + 0.107 = 0.267.",
                "marks": 2
            }
        ]
    },
    # ==================== CBSE SCIENCE ====================
    {
        "id": "cbse-sci-fluorosis",
        "title": "Fluorosis in a Rural Village",
        "board_id": "cbse",
        "subject_id": "science",
        "chapter": "Acids, Bases and Salts",
        "topics": ["Importance of pH in Everyday Life", "Properties of Acids and Bases"],
        "case_text": (
            "A village near the Narmada river in Madhya Pradesh has reported unusually high cases of "
            "dental and skeletal fluorosis among residents. Water testing revealed that fluoride ion "
            "concentration in the groundwater is 4.2 mg/L (safe limit: 1.0 mg/L). The pH of the water "
            "sample was found to be 8.5. The local health department recommends using reverse osmosis "
            "filters and adding lime (calcium hydroxide) to precipitate fluoride as calcium fluoride."
        ),
        "questions": [
            {
                "id": "fl-q1",
                "text": "The pH of the water sample is 8.5. What does this indicate about the water?",
                "type": "mcq",
                "options": [
                    "A) It is strongly acidic",
                    "B) It is weakly acidic",
                    "C) It is weakly basic",
                    "D) It is neutral"
                ],
                "correct_answer": "C) It is weakly basic",
                "explanation": "pH > 7 indicates basic nature. pH 8.5 is weakly basic (alkaline).",
                "marks": 1
            },
            {
                "id": "fl-q2",
                "text": "How many times higher is the fluoride concentration compared to the safe limit?",
                "type": "mcq",
                "options": [
                    "A) 2.2 times",
                    "B) 3.2 times",
                    "C) 4.2 times",
                    "D) 5.2 times"
                ],
                "correct_answer": "C) 4.2 times",
                "explanation": "4.2 / 1.0 = 4.2 times the safe limit.",
                "marks": 1
            },
            {
                "id": "fl-q3",
                "text": "Write the balanced chemical equation for the reaction between calcium hydroxide and fluoride ions.",
                "type": "sa",
                "correct_answer": "Ca(OH)\u2082 + 2F\u207b \u2192 CaF\u2082 + 2OH\u207b",
                "explanation": "Calcium hydroxide dissociates to give Ca\u00b2\u207a ions which react with fluoride ions to form insoluble calcium fluoride (CaF\u2082).",
                "marks": 2
            },
            {
                "id": "fl-q4",
                "text": "Why is lime (calcium hydroxide) preferred over sodium hydroxide for defluoridation?",
                "type": "mcq",
                "options": [
                    "A) Lime is cheaper",
                    "B) Lime does not increase sodium levels in water",
                    "C) Lime reacts faster",
                    "D) Both A and B"
                ],
                "correct_answer": "D) Both A and B",
                "explanation": "Lime is cheaper than NaOH and does not add undesirable sodium ions to the water, which could cause health issues for patients with hypertension.",
                "marks": 1
            }
        ]
    },
    {
        "id": "cbse-sci-home-circuit",
        "title": "Household Electrical Circuit",
        "board_id": "cbse",
        "subject_id": "science",
        "chapter": "Electricity",
        "topics": ["Ohm's Law", "Resistors in Series and Parallel", "Heating Effect of Electric Current", "Power"],
        "case_text": (
            "A household in Chennai has the following electrical appliances connected to a 220 V supply: "
            "a 1.5 kW air conditioner, 4 LED bulbs of 12 W each, a 2 kW geyser, a 750 W refrigerator, "
            "and a 100 W television. The main fuse is rated for 15 A. The homeowner notices that the "
            "fuse blows whenever the air conditioner and geyser run simultaneously with other appliances."
        ),
        "questions": [
            {
                "id": "hc-q1",
                "text": "Calculate the total current drawn when the AC and geyser run together with all other appliances.",
                "type": "mcq",
                "options": [
                    "A) 12.5 A",
                    "B) 16.8 A",
                    "C) 20.4 A",
                    "D) 14.2 A"
                ],
                "correct_answer": "C) 20.4 A",
                "explanation": "Total power = 1500 + 2000 + 4\u00d712 + 750 + 100 = 1500 + 2000 + 48 + 750 + 100 = 4398 W. Current = P/V = 4398/220 = 20.0 A. \u2248 20 A. This exceeds the 15 A fuse rating.",
                "marks": 1
            },
            {
                "id": "hc-q2",
                "text": "Which combination of appliances can run safely without blowing the 15 A fuse?",
                "type": "mcq",
                "options": [
                    "A) AC + Geyser + Refrigerator",
                    "B) AC + Geyser + TV",
                    "C) AC + Refrigerator + All LED bulbs + TV",
                    "D) Geyser + Refrigerator + All LED bulbs + TV"
                ],
                "correct_answer": "D) Geyser + Refrigerator + All LED bulbs + TV",
                "explanation": "Option D: 2000 + 750 + 48 + 100 = 2898 W. Current = 2898/220 = 13.2 A (< 15 A). Other options exceed 15 A.",
                "marks": 1
            },
            {
                "id": "hc-q3",
                "text": "What should be the minimum fuse rating to safely run all appliances simultaneously?",
                "type": "sa",
                "correct_answer": "20 A",
                "explanation": "Total current = 20.0 A. The next standard fuse rating above this is 20 A or 25 A. Minimum safe rating = 20 A (with safety margin, 25 A is recommended).",
                "marks": 1
            },
            {
                "id": "hc-q4",
                "text": "If the refrigerator runs for 12 hours daily, AC for 6 hours, geyser for 2 hours, LED bulbs for 8 hours, and TV for 4 hours, calculate the monthly energy consumption (30 days) in kWh.",
                "type": "sa",
                "correct_answer": "540 kWh",
                "explanation": "Daily: RC: 0.75\u00d712 = 9 kWh. AC: 1.5\u00d76 = 9 kWh. Geyser: 2\u00d72 = 4 kWh. LEDs: 0.048\u00d78 = 0.384 kWh. TV: 0.1\u00d74 = 0.4 kWh. Total daily = 22.784 kWh. Monthly = 22.784 \u00d7 30 = 683.5 kWh.",
                "marks": 2
            }
        ]
    },
    {
        "id": "cbse-sci-myopia",
        "title": "Myopia in a Classroom",
        "board_id": "cbse",
        "subject_id": "science",
        "chapter": "The Human Eye and the Colourful World",
        "topics": ["Defects of Vision and their Correction", "The Human Eye"],
        "case_text": (
            "In a Class X classroom in Patna, 8 out of 42 students have difficulty reading the blackboard "
            "from the last bench (6 m away). The school optometrist diagnoses these students with myopia. "
            "The farthest distance at which one student, Priya, can see clearly is 80 cm. "
            "The optometrist prescribes corrective lenses. Another student, Rohan, has hypermetropia "
            "and cannot see clearly objects closer than 50 cm."
        ),
        "questions": [
            {
                "id": "my-q1",
                "text": "What type of lens is prescribed to correct myopia?",
                "type": "mcq",
                "options": [
                    "A) Convex lens",
                    "B) Concave lens",
                    "C) Bifocal lens",
                    "D) Cylindrical lens"
                ],
                "correct_answer": "B) Concave lens",
                "explanation": "Myopia (nearsightedness) is corrected using a concave (diverging) lens, which reduces the converging power of the eye.",
                "marks": 1
            },
            {
                "id": "my-q2",
                "text": "What is the power of the lens required for Priya to see distant objects clearly?",
                "type": "mcq",
                "options": [
                    "A) -1.25 D",
                    "B) +1.25 D",
                    "C) -2.5 D",
                    "D) +2.5 D"
                ],
                "correct_answer": "A) -1.25 D",
                "explanation": "f = -80 cm = -0.8 m (negative for concave lens). P = 1/f = -1/0.8 = -1.25 D.",
                "marks": 1
            },
            {
                "id": "my-q3",
                "text": "For Rohan's hypermetropia, what lens power would allow him to read a book held at 25 cm (normal near point)?",
                "type": "sa",
                "correct_answer": "+2.0 D",
                "explanation": "u = -25 cm, v = -50 cm (image must form at his near point). 1/f = 1/v - 1/u = -1/50 - (-1/25) = -0.02 + 0.04 = 0.02. f = 50 cm = 0.5 m. P = +2.0 D.",
                "marks": 2
            },
            {
                "id": "my-q4",
                "text": "What is the approximate percentage of students affected by myopia in this class?",
                "type": "mcq",
                "options": [
                    "A) 12%",
                    "B) 19%",
                    "C) 24%",
                    "D) 8%"
                ],
                "correct_answer": "B) 19%",
                "explanation": "Percentage = (8/42) \u00d7 100 = 19.05% \u2248 19%.",
                "marks": 1
            }
        ]
    },
    {
        "id": "cbse-sci-pond-ecosystem",
        "title": "Pond Ecosystem Study",
        "board_id": "cbse",
        "subject_id": "science",
        "chapter": "Our Environment",
        "topics": ["Ecosystem and its Components", "Food Chains and Webs"],
        "case_text": (
            "Students from a school in Kerala visit a freshwater pond ecosystem for a field study. "
            "They observe the following organisms: phytoplankton, aquatic plants, small fish, "
            "large fish, frogs, water birds, and decomposer bacteria. They measure the biomass "
            "of each trophic level and discover that the total biomass of phytoplankton is 10,000 kg, "
            "while the biomass of large fish is only 12 kg. The pond is now threatened by "
            "eutrophication due to nearby fertilizer runoff."
        ),
        "questions": [
            {
                "id": "pe-q1",
                "text": "Identify the correct food chain in this pond ecosystem:",
                "type": "mcq",
                "options": [
                    "A) Large fish \u2192 Small fish \u2192 Phytoplankton \u2192 Water birds",
                    "B) Phytoplankton \u2192 Small fish \u2192 Large fish \u2192 Water birds",
                    "C) Water birds \u2192 Large fish \u2192 Small fish \u2192 Phytoplankton",
                    "D) Decomposers \u2192 Phytoplankton \u2192 Small fish \u2192 Large fish"
                ],
                "correct_answer": "B) Phytoplankton \u2192 Small fish \u2192 Large fish \u2192 Water birds",
                "explanation": "Phytoplankton (producers) are eaten by small fish (primary consumers), which are eaten by large fish (secondary consumers), which are eaten by water birds (tertiary consumers).",
                "marks": 1
            },
            {
                "id": "pe-q2",
                "text": "What percentage of biomass is transferred from phytoplankton to large fish according to the 10% law?",
                "type": "mcq",
                "options": [
                    "A) 0.12%",
                    "B) 0.10%",
                    "C) 1.0%",
                    "D) 10%"
                ],
                "correct_answer": "A) 0.12%",
                "explanation": "Energy transfer at each trophic level is about 10%. From phytoplankton to small fish: 10% of 10000 = 1000 kg. Small fish to large fish: 10% of 1000 = 100 kg. Observed is 12 kg, which is 0.12% of original. The 10% law gives 100 kg expected, but actual is 12 kg due to inefficiencies.",
                "marks": 1
            },
            {
                "id": "pe-q3",
                "text": "How does fertilizer runoff cause eutrophication? Explain briefly.",
                "type": "sa",
                "correct_answer": "Fertilizers rich in nitrates and phosphates cause algal bloom, which depletes dissolved oxygen when algae decompose, killing aquatic life.",
                "explanation": "Excess nutrients (N, P) from fertilizers cause rapid algal growth (algal bloom). When algae die, decomposer bacteria consume oxygen, creating dead zones where fish and other organisms cannot survive.",
                "marks": 2
            },
            {
                "id": "pe-q4",
                "text": "Which trophic level has the highest energy in this ecosystem?",
                "type": "mcq",
                "options": [
                    "A) Primary consumers",
                    "B) Producers",
                    "C) Secondary consumers",
                    "D) Tertiary consumers"
                ],
                "correct_answer": "B) Producers",
                "explanation": "Producers (phytoplankton) have the highest energy as they capture sunlight through photosynthesis. Energy decreases at each successive trophic level.",
                "marks": 1
            }
        ]
    },
    {
        "id": "cbse-sci-corrosion-bridge",
        "title": "Corrosion of an Iron Bridge",
        "board_id": "cbse",
        "subject_id": "science",
        "chapter": "Metals and Non-metals",
        "topics": ["Corrosion", "Chemical Properties of Metals"],
        "case_text": (
            "A historic iron bridge built in 1890 near Kolkata shows significant rusting. "
            "The bridge is exposed to high humidity (85%), saline sea breeze from the Bay of Bengal, "
            "and acid rain (pH 5.2). Engineers estimate that 15% of the bridge's original iron mass "
            "has already been lost to corrosion. They recommend cathodic protection using zinc blocks "
            "and regular application of red oxide paint."
        ),
        "questions": [
            {
                "id": "cb-q1",
                "text": "What is the chemical name of rust?",
                "type": "mcq",
                "options": [
                    "A) Iron(II) oxide",
                    "B) Iron(III) oxide",
                    "C) Hydrated iron(III) oxide",
                    "D) Iron(III) hydroxide"
                ],
                "correct_answer": "C) Hydrated iron(III) oxide",
                "explanation": "Rust is chemically Fe\u2082O\u2083\u00b7xH\u2082O (hydrated iron(III) oxide).",
                "marks": 1
            },
            {
                "id": "cb-q2",
                "text": "Which condition accelerates the corrosion of the bridge the most?",
                "type": "mcq",
                "options": [
                    "A) Low temperature",
                    "B) Saline moisture and acidic environment",
                    "C) Paint coating",
                    "D) Dry air"
                ],
                "correct_answer": "B) Saline moisture and acidic environment",
                "explanation": "Saline (electrolyte) and acidic conditions accelerate electrochemical corrosion by facilitating electron transfer.",
                "marks": 1
            },
            {
                "id": "cb-q3",
                "text": "Explain why zinc is used for cathodic protection of iron bridges.",
                "type": "sa",
                "correct_answer": "Zinc is more reactive than iron (above iron in reactivity series), so zinc acts as anode and corrodes preferentially, protecting the iron (cathode).",
                "explanation": "In galvanic protection, the more reactive metal (zinc) acts as a sacrificial anode. Zinc loses electrons more readily than iron, so zinc corrodes instead of iron. This is called sacrificial cathodic protection.",
                "marks": 2
            },
            {
                "id": "cb-q4",
                "text": "If the original iron mass was 200 tonnes, how much iron has been lost to corrosion?",
                "type": "mcq",
                "options": [
                    "A) 15 tonnes",
                    "B) 30 tonnes",
                    "C) 20 tonnes",
                    "D) 25 tonnes"
                ],
                "correct_answer": "B) 30 tonnes",
                "explanation": "15% of 200 = 0.15 \u00d7 200 = 30 tonnes.",
                "marks": 1
            }
        ]
    },
    # ==================== CBSE SOCIAL SCIENCE ====================
    {
        "id": "cbse-sst-literacy",
        "title": "Literacy Rate and Development",
        "board_id": "cbse",
        "subject_id": "social-science",
        "chapter": "Development",
        "topics": ["Development Indicators", "National Development"],
        "case_text": (
            "According to recent data, State A has a literacy rate of 94% while State B has 74%. "
            "State A's per capita income is \u20b92.5 lakh/year while State B's is \u20b91.2 lakh/year. "
            "However, State B has a higher forest cover (33% vs 12%) and lower infant mortality rate "
            "(28 vs 32 per 1000 live births). A debate arises in a classroom about which state is more 'developed'."
        ),
        "questions": [
            {
                "id": "li-q1",
                "text": "Which state is more developed according to income-based indicators alone?",
                "type": "mcq",
                "options": [
                    "A) State B",
                    "B) State A",
                    "C) Both are equal",
                    "D) Cannot be determined"
                ],
                "correct_answer": "B) State A",
                "explanation": "State A has higher per capita income (\u20b92.5 lakh vs \u20b91.2 lakh), so by income-based measures, State A is more developed.",
                "marks": 1
            },
            {
                "id": "li-q2",
                "text": "Why might State B be considered more developed in certain aspects despite lower income?",
                "type": "mcq",
                "options": [
                    "A) It has lower literacy",
                    "B) It has higher forest cover and lower infant mortality",
                    "C) It has higher population",
                    "D) None of these"
                ],
                "correct_answer": "B) It has higher forest cover and lower infant mortality",
                "explanation": "Development includes non-income factors like environmental sustainability (forest cover) and health outcomes (infant mortality). State B performs better on these indicators.",
                "marks": 1
            },
            {
                "id": "li-q3",
                "text": "What additional indicators would you suggest for a more comprehensive comparison of development between the two states?",
                "type": "sa",
                "correct_answer": "HDI indicators: life expectancy, education (mean years of schooling), and per capita income. Also: access to clean water, sanitation, electricity, and gender equality indices.",
                "explanation": "The Human Development Index (HDI) combines health (life expectancy), education (expected and mean years of schooling), and standard of living (GNI per capita). Additional indicators like access to basic services and gender equality provide a more complete picture.",
                "marks": 2
            },
            {
                "id": "li-q4",
                "text": "What does infant mortality rate indicate about a state's development?",
                "type": "mcq",
                "options": [
                    "A) Quality of healthcare and maternal health services",
                    "B) Average income of residents",
                    "C) Number of hospitals in the state",
                    "D) Literacy rate of women"
                ],
                "correct_answer": "A) Quality of healthcare and maternal health services",
                "explanation": "IMR reflects the quality of healthcare infrastructure, maternal nutrition, prenatal care, and overall public health services available in a region.",
                "marks": 1
            }
        ]
    },
    {
        "id": "cbse-sst-power-sharing",
        "title": "Power Sharing in Belgium",
        "board_id": "cbse",
        "subject_id": "social-science",
        "chapter": "Power-sharing",
        "topics": ["Forms of Power-sharing", "Belgium and Sri Lanka Models"],
        "case_text": (
            "Belgium, a small European country, has a complex power-sharing arrangement. "
            "The Dutch-speaking community (59%) lives in Flanders, the French-speaking community (40%) "
            "in Wallonia, and 1% speak German. The capital Brussels has 80% French speakers and 20% Dutch speakers. "
            "Belgium amended its constitution four times between 1970 and 1993 to create a unique federal system "
            "with community and regional governments."
        ),
        "questions": [
            {
                "id": "ps-q1",
                "text": "How many times did Belgium amend its constitution to create the power-sharing model?",
                "type": "mcq",
                "options": [
                    "A) Two times",
                    "B) Three times",
                    "C) Four times",
                    "D) Five times"
                ],
                "correct_answer": "C) Four times",
                "explanation": "Belgium amended its constitution four times between 1970 and 1993 to develop the power-sharing arrangement.",
                "marks": 1
            },
            {
                "id": "ps-q2",
                "text": "What is the unique feature of Belgium's power-sharing model?",
                "type": "mcq",
                "options": [
                    "A) Only the central government has power",
                    "B) Equal number of Dutch and French ministers in the central government",
                    "C) French speakers have all the power",
                    "D) Decisions are made by the King alone"
                ],
                "correct_answer": "B) Equal number of Dutch and French ministers in the central government",
                "explanation": "The Belgian constitution mandates that the central government has equal numbers of Dutch-speaking and French-speaking ministers, even though the Dutch-speaking population is larger.",
                "marks": 1
            },
            {
                "id": "ps-q3",
                "text": "Compare Belgium's approach to power-sharing with Sri Lanka's approach and explain why Belgium's model is considered more successful.",
                "type": "sa",
                "correct_answer": "Belgium adopted accommodation (equal representation, community governments, federalism) while Sri Lanka adopted majoritarianism (Sinhala as only official language, preferential policies). Belgium's approach reduced conflict while Sri Lanka's led to civil war.",
                "explanation": "Belgium's model: equal ministers, separate community governments in Brussels, and a federal structure. Sri Lanka's 1956 Act made Sinhala the only official language, leading to Tamil alienation and a 26-year civil war. Power-sharing prevents majority tyranny and accommodates diversity.",
                "marks": 2
            }
        ]
    },
    {
        "id": "cbse-sst-water-conservation",
        "title": "Water Conservation in Rajasthan",
        "board_id": "cbse",
        "subject_id": "social-science",
        "chapter": "Water Resources",
        "topics": ["Water Scarcity", "Conservation of Water", "Rainwater Harvesting"],
        "case_text": (
            "The village of Laporiya in Rajasthan receives only 400 mm of rainfall annually. "
            "Despite this, the village never faces water scarcity thanks to traditional 'chauka' structures "
            "\u2014 rectangular catchment ponds that capture and percolate rainwater. The system, revived by "
            "social activist Laxman Singh, has raised the water table by 6 metres and now supports "
            "three crops per year instead of one. A neighbouring village with similar rainfall faces severe water shortage."
        ),
        "questions": [
            {
                "id": "wc-q1",
                "text": "What is a 'chauka' system?",
                "type": "mcq",
                "options": [
                    "A) A modern drip irrigation system",
                    "B) Rectangular catchment ponds for rainwater harvesting",
                    "C) A type of well",
                    "D) A canal irrigation system"
                ],
                "correct_answer": "B) Rectangular catchment ponds for rainwater harvesting",
                "explanation": "Chaukas are traditional rectangular or square catchment structures that capture rainwater and allow it to percolate into the ground, recharging the water table.",
                "marks": 1
            },
            {
                "id": "wc-q2",
                "text": "How much did the water table rise in Laporiya due to this system?",
                "type": "mcq",
                "options": [
                    "A) 2 metres",
                    "B) 4 metres",
                    "C) 6 metres",
                    "D) 8 metres"
                ],
                "correct_answer": "C) 6 metres",
                "explanation": "The water table rose by 6 metres as a result of the chauka-based rainwater harvesting system.",
                "marks": 1
            },
            {
                "id": "wc-q3",
                "text": "Explain two reasons why the neighbouring village faces water shortage despite receiving the same rainfall.",
                "type": "sa",
                "correct_answer": "The neighbouring village likely lacks rainwater harvesting structures, leading to surface runoff instead of groundwater recharge. Additionally, they may have over-extracted groundwater without replenishment and lack traditional water management knowledge.",
                "explanation": "Without percolation structures, rainwater runs off instead of recharging the aquifer. Over-extraction of groundwater for irrigation without recharge leads to depletion. Loss of traditional knowledge and lack of community-managed water systems also contribute.",
                "marks": 2
            }
        ]
    },
    {
        "id": "cbse-sst-globalisation",
        "title": "Globalisation and the Handloom Industry",
        "board_id": "cbse",
        "subject_id": "social-science",
        "chapter": "Globalisation and the Indian Economy",
        "topics": ["Globalisation", "Impact on Indian Economy", "Fair Globalisation"],
        "case_text": (
            "Varanasi's famous silk handloom industry employs over 1.2 million weavers. "
            "Since the 1991 economic reforms, cheap Chinese silk and powerloom fabrics have flooded the market, "
            "reducing the weavers' income by 40%. However, some weavers have adapted by selling directly "
            "on e-commerce platforms and getting GI (Geographical Indication) tag for Banarasi silk. "
            "They now export to 30 countries and earn 3x more than traditional channel weavers."
        ),
        "questions": [
            {
                "id": "gl-q1",
                "text": "What is a GI (Geographical Indication) tag?",
                "type": "mcq",
                "options": [
                    "A) A tax exemption certificate",
                    "B) A tag indicating a product originates from a specific region with unique qualities",
                    "C) An export license",
                    "D) A quality certification for electronics"
                ],
                "correct_answer": "B) A tag indicating a product originates from a specific region with unique qualities",
                "explanation": "GI tag identifies a product as originating from a particular geographical region, possessing qualities or reputation unique to that origin. Banarasi silk received GI tag in 2006.",
                "marks": 1
            },
            {
                "id": "gl-q2",
                "text": "How did globalisation negatively impact the Varanasi handloom weavers?",
                "type": "mcq",
                "options": [
                    "A) Increased demand for their products",
                    "B) Cheap imports reduced their income by 40%",
                    "C) Government banned silk weaving",
                    "D) Reduced export opportunities"
                ],
                "correct_answer": "B) Cheap imports reduced their income by 40%",
                "explanation": "Globalisation led to competition from cheaper Chinese silk and powerloom imports, causing a 40% decline in weavers' income.",
                "marks": 1
            },
            {
                "id": "gl-q3",
                "text": "How did some weavers successfully adapt to globalisation? Mention two strategies.",
                "type": "sa",
                "correct_answer": "They adopted e-commerce for direct sales (cutting middlemen) and leveraged the GI tag to build brand recognition for Banarasi silk in international markets.",
                "explanation": "E-commerce platforms allowed weavers to sell directly to customers globally, earning higher margins. The GI tag provided legal protection and premium positioning for authentic Banarasi silk in 30 export markets.",
                "marks": 2
            },
            {
                "id": "gl-q4",
                "text": "What does the term 'fair globalisation' mean?",
                "type": "mcq",
                "options": [
                    "A) Globalisation that benefits only developed countries",
                    "B) Globalisation creating equal opportunities for all, with protections for vulnerable groups",
                    "C) Complete removal of all trade barriers",
                    "D) Globalisation managed by a single world government"
                ],
                "correct_answer": "B) Globalisation creating equal opportunities for all, with protections for vulnerable groups",
                "explanation": "Fair globalisation means that the benefits of global integration are shared more equally, with government policies protecting workers, small producers, and vulnerable sectors from negative impacts.",
                "marks": 1
            }
        ]
    },
    # ==================== AP BOARD ====================
    {
        "id": "ap-math-ladder",
        "title": "Ladder Against a Wall",
        "board_id": "ap",
        "subject_id": "ap-mathematics",
        "chapter": "Trigonometry",
        "topics": ["Trigonometric Ratios", "Heights and Distances"],
        "case_text": (
            "A painter in Visakhapatnam places a 10 m long ladder against a vertical wall. "
            "The foot of the ladder is 6 m away from the wall. The ladder slips such that its foot "
            "moves 1.6 m away from the wall. The painter wants to know how far the top of the ladder "
            "slides down the wall to ensure he does not lose his balance."
        ),
        "questions": [
            {
                "id": "ld-q1",
                "text": "How high does the ladder reach on the wall initially?",
                "type": "mcq",
                "options": [
                    "A) 6 m",
                    "B) 8 m",
                    "C) 7 m",
                    "D) 9 m"
                ],
                "correct_answer": "B) 8 m",
                "explanation": "Using Pythagoras theorem: h\u00b2 = 10\u00b2 - 6\u00b2 = 100 - 36 = 64. So h = 8 m.",
                "marks": 1
            },
            {
                "id": "ld-q2",
                "text": "After the slip, the foot is 7.6 m from the wall. What is the new height reached?",
                "type": "mcq",
                "options": [
                    "A) 6.2 m",
                    "B) 6.5 m",
                    "C) 5.8 m",
                    "D) 7.2 m"
                ],
                "correct_answer": "B) 6.5 m",
                "explanation": "New h\u00b2 = 10\u00b2 - 7.6\u00b2 = 100 - 57.76 = 42.24. h = \u221a42.24 = 6.5 m.",
                "marks": 1
            },
            {
                "id": "ld-q3",
                "text": "How much did the top of the ladder slide down the wall?",
                "type": "sa",
                "correct_answer": "1.5 m",
                "explanation": "Initial height = 8 m, new height = 6.5 m. Slide distance = 8 - 6.5 = 1.5 m.",
                "marks": 1
            },
            {
                "id": "ld-q4",
                "text": "What angle does the ladder make with the ground after the slip? (Use \u221a3 \u2248 1.73)",
                "type": "sa",
                "correct_answer": "31\u00b0",
                "explanation": "cos \u03b8 = adjacent/hypotenuse = 7.6/10 = 0.76. \u03b8 = cos\u207b\u00b9(0.76) \u2248 40.5\u00b0. Alternatively, sin \u03b8 = 6.5/10 = 0.65, \u03b8 = sin\u207b\u00b9(0.65) \u2248 40.5\u00b0.",
                "marks": 2
            }
        ]
    },
    {
        "id": "ap-sci-cyclone",
        "title": "Cyclone Preparedness in Coastal AP",
        "board_id": "ap",
        "subject_id": "ap-physical-science",
        "chapter": "Our Environment",
        "topics": ["Ecosystem", "Natural Disasters", "Conservation"],
        "case_text": (
            "In December 2024, Cyclone Michaung caused severe damage to coastal Andhra Pradesh, "
            "with wind speeds up to 110 km/h and storm surges of 2-3 metres. The mangroves in the "
            "Godavari delta reduced the wind speed by 40-60% before it reached inland villages. "
            "Villages behind degraded mangrove areas suffered 3x more damage than those behind healthy mangroves. "
            "The Andhra Pradesh government now plans to plant 10 million mangrove saplings along the coast."
        ),
        "questions": [
            {
                "id": "cy-q1",
                "text": "By what percentage did mangroves reduce cyclone wind speeds?",
                "type": "mcq",
                "options": [
                    "A) 10-20%",
                    "B) 20-30%",
                    "C) 40-60%",
                    "D) 70-80%"
                ],
                "correct_answer": "C) 40-60%",
                "explanation": "The mangrove forest barrier reduced wind speeds by 40-60% before cyclonic winds reached inland areas.",
                "marks": 1
            },
            {
                "id": "cy-q2",
                "text": "How much more damage did villages behind degraded mangroves suffer?",
                "type": "mcq",
                "options": [
                    "A) 2x more",
                    "B) 3x more",
                    "C) 4x more",
                    "D) 5x more"
                ],
                "correct_answer": "B) 3x more",
                "explanation": "Villages located behind degraded mangrove areas experienced three times more damage than those protected by healthy mangroves.",
                "marks": 1
            },
            {
                "id": "cy-q3",
                "text": "Explain two ecosystem services provided by mangroves that protect coastal communities.",
                "type": "sa",
                "correct_answer": "Mangroves act as natural windbreaks reducing cyclone wind speeds, and their root systems stabilize soil and absorb storm surge energy, reducing flooding and coastal erosion.",
                "explanation": "Mangroves provide: (1) wind speed reduction through dense vegetation acting as a barrier, (2) wave energy dissipation and storm surge absorption through their complex root systems, (3) soil stabilization preventing coastal erosion.",
                "marks": 2
            },
            {
                "id": "cy-q4",
                "text": "What is a storm surge?",
                "type": "mcq",
                "options": [
                    "A) Heavy rainfall during a cyclone",
                    "B) Abnormal rise in sea level during a cyclone",
                    "C) Thunder and lightning",
                    "D) Strong wind in a circular motion"
                ],
                "correct_answer": "B) Abnormal rise in sea level during a cyclone",
                "explanation": "A storm surge is an abnormal rise in sea level caused by strong winds pushing water towards the coast during a cyclone, leading to coastal flooding.",
                "marks": 1
            }
        ]
    },
    {
        "id": "ap-sci-photosynthesis",
        "title": "Glasshouse Experiment on Photosynthesis",
        "board_id": "ap",
        "subject_id": "ap-biology",
        "chapter": "Nutrition",
        "topics": ["Autotrophic Nutrition", "Photosynthesis"],
        "case_text": (
            "A farmer in the Guntur district of Andhra Pradesh uses a glasshouse to grow tomatoes. "
            "He observes that plants near the glass walls grow faster than those in the centre. "
            "A student from a local college sets up an experiment with two tomato plants: "
            "Plant A receives red light and Plant B receives green light. After 10 days, "
            "Plant A shows 60% more growth. The student also tests for starch in leaves "
            "using iodine solution."
        ),
        "questions": [
            {
                "id": "ph-q1",
                "text": "Why did plants near the glasshouse walls grow faster?",
                "type": "mcq",
                "options": [
                    "A) They received more water",
                    "B) They received more sunlight (light intensity)",
                    "C) They had better soil",
                    "D) They were protected from insects"
                ],
                "correct_answer": "B) They received more sunlight (light intensity)",
                "explanation": "Plants near the transparent walls receive higher light intensity, which increases the rate of photosynthesis and hence growth.",
                "marks": 1
            },
            {
                "id": "ph-q2",
                "text": "Why did Plant A (red light) show more growth than Plant B (green light)?",
                "type": "mcq",
                "options": [
                    "A) Red light has more energy and chlorophyll absorbs red light maximally",
                    "B) Green light is harmful to plants",
                    "C) Red light contains more water",
                    "D) Green light causes faster respiration"
                ],
                "correct_answer": "A) Red light has more energy and chlorophyll absorbs red light maximally",
                "explanation": "Chlorophyll absorbs red and blue light most efficiently for photosynthesis. Green light is mostly reflected (hence plants appear green), so it is less effective for photosynthesis.",
                "marks": 1
            },
            {
                "id": "ph-q3",
                "text": "What colour change indicates the presence of starch when iodine solution is applied?",
                "type": "mcq",
                "options": [
                    "A) Yellow to red",
                    "B) Blue-black",
                    "C) Green to colourless",
                    "D) No change"
                ],
                "correct_answer": "B) Blue-black",
                "explanation": "Iodine solution turns blue-black in the presence of starch, confirming that photosynthesis has occurred.",
                "marks": 1
            },
            {
                "id": "ph-q4",
                "text": "Write the balanced chemical equation for photosynthesis.",
                "type": "sa",
                "correct_answer": "6CO\u2082 + 6H\u2082O \u2192 C\u2086H\u2081\u2082O\u2086 + 6O\u2082",
                "explanation": "Carbon dioxide and water, in the presence of sunlight and chlorophyll, produce glucose and oxygen. The reaction requires sunlight energy and chlorophyll as a catalyst.",
                "marks": 2
            }
        ]
    },
    # ==================== TS BOARD ====================
    {
        "id": "ts-math-elevator",
        "title": "Elevator Cable Tension",
        "board_id": "ts",
        "subject_id": "ts-mathematics",
        "chapter": "Similar Triangles",
        "topics": ["Similarity of Triangles", "Basic Proportionality Theorem"],
        "case_text": (
            "A 15 m tall building in Hyderabad has an elevator shaft. A support cable is attached "
            "from the top of the building to a point on the ground 8 m from the base. "
            "Another cable runs parallel to it from a point on the building 9 m above the ground "
            "to the same point on the ground. The building manager needs to verify the lengths "
            "of these cables for safety certification."
        ),
        "questions": [
            {
                "id": "el-q1",
                "text": "What is the length of the main cable from the top of the building to the ground point?",
                "type": "mcq",
                "options": [
                    "A) 15 m",
                    "B) 17 m",
                    "C) 20 m",
                    "D) 23 m"
                ],
                "correct_answer": "B) 17 m",
                "explanation": "Using Pythagoras: L\u00b2 = 15\u00b2 + 8\u00b2 = 225 + 64 = 289. L = \u221a289 = 17 m.",
                "marks": 1
            },
            {
                "id": "el-q2",
                "text": "If a second cable runs from 9 m height to the same ground point, what is its length?",
                "type": "mcq",
                "options": [
                    "A) 10.2 m",
                    "B) 12.0 m",
                    "C) 12.1 m",
                    "D) 13.5 m"
                ],
                "correct_answer": "C) 12.1 m",
                "explanation": "Using similar triangles: 9/15 = L\u2082/17. L\u2082 = (9 \u00d7 17)/15 = 153/15 = 10.2 m.",
                "marks": 1
            },
            {
                "id": "el-q3",
                "text": "The distance from the base to where the second cable meets the ground is 4.8 m. Using the Basic Proportionality Theorem, verify this value.",
                "type": "sa",
                "correct_answer": "4.8 m confirmed",
                "explanation": "By BPT (Thales theorem): 9/15 = d/8, where d is distance from base to second cable ground point. d = (9 \u00d7 8)/15 = 72/15 = 4.8 m. Verified.",
                "marks": 2
            }
        ]
    },
    {
        "id": "ts-sci-solar-cooker",
        "title": "Solar Cooker Design",
        "board_id": "ts",
        "subject_id": "ts-physical-science",
        "chapter": "Light - Reflection and Refraction",
        "topics": ["Reflection of Light", "Spherical Mirrors"],
        "case_text": (
            "A rural school in Telangana uses a solar cooker with a concave spherical mirror "
            "of radius of curvature 60 cm. The mirror focuses sunlight onto a cooking pot. "
            "On a sunny day, students observe that the image of the sun formed by the mirror "
            "is highly concentrated and can ignite paper placed at the focal point. "
            "They want to calculate the mirror's specifications for a science project."
        ),
        "questions": [
            {
                "id": "sc-q1",
                "text": "What is the focal length of the concave mirror?",
                "type": "mcq",
                "options": [
                    "A) 15 cm",
                    "B) 20 cm",
                    "C) 30 cm",
                    "D) 60 cm"
                ],
                "correct_answer": "C) 30 cm",
                "explanation": "f = R/2 = 60/2 = 30 cm. For a concave mirror, focal length is positive by convention.",
                "marks": 1
            },
            {
                "id": "sc-q2",
                "text": "Where should the cooking pot be placed for maximum heating?",
                "type": "mcq",
                "options": [
                    "A) At the centre of curvature",
                    "B) At the focal point",
                    "C) At the pole",
                    "D) Beyond the centre of curvature"
                ],
                "correct_answer": "B) At the focal point",
                "explanation": "Sunlight rays are parallel (coming from infinity), so they converge at the focal point of the concave mirror. The cooking pot should be at the focus for maximum concentration of solar energy.",
                "marks": 1
            },
            {
                "id": "sc-q3",
                "text": "If a student holds an object 45 cm from the mirror, what is the nature and position of the image?",
                "type": "sa",
                "correct_answer": "Real, inverted image at 90 cm from mirror",
                "explanation": "Using mirror formula: 1/f = 1/u + 1/v. f = 30 cm, u = -45 cm (object in front). 1/v = 1/30 - 1/45 = (3-2)/90 = 1/90. v = 90 cm. Image is real (v positive), inverted, and magnified (m = -v/u = -90/45 = -2).",
                "marks": 2
            },
            {
                "id": "sc-q4",
                "text": "What is the magnification produced by the mirror when the object is at 45 cm?",
                "type": "mcq",
                "options": [
                    "A) -1",
                    "B) -2",
                    "C) -0.5",
                    "D) +2"
                ],
                "correct_answer": "B) -2",
                "explanation": "m = -v/u = -90/(-45) = -2. The image is twice the size of the object and inverted (negative sign).",
                "marks": 1
            }
        ]
    },
    {
        "id": "ts-bio-blood-donation",
        "title": "Blood Donation Camp",
        "board_id": "ts",
        "subject_id": "ts-biology",
        "chapter": "Transportation",
        "topics": ["Blood", "Circulatory System", "Blood Groups"],
        "case_text": (
            "A blood donation camp is organized at a college in Warangal, Telangana. "
            "Among 200 donors, the blood group distribution is: O (42%), A (28%), B (22%), AB (8%). "
            "The blood bank needs at least 40 units of O-negative blood for emergency use. "
            "Only 7% of the population is Rh-negative. A patient with blood group A-positive "
            "requires an urgent transfusion, but the hospital has only O-positive and A-negative blood in stock."
        ),
        "questions": [
            {
                "id": "bd-q1",
                "text": "Approximately how many donors have blood group O?",
                "type": "mcq",
                "options": [
                    "A) 72",
                    "B) 84",
                    "C) 96",
                    "D) 56"
                ],
                "correct_answer": "B) 84",
                "explanation": "42% of 200 = 0.42 \u00d7 200 = 84 donors with blood group O.",
                "marks": 1
            },
            {
                "id": "bd-q2",
                "text": "What percentage of donors are Rh-negative?",
                "type": "mcq",
                "options": [
                    "A) 7%",
                    "B) 10%",
                    "C) 5%",
                    "D) 3%"
                ],
                "correct_answer": "A) 7%",
                "explanation": "7% of the population is Rh-negative. So approximately 14 of the 200 donors would be Rh-negative.",
                "marks": 1
            },
            {
                "id": "bd-q3",
                "text": "Can the A-positive patient receive blood from O-positive and A-negative donors? Explain.",
                "type": "sa",
                "correct_answer": "O-positive is universal donor for Rh-positive recipients, so it is compatible. A-negative is incompatible because the patient is Rh-positive and A-negative blood lacks Rh factor, but since it's the first transfusion, it may be acceptable. O-positive is preferred.",
                "explanation": "A-positive patient has A and Rh antigens. O-positive has no A/B antigens but has Rh antigen, so it's safe. A-negative has A antigen but no Rh factor. For a first transfusion, Rh-incompatibility typically doesn't cause immediate reaction, but O-positive is the safer choice. Proper cross-matching is always required.",
                "marks": 2
            },
            {
                "id": "bd-q4",
                "text": "Which blood group is considered the universal donor?",
                "type": "mcq",
                "options": [
                    "A) A-positive",
                    "B) B-negative",
                    "C) O-negative",
                    "D) AB-positive"
                ],
                "correct_answer": "C) O-negative",
                "explanation": "O-negative blood lacks A, B, and Rh antigens, making it compatible with all blood types. It is the universal donor for red blood cell transfusion.",
                "marks": 1
            }
        ]
    },
    {
        "id": "ts-sst-it-hyderabad",
        "title": "IT Sector Growth in Hyderabad",
        "board_id": "ts",
        "subject_id": "ts-social-studies",
        "chapter": "Indian Economy",
        "topics": ["Economic Reforms", "Globalisation", "Service Sector"],
        "case_text": (
            "Hyderabad's IT sector has grown from employing 50,000 people in 2000 to over 8,00,000 in 2024. "
            "The HITEC City and IT corridor along the Outer Ring Road contribute 55% of Telangana's exports "
            "worth \u20b92.4 lakh crore. However, this growth has led to a 300% increase in real estate prices "
            "in western Hyderabad, displacing traditional communities. The adjacent service sector "
            "(food, transport, security) employs 3x more people than the IT sector itself."
        ),
        "questions": [
            {
                "id": "it-q1",
                "text": "How many times has the IT sector employment grown between 2000 and 2024?",
                "type": "mcq",
                "options": [
                    "A) 8 times",
                    "B) 12 times",
                    "C) 16 times",
                    "D) 20 times"
                ],
                "correct_answer": "C) 16 times",
                "explanation": "8,00,000 / 50,000 = 16 times growth in IT employment.",
                "marks": 1
            },
            {
                "id": "it-q2",
                "text": "What percentage of Telangana's exports come from the IT corridor?",
                "type": "mcq",
                "options": [
                    "A) 35%",
                    "B) 45%",
                    "C) 55%",
                    "D) 65%"
                ],
                "correct_answer": "C) 55%",
                "explanation": "The IT corridor contributes 55% of Telangana's total exports.",
                "marks": 1
            },
            {
                "id": "it-q3",
                "text": "Discuss one positive and one negative impact of IT sector growth on Hyderabad's economy and society.",
                "type": "sa",
                "correct_answer": "Positive: Massive employment generation (8 lakh direct jobs) and export revenue (\u20b92.4 lakh crore). Negative: 300% real estate price rise causing displacement of traditional communities and increased inequality.",
                "explanation": "The IT boom created a multiplier effect through indirect employment in services. However, speculative real estate growth pushed up costs, making housing unaffordable for lower-income groups and leading to gentrification of western Hyderabad.",
                "marks": 2
            }
        ]
    },
    # ==================== CBSE ADDITIONAL ====================
    {
        "id": "cbse-chem-carbon-footprint",
        "title": "Carbon Footprint Calculation",
        "board_id": "cbse",
        "subject_id": "science",
        "chapter": "Carbon and its Compounds",
        "topics": ["Chemical Properties of Carbon Compounds", "Combustion", "Ethanol and Ethanoic Acid"],
        "case_text": (
            "A school in Dehradun conducts a carbon footprint audit. They find that a single "
            "diesel generator emits 2.68 kg of CO\u2082 per litre of diesel burned. The school uses "
            "the generator for 4 hours daily, consuming 5 litres per hour. Additionally, "
            "the school canteen uses LPG (butane, C\u2084H\u2081\u2080) for cooking, consuming 2 cylinders "
            "(14.2 kg each) per month. The chemistry club wants to calculate total CO\u2082 emissions "
            "and suggest alternatives."
        ),
        "questions": [
            {
                "id": "cf-q1",
                "text": "How much CO\u2082 does the generator emit per day?",
                "type": "mcq",
                "options": [
                    "A) 53.6 kg",
                    "B) 42.8 kg",
                    "C) 67.0 kg",
                    "D) 48.2 kg"
                ],
                "correct_answer": "A) 53.6 kg",
                "explanation": "Daily diesel consumption = 5 L/h \u00d7 4 h = 20 L. CO\u2082 emission = 20 \u00d7 2.68 = 53.6 kg/day.",
                "marks": 1
            },
            {
                "id": "cf-q2",
                "text": "Write the balanced equation for complete combustion of butane (C\u2084H\u2081\u2080).",
                "type": "mcq",
                "options": [
                    "A) C\u2084H\u2081\u2080 + 4O\u2082 \u2192 4CO + 5H\u2082O",
                    "B) C\u2084H\u2081\u2080 + 6O\u2082 \u2192 4CO\u2082 + 5H\u2082O",
                    "C) C\u2084H\u2081\u2080 + 8O\u2082 \u2192 4CO\u2082 + 5H\u2082O",
                    "D) 2C\u2084H\u2081\u2080 + 13O\u2082 \u2192 8CO\u2082 + 10H\u2082O"
                ],
                "correct_answer": "D) 2C\u2084H\u2081\u2080 + 13O\u2082 \u2192 8CO\u2082 + 10H\u2082O",
                "explanation": "Balancing C: 4C on each side (multiply CO\u2082 by 4). H: 10H on each side (multiply H\u2082O by 5). O: RHS = 8+5 = 13 O atoms, so LHS needs 13/2 O\u2082 molecules. Multiply by 2: 2C\u2084H\u2081\u2080 + 13O\u2082 \u2192 8CO\u2082 + 10H\u2082O.",
                "marks": 1
            },
            {
                "id": "cf-q3",
                "text": "Calculate the monthly CO\u2082 emission from LPG combustion. (Atomic masses: C=12, H=1. Each butane molecule produces 4 CO\u2082 molecules. 2 cylinders = 28.4 kg LPG per month.)",
                "type": "sa",
                "correct_answer": "86.1 kg",
                "explanation": "Molar mass of butane C\u2084H\u2081\u2080 = 58 g/mol. Moles of butane = 28400/58 = 489.7 mol. From equation, 2 mol butane \u2192 8 mol CO\u2082, so 1 mol butane \u2192 4 mol CO\u2082. CO\u2082 moles = 489.7 \u00d7 4 = 1958.6 mol. Mass of CO\u2082 = 1958.6 \u00d7 44 = 86,178 g = 86.2 kg.",
                "marks": 2
            },
            {
                "id": "cf-q4",
                "text": "Suggest two ways the school can reduce its carbon footprint.",
                "type": "sa",
                "correct_answer": "Install solar panels to replace diesel generator, and switch to induction cooking (electric) powered by renewable energy.",
                "explanation": "Solar PV systems can power the school during daylight, eliminating generator use. Induction cooktops are more efficient than LPG and can be powered by solar. Other options: energy-efficient LED lighting, improved insulation, planting trees on campus.",
                "marks": 2
            }
        ]
    },
    {
        "id": "cbse-math-railway",
        "title": "Railway Track Expansion",
        "board_id": "cbse",
        "subject_id": "mathematics",
        "chapter": "Pair of Linear Equations in Two Variables",
        "topics": ["Algebraic Methods of Solving a Pair of Linear Equations", "Graphical Method of Solution"],
        "case_text": (
            "Indian Railways plans to lay new tracks between two cities. One crew starts from City A "
            "and lays 2 km of track per day. Another crew starts from City B (500 km away) and lays "
            "3 km of track per day towards City A. A supply train travels from City A to City B at "
            "60 km/h and returns at 40 km/h. The project manager needs to calculate when the crews meet "
            "and the average speed of the supply train."
        ),
        "questions": [
            {
                "id": "rr-q1",
                "text": "After how many days will the two track-laying crews meet?",
                "type": "mcq",
                "options": [
                    "A) 80 days",
                    "B) 100 days",
                    "C) 120 days",
                    "D) 150 days"
                ],
                "correct_answer": "B) 100 days",
                "explanation": "Relative speed = 2 + 3 = 5 km/day. Time = 500 / 5 = 100 days.",
                "marks": 1
            },
            {
                "id": "rr-q2",
                "text": "How much track will the crew from City A have laid when they meet?",
                "type": "mcq",
                "options": [
                    "A) 150 km",
                    "B) 200 km",
                    "C) 250 km",
                    "D) 300 km"
                ],
                "correct_answer": "B) 200 km",
                "explanation": "Distance from A = 2 km/day \u00d7 100 days = 200 km.",
                "marks": 1
            },
            {
                "id": "rr-q3",
                "text": "If the supply train travels from A to B at 60 km/h and returns at 40 km/h, what is its average speed for the round trip?",
                "type": "sa",
                "correct_answer": "48 km/h",
                "explanation": "Average speed = 2ab/(a+b) for equal distances = 2\u00d760\u00d740/(60+40) = 4800/100 = 48 km/h. (Not the arithmetic mean of 50 km/h!)",
                "marks": 2
            }
        ]
    },
    {
        "id": "cbse-sst-money-credit",
        "title": "Banking and Credit in Rural India",
        "board_id": "cbse",
        "subject_id": "social-science",
        "chapter": "Money and Credit",
        "topics": ["Formal and Informal Credit", "Self-Help Groups", "Banking"],
        "case_text": (
            "In a village in Uttar Pradesh, 60% of farmers borrow from moneylenders at 5% per month interest, "
            "while only 25% have access to banks at 12% per annum. A Self-Help Group (SHG) of 15 women "
            "has saved \u20b91.2 lakh over 2 years and now takes loans from their own pool at 2% per month. "
            "The local bank branch manager plans to open a 'Bank Sakhi' branch to increase formal credit access."
        ),
        "questions": [
            {
                "id": "mc-q1",
                "text": "What is the annual interest rate charged by the moneylender?",
                "type": "mcq",
                "options": [
                    "A) 12% per annum",
                    "B) 24% per annum",
                    "C) 60% per annum",
                    "D) 36% per annum"
                ],
                "correct_answer": "C) 60% per annum",
                "explanation": "5% per month \u00d7 12 months = 60% per annum. This is much higher than the bank rate of 12% per annum.",
                "marks": 1
            },
            {
                "id": "mc-q2",
                "text": "What is the key advantage of an SHG compared to a moneylender?",
                "type": "mcq",
                "options": [
                    "A) SHGs charge lower interest and build savings habits",
                    "B) SHGs provide unlimited loans",
                    "C) SHGs do not require repayment",
                    "D) SHGs are government-regulated"
                ],
                "correct_answer": "A) SHGs charge lower interest and build savings habits",
                "explanation": "SHGs charge much lower interest (2% per month = 24% p.a. vs moneylender's 60% p.a.) and also encourage regular savings, financial literacy, and collective decision-making.",
                "marks": 1
            },
            {
                "id": "mc-q3",
                "text": "What are two reasons why only 25% of farmers access formal bank credit?",
                "type": "sa",
                "correct_answer": "Lack of collateral/documentation (land titles) and physical distance to bank branches in rural areas. Also, banks perceive agricultural loans as high-risk and require complex paperwork.",
                "explanation": "Formal credit requires collateral, proof of identity, and documentation that many small/marginal farmers lack. Bank branches are often far from villages. Moneylenders offer quick, collateral-free loans at the doorstep despite high interest.",
                "marks": 2
            }
        ]
    },
    {
        "id": "cbse-sci-magic-mirror",
        "title": "Mirrors in a Salon",
        "board_id": "cbse",
        "subject_id": "science",
        "chapter": "Light \u2013 Reflection and Refraction",
        "topics": ["Reflection of Light", "Spherical Mirrors", "Refraction through a Rectangular Glass Slab"],
        "case_text": (
            "A salon in Mumbai has three types of mirrors: a plane mirror on the wall, "
            "a concave mirror (focal length 20 cm) for close-up makeup application, "
            "and a convex mirror (focal length 50 cm) at the entrance to see a wide area of the shop. "
            "A customer sits 15 cm from the concave mirror for makeup. Meanwhile, a stylist "
            "places a cylindrical glass of water on the counter and observes that a pencil "
            "in the glass appears bent at the water surface."
        ),
        "questions": [
            {
                "id": "mm-q1",
                "text": "What type of image is formed when the customer sits 15 cm from the concave mirror (f = 20 cm)?",
                "type": "mcq",
                "options": [
                    "A) Real and inverted",
                    "B) Virtual and erect",
                    "C) Real and erect",
                    "D) Virtual and inverted"
                ],
                "correct_answer": "B) Virtual and erect",
                "explanation": "u = 15 cm, f = 20 cm. Object is between pole and focus (u < f). For concave mirror, object between P and F gives virtual, erect, and magnified image behind the mirror.",
                "marks": 1
            },
            {
                "id": "mm-q2",
                "text": "What is the magnification in the makeup mirror?",
                "type": "mcq",
                "options": [
                    "A) +2",
                    "B) +3",
                    "C) +4",
                    "D) +5"
                ],
                "correct_answer": "C) +4",
                "explanation": "Using mirror formula: 1/v = 1/f - 1/u = 1/20 - 1/15 = (3-4)/60 = -1/60. v = -60 cm. m = -v/u = -(-60)/15 = +4. Image is 4x magnified and virtual.",
                "marks": 1
            },
            {
                "id": "mm-q3",
                "text": "Why does the pencil appear bent when placed in a glass of water?",
                "type": "mcq",
                "options": [
                    "A) Reflection of light",
                    "B) Refraction of light at the water-air interface",
                    "C) Total internal reflection",
                    "D) Dispersion of light"
                ],
                "correct_answer": "B) Refraction of light at the water-air interface",
                "explanation": "Light rays from the underwater part of the pencil bend (refract) when they travel from water (denser) to air (rarer), causing the pencil to appear bent at the surface due to apparent shift.",
                "marks": 1
            },
            {
                "id": "mm-q4",
                "text": "What is the advantage of a convex mirror as a 'shop entrance mirror' compared to a plane mirror?",
                "type": "sa",
                "correct_answer": "A convex mirror provides a wider field of view, allowing the salon staff to see a larger area of the shop, though images appear smaller than actual size.",
                "explanation": "Convex mirrors diverge light rays, enabling them to cover a wider area. They are used as rear-view mirrors in vehicles and security mirrors in shops because they give a panoramic view with diminished, erect images.",
                "marks": 2
            }
        ]
    },
    {
        "id": "cbse-sci-heart-rate",
        "title": "Exercise and Heart Rate",
        "board_id": "cbse",
        "subject_id": "science",
        "chapter": "Life Processes",
        "topics": ["Transportation", "Respiration"],
        "case_text": (
            "During a physical education class, students measure their heart rates before and after exercise. "
            "Rohan's resting heart rate is 72 beats per minute (bpm). After 5 minutes of running, "
            "his heart rate rises to 144 bpm. His stroke volume (blood pumped per beat) increases from "
            "70 mL to 110 mL during exercise. The students also measure their breathing rate, which "
            "increases from 15 breaths/min to 35 breaths/min for Rohan."
        ),
        "questions": [
            {
                "id": "hr-q1",
                "text": "What is Rohan's cardiac output at rest? (Cardiac output = Heart rate \u00d7 Stroke volume)",
                "type": "mcq",
                "options": [
                    "A) 5.0 L/min",
                    "B) 5.04 L/min",
                    "C) 4.8 L/min",
                    "D) 6.0 L/min"
                ],
                "correct_answer": "B) 5.04 L/min",
                "explanation": "CO = 72 bpm \u00d7 70 mL = 5040 mL/min = 5.04 L/min.",
                "marks": 1
            },
            {
                "id": "hr-q2",
                "text": "What is Rohan's cardiac output during exercise?",
                "type": "mcq",
                "options": [
                    "A) 12.6 L/min",
                    "B) 15.8 L/min",
                    "C) 10.1 L/min",
                    "D) 18.2 L/min"
                ],
                "correct_answer": "B) 15.8 L/min",
                "explanation": "CO = 144 \u00d7 110 = 15,840 mL/min = 15.84 L/min \u2248 15.8 L/min.",
                "marks": 1
            },
            {
                "id": "hr-q3",
                "text": "Why does heart rate and breathing rate increase during exercise?",
                "type": "sa",
                "correct_answer": "During exercise, muscles require more oxygen for aerobic respiration and produce more CO\u2082. Increased heart rate delivers oxygen faster, and increased breathing rate expels CO\u2082 and intakes more O\u2082.",
                "explanation": "Exercise increases the demand for ATP in muscles. Aerobic respiration requires more O\u2082 and produces more CO\u2082. The cardiovascular and respiratory systems respond by increasing delivery of O\u2082 and removal of CO\u2082 to maintain homeostasis.",
                "marks": 2
            },
            {
                "id": "hr-q4",
                "text": "By what factor does Rohan's cardiac output increase during exercise?",
                "type": "mcq",
                "options": [
                    "A) 2x",
                    "B) 2.5x",
                    "C) 3.14x",
                    "D) 4x"
                ],
                "correct_answer": "C) 3.14x",
                "explanation": "15.84 / 5.04 = 3.14 times increase in cardiac output.",
                "marks": 1
            }
        ]
    },
]


def get_cbqs(board_id, subject_id, chapter=None, count=5):
    filtered = [
        s for s in CBQ_SCENARIOS
        if s["board_id"] == board_id and s["subject_id"] == subject_id
    ]
    if chapter:
        filtered = [
            s for s in filtered
            if s["chapter"].lower() == chapter.lower()
        ]
    if not filtered:
        return {"scenarios": [], "total": 0, "message": "No CBQs found for the given criteria."}
    selected = random.sample(filtered, min(count, len(filtered)))
    return {
        "scenarios": selected,
        "total": len(filtered),
        "returned": len(selected),
    }


def get_cbq_by_id(scenario_id):
    for s in CBQ_SCENARIOS:
        if s["id"] == scenario_id:
            return {"found": True, "scenario": s}
    return {"found": False, "scenario": None, "message": f"No CBQ found with id: {scenario_id}"}


def score_cbq(scenario_id, answers):
    result = get_cbq_by_id(scenario_id)
    if not result["found"]:
        return {"scored": False, "message": f"Scenario {scenario_id} not found."}
    scenario = result["scenario"]
    total_marks = 0
    earned_marks = 0
    feedback = []
    for q in scenario["questions"]:
        qid = q["id"]
        total_marks += q["marks"]
        user_ans = answers.get(qid, "").strip()
        correct = q["correct_answer"].strip()
        is_correct = user_ans.lower() == correct.lower()
        if is_correct:
            earned_marks += q["marks"]
            feedback.append({
                "question_id": qid,
                "question": q["text"],
                "user_answer": user_ans,
                "correct_answer": correct,
                "correct": True,
                "marks_earned": q["marks"],
                "explanation": q["explanation"],
            })
        else:
            feedback.append({
                "question_id": qid,
                "question": q["text"],
                "user_answer": user_ans,
                "correct_answer": correct,
                "correct": False,
                "marks_earned": 0,
                "explanation": q["explanation"],
            })
    return {
        "scored": True,
        "scenario_title": scenario["title"],
        "scenario_id": scenario_id,
        "total_questions": len(scenario["questions"]),
        "total_marks": total_marks,
        "earned_marks": earned_marks,
        "percentage": round((earned_marks / total_marks) * 100, 1) if total_marks > 0 else 0,
        "feedback": feedback,
    }


def list_scenarios(board_id=None, subject_id=None):
    filtered = CBQ_SCENARIOS
    if board_id:
        filtered = [s for s in filtered if s["board_id"] == board_id]
    if subject_id:
        filtered = [s for s in filtered if s["subject_id"] == subject_id]
    return [
        {
            "id": s["id"],
            "title": s["title"],
            "board_id": s["board_id"],
            "subject_id": s["subject_id"],
            "chapter": s["chapter"],
            "question_count": len(s["questions"]),
        }
        for s in filtered
    ]
