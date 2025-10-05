import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import numpy as np
import requests
from collections import Counter

from math import ceil

import httpx
import asyncio

from models import *


import uvicorn


crowd_analysys_service = FastAPI(
    prefix='/api/v1'
)

crowd_analysys_service.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def frontal_gated_images(req: ProcRequest):
    frontal, gate = [], []

    for elem in req.images:
        if elem['cam_info'] == 'frontal':
            frontal.append(elem)
        elif elem['cam_info'] == 'gate':
            gate.append(elem)

    return frontal, gate


async def get_processed_images(images: list[Image]):
    async def fetch_url(client: httpx.AsyncClient, url, image):
        print(image.keys())
        response = await client.post(url, json=image)
        return response.json()
    async with httpx.AsyncClient() as client:
        tasks = [fetch_url(client, 'http://llm-service:1337/api/v1/proc_image', image) for image in images]
        results = await asyncio.gather(*tasks)

    return results

@crowd_analysys_service.post('/api/v1/crowd_analysis')
async def crowd_analysys(req: ProcRequest):
    frontal, gate = frontal_gated_images(req)

    if not len(frontal):
        raise HTTPException(400, 'There are no frontal images')

    frontal_processed = await get_processed_images(frontal)
    gate_processed = await get_processed_images(gate) if len(gate) else []
    print(frontal_processed)

    seats = np.mean([json.loads(x)['proc_data']['free_seats'] for x in frontal_processed]).astype(float)

    people = np.mean([json.loads(x)['proc_data']['people_num'] for x in frontal_processed]).astype(float) + 1.5 * np.mean([json.loads(x)['proc_data']['people_num'] for x in gate_processed]).astype(float) if gate_processed else np.mean([json.loads(x)['proc_data']['people_num'] for x in frontal_processed]).astype(float)
    
    if len(gate):
        frontal_free = [json.loads(x)['proc_data']['free_entrance'] for x in frontal_processed]
        gate_free = [json.loads(x)['proc_data']['free_entrance'] for x in frontal_processed]

        summurized_stat = list(filter(lambda x: x != 0, frontal_free + gate_free))
    else:
        frontal_free = [json.loads(x)['proc_data']['free_entrance'] for x in frontal_processed]

        summurized_stat = list(filter(lambda x: x != 0, frontal_free))

    if summurized_stat:
        unsqueezed_summurized_stat = []
        for elem in summurized_stat:
            unsqueezed_summurized_stat += elem
        print(unsqueezed_summurized_stat)
        free_entr = Counter(unsqueezed_summurized_stat).most_common(1)[0][0]
    else:
        free_entr = 0
    seats = int(ceil(seats))
    people = int(ceil(people))

    return {
        'seats': seats,
        'people': people,
        'free_entrance': free_entr
    }


if __name__ == '__main__':
    uvicorn.run(
        app=crowd_analysys_service,
        host='0.0.0.0',
        port=1338
    )
