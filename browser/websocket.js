// We have to use complete files in the backend. Have to assemble the stream there.
// This means we periodically have to reset the audio file here in the frontend.
// I.e. with a fixed interval (kind of a buffer-size {in the backend}) we need to stop and start the media recorder. The backend also has to be told when this happens.
document.getElementById("start").onclick = () => {
    // Get microphone access
    navigator.mediaDevices.getUserMedia({audio: true})
        .then(stream => {
            const mediaRecorder = new MediaRecorder(stream, {mimeType: "audio/webm;codecs=opus", bitsPerSecond: 256000});
            mediaRecorder.start(1000); // commit every second

            const socket = new WebSocket('ws://localhost:8000');

            socket.onmessage = msg => console.log(msg.data) // this will be the display of subtitles

            mediaRecorder.addEventListener('dataavailable', e => {
                // This should be called roughly every second, by the mediaRecorder
                console.log("data available:", e.data)
                socket.send(e.data)
            });

            console.log("Streaming audio to user with bitrate", mediaRecorder.audioBitsPerSecond)
            console.log("Streaming audio to user with mimeType", mediaRecorder.mimeType)
        })
        .catch(err => {
            console.log('Unable to access mic', err);
        });
}
