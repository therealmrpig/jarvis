# WakewordModule documentation

Monitors an audio stream for a specific trigger phrase using a continuous-drain pattern.

## Class `WakewordModule`

### `__init__(audio_queue: queue.Queue, trigger_phrase: str, on_detected: Callable[[], None])`
Initializes the wakeword listener with a provided audio queue and detection callback. 
- **Inputs**: 
    - `audio_queue` (queue.Queue): The subscriber queue containing raw PCM chunks.
    - `trigger_phrase` (str): The phrase to listen for (e.g., "Jarvis").
    - `on_detected` (function): Callback executed when the trigger is identified.

### `set_active(active: bool)`
Enables or disables the computational heavy-lifting of pattern matching. 
- **Inputs**: 
    - `active` (bool): If `True`, performs detection logic; if `False`, simply drains the queue to prevent latency.
- **Outputs**: None.

### Internal Logic: The "Running Vacuum"
The module runs a continuous loop that always pulls data from the `audio_queue`. 
- When `active` is **True**: The module performs signal analysis/pattern matching on the chunk.
- When `active` is **False**: The module immediately discards the chunk. This prevents buffer bloat and ensures that when activation resumes, the module is processing real-time audio rather than stale data.

## Responsibilities
- **Stream Maintenance**: Ensures the `audio_queue` stays fresh by continuous consumption.
- **Low Latency**: Minimizes delay between trigger detection and Orchestrator notification.
- **Resource Efficiency**: Zero computational overhead for pattern matching when the system is in an active dialogue state.
