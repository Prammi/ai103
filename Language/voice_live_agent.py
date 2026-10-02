import os
import sys
import asyncio
import base64
import queue
from typing import Optional, TYPE_CHECKING

import pyaudio

from dotenv import load_dotenv
from azure.identity.aio import AzureCliCredential
from azure.ai.voicelive.aio import connect
from azure.ai.voicelive.models import (
    AzureStandardVoice,
    InputAudioFormat,
    OutputAudioFormat,
    Modality,
    RequestSession,
    ServerEventType,
    ServerVad,
)

if TYPE_CHECKING:
    from azure.ai.voicelive.aio import VoiceLiveConnection


# =========================================================
# AUDIO CONFIGURATION
#
# Voice Live PCM16 default:
#   24,000 Hz
#   16-bit
#   Mono
# =========================================================

SAMPLE_RATE = 24000
CHANNELS = 1
CHUNK_SIZE = 1200


# =========================================================
# AUDIO PROCESSOR
# =========================================================
class AudioProcessor:

    def __init__(
        self,
        connection: "VoiceLiveConnection",
    ):
        self.connection = connection

        self.audio = pyaudio.PyAudio()

        self.format = pyaudio.paInt16
        self.channels = CHANNELS
        self.rate = SAMPLE_RATE
        self.chunk_size = CHUNK_SIZE

        self.loop: Optional[
            asyncio.AbstractEventLoop
        ] = None

        self.input_stream = None
        self.output_stream = None

        # Audio packets received from Voice Live
        self.playback_queue = queue.Queue()

        # Used when user interrupts the assistant
        self.playback_generation = 0

    # =====================================================
    # MICROPHONE
    # =====================================================
    def start_microphone(self):

        if self.input_stream:
            return

        self.loop = asyncio.get_running_loop()

        def microphone_callback(
            in_data,
            frame_count,
            time_info,
            status_flags,
        ):
            audio_base64 = base64.b64encode(
                in_data
            ).decode("utf-8")

            asyncio.run_coroutine_threadsafe(
                self.connection
                .input_audio_buffer
                .append(
                    audio=audio_base64
                ),
                self.loop,
            )

            return (
                None,
                pyaudio.paContinue,
            )

        self.input_stream = self.audio.open(
            format=self.format,
            channels=self.channels,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk_size,
            stream_callback=microphone_callback,
        )

        self.input_stream.start_stream()

        print("Microphone started.")

    # =====================================================
    # SPEAKER PLAYBACK
    # =====================================================
    def start_speaker(self):

        if self.output_stream:
            return

        # -------------------------------------------------
        # VERY IMPORTANT
        #
        # Voice Live packets don't necessarily have exactly
        # the same size as PyAudio callback buffers.
        #
        # Therefore we MUST keep unused bytes from a packet
        # and play them during the next callback.
        #
        # This is the important fix.
        # -------------------------------------------------

        remaining = bytes()
        remaining_generation = 0

        def speaker_callback(
            in_data,
            frame_count,
            time_info,
            status_flags,
        ):
            nonlocal remaining
            nonlocal remaining_generation

            bytes_per_sample = (
                pyaudio.get_sample_size(
                    pyaudio.paInt16
                )
            )

            # Mono:
            # frame_count × 2 bytes
            bytes_required = (
                frame_count
                * bytes_per_sample
                * CHANNELS
            )

            output = bytes()

            # ---------------------------------------------
            # First consume leftover audio from the
            # previous Voice Live packet.
            # ---------------------------------------------
            if (
                remaining
                and remaining_generation
                == self.playback_generation
            ):
                take = min(
                    bytes_required,
                    len(remaining),
                )

                output += remaining[:take]

                remaining = remaining[take:]

            else:
                remaining = bytes()

            # ---------------------------------------------
            # Continue taking Voice Live packets until
            # this PyAudio frame is completely filled.
            # ---------------------------------------------
            while len(output) < bytes_required:

                try:
                    (
                        generation,
                        packet,
                    ) = self.playback_queue.get_nowait()

                except queue.Empty:

                    # Nothing available yet.
                    # Fill rest with silence.
                    silence_length = (
                        bytes_required
                        - len(output)
                    )

                    output += bytes(
                        silence_length
                    )

                    break

                # Ignore old packets after interruption
                if (
                    generation
                    != self.playback_generation
                ):
                    continue

                if not packet:
                    continue

                bytes_needed = (
                    bytes_required
                    - len(output)
                )

                # -----------------------------------------
                # Take only what PyAudio currently needs.
                # -----------------------------------------
                output += packet[
                    :bytes_needed
                ]

                # -----------------------------------------
                # SAVE THE REST.
                #
                # This was missing from our previous
                # implementation.
                # -----------------------------------------
                if len(packet) > bytes_needed:

                    remaining = packet[
                        bytes_needed:
                    ]

                    remaining_generation = (
                        generation
                    )

            return (
                output,
                pyaudio.paContinue,
            )

        self.output_stream = self.audio.open(
            format=self.format,
            channels=self.channels,

            # Must match Voice Live PCM16 output
            rate=self.rate,

            output=True,
            frames_per_buffer=self.chunk_size,
            stream_callback=speaker_callback,
        )

        self.output_stream.start_stream()

        print(
            "Speaker started at "
            f"{self.rate} Hz PCM16 mono."
        )

    # =====================================================
    # QUEUE AGENT AUDIO
    # =====================================================
    def play_audio(
        self,
        audio_data: bytes,
    ):
        self.playback_queue.put(
            (
                self.playback_generation,
                audio_data,
            )
        )

    # =====================================================
    # USER INTERRUPTED AGENT
    # =====================================================
    def clear_playback(self):

        # Increase generation.
        #
        # Existing packets become obsolete automatically.
        self.playback_generation += 1

        while not self.playback_queue.empty():

            try:
                self.playback_queue.get_nowait()

            except queue.Empty:
                break

    # =====================================================
    # CLEANUP
    # =====================================================
    def shutdown(self):

        if self.input_stream:

            self.input_stream.stop_stream()
            self.input_stream.close()

            self.input_stream = None

        if self.output_stream:

            self.output_stream.stop_stream()
            self.output_stream.close()

            self.output_stream = None

        self.audio.terminate()


# =========================================================
# VOICE LIVE AGENT
# =========================================================
async def run_voice_agent():

    load_dotenv()

    endpoint = os.getenv(
        "AZURE_VOICELIVE_ENDPOINT"
    )

    agent_name = os.getenv(
        "AZURE_VOICELIVE_AGENT_NAME"
    )

    project_name = os.getenv(
        "AZURE_VOICELIVE_PROJECT_NAME"
    )

    if not endpoint:
        raise ValueError(
            "AZURE_VOICELIVE_ENDPOINT "
            "is missing from .env"
        )

    if not agent_name:
        raise ValueError(
            "AZURE_VOICELIVE_AGENT_NAME "
            "is missing from .env"
        )

    if not project_name:
        raise ValueError(
            "AZURE_VOICELIVE_PROJECT_NAME "
            "is missing from .env"
        )

    print()
    print("Connecting to Voice Live...")
    print(f"Agent   : {agent_name}")
    print(f"Project : {project_name}")
    print(
        f"Audio   : PCM16 / "
        f"{SAMPLE_RATE} Hz / mono"
    )

    credential = AzureCliCredential()

    audio_processor = None

    try:

        # =================================================
        # CONNECT TO VOICE LIVE
        # =================================================
        async with connect(
            endpoint=endpoint,
            credential=credential,
            api_version="2026-01-01-preview",
            agent_name=agent_name,
            project_name=project_name,
        ) as connection:

            print(
                "Connected to Voice Live."
            )

            # =================================================
            # VOICE CONFIGURATION
            # =================================================

            voice = AzureStandardVoice(
                name="en-US-AvaNeural",

                # Slightly slower speech.
                #
                # Once playback is correct,
                # you can change this to:
                #
                # 0.8
                # 0.7
                # 0.6
                rate="0.8",
            )

            # =================================================
            # VAD
            # =================================================

            turn_detection = ServerVad(
                threshold=0.5,
                prefix_padding_ms=300,
                silence_duration_ms=700,
            )

            # =================================================
            # SESSION
            # =================================================

            session = RequestSession(

                modalities=[
                    Modality.TEXT,
                    Modality.AUDIO,
                ],

                voice=voice,

                # Microphone sends PCM16
                input_audio_format=(
                    InputAudioFormat.PCM16
                ),

                # Voice Live returns PCM16
                output_audio_format=(
                    OutputAudioFormat.PCM16
                ),

                # Explicit microphone sample rate
                input_audio_sampling_rate=(
                    SAMPLE_RATE
                ),

                turn_detection=(
                    turn_detection
                ),
            )

            await connection.session.update(
                session=session
            )

            # =================================================
            # AUDIO PROCESSOR
            # =================================================

            audio_processor = AudioProcessor(
                connection
            )

            audio_processor.start_speaker()

            print()
            print("=" * 60)
            print("AZURE VOICE LIVE AGENT")
            print("=" * 60)
            print(
                "Voice       : en-US-AvaNeural"
            )
            print(
                "Speech rate : 0.8"
            )
            print(
                "Format      : PCM16"
            )
            print(
                "Sample rate : 24000 Hz"
            )
            print(
                "Channels    : Mono"
            )
            print()
            print(
                "Waiting for session..."
            )
            print(
                "Press Ctrl+C to exit."
            )
            print("=" * 60)
            print()

            # =================================================
            # EVENTS
            # =================================================

            async for event in connection:

                # -----------------------------------------
                # SESSION READY
                # -----------------------------------------
                if (
                    event.type
                    == ServerEventType
                    .SESSION_UPDATED
                ):

                    print(
                        "Session ready."
                    )

                    print(
                        "Start speaking...\n"
                    )

                    audio_processor.start_microphone()

                # -----------------------------------------
                # USER STARTED SPEAKING
                # -----------------------------------------
                elif (
                    event.type
                    == ServerEventType
                    .INPUT_AUDIO_BUFFER_SPEECH_STARTED
                ):

                    print(
                        "Listening..."
                    )

                    # Stop queued assistant speech
                    audio_processor.clear_playback()

                # -----------------------------------------
                # USER STOPPED SPEAKING
                # -----------------------------------------
                elif (
                    event.type
                    == ServerEventType
                    .INPUT_AUDIO_BUFFER_SPEECH_STOPPED
                ):

                    print(
                        "Processing..."
                    )

                # -----------------------------------------
                # USER TRANSCRIPTION
                # -----------------------------------------
                elif (
                    event.type
                    == ServerEventType
                    .CONVERSATION_ITEM_INPUT_AUDIO_TRANSCRIPTION_COMPLETED
                ):

                    transcript = event.get(
                        "transcript",
                        "",
                    )

                    print()
                    print(
                        f"You: {transcript}"
                    )

                # -----------------------------------------
                # AGENT AUDIO
                # -----------------------------------------
                elif (
                    event.type
                    == ServerEventType
                    .RESPONSE_AUDIO_DELTA
                ):

                    # SDK 1.3.0 exposes the PCM bytes
                    # directly as event.delta.
                    #
                    # Microsoft's official Python sample
                    # queues event.delta directly.
                    audio_processor.play_audio(
                        event.delta
                    )

                # -----------------------------------------
                # AGENT TRANSCRIPT
                # -----------------------------------------
                elif (
                    event.type
                    == ServerEventType
                    .RESPONSE_AUDIO_TRANSCRIPT_DONE
                ):

                    transcript = event.get(
                        "transcript",
                        "",
                    )

                    print()
                    print(
                        f"Agent: {transcript}"
                    )
                    print()

                # -----------------------------------------
                # RESPONSE FINISHED
                # -----------------------------------------
                elif (
                    event.type
                    == ServerEventType
                    .RESPONSE_AUDIO_DONE
                ):

                    print(
                        "Agent finished speaking."
                    )

                # -----------------------------------------
                # ERROR
                # -----------------------------------------
                elif (
                    event.type
                    == ServerEventType.ERROR
                ):

                    print()
                    print(
                        "Voice Live error:"
                    )

                    print(
                        event.error.message
                    )

    finally:

        if audio_processor:

            audio_processor.shutdown()

        await credential.close()


# =========================================================
# MAIN
# =========================================================
def main():

    try:

        asyncio.run(
            run_voice_agent()
        )

    except KeyboardInterrupt:

        print()
        print(
            "Voice Live session ended."
        )

    except Exception as error:

        print()
        print("ERROR:")
        print(error)

        sys.exit(1)


if __name__ == "__main__":
    main()