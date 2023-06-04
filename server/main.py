import asyncio
import os

import websockets
import whisper
from pydub import AudioSegment

streamed_audio = 'audio.ogg'
if os.path.exists(streamed_audio):
    os.remove(streamed_audio)
decompressed_wave = "destination.wav"
if os.path.exists(decompressed_wave):
    os.remove(decompressed_wave)

audio_model = whisper.load_model("medium")

print("READY")


async def websocket_handler(websocket, path):
    q = asyncio.Queue()
    listener_task = asyncio.create_task(listen_for_messages(websocket, q))
    sender_task = asyncio.create_task(send_messages(websocket, q))

    print("Starting tasks")
    done, pending = await asyncio.wait(
        [listener_task, sender_task],
        return_when=asyncio.FIRST_COMPLETED,
    )

    print("cleaning up")
    for task in pending:
        task.cancel()


async def listen_for_messages(websocket, q):
    try:
        async for message in websocket:
            print(f"Received message: {message}")
            if len(message) > 5:
                print("appending x bytes to file", len(message))
                with open(streamed_audio, 'ab') as file:
                    file.write(message)
                await q.put(streamed_audio)
                print("Triggered Queue")
    except websockets.exceptions.ConnectionClosed:
        print("ConnectionClosed")


async def send_messages(websocket, q):
    while True:
        if q.empty():
            fname = await q.get()
        while not q.empty():
            fname = await q.get()
        print("Converting audio")
        AudioSegment.from_file(fname).export(decompressed_wave, format="wav")
        print("Finished wav audio")

        filesize = os.path.getsize(decompressed_wave)
        print("Transcribing filesize", filesize)
        result = audio_model.transcribe(decompressed_wave, language="en", task="transcribe")["text"]
        print("Sending result", result)
        await websocket.send(result)


# Start websocket server on port 8000
if __name__ == "__main__":
    start_server = websockets.serve(websocket_handler, "localhost", 8000)
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()
