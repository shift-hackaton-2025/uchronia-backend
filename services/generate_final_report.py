import litellm

from utils.parse_llm_output import parse_json_markdown, extract_tag_content

from dotenv import load_dotenv

load_dotenv()

litellm.success_callback = ["langfuse"]
litellm.failure_callback = ["langfuse"]


async def generate_final_report(events, model="gpt-4o", temperature=0.9):
    system_message = {
        "role": "system",
        "content": """
        We are working on uchronia, a game that displays a chronological timeline, with events and we allow our users to change the course of history.

        For that, at each turn, the user click on a event and choose one of the two options.

        I will give you a list of events each one  will look like this :
        - an id (str, should increment from the highest id of the events)
        - a title (10 words top)
        - a date (str, YYYY-MM-DD)
        - a description text (4/5 lines of text top)
        - 2 impactful / full uchronic options. Each option should have up to 5 words as title and for each we need a consequence (2-3 paragraphs of 2-3 lines)

        and a chaos_level string. 

        <json>
        The output is constituted of : 
        a json with the following fields :
        - description : You congratulate the user for the decision taken and you give him a summary of the consequences of the decision taken by the user (2-3 lines)
        </json>
        Notes : 
        - The language of the generated json fields should be in french. 
    """,
    }
    user_message = {
        "role": "user",
        "content": f"""
        Events : {events}
        """,
    }
    summary = await litellm.acompletion(
        model=model, temperature=temperature, messages=[system_message, user_message]
    )
    summary_str = summary.choices[0].message.content
    events = parse_json_markdown(summary_str)
    
    return events