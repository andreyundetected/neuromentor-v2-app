def generate_default_recommendations(language):
    base_recommendation = []
    if language == "ru":
        base_recommendation = [
            {
                "recommendation_name": "Алгебра для 7 класса",
                "base_json": {
                    "0_topic": "Алгебра",
                    "1_initial_level": "",
                    "2_target_level": "",
                    "3_name": "Курс по Алгебре",
                    "4_structure": [],
                    "5_categories": ["Математика", "Алгебра", "Школа"],
                },
                "start_message": "Привет! Давай начнем создавать курс по алгебре. Что последнее ты прошел в этой теме?"
            },
            {
                "recommendation_name": "Физика уровня средней школы",
                "base_json": {
                    "0_topic": "Физика",
                    "1_initial_level": "",
                    "2_target_level": "",
                    "3_name": "Курс по физике",
                    "4_structure": [],
                    "5_categories": ["Физика", "Школа"],
                },
                "start_message": "Привет! Давай начнем создавать курс по физике. Что последнее ты прошел в этой теме?"
            },
            {
                "recommendation_name": "Химия для начинающих",
                "base_json": {
                    "0_topic": "Химия",
                    "1_initial_level": "",
                    "2_target_level": "",
                    "3_name": "Курс по химии",
                    "4_structure": [],
                    "5_categories": ["Химия", "Школа"],
                },
                "start_message": "Привет! Давай начнем создавать курс по химии. Что последнее ты прошел в этой теме?"
            },
            {
                "recommendation_name": "Биология средних классов",
                "base_json": {
                    "0_topic": "Биология",
                    "1_initial_level": "",
                    "2_target_level": "",
                    "3_name": "Курс по биологии",
                    "4_structure": [],
                    "5_categories": ["Биология", "Школа"],
                },
                "start_message": "Привет! Давай начнем создавать курс по биологии. Что последнее ты прошел в этой теме?"
            },
            {
                "recommendation_name": "Геометрия. Средняя школа",
                "base_json": {
                    "0_topic": "Геометрия",
                    "1_initial_level": "",
                    "2_target_level": "",
                    "3_name": "Курс по геометрии",
                    "4_structure": [],
                    "5_categories": ["Математика", "Геометрия", "Школа"],
                },
                "start_message": "Привет! Давай начнем создавать курс по геометрии. Что последнее ты прошел в этой теме?"
            },
            {
                "recommendation_name": "Школьное обществознание",
                "base_json": {
                    "0_topic": "Обществознание",
                    "1_initial_level": "",
                    "2_target_level": "",
                    "3_name": "Курс по обществознанию",
                    "4_structure": [],
                    "5_categories": ["Обществознание", "Школа"],
                },
                "start_message": "Привет! Давай начнем создавать курс по обществознанию. Что последнее ты прошел в этой теме?"
            }
        ]
    elif language == "en":
        base_recommendation = [
            {
                "recommendation_name": "Algebra for 7th Grade",
                "base_json": {
                    "0_topic": "Algebra",
                    "1_initial_level": "",
                    "2_target_level": "",
                    "3_name": "Algebra Course",
                    "4_structure": [],
                    "5_categories": ["Mathematics", "Algebra", "School"],
                },
                "start_message": "Hello! Let's start creating an algebra course. What is the last topic you studied in this subject?",
                "image_text": "",
                                               
            },
            {
                "recommendation_name": "High School Physics",
                "base_json": {
                    "0_topic": "Physics",
                    "1_initial_level": "",
                    "2_target_level": "",
                    "3_name": "Physics Course",
                    "4_structure": [],
                    "5_categories": ["Physics", "School"],
                },
                "start_message": "Hello! Let's start creating a physics course. What is the last topic you studied in this subject?",
                "image_text": "",
                                        
            },
            {
                "recommendation_name": "Beginner Chemistry",
                "base_json": {
                    "0_topic": "Chemistry",
                    "1_initial_level": "",
                    "2_target_level": "",
                    "3_name": "Chemistry Course",
                    "4_structure": [],
                    "5_categories": ["Chemistry", "School"],
                },
                "start_message": "Hello! Let's start creating a chemistry course. What is the last topic you studied in this subject?",
                "image_text": "",
                                                   
            },
            {
                "recommendation_name": "Middle School Biology",
                "base_json": {
                    "0_topic": "Biology",
                    "1_initial_level": "",
                    "2_target_level": "",
                    "3_name": "Biology Course",
                    "4_structure": [],
                    "5_categories": ["Biology", "School"],
                },
                "start_message": "Hello! Let's start creating a biology course. What is the last topic you studied in this subject?",
                "image_text": "",
                                                     
            },
            {
                "recommendation_name": "Geometry. High School",
                "base_json": {
                    "0_topic": "Geometry",
                    "1_initial_level": "",
                    "2_target_level": "",
                    "3_name": "Geometry Course",
                    "4_structure": [],
                    "5_categories": ["Mathematics", "Geometry", "School"],
                },
                "start_message": "Hello! Let's start creating a geometry course. What is the last topic you studied in this subject?",
                "image_text": "",
                                                 
            },
            {
                "recommendation_name": "School Social Studies",
                "base_json": {
                    "0_topic": "Social Studies",
                    "1_initial_level": "",
                    "2_target_level": "",
                    "3_name": "Social Studies Course",
                    "4_structure": [],
                    "5_categories": ["Social Studies", "School"],
                },
                "start_message": "Hello! Let's start creating a social studies course. What is the last topic you studied in this subject?",
                "image_text": "",
                                                     
            }
        ]

    return base_recommendation 