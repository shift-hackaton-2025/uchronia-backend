import yaml
import os

from generate_image import generate_image  # Assuming this function is defined in a separate module

# Assuming generate_image is defined elsewhere and properly imported
# from image_generator import generate_image

def load_cycles_from_yaml(file_path):
    with open(file_path, 'r') as f:
        data = yaml.safe_load(f)
    return data['cycles']

def build_prompt(context, emotions, keywords):
    prompt = (
        f"Illustrate a scene based on the following description:\n\n"
        f"{context}\n\n"
        f"Emotions to convey: {', '.join(emotions)}.\n"
        f"Key themes and elements to include: {', '.join(keywords)}.\n\n"
        f"The style should be atmospheric and immersive, capturing the tone of the era."
    )
    return prompt


def create_next_numbered_subdirectory(output_dir):
    if not os.path.isdir(output_dir):
        raise NotADirectoryError(f"{output_dir} is not a valid directory")

    numbered_subdirs = [
        int(name) for name in os.listdir(output_dir)
        if os.path.isdir(os.path.join(output_dir, name)) and name.isdigit()
    ]

    next_number = max(numbered_subdirs) + 1 if numbered_subdirs else 0
    new_dir_path = os.path.join(output_dir, str(next_number))

    os.makedirs(new_dir_path, exist_ok=False)
    return new_dir_path

    
    
def save_dict_to_yaml(data: dict, file_path: str):
    with open(file_path, 'w') as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def generate_images_from_cycles(cycle):
    output_dir = "data/rag"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    for i, cycle in enumerate(cycles):
        year = cycle['year']
        context = cycle['context']
        emotions = cycle['emotions']
        keywords = cycle['keywords']

        prompt = build_prompt(context, emotions, keywords)
        
        new_output_dir = create_next_numbered_subdirectory(output_dir)
        print(f"Output directory created: {new_output_dir}")
        text_path = os.path.join(new_output_dir, "text.yaml")
        save_dict_to_yaml(cycle, text_path)

        output_image_path = os.path.join(new_output_dir, "text.png")
        generate_image(prompt, output_image_path)
        
        print(f"Saved image and text into directory {new_output_dir}.")


if __name__ == "__main__":
    yaml_path = "services/create_rag/stories/story_3.yaml"  # Replace with the actual path to your YAML file
    cycles = load_cycles_from_yaml(yaml_path)
    generate_images_from_cycles(cycles)
