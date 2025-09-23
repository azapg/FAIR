from abc import ABC
from typing import List

from fair_platform.sdk import TranscriptionPlugin, GradePlugin, TextField, TranscribedSubmission, SwitchField, \
    GradeResult, FairPlugin, NumberField, Submission
from fair_platform.sdk.settings import FileField


@FairPlugin(id="up.ac.pa.allan.zapata.simple_transcriber", name="SimpleTranscriber", version="1.0.0",
            author="Test Author", description="A simple transcriber plugin.")
class SimpleTranscriber(TranscriptionPlugin, ABC):
    instructions = TextField(label="Instructions", required=True, default="Transcribe the following math problem.")

    def transcribe(self, submission) -> TranscribedSubmission:
        transcription = f"{self.instructions.value} [Transcribed content from {submission.id}]"
        confidence = 0.95
        return TranscribedSubmission(
            transcription=transcription,
            confidence=confidence,
            original_submission=submission
        )


@FairPlugin(id="up.ac.pa.allan.zapata.simple_grader", name="SimpleGrader", version="1.0.0", author="Test Author")
class SimpleGrader(GradePlugin, ABC):
    strict = SwitchField(label="Strict Grading", required=False, default=False)

    def grade(self, transcription: TranscribedSubmission) -> GradeResult:
        if self.strict.value:
            return GradeResult(
                score=1.0 if "correct" in transcription.transcription.lower() else 0.0,
                feedback="Strict grading applied.",
                meta={}
            )
        return GradeResult(
            score=0.5,
            feedback="Lenient grading applied.",
            meta={}
        )


# TODO: What happens if a plugin implements multiple plugin types?
@FairPlugin(id="up.ac.pa.allan.zapata.complex_plugin", name="ComplexPlugin", version="1.0.0", author="Test Author")
class ComplexPlugin(TranscriptionPlugin, ABC):
    instructions = TextField(label="Instructions", required=True, default="Transcribe and grade the following content.")
    strict = SwitchField(label="Strict Grading", required=False, default=False)
    max_tokens = NumberField(label="Max Tokens", required=False, default=1000, ge=100, le=2000)
    temperature = NumberField(label="Temperature", required=False, default=0.7, ge=0.0, le=1.0)
    file = FileField(label="Reference File", required=False, file_types=["txt", "pdf"])

    def transcribe(self, submission) -> TranscribedSubmission:
        transcription = f"{self.instructions.value} [Transcribed content from {submission.id}]"
        confidence = 0.90
        return TranscribedSubmission(
            transcription=transcription,
            confidence=confidence,
            original_submission=submission
        )

    def transcribe_batch(self, submissions: List[Submission]) -> List[TranscribedSubmission]:
        return [self.transcribe(sub) for sub in submissions]


from fair_platform.sdk import get_plugin_metadata, list_plugins, list_transcription_plugins, list_grade_plugins

print(get_plugin_metadata("SimpleTranscriber"))
print(list_plugins())
