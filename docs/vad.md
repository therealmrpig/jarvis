# VADModule documentation

Monitors audio streams for end-of-speech detection using Silero VAD.

## Class `VADModule`

### `__init__(audio_queue: queue.Queue, on_end_of_speech: Callable[[], None])`
Initializes the VAD engine with a provided audio queue and an end-of-speech callback.
- **Inputs**: 
    - `audio_queue` (queue.Queue): The subscriber queue containing raw PCM chunks.
    - `on_end_of_speech` (function): Callback executed when silence exceeds the 500ms threshold.

### `set_active(active: bool)`
Enables or disables the detection engine via the Client Orchestrator.
- **Inputs**: 
    - `active` (bool): If `True`, performs inference; if `False`, purely drains the queue to maintain real-time freshness.
- **Usage**: Set to `False` during active speaker playback/TTS to prevent false triggers.

### `stop()`
Gracefully terminates the background processing thread and cleans up resources.
- **Inputs**: None.
- **Outputs**: None.

## Internal Logic: The "Running Vacuum"
To ensure zero latency when re-activating, the module follows a strict continuous-drain pattern:
1.  **Continuous Drain:** The module calls `audio_queue.get()` on every loop iteration. This prevents audio accumulation (buffer bloat) and ensures that any data processed is real-time.
2.  **Threshold Detection:** Uses a fixed 500ms silence window to trigger the `on_end_of_speech` event.
3.  **Efficient Idling:** When `active` is `False`, the module stays alive but performs no expensive neural network inference, simply discarding incoming chunks.

## Dependencies
- `silero-vad` (via ONNX runtime)
- `numpy`
- `queue.Queue`
