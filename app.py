import os
import subprocess
import traceback
from urllib.parse import urlparse
import glob

import boto3
import requests
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MinIO config
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
        try:
            data = await request.json()
        except Exception:
            print("⚠️ Failed to parse JSON body.")
            return {"error": "❌ Invalid or incomplete JSON body."}

        url = data.get("url")
        if not url:
            return {"error": "❌ No URL provided."}
        print(f"📥 Downloading from: {url}")

        filename = os.path.basename(urlparse(url).path)
        name, ext = os.path.splitext(filename)
        if not ext:
            filename += ".mov"
            print(f"📛 Appended .mov: {filename}")

        r = requests.get(url)
        print(f"📦 Download status code: {r.status_code}")
        if r.status_code != 200:
            return {"error": f"❌ Failed to download. Status {r.status_code}"}
        with open(filename, "wb") as f:
            f.write(r.content)

        size = os.path.getsize(filename)
        print(f"✅ File saved: {filename} ({size} bytes)")

        # 🔸 Reject too small files (very likely not a valid video)
        if size < 50000:
            return {"error": f"❌ File too small to be a valid video. Size: {size} bytes."}

        if "_RAW_V1" in filename:
            newname = filename.replace("_RAW_V1", "")
            os.rename(filename, newname)
            filename = newname
            print(f"✏️ Renamed to: {filename}")

        basename = os.path.splitext(filename)[0]
        folder = f"{basename}-massUpload"
        os.makedirs(folder, exist_ok=True)
        output_file = f"{folder}/{basename}.mp4"

        # ✅ ffmpeg command with -pix_fmt to ensure color compatibility
        command = [
            "ffmpeg",
            "-y",
            "-i", filename,
            "-vf", "fps=24,scale=1080:1920",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "23",
            "-pix_fmt", "yuv420p",  # ✅ added to fix output compatibility
            "-c:a", "aac",
            "-strict", "experimental",
            output_file
        ]

        print("🎞 ffmpeg command:")
        print(" ".join(command))

        result = subprocess.run(command, capture_output=True, text=True)
        print("📄 ffmpeg stdout:\n", result.stdout)
        print("⚠️ ffmpeg stderr:\n", result.stderr)

        if result.returncode != 0:
            return {
                "error": "❌ ffmpeg failed.",
                "details": result.stderr
            }

        if not os.path.exists(output_file) or os.path.getsize(output_file) < 50000:
            return {"error": "❌ Output not found or too small after ffmpeg."}
        print(f"✅ Output created: {output_file}")

        # Clean up filename from " RAW"
        for f in glob.glob(f"{folder}/*.mp4"):
            if " RAW" in f:
                new_f = f.replace(" RAW", "")
                os.rename(f, new_f)
                print(f"🧽 Renamed output to: {new_f}")
                output_file = new_f

        # Upload to MinIO
        s3.upload_file(output_file, BUCKET, f"{FOLDER}/{os.path.basename(output_file)}")
        print(f"☁️ Uploaded to MinIO: {FOLDER}/{os.path.basename(output_file)}")

        return {
            "status": "done",
            "converted_file": os.path.basename(output_file),
            "uploaded_to": f"{FOLDER}/{os.path.basename(output_file)}"
        }

    except Exception as e:
        print("❌ Exception:")
        traceback.print_exc()
        return {"error": str(e)}
