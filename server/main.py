import asyncio

import websockets
import whisper

audio_model = whisper.load_model("tiny")

i = 0
y = 8
bytesToSave = b""


async def websocket_handler(websocket, path):
    global i, y, bytesToSave
    async for message in websocket:
        print(f"Received message: {message}")
        byteString = message
        if len(byteString) > 5:
            filename = str(i) + 'audio.ogg'
            i += 1
            if y > 0:
                # just testing the sound quality when adding multiple seconds together. It seems good!
                y -= 1
                bytesToSave += byteString
            else:
                y = 8
                with open(filename, 'wb') as file:
                    file.write(bytesToSave)
                bytesToSave = b""

            # result = audio_model.transcribe(filename, language="en", task="transcribe")
            await websocket.send('result["text"]')


# Start websocket server on port 8000
if __name__ == "__main__":
    start_server = websockets.serve(websocket_handler, "localhost", 8000)
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()
