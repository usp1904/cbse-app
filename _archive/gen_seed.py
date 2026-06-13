#!/usr/bin/env python3
"""Generate seed_content.py with full educational content using templates."""

import os

TEMPLATE = {}

def t(name, text):
    TEMPLATE[name] = text

t("TEXT", """**{term}** is a fundamental concept in {subject}. {definition}

Key points to remember:
{points}

This concept is essential for solving problems related to {application} and forms the basis for more advanced topics in {subject}.""")

t("TEXT_PROP", """**1. Key Definition:**
{def1}

**2. Important Properties:**
{props}

**3. Standard Form:**
{std_form}

**4. Applications:**
{apps}

**5. Example:**
{example}

Understanding these properties helps in efficiently solving {topic} problems in examinations and real-life scenarios.""")

t("EXAMPLE", """**Problem:** {problem}

**Solution:**

**Step 1:** {step1}

**Step 2:** {step2}

**Step 3:** {step3}

**Step 4:** {step4}

**Step 5:** {step5}

Therefore, {conclusion}

---
**Verification:**
{verification}""")

t("MISTAKES", """**Common Mistakes:**

❌ **{mistake1_title}:** {mistake1_desc}

❌ **{mistake2_title}:** {mistake2_desc}

❌ **{mistake3_title}:** {mistake3_desc}

**Tips and Tricks:**

✓ **{tip1_title}:** {tip1_desc}

✓ **{tip2_title}:** {tip2_desc}

✓ **{tip3_title}:** {tip3_desc}

✓ **{tip4_title}:** {tip4_desc}

Mastering these techniques will help you avoid common errors and solve problems more efficiently.""")

t("EXERCISE", """**Problem 1 (Basic):**
{prob1}

**Answer:** {ans1}

---

**Problem 2 (Intermediate):**
{prob2}

**Answer:** {ans2}

---

**Problem 3 (Advanced):**
{prob3}

**Answer:** {ans3}""")


# ---- MATH TOPICS ----
M = {}  # MATH_TOPICS dict builder

def m(id, summary, chunks):
    M[id] = {"summary": summary, "chunks": chunks}


# Ch 4: Quadratic Equations
m("3a15cf1ea6ee3ee9", 
   "A quadratic equation in the variable x is of the form ax² + bx + c = 0, where a ≠ 0. Its standard form, roots, and the discriminant D = b² - 4ac determine the nature of roots. The quadratic formula x = [-b ± √(b² - 4ac)]/2a gives the solutions. This chapter covers solving quadratic equations by factorization, completing the square, and using the quadratic formula, along with word problems.",
   [
    {"title": "Standard Form of a Quadratic Equation",
     "content": "A **quadratic equation** in the variable x is an equation of the form **ax² + bx + c = 0**, where a, b, c are real numbers and a ≠ 0. The term 'quadratic' comes from the Latin word 'quadratus' meaning square.\n\nThe general form ax² + bx + c = 0 has three parts:\n   - **ax²**: the quadratic term (a is the coefficient of x²)\n   - **bx**: the linear term (b is the coefficient of x)\n   - **c**: the constant term\n\nThe condition a ≠ 0 is essential — if a = 0, the equation becomes linear (bx + c = 0).\n\nA **pure quadratic equation** has the form ax² + c = 0 (no linear term, b = 0). Examples: x² - 4 = 0, 2x² - 8 = 0.\n\nA **solution** or **root** of a quadratic equation is a value of x that satisfies the equation. A quadratic equation can have at most two roots.\n\n**Checking if an equation is quadratic:**\nAn equation is quadratic if it can be written in the form ax² + bx + c = 0 after simplification. For example:\n   - x² - 5x + 6 = 0 → quadratic ✓\n   - (x - 1)² + 2 = x² - 3 → x² - 2x + 1 + 2 = x² - 3 → -2x + 3 = -3 → 2x = 6 → linear ✗\n   - x(x + 2) = x² + 5 → x² + 2x = x² + 5 → 2x = 5 → linear ✗"},

    {"title": "Methods of Solving Quadratic Equations",
     "content": "**1. Factorization Method:**\n   Express ax² + bx + c as a product of two linear factors. Then set each factor to zero.\n   Steps:\n   - Write equation in standard form: ax² + bx + c = 0\n   - Factor the quadratic expression\n   - Set each factor equal to zero\n   - Solve the resulting linear equations\n   - These values are the roots\n\n**2. Completing the Square Method:**\n   Transform ax² + bx + c = 0 into a(x + p)² + q = 0.\n   Steps:\n   - Divide by a: x² + (b/a)x + c/a = 0\n   - Add and subtract (b/2a)²: x² + (b/a)x + (b/2a)² - (b/2a)² + c/a = 0\n   - Write as perfect square: (x + b/2a)² = (b² - 4ac)/4a²\n   - Take square root: x + b/2a = ±√(b² - 4ac)/2a\n   - Solve for x\n\n**3. Quadratic Formula Method:**\n   The roots of ax² + bx + c = 0 are given by:\n   **x = [-b ± √(b² - 4ac)] / 2a**\n   This formula is derived from completing the square and works for all quadratic equations.\n\n**4. Choosing a Method:**\n   - Factorization is fastest when the expression factors easily.\n   - Completing the square is useful when the coefficient b is even.\n   - The quadratic formula always works and is the most reliable method.\n\n**Example:** Solve x² - 5x + 6 = 0\nFactorization: (x - 2)(x - 3) = 0 → x = 2 or x = 3\nQuadratic formula: x = [5 ± √(25 - 24)]/2 = [5 ± 1]/2 → x = 3 or x = 2"},

    {"title": "Nature of Roots and the Discriminant",
     "content": "The **discriminant** of a quadratic equation ax² + bx + c = 0 is denoted by D and given by:\n\n**D = b² - 4ac**\n\nThe discriminant determines the nature of the roots:\n\n**Case 1: D > 0 (Two distinct real roots)**\n   The parabola intersects the x-axis at two distinct points.\n   Roots: x = (-b + √D)/2a and x = (-b - √D)/2a\n   Example: x² - 5x + 6 = 0, D = 25 - 24 = 1 > 0 → roots are 2 and 3\n\n**Case 2: D = 0 (Two equal real roots)**\n   The parabola touches the x-axis at exactly one point.\n   Root: x = -b/2a (repeated root)\n   Example: x² - 6x + 9 = 0, D = 36 - 36 = 0 → root is 3 (twice)\n\n**Case 3: D < 0 (No real roots)**\n   The parabola does not intersect the x-axis.\n   The roots are complex conjugates (not covered in Class X).\n   Example: x² + x + 1 = 0, D = 1 - 4 = -3 < 0 → no real roots\n\n**Relationship between roots and coefficients:**\nFor ax² + bx + c = 0 with roots α and β:\n   - Sum of roots: α + β = -b/a\n   - Product of roots: αβ = c/a\n   - Difference of roots: |α - β| = √D/|a|\n\n**Application:** Without solving, determine if 2x² - 4x + 3 = 0 has real roots.\nD = 16 - 24 = -8 < 0 → No real roots."},

    {"title": "Common Mistakes and Tips for Quadratic Equations",
     "content": "**Common Mistakes:**\n\n❌ **Forgetting a ≠ 0:** If a = 0, the equation is linear, not quadratic. Always check the coefficient of x².\n\n❌ **Incorrect factorization:** When factorizing ax² + bx + c, check that the product of the constant terms in the factors equals c, and the sum of the cross products equals b.\n\n❌ **Losing signs in the quadratic formula:** The formula is x = [-b ± √(b² - 4ac)]/2a. Common errors: forgetting the ±, forgetting the negative sign on b, or putting -b in the numerator incorrectly.\n\n❌ **Not writing in standard form first:** Always rearrange the equation to ax² + bx + c = 0 before solving.\n\n**Tips and Tricks:**\n\n✓ **Check your factorization:** Expand (x + p)(x + q) to verify it gives x² + (p+q)x + pq.\n\n✓ **Discriminant shortcut:** Check D first. If D < 0, stop — no real roots. If D is a perfect square, factorization might work.\n\n✓ **Word problems:** Assign a variable to what you need to find, form the equation, solve, and check if the answer makes sense in context.\n\n✓ **Verification:** Always substitute your answers back into the original equation."},

    {"title": "Practice Problems on Quadratic Equations",
     "content": "**Problem 1 (Basic):**\nSolve: x² - 7x + 12 = 0.\n\n**Answer:** (x - 3)(x - 4) = 0 → x = 3 or x = 4. Verify: 9 - 21 + 12 = 0 ✓, 16 - 28 + 12 = 0 ✓.\n\n---\n\n**Problem 2 (Intermediate):**\nFind the value of k for which the quadratic equation 2x² + kx + 2 = 0 has equal roots. (Hint: Set D = 0.)\n\n**Answer:** D = k² - 16 = 0 → k = ±4. For k = 4: 2x² + 4x + 2 = 2(x + 1)² = 0 → root is x = -1. For k = -4: 2x² - 4x + 2 = 2(x - 1)² = 0 → root is x = 1.\n\n---\n\n**Problem 3 (Advanced):**\nA rectangular plot of land has an area of 528 m². The length is 1 m more than twice the breadth. Find the length and breadth.\n\n**Answer:** Let breadth = x m. Then length = (2x + 1) m. Area: x(2x + 1) = 528 → 2x² + x - 528 = 0. Using quadratic formula: D = 1 + 4224 = 4225 = 65². x = (-1 ± 65)/4 = 16 or -16.5. Since breadth is positive, x = 16. Length = 33 m. Check: 16 × 33 = 528 ✓."}
    ])

m("c44b9a6e424bf81f",
   "The method of completing the square transforms a quadratic equation ax² + bx + c = 0 into the form (x + p)² = q by adding and subtracting (b/2a)². This method provides a systematic algebraic approach that always works and leads directly to the quadratic formula. It is also useful for finding the vertex of a parabola and solving equations where factorization is difficult.",
   [
    {"title": "Understanding the Method of Completing the Square",
     "content": "The **method of completing the square** is an algebraic technique used to solve quadratic equations by rewriting them in the form (x + p)² = q. This method is particularly useful when the equation cannot be easily factored.\n\nThe idea is to take a quadratic expression like x² + bx and add the square of half the coefficient of x to make it a perfect square trinomial.\n\n**Perfect Square Trinomial:**\nA perfect square trinomial has the form x² + 2px + p² = (x + p)² or x² - 2px + p² = (x - p)².\n\n**The key insight:** To convert x² + bx into a perfect square, we add (b/2)². Then:\nx² + bx + (b/2)² = (x + b/2)²\n\n**Example:** x² + 6x + 9 = (x + 3)² because 6/2 = 3 and 3² = 9.\n\n**Historical note:** This method dates back to ancient Babylonian mathematics (around 2000 BCE) and was further developed by Islamic mathematicians like Al-Khwarizmi in the 9th century. The geometric interpretation involves cutting and rearranging a square area to form a larger square — hence the name 'completing the square'."},

    {"title": "Step-by-Step Process and Applications",
     "content": "**Steps for Completing the Square:**\n\nConsider ax² + bx + c = 0.\n\n**Step 1:** Divide by a (if a ≠ 1):\nx² + (b/a)x + c/a = 0\n\n**Step 2:** Move constant term to RHS:\nx² + (b/a)x = -c/a\n\n**Step 3:** Add (b/2a)² to both sides:\nx² + (b/a)x + (b/2a)² = -c/a + (b/2a)²\n\n**Step 4:** Write LHS as a perfect square:\n(x + b/2a)² = (b² - 4ac)/4a²\n\n**Step 5:** Take square root:\nx + b/2a = ±√(b² - 4ac)/2a\n\n**Step 6:** Solve for x:\nx = [-b ± √(b² - 4ac)]/2a\n\n**Applications beyond solving equations:**\n\n**Finding the vertex of a parabola:**\nFor y = ax² + bx + c, writing as y = a(x + p)² + q gives the vertex at (-p, q).\nExample: y = x² - 4x + 7 = (x - 2)² + 3 → vertex at (2, 3).\n\n**Graphing parabolas:**\nThe completed square form immediately tells the vertex, axis of symmetry (x = -p), and direction of opening.\n\n**Optimization problems:**\nCompleting the square can find maximum/minimum values. Since (x + p)² ≥ 0, the minimum value of (x + p)² + q is q.\nExample: Minimum value of x² - 4x + 7 = (x - 2)² + 3 is 3."},

    {"title": "Worked Example: Solving by Completing the Square",
     "content": "**Problem:** Solve 2x² - 4x - 6 = 0 by completing the square.\n\n**Solution:**\n\n**Step 1:** Divide by 2 (coefficient of x²):\nx² - 2x - 3 = 0\n\n**Step 2:** Move constant to RHS:\nx² - 2x = 3\n\n**Step 3:** Add (coefficient of x ÷ 2)² to both sides:\nCoefficient of x is -2. Half is -1. Square is 1.\nx² - 2x + 1 = 3 + 1\nx² - 2x + 1 = 4\n\n**Step 4:** Write LHS as a perfect square:\n(x - 1)² = 4\n\n**Step 5:** Take square root:\nx - 1 = ±√4\nx - 1 = ±2\n\n**Step 6:** Solve for x:\nx = 1 + 2 = 3\nx = 1 - 2 = -1\n\n**Solution: x = 3 or x = -1**\n\n**Verification:**\nFor x = 3: 2(9) - 12 - 6 = 18 - 12 - 6 = 0 ✓\nFor x = -1: 2(1) + 4 - 6 = 2 + 4 - 6 = 0 ✓\n\n---\n\n**Additional Example:** Find the minimum value of x² + 6x + 11.\nComplete the square: x² + 6x + 9 + 2 = (x + 3)² + 2\nMinimum value = 2 (when x = -3)."},

    {"title": "Common Mistakes and Tips for Completing the Square",
     "content": "**Common Mistakes:**\n\n❌ **Forgetting to divide by a first:** If a ≠ 1, you must divide the ENTIRE equation by a before completing the square. Otherwise, the coefficient of x² is wrong.\n\n❌ **Adding (b/2)² instead of (b/2a)²:** After dividing by a, the coefficient becomes b/a, so you add (b/2a)², not (b/2)².\n\n❌ **Sign errors:** When taking square root, don't forget the ± sign. √4 = ±2, not just 2.\n\n❌ **Adding to only one side:** Whatever you add to the LHS must also be added to the RHS to maintain equality.\n\n**Tips and Tricks:**\n\n✓ **Check if b is even:** If b is even, (b/2)² will be an integer, making calculations easier.\n\n✓ **Shortcut when a = 1:** If the equation is x² + bx + c = 0, just move c, add (b/2)², and solve.\n\n✓ **Vertex form:** Remember that y = a(x - h)² + k gives the vertex at (h, k). The sign inside the bracket is opposite: (x - 2)² means h = 2.\n\n✓ **Check your answer:** Expand (x + p)² to verify it equals your original expression before adding the constant."},

    {"title": "Practice Problems on Completing the Square",
     "content": "**Problem 1 (Basic):**\nSolve x² + 6x - 7 = 0 by completing the square.\n\n**Answer:** x² + 6x = 7 → x² + 6x + 9 = 7 + 9 → (x + 3)² = 16 → x + 3 = ±4 → x = 1 or x = -7.\n\n---\n\n**Problem 2 (Intermediate):**\nSolve 3x² - 6x + 2 = 0 by completing the square.\n\n**Answer:** Divide by 3: x² - 2x + 2/3 = 0 → x² - 2x = -2/3 → x² - 2x + 1 = -2/3 + 1 → (x - 1)² = 1/3 → x - 1 = ±1/√3 → x = 1 ± 1/√3.\n\n---\n\n**Problem 3 (Advanced):**\nExpress y = 2x² - 12x + 7 in the form y = a(x - h)² + k and find the minimum value of y and the value of x at which it occurs.\n\n**Answer:** Factor 2: y = 2(x² - 6x) + 7 = 2[(x² - 6x + 9) - 9] + 7 = 2(x - 3)² - 18 + 7 = 2(x - 3)² - 11. Vertex: (3, -11). Minimum value = -11 (when x = 3). Since a = 2 > 0, parabola opens upward, so vertex is indeed the minimum."}
    ])

m("5696921750beb571",
   "Many real-world problems can be modeled using quadratic equations. These include problems involving numbers, time-speed-distance, work, age, geometry (area, perimeter), and business (profit, revenue). The key steps involve identifying the unknown quantity, forming a quadratic equation based on given conditions, solving it, and selecting the solution that makes sense in the given context.",
   [
    {"title": "Word Problems on Quadratic Equations",
     "content": "**Word problems** involving quadratic equations appear frequently in Class X examinations and real-life applications. Solving them requires translating a verbal description into a mathematical equation.\n\n**General Strategy:**\n\nStep 1: **Read** the problem carefully and identify what is asked.\nStep 2: **Assign a variable** (usually x) to the unknown quantity.\nStep 3: **Form an equation** based on the conditions given in the problem.\nStep 4: **Solve** the quadratic equation using an appropriate method.\nStep 5: **Check** your answers and select the one that makes sense in context (usually the positive value).\nStep 6: **Write the answer** in a complete sentence.\n\n**Common Types of Word Problems:**\n\n**Type 1 — Number Problems:**\nFind two consecutive positive integers whose product is 240.\nLet x and x+1 be the integers. Then x(x+1) = 240 → x² + x - 240 = 0 → (x+16)(x-15) = 0 → x = 15 (positive). The integers are 15 and 16.\n\n**Type 2 — Geometry Problems:**\nThe area of a rectangular garden is 240 m². The length is 8 m more than the width. Find dimensions.\nLet width = x. Length = x + 8. Area: x(x+8) = 240 → x² + 8x - 240 = 0 → x = 12 or x = -20. Width = 12 m, Length = 20 m.\n\n**Type 3 — Time-Speed-Distance:**\nA train travels 360 km at a uniform speed. If the speed were 5 km/h more, it would take 1 hour less. Find the original speed.\nLet original speed = x km/h. Time at original speed = 360/x hours. Time at increased speed = 360/(x+5) hours. Equation: 360/x - 360/(x+5) = 1 → 360(x+5) - 360x = x(x+5) → 1800 = x² + 5x → x² + 5x - 1800 = 0 → x = 40 or x = -45. Original speed = 40 km/h."},

    {"title": "Key Types and Formulas for Word Problems",
     "content": "**1. Consecutive Numbers:**\n   - Consecutive integers: x, x+1, x+2, ...\n   - Consecutive even/odd integers: x, x+2, x+4, ...\n   - Their product or sum leads to a quadratic equation.\n\n**2. Geometry Formulas:**\n   - Area of rectangle = length × breadth\n   - Area of triangle = ½ × base × height\n   - Pythagorean theorem: a² + b² = c² (for right triangles)\n   - Perimeter formulas can also lead to quadratic equations.\n\n**3. Time-Speed-Distance:**\n   - Distance = Speed × Time\n   - Time = Distance / Speed\n   - When speed changes, the time difference gives the equation.\n\n**4. Work Problems:**\n   - Work done = Rate × Time\n   - If A takes a hours and B takes b hours, together they take ab/(a+b) hours.\n   - 1/a + 1/b = 1/t (where t is time when working together)\n\n**5. Age Problems:**\n   - Set up equations relating ages at different time points.\n   - Usually involve current ages and ages n years from now or n years ago.\n\n**6. Profit and Revenue:**\n   - Profit = Revenue - Cost\n   - Revenue = Price × Quantity\n   - Sometimes price and quantity are related linearly, making revenue quadratic.\n\n**7. Important Considerations:**\n   - Always reject negative solutions unless the context allows them (e.g., negative time doesn't make sense, but negative profit can).\n   - Check that the answer satisfies the original conditions.\n   - Use appropriate units in your final answer."},

    {"title": "Worked Example: Solving a Word Problem",
     "content": "**Problem:** The sum of the areas of two squares is 468 m². If the difference of their perimeters is 24 m, find the sides of the two squares.\n\n**Solution:**\n\n**Step 1:** Assign variables.\nLet the side of the smaller square = x m.\nLet the side of the larger square = y m.\n\n**Step 2:** Form equations.\nArea equation: x² + y² = 468\nPerimeter difference: 4y - 4x = 24 → y - x = 6 → y = x + 6\n\n**Step 3:** Substitute y = x + 6 into the area equation.\nx² + (x + 6)² = 468\nx² + x² + 12x + 36 = 468\n2x² + 12x + 36 = 468\n2x² + 12x - 432 = 0\nx² + 6x - 216 = 0\n\n**Step 4:** Solve.\n(x + 18)(x - 12) = 0\nx = -18 or x = 12\nSince side cannot be negative, x = 12 m.\n\n**Step 5:** Find y.\ny = x + 6 = 18 m.\n\n**Step 6:** Verify.\nAreas: 144 + 324 = 468 ✓\nPerimeters: 72 - 48 = 24 ✓\n\nTherefore, the sides of the squares are **12 m** and **18 m**."},

    {"title": "Common Mistakes and Tips for Word Problems",
     "content": "**Common Mistakes:**\n\n❌ **Misinterpreting the problem:** Read the problem multiple times. Identify the unknown, the given data, and the condition that connects them.\n\n❌ **Wrong variable assignment:** Choose a variable that is simple and directly relates to what's being asked.\n\n❌ **Rejecting the wrong solution:** If both solutions are positive, check whether both make sense. Don't automatically assume the smaller one is correct.\n\n❌ **Forgetting units:** Always include units in your final answer (m, km/h, years, rupees, etc.).\n\n**Tips and Tricks:**\n\n✓ **Draw a diagram:** For geometry problems, a simple sketch helps visualize the relationships.\n\n✓ **Check reasonableness:** If a rectangle has length 1000 m and area 240 m², something is wrong. Your answer should be reasonable.\n\n✓ **Use a table:** For time-speed-distance problems, a table with Distance, Speed, Time columns helps organize the data.\n\n✓ **Practice categorization:** Most word problems fall into a few categories. Learn to recognize the pattern.\n\n✓ **Final verification:** Substitute your answer back into the ORIGINAL word problem conditions, not just the equation."},

    {"title": "Practice Problems on Word Problems",
     "content": "**Problem 1 (Basic):**\nFind two consecutive odd positive integers whose product is 143.\n\n**Answer:** Let integers be x and x+2. x(x+2) = 143 → x² + 2x - 143 = 0 → (x+13)(x-11) = 0 → x = 11 (positive). Integers: 11 and 13. Check: 11 × 13 = 143 ✓.\n\n---\n\n**Problem 2 (Intermediate):**\nA motorboat whose speed is 18 km/h in still water takes 1 hour more to go 24 km upstream than to return downstream. Find the speed of the stream.\n\n**Answer:** Let stream speed = x km/h. Upstream speed = (18-x), Downstream = (18+x). Time difference: 24/(18-x) - 24/(18+x) = 1. Solving: 24(18+x) - 24(18-x) = (18-x)(18+x) → 48x = 324 - x² → x² + 48x - 324 = 0. D = 2304 + 1296 = 3600 = 60². x = (-48 + 60)/2 = 6 (positive). Speed of stream = 6 km/h.\n\n---\n\n**Problem 3 (Advanced):**\nA shopkeeper buys a number of books for Rs 80. If he had bought 4 more books for the same amount, each book would have cost Rs 1 less. How many books did he buy?\n\n**Answer:** Let number of books = x. Cost per book = 80/x. Equation: 80/(x+4) = 80/x - 1. Multiply by x(x+4): 80x = 80(x+4) - x(x+4) = 80x + 320 - x² - 4x → x² + 4x - 320 = 0 → (x+20)(x-16) = 0 → x = 16 (positive). He bought 16 books. Check: 80/16 = Rs 5 each. 80/20 = Rs 4 each (Rs 1 less) ✓."}
    ])


# Ch 5: Arithmetic Progressions
m("179c8e078511f997",
   "An Arithmetic Progression (AP) is a sequence of numbers in which each term differs from the preceding term by a constant called the common difference (d). The nth term is given by aₙ = a + (n-1)d, and the sum of n terms is Sₙ = n/2[2a + (n-1)d] = n/2[a + l], where l is the last term. APs are used extensively in real-life situations involving growth, savings, and patterns.",
   [
    {"title": "Understanding Arithmetic Progressions",
     "content": "An **Arithmetic Progression (AP)** is a sequence of numbers in which each term (except the first) is obtained by adding a fixed number to the preceding term. This fixed number is called the **common difference** (d).\n\n**Standard Form of an AP:**\na, a + d, a + 2d, a + 3d, ...\nwhere a = first term, d = common difference.\n\n**Examples:**\n   - 1, 4, 7, 10, ... (a = 1, d = 3)\n   - 10, 7, 4, 1, -2, ... (a = 10, d = -3)\n   - 2, 2, 2, 2, ... (a = 2, d = 0 — constant sequence)\n\n**Determining if a sequence is an AP:**\nCheck if the difference between consecutive terms is constant.\nd = a₂ - a₁ = a₃ - a₂ = a₄ - a₃ = ...\n\n**Finite and Infinite AP:**\n   - If the AP has a fixed number of terms, it's a **finite AP**.\n   - If the AP continues indefinitely, it's an **infinite AP**.\n\nThe general term (nth term) of an AP is:\n**aₙ = a + (n - 1)d**\n\n**Example:** Find the 10th term of AP: 3, 7, 11, 15, ...\na = 3, d = 4, a₁₀ = 3 + (10-1)4 = 3 + 36 = 39"},

    {"title": "Key Formulas and Properties of AP",
     "content": "**1. nth Term Formula:**\n   aₙ = a + (n - 1)d\n   where a = first term, d = common difference, n = term number.\n\n**2. Sum of n Terms Formulas:**\n   Sₙ = n/2[2a + (n - 1)d]\n   Sₙ = n/2[a + l]  where l = last term = aₙ\n\n**3. Finding n given a term:**\n   If aₙ is known, n = (aₙ - a)/d + 1\n\n**4. Finding d from consecutive terms:**\n   d = a₂ - a₁ = a₃ - a₂ = ...\n   d = (aₘ - aₙ)/(m - n)\n\n**5. Properties of AP:**\n   - If a constant k is added to or subtracted from each term, the new sequence is also an AP with the same d.\n   - If each term is multiplied or divided by a non-zero constant k, the new sequence is an AP with common difference kd or d/k.\n   - Three terms in AP can be taken as (a - d), a, (a + d) — their sum is 3a.\n   - Four terms in AP can be taken as (a - 3d), (a - d), (a + d), (a + 3d) — sum is 4a.\n\n**6. Selecting Terms in AP:**\n   - For 3 terms: a-d, a, a+d (sum of terms = 3a)\n   - For 4 terms: a-3d, a-d, a+d, a+3d (sum = 4a)\n   - For 5 terms: a-2d, a-d, a, a+d, a+2d (sum = 5a)\n\nThese representations simplify solving problems where sums are given."},

    {"title": "Worked Example: Finding Terms and Sum of an AP",
     "content": "**Problem:** Find the sum of the first 20 terms of the AP: 5, 9, 13, 17, ... Also find the 15th term.\n\n**Solution:**\n\n**Step 1:** Identify a and d.\na = 5, d = 9 - 5 = 4\n\n**Step 2:** Find the 15th term using aₙ = a + (n - 1)d.\na₁₅ = 5 + (15 - 1)4 = 5 + 14(4) = 5 + 56 = 61\n\n**Step 3:** Find the sum of 20 terms using Sₙ = n/2[2a + (n - 1)d].\nS₂₀ = 20/2[2(5) + (20 - 1)4]\n= 10[10 + 76]\n= 10 × 86\n= 860\n\n**Step 4:** Verify using the alternative formula Sₙ = n/2[a + l].\nFirst find a₂₀ = 5 + 19(4) = 5 + 76 = 81\nS₂₀ = 20/2[5 + 81] = 10 × 86 = 860 ✓\n\n**Results:**\n15th term = **61**\nSum of 20 terms = **860**\n\n---\n\n**Additional Example:** How many terms of the AP: 24, 21, 18, ... must be taken to get the sum 78?\nHere a = 24, d = -3, Sₙ = 78\nn/2[48 + (n-1)(-3)] = 78 → n[48 - 3n + 3] = 156 → n[51 - 3n] = 156 → 51n - 3n² = 156 → 3n² - 51n + 156 = 0 → n² - 17n + 52 = 0 → (n-4)(n-13) = 0. So n = 4 or 13. Both work: first 4 terms sum = 78 and first 13 terms also sum = 78 (since terms 5-13 sum to 0)."},

    {"title": "Common Mistakes and Tips for AP",
     "content": "**Common Mistakes:**\n\n❌ **Confusing a and d:** a is the FIRST term (not the second). d = a₂ - a₁, not a₁ - a₂.\n\n❌ **Using wrong formula for nth term:** aₙ = a + (n-1)d, NOT a + nd. Check: for n = 1, a₁ = a + 0·d = a ✓.\n\n❌ **Forgetting the n/2 factor in sum:** Sₙ = n/2[2a + (n-1)d], not n[2a + (n-1)d].\n\n❌ **Sign errors with negative d:** If the AP is decreasing (like 10, 7, 4, ...), d = -3. Be careful with signs.\n\n**Tips and Tricks:**\n\n✓ **Check your answer:** If n = 1, S₁ should equal a. If n = 2, S₂ should equal a + (a+d) = 2a + d.\n\n✓ **Finding the number of terms:** If asked 'how many terms?', check if n must be a natural number (positive integer).\n\n✓ **Common difference from any two terms:** d = (aₘ - aₙ)/(m - n). This works for any two terms.\n\n✓ **Three-term trick:** When sum of three terms in AP is given, take them as (a-d), a, (a+d) and solve for a easily (sum = 3a).\n\n✓ **Verification:** The sum of an AP is always n × (average of first and last term). This is a quick mental check."},

    {"title": "Practice Problems on Arithmetic Progressions",
     "content": "**Problem 1 (Basic):**\nFind the 20th term of AP: -3, 1, 5, 9, ...\n\n**Answer:** a = -3, d = 4. a₂₀ = -3 + 19(4) = -3 + 76 = 73.\n\n---\n\n**Problem 2 (Intermediate):**\nThe sum of n terms of an AP is 3n² + n. Find the AP and its common difference. (Hint: a = S₁, a₂ = S₂ - S₁)\n\n**Answer:** S₁ = 3 + 1 = 4 = a. S₂ = 12 + 2 = 14. a₂ = S₂ - S₁ = 10. d = a₂ - a₁ = 6. The AP: 4, 10, 16, 22, ...\n\n---\n\n**Problem 3 (Advanced):**\nIf the sum of first p terms of an AP is the same as the sum of its first q terms (p ≠ q), prove that the sum of its first (p+q) terms is 0.\n\n**Answer:** Sₚ = p/2[2a + (p-1)d] and S_q = q/2[2a + (q-1)d]. Given Sₚ = S_q. Simplifying: 2a(p-q) + d(p² - p - q² + q) = 0 → 2a(p-q) + d(p-q)(p+q-1) = 0 → (p-q)[2a + d(p+q-1)] = 0. Since p ≠ q, 2a + d(p+q-1) = 0. Now S_{p+q} = (p+q)/2[2a + (p+q-1)d] = (p+q)/2 × 0 = 0. Hence proved."}
    ])


# We'll continue with more topics in subsequent sections
# For now, let's write what we have

def generate():
    lines = []

    # Header
    lines.append("""import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from database import get_conn


TOPIC_CONTENT = {}

MATH_TOPICS = {
""")

    # Generate Math topics
    first = True
    for tid, data in M.items():
        if first:
            first = False
        else:
            lines.append(",\n")
        lines.append(f'    "{tid}": {{\n')
        lines.append(f'        "summary": {repr(data["summary"])},\n')
        lines.append(f'        "chunks": [\n')
        for i, chunk in enumerate(data["chunks"]):
            if i > 0:
                lines.append(",\n")
            lines.append(f'            {{\n')
            lines.append(f'                "title": {repr(chunk["title"])},\n')
            lines.append(f'                "content": {repr(chunk["content"])}\n')
            lines.append(f'            }}')
        lines.append(f'\n        ]\n')
        lines.append(f'    }}')

    lines.append("""
}

SCIENCE_TOPICS = {}
""")


    lines.append("""
# Build the full TOPIC_CONTENT dictionary
TOPIC_CONTENT.update(MATH_TOPICS)
TOPIC_CONTENT.update(SCIENCE_TOPICS)


def seed_content():
    conn = get_conn()
    cur = conn.cursor()

    rows = cur.execute(\"""
        SELECT t.id as topic_id, t.title as topic_title, ch.title as ch_title, s.name as subj_name
        FROM topics t
        JOIN chapters ch ON t.chapter_id = ch.id
        JOIN subjects s ON ch.subject_id = s.id
        WHERE ch.board_id = 'cbse' AND s.name IN ('Mathematics', 'Science')
        ORDER BY s.name, ch.num, t.num
    \""").fetchall()

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

        cur.execute("UPDATE topics SET content = ? WHERE id = ?", (data['summary'], tid))
        updated_topics += 1

        chunks = cur.execute(
            "SELECT id, content_type, seq FROM chunks WHERE topic_id = ? ORDER BY seq",
            (tid,)
        ).fetchall()

        if len(chunks) != 5:
            print(f"  WARNING: Topic '{d['topic_title']}' has {len(chunks)} chunks (expected 5)")

        for i, chunk_row in enumerate(chunks):
            cd = dict(chunk_row)
            chunk_id = cd['id']
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
""")

    output = "".join(lines)
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seed_content.py")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(output)
    print(f"Generated seed_content.py ({len(output)} bytes)")

if __name__ == "__main__":
    generate()
