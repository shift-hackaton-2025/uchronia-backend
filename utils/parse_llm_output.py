import json
import re
from typing import Any


def _replace_new_line(match: re.Match[str]) -> str:
    """
    Replace newlines and special characters in a regex match with their escaped counterparts.

    Args:
        match (re.Match[str]): Regex match object containing the text to process

    Returns:
        str: Processed string with escaped special characters
    """
    value = match.group(2)
    value = re.sub(r"\n", r"\\n", value)
    value = re.sub(r"\r", r"\\r", value)
    value = re.sub(r"\t", r"\\t", value)
    value = re.sub(r'(?<!\\)"', r"\"", value)
    return match.group(1) + value + match.group(3)


def _custom_parser(multiline_string: str) -> str:
    """
    Process multiline strings from LLM responses that may contain unescaped special characters.

    The LLM response for `action_input` may be a multiline string containing unescaped
    newlines, tabs or quotes. This function replaces those characters with their escaped
    counterparts. (newlines in JSON must be double-escaped: `\\n`)

    Args:
        multiline_string (str): The input string to process

    Returns:
        str: Processed string with properly escaped special characters
    """
    if isinstance(multiline_string, (bytes, bytearray)):
        multiline_string = multiline_string.decode()
    multiline_string = re.sub(
        r'("action_input"\:\s*")(.*?)(")',
        _replace_new_line,
        multiline_string,
        flags=re.DOTALL,
    )
    return multiline_string


def _parse_json(json_str: str) -> dict[str, Any]:
    """
    Parse a JSON string into a Python dictionary, handling special characters.

    Args:
        json_str (str): JSON string to parse

    Returns:
        dict[str, Any]: Parsed JSON as a Python dictionary
    """
    # Strip whitespace and newlines from the start and end
    json_str = json_str.strip().strip("`")
    # handle newlines and other special characters inside the returned value
    json_str = _custom_parser(json_str)
    # Parse the JSON string into a Python dictionary
    return json.loads(json_str)


def parse_json_markdown(json_string: str) -> dict[str, Any]:
    """
    Parse JSON from a markdown string that may contain code blocks.

    This function handles JSON strings that might be wrapped in markdown code blocks
    (with or without language specifiers) and properly escapes special characters.

    Args:
        json_string (str): The input string that may contain JSON in markdown format

    Returns:
        dict[str, Any]: Parsed JSON as a Python dictionary

    Raises:
        json.JSONDecodeError: If the string cannot be parsed as valid JSON
    """
    try:
        return _parse_json(json_string)
    except json.JSONDecodeError:
        # Try to find JSON string within triple backticks
        if "python" in json_string:
            match = re.search(r"```(python)?(.*)", json_string, re.DOTALL)
        else:
            match = re.search(r"```(json)?(.*)", json_string, re.DOTALL)
        # If no match found, assume the entire string is a JSON string
        if match is None:
            json_str = json_string
        else:
            # If match found, use the content within the backticks
            json_str = match.group(2)
        return _parse_json(json_str)


def extract_tag_content(text: str, tag_name: str) -> str | None:
    """
    Extract content from within specified XML-like tags in a text.

    Args:
        text (str): The input text containing XML-like tags
        tag_name (str): Name of the tag to extract content from (without < >)

    Returns:
        str | None: Content between the specified tags, or None if tag not found

    Example:
        >>> text = "<thinking>Some thoughts</thinking>"
        >>> extract_tag_content(text, "thinking")
        'Some thoughts'
    """
    pattern = f"<{tag_name}>(.*?)</{tag_name}>"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None
