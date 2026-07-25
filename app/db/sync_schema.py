"""
Apply additive schema fixes that create_all cannot do on existing tables.

Usage (from repo root):

    python -m app.db.sync_schema
"""

from sqlalchemy import text

from app.db.database import engine


def _column_names(conn, table: str) -> set[str]:
    rows = conn.execute(
        text(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = :table
            """
        ),
        {"table": table},
    )
    return {row[0] for row in rows}


def sync() -> None:
    with engine.begin() as conn:
        exhibit_cols = _column_names(conn, "exhibits")
        if "source_text" not in exhibit_cols:
            conn.execute(
                text(
                    "ALTER TABLE exhibits "
                    "ADD COLUMN source_text TEXT NOT NULL DEFAULT ''"
                )
            )
            conn.execute(
                text("ALTER TABLE exhibits ALTER COLUMN source_text DROP DEFAULT")
            )
            print("Added exhibits.source_text")
        else:
            print("exhibits.source_text already exists")

        content_cols = _column_names(conn, "exhibit_contents")
        if "historical_text" in content_cols and "generated_text" not in content_cols:
            conn.execute(
                text(
                    "ALTER TABLE exhibit_contents "
                    "RENAME COLUMN historical_text TO generated_text"
                )
            )
            print("Renamed exhibit_contents.historical_text -> generated_text")
        elif "generated_text" in content_cols:
            print("exhibit_contents.generated_text already exists")
        else:
            conn.execute(
                text(
                    "ALTER TABLE exhibit_contents "
                    "ADD COLUMN generated_text TEXT NOT NULL DEFAULT ''"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE exhibit_contents "
                    "ALTER COLUMN generated_text DROP DEFAULT"
                )
            )
            print("Added exhibit_contents.generated_text")

        content_cols = _column_names(conn, "exhibit_contents")
        if "audio_path" in content_cols and "audio_url" not in content_cols:
            conn.execute(
                text(
                    "ALTER TABLE exhibit_contents "
                    "RENAME COLUMN audio_path TO audio_url"
                )
            )
            print("Renamed exhibit_contents.audio_path -> audio_url")
        elif "audio_url" in content_cols:
            print("exhibit_contents.audio_url already exists")
        else:
            conn.execute(
                text("ALTER TABLE exhibit_contents ADD COLUMN audio_url VARCHAR(512)")
            )
            print("Added exhibit_contents.audio_url")

    print("Schema sync complete.")


if __name__ == "__main__":
    sync()
