import os
import torch
import gradio as gr

from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel


BASE_MODEL = "unsloth/qwen2.5-1.5b-instruct-unsloth-bnb-4bit"
ADAPTER_MODEL = "gayathri-sanjana/MeenaMitra-Qwen2.5-1.5B"


print("Loading MeenaMitra model...")

tokenizer = AutoTokenizer.from_pretrained(
    BASE_MODEL,
    trust_remote_code=True
)

base_model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    torch_dtype=torch.float16,
    device_map="auto",
    trust_remote_code=True
)

model = PeftModel.from_pretrained(
    base_model,
    ADAPTER_MODEL
)

model.eval()

print("MeenaMitra model loaded successfully.")


def answer_question(question):
    if not question or not question.strip():
        return "Please enter a fish-farming question."

    messages = [
        {
            "role": "system",
            "content": (
                "You are MeenaMitra, an AI aquaculture advisor. "
                "Give practical, simple and clear advice about fish farming, "
                "including water quality, feeding, fish health, pond management "
                "and fish behavior. Do not invent facts. "
                "If a situation may require an aquaculture expert or veterinarian, "
                "clearly recommend professional help."
            )
        },
        {
            "role": "user",
            "content": question.strip()
        }
    ]

    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )

    inputs = tokenizer(
        prompt,
        return_tensors="pt"
    ).to(model.device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=300,
            temperature=0.7,
            top_p=0.9,
            do_sample=True,
            repetition_penalty=1.1
        )

    generated_tokens = outputs[0][inputs["input_ids"].shape[1]:]

    answer = tokenizer.decode(
        generated_tokens,
        skip_special_tokens=True
    )

    return answer.strip()


demo = gr.Interface(
    fn=answer_question,
    inputs=gr.Textbox(
        label="Ask MeenaMitra",
        placeholder="Ask a fish-farming question..."
    ),
    outputs=gr.Textbox(
        label="MeenaMitra Answer"
    ),
    title="🐟 MeenaMitra",
    description=(
        "AI Aquaculture Advisor powered by a fine-tuned "
        "Qwen2.5-1.5B model."
    )
)


if __name__ == "__main__":
    demo.launch()