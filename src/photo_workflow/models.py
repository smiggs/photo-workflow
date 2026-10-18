"""Versioned records shared by pipeline stages."""

from datetime import datetime, timezone
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Sha256 = Annotated[str, Field(pattern=r'^[0-9a-f]{64}$')]
PositiveInt = Annotated[int, Field(gt=0)]


class Record(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True, allow_inf_nan=False)
    schema_version: Literal[1] = 1


class StageState(StrEnum):
    COMPLETE = 'complete'
    PARTIAL = 'partial'
    AWAITING_APPROVAL = 'awaiting_approval'
    FAILED = 'failed'


class Issue(Record):
    severity: Literal['warning', 'error'] = 'warning'
    code: str
    message: str
    relative_path: str | None = None


class ToolVersion(Record):
    name: str
    available: bool
    executable_path: str | None = None
    version: str | None = None
    native_versions: dict[str, str] = Field(default_factory=dict)


class ApprovalRecord(Record):
    checkpoint: str
    reviewer: Annotated[str, Field(min_length=1)]
    decision: Literal['approved', 'rejected']
    timestamp_utc: datetime
    input_hashes: Annotated[dict[str, Sha256], Field(min_length=1)]
    reason: Annotated[str, Field(min_length=1)]

    @field_validator('reviewer', 'reason')
    @classmethod
    def nonblank_text(cls, value):
        if not value.strip():
            raise ValueError('reviewer and reason must contain text')
        return value

    @field_validator('timestamp_utc')
    @classmethod
    def utc_timestamp(cls, value):
        if value.tzinfo is None or value.utcoffset().total_seconds() != 0:
            raise ValueError('timestamp_utc must include UTC offset')
        return value.astimezone(timezone.utc)


Checkpoint = Literal['cohort-rules', 'coordinate-contract']


class ReviewScope(Record):
    cohort_rule_version: Literal['1'] = '1'
    coordinate_contract_version: Literal['1'] = '1'
    cohort_ids: list[Sha256]
    coordinate_spaces: list[Literal['raw_sensor', 'active_sensor', 'decoded_detection', 'preview']]


class ReviewPacket(Record):
    run_id: Sha256
    checkpoint: Checkpoint
    scope: ReviewScope
    input_hashes: dict[str, Sha256]
    evidence_paths: list[str]
    camera_coverage: list[dict]
    blockers: list[str]
    limitations: list[str]


class ReviewDecision(ApprovalRecord):
    checkpoint: Checkpoint
    run_id: Sha256
    packet_sha256: Sha256
    scope: ReviewScope
    supersedes_sha256: Sha256 | None = None


class LensState(Record):
    lens: str | None = None
    focal_length_mm: Annotated[float, Field(gt=0)] | None = None
    aperture_f_number: Annotated[float, Field(gt=0)] | None = None
    focus_distance_m: Annotated[float, Field(gt=0)] | None = None


class CaptureMetadata(Record):
    make: str | None = None
    model: str | None = None
    body_serial: str | None = None
    captured_at_local: str | None = None
    captured_at_utc: datetime | None = None
    orientation: Annotated[int, Field(ge=1, le=8)] | None = None
    readout_mode: str | None = None
    lens: LensState = Field(default_factory=LensState)
    source_fields: dict[str, str | int | float | list] = Field(default_factory=dict)

    @field_validator('captured_at_utc')
    @classmethod
    def capture_utc(cls, value):
        return ApprovalRecord.utc_timestamp(value) if value is not None else None


class Rectangle(Record):
    x_px: float = 0
    y_px: float = 0
    width_px: Annotated[float, Field(gt=0)]
    height_px: Annotated[float, Field(gt=0)]


class ImageGeometry(Record):
    raw_width_px: PositiveInt
    raw_height_px: PositiveInt
    active_area: Rectangle
    cfa_pattern: list[list[int]] | None = None
    colour_description: str
    decoder_flip: int

    @model_validator(mode='after')
    def within_raw(self):
        a = self.active_area
        if (a.x_px < 0 or a.y_px < 0 or a.x_px + a.width_px > self.raw_width_px
                or a.y_px + a.height_px > self.raw_height_px):
            raise ValueError('active area must lie within raw dimensions')
        return self


class CoordinateSpace(StrEnum):
    RAW = 'raw_sensor'
    ACTIVE = 'active_sensor'
    DETECTION = 'decoded_detection'
    DARKTABLE = 'darktable_input'
    EXPORT = 'final_export'
    PREVIEW = 'preview'


class CoordinateTransform(Record):
    contract_version: Literal['1'] = '1'
    source_space: CoordinateSpace
    target_space: CoordinateSpace
    kind: Literal['homography', 'unsupported'] = 'homography'
    matrix: tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]] | None = None
    source_domain: Rectangle
    target_domain: Rectangle
    inverse_available: bool = True
    max_error_px: Annotated[float, Field(ge=0)] = 1e-6
    implementation: Literal['photo_workflow.coordinates.v1'] = 'photo_workflow.coordinates.v1'
    rounding: Literal['nearest_half_up'] = 'nearest_half_up'
    mask_resampling: Literal['nearest'] = 'nearest'
    unsupported_reason: str | None = None

    @model_validator(mode='after')
    def check_kind(self):
        if self.kind == 'homography' and self.matrix is None:
            raise ValueError('homography requires a matrix')
        if self.kind == 'unsupported' and (self.inverse_available or not self.unsupported_reason):
            raise ValueError('unsupported mapping requires a reason and no inverse')
        return self


class RawFrame(Record):
    frame_id: Sha256
    content_sha256: Sha256
    relative_paths: Annotated[list[str], Field(min_length=1)]
    size_bytes: Annotated[int, Field(ge=0)]
    metadata: CaptureMetadata = Field(default_factory=CaptureMetadata)
    geometry: ImageGeometry | None = None
    cohort_id: Sha256 | None = None
    status: Literal['unreviewed', 'excluded'] = 'unreviewed'
    exclusion_reasons: list[str] = Field(default_factory=list)


class Cohort(Record):
    cohort_id: Sha256
    frame_ids: Annotated[list[Sha256], Field(min_length=1)]
    compatibility_facts: dict
    review_status: Literal['unreviewed'] = 'unreviewed'


class StageResult(Record):
    stage: str
    fingerprint_sha256: Sha256
    state: StageState
    artefacts: dict[str, Sha256]
    issues: list[Issue] = Field(default_factory=list)
    upstream_ids: list[Sha256] = Field(default_factory=list)
    counts: dict[str, Annotated[int, Field(ge=0)]] = Field(default_factory=dict)


class RunManifest(Record):
    run_id: Sha256
    source_root: str
    hash_algorithm: Literal['sha256'] = 'sha256'
    configuration_sha256: Sha256
    tools: list[ToolVersion]
    stages: dict[str, StageResult] = Field(default_factory=dict)
    approvals: list[ReviewDecision | ApprovalRecord] = Field(default_factory=list)


class Inventory(Record):
    source_root: str
    input_sha256: Sha256
    configuration_sha256: Sha256
    tools: list[ToolVersion]
    frames: list[RawFrame]
    cohorts: list[Cohort]
    issues: list[Issue]
    coordinate_contract_version: Literal['1'] = '1'
    review_status: Literal['awaiting_approval'] = 'awaiting_approval'


class CohortCollection(Record):
    cohorts: list[Cohort]


class DecodeOptions(Record):
    adapter: Literal['rawpy.raw_image_visible'] = 'rawpy.raw_image_visible'
    shot_select: Literal[0] = 0
    postprocess: Literal[False] = False
    domain: Literal['camera_native_sensor_samples'] = 'camera_native_sensor_samples'
    demosaicing: Literal[False] = False
    black_subtraction: Literal[False] = False
    automatic_brightness: Literal[False] = False
    white_balance: Literal[False] = False
    gamma: Literal[False] = False
    orientation_applied_to_samples: Literal[False] = False


class DecodedFrame(Record):
    frame_id: Sha256
    samples_path: str
    samples_sha256: Sha256
    samples_shape: tuple[PositiveInt, PositiveInt]
    samples_dtype: Literal['uint16'] = 'uint16'
    cfa_path: str
    cfa_sha256: Sha256
    cfa_dtype: Literal['uint8'] = 'uint8'
    overlay_path: str
    geometry: ImageGeometry
    decode_options: DecodeOptions = Field(default_factory=DecodeOptions)
    black_level_per_channel: list[int]
    white_level: PositiveInt
    coordinate_transforms: list[CoordinateTransform]
    round_trip_max_error_px: Annotated[float, Field(ge=0)]
    unsupported_spaces: list[CoordinateSpace] = Field(default_factory=lambda: [CoordinateSpace.DARKTABLE, CoordinateSpace.EXPORT])


class DecodeReport(Record):
    state: StageState
    inventory_sha256: Sha256
    frames: list[DecodedFrame]
    issues: list[Issue]
    darktable_export_calibration: Literal['unverified'] = 'unverified'


class LogEvent(Record):
    timestamp_utc: datetime
    stage: str
    event: Literal['stage_committed'] = 'stage_committed'
    state: StageState
    fingerprint_sha256: Sha256

    @field_validator('timestamp_utc')
    @classmethod
    def log_utc(cls, value):
        return ApprovalRecord.utc_timestamp(value)
