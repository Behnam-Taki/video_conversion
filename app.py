# app.py

import os
import subprocess
from urllib.parse import urlparse

import boto3
import requests
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# ✅ CORS Middleware (برای پذیرش درخواست از Make.com یا هر دامنه دیگر)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # بهتره دامنه خاص رو بزاری برای امنیت بالاتر مثلاً ["https://make.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ MinIO setup (S3 compatible)
s3 = boto3.client(
    's3',
    endpoint_url='https://minio-api.farazpardazan.com',
    aws_access_key_id='hpHq4eAsPfNmqtbLENTj',
    aws_secret_access_key='A02KuirdpnXG0ZLhMpcadeT010XiK7Fp6SZccrGQ'
)

# ✅ Bucket/Folder setup
BUCKET = "test"
FOLDER = "maketest"

@app.post("/convert")
async def convert_video(request: Request):
    data = await request.json()
    url = data.get("url")

    # استخراج نام فایل از URL
    filename = os.path.basename(urlparse(url).path)

    # ✅ دانلود فایل و ذخیره محلی
    r = requests.get(url)
    with open(filename, "wb") as f:
        f.write(r.content)

    # ✅ تغییر نام فایل در صورت نیاز
    if "_RAW_V1" in filename:
        newname = filename.replace("_RAW_V1", "")
        os.rename(filename, newname)
        filename = newname

    # ✅ مسیر خروجی و ساخت پوشه برای فایل کانورت‌شده
    folder = f"{filename[:-4]}-massUpload"
    os.makedirs(folder, exist_ok=True)
    output_file = f"{folder}/{filename[:-4]}.mp4"

    # ✅ تبدیل با ffmpeg
    command = f"""ffmpeg -i "{filename}" -qscale 0 -pix_fmt yuv420p -filter:v fps=fps=24 -vf scale=1080:1920 -c:a copy "{output_file}" """
    subprocess.call(command, shell=True)

    # ✅ آپلود به MinIO
    s3.upload_file(output_file, BUCKET, f"{FOLDER}/{os.path.basename(output_file)}")

    return {
        "status": "done",
        "converted_file": os.path.basename(output_file),
        "uploaded_to": f"{FOLDER}/{os.path.basename(output_file)}"
    }
