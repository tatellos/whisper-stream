let chunks = [];
let mediaRecorder;

// Get microphone access
navigator.mediaDevices.getUserMedia({audio: true})
    .then(stream => {
        mediaRecorder = new MediaRecorder(stream);
        mediaRecorder.start();
        mediaRecorder.addEventListener('dataavailable', e => {
            chunks.push(e.data);
        });
    })
    .catch(err => {
        console.log('Unable to access mic', err);
    });

const socket = new WebSocket('ws://localhost:8000');
socket.onopen = () => {
    setInterval(() => {
        mediaRecorder.stop();
        const blob = new Blob(chunks, {'type': 'audio/ogg; codecs=opus'});
        console.log(blob)
        socket.send(blob)
        chunks = [];
        mediaRecorder.start();
    }, 1000);
}

socket.onmessage = msg => console.log(msg.data)
