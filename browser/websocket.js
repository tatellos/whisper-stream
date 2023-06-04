document.getElementById("start").onclick = () => {
    // Get microphone access
    navigator.mediaDevices.getUserMedia({audio: true})
        .then(stream => {
            const mediaRecorder = new MediaRecorder(stream);
            mediaRecorder.start(1000); // commit every second

            const socket = new WebSocket('ws://localhost:8000');

            socket.onmessage = msg => console.log(msg.data) // this will be the display of subtitles

            mediaRecorder.addEventListener('dataavailable', e => {
                // This should be called roughly every second, by the mediaRecorder
                console.log("data available:", e.data)
                socket.send(e.data)
            });
        })
        .catch(err => {
            console.log('Unable to access mic', err);
        });
}
