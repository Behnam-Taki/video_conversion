# app.py
from urllib.parse import urlparse

import boto3
import os
import requests
import subprocess
from fastapi import FastAPI, Request

app = FastAPI()

# MinIO setup
s3 = boto3.client(
    's3',
    endpoint_url='https://minio-api.farazpardazan.com',
    aws_access_key_id='hpHq4eAsPfNmqtbLENTj',
    aws_secret_access_key='A02KuirdpnXG0ZLhMpcadeT010XiK7Fp6SZccrGQ'
)

BUCKET = "test"
FOLDER = "maketest"


@app.post("/convert")
async def convert_video(request: Request):
    data = await request.json()
    url = data.get("url")
    filename = os.path.basename(urlparse(url).path)

    # Download video
    r = requests.get(url)
    with open(filename, "wb") as f:
        f.write(r.content)

    # Rename if needed
    if "_RAW_V1" in filename:
        newname = filename.replace("_RAW_V1", "")
        os.rename(filename, newname)
        filename = newname

    folder = f"{filename[:-4]}-massUpload"
    os.makedirs(folder, exist_ok=True)
    output_file = f"{folder}/{filename[:-4]}.mp4"

    # ffmpeg conversion
    command = f"""ffmpeg -i "{filename}" -qscale 0 -pix_fmt yuv420p -filter:v fps=fps=24 -vf scale=1080:1920 -c:a copy "{output_file}" """
    subprocess.call(command, shell=True)

    # Upload to MinIO
    s3.upload_file(output_file, BUCKET, f"{FOLDER}/{os.path.basename(output_file)}")

    return {"status": "done", "file": os.path.basename(output_file)}
