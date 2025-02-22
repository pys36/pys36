import os
import re
import tempfile
import subprocess
import requests
import asyncio
from concurrent.futures import ThreadPoolExecutor
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, filters

executor = ThreadPoolExecutor(max_workers=6)
MAGISKBOOT_PATH = os.path.abspath('./magiskboot')
if os.path.exists(MAGISKBOOT_PATH):
    os.chmod(MAGISKBOOT_PATH, 0o755)

def download_boot_img(url: str, dest_dir: str) -> str:
    try:
        response = requests.get(url, stream=True, timeout=40)
        response.raise_for_status()
        temp_file = tempfile.NamedTemporaryFile(delete=False, dir=dest_dir)
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                temp_file.write(chunk)
        temp_file.close()
        return temp_file.name
    except Exception as e:
        raise Exception(f"Error downloading file: {e}")

def process_boot_image(file_path: str, work_dir: str) -> str:
    try:
        result = subprocess.run(
            [MAGISKBOOT_PATH, "unpack", file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=True,
            cwd=work_dir
        )
        output = result.stdout.strip()
        if not output:
            return "magiskboot have no output"
        return output
    except subprocess.CalledProcessError as e:
        return f"Error processing boot image: {e.stdout.strip()}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"

async def unpack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /unpack <download_link>", reply_to_message_id=update.message.message_id)
        return
    link = context.args[0]
    if not re.match(r'^https?://', link):
        await update.message.reply_text("Please provide a valid URL starting with http:// or https:// !", reply_to_message_id=update.message.message_id)
        return
    await update.message.reply_text("Downloading and processing the boot image...", reply_to_message_id=update.message.message_id)
    def task():
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                boot_img_path = download_boot_img(link, temp_dir)
                cli_output = process_boot_image(boot_img_path, temp_dir)
                return cli_output
        except Exception as e:
            return f"An error occurred: {str(e)}"
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(executor, task)
    reply_message = f"Magiskboot output:\n```\n{result}\n```"
    await update.message.reply_text(reply_message, parse_mode="Markdown", reply_to_message_id=update.message.message_id)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("use /unpack <download_link> to process a boot.img file\nSupports Filebin + GitHub", reply_to_message_id=update.message.message_id)

def main():
    TOKEN = "TELEGRAM_TOKEN_HEREEEEEEEEEE"
    # ^ get from botfather
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("unpack", unpack, filters=filters.Regex(r'^/unpack\s+')))
    app.run_polling()

if __name__ == '__main__':
    main()
