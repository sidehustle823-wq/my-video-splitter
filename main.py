import os
import subprocess
import asyncio
from pyrogram import Client, filters

# अपने क्रेडेंशियल्स डालें (या इन्हें होस्टिंग पर एन्वायरमेंट वेरिएबल्स में सेट करें)
API_ID = 1234567  # अपना API ID यहाँ लिखें
API_HASH = "YOUR_API_HASH"  # अपना API Hash यहाँ लिखें
BOT_TOKEN = "YOUR_BOT_TOKEN"  # अपना Bot Token यहाँ लिखें

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
    except:
        await message.reply_text("❌ गलत फॉर्मेट! ऐसे लिखें: `/set 2`")

@app.on_message(filters.video)
async def split_video(client, message):
    chat_id = message.chat.id
    split_seconds = user_time.get(chat_id, 300)
    
    status = await message.reply_text("📥 वीडियो डाउनलोड हो रहा है... इसमें थोड़ा समय लग सकता है।")
    
    # वीडियो डाउनलोड करना
    input_file = await message.download()
    await status.edit_text("⚙️ FFmpeg इंजन से वीडियो को टुकड़ों में काटा जा रहा है...")
    
    # FFmpeg से वीडियो को बिना री-एन्कोड किए काटना (फास्ट प्रोसेस)
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
    
    # कटे हुए पार्ट्स को भेजना
    files = sorted([f for f in os.listdir('.') if f.startswith(f"part_{chat_id}_") and f.endswith(".mp4")])
    
    for idx, file_name in enumerate(files, start=1):
        await message.reply_video(video=file_name, caption=f"🎬 भाग {idx}")
        os.remove(file_name)  # स्पेस खाली करने के लिए डिलीट करें
        
    os.remove(input_file)  # ओरिजinal फाइल डिलीट
    await status.delete()

app.run()
