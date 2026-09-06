import json
import os

INPUT_FILE = "dataset/aquaculture_dataset.jsonl"
OUTPUT_FILE = "dataset/meenamitra_dataset.jsonl"


def load_dataset(path):
    records = []

    with open(path, "r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                record = json.loads(line)

                if not all(key in record for key in ["instruction", "input", "output"]):
                    print(f"Skipping line {line_number}: missing required fields")
                    continue

                records.append(record)

            except json.JSONDecodeError:
                print(f"Skipping invalid JSON on line {line_number}")

    return records


def create_variants(record):
    instruction = record["instruction"]
    question = record["input"]
    answer = record["output"]

    variants = []

    # Original record
    variants.append({
        "instruction": instruction,
        "input": question,
        "output": answer
    })

    # Variant 1
    if any(char in question for char in "అఆఇఈఉఊఎఏఐఒఓకఖగఘ"):
        variant_1 = f"నేను చేపల పెంపకం చేస్తున్నాను. {question}"
        variant_2 = f"చేపల రైతుగా నాకు తెలుసుకోవాలి: {question}"
    else:
        variant_1 = f"I am a fish farmer. {question}"
        variant_2 = f"As a fish farmer, I want to know: {question}"

    variants.append({
        "instruction": instruction,
        "input": variant_1,
        "output": answer
    })

    # Variant 2
    variants.append({
        "instruction": instruction,
        "input": variant_2,
        "output": answer
    })

    return variants


def main():
    print("Loading original dataset...")

    original_records = load_dataset(INPUT_FILE)

    print(f"Original records: {len(original_records)}")

    expanded_records = []

    for record in original_records:
        variants = create_variants(record)
        expanded_records.extend(variants)

    # Remove exact duplicate questions
    unique_records = []
    seen_questions = set()

    for record in expanded_records:
        question = record["input"].strip()

        if question not in seen_questions:
            seen_questions.add(question)
            unique_records.append(record)

    # Create output directory if needed
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    # Save JSONL
    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        for record in unique_records:
            file.write(
                json.dumps(
                    record,
                    ensure_ascii=False
                ) + "\n"
            )

    print()
    print("Dataset augmentation completed!")
    print(f"Original records : {len(original_records)}")
    print(f"Final records    : {len(unique_records)}")
    print(f"Unique questions : {len(set(r['input'] for r in unique_records))}")
    print()
    print(f"Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()