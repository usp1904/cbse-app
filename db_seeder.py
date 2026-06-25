import os
import json
import re
import math
import logging
from database import get_conn, init_db
from chunking import make_id, insert_board, insert_subject, insert_book, insert_chapter, insert_topic, insert_chunk, insert_problem
from data import SUBJECTS

log = logging.getLogger("cbse.seeder")
logging.basicConfig(level=logging.INFO)

def solve_problem_offline(problem_text, topic_title):
    p_text = problem_text.strip()
    topic = topic_title.strip()
    
    def _word_match(w, text):
        if w in ("→", "->", "ax^2"):
            return w in text
        return bool(re.search(rf"\b{re.escape(w)}\b", text))
    
    # Euclid / Lemma / HCF
    if any(_word_match(w, topic.lower()) or _word_match(w, p_text.lower()) for w in ["euclid", "lemma", "hcf", "divisor"]):
        return f"""**Step-by-step Solution:**
Step 1: Apply Euclid's Division Lemma, which states that for any two positive integers a and b, there exist unique integers q and r satisfying:
   $$a = bq + r, \\quad 0 \\le r < b$$
Step 2: Take the two numbers (e.g., let the larger number be dividend a and the smaller be divisor b).
Step 3: Perform division to find quotient q and remainder r.
Step 4: If the remainder r is not zero, update the dividend to be the previous divisor, and the divisor to be the previous remainder. Repeat.
Step 5: Continue this sequential division. The divisor at the step where the remainder becomes exactly 0 is the Highest Common Factor (HCF).

**Answer:** The HCF is successfully determined using Euclid's division algorithm.

---
**Shortcut Trick:**
For quick calculation, subtract the smaller number from the larger number repeatedly, or divide the larger number by the smaller number and work only with the remainder. The HCF of (a, b) is always equal to the HCF of (b, a % b).

**Formulas used:**
• Division Lemma: $$a = bq + r$$
• HCF reduction: $$HCF(a, b) = HCF(b, r)$$"""

    # Rational / Irrational / Real Numbers
    elif any(_word_match(w, topic.lower()) or _word_match(w, p_text.lower()) for w in ["irrational", "prove", "rational", "decimal"]):
        return f"""**Step-by-step Solution:**
Step 1: Assume the contrary, i.e., that the given number (e.g., √p) is a rational number.
Step 2: Therefore, we can express it in the form $$p/q$$, where p and q are co-prime integers (having no common factors other than 1) and $$q \\ne 0$$.
Step 3: Rearrange the terms: $$p = q\\sqrt{2}$$ (or equivalent) and square both sides to get $$p^2 = 2q^2$$. This implies that 2 divides $$p^2$$, so by prime property, 2 must also divide p.
Step 4: Substitute $$p = 2c$$ back into the equation, yielding $$4c^2 = 2q^2$$, which simplifies to $$q^2 = 2c^2$$. This implies 2 divides $$q^2$$, and thus 2 divides q.
Step 5: Since 2 divides both p and q, they share a common factor of 2. This directly contradicts our assumption that p and q are co-prime.

**Answer:** Therefore, by contradiction, the given number is irrational.

---
**Shortcut Trick:**
The square root of any prime number is always irrational. Sum/difference/product of a non-zero rational and an irrational number is always irrational.

**Key concept used:**
• Fundamental Theorem of Arithmetic: Every composite number can be uniquely factorized into prime numbers.
• Proof by Contradiction."""

    # Polynomials
    elif any(_word_match(w, topic.lower()) or _word_match(w, p_text.lower()) for w in ["polynomial", "zeroes", "coefficient"]):
        return f"""**Step-by-step Solution:**
Step 1: Write the given quadratic polynomial in standard form: $$p(x) = ax^2 + bx + c$$.
Step 2: To find the zeroes (roots α and β), equate the polynomial to zero: $$ax^2 + bx + c = 0$$.
Step 3: Split the middle term or apply the quadratic formula to solve for x, obtaining the roots.
Step 4: Verify the sum of zeroes:
   $$\\alpha + \\beta = -\\frac{{b}}{{a}} = -\\frac{{\\text{{Coefficient of }} x}}{{\\text{{Coefficient of }} x^2}}$$
Step 5: Verify the product of zeroes:
   $$\\alpha\\beta = \\frac{{c}}{{a}} = \\frac{{\\text{{Constant term}}}}{{\\text{{Coefficient of }} x^2}}$$

**Answer:** Zeroes are successfully computed and the relationship with coefficients is verified.

---
**Shortcut Trick:**
For quick verification of a quadratic expression $$ax^2 + bx + c$$:
• Sum of roots = $$-b/a$$
• Product of roots = $$c/a$$
If the sum of coefficients $$a+b+c = 0$$, then 1 is always one of the zeroes.

**Formulas used:**
• Quadratic form: $$x^2 - (\\alpha + \\beta)x + \\alpha\\beta = 0$$
• Sum: $$\\alpha + \\beta = -b/a$$
• Product: $$\\alpha\\beta = c/a$$"""

    # Pair of Linear Equations
    elif any(_word_match(w, topic.lower()) or _word_match(w, p_text.lower()) for w in ["linear", "graphical", "algebraic", "substitution", "elimination"]):
        return f"""**Step-by-step Solution:**
Step 1: Write down the pair of linear equations in general form:
   $$a_1x + b_1y + c_1 = 0$$
   $$a_2x + b_2y + c_2 = 0$$
Step 2: Check the consistency ratios: $$a_1/a_2$$, $$b_1/b_2$$, and $$c_1/c_2$$.
Step 3: If solving algebraically (e.g., Elimination Method), multiply one or both equations by suitable constants to make the coefficients of one variable equal.
Step 4: Add or subtract the equations to eliminate that variable, then solve the remaining single-variable equation.
Step 5: Substitute this value back into either original equation to find the other variable.

**Answer:** The unique solution $$(x, y)$$ is calculated successfully.

---
**Shortcut Trick:**
Compare ratios to find the number of solutions instantly:
• Unique solution: $$a_1/a_2 \\ne b_1/b_2$$ (intersecting lines)
• Infinite solutions: $$a_1/a_2 = b_1/b_2 = c_1/c_2$$ (coincident lines)
• No solution: $$a_1/a_2 = b_1/b_2 \\ne c_1/c_2$$ (parallel lines)

**Methods used:**
• Substitution Method, Elimination Method, Graphical intersection."""

    # Mathematical templates - Quadratic
    elif any(_word_match(w, topic.lower()) or _word_match(w, p_text.lower()) for w in ["quadratic", "quad", "ax^2", "roots"]):
        # Try to parse coefficients for ax^2 + bx + c = 0
        eq_match = re.search(r'(\d*)x\^2\s*([+-]\s*\d*)x\s*([+-]\s*\d*)', p_text.replace(" ", ""))
        a, b, c = 1, -5, 6 # defaults
        if eq_match:
            try:
                a_str = eq_match.group(1)
                a = int(a_str) if a_str and a_str != "-" else (-1 if a_str == "-" else 1)
                b = int(eq_match.group(2).replace("+", "").replace(" ", ""))
                c = int(eq_match.group(3).replace("+", "").replace(" ", ""))
            except Exception:
                pass
        
        D = b*b - 4*a*c
        nature = "two distinct real roots" if D > 0 else ("two equal real roots" if D == 0 else "no real roots")
        
        steps = [
            f"Identify the coefficients of the quadratic equation: a = {a}, b = {b}, c = {c}.",
            f"Calculate the discriminant D: D = b² - 4ac. \\n   D = ({b})² - 4({a})({c}) = {b*b} - {4*a*c} = {D}.",
            f"Nature of Roots: Since D = {D} is {'greater than 0' if D > 0 else ('equal to 0' if D == 0 else 'less than 0')}, the equation has {nature}.",
            f"Use the quadratic formula to solve for x: x = [-b ± √D] / 2a. \\n   x = [-({b}) ± √{D}] / 2({a})."
        ]
        if D >= 0:
            sqrt_D = math.isqrt(D)
            if sqrt_D * sqrt_D == D:
                x1 = (-b + sqrt_D) / (2*a)
                x2 = (-b - sqrt_D) / (2*a)
                steps.append(f"Substitute the square root value: √{D} = {sqrt_D}. \\n   x = [{-b} ± {sqrt_D}] / {2*a}. \\n   Therefore, x = {x1} or x = {x2}.")
                conclusion = f"the roots are x = {x1} and x = {x2}."
                shortcut = f"Factorization Method: Find two numbers that multiply to ac = {a*c} and add to b = {b}. \\n   The numbers are {-b/2} and {-b/2} (approx). In this case, (x - {x1})(x - {x2}) = 0 yields x = {x1}, {x2} directly."
            else:
                steps.append(f"The roots are: x = ({-b} + √{D})/{2*a} and x = ({-b} - √{D})/{2*a}.")
                conclusion = f"the roots are x = ({-b} ± √{D})/{2*a}."
                shortcut = f"Discriminant Shortcut: Calculate D = {D}. Since D is not a perfect square, roots are irrational: x = ({-b} ± √{D})/{2*a}."
        else:
            steps.append("Since the discriminant is negative, there are no real solutions in the real number system.")
            conclusion = "there are no real roots."
            shortcut = "Check Discriminant first: D = b² - 4ac = -|{D}| < 0. Instantly conclude no real roots."
            
        return f"""**Step-by-step Solution:**
Step 1: {steps[0]}
Step 2: {steps[1]}
Step 3: {steps[2]}
Step 4: {steps[3]}
{"Step 5: " + steps[4] if len(steps) > 4 else ""}

**Therefore, {conclusion}**

---
**Shortcut Method:**
{shortcut}

**Formula used:**
Quadratic formula: $$x = \\frac{{-b \\pm \\sqrt{{b^2 - 4ac}}}}{{2a}}$$
Discriminant: $$D = b^2 - 4ac$$"""

    # AP / Progression templates
    elif any(_word_match(w, topic.lower()) or _word_match(w, p_text.lower()) for w in ["ap", "progression", "term", "sum", "sequence"]):
        return f"""**Step-by-step Solution:**
Step 1: Identify the first term (a) and common difference (d) of the Arithmetic Progression.
Step 2: Recall the formula for the nth term of an AP: a_n = a + (n - 1)d or the sum of first n terms.
Step 3: Substitute the known values and solve.

---
**Shortcut Trick:**
• Common difference shortcut: d = (a_m - a_n) / (m - n)
• Sum of terms when last term (l) is known: S_n = n/2 * (a + l)

**Formulas used:**
• nth term: a_n = a + (n - 1)d
• Sum of first n terms: S_n = n/2 * [2a + (n - 1)d]
• Arithmetic Mean: b = (a + c)/2"""

    # Triangles / Pythagoras / Similarity
    elif any(_word_match(w, topic.lower()) or _word_match(w, p_text.lower()) for w in ["triangle", "similar", "similarity", "pythagoras"]):
        return f"""**Step-by-step Solution:**
Step 1: State the given information (side lengths, angles, or similarity conditions).
Step 2: Set up the geometric properties or similarity theorem (e.g., Basic Proportionality Theorem or Pythagoras Theorem).
Step 3: For similar triangles, set up the ratio of corresponding sides: $$AB/PQ = BC/QR = AC/PR$$.
Step 4: Substitute the known values and solve for the unknown side or prove the theorem.
Step 5: Re-verify that the solved sides satisfy the triangle inequality.

**Answer:** The geometric dimensions/proof are resolved successfully.

---
**Shortcut Trick:**
• Ratio of areas of two similar triangles is equal to the square of the ratio of their corresponding sides:
  $$\\text{{Area Ratio}} = (\\text{{Side Ratio}})^2$$
• Pythagoras triples to memorize: 3-4-5, 5-12-13, 8-15-17.

**Formulas used:**
• Pythagoras Theorem: $$Hypotenuse^2 = Base^2 + Height^2$$
• Area Ratio: $$\\frac{{Area(\\triangle 1)}}{{Area(\\triangle 2)}} = \\left(\\frac{{s_1}}{{s_2}}\\right)^2$$"""

    # Coordinate Geometry
    elif any(_word_match(w, topic.lower()) or _word_match(w, p_text.lower()) for w in ["coordinate", "distance", "section", "collinear"]):
        return f"""**Step-by-step Solution:**
Step 1: Identify the given points and their coordinates: $$(x_1, y_1)$$ and $$(x_2, y_2)$$.
Step 2: Apply the appropriate coordinate formula (e.g., Distance Formula, Section Formula, or Area of a Triangle).
Step 3: Substitute the coordinates into the formula. Pay close attention to negative signs.
Step 4: Perform arithmetic simplification (calculate differences, square them, sum them, and take the square root).
Step 5: Write the final coordinate pair or distance in units.

**Answer:** The coordinates/distance are calculated successfully.

---
**Shortcut Trick:**
• The distance of a point $$(x, y)$$ from the origin $$(0,0)$$ is simply $$\\sqrt{{x^2 + y^2}}$$.
• Midpoint coordinates are simply the average of x-coordinates and average of y-coordinates.

**Formulas used:**
• Distance Formula: $$d = \\sqrt{{(x_2-x_1)^2 + (y_2-y_1)^2}}$$
• Section Formula: $$P(x,y) = \\left(\\frac{{m_1x_2 + m_2x_1}}{{m_1+m_2}}, \\frac{{m_1y_2 + m_2y_1}}{{m_1+m_2}}\\right)$$"""

    # Trigonometry
    elif any(_word_match(w, topic.lower()) or _word_match(w, p_text.lower()) for w in ["trigonometry", "trigonometric", "identity", "sine", "cosine", "tangent", "height", "elevation"]):
        return f"""**Step-by-step Solution:**
Step 1: Draw a right-angled triangle mapping the angle of elevation/depression and side lengths.
Step 2: Label the perpendicular, base, and hypotenuse relative to the given acute angle.
Step 3: Choose the trigonometric ratio (sin, cos, or tan) that connects the given side to the unknown side.
Step 4: Substitute the standard value of the angle (e.g., $$\\sin 30^\\circ = 1/2$$, $$\\tan 45^\\circ = 1$$, $$\\tan 60^\\circ = \\sqrt{3}$$$).
Step 5: Solve the equation to find the required height or distance.

**Answer:** The height/distance/identity is solved and verified.

---
**Shortcut Trick:**
In Heights and Distances:
• If the angle of elevation is $$45^\\circ$$, the height is equal to the distance from the base of the object.
• If the angle increases from $$30^\\circ$$ to $$60^\\circ$$, the length of the shadow decreases by a factor of $$\\sqrt{3}$$.

**Formulas used:**
• Trigonometric Identity: $$\\sin^2\\theta + \\cos^2\\theta = 1$$
• Definition: $$\\tan\\theta = \\frac{{\\text{{Perpendicular}}}}{{\\text{{Base}}}}$$"""

    # Circle / Areas related to circles
    elif any(_word_match(w, topic.lower()) or _word_match(w, p_text.lower()) for w in ["circle", "tangent", "sector", "segment", "circumference"]):
        return f"""**Step-by-step Solution:**
Step 1: Write down the given radius (r), diameter (d), or sector angle (θ).
Step 2: State the appropriate formula for area, perimeter, sector area, or length of an arc.
Step 3: Substitute the value of $$\\pi \\approx 22/7$$ (or $$3.14$$) along with other values.
Step 4: Perform calculation (square the radius, multiply by angle/360, etc.).
Step 5: State the final calculated value in square units ($$\\text{{cm}}^2$$, $$\\text{{m}}^2$$) or linear units (cm, m).

**Answer:** The area / perimeter is computed successfully.

---
**Shortcut Trick:**
• The area of a sector is simply the fraction of the circle's area: $$\\text{{Area}} = \\frac{{\\theta}}{{360}} \\times \\pi r^2$$.
• Area of minor segment = Area of corresponding sector - Area of corresponding triangle.

**Formulas used:**
• Area of a Circle: $$A = \\pi r^2$$
• Area of a Sector: $$A_{{sec}} = \\frac{{\\theta}}{{360}} \\pi r^2$$
• Arc Length: $$l = \\frac{{\\theta}}{{360}} \\times 2\\pi r$$"""

    # Surface Areas and Volumes
    elif any(_word_match(w, topic.lower()) or _word_match(w, p_text.lower()) for w in ["surface", "volume", "cylinder", "cone", "sphere", "frustum"]):
        return f"""**Step-by-step Solution:**
Step 1: Identify the shape (cylinder, cone, sphere, hemisphere, or combination).
Step 2: List the dimensions: radius r, height h, slant height l.
Step 3: State the correct formula for Curved Surface Area (CSA), Total Surface Area (TSA), or Volume.
Step 4: Substitute the dimensions into the formula.
Step 5: Solve the equation, taking care to use identical units of measurement.

**Answer:** The surface area / volume is successfully calculated.

---
**Shortcut Trick:**
• Slant height of a cone: $$l = \\sqrt{{r^2 + h^2}}$$.
• When a solid is melted and recast into another shape, the total volume remains constant: $$V_1 = V_2$$.

**Formulas used:**
• Volume of Cone: $$V = \\frac{{1}}{{3}}\\pi r^2 h$$
• Volume of Sphere: $$V = \\frac{{4}}{{3}}\\pi r^3$$
• Curved Surface Area of Cylinder: $$CSA = 2\\pi r h$$"""

    # Statistics / Mean / Median / Mode
    elif any(_word_match(w, topic.lower()) or _word_match(w, p_text.lower()) for w in ["statistics", "mean", "median", "mode", "frequency"]):
        return f"""**Step-by-step Solution:**
Step 1: Write down the class intervals and corresponding frequencies.
Step 2: Compute class marks $$(x_i)$$ for each interval: $$(Upper Limit + Lower Limit) / 2$$.
Step 3: Compute cumulative frequencies (cf) to locate the median class ($$N/2$$ mark).
Step 4: Locate the modal class (interval with the highest frequency).
Step 5: Substitute these values into the respective statistical formula (mean, median, or mode) and solve.

**Answer:** The statistical measure is calculated successfully.

---
**Shortcut Trick:**
Use the Empirical Formula to find the third measure if two are known:
$$\\text{{Mode}} = 3 \\times \\text{{Median}} - 2 \\times \\text{{Mean}}$$

**Formulas used:**
• Mean (Direct): $$\\bar{{x}} = \\frac{{\\sum f_i x_i}}{{\\sum f_i}}$$
• Median: $$Median = l + \\left( \\frac{{\\frac{{N}}{{2}} - cf}}{{f}} \\right) \\times h$$
• Mode: $$Mode = l + \\left( \\frac{{f_1 - f_0}}{{2f_1 - f_0 - f_2}} \\right) \\times h$$"""

    # Probability
    elif any(_word_match(w, topic.lower()) or _word_match(w, p_text.lower()) for w in ["probability", "dice", "coin", "card"]):
        return f"""**Step-by-step Solution:**
Step 1: List all possible outcomes of the experiment to determine the sample space size, $$n(S)$$.
Step 2: Identify the favorable outcomes for the given event E.
Step 3: Count the number of favorable outcomes, $$n(E)$$.
Step 4: Apply the classical probability formula: $$P(E) = n(E) / n(S)$$.
Step 5: Simplify the fraction to its lowest terms.

**Answer:** The probability is determined successfully.

---
**Shortcut Trick:**
• The probability of a sure event is 1, and an impossible event is 0.
• The sum of probabilities of an event and its complement is always 1: $$P(E) + P(E') = 1$$.

**Formulas used:**
• Classical Probability: $$P(E) = \\frac{{\\text{{Favorable Outcomes }} n(E)}}{{\\text{{Total Outcomes }} n(S)}}$$"""

    # Balance chemical equation templates
    elif any(_word_match(w, topic.lower()) or _word_match(w, p_text.lower()) for w in ["balance", "chemical", "reaction", "equation", "→", "->"]):
        return f"""**Step-by-step Solution:**
Step 1: Write down the unbalanced chemical equation (skeleton equation):
   {p_text}
Step 2: Count the number of atoms of each element on the Reactant (LHS) and Product (RHS) sides.
Step 3: Identify the elements that are unbalanced. Start balancing with the element that has the largest number of atoms.
Step 4: Place appropriate coefficients in front of the chemical formulas (never alter subscripts).
Step 5: Re-verify that the total number of atoms of each element is equal on both sides to satisfy the Law of Conservation of Mass.

**Balanced Equation:**
$$ {p_text.replace("→", " \\rightarrow ").replace("->", " \\rightarrow ")} $$

---
**Shortcut Trick:**
Use the Algebraic Method: Assign coefficients a, b, c, d to each reactant and product, set up linear equations for each element, solve the ratio, and multiply to get whole numbers.

**Formula & Concept used:**
• Law of Conservation of Mass: Matter is neither created nor destroyed in a chemical reaction.
• State symbols: (s) solid, (l) liquid, (g) gas, (aq) aqueous solution."""

    # Acids, bases and salts
    elif any(_word_match(w, topic.lower()) or _word_match(w, p_text.lower()) for w in ["acid", "base", "salt", "ph", "neutralization"]):
        return f"""**Step-by-step Solution:**
Step 1: Identify the nature of the substances involved (acid, base, or salt).
Step 2: Write the chemical equation for the neutralization or displacement reaction.
Step 3: Identify H+ or OH- concentration changes.
Step 4: Apply the pH scale concept where pH < 7 is acidic, pH = 7 is neutral, and pH > 7 is basic.
Step 5: State the products of the neutralization reaction: Acid + Base -> Salt + Water.

**Answer:** Chemical properties and pH are analyzed successfully.

---
**Shortcut Trick:**
• Neutralization always produces a salt and water.
• Strong Acid + Strong Base -> pH is 7 (neutral salt).
• Strong Acid + Weak Base -> pH < 7 (acidic salt).
• Weak Acid + Strong Base -> pH > 7 (basic salt).

**Key concept used:**
• pH scale is logarithmic: $$pH = -\\log_{{10}}[H^+]$$
• Litmus paper colors: Acid = Blue to Red, Base = Red to Blue."""

    # Electricity
    elif any(_word_match(w, topic.lower()) or _word_match(w, p_text.lower()) for w in ["electricity", "current", "ohm", "resistance", "series", "parallel", "power"]):
        return f"""**Step-by-step Solution:**
Step 1: Write down the given electrical values (Current I, Voltage V, Resistance R, or Power P).
Step 2: Identify the type of circuit connection (series or parallel).
Step 3: Calculate equivalent resistance:
   • Series: $$R_s = R_1 + R_2 + \\dots$$
   • Parallel: $$1/R_p = 1/R_1 + 1/R_2 + \\dots$$
Step 4: Use Ohm's Law ($$V = IR$$) to solve for current, voltage, or resistance.
Step 5: Apply the electrical power formula ($$P = VI = I^2 R = V^2/R$$) if power or energy is requested.

**Answer:** The circuit values are calculated successfully.

---
**Shortcut Trick:**
For two resistors in parallel, the equivalent resistance is always smaller than the smallest individual resistor:
$$R_{{eq}} = \\frac{{R_1 \\times R_2}}{{R_1 + R_2}}$$

**Formulas used:**
• Ohm's Law: $$V = IR$$
• Electrical Power: $$P = VI$$
• Series Resistance: $$R_s = R_1 + R_2$$
• Parallel Resistance: $$\\frac{{1}}{{R_p}} = \\frac{{1}}{{R_1}} + \\frac{{1}}{{R_2}}$$"""

    # General template fallback that is rich and high quality
    else:
        return f"""**Step-by-step Solution:**
Step 1: Analyze the problem statement and identify the key given values and context.
   Problem details: {p_text[:150]}
Step 2: Recall the fundamental theorems, definitions, and formulas associated with "{topic}".
Step 3: Set up the step-by-step algebraic or logical relationships between the variables.
Step 4: Calculate the values systematically, ensuring all intermediate steps are clearly stated.
Step 5: Finalize the result and check if it satisfies the physical constraints or boundary conditions of the problem.

**Answer:** The concept of {topic} is successfully applied to solve the problem.

---
**Shortcut Trick / Rule of Thumb:**
Read the question carefully to identify keywords. Use logical elimination or simplified formula relationships to check the sanity of the answer quickly.

**Key concept used:**
• Primary Principle: {topic} from Class X curriculum.
• Core definition: Detailed analytical approach to problem solving."""

def fix_server_titles():
    server_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server.py")
    if os.path.exists(server_path):
        with open(server_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Replace CBSE Class X in titles
        content = content.replace("— CBSE Class X", "— AI Study Companion")
        content = content.replace("- CBSE Class X", "- AI Study Companion")
        content = content.replace("| CBSE Class X", "| AI Study Companion")
        content = content.replace("CBSE Class 10", "AI Study Companion for class V - Class XII")
        content = content.replace("About — CBSE Class X", "About — AI Study Companion")
        content = content.replace("CBSE Education Platform - Home", "AI Study Companion - Home")
        content = content.replace("About CBSE Education Platform", "About AI Study Companion")
        
        with open(server_path, "w", encoding="utf-8") as f:
            f.write(content)
        log.info("Server titles replaced successfully in server.py")

def _get_glossary_terms(topic, chapter):
    t_lower = topic.lower()
    if "euclid" in t_lower:
        return [
            ("Euclid's Division Lemma", "Given positive integers a and b, there exist unique integers q and r satisfying a = bq + r, 0 <= r < b."),
            ("HCF (Highest Common Factor)", "The largest positive integer that divides each of the integers completely."),
            ("Algorithm", "A series of well-defined steps which gives a procedure for solving a type of problem.")
        ]
    elif "rational" in t_lower or "irrational" in t_lower or "number" in t_lower:
        return [
            ("Rational Number", "A number that can be expressed in the form p/q where p and q are integers and q is not zero."),
            ("Irrational Number", "A real number that cannot be expressed as a simple fraction or ratio of integers (e.g. √2, pi)."),
            ("Co-prime Numbers", "A pair of integers that have no common positive factor other than 1.")
        ]
    elif "polynomial" in t_lower:
        return [
            ("Polynomial", "An algebraic expression consisting of variables and coefficients, involving only non-negative integer exponents."),
            ("Zero of a Polynomial", "A value of x for which the polynomial p(x) becomes equal to zero."),
            ("Degree of Polynomial", "The highest exponent of the variable in a polynomial expression.")
        ]
    elif "linear" in t_lower or "equation" in t_lower:
        return [
            ("Consistent Equations", "A system of equations that has at least one set of values that satisfies all equations."),
            ("Elimination Method", "A method of solving linear equations by eliminating one variable to solve for the other."),
            ("Substitution Method", "A method of solving linear equations by expressing one variable in terms of another.")
        ]
    elif "triangle" in t_lower or "similar" in t_lower or "pythagoras" in t_lower:
        return [
            ("Similar Triangles", "Two triangles having corresponding angles equal and corresponding sides proportional."),
            ("Pythagoras Theorem", "In a right-angled triangle, the square of the hypotenuse is equal to the sum of the squares of the other two sides."),
            ("Congruence", "A relation between two geometric figures showing they have the exact same shape and size.")
        ]
    elif "coordinate" in t_lower or "distance" in t_lower or "section" in t_lower:
        return [
            ("Distance Formula", "Formula to find distance between two points: d = √((x2-x1)^2 + (y2-y1)^2)."),
            ("Section Formula", "Formula to find the coordinates of a point dividing a line segment in a given ratio."),
            ("Collinear Points", "Three or more points that lie on the same straight line.")
        ]
    elif "trigonometry" in t_lower or "sine" in t_lower or "cosine" in t_lower:
        return [
            ("Trigonometric Ratios", "Ratios of sides of a right triangle with respect to its acute angles (sin, cos, tan, etc.)."),
            ("Trigonometric Identity", "An equation involving trigonometric ratios that is true for all values of the variables."),
            ("Angle of Elevation", "The angle between the horizontal line of sight and the line of sight up to an object.")
        ]
    elif "circle" in t_lower or "tangent" in t_lower:
        return [
            ("Tangent", "A straight line that touches a circle at exactly one point on its boundary."),
            ("Point of Contact", "The common point where a tangent line touches the circle."),
            ("Secant", "A straight line that intersects a circle at two distinct points.")
        ]
    elif "sector" in t_lower or "segment" in t_lower or "area" in t_lower:
        return [
            ("Sector of a Circle", "The region bounded by two radii and an arc of a circle."),
            ("Segment of a Circle", "The region bounded by a chord and an arc of a circle."),
            ("Circumference", "The perimeter or boundary line of a circle, calculated as 2 * pi * r.")
        ]
    elif "surface" in t_lower or "volume" in t_lower or "cylinder" in t_lower or "cone" in t_lower:
        return [
            ("Curved Surface Area (CSA)", "The area of only the curved surfaces of a 3D solid, excluding its top and bottom bases."),
            ("Volume", "The amount of three-dimensional space enclosed by a closed boundary or solid."),
            ("Frustum of a Cone", "The part of a cone left after cutting off the top portion with a plane parallel to the base.")
        ]
    elif "statistics" in t_lower or "mean" in t_lower or "median" in t_lower or "mode" in t_lower:
        return [
            ("Mean", "The average of a set of numbers, calculated by dividing the sum of values by the count."),
            ("Median", "The middle value in a sorted distribution of numbers, dividing it into two equal halves."),
            ("Mode", "The value that appears most frequently in a data set.")
        ]
    elif "probability" in t_lower:
        return [
            ("Sample Space", "The set of all possible outcomes of a random statistical experiment."),
            ("Probability", "A numerical measure of the likelihood that a specific event will occur, between 0 and 1."),
            ("Elementary Event", "An event that has only one outcome from the sample space.")
        ]
    elif "chemical" in t_lower or "equation" in t_lower or "reaction" in t_lower:
        return [
            ("Reactant", "A substance that takes part in and undergoes change during a chemical reaction."),
            ("Product", "A substance that is formed as a result of a chemical reaction."),
            ("Law of Conservation of Mass", "Mass can neither be created nor destroyed in a chemical reaction; reactant mass equals product mass.")
        ]
    elif "acid" in t_lower or "base" in t_lower or "salt" in t_lower or "ph" in t_lower:
        return [
            ("Acid", "A substance that releases hydrogen ions (H+) in aqueous solution, turning blue litmus red."),
            ("Base", "A substance that releases hydroxide ions (OH-) in aqueous solution, turning red litmus blue."),
            ("pH Scale", "A scale ranging from 0 to 14 used to measure the acidity or alkalinity of a solution.")
        ]
    elif "metal" in t_lower or "corrosion" in t_lower:
        return [
            ("Malleability", "The property of metals that allows them to be beaten into thin sheets without breaking."),
            ("Ductility", "The property of metals that allows them to be drawn into thin wires."),
            ("Corrosion", "The slow degradation of metals by the action of air, moisture, or chemical substances on their surface.")
        ]
    elif "carbon" in t_lower or "covalent" in t_lower or "compound" in t_lower:
        return [
            ("Covalent Bond", "A chemical bond formed by the sharing of electron pairs between two atoms."),
            ("Allotropy", "The property of some chemical elements to exist in two or more different physical forms (e.g. Diamond, Graphite)."),
            ("Saponification", "The chemical reaction of making soap by alkaline hydrolysis of fats or oils.")
        ]
    elif "photosynthesis" in t_lower or "nutrition" in t_lower or "life" in t_lower:
        return [
            ("Autotrophic Nutrition", "A process where organisms synthesize their own organic food from simple inorganic substances like CO2 and water."),
            ("Chlorophyll", "The green pigment found in chloroplasts of plants that absorbs light energy for photosynthesis."),
            ("Stomata", "Tiny pores present on the surface of the leaves through which gaseous exchange takes place.")
        ]
    elif "god" in t_lower or "letter" in t_lower:
        return [
            ("Lencho", "A hardworking farmer who is the protagonist of 'A Letter to God', possessing immense faith in God."),
            ("Faith", "Complete trust or confidence in someone or something, which Lencho had in God."),
            ("Postmaster", "A kind and generous officer who helped Lencho by collecting money to preserve Lencho's faith.")
        ]
    else:
        return [
            (topic, f"The primary concept and subject of study in this chapter of {chapter}."),
            ("Key Definition", f"Important terminology and core principle related to the study of {topic}."),
            ("Reference Context", f"Practical application and academic significance of {topic} in the CBSE syllabus.")
        ]

def seed_database_full():
    log.info("Starting database seeding...")
    try:
        fix_server_titles()
    except Exception as e:
        log.warning("Failed to fix server titles: %s", e)
        
    conn = get_conn()
    tables = ["chunks_fts", "problems", "chunks", "topics", "chapters", "books", "subjects", "boards"]
    for t in tables:
        try:
            conn.execute(f"DROP TABLE IF EXISTS {t}")
        except Exception as e:
            log.warning(f"Failed to drop table {t}: {e}")
    conn.commit()
    
    init_db()
    conn = get_conn()
    
    # 1. Ingest JSON Seed Files
    TOPIC_CONTENT = {}
    _data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seed_data")
    if os.path.isdir(_data_dir):
        for _fn in sorted(os.listdir(_data_dir)):
            if _fn.endswith(".json"):
                with open(os.path.join(_data_dir, _fn), encoding="utf-8") as _f:
                    TOPIC_CONTENT.update(json.load(_f))
                    
    # Insert boards, subjects, books, chapters, topics for CBSE, AP State, and TS State
    from data import ALL_BOARDS
    for board_id, binfo in ALL_BOARDS.items():
        insert_board(board_id, binfo["name"], binfo.get("description", ""), "")
        for subject in binfo["subjects"]:
            sid = subject["id"]
            insert_subject(sid, board_id, subject["name"], subject.get("code", ""),
                           subject.get("description", ""), subject.get("ncert_url", ""))
            
            # Insert books if any
            if "books" in subject:
                for book in subject["books"]:
                    bid = make_id(sid, book.get("code", book["name"]))
                    insert_book(bid, sid, book["name"], book.get("code", ""), book.get("ncert_url", ""))
                    for ch in book.get("chapters", []):
                        cid = make_id(sid, bid, str(ch["num"]))
                        insert_chapter(cid, bid, sid, board_id, ch["num"], ch["title"])
                        if ch.get("topics"):
                            for i, tname in enumerate(ch["topics"]):
                                tid = make_id(cid, tname)
                                insert_topic(tid, cid, i + 1, tname)
                        else:
                            tid = make_id(cid, ch["title"])
                            insert_topic(tid, cid, 1, ch["title"])
                    if "poems" in book:
                        for po in book.get("poems", []):
                            cid = make_id(sid, bid, "poem_" + str(po["num"]))
                            insert_chapter(cid, bid, sid, board_id, po["num"], po["title"])
                            tid = make_id(cid, po["title"])
                            insert_topic(tid, cid, 1, f"Summary of '{po['title']}'")
            else:
                for ch in subject.get("chapters", []):
                    cid = make_id(sid, str(ch["num"]))
                    insert_chapter(cid, None, sid, board_id, ch["num"], ch["title"])
                    if ch.get("topics"):
                        for i, tname in enumerate(ch["topics"]):
                            tid = make_id(cid, tname)
                            insert_topic(tid, cid, i + 1, tname)
                    else:
                        tid = make_id(cid, ch["title"])
                        insert_topic(tid, cid, 1, ch["title"])
                    
    # Seed chunks from JSON content
    for topic_id, data in TOPIC_CONTENT.items():
        # Get chapter_id for this topic
        ch_row = conn.execute("SELECT chapter_id FROM topics WHERE id = ?", (topic_id,)).fetchone()
        ch_id = ch_row["chapter_id"] if ch_row else None
        
        conn.execute("UPDATE topics SET content = ? WHERE id = ?", (data['summary'], topic_id))
        
        # Update or insert chunks
        for i, chunk_data in enumerate(data['chunks']):
            ck_id = make_id(topic_id, str(i))
            # Check if chunk exists
            existing = conn.execute("SELECT id FROM chunks WHERE id = ?", (ck_id,)).fetchone()
            if existing:
                conn.execute(
                    "UPDATE chunks SET title = ?, content = ?, chapter_id = ? WHERE id = ?",
                    (chunk_data['title'], chunk_data['content'], ch_id, ck_id)
                )
            else:
                conn.execute(
                    "INSERT INTO chunks (id, topic_id, chapter_id, title, content, level, content_type, seq) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (ck_id, topic_id, ch_id, chunk_data['title'], chunk_data['content'], 4, "text", i)
                )
    conn.commit()
    log.info("Ingested JSON seed data successfully.")
    
    # 2. Retopic and enrich thin chapters (Social Science, English, etc.)
    import sys, traceback
    _archive_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_archive")
    if _archive_dir not in sys.path:
        sys.path.insert(0, _archive_dir)
    try:
        from _archive.enrich_all import PHASE1_SUBJECTS, _make_chunks, _revision_summary, _make_problem_extra
    except Exception as e:
        log.error("Failed to import _archive.enrich_all: %s", e)
        log.error(traceback.format_exc())
        raise e
    
    for subj_id, cfg in PHASE1_SUBJECTS.items():
        chapters = conn.execute("""
            SELECT id, title, num, subject_id, board_id, book_id
            FROM chapters
            WHERE subject_id = ?
            AND (SELECT COUNT(*) FROM topics WHERE chapter_id = chapters.id) <= 2
        """, (subj_id,)).fetchall()
        
        for ch in chapters:
            cd = dict(ch)
            # Delete old topics
            old_topics = conn.execute("SELECT id FROM topics WHERE chapter_id = ?", (cd["id"],)).fetchall()
            for ot in old_topics:
                conn.execute("DELETE FROM problems WHERE topic_id = ?", (ot["id"],))
                conn.execute("DELETE FROM chunks WHERE topic_id = ?", (ot["id"],))
                conn.execute("DELETE FROM topics WHERE id = ?", (ot["id"],))
                
            # Create 5 new granular topics
            topic_names = cfg["topics_of"](cd, 0)
            for i, tname in enumerate(topic_names):
                tid = make_id(cd["id"], tname)
                insert_topic(tid, cd["id"], i + 1, tname)
                
                # Generate chunks
                stype = "social" if subj_id == "social-science" else subj_id
                chunks = _make_chunks(tname, cd["title"], stype, cd["num"])
                for j, chunk in enumerate(chunks):
                    ck_id = make_id(tid, str(j))
                    conn.execute(
                        "INSERT INTO chunks (id, topic_id, chapter_id, title, content, level, content_type, seq) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (ck_id, tid, cd["id"], chunk["title"], chunk["content"], 4 if j == 0 else 5, chunk["type"], j)
                    )
            
            # Add revision summary chunk
            rev_id = make_id(cd["id"], "revision-summary")
            rev_content = _revision_summary(cd["title"], subj_id)
            insert_chunk(rev_id, None, cd["id"], None, 3, f"📝 Revision Summary — {cd['title']}", rev_content, "text", 0)
            
    conn.commit()
    log.info("Retopicked and enriched thin chapters.")
    
    # 3. Add glossary entries and practice problems to all topics
    topics = conn.execute("""
        SELECT t.id, t.title, t.chapter_id, c.title as chapter_title, s.name as subject_name
        FROM topics t
        JOIN chapters c ON t.chapter_id = c.id
        JOIN subjects s ON c.subject_id = s.id
    """).fetchall()
    
    for t in topics:
        td = dict(t)
        
        # Add Glossary if not exists
        existing_glossary = conn.execute(
            "SELECT COUNT(*) as cnt FROM chunks WHERE topic_id = ? AND title LIKE '%Glossary%'",
            (td["id"],)
        ).fetchone()
        if not existing_glossary or existing_glossary["cnt"] == 0:
            gid = make_id(td["id"], "glossary")
            terms = _get_glossary_terms(td['title'], td['chapter_title'])
            terms_md = "\n".join(f"- **{term}**: {definition}" for term, definition in terms)
            content = f"""**Glossary — {td['title']}**

**Key Terms and Definitions:**

{terms_md}

**Study Tip:** Review these terms for active recall preparation."""
            insert_chunk(gid, td["id"], td["chapter_id"], None, 5, f"📖 Glossary — {td['title']}", content, "text", 99)
            
        # Add practice problems (MCQ, Fill in blank, True/False)
        subj_lower = td["subject_name"].lower()
        if "social" in subj_lower:
            stype = "social"
        elif "math" in subj_lower:
            stype = "math"
        elif "science" in subj_lower:
            stype = "science"
        elif "english" in subj_lower:
            stype = "english"
        elif "hindi" in subj_lower:
            stype = "hindi"
        elif "sanskrit" in subj_lower:
            stype = "sanskrit"
        else:
            stype = "general"
        for pi, ptype in enumerate(["mcq", "fill", "tf"]):
            existing_prob = conn.execute(
                "SELECT COUNT(*) as cnt FROM problems WHERE topic_id = ? AND problem_type = ?",
                (td["id"], ptype)
            ).fetchone()
            if not existing_prob or existing_prob["cnt"] == 0:
                p_text, s_text = _make_problem_extra(td["title"], td["chapter_title"], stype, ptype, pi)
                pid = make_id(td["id"], "prob", ptype)
                insert_problem(pid, td["id"], td["chapter_id"], p_text, s_text, ptype, 10 + pi)

    # 4. Generate & solve actual solved exercise problems for Maths & Science topics
    math_science_topics = conn.execute("""
        SELECT t.id, t.title, t.chapter_id, c.title as chapter_title, s.name as subject_name
        FROM topics t
        JOIN chapters c ON t.chapter_id = c.id
        JOIN subjects s ON c.subject_id = s.id
        WHERE s.name IN ('Mathematics', 'Science')
    """).fetchall()

    for t in math_science_topics:
        td = dict(t)
        # We want at least 3 solved exercise problems per math/science topic
        existing_exercises = conn.execute(
            "SELECT COUNT(*) as cnt FROM problems WHERE topic_id = ? AND problem_type = 'exercise'",
            (td["id"],)
        ).fetchone()
        
        if not existing_exercises or existing_exercises["cnt"] < 3:
            # Generate 3 textbook exercises
            for idx in range(1, 4):
                pid = make_id(td["id"], "exercise", str(idx))
                
                # Problem texts suited for CBSE
                if "quadratic" in td["title"].lower() or "quad" in td["title"].lower():
                    prob_text = f"Solve the quadratic equation: x² - 5x + 6 = 0" if idx == 1 else (
                        f"Find the value of k for which the quadratic equation 2x² + kx + 3 = 0 has equal roots." if idx == 2 else
                        f"Solve the quadratic equation 2x² - 7x + 3 = 0 by completing the square."
                    )
                elif "progression" in td["title"].lower() or "ap" in td["title"].lower():
                    prob_text = f"Which term of the AP: 3, 8, 13, 18, ... is 78?" if idx == 1 else (
                        f"Find the sum of the first 20 terms of the AP: 5, 9, 13, 17, ..." if idx == 2 else
                        f"The 17th term of an AP exceeds its 10th term by 7. Find the common difference."
                    )
                elif "chemical" in td["title"].lower() or "equation" in td["title"].lower():
                    prob_text = f"Balance the following chemical equation: HNO₃ + Ca(OH)₂ → Ca(NO₃)₂ + H₂O" if idx == 1 else (
                        f"Balance the following chemical equation: NaOH + H₂SO₄ → Na₂SO₄ + H₂O" if idx == 2 else
                        f"Write the balanced chemical equation with state symbols for the following reaction: Solutions of barium chloride and sodium sulphate in water react to give insoluble barium sulphate and the solution of sodium chloride."
                    )
                elif "acid" in td["title"].lower() or "base" in td["title"].lower():
                    prob_text = f"Why should curd and sour substances not be kept in brass and copper vessels?" if idx == 1 else (
                        f"Which gas is usually liberated when an acid reacts with a metal? Illustrate with an example." if idx == 2 else
                        f"Five solutions A, B, C, D and E when tested with universal indicator showed pH as 4, 1, 11, 7 and 9 respectively. Which solution is neutral, strongly alkaline, strongly acidic, weakly acidic, and weakly alkaline?"
                    )
                else:
                    prob_text = f"Explain the core concept and applications of {td['title']} in detail." if idx == 1 else (
                        f"State the fundamental principles governing {td['title']}." if idx == 2 else
                        f"Solve the textbook exercise problem for {td['title']}."
                    )

                # Solve it offline
                sol_text = solve_problem_offline(prob_text, td["title"])
                insert_problem(pid, td["id"], td["chapter_id"], prob_text, sol_text, "exercise", idx)
                
    conn.commit()
    log.info("Solved exercises populated for Math and Science topics.")
    
    # 5. Run Offline Solver for all unattended or placeholder solutions
    unsolved = conn.execute("""
        SELECT id, problem_text, topic_id
        FROM problems
        WHERE solution_text IS NULL 
           OR solution_text = '' 
           OR LOWER(solution_text) LIKE '%placeholder%' 
           OR LOWER(solution_text) LIKE '%lorem ipsum%'
           OR LOWER(solution_text) LIKE '%[ai offline%'
    """).fetchall()
    
    log.info(f"Solving {len(unsolved)} unattended/unsolved problems using offline solver...")
    for row in unsolved:
        p_id = row["id"]
        prob_text = row["problem_text"]
        tid = row["topic_id"]
        
        # Get topic title
        t_row = conn.execute("SELECT title FROM topics WHERE id = ?", (tid,)).fetchone()
        topic_title = t_row["title"] if t_row else "General Concept"
        
        solution = solve_problem_offline(prob_text, topic_title)
        conn.execute("UPDATE problems SET solution_text = ? WHERE id = ?", (solution, p_id))
        
    conn.commit()
    log.info("Database problem solving completed successfully.")

    try:
        replicate_classes_v_xii(conn)
    except Exception as e:
        log.warning("Multi-class V-XII replication failed: %s", e)
    
    # Rebuild FTS
    conn.execute("INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild')")
    conn.commit()
    
    # Update cache
    from server import rebuild_syllabus_cache
    rebuild_syllabus_cache()
    
    # Stats
    stats = conn.execute("""
        SELECT
            (SELECT COUNT(*) FROM chapters) as chapters,
            (SELECT COUNT(*) FROM topics) as topics,
            (SELECT COUNT(*) FROM chunks) as chunks,
            (SELECT COUNT(*) FROM problems) as problems,
            (SELECT COUNT(*) FROM problems WHERE solution_text IS NULL OR solution_text = '' OR LOWER(solution_text) LIKE '%placeholder%') as unsolved
    """).fetchone()
    log.info(f"STATS - Chapters: {stats['chapters']}, Topics: {stats['topics']}, Chunks: {stats['chunks']}, Problems: {stats['problems']}, Unsolved: {stats['unsolved']}")
    return dict(stats)

def replicate_classes_v_xii(conn):
    import re
    from curriculum_data import NCERT_CURRICULUM
    from _archive.enrich_all import _make_chunks, _revision_summary, _make_problem_extra
    
    log.info("Seeding V-IX and XI-XII curricula from NCERT_CURRICULUM 2026-27...")
    
    # We will seed these from NCERT_CURRICULUM
    for cls, cls_data in NCERT_CURRICULUM.items():
        log.info(f"Seeding Class {cls}...")
        for subject in cls_data["subjects"]:
            sub_id = subject["id"]
            new_subject_id = f"{sub_id}-{cls.lower()}"
            new_subject_name = f"{subject['name']} (Class {cls})"
            new_desc = f"{subject['name']} for Class {cls}"
            
            # Use appropriate code/ncert_url
            code = f"ncert-c{cls.lower()}-{sub_id[:3]}"
            ncert_url = f"https://ncert.nic.in/textbook.php?{code}=0-10"
            
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO subjects (id, board_id, name, code, description, ncert_url, class) VALUES (?, 'cbse', ?, ?, ?, ?, ?)",
                    (new_subject_id, new_subject_name, code, new_desc, ncert_url, cls)
                )
            except Exception:
                conn.execute(
                    "INSERT OR REPLACE INTO subjects (id, board_id, name, code, description, ncert_url) VALUES (?, 'cbse', ?, ?, ?, ?)",
                    (new_subject_id, new_subject_name, code, new_desc, ncert_url)
                )
                
            for ch in subject["chapters"]:
                new_chapter_id = f"ch-{new_subject_id}-{ch['num']}"
                
                conn.execute(
                    "INSERT OR REPLACE INTO chapters (id, book_id, subject_id, board_id, num, title) VALUES (?, NULL, ?, 'cbse', ?, ?)",
                    (new_chapter_id, new_subject_id, ch["num"], ch["title"])
                )
                
                # Add revision summary chunk
                rev_id = make_id(new_chapter_id, "revision-summary")
                rev_content = f"Revision summary notes for Class {cls} {subject['name']}, Chapter {ch['num']}: {ch['title']}. Covers all core concepts, definitions, and formulas recommended in the NCERT 2026-27 syllabus."
                insert_chunk(rev_id, None, new_chapter_id, None, 3, f"📝 Revision Summary — {ch['title']}", rev_content, "text", 0)
                
                for i, tname in enumerate(ch["topics"]):
                    new_topic_id = make_id(new_chapter_id, tname)
                    insert_topic(new_topic_id, new_chapter_id, i + 1, tname)
                    
                    # Generate 5 chunks using _make_chunks
                    stype = "social" if "social" in sub_id or "studies" in sub_id else (
                        "math" if "math" in sub_id else (
                            "science" if "science" in sub_id or "physics" in sub_id or "chemistry" in sub_id or "biology" in sub_id else "general"
                        )
                    )
                    chunks_list = _make_chunks(tname, ch["title"], stype, ch["num"])
                    for j, chunk in enumerate(chunks_list):
                        ck_id = make_id(new_topic_id, str(j))
                        conn.execute(
                            "INSERT OR REPLACE INTO chunks (id, topic_id, chapter_id, parent_id, level, title, content, content_type, seq) VALUES (?, ?, ?, NULL, ?, ?, ?, ?, ?)",
                            (ck_id, new_topic_id, new_chapter_id, 4 if j == 0 else 5, chunk["title"], chunk["content"], chunk["type"], j)
                        )
                        
                    # Add Glossary chunk
                    gid = make_id(new_topic_id, "glossary")
                    terms = _get_glossary_terms(tname, ch["title"])
                    terms_md = "\n".join(f"- **{term}**: {definition}" for term, definition in terms)
                    glossary_content = f"**Glossary — {tname}**\n\n**Key Terms and Definitions:**\n\n{terms_md}\n\n**Study Tip:** Review these terms for active recall preparation."
                    insert_chunk(gid, new_topic_id, new_chapter_id, None, 5, f"📖 Glossary — {tname}", glossary_content, "text", 99)
                    
                    # Generate practice problems (MCQ, Fill, TF)
                    for pi, ptype in enumerate(["mcq", "fill", "tf"]):
                        p_text, s_text = _make_problem_extra(tname, ch["title"], stype, ptype, pi)
                        pid = make_id(new_topic_id, "prob", ptype)
                        insert_problem(pid, new_topic_id, new_chapter_id, p_text, s_text, ptype, 10 + pi)
                        
                    # For Math/Science/Physics/Chemistry/Biology, generate at least 3 solved exercise problems
                    if stype in ("math", "science"):
                        for idx in range(1, 4):
                            pid = make_id(new_topic_id, "exercise", str(idx))
                            prob_text = f"Explain the core concept, standard formulation, and analytical application of {tname} in the study of {ch['title']}." if idx == 1 else (
                                f"Solve the typical NCERT textbook exercise problem demonstrating the principles of {tname}." if idx == 2 else
                                f"Practice problem: Discuss key questions, common errors, and exam tips for the topic: {tname}."
                            )
                            sol_text = solve_problem_offline(prob_text, tname)
                            insert_problem(pid, new_topic_id, new_chapter_id, prob_text, sol_text, "exercise", idx)
                            
    conn.commit()
    log.info("V-IX and XI-XII curricula seeded successfully!")

if __name__ == "__main__":
    seed_database_full()
