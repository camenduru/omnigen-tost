import os, json, requests, random, time, runpod
from urllib.parse import urlsplit

import torch
from PIL import Image
import numpy as np

from nodes import load_custom_node
from nodes import NODE_CLASS_MAPPINGS

load_custom_node("/content/ComfyUI/custom_nodes/ComfyUI-OmniGen")

LoadImage = NODE_CLASS_MAPPINGS["LoadImage"]()
ailab_OmniGen = NODE_CLASS_MAPPINGS["ailab_OmniGen"]()

def download_file(url, save_dir, file_name):
    os.makedirs(save_dir, exist_ok=True)
    file_suffix = os.path.splitext(urlsplit(url).path)[1]
    file_name_with_suffix = file_name + file_suffix
    file_path = os.path.join(save_dir, file_name_with_suffix)
    response = requests.get(url)
    response.raise_for_status()
    with open(file_path, 'wb') as file:
        file.write(response.content)
    return file_path

@torch.inference_mode()
def generate(input):
    values = input["input"]

    image_1 = values.get('image_1')
    if image_1:
        image_1 = download_file(url=image_1, save_dir='/content/ComfyUI/input', file_name='image_1')
        image_1, _ = LoadImage.load_image(image_1)
    else:
        image_1 = None
    image_2 = values.get('image_2')
    if image_2:
        image_2 = download_file(url=image_2, save_dir='/content/ComfyUI/input', file_name='image_2')
        image_2, _ = LoadImage.load_image(image_2)
    else:
        image_2 = None
    image_3 = values.get('image_3')
    if image_3:
        image_3 = download_file(url=image_3, save_dir='/content/ComfyUI/input', file_name='image_3')
        image_3, _ = LoadImage.load_image(image_3)
    else:
        image_3 = None
    prompt = values.get('prompt')
    num_inference_steps = values.get('num_inference_steps')
    guidance_scale = values.get('guidance_scale')
    img_guidance_scale = values.get('img_guidance_scale')
    max_input_image_size = values.get('max_input_image_size')
    separate_cfg_infer = values.get('separate_cfg_infer')
    offload_model = values.get('offload_model')
    use_input_image_size_as_output = values.get('use_input_image_size_as_output')
    width = values.get('width')
    height = values.get('height')
    seed = values.get('seed')

    if seed == 0:
        random.seed(int(time.time()))
        seed = random.randint(0, 18446744073709551615)

    image = ailab_OmniGen.generation(prompt, num_inference_steps, guidance_scale, img_guidance_scale, max_input_image_size, separate_cfg_infer, offload_model, use_input_image_size_as_output, width, height, seed, image_1=image_1, image_2=image_2, image_3=image_3)[0]
    Image.fromarray(np.array(image*255, dtype=np.uint8)[0]).save(f"/content/ComfyUI/output/omnigen-{seed}-tost.png")

    result = f"/content/ComfyUI/output/omnigen-{seed}-tost.png"
    try:
        notify_uri = values['notify_uri']
        del values['notify_uri']
        notify_token = values['notify_token']
        del values['notify_token']
        discord_id = values['discord_id']
        del values['discord_id']
        if(discord_id == "discord_id"):
            discord_id = os.getenv('com_camenduru_discord_id')
        discord_channel = values['discord_channel']
        del values['discord_channel']
        if(discord_channel == "discord_channel"):
            discord_channel = os.getenv('com_camenduru_discord_channel')
        discord_token = values['discord_token']
        del values['discord_token']
        if(discord_token == "discord_token"):
            discord_token = os.getenv('com_camenduru_discord_token')
        job_id = values['job_id']
        del values['job_id']
        default_filename = os.path.basename(result)
        with open(result, "rb") as file:
            files = {default_filename: file.read()}
        payload = {"content": f"{json.dumps(values)} <@{discord_id}>"}
        response = requests.post(
            f"https://discord.com/api/v9/channels/{discord_channel}/messages",
            data=payload,
            headers={"Authorization": f"Bot {discord_token}"},
            files=files
        )
        response.raise_for_status()
        result_url = response.json()['attachments'][0]['url']
        notify_payload = {"jobId": job_id, "result": result_url, "status": "DONE"}
        web_notify_uri = os.getenv('com_camenduru_web_notify_uri')
        web_notify_token = os.getenv('com_camenduru_web_notify_token')
        if(notify_uri == "notify_uri"):
            requests.post(web_notify_uri, data=json.dumps(notify_payload), headers={'Content-Type': 'application/json', "Authorization": web_notify_token})
        else:
            requests.post(web_notify_uri, data=json.dumps(notify_payload), headers={'Content-Type': 'application/json', "Authorization": web_notify_token})
            requests.post(notify_uri, data=json.dumps(notify_payload), headers={'Content-Type': 'application/json', "Authorization": notify_token})
        return {"jobId": job_id, "result": result_url, "status": "DONE"}
    except Exception as e:
        error_payload = {"jobId": job_id, "status": "FAILED"}
        try:
            if(notify_uri == "notify_uri"):
                requests.post(web_notify_uri, data=json.dumps(error_payload), headers={'Content-Type': 'application/json', "Authorization": web_notify_token})
            else:
                requests.post(web_notify_uri, data=json.dumps(error_payload), headers={'Content-Type': 'application/json', "Authorization": web_notify_token})
                requests.post(notify_uri, data=json.dumps(error_payload), headers={'Content-Type': 'application/json', "Authorization": notify_token})
        except:
            pass
        return {"jobId": job_id, "result": f"FAILED: {str(e)}", "status": "FAILED"}
    finally:
        if os.path.exists(result):
            os.remove(result)

runpod.serverless.start({"handler": generate})
