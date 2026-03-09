import os
import re
import asyncio
import requests
import logging
import threading
from flask import Flask
from pyrogram import Client, filters
from pyromod import listen
from pyrogram.types import Message
import config

logging.basicConfig(level=logging.INFO)

# -------- Render Web Server --------

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot Running"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# -------- Bot Setup --------

bot = Client(
    "QualityBot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN
)

def clean_filename(text):
    return re.sub(r'[\\/*?:"<>|]', "", text).strip()

def count_urls(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()

        total_links = len(lines)
        video_links = sum(1 for line in lines if any(x in line.lower() for x in [".m3u8",".mp4"]))
        pdf_links = sum(1 for line in lines if ".pdf" in line.lower())

        return total_links, pdf_links, video_links
    except:
        return 0,0,0


@bot.on_message(filters.command(["start"]))
async def start_handler(client, m: Message):
    await m.reply_text("नमस्ते! Quality Education बैच निकालने के लिए /qe कमांड का उपयोग करें।")


@bot.on_message(filters.command(["qe"]))
async def qe_handler(client, m: Message):

    temp_msg = await m.reply_text("🔍 Fetching batches...")

    headers = {
        "Host": "test.qualityeducation.in",
        "accept-encoding": "gzip",
        "user-agent": "okhttp/3.14.7"
    }

    try:

        r = requests.get(
            "https://test.qualityeducation.in/api/video-category-get",
            headers=headers
        )

        j = r.json()

        listing = "🎓 Available Batches\n\n"

        for i in j["data"]:
            listing += f"🔹 `{i['id']}` → {i['category_name']}\n"

        await temp_msg.edit_text(listing)

        bi_msg = await client.ask(m.chat.id,"🆔 Course ID भेजो")
        bi = bi_msg.text.strip()

        update = await m.reply_text(f"⏳ Extracting `{bi}`")

        r2 = requests.get(
            f"https://test.qualityeducation.in/api/combo-get/318096/{bi}",
            headers=headers
        )

        j2 = r2.json()

        if not j2.get("data") or not j2["data"].get("video"):
            await update.edit_text("❌ Invalid ID")
            return

        dn = j2["data"]["video"][0]["title"]

        file_name = f"{clean_filename(bi)}_{clean_filename(dn)}.txt"

        with open(file_name,"w",encoding="utf-8") as f:

            for video_data in j2["data"]["video"]:

                di = video_data["id"]

                r3 = requests.get(
                    f"https://test.qualityeducation.in/api/subject-get/{di}",
                    headers=headers
                )

                j3 = r3.json()

                for subject in j3.get("data",[]):

                    ti = subject["id"]

                    r4 = requests.get(
                        f"https://test.qualityeducation.in/api/subject-get/{di}/{ti}",
                        headers=headers
                    )

                    j4 = r4.json()

                    for content in j4.get("data",[]):

                        topic = content.get("topic_name","Untitled")
                        pdf = content.get("pdf_link")

                        videos = [
                            content.get("quality_1080"),
                            content.get("quality_720"),
                            content.get("quality_480"),
                            content.get("quality_360"),
                            content.get("video_link")
                        ]

                        v = next((x for x in videos if x),None)

                        if pdf:
                            f.write(f"{topic}: {pdf}\n")

                        if v:
                            f.write(f"{topic}: {v}\n")


        total,pdfs,vids = count_urls(file_name)

        caption = (
            f"📦 Batch Extracted\n\n"
            f"📛 Batch: {dn}\n\n"
            f"Total: {total}\n"
            f"Videos: {vids}\n"
            f"PDFs: {pdfs}"
        )

        await m.reply_document(file_name,caption=caption)

        os.remove(file_name)

        await update.delete()

    except Exception as e:
        logging.error(e)
        await m.reply_text(f"Error:\n{e}")


# -------- Start Bot --------

async def main():

    await bot.start()

    logging.info("BOT STARTED")

    await asyncio.Event().wait()


if __name__ == "__main__":

    threading.Thread(target=run_web).start()

    asyncio.run(main())                    
