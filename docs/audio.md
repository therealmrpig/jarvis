# AudioHandler documentation

Manages real-time microphone input (via subscribers) and audio playback using PyAudio.

## Class `AudioHandler`

### `__init__(rate=16000, chunk=1024)`
Initializes the audio handler with a specific sample rate and buffer chunk size. Sets up queues for input/output and threading primitives.
- **Inputs**: 
    - `rate` (int): Sample rate in Hz (default: 16000).
    - `chunk` (int): Number of frames per buffer (default: 1024).

### `subscribe() -> queue.Queue`
Creates a new subscriber for live microphone audio stream. Any data received from the microphone will be pushed to this queue.
- **Inputs**: None.
- **Outputs**: A `queue.Queue` containing raw audio byte chunks.

### `start()`
Opens the microphone input stream and starts the background thread responsible for processing the playback queue.
- **Inputs**: None.
- **Outputs**: None.

### `play(audio_bytes)`
Queues raw audio data to be played back through the speakers. The data is sliced into chunks before being added to the output queue.
- **Inputs**: 
    - `audio_bytes` (bytes): Raw PCM audio data.
- **Outputs**: None.

### `cancel_playback()`
Immediately empties the playback queue, effectively stopping any queued audio from playing.
- **Inputs**: None.
- **Outputs**: None.

### `stop()`
Gracefully shuts down the audio handler by stopping all streams, joining threads, and terminating the PyAudio instance.
- **Inputs**: None.
- **Outputs**: None.
