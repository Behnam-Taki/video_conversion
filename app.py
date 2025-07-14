# app.py

import os
import subprocess
from urllib.parse import urlparse
import traceback

import boto3
import requests
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# ✅ CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Make.com یا دامنه‌ی خاص بهتره
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ MinIO setup
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
    try:
        data = await request.json()
        url = data.get("url")
        if not url:
            return {"error": "❌ No URL provided in the request."}
        print(f"📥 Request received. Downloading from: {url}")

        filename = os.path.basename(urlparse(url).path)
        print(f"📄 Extracted filename: {filename}")

        # ✅ Download file
        r = requests.get(url)
        print(f"📦 Download status code: {r.status_code}")
        if r.status_code != 200:
            return {"error": f"❌ Failed to download file. Status: {r.status_code}"}
        with open(filename, "wb") as f:
            f.write(r.content)
        print(f"✅ File saved locally: {filename}")

        # ✅ Rename if needed
        if "_RAW_V1" in filename:
            newname = filename.replace("_RAW_V1", "")
            os.rename(filename, newname)
            filename = newname
            print(f"✏️ Renamed to: {filename}")

        # ✅ Prepare output
        folder = f"{filename[:-4]}-massUpload"
        os.makedirs(folder, exist_ok=True)
        output_file = f"{folder}/{filename[:-4]}.mp4"

        # ✅ ffmpeg conversion
        command = f"""ffmpeg -i "{filename}" -qscale 0 -pix_fmt yuv420p -filter:v fps=fps=24 -vf scale=1080:1920 -c:a copy "{output_file}" """
        print(f"🎞 Running ffmpeg: {command}")
        result = subprocess.call(command, shell=True)
        print(f"🎬 ffmpeg exit code: {result}")

        if not os.path.exists(output_file):
            return {"error": "❌ ffmpeg failed. Output file not found."}
        print(f"✅ Converted file exists: {output_file}")

        # ✅ Upload to MinIO
        s3.upload_file(output_file, BUCKET, f"{FOLDER}/{os.path.basename(output_file)}")
        print(f"☁️ Uploaded to MinIO: {FOLDER}/{os.path.basename(output_file)}")

        return {
            "status": "done",
            "converted_file": os.path.basename(output_file),
            "uploaded_to": f"{FOLDER}/{os.path.basename(output_file)}"
        }

    except Exception as e:
        print("❌ Exception occurred:")
        traceback.print_exc()
        return {"error": str(e)}
