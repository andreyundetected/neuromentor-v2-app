import aiohttp
import os


async def get_empty_course_info():
    return {
        "0_topic": "",
        "1_initial_level": "",
        "2_target_level": "",
        "3_name": "",
        "4_structure": [
            {
                "0_topic": "",
                "1_description": "",
                "2_instructions_for_generating_lessons": "",
                "3_lessons": [
                    {"name": "", "description": ""},
                    {"name": "", "description": ""}
                ]
            }
        ],
        "5_categories": []
    }


NEURO_API_URL = "https://" + os.getenv("NEURO_API-DOMAIN", "") + "/neuro_api"


async def send_request_to_api(payload):
    print("Отправка запроса к API с payload:", payload)
    async with aiohttp.ClientSession() as session:
        async with session.post(NEURO_API_URL, json=payload) as response:
            return await response.json()
