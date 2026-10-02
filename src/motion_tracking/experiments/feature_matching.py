"""Measure full-frame SIFT matching through the application runner."""

from motion_tracking.datasets.paths import MATCHER
from motion_tracking.experiments.measurements import measure_application_matcher
from motion_tracking.experiments.storage import (
    environment,
    publish_results,
    result_arguments,
    result_directory,
)


def main(argv: list[str] | None = None) -> None:
    args = result_arguments("matching", argv)
    with result_directory(args.output, "matching") as output:
        details = output / "details" if args.details else None
        if details is not None:
            details.mkdir()
        rows, images = measure_application_matcher(details)
        metadata = environment(
            [MATCHER / "inputs/jogging.mp4", MATCHER / "inputs/target.png"]
        )
        metadata["measurement"] = "motion_tracking.runner.run; full-frame SIFT"
        publish_results(
            output,
            "matching",
            rows,
            images,
            metadata,
            details=args.details,
        )


if __name__ == "__main__":
    main()
