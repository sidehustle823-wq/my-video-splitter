import os
import subprocess
import asyncio
from dotenv import load_dotenv
from pyrogram import Client, filters

# .env (Secret File) से क्रेडेंशियल्स लोड करने के लिए
load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

app = Client("splitter_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# यूजर की टाइम सेटिंग्स रखने के लिए (डिफ़ॉल्ट 5 मिनट = 300 सेकेंड)
user_time = {}

@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text(
        "👋 **नमस्ते! मुझे 1GB+ का कोई भी वीडियो भेजें।**\n\n"
        "डिफ़ॉल्ट रूप से मैं हर 5 मिनट पर वीडियो काटूँगा।\n"
        "समय बदलने के लिए टाइप करें: `/set <मिनट>`\n"
        "उदाहरण: `/set 3` (3-3 मिनट के टुकड़ों के लिए)"
    )

@app.on_message(filters.command("set"))
async def set_timer(client, message):
    try:
        minutes = int(message.command[1])
        user_time[message.chat.id] = minutes * 60
        await message.reply_text(f"✅ टाइम सेट! अब वीडियो को हर **{minutes} मिनट** के टुकड़ों में काटा जाएगा।")
    except Exception as e:
        await message.reply_text("❌ गलत फॉर्मेट! ऐसे लिखें: `/set 2`")

@app.on_message(filters.video)
async def split_video(client, message):
    chat_id = message.chat.id
    split_seconds = user_time.get(chat_id, 300)
    
    status = await message.reply_text("📥 वीडियो डाउनलोड हो रहा है... इसमें थोड़ा समय लग सकता है।")
    
    try:
        # वीडियो डाउनलोड करना
        input_file = await message.download()
        await status.edit_text("⚙️ FFmpeg इंजन से video को टुकड़ों में काटा जा रहा है...")
        
        # FFmpeg पाथ लोड करना (ताकि Render पर एरर न आए)
        import static_ffmpeg
        static_ffmpeg.add_paths()
        
        # FFmpeg से वीडियो को बिना री-एन्कोड किए काटना (बेहद फास्ट प्रोसेस)
        output_pattern = f"part_{chat_id}_%03d.mp4"
        ffmpeg_cmd = [
            "ffmpeg", "-i", input_file, "-c", "copy", "-map", "0",
            "-segment_time", str(split_seconds), "-f", "segment",
            "-reset_timestamps", "1", output_pattern
        ]
        
        # कमांड रन करना
        process = await asyncio.create_subprocess_exec(*ffmpeg_cmd)
        await process.communicate()
        
        await status.edit_text("📤 कटे हुए टुकड़े टेलीग्राम पर अपलोड हो रहे हैं...")
        
        # कटे हुए पार्ट्स को खोजना और भेजना
        files = sorted([f for f in os.listdir('.') if f.startswith(f"part_{chat_id}_") and f.endswith(".mp4")])
        
        if not files:
            await status.edit_text("❌ वीडियो काटने में कोई दिक्कत आई।")
            if os.path.exists(input_file):
                os.remove(input_file)
            return

        for idx, file_name in enumerate(files, start=1):
            try:
                await message.reply_video(video=file_name, caption=f"🎬 भाग {idx}")
            except Exception as upload_err:
                print(f"Upload error: {upload_err}")
            finally:
                if os.path.exists(file_name):
                    os.remove(file_name)  # स्पेस खाली करने के लिए डिलीट करें
            
        if os.path.exists(input_file):
            os.remove(input_file)  # ओरिजिनल फाइल डिलीट
            
        await status.delete()
        
    except Exception as main_err:
        await status.edit_text(f"❌ एक एरर आया: {str(main_err)}")
        if 'input_file' in locals() and os.path.exists(input_file):
            os.remove(input_file)

print("बॉट बैकएंड में चालू हो गया है...")
app.run()
