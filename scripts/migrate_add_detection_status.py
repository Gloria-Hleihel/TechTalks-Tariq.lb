"""
Add the Week 3 detection-status fields to an existing SQLite database.
"""

import os
import sqlite3
import sys


sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
        )
    ),
)

import config


def main():
    database_path = os.path.join(
        config.BASE_DIR,
        "tariq.db",
    )

    if not os.path.exists(database_path):
        print(
            "No tariq.db exists yet. "
            "Start the app once to create the new schema."
        )

        return

    connection = sqlite3.connect(
        database_path
    )

    try:
        columns = {
            row[1]
            for row
            in connection.execute(
                "PRAGMA table_info(reports)"
            ).fetchall()
        }

        if "detection_status" not in columns:
            connection.execute(
                "ALTER TABLE reports "
                "ADD COLUMN detection_status "
                "TEXT NOT NULL DEFAULT 'pending'"
            )

            print(
                "Added reports.detection_status"
            )

        else:
            print(
                "reports.detection_status already exists"
            )

        if "detection_error" not in columns:
            connection.execute(
                "ALTER TABLE reports "
                "ADD COLUMN detection_error TEXT"
            )

            print(
                "Added reports.detection_error"
            )

        else:
            print(
                "reports.detection_error already exists"
            )

        connection.execute(
            """
            UPDATE reports
            SET
                detection_status = 'completed',
                detection_error = NULL
            WHERE EXISTS (
                SELECT 1
                FROM detections
                WHERE detections.report_id = reports.id
            )
            """
        )

        connection.commit()

        print(
            "Migration completed successfully."
        )

    finally:
        connection.close()


if __name__ == "__main__":
    main()