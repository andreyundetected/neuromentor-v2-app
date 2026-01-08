import json
import sqlite3


user_id = 23


DB_PATH = "neuromentor.db"


conn = sqlite3.connect(DB_PATH)


cursor = conn.cursor()


result = cursor.fetchone()


ui = [
    {
      "course": {
        "0_topic": "Algebra",
        "1_initial_level": "Understood basic arithmetic and fractions, and started on linear equations.",
        "2_target_level": "Understand and solve linear equations, quadratic equations, systems of equations, polynomials, and factoring.",
        "3_name": "Mathematics. From fractions to quadratic equations",
        "4_structure": [
          {
            "0_topic": "Introduction to Algebraic Expressions",
            "1_description": "A review of algebraic expressions, including variables, coefficients, and basic operations.",
            "2_instructions_for_generating_lessons": "Generate 2-3 lessons covering simplification of expressions, combining like terms, and basic operations with polynomials.",
            "3_lessons": [
              {
                "description": "This lesson introduces you to the building blocks of algebraic expressions: variables and coefficients. We'll explore what variables are and how coefficients work alongside these variables to form expressions. Practical examples will help you see these concepts in action, and interactive exercises will reinforce your learning.",
                "name": "Understanding Variables and Coefficients"
              },
              {
                "description": "In this lesson, we'll dive into the process of simplifying algebraic expressions. You'll learn how to identify like terms and apply basic operations to simplify expressions. Through guided practice problems, you'll build confidence in handling these simplifications on your own.",
                "name": "Simplifying Algebraic Expressions"
              },
              {
                "description": "This lesson focuses on the basics of polynomials, a key component of algebraic expressions. We'll discuss how to perform basic operations like addition, subtraction, and multiplication of polynomials. With a focus on understanding polynomial terms and their interactions, you'll work through examples and interactive scenarios to solidify your skills.",
                "name": "Basics of Working with Polynomials"
              }
            ]
          },
          {
            "0_topic": "Linear Equations and Their Solutions",
            "1_description": "Understanding linear equations, methods of solving them, and their applications.",
            "2_instructions_for_generating_lessons": "Develop 3 -4 lessons that cover solving linear equations, equations with fractions, and word problems involving linear equations.",
            "3_lessons": [
              {
                "description": "This lesson covers the fundamental concepts of linear equations, including how to identify them and the basic principles behind solving them. Students will learn how to isolate variables and simplify expressions to find solutions.",
                "name": "Introduction to Linear Equations"
              },
              {
                "description": "Building on basic linear equations, this lesson introduces equations involving fractions. Students will learn techniques to handle fractions effectively and solve equations that incorporate fractional coefficients or constants.",
                "name": "Solving Linear Equations with Fractions"
              },
              {
                "description": "This lesson focuses on applying linear equations to solve real-world word problems. Students will develop skills to translate problem statements into mathematical equations and find solutions, understanding how linear equations model real-life scenarios.",
                "name": "Applications of Linear Equations: Word Problems"
              },
              {
                "description": "In this lesson, students will explore more advanced methods for solving linear equations, such as using different forms of equations and exploring systems of linear equations as an introduction to more complex algebraic concepts.",
                "name": "Advanced Techniques in Solving Linear Equations"
              }
            ]
          },
          {
            "0_topic": "Systems of Linear Equations",
            "1_description": "Solving systems of equations using various methods and understanding their applications.",
            "2_instructions_for_generating_lessons": "Generate 5 lessons on solving systems using substitution, elimination, and graphical methods, including application problems.",
            "3_lessons": [
              {
                "description": "Understand the concept of systems of linear equations and learn about the different methods used to solve them. Discuss real-world scenarios where these systems can be applied.",
                "name": "Introduction to Systems of Linear Equations"
              },
              {
                "description": "Learn how to solve systems of linear equations using the substitution method. Practice this method with guided examples and exercises to build confidence.",
                "name": "Solving Systems Using Substitution Method"
              },
              {
                "description": "Explore the elimination method for solving systems of linear equations. This lesson includes step-by-step examples and exercises to reinforce learning.",
                "name": "Solving Systems Using Elimination Method"
              },
              {
                "description": "Discover how to solve systems of linear equations graphically. Learn how to interpret the graphical representations and relate them to algebraic solutions.",
                "name": "Graphical Method for Solving Systems of Equations"
              },
              {
                "description": "Apply your knowledge by solving real-world problems using systems of equations. This lesson focuses on word problems and scenarios where multiple equations are set up and solved using the methods learned.",
                "name": "Application of Systems of Linear Equations"
              }
            ]
          },
          {
            "0_topic": "Introduction to Quadratic Equations",
            "1_description": "An overview of quadratic equations, their forms, and key properties.",
            "2_instructions_for_generating_lessons": "Develop 2-3 lessons introducing standard form, identifying key characteristics like vertex and axis of symmetry, and basic problem-solving.",
            "3_lessons": [
              {
                "description": "This lesson introduces students to the concept of quadratic equations, explaining what they are and why they are important in algebra. It covers the basic form of quadratic equations and provides a historical context to pique interest.",
                "name": "Understanding Quadratic Equations: An Introduction"
              },
              {
                "description": "This lesson dives into the standard form of a quadratic equation, ax^2 + bx + c = 0. It teaches students how to identify and write equations in this form, explaining each component's role in shaping the parabola.",
                "name": "Forms of Quadratic Equations: Standard Form Explained"
              },
              {
                "description": "In this lesson, students learn how to determine the vertex and axis of symmetry of a parabola from the quadratic equation. It explains these concepts with visual aids and examples, making connections to real-world parabolic graphs.",
                "name": "Key Characteristics: Identifying the Vertex and Axis of Symmetry"
              },
              {
                "description": "This lesson introduces basic methods for solving quadratic equations, such as factoring and using the quadratic formula. It includes practice problems to solidify understanding and encourages students to explore these methods interactively.",
                "name": "Solving Quadratic Equations: Basic Approaches"
              }
            ]
          },
          {
            "0_topic": "Solving Quadratic Equations",
            "1_description": "Exploring different methods for solving quadratic equations, including factoring and formulas.",
            "2_instructions_for_generating_lessons": "Create 6 lessons covering factoring, completing the square, and the quadratic formula, with real-world applications.",
            "3_lessons": [
              {
                "description": "Explore the basics of factoring quadratic equations. Learn how to rewrite quadratics as the product of two linear expressions and solve them. Utilize easy-to-understand examples to illustrate the technique and its application in real-world scenarios, such as calculating areas.",
                "name": "Introduction to Factoring Quadratic Equations"
              },
              {
                "description": "Delve deeper into more complex factoring strategies. Learn how to identify and apply special factorization patterns like the difference of squares and perfect square trinomial. Examine examples from physics and daily life to illustrate the importance of choosing the right method for efficiency.",
                "name": "Advanced Factoring Techniques"
              },
              {
                "description": "Understand how to solve quadratic equations by completing the square. Start with the method fundamentals and progress to its application in deriving the quadratic formula. Discuss practical uses, such as optimizing functions in economics and physics, to demonstrate its importance.",
                "name": "Completing the Square: Method and Applications"
              },
              {
                "description": "Introduce the quadratic formula as a universal method for solving any quadratic equation. Cover the derivation, practical implementation, and significance. Use real-world scenarios such as projectile motion and investment calculations to provide context and application.",
                "name": "Exploring the Quadratic Formula"
              },
              {
                "description": "Compare and contrast the different methods of solving quadratic equations. Highlight the strengths and considerations of each method to empower students to choose the most efficient strategy depending on the problem at hand. Include examples from engineering and design.",
                "name": "Comparing Methods: Choosing the Right Approach"
              },
              {
                "description": "Explore diverse applications of quadratic equations in real-world contexts. Examine scenarios in physics, finance, engineering, and construction where quadratic equations are indispensable. Encourage problem-solving using examples that connect math with daily life challenges.",
                "name": "Real-World Applications of Quadratic Equations"
              }
            ]
          }
        ],
        "5_categories": [
          "Algebra",
          "Beginner",
          "Mathematics"
        ],
        "6_teaching_style": "friendly",
        "7_lecture_type": "audio"
      },
      "course_settings": {"lesson":"Understanding Variables and Coefficients"}
    }
  ]


if result:
    updated_course_info = json.dumps(ui, ensure_ascii=False)
    cursor.execute("UPDATE user SET course_info = ? WHERE id = ?", (updated_course_info, user_id))
    conn.commit()
