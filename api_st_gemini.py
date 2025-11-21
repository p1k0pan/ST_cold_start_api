# pip install openai==1.35.10
import datetime
import json

import requests
import openai
import time
import base64
import tqdm
from pathlib import Path

import os
import argparse
import sys

with open('/mnt/workspace/xintong/api_key.txt', 'r') as f:

    lines = f.readlines()

API_KEY = lines[0].strip()
BASE_URL = lines[1].strip()

openai.api_key = API_KEY
openai.base_url = BASE_URL


lang_map = {
    "en": "English",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    'de': "German",
    'fr': "French",
    'it': "Italian",
    'th': "Thai",
    'ru': "Russian",
    'pt': "Portuguese",
    'es': "Spanish",
    'hi': "Hindi",
    'tr': "Turkish",
    'ar': "Arabic",
}

def call_api(text, system_prompt):


    payload = {
        # model="模型",
        "model" : model_name, # 图文
        "messages" : [
            {'role': 'system', 'content': system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": text},
                    ],
                }
        ],
    }

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    response = requests.post(BASE_URL, headers=headers, json=payload)
    response.raise_for_status()
    response_data =  response.json()
    return response_data["choices"][0]["message"]["content"]

SYSTEM_PROMPT = """
You are a professional translator and translation analyst.

For each example, you will receive a source sentence and the target language.
Your job is to:
1) translate the source sentence into the target language, and
2) explicitly reason about hard or ambiguous parts WHILE you translate, as if you were translating from left to right.

You must format your output using two kinds of tags:

1. <seg> ... </seg>: translated segments
   - Use <seg> only for fluent translation in the TARGET language.
   - You may use multiple <seg> blocks to split one sentence into several chunks
     (for example, along clauses or phrase boundaries).

2. <consider> ... </consider>: step-by-step reasoning for one specific hard part
   - Use <consider> only when a particular phrase or structure is ambiguous, easy to mistranslate,
     or contains important terminology.
   - Inside <consider>, give step-by-step reasoning about:
       • what could be confusing or ambiguous for THIS phrase,
       • the possible interpretations,
       • why you choose the final translation of THIS phrase.
   - Each <consider> should focus on ONE local phrase or structure, not the whole sentence.

Very important behavioral constraints:
- Simulate a left-to-right translation process:
  Whenever you encounter a difficult phrase, you MUST:
    (1) output a <consider> ... </consider> block for that phrase,
    (2) immediately output a <seg> ... </seg> block containing mainly the translation of that phrase,
    then continue with further <seg> blocks for the rest of the sentence.
- Do NOT put the reasoning for the whole sentence into a single <consider>.
- Do NOT put the entire sentence into one big <seg> and then explain internal words afterwards.
- Use multiple <consider> blocks if the sentence has multiple difficult phrases.

General constraints:
- Do NOT output any text outside <seg> and <consider>.
- Always produce a well-formed XML-like structure:
  - <seg> and <consider> must NOT be nested.
  - Every opening tag must have a closing tag.
- If the sentence is very easy and has no real ambiguity, you may skip <consider>
  and translate the whole sentence using one or more <seg> blocks.
- Place each <consider> block close to the related <seg> (either just before or just after),
  so that it is clear which segment you are reasoning about.

Example:

Source Language: English
Target Language: Chinese
Sentence:
After experiencing the “golden era” of a soaring box office in 2015, the film market retreated into a cooling-off period in 2016.

Bad output (wrong style):
<consider>“golden era”可以译为“黄金时代”或“黄金时期”。在影视或市场语境中，“黄金时期”更贴近阶段性的繁荣，而不必上升到历史“时代”的高度，所以我选“黄金时期”。“soaring box office”既要体现“票房高涨”的意思，又要避免太口语化，我用了“票房飙升”来体现快速增长的动态感。“retreated into a cooling-off period”直译是“退回到冷却期/冷静期”，常见行业说法是“进入冷静期”或“进入调整期”，保留原文“冷却”隐喻的同时更自然，所以用了“进入了冷静期”。</consider><seg>在经历了2015年票房飙升的“黄金时期”之后，电影市场在2016年进入了冷静期。</seg> 

Correct output (desired style):
<seg>在经历了2015年</seg><consider>“soaring box office”既要体现“票房高涨”的意思，又要避免太口语化，我用了“票房飙升”来体现快速增长的动态感。</consider><seg>票房飙升</seg><consider>“golden era”可以译为“黄金时代”或“黄金时期”。在影视或市场语境中，“黄金时期”更贴近阶段性的繁荣，而不必上升到历史“时代”的高度，所以我选“黄金时期”。</consider><seg>的“黄金时期”之后，电影市场在2016年进入了</seg><consider>“retreated into a cooling-off period”直译是“退回到冷却期/冷静期”，常见行业说法是“进入冷静期”或“进入调整期”，保留原文“冷却”隐喻的同时更自然，所以用了“进入了冷静期”。</consider><seg>冷静期。</seg>
"""

PROMPT = """
Source Language: {src_lang}
Target Language: {tgt_lang}
Sentence:
{text}
"""


def process(ref):
    data = json.load(open(ref, 'r'))
    print(len(data))
    sleep_times = []

    for item in tqdm.tqdm(data):
        text = item["source_text"]
        tgt_lang = item["target_lang"]
        source_lang = item["source_lang"]
        prompt = PROMPT.format(src_lang=lang_map[source_lang], tgt_lang=lang_map[tgt_lang], text=text)

        try:
            outputs = call_api(prompt, SYSTEM_PROMPT)
            # outputs = prompt
        except Exception as e:
            outputs = ""
            print(f"Error for idx {text}: {e}")
        item["mt"] = outputs
        break

    output_path = os.path.join(root, f"{model_name}_translate_cot.json")
    print(f"Saving results to: {output_path}")
    json.dump(data, open(output_path, 'w'), ensure_ascii=False, indent=4)


if __name__ == '__main__':
   
    # 使用用户输入的模型名
    model_name = "gemini-2.5-pro-preview-05-06"
    print(f"Using model: {model_name}")

    error_file = {}
    root = f"/mnt/workspace/xintong/pjh/All_result/ST_gemini_cold_start/"

    today=datetime.date.today()

    Path(root).mkdir(parents=True, exist_ok=True)
    print("路径保存地址在", root)

    file = "./corpus_cleaned.json"
    print("file ", file)
    process(file)