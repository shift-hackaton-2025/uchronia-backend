import litellm

from utils.parse_llm_output import parse_json_markdown, extract_tag_content

from dotenv import load_dotenv

load_dotenv()

litellm.success_callback = ["langfuse"]
litellm.failure_callback = ["langfuse"]


async def generate_future_events(events, option_chosen, model="gpt-4o", temperature=0.7):
    system_message = {
        "role": "system",
        "content": """
        We are working on uchronia, a game that displays a chronological timeline, with events and we allow our users to change the course of history.

        For that, at each turn, the user click on a event and choose one of the two options.
        Your mission is to :
        - imagine what the future could look like
        - create future events to replace the current ones.

        For each of these future events, we want to have :
        - an id (str, should increment from the highest id of the events)
        - a title (10 words top)
        - a date (str, YYYY-MM-DD)
        - a description text (4/5 lines of text top)
        - 2 impactful / full uchronic options. Each option should have up to 5 words as title (start with verb) and for each we need a consequence (2-3 paragraphs of 2-3 lines)

        The output is constituted of : 
        - a think tag with your projection of the future:
        <think>
        - Imagine what the future could look like (The story must follow four phases — rise, peak, fall, and rebirth — but be told in a vivid and immersive tone suitable for a narrative game.)
        - You must create an alternative narrative arc, unrelated to the main story, that runs in parallel
        - extract 2 events from the main arc and 1 from the side arc (one kind of immediately, one some time after (year-decades) and one way later (decades - century)
        </think>
        - a events tag, where you output a json that contains the future cards :
        <events>
        Notes : 
        - We want diversified options : funny, artistic, violent, serious.
        - We want all options to have impactful outcomes in the timeline
        - The language of the generated events should be in French
    """,
    }
    user_message = {
        "role": "user",
        "content": f"""
        Option chosen : {option_chosen} 
        Events : {events}
        """,
    }
    completion = await litellm.acompletion(
        model=model,
        # model="groq/llama-3.3-70b-versatile",
        temperature=temperature,
        messages=[system_message, user_message],
        metadata={
            "tags": ["generate_future_events"]
        }
    )
    think = extract_tag_content(completion.choices[0].message.content, "think")
    events_str = extract_tag_content(completion.choices[0].message.content, "events")
    events = parse_json_markdown(events_str)
    return think, events


async def generate_narrative_arc(events, option_chosen):
    user_message = {
        "role": "user",
        "content": f"""
        We are working on uchronia, a game that displays a chronological timeline, with events and we allow our users to change the course of history.
        Your mission is to imagine what the future could look like (The story must follow four phases — rise, peak, fall, and rebirth — but be told in a vivid and immersive tone suitable for a narrative game.)
        - extract 3 events (one kind of immediately, one some time after (year-decades) and one way later (decades - century).

        Option chosen: {option_chosen}
        Events:
        {events}

        Notes: 
        - Be funny sometimes
        - choose impactful events
        """,
    }
    completion = await litellm.acompletion(
        # model="groq/llama-3.3-70b-versatile",
        model="groq/deepseek-r1-distill-llama-70b",
        temperature=0.7,
        messages=[user_message],
        metadata={"tags": ["generate_narrative_arc"]},
    )

    return completion.choices[0].message.content


async def format_narrative_arc(narrative_arc):
    system_message = {
        "role": "system",
        "content": """
        Your role is to transform the events into a JSON format with the following structure:
        {
            "events": [                           // Type: Array of event objects.
                {
                "title": "string",                // Type: String. Title of the event. Should be explicit and start with a noun.
                "date": "YYYY-MM-DD",             // Type: String. Date of the event in ISO format.
                "description": "string",          // Type: String. Detailed description of the event (4-5 lines)
                "options": [                      // Type: Array of option objects.
                    {
                    "title": "string",            // Type: String. Title of the option. Should start with a verb.
                    "consequence": "string"       // Type: String. Outcome or consequence if this option is selected. (2-3 paragraphs of 2-3 lines)
                    }
                ]
                }
            ]
        }
        Don't output any text other than the JSON. Output should be in French
        There should be exactly 3 events and 2 options for each event
        """,
    }
    user_message = {
        "role": "user",
        "content": f"""
        Narrative Arc: {narrative_arc}
        """,
    }
    completion = await litellm.acompletion(
        model="groq/llama-3.3-70b-versatile",
        temperature=0.7,
        messages=[system_message, user_message],
        metadata={
            "tags": ["format_narrative_arc"]
        }
    )
    return completion.choices[0].message.content


async def generate_narrative_arc_events(events, option_chosen):
    narrative_arc = await generate_narrative_arc(events, option_chosen)
    formatted_narrative_arc = await format_narrative_arc(narrative_arc)
    narrative_arc_events = parse_json_markdown(formatted_narrative_arc)["events"]

    # generate ids
    max_id = max([int(event.id) for event in events])
    for event in narrative_arc_events:
        event["id"] = str(max_id + 1)
        max_id += 1
    return narrative_arc_events


if __name__ == "__main__":
    import asyncio

    option_chosen = {
        "title": "Unexpected Lunar Encounter",
        "consequence": "During routine exploration, the crew detects mysterious signals and observes unexplained phenomena on the dark side of the moon. These anomalies—strange lights and unusual formations—hint at secrets long hidden beneath the lunar surface. The encounter turns the mission into a quest for answers.\n\n The discovery launches an international scientific expedition dedicated to uncovering the moon's mysteries. This newfound focus on the unknown transforms space exploration from a race for technical achievement into a profound investigation of cosmic enigmas, stirring both scientific inquiry and popular imagination."
    }

    events = [
        {
            "id": "1",
            "title": "The New World Unveiled",
            "date": "1492-08-25",
            "description": "The discovery of America is a watershed moment that forever alters global history. Explorers encounter vast, diverse lands and indigenous cultures, opening up countless paths for change. In this alternate timeline, every twist not only redefines who holds power but also forges new cultural identities that ripple throughout the world.",
            "options": [
                {
                    "title": "Peaceful Native Alliance",
                    "consequence": "Early explorers engage in genuine dialogue with indigenous peoples, fostering mutual respect and understanding. Over time, intermarriage, trade, and cultural exchange create a unique society—a rich blend of European and native traditions.\n\nThis new identity reshapes the continent, fueling artistic, culinary, and linguistic innovations. The harmonious union becomes a beacon of multicultural coexistence, influencing social reforms and international diplomacy for generations.",
                },
                {
                    "title": "Native Empire Rises",
                    "consequence": "Inspired by ancient traditions and modern challenges, a coalition of indigenous tribes unites to forge a powerful empire. This indigenous state, blending traditional governance with adapted European technologies, rises to dominance in the region.\n\nThe Native Empire reshapes trade, warfare, and cultural norms, forcing European powers to negotiate on equal footing. Its influence sparks a global reassessment of colonization, ultimately redefining power balances and inspiring movements for indigenous rights worldwide.",
                },
            ],
        },
        {
            "id": "2",
            "title": "Empire Reborn: Revolutionary Shadows",
            "date": "1789-07-14",
            "description": "The historic revolution takes an unexpected turn, preserving the royal family and birthing a new empire. Ambitious leaders reminiscent of Napoleon rise to power, reshaping France's destiny. A reimagined national identity emerges with a bold new anthem and emblem. History is rewritten in a clash of tradition and imperial ambition.",
            "options": [
                {
                    "title": "Imperial Resurgence",
                    "consequence": "The royal family remains intact, steering France toward an imperial destiny. A strategic mastermind, echoing Napoleon's brilliance, unites disparate factions under a singular, imperial banner.\n\nThe nation adopts a powerful new national anthem and emblem that celebrate martial pride and grandeur. This bold transformation forges a legacy of ambition and order that redefines French society.",
                },
                {
                    "title": "Napoleonic Reclamation",
                    "consequence": "In a dramatic shift, a charismatic general emerges to reclaim and redefine France's future. His military prowess and visionary leadership catalyze the transition from revolutionary chaos to imperial stability.\n\nA striking new anthem and symbolic crest are introduced, reflecting",
                },
            ],
        },
    ]

    think, events = asyncio.run(generate_future_events(events, option_chosen))
    print(think)
    print(events)

    narrative_arc = asyncio.run(generate_narrative_arc(events, option_chosen))
    print(narrative_arc)

    formatted_narrative_arc = asyncio.run(format_narrative_arc(narrative_arc))
    print(formatted_narrative_arc)

    narrative_arc_events = parse_json_markdown(formatted_narrative_arc)

    from time import time
    start_time = time()
    output = asyncio.run(generate_narrative_arc_events(events, option_chosen))
    end_time = time()
    print(f"Time taken: {end_time - start_time} seconds")
