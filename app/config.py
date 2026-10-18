"""Settings, read from `.env` in the repo root (each machine's `.env` is its environment).

The internal slug is always `rugby-coaching`; the brand only ever appears as
`app_name` (docs/decisions.md D26).
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent
DEV_KEYS = {"dev-coach", "dev-player", "dev-secret-change-me"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    coach_key: str = "dev-coach"
    player_key: str = "dev-player"
    secret_key: str = "dev-secret-change-me"
    https_only: bool = False

    app_name: str = "Rugby Coaching"
    coaches: str = "John"
    default_start_time: str = "18:30"
    training_weekday: int = 2  # Monday = 0 … Sunday = 6; new sessions default to the next one
    tz: str = "Europe/London"

    data_dir: Path = ROOT / "data"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "rugby-coaching.db"

    @property
    def coach_names(self) -> list[str]:
        return [n.strip() for n in self.coaches.split(",") if n.strip()]


settings = Settings()


def check_prod_settings(s: Settings) -> None:
    """Refuse to start in prod with weak, shared or dev keys."""
    if not s.https_only:
        return
    problems = []
    for name in ("coach_key", "player_key", "secret_key"):
        value = getattr(s, name)
        if len(value) < 20:
            problems.append(f"{name} is shorter than 20 characters")
        if value in DEV_KEYS:
            problems.append(f"{name} is a dev default")
    if s.coach_key == s.player_key:
        problems.append("coach_key and player_key are the same")
    if problems:
        raise RuntimeError("Unsafe prod settings: " + "; ".join(problems))
