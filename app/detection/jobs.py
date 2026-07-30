from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timezone
from threading import Lock
from time import perf_counter
from uuid import uuid4

from flask import Flask
from sqlalchemy.exc import SQLAlchemyError

from app.detection.detector import (
    DetectionError,
    ImageNotFoundError,
    InferenceError,
    InvalidImageError,
    InvalidImagePathError,
    ModelLoadError,
    ModelNotFoundError,
    UnsupportedImageTypeError,
    detect_damage,
)
from models import Detection, Report, db


# A small worker pool is enough for local YOLO inference.
# More workers could overload the CPU or consume too much memory.
_executor = ThreadPoolExecutor(
    max_workers=2,
    thread_name_prefix="detection-worker",
)

_jobs = {}
_jobs_lock = Lock()


def utc_now() -> str:
    """
    Return the current UTC time in ISO 8601 format.
    """
    return datetime.now(timezone.utc).isoformat()


def create_detection_job(
    app: Flask,
    image_path: str,
    report_id: int | None = None,
) -> dict:
    """
    Create a queued detection job and submit it to the worker pool.
    """
    job_id = uuid4().hex

    job = {
        "job_id": job_id,
        "status": "queued",
        "image_path": image_path,
        "report_id": report_id,
        "progress": 0,
        "message": "Detection job is waiting to start.",
        "result": None,
        "error": None,
        "created_at": utc_now(),
        "started_at": None,
        "completed_at": None,
        "processing_time_ms": None,
    }

    with _jobs_lock:
        _jobs[job_id] = job

    _executor.submit(
        _run_detection_job,
        app,
        job_id,
        image_path,
        report_id,
    )

    return deepcopy(job)


def get_detection_job(job_id: str) -> dict | None:
    """
    Return a safe copy of a job so callers cannot modify job storage.
    """
    with _jobs_lock:
        job = _jobs.get(job_id)

        if job is None:
            return None

        return deepcopy(job)


def _update_job(job_id: str, **changes) -> None:
    """
    Update a job safely from any thread.
    """
    with _jobs_lock:
        job = _jobs.get(job_id)

        if job is not None:
            job.update(changes)


def _run_detection_job(
    app: Flask,
    job_id: str,
    image_path: str,
    report_id: int | None,
) -> None:
    """
    Run detection in a background thread.

    Flask application context is required because database operations
    use Flask-SQLAlchemy.
    """
    started = perf_counter()

    _update_job(
        job_id,
        status="processing",
        progress=25,
        message="The road image is being analyzed.",
        started_at=utc_now(),
    )

    try:
        with app.app_context():
            if report_id is not None:
                report = db.session.get(Report, report_id)

                if report is None:
                    _fail_job(
                        job_id,
                        started,
                        "REPORT_NOT_FOUND",
                        "The specified report does not exist.",
                    )
                    return

            detection_result = detect_damage(image_path)

            _update_job(
                job_id,
                progress=80,
                message="Detection completed. Preparing the result.",
            )

            response = {
                "report_id": report_id,
                "damage_type": detection_result.get(
                    "damage_type",
                    "None",
                ),
                "confidence": detection_result.get(
                    "confidence",
                    0.0,
                ),
                "severity_score": detection_result.get(
                    "severity_score",
                    0,
                ),
                "severity_label": detection_result.get(
                    "severity_label",
                    "Low",
                ),
                "bounding_boxes": detection_result.get(
                    "bounding_boxes",
                    [],
                ),
                "annotated_image_path": detection_result.get(
                    "annotated_image_path",
                ),
                "message": detection_result.get(
                    "message",
                    "Detection completed.",
                ),
                "saved_to_db": False,
            }

            if report_id is not None:
                detection = Detection(
                    report_id=report_id,
                    damage_type=response["damage_type"],
                    confidence=response["confidence"],
                    severity_score=response["severity_score"],
                    severity_label=response["severity_label"],
                    annotated_image_path=response[
                        "annotated_image_path"
                    ],
                )

                db.session.add(detection)
                db.session.commit()

                response["detection_id"] = detection.id
                response["saved_to_db"] = True

            elapsed_ms = round(
                (perf_counter() - started) * 1000,
                2,
            )

            response["processing_time_ms"] = elapsed_ms

            _update_job(
                job_id,
                status="completed",
                progress=100,
                message="Detection completed successfully.",
                result=response,
                completed_at=utc_now(),
                processing_time_ms=elapsed_ms,
            )

    except InvalidImagePathError:
        _fail_job(
            job_id,
            started,
            "INVALID_IMAGE_PATH",
            "The supplied image path is invalid.",
        )

    except ImageNotFoundError:
        _fail_job(
            job_id,
            started,
            "IMAGE_NOT_FOUND",
            "The requested image could not be found.",
        )

    except UnsupportedImageTypeError:
        _fail_job(
            job_id,
            started,
            "UNSUPPORTED_IMAGE_TYPE",
            "Only JPG, JPEG, and PNG images are supported.",
        )

    except InvalidImageError:
        _fail_job(
            job_id,
            started,
            "INVALID_IMAGE",
            "The supplied file is not a valid or readable image.",
        )

    except ModelNotFoundError:
        _fail_job(
            job_id,
            started,
            "MODEL_NOT_FOUND",
            "The detection model is currently unavailable.",
        )

    except ModelLoadError:
        _fail_job(
            job_id,
            started,
            "MODEL_LOAD_FAILED",
            "The detection model could not be initialized.",
        )

    except InferenceError:
        _fail_job(
            job_id,
            started,
            "INFERENCE_FAILED",
            "The image could not be analyzed.",
        )

    except SQLAlchemyError:
        db.session.rollback()

        _fail_job(
            job_id,
            started,
            "DATABASE_SAVE_FAILED",
            "Detection completed, but the result could not be saved.",
        )

    except DetectionError:
        _fail_job(
            job_id,
            started,
            "DETECTION_FAILED",
            "Detection could not be completed.",
        )

    except Exception:
        _fail_job(
            job_id,
            started,
            "INTERNAL_SERVER_ERROR",
            "An unexpected server error occurred.",
        )

    finally:
        with app.app_context():
            db.session.remove()


def _fail_job(
    job_id: str,
    started: float,
    error_code: str,
    message: str,
) -> None:
    """
    Mark a detection job as failed without exposing internal exceptions.
    """
    elapsed_ms = round(
        (perf_counter() - started) * 1000,
        2,
    )

    _update_job(
        job_id,
        status="failed",
        progress=100,
        message="Detection failed.",
        error={
            "code": error_code,
            "message": message,
        },
        completed_at=utc_now(),
        processing_time_ms=elapsed_ms,
    )