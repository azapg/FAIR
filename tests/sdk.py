from abc import ABC

from fair_platform.sdk import TranscriptionPlugin, GradePlugin, TextField, TranscribedSubmission, SwitchField, \
    GradeResult


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
