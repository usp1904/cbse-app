NCERT_BASE = "https://ncert.nic.in/textbook.php"

SUBJECTS = [
    {
        "id": "mathematics",
        "name": "Mathematics",
        "code": "jemh1",
        "textbook_code": "jemh1",
        "publisher": "NCERT",
        "board": "cbse",
        "description": "Mathematics Textbook for Class X",
        "ncert_url": "https://ncert.nic.in/textbook.php?jemh1=0-7",
        "chapters": [
            {"num": 1, "title": "Real Numbers", "topics": ["Euclid's Division Lemma", "Fundamental Theorem of Arithmetic", "Revisiting Irrational Numbers", "Revisiting Rational Numbers and their Decimal Expansions"]},
            {"num": 2, "title": "Polynomials", "topics": ["Geometrical Meaning of Zeroes of Polynomials", "Relationship between Zeroes and Coefficients", "Division Algorithm for Polynomials"]},
            {"num": 3, "title": "Pair of Linear Equations in Two Variables", "topics": ["Graphical Method of Solution", "Algebraic Methods of Solving a Pair of Linear Equations", "Equations Reducible to a Pair of Linear Equations in Two Variables"]},
            {"num": 4, "title": "Quadratic Equations", "topics": ["Solution of a Quadratic Equation by Factorisation", "Solution of a Quadratic Equation by Completing the Square", "Nature of Roots"]},
            {"num": 5, "title": "Arithmetic Progressions", "topics": ["Arithmetic Progressions", "nth Term of an AP", "Sum of First n Terms of an AP"]},
            {"num": 6, "title": "Triangles", "topics": ["Similar Figures", "Similarity of Triangles", "Criteria for Similarity of Triangles", "Areas of Similar Triangles", "Pythagoras Theorem"]},
            {"num": 7, "title": "Coordinate Geometry", "topics": ["Distance Formula", "Section Formula", "Area of a Triangle"]},
            {"num": 8, "title": "Introduction to Trigonometry", "topics": ["Trigonometric Ratios", "Trigonometric Ratios of Some Specific Angles", "Trigonometric Ratios of Complementary Angles", "Trigonometric Identities"]},
            {"num": 9, "title": "Some Applications of Trigonometry", "topics": ["Heights and Distances"]},
            {"num": 10, "title": "Circles", "topics": ["Tangent to a Circle", "Number of Tangents from a Point on a Circle"]},
            {"num": 11, "title": "Constructions", "topics": ["Division of a Line Segment", "Construction of Tangents to a Circle"]},
            {"num": 12, "title": "Areas Related to Circles", "topics": ["Perimeter and Area of a Circle", "Areas of Sector and Segment of a Circle", "Areas of Combinations of Plane Figures"]},
            {"num": 13, "title": "Surface Areas and Volumes", "topics": ["Surface Area of a Combination of Solids", "Volume of a Combination of Solids", "Conversion of Solid from One Shape to Another", "Frustum of a Cone"]},
            {"num": 14, "title": "Statistics", "topics": ["Mean of Grouped Data", "Mode of Grouped Data", "Median of Grouped Data", "Graphical Representation of Cumulative Frequency Distribution"]},
            {"num": 15, "title": "Probability", "topics": ["Probability - A Theoretical Approach"]},
        ]
    },
    {
        "id": "science",
        "name": "Science",
        "code": "jesc1",
        "publisher": "NCERT",
        "board": "cbse",
        "description": "Science Textbook for Class X",
        "ncert_url": "https://ncert.nic.in/textbook.php?jesc1=0-7",
        "chapters": [
            {"num": 1, "title": "Chemical Reactions and Equations", "topics": ["Chemical Equations", "Types of Chemical Reactions", "Oxidation and Reduction Reactions"]},
            {"num": 2, "title": "Acids, Bases and Salts", "topics": ["Understanding the Chemical Properties of Acids and Bases", "Properties of Acids and Bases", "Reactions of Acids and Bases with each other", "Importance of pH in Everyday Life", "More about Salts"]},
            {"num": 3, "title": "Metals and Non-metals", "topics": ["Physical Properties of Metals and Non-metals", "Chemical Properties of Metals", "How do Metals and Non-metals React?", "Occurrence of Metals", "Corrosion"]},
            {"num": 4, "title": "Carbon and its Compounds", "topics": ["Bonding in Carbon - The Covalent Bond", "Versatile Nature of Carbon", "Chemical Properties of Carbon Compounds", "Some Important Carbon Compounds - Ethanol and Ethanoic Acid", "Soaps and Detergents"]},
            {"num": 5, "title": "Life Processes", "topics": ["Nutrition", "Respiration", "Transportation", "Excretion"]},
            {"num": 6, "title": "Control and Coordination", "topics": ["Animals - Nervous System", "Coordination in Plants", "Hormones in Animals"]},
            {"num": 7, "title": "How do Organisms Reproduce?", "topics": ["Asexual Reproduction", "Sexual Reproduction", "Reproduction in Human Beings"]},
            {"num": 8, "title": "Heredity and Evolution", "topics": ["Heredity", "Accumulation of Variation during Reproduction", "Evolution", "Speciation", "Evolution and Classification", "Evolution should not be equated with Progress"]},
            {"num": 9, "title": "Light \u2013 Reflection and Refraction", "topics": ["Reflection of Light", "Spherical Mirrors", "Refraction of Light", "Refraction through a Rectangular Glass Slab", "Refractive Index", "Refraction by Spherical Lenses"]},
            {"num": 10, "title": "The Human Eye and the Colourful World", "topics": ["The Human Eye", "Defects of Vision and their Correction", "Refraction of Light through a Prism", "Dispersion of White Light by a Glass Prism", "Atmospheric Refraction", "Scattering of Light"]},
            {"num": 11, "title": "Electricity", "topics": ["Electric Current and Circuit", "Electric Potential and Potential Difference", "Ohm's Law", "Factors on which the Resistance of a Conductor depends", "Resistors in Series and Parallel", "Heating Effect of Electric Current", "Power"]},
            {"num": 12, "title": "Magnetic Effects of Electric Current", "topics": ["Magnetic Field and Field Lines", "Magnetic Field due to a Current-Carrying Conductor", "Force on a Current-Carrying Conductor in a Magnetic Field", "Electric Motor", "Electromagnetic Induction", "Electric Generator"]},
            {"num": 13, "title": "Our Environment", "topics": ["Ecosystem and its Components", "Food Chains and Webs", "How do our Activities affect the Environment?"]},
        ]
    },
    {
        "id": "english",
        "name": "English",
        "code": "jenb1",
        "publisher": "NCERT",
        "board": "cbse",
        "description": "First Flight and Footprints without Feet",
        "ncert_url": "https://ncert.nic.in/textbook.php?jenb1=0-7",
        "books": [
            {
                "name": "First Flight",
                "code": "jenb1",
                "ncert_url": "https://ncert.nic.in/textbook.php?jenb1=0-7",
                "chapters": [
                    {"num": 1, "title": "A Letter to God", "type": "Prose", "author": "G.L. Fuentes"},
                    {"num": 2, "title": "Nelson Mandela: Long Walk to Freedom", "type": "Prose", "author": "Nelson Mandela"},
                    {"num": 3, "title": "Two Stories about Flying", "type": "Prose", "author": "Liam O' Flaherty / Frederick Forsyth"},
                    {"num": 4, "title": "From the Diary of Anne Frank", "type": "Prose", "author": "Anne Frank"},
                    {"num": 5, "title": "Glimpses of India", "type": "Prose", "author": "Arup Kumar Dutta / Lokesh Abrol / H.P.S. Ahluwalia"},
                    {"num": 6, "title": "Mijbil the Otter", "type": "Prose", "author": "Gavin Maxwell"},
                    {"num": 7, "title": "Madam Rides the Bus", "type": "Prose", "author": "Vallikkannan"},
                    {"num": 8, "title": "The Sermon at Benares", "type": "Prose", "author": "Betty Renshaw"},
                    {"num": 9, "title": "The Proposal", "type": "Play", "author": "Anton Chekhov"},
                ],
                "poems": [
                    {"num": 1, "title": "Dust of Snow", "poet": "Robert Frost"},
                    {"num": 2, "title": "Fire and Ice", "poet": "Robert Frost"},
                    {"num": 3, "title": "A Tiger in the Zoo", "poet": "Leslie Norris"},
                    {"num": 4, "title": "How to Tell Wild Animals", "poet": "Carolyn Wells"},
                    {"num": 5, "title": "The Ball Poem", "poet": "John Berryman"},
                    {"num": 6, "title": "Amanda!", "poet": "Robin Klein"},
                    {"num": 7, "title": "Animals", "poet": "Walt Whitman"},
                    {"num": 8, "title": "The Trees", "poet": "Adrienne Rich"},
                    {"num": 9, "title": "Fog", "poet": "Carl Sandburg"},
                    {"num": 10, "title": "The Tale of Custard the Dragon", "poet": "Ogden Nash"},
                    {"num": 11, "title": "For Anne Gregory", "poet": "W.B. Yeats"},
                ]
            },
            {
                "name": "Footprints without Feet",
                "code": "jenf1",
                "ncert_url": "https://ncert.nic.in/textbook.php?jenf1=0-7",
                "chapters": [
                    {"num": 1, "title": "A Triumph of Surgery", "author": "James Herriot"},
                    {"num": 2, "title": "The Thief's Story", "author": "Ruskin Bond"},
                    {"num": 3, "title": "The Midnight Visitor", "author": "Robert Arthur"},
                    {"num": 4, "title": "A Question of Trust", "author": "Victor Canning"},
                    {"num": 5, "title": "Footprints without Feet", "author": "H.G. Wells"},
                    {"num": 6, "title": "The Making of a Scientist", "author": "Robert W. Peterson"},
                    {"num": 7, "title": "The Necklace", "author": "Guy de Maupassant"},
                    {"num": 8, "title": "The Hack Driver", "author": "Sinclair Lewis"},
                    {"num": 9, "title": "Bholi", "author": "K.A. Abbas"},
                    {"num": 10, "title": "The Book That Saved the Earth", "author": "Claire Boiko"},
                ]
            }
        ]
    },
    {
        "id": "social-science",
        "name": "Social Science",
        "code": "jess1",
        "publisher": "NCERT",
        "board": "cbse",
        "description": "History, Geography, Political Science, Economics",
        "ncert_url": "https://ncert.nic.in/textbook.php?jess1=0-7",
        "books": [
            {
                "name": "India and the Contemporary World - II (History)",
                "code": "jess1",
                "ncert_url": "https://ncert.nic.in/textbook.php?jess1=0-7",
                "chapters": [
                    {"num": 1, "title": "The Rise of Nationalism in Europe"},
                    {"num": 2, "title": "Nationalism in India"},
                    {"num": 3, "title": "The Making of a Global World"},
                    {"num": 4, "title": "The Age of Industrialisation"},
                    {"num": 5, "title": "Print Culture and the Modern World"},
                ]
            },
            {
                "name": "Contemporary India - II (Geography)",
                "code": "jeso1",
                "ncert_url": "https://ncert.nic.in/textbook.php?jeso1=0-7",
                "chapters": [
                    {"num": 1, "title": "Resources and Development"},
                    {"num": 2, "title": "Forest and Wildlife Resources"},
                    {"num": 3, "title": "Water Resources"},
                    {"num": 4, "title": "Agriculture"},
                    {"num": 5, "title": "Minerals and Energy Resources"},
                    {"num": 6, "title": "Manufacturing Industries"},
                    {"num": 7, "title": "Lifelines of National Economy"},
                ]
            },
            {
                "name": "Democratic Politics - II (Political Science)",
                "code": "jess2",
                "ncert_url": "https://ncert.nic.in/textbook.php?jess2=0-7",
                "chapters": [
                    {"num": 1, "title": "Power-sharing"},
                    {"num": 2, "title": "Federalism"},
                    {"num": 3, "title": "Gender, Religion and Caste"},
                    {"num": 4, "title": "Political Parties"},
                    {"num": 5, "title": "Outcomes of Democracy"},
                    {"num": 6, "title": "Challenges to Democracy"},
                ]
            },
            {
                "name": "Understanding Economic Development (Economics)",
                "code": "jess3",
                "ncert_url": "https://ncert.nic.in/textbook.php?jess3=0-7",
                "chapters": [
                    {"num": 1, "title": "Development"},
                    {"num": 2, "title": "Sectors of the Indian Economy"},
                    {"num": 3, "title": "Money and Credit"},
                    {"num": 4, "title": "Globalisation and the Indian Economy"},
                    {"num": 5, "title": "Consumer Rights"},
                ]
            }
        ]
    },
    {
        "id": "hindi",
        "name": "Hindi - A",
        "code": "jhh1",
        "publisher": "NCERT",
        "board": "cbse",
        "description": "Hindi 'A' Course - Kshitij and Kritika",
        "ncert_url": "https://ncert.nic.in/textbook.php?jhh1=0-7",
        "books": [
            {
                "name": "Kshitij (क्षितिज)",
                "code": "jhh1",
                "ncert_url": "https://ncert.nic.in/textbook.php?jhh1=0-7",
                "chapters": [
                    {"num": 1, "title": "पद", "author": "सूरदास"},
                    {"num": 2, "title": "राम-लक्ष्मण-परशुराम संवाद", "author": "तुलसीदास"},
                    {"num": 3, "title": "आत्मकथ्य", "author": "जयशंकर प्रसाद"},
                    {"num": 4, "title": "पर्वत प्रदेश में पावस", "author": "सुमित्रानंदन पंत"},
                    {"num": 5, "title": "उत्साह और अट नहीं रही", "author": "सूर्यकांत त्रिपाठी 'निराला'"},
                    {"num": 6, "title": "यह दंतुरहित मुस्कान और फसल", "author": "नागार्जुन"},
                    {"num": 7, "title": "छाया मत छूना", "author": "सर्वेश्वर दयाल सक्सेना"},
                    {"num": 8, "title": "कन्यादान", "author": "रामधारी सिंह 'दिनकर'"},
                    {"num": 9, "title": "संगतकार", "author": "मंगलेश डबराल"},
                    {"num": 10, "title": "नौबतखाने में इबादत", "author": "यतींद्र मिश्र"},
                    {"num": 11, "title": "डायरी का एक पन्ना", "author": "सियारामशरण गुप्त"},
                    {"num": 12, "title": "दोहे", "author": "बिहारी, रहीम, जायसी, घनानंद"},
                ]
            },
            {
                "name": "Kritika (कृतिका)",
                "code": "jhh2",
                "ncert_url": "https://ncert.nic.in/textbook.php?jhh2=0-7",
                "chapters": [
                    {"num": 1, "title": "माता का अंचल", "author": "शिवपूजन सहाय"},
                    {"num": 2, "title": "जॉर्ज पंचम की नाक", "author": "विजय तेंडुलकर"},
                    {"num": 3, "title": "साना-साना हाथ जोड़ि", "author": "मधु कांकरिया"},
                    {"num": 4, "title": "एही ठैयाँ झुलनी हेरानी हो रामा!", "author": "अज्ञेय"},
                    {"num": 5, "title": "मैं क्यों लिखता हूँ?", "author": "गुलाब कोठारी"},
                ]
            }
        ]
    },
    {
        "id": "sanskrit",
        "name": "Sanskrit",
        "code": "jss1",
        "publisher": "NCERT",
        "board": "cbse",
        "description": "Shemushi - Sanskrit Textbook for Class X",
        "ncert_url": "https://ncert.nic.in/textbook.php?jss1=0-7",
        "chapters": [
            {"num": 1, "title": "शुचिपर्यावरणम्"},
            {"num": 2, "title": "गुणवती कन्या"},
            {"num": 3, "title": "शिशुलालनम्"},
            {"num": 4, "title": "व्यावहारिकी संस्कृतम्"},
            {"num": 5, "title": "जननी तुल्यवत्सला"},
            {"num": 6, "title": "सुभाषितानि"},
            {"num": 7, "title": "सौहार्दं प्रकृतिशोभा"},
            {"num": 8, "title": "विचित्रः साक्षी"},
            {"num": 9, "title": "सूक्तयः"},
            {"num": 10, "title": "अन्योक्तयः"},
            {"num": 11, "title": "प्राणेभ्योपि प्रियः सुहृद्"},
            {"num": 12, "title": "अन्योऽपि समानः"},
        ]
    },
    {
        "id": "french",
        "name": "French",
        "code": "jef1",
        "publisher": "NCERT",
        "board": "cbse",
        "description": "French (Entre Jeunes) - Textbook for Class X",
        "chapters": [
            {"num": 1, "title": "Retrouvons nos amis", "topics": ["Les verbes", "Les articles", "Le vocabulaire"]},
            {"num": 2, "title": "Après le bac", "topics": ["Le futur simple", "Les métiers", "Les études"]},
            {"num": 3, "title": "On recherche un(e) correspondant(e)", "topics": ["Les adjectifs", "La description", "Les loisirs"]},
            {"num": 4, "title": "Les médias", "topics": ["Les médias et la communication", "L'opinion", "Le subjonctif"]},
            {"num": 5, "title": "Les voyages", "topics": ["Le vocabulaire du voyage", "Les moyens de transport", "Le passé composé"]},
            {"num": 6, "title": "Diversité et inclusion", "topics": ["Les différences culturelles", "Le respect", "L'égalité"]},
            {"num": 7, "title": "Environnement et écologie", "topics": ["La protection de l'environnement", "Le recyclage", "Les gestes éco-responsables"]},
            {"num": 8, "title": "Science et technologie", "topics": ["Les découvertes scientifiques", "L'innovation", "Le conditionnel"]},
        ]
    },
    {
        "id": "ai",
        "name": "Artificial Intelligence",
        "code": "ai417",
        "publisher": "CBSE",
        "board": "cbse",
        "description": "Artificial Intelligence (Code 417) - Skill Subject",
        "chapters": [
            {"num": 1, "title": "Introduction to AI", "topics": ["What is AI", "Types of AI", "Applications of AI", "AI Ethics"]},
            {"num": 2, "title": "AI Project Cycle", "topics": ["Problem Scoping", "Data Acquisition", "Data Exploration", "Modelling", "Evaluation"]},
            {"num": 3, "title": "Neural Networks", "topics": ["Neurons and Layers", "Activation Functions", "Forward Propagation", "Backpropagation"]},
            {"num": 4, "title": "Computer Vision", "topics": ["Image Processing", "Object Detection", "Face Recognition", "Applications"]},
            {"num": 5, "title": "Natural Language Processing", "topics": ["Text Processing", "Sentiment Analysis", "Language Models", "Chatbots"]},
            {"num": 6, "title": "Data Science", "topics": ["Data Collection", "Data Visualization", "Statistics", "Decision Making"]},
            {"num": 7, "title": "Model Evaluation", "topics": ["Confusion Matrix", "Accuracy and Precision", "Recall and F1 Score", "Cross-validation"]},
            {"num": 8, "title": "AI in Society", "topics": ["Bias in AI", "Privacy Concerns", "AI and Jobs", "Responsible AI"]},
        ]
    },
    {
        "id": "it",
        "name": "Information Technology",
        "code": "it402",
        "publisher": "CBSE",
        "board": "cbse",
        "description": "Information Technology (Code 402) - Skill Subject",
        "chapters": [
            {"num": 1, "title": "Digital Documentation", "topics": ["Styles and Formatting", "Mail Merge", "Table of Contents", "Templates"]},
            {"num": 2, "title": "Electronic Spreadsheet", "topics": ["Cell Referencing", "Functions and Formulas", "Data Analysis", "Macros", "Linking Data"]},
            {"num": 3, "title": "Database Management System", "topics": ["Database Concepts", "Creating Tables", "Queries and Forms", "Reports"]},
            {"num": 4, "title": "Web Applications", "topics": ["Networking Fundamentals", "Internet and Web", "Instant Messaging", "Blogs and Forums"]},
            {"num": 5, "title": "Workplace Safety", "topics": ["Health and Safety", "Ergonomics", "Fire Safety", "Emergency Procedures"]},
            {"num": 6, "title": "Entrepreneurship", "topics": ["Entrepreneurial Skills", "Business Planning", "Marketing", "Financial Management"]},
            {"num": 7, "title": "Green Skills", "topics": ["Sustainable Development", "Green Economy", "Waste Management", "Water Conservation"]},
        ]
    },
]

AP_BOARD_SUBJECTS = [
    {
        "id": "ap-mathematics",
        "name": "Mathematics (AP Board)",
        "code": "ap",
        "board": "ap",
        "description": "Andhra Pradesh Board Class X Mathematics - based on APSCERT textbook",
        "chapters": [
            {"num": 1, "title": "Real Numbers", "topics": ["Euclid's Division Lemma", "Fundamental Theorem of Arithmetic", "Rational and Irrational Numbers", "Decimal Expansions"]},
            {"num": 2, "title": "Sets", "topics": ["Introduction to Sets", "Types of Sets", "Operations on Sets", "Venn Diagrams"]},
            {"num": 3, "title": "Polynomials", "topics": ["Value of a Polynomial", "Zeroes of a Polynomial", "Relationship between Zeroes and Coefficients", "Division Algorithm"]},
            {"num": 4, "title": "Pair of Linear Equations in Two Variables", "topics": ["Graphical Method", "Substitution Method", "Elimination Method", "Cross Multiplication Method"]},
            {"num": 5, "title": "Quadratic Equations", "topics": ["Standard Form of Quadratic Equation", "Factorisation Method", "Completing the Square", "Nature of Roots"]},
            {"num": 6, "title": "Progressions", "topics": ["Arithmetic Progressions", "nth Term of an AP", "Sum of n Terms of an AP", "Geometric Progressions"]},
            {"num": 7, "title": "Coordinate Geometry", "topics": ["Distance Formula", "Section Formula", "Area of Triangle", "Collinearity of Points"]},
            {"num": 8, "title": "Similar Triangles", "topics": ["Similar Figures", "Basic Proportionality Theorem", "Criteria for Similarity", "Areas of Similar Triangles"]},
            {"num": 9, "title": "Tangents and Secants to a Circle", "topics": ["Tangent to a Circle", "Number of Tangents", "Secant and Tangent Properties", "Construction of Tangents"]},
            {"num": 10, "title": "Mensuration", "topics": ["Surface Area of Solids", "Volume of Solids", "Conversion of Solids", "Combination of Solids"]},
            {"num": 11, "title": "Trigonometry", "topics": ["Trigonometric Ratios", "Trigonometric Identities", "Heights and Distances", "Complementary Angles"]},
            {"num": 12, "title": "Statistics", "topics": ["Mean of Grouped Data", "Mode of Grouped Data", "Median of Grouped Data", "Ogive Curves"]},
            {"num": 13, "title": "Probability", "topics": ["Theoretical Probability", "Complementary Events", "Sure and Impossible Events"]},
        ]
    },
    {
        "id": "ap-physical-science",
        "name": "Physical Science (AP Board)",
        "code": "ap",
        "board": "ap",
        "description": "Andhra Pradesh Board Class X Physical Science",
        "chapters": [
            {"num": 1, "title": "Chemical Reactions and Equations", "topics": ["Chemical Equations", "Types of Reactions", "Balancing Equations", "Redox Reactions"]},
            {"num": 2, "title": "Acids, Bases and Salts", "topics": ["Properties of Acids and Bases", "pH Scale", "Neutralisation", "Salts and their Uses"]},
            {"num": 3, "title": "Metals and Non-metals", "topics": ["Physical Properties", "Chemical Properties", "Reactivity Series", "Corrosion", "Alloys"]},
            {"num": 4, "title": "Carbon and its Compounds", "topics": ["Covalent Bonding", "Hydrocarbons", "Functional Groups", "Ethanol and Ethanoic Acid", "Soaps and Detergents"]},
            {"num": 5, "title": "Light - Reflection and Refraction", "topics": ["Reflection", "Spherical Mirrors", "Refraction", "Lenses", "Lens Formula"]},
            {"num": 6, "title": "Human Eye and Colourful World", "topics": ["Structure of Eye", "Defects of Vision", "Dispersion", "Scattering"]},
            {"num": 7, "title": "Electricity", "topics": ["Ohm's Law", "Resistance", "Series and Parallel", "Heating Effect", "Power"]},
            {"num": 8, "title": "Magnetic Effects of Electric Current", "topics": ["Magnetic Field", "Force on Conductor", "Motor", "Generator", "Induction"]},
            {"num": 9, "title": "Our Environment", "topics": ["Ecosystem", "Food Chains", "Ozone Depletion", "Waste Management"]},
        ]
    },
    {
        "id": "ap-biology",
        "name": "Biological Science (AP Board)",
        "code": "ap",
        "board": "ap",
        "description": "Andhra Pradesh Board Class X Biological Science",
        "chapters": [
            {"num": 1, "title": "Nutrition", "topics": ["Autotrophic Nutrition", "Heterotrophic Nutrition", "Photosynthesis", "Human Digestive System"]},
            {"num": 2, "title": "Respiration", "topics": ["Types of Respiration", "Human Respiratory System", "Transport of Gases", "Plant Respiration"]},
            {"num": 3, "title": "Transportation", "topics": ["Circulatory System", "Heart and Blood Vessels", "Lymphatic System", "Transport in Plants"]},
            {"num": 4, "title": "Excretion", "topics": ["Human Excretory System", "Kidney Function", "Dialysis", "Excretion in Plants"]},
            {"num": 5, "title": "Control and Coordination", "topics": ["Nervous System", "Brain", "Reflex Actions", "Hormones in Animals", "Plant Hormones"]},
            {"num": 6, "title": "Reproduction", "topics": ["Asexual Reproduction", "Sexual Reproduction in Plants", "Human Reproductive System", "Reproductive Health"]},
            {"num": 7, "title": "Heredity and Evolution", "topics": ["Mendelian Genetics", "DNA and Chromosomes", "Evolution", "Natural Selection"]},
            {"num": 8, "title": "Coordination in Life Processes", "topics": ["Homeostasis", "Feedback Mechanisms", "Behavioural Responses"]},
        ]
    },
    {
        "id": "ap-social-studies",
        "name": "Social Studies (AP Board)",
        "code": "ap",
        "board": "ap",
        "description": "Andhra Pradesh Board Class X Social Studies",
        "chapters": [
            {"num": 1, "title": "India: Relief Features", "topics": ["Physical Divisions", "Himalayas", "Peninsular Plateau", "Coastal Plains", "Islands"]},
            {"num": 2, "title": "Ideas of Development", "topics": ["Development Indicators", "HDI", "Sustainable Development"]},
            {"num": 3, "title": "Production and Employment", "topics": ["Sectors of Economy", "GDP", "Employment", "Organised and Unorganised Sector"]},
            {"num": 4, "title": "Climate of India", "topics": ["Monsoon", "Seasons", "Distribution of Rainfall", "Climate Regions"]},
            {"num": 5, "title": "Indian Rivers and Water Resources", "topics": ["River Systems", "Water Conservation", "Irrigation"]},
            {"num": 6, "title": "The People", "topics": ["Population Distribution", "Population Growth", "Migration", "Population Policy"]},
            {"num": 7, "title": "People and Settlement", "topics": ["Rural Settlements", "Urban Settlements", "Urbanisation"]},
            {"num": 8, "title": "World Between Wars", "topics": ["World War I", "Great Depression", "Rise of Fascism", "World War II"]},
            {"num": 9, "title": "National Liberation Movements", "topics": ["Colonialism", "Nationalism in Asia", "African Liberation"]},
            {"num": 10, "title": "The Making of Independent India", "topics": ["Freedom Struggle", "Constituent Assembly", "Constitution"]},
            {"num": 11, "title": "Independent India", "topics": ["Nehru Era", "Green Revolution", "Economic Reforms", "Foreign Policy"]},
            {"num": 12, "title": "Emerging Political Trends", "topics": ["Democracy in India", "Coalition Politics", "Regional Parties"]},
        ]
    },
    {
        "id": "ap-english",
        "name": "English (AP Board)",
        "code": "ap",
        "board": "ap",
        "description": "Andhra Pradesh Board Class X English",
        "books": [
            {
                "name": "First Language English",
                "code": "ap-eng",
                "chapters": [
                    {"num": 1, "title": "Attitude is Altitude", "author": "Nick Vujicic"},
                    {"num": 2, "title": "The Dear Departed", "author": "Stanley Houghton"},
                    {"num": 3, "title": "The Journey", "author": "T. S. Raju"},
                    {"num": 4, "title": "The River", "author": "Caroline Bowles"},
                    {"num": 5, "title": "Or will the Dreamer Wake?", "author": "Medha Patkar"},
                    {"num": 6, "title": "My Childhood", "author": "A.P.J. Abdul Kalam"},
                    {"num": 7, "title": "A Tribute to Netaji", "author": "Mamta Kalia"},
                    {"num": 8, "title": "What is My Name?", "author": "Satyavati Srivastava"},
                ]
            }
        ]
    },
]

TS_BOARD_SUBJECTS = [
    {
        "id": "ts-mathematics",
        "name": "Mathematics (TS Board)",
        "code": "ts",
        "board": "ts",
        "description": "Telangana Board Class X Mathematics - based on TSSCERT textbook",
        "chapters": [
            {"num": 1, "title": "Real Numbers", "topics": ["Euclid's Division Lemma", "Fundamental Theorem of Arithmetic", "Rational Numbers", "Decimal Expansions"]},
            {"num": 2, "title": "Sets", "topics": ["Introduction to Sets", "Types of Sets", "Set Operations", "Venn Diagrams", "De Morgan's Laws"]},
            {"num": 3, "title": "Polynomials", "topics": ["Zeroes of Polynomial", "Relationship between Zeroes and Coefficients", "Division Algorithm", "Graph of Polynomial"]},
            {"num": 4, "title": "Pair of Linear Equations in Two Variables", "topics": ["Graphical Method", "Substitution", "Elimination", "Cross Multiplication"]},
            {"num": 5, "title": "Quadratic Equations", "topics": ["Standard Form", "Factorisation", "Quadratic Formula", "Nature of Roots"]},
            {"num": 6, "title": "Progressions", "topics": ["Arithmetic Progressions", "nth Term", "Sum of n Terms", "Geometric Progressions"]},
            {"num": 7, "title": "Coordinate Geometry", "topics": ["Distance Formula", "Section Formula", "Area of Triangle"]},
            {"num": 8, "title": "Similar Triangles", "topics": ["Similarity", "Basic Proportionality Theorem", "Pythagoras Theorem", "Criteria for Similarity"]},
            {"num": 9, "title": "Tangents and Secants", "topics": ["Tangent Properties", "Secant Properties", "Construction of Tangents"]},
            {"num": 10, "title": "Mensuration", "topics": ["Surface Areas", "Volumes", "Conversion of Solids", "Combination of Solids"]},
            {"num": 11, "title": "Trigonometry", "topics": ["Trigonometric Ratios", "Identities", "Heights and Distances"]},
            {"num": 12, "title": "Statistics", "topics": ["Mean", "Mode", "Median", "Ogive Curves"]},
            {"num": 13, "title": "Probability", "topics": ["Probability Basics", "Complementary Events", "Dice and Coins Problems"]},
        ]
    },
    {
        "id": "ts-physical-science",
        "name": "Physical Science (TS Board)",
        "code": "ts",
        "board": "ts",
        "description": "Telangana Board Class X Physical Science",
        "chapters": [
            {"num": 1, "title": "Chemical Reactions and Equations", "topics": ["Types of Reactions", "Balancing", "Redox", "Corrosion"]},
            {"num": 2, "title": "Acids, Bases and Salts", "topics": ["Properties", "pH", "Neutralisation", "Salts"]},
            {"num": 3, "title": "Metals and Non-metals", "topics": ["Properties", "Reactivity", "Extraction", "Corrosion"]},
            {"num": 4, "title": "Carbon and its Compounds", "topics": ["Covalent Bonds", "Hydrocarbons", "Functional Groups", "Polymers"]},
            {"num": 5, "title": "Light - Reflection and Refraction", "topics": ["Reflection", "Mirrors", "Refraction", "Lenses"]},
            {"num": 6, "title": "Human Eye and Colourful World", "topics": ["Eye Structure", "Defects", "Dispersion", "Scattering"]},
            {"num": 7, "title": "Electricity", "topics": ["Current", "Ohm's Law", "Resistance", "Power"]},
            {"num": 8, "title": "Magnetic Effects of Electric Current", "topics": ["Magnetic Field", "Electromagnet", "Motor", "Generator"]},
            {"num": 9, "title": "Our Environment", "topics": ["Ecosystem", "Biodiversity", "Pollution", "Conservation"]},
        ]
    },
    {
        "id": "ts-biology",
        "name": "Biological Science (TS Board)",
        "code": "ts",
        "board": "ts",
        "description": "Telangana Board Class X Biological Science",
        "chapters": [
            {"num": 1, "title": "Nutrition", "topics": ["Plant Nutrition", "Human Nutrition", "Digestive System", "Balanced Diet"]},
            {"num": 2, "title": "Respiration", "topics": ["Aerobic and Anaerobic", "Human Respiratory System", "Gas Exchange"]},
            {"num": 3, "title": "Transportation", "topics": ["Blood", "Heart", "Blood Vessels", "Transport in Plants"]},
            {"num": 4, "title": "Excretion", "topics": ["Kidney Structure", "Urine Formation", "Dialysis"]},
            {"num": 5, "title": "Control and Coordination", "topics": ["Nervous System", "Brain", "Reflexes", "Hormones"]},
            {"num": 6, "title": "Reproduction", "topics": ["Asexual", "Sexual in Plants", "Human Reproduction", "Health"]},
            {"num": 7, "title": "Heredity and Evolution", "topics": ["Mendel's Laws", "DNA", "Evolution Theories"]},
        ]
    },
    {
        "id": "ts-social-studies",
        "name": "Social Studies (TS Board)",
        "code": "ts",
        "board": "ts",
        "description": "Telangana Board Class X Social Studies",
        "chapters": [
            {"num": 1, "title": "India: Physical Features", "topics": ["Geographic Divisions", "Climate", "Soils", "Natural Vegetation"]},
            {"num": 2, "title": "Development", "topics": ["Economic Development", "HDI", "Inequality"]},
            {"num": 3, "title": "Production", "topics": ["Sectors", "GDP", "Employment"]},
            {"num": 4, "title": "Food Security", "topics": ["Agriculture", "Food Systems", "PDS"]},
            {"num": 5, "title": "Indian Economy", "topics": ["Reforms", "Globalisation", "Liberalisation"]},
            {"num": 6, "title": "Social Movements", "topics": ["Civil Rights", "Environmental Movements", "Women's Movements"]},
            {"num": 7, "title": "Post-War World", "topics": ["Cold War", "UNO", "Non-Alignment"]},
            {"num": 8, "title": "Independent India", "topics": ["Constitution", "Democracy", "Challenges"]},
            {"num": 9, "title": "Telangana Movement", "topics": ["Formation of Telangana", "Agitation", "State Reorganisation"]},
        ]
    },
]

ALL_BOARDS = {
    "cbse": {"name": "CBSE Class X", "subjects": SUBJECTS, "description": "Central Board of Secondary Education - National curriculum based on NCERT"},
    "ap": {"name": "Andhra Pradesh Board Class X", "subjects": AP_BOARD_SUBJECTS, "description": "Andhra Pradesh State Board of Secondary Education"},
    "ts": {"name": "Telangana Board Class X", "subjects": TS_BOARD_SUBJECTS, "description": "Telangana State Board of Secondary Education"},
}


def get_subject(subject_id):
    for s in SUBJECTS:
        if s["id"] == subject_id:
            return s
    for s in AP_BOARD_SUBJECTS:
        if s["id"] == subject_id:
            return s
    for s in TS_BOARD_SUBJECTS:
        if s["id"] == subject_id:
            return s
    return None


def get_subject_flat(subject_id):
    subject = get_subject(subject_id)
    if not subject:
        return None
    if "books" in subject:
        result = dict(subject)
        result["all_chapters"] = []
        for b in subject["books"]:
            for ch in b.get("chapters", []):
                entry = dict(ch)
                entry["book_name"] = b["name"]
                result["all_chapters"].append(entry)
            for po in b.get("poems", []):
                entry = dict(po)
                entry["book_name"] = b["name"]
                entry["is_poem"] = True
                result["all_chapters"].append(entry)
        return result
    return subject
