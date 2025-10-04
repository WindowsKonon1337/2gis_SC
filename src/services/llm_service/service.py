from openai import AsyncOpenAI
import json
from fastapi import FastAPI, HTTPException

from models import *
from prompts import *


import uvicorn


llm_service = FastAPI(
    prefix='/api/v1'
)
client = AsyncOpenAI(
    api_key="sk-wAE07IvRJmwoTNlImRlMRvfV8hSQkhlK",
    base_url="https://api.proxyapi.ru/openai/v1",
)


@llm_service.post('/api/v1/proc_image')
async def proc_image(req: ProcRequest):
    try:
        llm_output = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": main_prompt['user']},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{req.image}"
                            }
                        },
                    ],
                }],
        )
        result = llm_output.choices[0].message.content

        result.replace('`', '').replace('json', '').strip()

        response = req.model_dump()
        del response['image']
        response['proc_data'] = json.loads(result)

        return json.dumps(response)
    except Exception as e:
        print(e)
        raise HTTPException(500, 'something not good : (')


if __name__ == '__main__':
    uvicorn.run(
        app=llm_service,
        host='0.0.0.0',
        port=1337
    )
